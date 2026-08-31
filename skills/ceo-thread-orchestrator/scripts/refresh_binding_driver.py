#!/usr/bin/env python3
"""Direct, idempotent CEO Flow driver for Zhixia accepted binding refreshes.

The driver accepts compact structured events only. It never calls a model,
sends a Codex task message, or reads chat/session/log/database payloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Optional

import context_governor
import atomic_state

SCHEMA = "ceo_refresh_binding_driver_v2"
LEGACY_SCHEMA = "ceo_refresh_binding_driver_v1"
DEFAULT_RUNTIME = Path.home() / ".codex/skills/zhixia-local-docs/scripts/invoke-app-memory-runtime.cjs"
DEFAULT_VERIFY_ATTEMPTS = 6
DEFAULT_MAX_VERIFY_CALLS_PER_KEY = 6
DEFAULT_VERIFY_DELAY_SECONDS = 0.25
RuntimeInvoke = Callable[[dict[str, Any]], dict[str, Any]]
RECEIPT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,219}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def compact_text(value: Any, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[:limit]


def default_driver_state() -> dict[str, Any]:
    return {"schema": SCHEMA, "refreshAttempts": {}, "laneRecovery": {}}


def receipt_id(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("receiptId") or value.get("id") or "").strip()
    return ""


def refresh_key(request: dict[str, Any]) -> str:
    identity = {
        "workspace": canonical_workspace(request.get("workspace")) or request.get("workspace"),
        "expectedProjectIdentitySha256": request.get("expectedProjectIdentitySha256"),
        "expectedScanSha256": request.get("expectedScanSha256"),
        "previousCheckpointId": request.get("previousCheckpointId"),
        "acceptedEvidenceReceipt": receipt_id(request.get("acceptedEvidenceReceipt")),
        "acceptedEvidenceReceiptDigest": str(
            request.get("acceptedEvidenceReceiptDigest") or ""
        ).strip().lower(),
        "acceptedPathDigest": accepted_path_digest(request.get("acceptedChangedPaths")),
        "lane": request.get("lane"),
    }
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def legacy_refresh_key(request: dict[str, Any]) -> str:
    identity = {
        "workspace": canonical_workspace(request.get("workspace")) or request.get("workspace"),
        "projectIdentity": request.get("expectedProjectIdentitySha256"),
        "scan": request.get("expectedScanSha256"),
        "receipt": receipt_id(request.get("acceptedEvidenceReceipt")),
    }
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def canonical_changed_paths(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(path) for path in value)


def accepted_path_digest(value: Any) -> str:
    raw = json.dumps(canonical_changed_paths(value), separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def canonical_workspace(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip() or not Path(value).is_absolute():
        return None
    return str(Path(value).resolve())


def resolve_refresh_namespace(
    governor_state: dict[str, Any], event: dict[str, Any], request: dict[str, Any]
) -> tuple[dict[str, str] | None, str | None]:
    """Bind refresh state to governor-owned workspace identity, never caller labels."""

    task = str(event.get("taskId") or event.get("threadId") or "default")
    request_workspace = canonical_workspace(request.get("workspace"))
    identity = str(request.get("expectedProjectIdentitySha256") or "").strip()
    if request_workspace is None or not identity:
        return None, "refresh_namespace_identity_missing"

    registered = governor_state.get("projectWorkspacesByTask", {}).get(task)
    if isinstance(registered, list) and registered:
        project_key = str(request.get("projectKey") or "").strip()
        match = next(
            (
                item
                for item in registered
                if isinstance(item, dict) and item.get("projectKey") == project_key
            ),
            None,
        )
        if not isinstance(match, dict):
            return None, "refresh_project_namespace_unregistered"
        registered_workspace = canonical_workspace(match.get("workspace"))
        ledger = (
            governor_state.get("projectInjectionLedger", {})
            .get(task, {})
            .get(project_key)
        )
        if not isinstance(ledger, dict):
            return None, "refresh_project_ledger_unregistered"
        registered_id = str(match.get("projectId") or ledger.get("projectId") or "").strip()
        request_id = str(request.get("projectId") or "").strip()
        caller_id = str(event.get("projectId") or event.get("expectedProjectId") or "").strip()
        if (
            registered_workspace != request_workspace
            or not registered_id
            or request_id != registered_id
            or (caller_id and caller_id != registered_id)
            or str(ledger.get("workspace") or "") != registered_workspace
        ):
            return None, "refresh_project_namespace_mismatch"
        ledger_identity = str(
            ledger.get("lastGenerationBasis", {}).get("projectIdentitySha256") or ""
        ).strip()
        if not ledger_identity or ledger_identity != identity:
            return None, "refresh_project_identity_mismatch"
        return {
            "mode": "registered_project",
            "task": task,
            "ledgerKey": project_key,
            "namespace": f"registered:{project_key}",
            "workspace": request_workspace,
            "projectIdentity": identity,
            "projectId": registered_id,
        }, None

    if event.get("activeProjectKey") not in (None, "") or event.get("projectId") not in (None, ""):
        return None, "refresh_project_namespace_unregistered"
    ledger = governor_state.get("taskInjectionLedger", {}).get(task)
    if not isinstance(ledger, dict):
        return None, "refresh_single_project_ledger_missing"
    verified_identity = str(
        ledger.get("lastGenerationBasis", {}).get("projectIdentitySha256") or ""
    ).strip()
    verified_workspace = canonical_workspace(ledger.get("workspace"))
    if (
        verified_workspace is None
        or verified_workspace != request_workspace
        or not verified_identity
        or verified_identity != identity
    ):
        return None, "refresh_single_project_identity_mismatch"
    digest = hashlib.sha256(
        f"{request_workspace}\0{verified_identity}".encode("utf-8")
    ).hexdigest()
    return {
        "mode": "single_project",
        "task": task,
        "ledgerKey": task,
        "namespace": f"single:{digest}",
        "workspace": request_workspace,
        "projectIdentity": verified_identity,
        "projectId": "",
    }, None


def validate_refresh_request(request: dict[str, Any]) -> list[str]:
    required = (
        "workspace",
        "expectedProjectIdentitySha256",
        "expectedScanSha256",
        "previousCheckpointId",
        "lane",
    )
    missing = [name for name in required if request.get(name) in (None, "")]
    if request.get("execute") is not True:
        missing.append("execute=true")
    if not RECEIPT_RE.fullmatch(receipt_id(request.get("acceptedEvidenceReceipt"))):
        missing.append("acceptedEvidenceReceipt")
    receipt_digest = str(request.get("acceptedEvidenceReceiptDigest") or "").strip().lower()
    if not SHA256_RE.fullmatch(receipt_digest):
        missing.append("acceptedEvidenceReceiptDigest")
    paths = request.get("acceptedChangedPaths")
    if (
        not isinstance(paths, list)
        or not paths
        or any(not isinstance(path, str) or not path for path in paths)
    ):
        missing.append("acceptedChangedPaths")
    evidence = request.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("decision") != "accept":
        missing.append("evidence.decision=accept")
    elif not isinstance(evidence.get("sourceRefs"), list) or not evidence["sourceRefs"]:
        missing.append("evidence.sourceRefs")
    else:
        workspace = str(request.get("workspace") or "")
        root = Path(workspace).resolve() if workspace else None
        referenced_paths = set()
        for ref in evidence["sourceRefs"]:
            if not isinstance(ref, dict) or not ref.get("path") or not ref.get("hash"):
                continue
            path = str(ref["path"])
            if re.match(r"^[a-z][a-z0-9+.-]*://", path, re.IGNORECASE):
                if not path.startswith(("git://", "memory-runtime://")):
                    missing.append("cross-project evidence.sourceRefs")
                    continue
            elif root is not None:
                try:
                    candidate = Path(path)
                    scoped = candidate if candidate.is_absolute() else root / candidate
                    resolved = scoped.resolve(strict=True)
                    resolved.relative_to(root)
                except (FileNotFoundError, OSError, RuntimeError, ValueError):
                    missing.append("cross-project evidence.sourceRefs")
                    continue
                expected_hash = str(ref.get("hash") or "").strip().lower()
                if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                    missing.append("evidence.sourceRefs sha256")
                    continue
                if hashlib.sha256(resolved.read_bytes()).hexdigest() != expected_hash:
                    missing.append("evidence.sourceRefs hash mismatch")
                    continue
            request_project_id = request.get("projectId")
            ref_project_id = ref.get("projectId")
            if request_project_id and not ref_project_id:
                missing.append("cross-project evidence.projectId")
                continue
            if request_project_id and ref_project_id and str(request_project_id) != str(ref_project_id):
                missing.append("cross-project evidence.projectId")
                continue
            if os.path.isabs(path) and workspace:
                try:
                    path = os.path.relpath(path, workspace)
                except ValueError:
                    continue
            referenced_paths.add(path.replace("\\", "/").removeprefix("./"))
        accepted_paths = {str(path).replace("\\", "/").removeprefix("./") for path in paths or []}
        if not accepted_paths.issubset(referenced_paths):
            missing.append("acceptedChangedPaths sourceRefs coverage")
    return missing


def runtime_refresh_request(request: dict[str, Any]) -> dict[str, Any]:
    """Remove CEO Flow-only project routing metadata before Runtime invocation."""
    runtime_request = {
        key: value for key, value in request.items() if key not in {"projectKey", "projectId"}
    }
    runtime_request["acceptedPathDigest"] = accepted_path_digest(
        request.get("acceptedChangedPaths")
    )
    runtime_request["refreshKey"] = refresh_key(request)
    return runtime_request


def runtime_outcome_query_request(request: dict[str, Any]) -> dict[str, Any]:
    """Describe the required read-only Runtime reconciliation contract."""

    return {
        "operation": "query_refresh_outcome",
        "workspace": request["workspace"],
        "expectedProjectIdentitySha256": request["expectedProjectIdentitySha256"],
        "expectedScanSha256": request["expectedScanSha256"],
        "previousCheckpointId": request["previousCheckpointId"],
        "acceptedEvidenceReceipt": receipt_id(request["acceptedEvidenceReceipt"]),
        "acceptedEvidenceReceiptDigest": request["acceptedEvidenceReceiptDigest"],
        "acceptedChangedPaths": canonical_changed_paths(request["acceptedChangedPaths"]),
        "acceptedPathDigest": accepted_path_digest(request["acceptedChangedPaths"]),
        "lane": request["lane"],
        "refreshKey": refresh_key(request),
    }


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
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("app_owned_runtime_invalid_json") from exc
    if not isinstance(response, dict):
        raise RuntimeError("app_owned_runtime_object_required")
    return response


def valid_refresh_response(response: dict[str, Any], request: dict[str, Any]) -> tuple[bool, str]:
    checks = {
        "operation": response.get("operation") == "refresh_binding",
        "status": response.get("status") == "verified",
        "memoryMode": response.get("memoryMode") == context_governor.REQUIRED_TAKEOVER_MEMORY_MODE,
        "authorityVerification": response.get("authorityVerification") == context_governor.REQUIRED_AUTHORITY_VERIFICATION,
        "current": response.get("current") is True,
        "recoveryReady": response.get("recoveryReady") is True,
        "scan": response.get("scanSha256") == request.get("expectedScanSha256"),
        "projectIdentity": context_governor.first_present(response, "projectIdentity.projectIdentitySha256")
        == request.get("expectedProjectIdentitySha256"),
        "previousCheckpoint": response.get("previousCheckpointId") == request.get("previousCheckpointId"),
        "newCheckpoint": bool(response.get("authorizedCheckpointId"))
        and response.get("authorizedCheckpointId") != request.get("previousCheckpointId"),
        "receipt": bool(response.get("receiptId")),
        "generation": bool(response.get("contextGenerationId")),
        "acceptedReceipt": response.get("acceptedEvidenceReceipt") == request.get("acceptedEvidenceReceipt"),
        "acceptedReceiptDigest": response.get("acceptedEvidenceReceiptDigest")
        == request.get("acceptedEvidenceReceiptDigest"),
        "acceptedPaths": canonical_changed_paths(response.get("acceptedChangedPaths"))
        == canonical_changed_paths(request.get("acceptedChangedPaths")),
        "acceptedPathDigest": response.get("acceptedPathDigest")
        == accepted_path_digest(request.get("acceptedChangedPaths")),
        "lane": response.get("lane") == request.get("lane"),
        "refreshKey": response.get("refreshKey") == refresh_key(request),
        "outcomeDigest": bool(SHA256_RE.fullmatch(str(response.get("outcomeDigest") or ""))),
        "outcomeVerification": response.get("outcomeVerification")
        == "app_owned_authenticated",
        "shouldInject": context_governor.as_bool(context_governor.first_present(response, "takeover.shouldInject")) is True,
    }
    failed = [name for name, ok in checks.items() if not ok]
    return not failed, failed[0] if failed else "verified_refresh_receipt"


def valid_verify_response(response: dict[str, Any], request: dict[str, Any], checkpoint_id: str) -> tuple[bool, str]:
    checks = {
        "operation": response.get("operation") == "verify",
        "memoryMode": response.get("memoryMode") == context_governor.REQUIRED_TAKEOVER_MEMORY_MODE,
        "authorityVerification": response.get("authorityVerification") == context_governor.REQUIRED_AUTHORITY_VERIFICATION,
        "current": response.get("current") is True,
        "recoveryReady": response.get("recoveryReady") is True,
        "matched": context_governor.as_bool(context_governor.first_present(response, "scanBinding.matched")) is True,
        "scan": context_governor.first_present(response, "scanBinding.currentScanSha256")
        == request.get("expectedScanSha256"),
        "projectIdentity": context_governor.first_present(response, "projectIdentity.projectIdentitySha256")
        == request.get("expectedProjectIdentitySha256"),
        "checkpoint": context_governor.first_present(response, "scanBinding.authorizedCheckpointId") == checkpoint_id,
    }
    failed = [name for name, ok in checks.items() if not ok]
    return not failed, failed[0] if failed else "verified_current_binding"


def compact_runtime_receipt(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation": response.get("operation"),
        "status": response.get("status"),
        "memoryMode": response.get("memoryMode"),
        "authorityVerification": response.get("authorityVerification"),
        "current": response.get("current"),
        "recoveryReady": response.get("recoveryReady"),
        "matched": context_governor.first_present(response, "scanBinding.matched"),
        "scanSha256": response.get("scanSha256") or context_governor.first_present(response, "scanBinding.currentScanSha256"),
        "authorizedCheckpointId": response.get("authorizedCheckpointId")
        or context_governor.first_present(response, "scanBinding.authorizedCheckpointId"),
        "receiptId": response.get("receiptId"),
        "contextGenerationId": response.get("contextGenerationId"),
        "refreshKey": response.get("refreshKey"),
        "acceptedEvidenceReceiptDigest": response.get("acceptedEvidenceReceiptDigest"),
        "acceptedPathDigest": response.get("acceptedPathDigest"),
        "lane": response.get("lane"),
        "outcomeDigest": response.get("outcomeDigest"),
        "outcomeVerification": response.get("outcomeVerification"),
    }


def generation_ledger(
    governor_state: dict[str, Any], namespace: dict[str, str]
) -> dict[str, Any] | None:
    task = namespace["task"]
    if namespace["mode"] == "registered_project":
        ledger = governor_state.get("projectInjectionLedger", {}).get(task, {}).get(namespace["ledgerKey"])
    else:
        ledger = governor_state.get("taskInjectionLedger", {}).get(task)
    return ledger if isinstance(ledger, dict) else None


def commit_verified_generation(
    governor_state: dict[str, Any],
    event: dict[str, Any],
    request: dict[str, Any],
    attempt: dict[str, Any],
    namespace: dict[str, str],
) -> None:
    ledger = generation_ledger(governor_state, namespace)
    if ledger is None:
        raise atomic_state.StateConflictError("verified refresh ledger disappeared")
    generation = str(attempt.get("contextGenerationId") or "")
    injected = ledger.setdefault("injectedGenerationIds", [])
    if generation and generation not in injected:
        injected.append(generation)
    prior_basis = ledger.get("lastGenerationBasis") if isinstance(ledger.get("lastGenerationBasis"), dict) else {}
    ledger["lastGenerationBasis"] = {
        **prior_basis,
        "scanHash": str(request.get("expectedScanSha256") or ""),
        "projectIdentitySha256": str(request.get("expectedProjectIdentitySha256") or ""),
        "verifiedMemoryStateHash": str(attempt.get("authorizedCheckpointId") or ""),
    }
    ledger["verifiedRefresh"] = {
        "refreshKey": refresh_key(request),
        "contextGenerationId": generation,
        "scanSha256": str(request.get("expectedScanSha256") or ""),
        "authorizedCheckpointId": str(attempt.get("authorizedCheckpointId") or ""),
        "authorityReceiptId": str(attempt.get("receiptId") or ""),
        "namespace": namespace["namespace"],
    }
    if namespace["mode"] == "single_project":
        governor_state["injectedGenerationIds"] = list(injected)
        governor_state["lastGenerationBasis"] = dict(ledger["lastGenerationBasis"])


def verified_generation_committed(
    governor_state: dict[str, Any],
    event: dict[str, Any],
    request: dict[str, Any],
    attempt: dict[str, Any],
    namespace: dict[str, str],
) -> bool:
    ledger = generation_ledger(governor_state, namespace)
    if ledger is None:
        return False
    committed = ledger.get("verifiedRefresh")
    return isinstance(committed, dict) and committed == {
        "refreshKey": refresh_key(request),
        "contextGenerationId": str(attempt.get("contextGenerationId") or ""),
        "scanSha256": str(request.get("expectedScanSha256") or ""),
        "authorizedCheckpointId": str(attempt.get("authorizedCheckpointId") or ""),
        "authorityReceiptId": str(attempt.get("receiptId") or ""),
        "namespace": namespace["namespace"],
    }


def verified_commit_digest(
    governor_state: dict[str, Any],
    request: dict[str, Any],
    attempt: dict[str, Any],
    namespace: dict[str, str],
) -> str | None:
    ledger = generation_ledger(governor_state, namespace)
    committed = ledger.get("verifiedRefresh") if isinstance(ledger, dict) else None
    if not isinstance(committed, dict) or not verified_generation_committed(
        governor_state, {}, request, attempt, namespace
    ):
        return None
    envelope = {
        "refreshKey": refresh_key(request),
        "namespace": namespace["namespace"],
        "driver": {
            "status": "verified",
            "workspace": attempt.get("workspace"),
            "scanSha256": attempt.get("scanSha256"),
            "acceptedEvidenceReceipt": attempt.get("acceptedEvidenceReceipt"),
            "acceptedEvidenceReceiptDigest": attempt.get("acceptedEvidenceReceiptDigest"),
            "previousCheckpointId": attempt.get("previousCheckpointId"),
            "acceptedChangedPaths": attempt.get("acceptedChangedPaths"),
            "acceptedPathDigest": attempt.get("acceptedPathDigest"),
            "lane": attempt.get("lane"),
            "authorizedCheckpointId": attempt.get("authorizedCheckpointId"),
            "receiptId": attempt.get("receiptId"),
            "contextGenerationId": attempt.get("contextGenerationId"),
            "refreshReceipt": attempt.get("refreshReceipt"),
            "verifyReceipt": attempt.get("verifyReceipt"),
        },
        "governor": committed,
    }
    raw = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def confirmation_matches(
    confirmations: dict[str, Any] | None,
    key: str,
    digest: str | None,
    durability_required: bool,
) -> bool:
    if not durability_required:
        return digest is not None
    if confirmations is None:
        return False
    record = confirmations.get("confirmedCommits", {}).get(key)
    return (
        isinstance(record, dict)
        and record.get("status") == "confirmed"
        and record.get("commitDigest") == digest
    )


def confirmation_state(
    confirmations: dict[str, Any] | None, key: str, digest: str
) -> dict[str, Any]:
    state = deepcopy(confirmations) if isinstance(confirmations, dict) else {}
    state.setdefault("schema", "ceo_refresh_durability_v1")
    state.setdefault("confirmedCommits", {})[key] = {
        "status": "confirmed",
        "commitDigest": digest,
    }
    return state


def result_base(scope: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "scope": scope,
        "programGoalBlocked": False,
        "unrelatedLanesMayContinue": True,
        "knowledgeTaskMessages": 0,
        "sendCodexDelegation": False,
        "paidProviderCalls": 0,
        "providerCallsBeforeMatched": 0,
        "paidProviderRetry": 0,
        "userAuthorizationRequired": False,
        "allowToolCalls": False,
        "allowProjectToolCalls": False,
        "allowRecoveryControlTools": False,
        "recoveryControlToolAllowlist": [],
        "allowOldThreadExecution": False,
        "unbindHarvestDriver": False,
    }


def scoped_block(reason: str, next_action: str, scope: str, *, detail: str | None = None) -> dict[str, Any]:
    recovery_tools = [] if next_action == "wait_for_new_scan_or_formal_receipt" else ["refresh_binding_driver"]
    result = result_base(scope) | {
        "ok": True,
        "decision": "block",
        "reason": reason,
        "allowProviderCalls": False,
        "allowRecoveryControlTools": bool(recovery_tools),
        "recoveryControlToolAllowlist": recovery_tools,
        "laneStatus": "paused_for_memory_binding",
        "lifecycleState": "lane_paused_recoverable",
        "autoRecoveryEligible": True,
        "nextAction": next_action,
        "blocker": {"code": reason, "scope": scope, "nextAction": next_action},
    }
    if detail:
        result["blocker"]["detail"] = compact_text(detail)
    return result


def run(
    event: dict[str, Any],
    governor_state: dict[str, Any],
    driver_state: dict[str, Any],
    runtime_invoke: RuntimeInvoke = invoke_app_runtime,
    *,
    limits: Optional[dict[str, int]] = None,
    verify_attempts: int = DEFAULT_VERIFY_ATTEMPTS,
    max_verify_calls_per_key: int = DEFAULT_MAX_VERIFY_CALLS_PER_KEY,
    verify_delay_seconds: float = DEFAULT_VERIFY_DELAY_SECONDS,
    sleeper: Callable[[float], None] = time.sleep,
    persist_driver_state: Optional[Callable[[dict[str, Any]], None]] = None,
    persist_governor_state: Optional[Callable[[dict[str, Any]], None]] = None,
    durability_confirmations: dict[str, Any] | None = None,
    persist_durability_confirmation: Optional[Callable[[dict[str, Any]], None]] = None,
    runtime_outcome_query: RuntimeInvoke | None = None,
) -> dict[str, Any]:
    limits = limits or {
        "inputTokenLimit": context_governor.DEFAULT_INPUT_TOKEN_LIMIT,
        "contextTokenLimit": context_governor.DEFAULT_CONTEXT_TOKEN_LIMIT,
        "cumulativeInputLimit": context_governor.DEFAULT_CUMULATIVE_INPUT_LIMIT,
        "contextBytesLimit": context_governor.DEFAULT_CONTEXT_BYTES_LIMIT,
        "takeoverTokenLimit": context_governor.DEFAULT_TAKEOVER_TOKEN_LIMIT,
    }
    for label, value, max_bytes in (
        ("driver_state", driver_state or {}, context_governor.MAX_STATE_SERIALIZED_BYTES),
        ("durability_state", durability_confirmations or {}, context_governor.MAX_STATE_SERIALIZED_BYTES),
    ):
        valid, reason, _ = context_governor.inspect_control_structure(value, max_bytes=max_bytes)
        if not valid:
            result = scoped_block(
                f"{label}_{reason}",
                "replace_with_bounded_typed_control_state",
                "refresh_state",
            )
            result.update(
                {
                    "governorState": governor_state if isinstance(governor_state, dict) else {},
                    "driverState": default_driver_state(),
                }
            )
            return result
    state = deepcopy(driver_state) if driver_state else default_driver_state()
    state.setdefault("schema", SCHEMA)
    attempts = state.setdefault("refreshAttempts", {})
    lane_recovery = state.setdefault("laneRecovery", {})
    durability_required = (
        durability_confirmations is not None
        or persist_driver_state is not None
        or persist_governor_state is not None
        or persist_durability_confirmation is not None
    )
    governor_result = context_governor.evaluate(event, governor_state, limits)
    lane_scope = str(event.get("lane") or event.get("module") or event.get("laneId") or event.get("moduleId") or "lane_or_module")
    scope = lane_scope

    if governor_result.get("reason") != "refresh_binding_required":
        result = dict(governor_result)
        result.update(
            {
                "knowledgeTaskMessages": 0,
                "sendCodexDelegation": False,
                "paidProviderCalls": 0,
                "providerCallsBeforeMatched": 0,
                "paidProviderRetry": 0,
            }
        )
        result["governorState"] = governor_result["state"]
        result["driverState"] = state
        return result

    request = governor_result.get("refreshBindingRequest") or {}
    namespace, namespace_error = resolve_refresh_namespace(governor_result["state"], event, request)
    if namespace_error or namespace is None:
        result = scoped_block(
            namespace_error or "refresh_namespace_invalid",
            "register_exact_project_workspace_or_verify_single_project_identity",
            scope,
        )
        result.update({"governorState": governor_result["state"], "driverState": state})
        return result
    recovery_scope = f"{namespace['namespace']}:{lane_scope}"
    missing = validate_refresh_request(request)
    if missing:
        result = scoped_block("refresh_binding_request_invalid", "repair_compact_refresh_evidence", scope, detail=",".join(missing))
        result.update({"governorState": governor_result["state"], "driverState": state})
        return result

    key = refresh_key(request)
    legacy_key = legacy_refresh_key(request)
    if (
        state.get("schema") == LEGACY_SCHEMA
        and key not in attempts
        and legacy_key in attempts
    ):
        result = scoped_block(
            "legacy_refresh_attempt_v2_reconciliation_required",
            "inspect_legacy_attempt_without_replaying_runtime",
            scope,
        )
        result.update(
            {
                "refreshKey": key,
                "legacyRefreshKey": legacy_key,
                "governorState": governor_result["state"],
                "driverState": state,
            }
        )
        return result
    state["schema"] = SCHEMA
    attempt = attempts.get(key)
    refresh_response: dict[str, Any] | None = None
    if attempt:
        evidence_changed = (
            attempt.get("workspace") != canonical_workspace(request.get("workspace"))
            or attempt.get("projectIdentitySha256")
            != request.get("expectedProjectIdentitySha256")
            or attempt.get("scanSha256") != request.get("expectedScanSha256")
            or attempt.get("acceptedEvidenceReceipt")
            != receipt_id(request.get("acceptedEvidenceReceipt"))
            or attempt.get("previousCheckpointId") != request.get("previousCheckpointId")
            or attempt.get("acceptedEvidenceReceiptDigest")
            != request.get("acceptedEvidenceReceiptDigest")
            or attempt.get("lane") != request.get("lane")
            or canonical_changed_paths(attempt.get("acceptedChangedPaths"))
            != canonical_changed_paths(request.get("acceptedChangedPaths"))
            or attempt.get("acceptedPathDigest")
            != accepted_path_digest(request.get("acceptedChangedPaths"))
            or attempt.get("refreshKey") != key
        )
        if evidence_changed:
            result = scoped_block("refresh_attempt_evidence_changed", "inspect_local_refresh_blocker", scope)
            result.update({"refreshKey": key, "governorState": governor_result["state"], "driverState": state})
            return result
        if attempt.get("status") == "started":
            if runtime_outcome_query is None:
                result = scoped_block(
                    "runtime_outcome_query_required",
                    "query_exact_refresh_outcome_without_replaying_refresh",
                    scope,
                )
                result.update(
                    {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
                )
                return result
            if int(attempt.get("reconciliationQueryCount") or 0) >= 1:
                result = scoped_block(
                    "runtime_outcome_query_exhausted_no_poll",
                    "wait_for_exact_runtime_outcome_receipt_or_new_scan",
                    scope,
                )
                result.update(
                    {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
                )
                return result
            attempt["reconciliationQueryCount"] = 1
            if persist_driver_state:
                persist_driver_state(state)
            try:
                queried = runtime_outcome_query(runtime_outcome_query_request(request))
            except Exception as exc:
                attempt["status"] = "outcome_unknown"
                attempt["reconciliationFailure"] = compact_text(exc)
                if persist_driver_state:
                    persist_driver_state(state)
                result = scoped_block(
                    "runtime_outcome_query_failed_no_poll",
                    "wait_for_exact_runtime_outcome_receipt_or_new_scan",
                    scope,
                    detail=str(exc),
                )
                result.update(
                    {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
                )
                return result
            query_valid, query_reason, _ = context_governor.inspect_control_structure(
                queried, max_bytes=context_governor.MAX_TAKEOVER_SERIALIZED_BYTES
            )
            if not query_valid:
                queried = {"operation": "invalid", "status": query_reason}
            valid, reason = valid_refresh_response(
                {**queried, "operation": "refresh_binding"}, request
            )
            exact_query_envelope = (
                queried.get("operation") == "query_refresh_outcome"
                and queried.get("refreshKey") == key
            )
            if not valid or not exact_query_envelope:
                attempt["status"] = "outcome_unknown"
                attempt["reconciliationFailure"] = (
                    reason if not valid else "query_operation_or_refreshKey_mismatch"
                )
                if persist_driver_state:
                    persist_driver_state(state)
                result = scoped_block(
                    "runtime_outcome_receipt_invalid_no_poll",
                    "wait_for_exact_runtime_outcome_receipt_or_new_scan",
                    scope,
                    detail=reason,
                )
                result.update(
                    {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
                )
                return result
            attempt.update(
                {
                    "status": "refreshed",
                    "authorizedCheckpointId": queried["authorizedCheckpointId"],
                    "receiptId": queried["receiptId"],
                    "contextGenerationId": queried["contextGenerationId"],
                    "refreshReceipt": compact_runtime_receipt(queried),
                    "reconciledFromStarted": True,
                }
            )
            if persist_driver_state:
                persist_driver_state(state)
            refresh_response = queried
        elif attempt.get("status") == "outcome_unknown":
            result = scoped_block(
                "runtime_outcome_query_exhausted_no_poll",
                "wait_for_exact_runtime_outcome_receipt_or_new_scan",
                scope,
            )
            result.update(
                {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
            )
            return result
        elif attempt.get("status") not in {"refreshed", "verified", "governor_commit_failed"}:
            result = scoped_block("duplicate_refresh_blocked", "inspect_local_refresh_blocker", scope)
            result.update({"refreshKey": key, "governorState": governor_result["state"], "driverState": state})
            return result
        if attempt.get("status") in {"verified", "governor_commit_failed"}:
            exact_commit = verified_generation_committed(
                governor_result["state"], event, request, attempt, namespace
            )
            repaired_commit = not exact_commit
            if repaired_commit:
                commit_verified_generation(
                    governor_result["state"], event, request, attempt, namespace
                )
                if persist_governor_state:
                    try:
                        persist_governor_state(governor_result["state"])
                    except Exception as exc:
                        attempt["status"] = "governor_commit_failed"
                        attempt["governorCommitFailure"] = compact_text(exc)
                        if persist_driver_state:
                            persist_driver_state(state)
                        result = scoped_block(
                            "refresh_state_reconciliation_required",
                            "retry_local_commit_reconciliation_without_runtime_call",
                            scope,
                            detail=str(exc),
                        )
                        result.update(
                            {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
                        )
                        return result
            attempt["status"] = "verified"
            attempt.pop("governorCommitFailure", None)
            digest = verified_commit_digest(
                governor_result["state"], request, attempt, namespace
            )
            if digest is None:
                result = scoped_block(
                    "refresh_state_reconciliation_required",
                    "reconcile_verified_refresh_into_governor_state_without_runtime_call",
                    scope,
                )
                result.update(
                    {
                        "refreshKey": key,
                        "governorState": governor_result["state"],
                        "driverState": state,
                    }
                )
                return result
            if repaired_commit:
                attempt["coherenceDigest"] = digest
                if persist_driver_state:
                    persist_driver_state(state)
                result = scoped_block(
                    "refresh_state_reconciled_retry_required",
                    "retry_once_after_exact_governor_commit_reconciliation",
                    scope,
                )
                result.update(
                    {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
                )
                return result
            if not confirmation_matches(
                durability_confirmations, key, digest, durability_required
            ):
                attempt["coherenceDigest"] = digest
                if persist_driver_state:
                    persist_driver_state(state)
                confirmations = confirmation_state(durability_confirmations, key, digest)
                if persist_durability_confirmation:
                    persist_durability_confirmation(confirmations)
                elif durability_confirmations is not None:
                    result = scoped_block(
                        "refresh_durability_reconciliation_required",
                        "persist_exact_durability_confirmation_without_runtime_call",
                        scope,
                    )
                    result.update(
                        {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
                    )
                    return result
                result = scoped_block(
                    "refresh_durability_reconciled_retry_required",
                    "retry_once_after_confirmed_local_reconciliation",
                    scope,
                )
                result.update(
                    {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
                )
                return result
            result = result_base(scope) | {
                "ok": True,
                "decision": "allow",
                "reason": "refresh_binding_already_verified_no_poll",
                "allowProviderCalls": True,
                "allowToolCalls": True,
                "allowProjectToolCalls": True,
                "allowRecoveryControlTools": False,
                "recoveryControlToolAllowlist": [],
                "allowOldThreadExecution": True,
                "laneStatus": "resumed",
                "lifecycleState": "active",
                "autoRecoveryEligible": False,
                "resumeProgramGoal": False,
                "clearHistoricalGoalBlocked": False,
                "nextAction": "continue_related_lane_without_runtime_poll",
                "refreshKey": key,
                "refresh": attempt.get("refreshReceipt") or {},
                "verify": attempt.get("verifyReceipt") or {},
                "governorState": governor_result["state"],
                "driverState": state,
            }
            return result
        if attempt.get("verifySequenceCompleted") is True:
            result = scoped_block("verify_retry_exhausted_no_poll", "wait_for_new_scan_or_formal_receipt", scope)
            result.update(
                {
                    "refreshKey": key,
                    "refresh": attempt.get("refreshReceipt") or {},
                    "verify": attempt.get("verifyReceipt") or {},
                    "governorState": governor_result["state"],
                    "driverState": state,
                }
            )
            return result
        refresh_response = {
            "operation": "refresh_binding",
            "status": "verified",
            "authorizedCheckpointId": attempt.get("authorizedCheckpointId"),
            "receiptId": attempt.get("receiptId"),
            "contextGenerationId": attempt.get("contextGenerationId"),
        }
    else:
        attempt = {
            "status": "started",
            "workspace": canonical_workspace(request["workspace"]),
            "projectIdentitySha256": request["expectedProjectIdentitySha256"],
            "scanSha256": request["expectedScanSha256"],
            "acceptedEvidenceReceipt": receipt_id(request["acceptedEvidenceReceipt"]),
            "acceptedEvidenceReceiptDigest": request["acceptedEvidenceReceiptDigest"],
            "previousCheckpointId": request["previousCheckpointId"],
            "acceptedChangedPaths": canonical_changed_paths(request["acceptedChangedPaths"]),
            "acceptedPathDigest": accepted_path_digest(request["acceptedChangedPaths"]),
            "lane": request["lane"],
            "refreshKey": key,
            "namespace": deepcopy(namespace),
            "refreshCallCount": 1,
        }
        attempts[key] = attempt
        if persist_driver_state:
            persist_driver_state(state)
        try:
            refresh_response = runtime_invoke(runtime_refresh_request(request))
        except Exception as exc:  # Runtime boundary: return a compact lane-local blocker.
            attempt.update({"status": "failed", "failure": compact_text(exc)})
            lane_recovery[recovery_scope] = {
                "status": "lane_paused_recoverable",
                "refreshKey": key,
                "nextAction": "wait_for_new_scan_or_formal_receipt",
            }
            if persist_driver_state:
                persist_driver_state(state)
            result = scoped_block("refresh_binding_failed", "inspect_local_refresh_blocker", scope, detail=str(exc))
            result.update({"refreshKey": key, "governorState": governor_result["state"], "driverState": state})
            return result
        response_valid, response_reason, _ = context_governor.inspect_control_structure(
            refresh_response, max_bytes=context_governor.MAX_TAKEOVER_SERIALIZED_BYTES
        )
        if not response_valid:
            refresh_response = {"operation": "invalid", "status": response_reason}
        valid, reason = valid_refresh_response(refresh_response, request)
        task = str(event.get("taskId") or event.get("threadId") or "default")
        project_ledger = generation_ledger(governor_result["state"], namespace) or {}
        injected_source = project_ledger.get("injectedGenerationIds", [])
        injected = set(str(value) for value in injected_source)
        if valid and str(refresh_response.get("contextGenerationId")) in injected:
            valid, reason = False, "contextGenerationId_not_new"
        if not valid:
            attempt.update({"status": "failed", "failure": reason})
            lane_recovery[recovery_scope] = {
                "status": "lane_paused_recoverable",
                "refreshKey": key,
                "nextAction": "wait_for_new_scan_or_formal_receipt",
            }
            if persist_driver_state:
                persist_driver_state(state)
            result = scoped_block("refresh_binding_invalid_receipt", "inspect_local_refresh_blocker", scope, detail=reason)
            result.update({"refreshKey": key, "governorState": governor_result["state"], "driverState": state})
            return result
        attempt.update(
            {
                "status": "refreshed",
                "authorizedCheckpointId": refresh_response["authorizedCheckpointId"],
                "receiptId": refresh_response["receiptId"],
                "contextGenerationId": refresh_response["contextGenerationId"],
                "refreshReceipt": compact_runtime_receipt(refresh_response),
            }
        )
        if persist_driver_state:
            persist_driver_state(state)

    checkpoint_id = str(attempt.get("authorizedCheckpointId") or "")
    verify_response: dict[str, Any] = {}
    verify_reason = "verify_not_run"
    verify_request = {
        "operation": "verify",
        "workspace": request["workspace"],
        "taskGoal": compact_text(event.get("taskGoal") or event.get("goal") or "verify accepted binding refresh"),
    }
    prior_verify_calls = int(attempt.get("verifyCallCount") or 0)
    remaining_verify_calls = max(0, max_verify_calls_per_key - prior_verify_calls)
    calls_this_run = min(max(1, verify_attempts), remaining_verify_calls)
    if calls_this_run == 0:
        result = scoped_block("verify_retry_exhausted_no_poll", "wait_for_new_scan_or_formal_receipt", scope)
        result.update(
            {
                "refreshKey": key,
                "refresh": compact_runtime_receipt(refresh_response or {}),
                "governorState": governor_result["state"],
                "driverState": state,
            }
        )
        return result
    for index in range(calls_this_run):
        try:
            verify_response = runtime_invoke(verify_request)
            verify_valid, verify_shape_reason, _ = context_governor.inspect_control_structure(
                verify_response, max_bytes=context_governor.MAX_TAKEOVER_SERIALIZED_BYTES
            )
            if not verify_valid:
                raise ValueError(verify_shape_reason)
            verified, verify_reason = valid_verify_response(verify_response, request, checkpoint_id)
        except Exception as exc:
            verified, verify_reason = False, compact_text(exc)
        if verified:
            attempt["status"] = "verified"
            attempt["verifyCallCount"] = prior_verify_calls + index + 1
            attempt["verifySequenceCompleted"] = True
            attempt["verifyReceipt"] = compact_runtime_receipt(verify_response)
            commit_verified_generation(
                governor_result["state"], event, request, attempt, namespace
            )
            if persist_governor_state:
                try:
                    persist_governor_state(governor_result["state"])
                except Exception as exc:
                    attempt["status"] = "governor_commit_failed"
                    attempt["governorCommitFailure"] = compact_text(exc)
                    if persist_driver_state:
                        persist_driver_state(state)
                    result = scoped_block(
                        "refresh_state_reconciliation_required",
                        "reconcile_verified_refresh_into_governor_state_without_runtime_call",
                        scope,
                        detail=str(exc),
                    )
                    result.update(
                        {
                            "refreshKey": key,
                            "governorState": governor_result["state"],
                            "driverState": state,
                        }
                    )
                    return result
            if persist_driver_state:
                persist_driver_state(state)
            digest = verified_commit_digest(
                governor_result["state"], request, attempt, namespace
            )
            if digest is None:
                result = scoped_block(
                    "refresh_state_reconciliation_required",
                    "reconcile_verified_refresh_into_governor_state_without_runtime_call",
                    scope,
                )
                result.update(
                    {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
                )
                return result
            attempt["coherenceDigest"] = digest
            if persist_driver_state:
                persist_driver_state(state)
            if persist_durability_confirmation:
                persist_durability_confirmation(
                    confirmation_state(durability_confirmations, key, digest)
                )
            elif durability_confirmations is not None:
                result = scoped_block(
                    "refresh_durability_reconciliation_required",
                    "persist_exact_durability_confirmation_without_runtime_call",
                    scope,
                )
                result.update(
                    {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
                )
                return result
            if durability_required:
                result = scoped_block(
                    "refresh_durability_confirmed_retry_required",
                    "retry_once_after_exact_durable_commit_confirmation",
                    scope,
                )
                result.update(
                    {"refreshKey": key, "governorState": governor_result["state"], "driverState": state}
                )
                return result
            previous_lane_state = lane_recovery.get(recovery_scope, {})
            lane_recovery[recovery_scope] = {
                "status": "resumed",
                "refreshKey": key,
                "contextGenerationId": attempt.get("contextGenerationId"),
            }
            result = result_base(scope) | {
                "ok": True,
                "decision": "allow",
                "reason": "refresh_binding_verified",
                "allowProviderCalls": True,
                "allowToolCalls": True,
                "allowProjectToolCalls": True,
                "allowRecoveryControlTools": False,
                "recoveryControlToolAllowlist": [],
                "allowOldThreadExecution": True,
                "laneStatus": "resumed",
                "lifecycleState": "active",
                "autoRecoveryEligible": False,
                "resumeProgramGoal": previous_lane_state.get("status") == "lane_paused_recoverable"
                or context_governor.as_bool(event.get("historicalProgramGoalBlocked")) is True,
                "clearHistoricalGoalBlocked": previous_lane_state.get("status") == "lane_paused_recoverable"
                or context_governor.as_bool(event.get("historicalProgramGoalBlocked")) is True,
                "nextAction": "resume_related_lane_after_verified_binding",
                "refreshKey": key,
                "refresh": compact_runtime_receipt(refresh_response or {}),
                "verify": compact_runtime_receipt(verify_response),
                "governorState": governor_result["state"],
                "driverState": state,
            }
            return result
        if index + 1 < calls_this_run:
            sleeper(max(0.0, verify_delay_seconds))

    attempt.update(
        {
            "status": "refreshed",
            "verifyCallCount": prior_verify_calls + calls_this_run,
            "verifyFailure": verify_reason,
            "verifySequenceCompleted": True,
            "verifyReceipt": compact_runtime_receipt(verify_response),
        }
    )
    lane_recovery[recovery_scope] = {
        "status": "lane_paused_recoverable",
        "refreshKey": key,
        "nextAction": "wait_for_new_scan_or_formal_receipt",
    }
    if persist_driver_state:
        persist_driver_state(state)
    result = scoped_block("post_refresh_verify_not_ready", "wait_for_new_scan_or_formal_receipt", scope, detail=verify_reason)
    result.update(
        {
            "refreshKey": key,
            "refresh": compact_runtime_receipt(refresh_response or {}),
            "verify": compact_runtime_receipt(verify_response),
            "governorState": governor_result["state"],
            "driverState": state,
        }
    )
    return result


def read_json(path: Optional[Path]) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


def read_confirmed_state_json(path: Path) -> dict[str, Any]:
    try:
        value = atomic_state.read_confirmed_json(path)
    except (atomic_state.StateDurabilityError, atomic_state.StatePermissionError) as exc:
        raise SystemExit(f"durable_state_unavailable:{exc}") from exc
    valid, reason, serialized_bytes = context_governor.inspect_control_structure(
        value, max_bytes=context_governor.MAX_STATE_SERIALIZED_BYTES
    )
    if not valid:
        raise SystemExit(f"durable_state_unavailable:state_{reason}:{serialized_bytes}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_state.atomic_write_json(path, value)


def reconcile_marked_state_files(paths: list[Path]) -> dict[str, Any] | None:
    marked = [
        path
        for path in paths
        if atomic_state.has_uncertainty(path) or atomic_state.has_confirmation(path)
    ]
    if not marked:
        return None
    reconciled = []
    had_pending = any(atomic_state.has_uncertainty(path) for path in marked)
    try:
        for path in marked:
            if atomic_state.has_uncertainty(path):
                pending = atomic_state.reconcile_atomic_json(path)
            else:
                pending = {"status": "pending_not_present"}
            confirmed = atomic_state.confirm_atomic_json(path)
            reconciled.append({"path": str(path), "pending": pending, "confirmed": confirmed})
    except atomic_state.StateDurabilityError as exc:
        result = scoped_block(
            "filesystem_state_reconciliation_required",
            "retry_local_filesystem_reconciliation_without_runtime_call",
            "refresh_state",
            detail=str(exc),
        )
        result["reconciled"] = reconciled
        return result
    if not had_pending:
        return None
    result = scoped_block(
        "filesystem_state_reconciled_retry_required",
        "retry_once_after_confirmed_filesystem_reconciliation",
        "refresh_state",
    )
    result["reconciled"] = reconciled
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run direct accepted binding refresh and bounded verification.")
    parser.add_argument("event", type=Path, help="Compact accepted exact-scan event JSON")
    parser.add_argument("--governor-state", type=Path, required=True)
    parser.add_argument("--driver-state", type=Path, required=True)
    parser.add_argument("--durability-state", type=Path)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--verify-attempts", type=int, default=DEFAULT_VERIFY_ATTEMPTS)
    parser.add_argument("--max-verify-calls-per-key", type=int, default=DEFAULT_MAX_VERIFY_CALLS_PER_KEY)
    parser.add_argument("--verify-delay-seconds", type=float, default=DEFAULT_VERIFY_DELAY_SECONDS)
    args = parser.parse_args()

    durability_path = args.durability_state or args.driver_state.with_name(
        f"{args.driver_state.name}.durability.json"
    )
    filesystem_reconciliation = reconcile_marked_state_files(
        [args.governor_state, args.driver_state, durability_path]
    )
    if filesystem_reconciliation is not None:
        print(json.dumps(filesystem_reconciliation, indent=2, sort_keys=True))
        return 2

    event = read_json(args.event)
    try:
        governor_state = read_confirmed_state_json(args.governor_state)
        driver_state = read_confirmed_state_json(args.driver_state)
        durability_state = read_confirmed_state_json(durability_path)
    except SystemExit as exc:
        result = scoped_block(
            "durable_control_state_unavailable",
            "reconcile_or_reinitialize_exact_control_state_without_runtime_call",
            "refresh_state",
            detail=str(exc),
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    governor_state_sha256 = atomic_state.state_sha256(governor_state)
    driver_state_sha256 = atomic_state.state_sha256(driver_state)
    persisted_driver_sha256 = driver_state_sha256
    persisted_governor_sha256 = governor_state_sha256
    persisted_durability_sha256 = atomic_state.state_sha256(durability_state)

    def persist_driver_state(value: dict[str, Any]) -> None:
        nonlocal persisted_driver_sha256
        persisted_driver_sha256 = atomic_state.atomic_write_json(
            args.driver_state, value, expected_sha256=persisted_driver_sha256
        )

    def persist_governor_state(value: dict[str, Any]) -> None:
        nonlocal persisted_governor_sha256
        persisted_governor_sha256 = atomic_state.atomic_write_json(
            args.governor_state, value, expected_sha256=persisted_governor_sha256
        )
    def persist_durability_confirmation(value: dict[str, Any]) -> None:
        nonlocal persisted_durability_sha256
        persisted_durability_sha256 = atomic_state.atomic_write_json(
            durability_path, value, expected_sha256=persisted_durability_sha256
        )
    runtime = lambda request: invoke_app_runtime(request, args.runtime)
    result = run(
        event,
        governor_state,
        driver_state,
        runtime,
        verify_attempts=args.verify_attempts,
        max_verify_calls_per_key=args.max_verify_calls_per_key,
        verify_delay_seconds=args.verify_delay_seconds,
        persist_driver_state=persist_driver_state,
        persist_governor_state=persist_governor_state,
        durability_confirmations=durability_state,
        persist_durability_confirmation=persist_durability_confirmation,
        runtime_outcome_query=runtime,
    )
    try:
        if atomic_state.state_sha256(result["governorState"]) != persisted_governor_sha256:
            persist_governor_state(result["governorState"])
        if atomic_state.state_sha256(result["driverState"]) != persisted_driver_sha256:
            persist_driver_state(result["driverState"])
    except (atomic_state.StateConflictError, atomic_state.StateDurabilityError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({k: v for k, v in result.items() if k not in {"governorState", "driverState"}}, indent=2, sort_keys=True))
    return 0 if result["decision"] == "allow" else 2


if __name__ == "__main__":
    raise SystemExit(main())
