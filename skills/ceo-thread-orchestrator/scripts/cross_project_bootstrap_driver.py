#!/usr/bin/env python3
"""Lazy, project-scoped Memory Runtime bootstrap for cross-project CEO tasks."""

from __future__ import annotations

import argparse
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Optional

import context_governor
import atomic_state

SCHEMA = "ceo_cross_project_bootstrap_driver_v1"
DEFAULT_RUNTIME = Path.home() / ".codex/skills/zhixia-local-docs/scripts/invoke-app-memory-runtime.cjs"
RuntimeInvoke = Callable[[dict[str, Any]], dict[str, Any]]


def compact_text(value: Any, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[:limit]


def invoke_app_runtime(request: dict[str, Any], runtime_path: Path = DEFAULT_RUNTIME) -> dict[str, Any]:
    completed = subprocess.run(
        ["node", str(runtime_path)],
        input=json.dumps(request, separators=(",", ":")),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(compact_text(completed.stderr or "app_owned_runtime_failed"))
    result = json.loads(completed.stdout)
    if not isinstance(result, dict):
        raise RuntimeError("app_owned_runtime_response_not_object")
    return result


def default_limits() -> dict[str, int]:
    return {
        "inputTokenLimit": context_governor.DEFAULT_INPUT_TOKEN_LIMIT,
        "contextTokenLimit": context_governor.DEFAULT_CONTEXT_TOKEN_LIMIT,
        "cumulativeInputLimit": context_governor.DEFAULT_CUMULATIVE_INPUT_LIMIT,
        "contextBytesLimit": context_governor.DEFAULT_CONTEXT_BYTES_LIMIT,
        "takeoverTokenLimit": context_governor.DEFAULT_TAKEOVER_TOKEN_LIMIT,
    }


def result_base() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "ok": True,
        "allowToolCalls": False,
        "allowProjectToolCalls": False,
        "allowProviderCalls": False,
        "allowOldThreadExecution": False,
        "knowledgeTaskMessages": 0,
        "sendCodexDelegation": False,
        "paidProviderCalls": 0,
        "paidProviderRetry": 0,
        "combinedProjectPacket": False,
    }


def verified_project_receipt(verify: dict[str, Any], workspace: str) -> tuple[dict[str, str] | None, str | None]:
    project_id = context_governor.first_present(verify, "projectId", "projectIdentity.projectId")
    identity = context_governor.first_present(verify, "projectIdentity.projectIdentitySha256")
    canonical_root = context_governor.first_present(verify, "projectIdentity.canonicalRoot", "projectIdentity.worktreeRoot")
    checkpoint = context_governor.first_present(verify, "scanBinding.authorizedCheckpointId")
    matched = context_governor.as_bool(context_governor.first_present(verify, "scanBinding.matched"))
    if str(verify.get("operation") or "") != "verify":
        return None, "verify_operation_mismatch"
    if str(verify.get("memoryMode") or "") != context_governor.REQUIRED_TAKEOVER_MEMORY_MODE:
        return None, "verify_memory_mode_not_app_owned"
    if str(verify.get("authorityVerification") or "") != context_governor.REQUIRED_AUTHORITY_VERIFICATION:
        return None, "verify_authority_not_app_owned"
    if context_governor.as_bool(verify.get("current")) is not True:
        return None, "verify_current_not_true"
    if context_governor.as_bool(verify.get("recoveryReady")) is not True:
        return None, "verify_recovery_not_ready"
    if not project_id or not identity or not canonical_root or not checkpoint or matched is not True:
        return None, "verify_project_scope_incomplete"
    if str(Path(str(canonical_root)).resolve()) != str(Path(workspace).resolve()):
        return None, "verify_workspace_mismatch"
    receipt = {
        "workspace": str(Path(workspace).resolve()),
        "projectId": str(project_id),
        "projectIdentitySha256": str(identity),
        "authorizedCheckpointId": str(checkpoint),
        "_driverCapability": context_governor.APP_OWNED_BOOTSTRAP_DRIVER_CAPABILITY,
    }
    receipt["verifyReceiptSha256"] = context_governor.project_bootstrap_receipt_sha256(receipt)
    return receipt, None


def run(
    event: dict[str, Any],
    governor_state: dict[str, Any],
    runtime_invoke: RuntimeInvoke = invoke_app_runtime,
    *,
    limits: Optional[dict[str, int]] = None,
) -> dict[str, Any]:
    limits = limits or default_limits()
    state_valid, state_reason, _ = context_governor.inspect_control_structure(
        governor_state or {}, max_bytes=context_governor.MAX_STATE_SERIALIZED_BYTES
    )
    if not state_valid:
        return result_base() | {
            "decision": "block",
            "reason": f"governor_state_{state_reason}",
            "programGoalBlocked": False,
            "unrelatedProjectsMayContinue": True,
            "nextAction": "replace_with_bounded_typed_control_state",
            "governorState": {},
        }
    initial = context_governor.evaluate(event, governor_state, limits)
    bootstrap = initial.get("projectBootstrap") if isinstance(initial.get("projectBootstrap"), dict) else {}
    if initial.get("reason") != "project_workspace_bootstrap_required":
        return result_base() | {
            "decision": initial.get("decision"),
            "reason": initial.get("reason"),
            "nextAction": initial.get("nextAction"),
            "governorState": initial.get("state"),
            "projectBootstrap": bootstrap,
        }

    project_key = str(bootstrap.get("activeProjectKey") or "")
    workspace = str(bootstrap.get("workspace") or "")
    if not project_key or not workspace:
        return result_base() | {
            "decision": "block",
            "reason": "project_workspace_bootstrap_contract_invalid",
            "programGoalBlocked": False,
            "nextAction": "repair_ordered_project_workspaces",
            "governorState": initial["state"],
        }

    task_goal = compact_text(event.get("taskGoal") or event.get("goal") or "load project continuity")
    try:
        verify = runtime_invoke({"operation": "verify", "workspace": workspace, "taskGoal": task_goal})
    except Exception as exc:
        verify = {
            "memoryMode": "fallback_stale",
            "authorityVerification": "unavailable",
            "current": False,
            "recoveryReady": False,
            "status": compact_text(exc),
        }
    verify_valid, verify_shape_reason, _ = context_governor.inspect_control_structure(
        verify, max_bytes=context_governor.MAX_TAKEOVER_SERIALIZED_BYTES
    )
    if not verify_valid:
        verify = {
            "memoryMode": "fallback_stale",
            "authorityVerification": "unavailable",
            "current": False,
            "recoveryReady": False,
            "status": verify_shape_reason,
        }

    verify_event = deepcopy(event)
    verify_event["activeProjectKey"] = project_key
    verify_event["inputTokens"] = 0
    verify_event["estimatedContextTokens"] = 0
    verify_event["estimatedContextBytes"] = 0
    verify_event["memory"] = verify
    verify_event.pop("takeoverPacket", None)
    verify_receipt, verify_scope_error = verified_project_receipt(verify, workspace)
    if context_governor.memory_fail_reason(verify) or verify_scope_error:
        if verify_scope_error and not context_governor.memory_fail_reason(verify):
            verify_event["memory"] = {
                "memoryMode": "fallback_stale",
                "authorityVerification": "unavailable",
                "current": False,
                "recoveryReady": False,
                "status": verify_scope_error,
            }
        blocked = context_governor.evaluate(verify_event, initial["state"], limits)
        return result_base() | {
            "decision": "block",
            "reason": verify_scope_error or blocked.get("reason"),
            "programGoalBlocked": False,
            "unrelatedProjectsMayContinue": True,
            "nextAction": "lazy_bootstrap_next_pending_project_or_repair_active_project",
            "governorState": blocked["state"],
            "projectBootstrap": blocked.get("projectBootstrap"),
        }

    prepare_request = {
        "operation": "prepare_takeover",
        "workspace": workspace,
        "taskGoal": task_goal,
        "queryType": "thread_recovery",
        "limit": 12,
        "tokenBudget": context_governor.DEFAULT_TAKEOVER_PREFERRED_TOKENS,
        "maxTokenBudget": context_governor.DEFAULT_TAKEOVER_TOKEN_LIMIT,
    }
    try:
        packet = runtime_invoke(prepare_request)
    except Exception as exc:
        packet = {
            "memoryMode": "fallback_stale",
            "authorityVerification": "unavailable",
            "current": False,
            "recoveryReady": False,
            "returnedCount": 0,
            "takeover": {"shouldInject": False},
            "status": compact_text(exc),
        }
    packet_valid, packet_shape_reason, _ = context_governor.inspect_control_structure(
        packet, max_bytes=context_governor.MAX_TAKEOVER_SERIALIZED_BYTES
    )
    if not packet_valid:
        packet = {
            "memoryMode": "fallback_stale",
            "authorityVerification": "unavailable",
            "current": False,
            "recoveryReady": False,
            "returnedCount": 0,
            "takeover": {"shouldInject": False},
            "status": packet_shape_reason,
        }
    if isinstance(packet, dict) and verify_receipt:
        packet = deepcopy(packet)
        packet["projectBootstrapReceipt"] = verify_receipt

    packet_event = deepcopy(event)
    packet_event["activeProjectKey"] = project_key
    packet_event["inputTokens"] = 0
    packet_event["estimatedContextTokens"] = 0
    packet_event["estimatedContextBytes"] = 0
    packet_event["takeoverPacket"] = packet
    packet_event.pop("memory", None)
    governed = context_governor.evaluate(packet_event, initial["state"], limits)
    if governed.get("decision") != "allow":
        ledger = governed["state"].get("projectInjectionLedger", {}).get(str(event.get("taskId") or event.get("threadId") or "default"), {}).get(project_key, {})
        ledger["bootstrapStatus"] = "stale"
        ledger["authority"] = {"status": str(governed.get("reason") or "prepare_takeover_failed")}
    result = result_base() | {
        "decision": governed.get("decision"),
        "reason": governed.get("reason"),
        "programGoalBlocked": governed.get("programGoalBlocked", False),
        "activeProjectKey": project_key,
        "workspace": workspace,
        "nextAction": governed.get("nextAction"),
        "contextInjectionMode": governed.get("contextInjectionMode"),
        "governorState": governed["state"],
        "projectBootstrap": governed.get("projectBootstrap"),
    }
    if governed.get("decision") == "allow":
        public_packet = deepcopy(packet)
        public_receipt = public_packet.get("projectBootstrapReceipt")
        if isinstance(public_receipt, dict):
            public_receipt.pop("_driverCapability", None)
        result["takeoverPacket"] = public_packet
    else:
        result["unrelatedProjectsMayContinue"] = True
        result["nextAction"] = "lazy_bootstrap_next_pending_project_or_repair_active_project"
    return result


def read_event(path: Path) -> dict[str, Any]:
    return context_governor.read_json(
        path, max_bytes=context_governor.MAX_EVENT_SERIALIZED_BYTES
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Lazy-bootstrap one explicit project workspace.")
    parser.add_argument("event", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--write-state", action="store_true")
    args = parser.parse_args()
    try:
        event = read_event(args.event)
        state = context_governor.read_confirmed_state_json(
            args.state, max_bytes=context_governor.MAX_STATE_SERIALIZED_BYTES
        ) if args.state else {}
    except (context_governor.ControlPayloadError, atomic_state.StateDurabilityError) as exc:
        result = result_base() | {
            "decision": "block",
            "reason": f"control_state_unavailable:{compact_text(exc)}",
            "programGoalBlocked": False,
            "unrelatedProjectsMayContinue": True,
            "nextAction": "reconcile_or_replace_bounded_control_state",
            "governorState": {},
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    state_sha256 = atomic_state.state_sha256(state)
    result = run(event, state)
    if args.write_state and args.state:
        try:
            atomic_state.atomic_write_json(
                args.state, result["governorState"], expected_sha256=state_sha256
            )
        except atomic_state.StateConflictError as exc:
            raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("decision") == "allow" else 2


if __name__ == "__main__":
    raise SystemExit(main())
