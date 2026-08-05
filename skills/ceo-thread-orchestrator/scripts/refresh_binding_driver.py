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

SCHEMA = "ceo_refresh_binding_driver_v1"
DEFAULT_RUNTIME = Path.home() / ".codex/skills/zhixia-local-docs/scripts/invoke-app-memory-runtime.cjs"
DEFAULT_VERIFY_ATTEMPTS = 3
DEFAULT_VERIFY_DELAY_SECONDS = 0.25
RuntimeInvoke = Callable[[dict[str, Any]], dict[str, Any]]
RECEIPT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,219}$")


def compact_text(value: Any, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[:limit]


def default_driver_state() -> dict[str, Any]:
    return {"schema": SCHEMA, "refreshAttempts": {}}


def receipt_id(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("receiptId") or value.get("id") or "").strip()
    return ""


def refresh_key(request: dict[str, Any]) -> str:
    identity = {
        "workspace": request.get("workspace"),
        "projectIdentity": request.get("expectedProjectIdentitySha256"),
        "scan": request.get("expectedScanSha256"),
        "receipt": receipt_id(request.get("acceptedEvidenceReceipt")),
    }
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
    paths = request.get("acceptedChangedPaths")
    if not isinstance(paths, list) or not paths:
        missing.append("acceptedChangedPaths")
    evidence = request.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("decision") != "accept":
        missing.append("evidence.decision=accept")
    elif not isinstance(evidence.get("sourceRefs"), list) or not evidence["sourceRefs"]:
        missing.append("evidence.sourceRefs")
    else:
        workspace = str(request.get("workspace") or "")
        referenced_paths = set()
        for ref in evidence["sourceRefs"]:
            if not isinstance(ref, dict) or not ref.get("path") or not ref.get("hash"):
                continue
            path = str(ref["path"])
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
        "acceptedPaths": sorted(response.get("acceptedChangedPaths") or [])
        == sorted(request.get("acceptedChangedPaths") or []),
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
    }


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
    }


def scoped_block(reason: str, next_action: str, scope: str, *, detail: str | None = None) -> dict[str, Any]:
    result = result_base(scope) | {
        "ok": True,
        "decision": "block",
        "reason": reason,
        "allowProviderCalls": False,
        "laneStatus": "paused_for_memory_binding",
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
    verify_delay_seconds: float = DEFAULT_VERIFY_DELAY_SECONDS,
    sleeper: Callable[[float], None] = time.sleep,
    persist_driver_state: Optional[Callable[[dict[str, Any]], None]] = None,
) -> dict[str, Any]:
    limits = limits or {
        "inputTokenLimit": context_governor.DEFAULT_INPUT_TOKEN_LIMIT,
        "contextTokenLimit": context_governor.DEFAULT_CONTEXT_TOKEN_LIMIT,
        "cumulativeInputLimit": context_governor.DEFAULT_CUMULATIVE_INPUT_LIMIT,
        "contextBytesLimit": context_governor.DEFAULT_CONTEXT_BYTES_LIMIT,
        "takeoverTokenLimit": context_governor.DEFAULT_TAKEOVER_TOKEN_LIMIT,
    }
    state = deepcopy(driver_state) if driver_state else default_driver_state()
    state.setdefault("schema", SCHEMA)
    attempts = state.setdefault("refreshAttempts", {})
    governor_result = context_governor.evaluate(event, governor_state, limits)
    scope = str(event.get("lane") or event.get("module") or event.get("laneId") or event.get("moduleId") or "lane_or_module")

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
    missing = validate_refresh_request(request)
    if missing:
        result = scoped_block("refresh_binding_request_invalid", "repair_compact_refresh_evidence", scope, detail=",".join(missing))
        result.update({"governorState": governor_result["state"], "driverState": state})
        return result

    key = refresh_key(request)
    attempt = attempts.get(key)
    refresh_response: dict[str, Any] | None = None
    if attempt:
        evidence_changed = (
            attempt.get("previousCheckpointId") != request.get("previousCheckpointId")
            or sorted(attempt.get("acceptedChangedPaths") or []) != sorted(request.get("acceptedChangedPaths") or [])
        )
        if evidence_changed:
            result = scoped_block("refresh_attempt_evidence_changed", "inspect_local_refresh_blocker", scope)
            result.update({"refreshKey": key, "governorState": governor_result["state"], "driverState": state})
            return result
        if attempt.get("status") not in {"refreshed", "verified"}:
            result = scoped_block("duplicate_refresh_blocked", "inspect_local_refresh_blocker", scope)
            result.update({"refreshKey": key, "governorState": governor_result["state"], "driverState": state})
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
            "workspace": request["workspace"],
            "scanSha256": request["expectedScanSha256"],
            "acceptedEvidenceReceipt": receipt_id(request["acceptedEvidenceReceipt"]),
            "previousCheckpointId": request["previousCheckpointId"],
            "acceptedChangedPaths": sorted(request["acceptedChangedPaths"]),
            "refreshCallCount": 1,
        }
        attempts[key] = attempt
        if persist_driver_state:
            persist_driver_state(state)
        try:
            refresh_response = runtime_invoke(request)
        except Exception as exc:  # Runtime boundary: return a compact lane-local blocker.
            attempt.update({"status": "failed", "failure": compact_text(exc)})
            if persist_driver_state:
                persist_driver_state(state)
            result = scoped_block("refresh_binding_failed", "inspect_local_refresh_blocker", scope, detail=str(exc))
            result.update({"refreshKey": key, "governorState": governor_result["state"], "driverState": state})
            return result
        valid, reason = valid_refresh_response(refresh_response, request)
        injected = set(str(value) for value in governor_result["state"].get("injectedGenerationIds", []))
        if valid and str(refresh_response.get("contextGenerationId")) in injected:
            valid, reason = False, "contextGenerationId_not_new"
        if not valid:
            attempt.update({"status": "failed", "failure": reason})
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
    for index in range(max(1, verify_attempts)):
        try:
            verify_response = runtime_invoke(verify_request)
            verified, verify_reason = valid_verify_response(verify_response, request, checkpoint_id)
        except Exception as exc:
            verified, verify_reason = False, compact_text(exc)
        if verified:
            attempt["status"] = "verified"
            attempt["verifyCallCount"] = index + 1
            if persist_driver_state:
                persist_driver_state(state)
            result = result_base(scope) | {
                "ok": True,
                "decision": "allow",
                "reason": "refresh_binding_verified",
                "allowProviderCalls": True,
                "laneStatus": "resumed",
                "nextAction": "resume_related_lane_after_verified_binding",
                "refreshKey": key,
                "refresh": compact_runtime_receipt(refresh_response or {}),
                "verify": compact_runtime_receipt(verify_response),
                "governorState": governor_result["state"],
                "driverState": state,
            }
            return result
        if index + 1 < max(1, verify_attempts):
            sleeper(max(0.0, verify_delay_seconds))

    attempt.update({"status": "refreshed", "verifyCallCount": max(1, verify_attempts), "verifyFailure": verify_reason})
    if persist_driver_state:
        persist_driver_state(state)
    result = scoped_block("post_refresh_verify_not_ready", "retry_local_verify_without_refresh", scope, detail=verify_reason)
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


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run direct accepted binding refresh and bounded verification.")
    parser.add_argument("event", type=Path, help="Compact accepted exact-scan event JSON")
    parser.add_argument("--governor-state", type=Path, required=True)
    parser.add_argument("--driver-state", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--verify-attempts", type=int, default=DEFAULT_VERIFY_ATTEMPTS)
    parser.add_argument("--verify-delay-seconds", type=float, default=DEFAULT_VERIFY_DELAY_SECONDS)
    args = parser.parse_args()

    event = read_json(args.event)
    governor_state = read_json(args.governor_state)
    driver_state = read_json(args.driver_state)
    runtime = lambda request: invoke_app_runtime(request, args.runtime)
    result = run(
        event,
        governor_state,
        driver_state,
        runtime,
        verify_attempts=args.verify_attempts,
        verify_delay_seconds=args.verify_delay_seconds,
        persist_driver_state=lambda value: write_json(args.driver_state, value),
    )
    write_json(args.governor_state, result["governorState"])
    write_json(args.driver_state, result["driverState"])
    print(json.dumps({k: v for k, v in result.items() if k not in {"governorState", "driverState"}}, indent=2, sort_keys=True))
    return 0 if result["decision"] == "allow" else 2


if __name__ == "__main__":
    raise SystemExit(main())
