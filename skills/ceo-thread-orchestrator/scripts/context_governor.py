#!/usr/bin/env python3
"""CEO Flow context pressure and memory-freeze governor.

This helper evaluates structured metrics only. It must not read raw chats, raw
sessions, full logs, SQLite databases, credentials, API keys, image bodies, or
base64 payloads. Use it to make CEO Flow freeze/takeover decisions idempotent
and auditable from compact state.
"""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

SCHEMA = "ceo_context_governor_v1"
DEFAULT_INPUT_TOKEN_LIMIT = 120_000
DEFAULT_CONTEXT_TOKEN_LIMIT = 120_000
DEFAULT_CUMULATIVE_INPUT_LIMIT = 10_000_000
DEFAULT_CONTEXT_BYTES_LIMIT = 50 * 1024 * 1024
DEFAULT_TAKEOVER_TOKEN_LIMIT = 3_000

FAIL_CLOSED_MEMORY_MODES = {"fallback_stale"}
REQUIRED_TAKEOVER_MEMORY_MODE = "app_owned_memory_core"
REQUIRED_AUTHORITY_VERIFICATION = "app_owned_verified"
NON_MEMORY_EVENT_TYPES = {"heartbeat", "tool_result", "commentary", "wake_check", "status_poll"}
DISPATCH_EVENT_TYPES = {"task_start", "resume", "direction_switch", "pre_dispatch", "dispatch"}
CRITICAL_BASIS_KEYS = {
    "head",
    "scanHash",
    "projectIdentitySha256",
    "postimageSha256",
    "verifiedMemoryStateHash",
}
REQUIRED_TAKEOVER_BASIS_KEYS = {"head", "scanHash", "verifiedMemoryStateHash"}
FAIL_CLOSED_STATUSES = {
    "project_unresolved",
    "project_scope_mismatch",
    "project_identity_mismatch",
    "schema_or_cursor_failure",
    "invalid_cursor",
    "missing_current_project_brain",
}
FORBIDDEN_KEYS = {
    "rawChat",
    "raw_chat",
    "rawSession",
    "raw_session",
    "sessionBody",
    "fullLog",
    "full_log",
    "completeLog",
    "sqlite",
    "databasePath",
    "apiKey",
    "api_key",
    "credential",
    "credentials",
    "secret",
    "imageBase64",
    "base64",
}
FORBIDDEN_VALUE_RE = re.compile(
    r"(data:image/[a-z0-9.+-]+|;\s*base64\s*,|[A-Za-z0-9+/]{240,}={0,2})",
    re.IGNORECASE,
)
ALLOWED_TAKEOVER_TOP_LEVEL_KEYS = {
    "HEAD",
    "authorityCheckpointSha256",
    "authorityVerification",
    "baselineHead",
    "checkpointSha256",
    "coldBodyIncluded",
    "containsColdBody",
    "containsFullLog",
    "containsImagePayload",
    "containsRawChat",
    "contextGenerationId",
    "continuity",
    "current",
    "currentScanSha256",
    "durationMs",
    "exactScan",
    "graph",
    "head",
    "identity",
    "items",
    "lane",
    "laneId",
    "memory",
    "memoryLayers",
    "memoryMode",
    "module",
    "moduleId",
    "ok",
    "operation",
    "partial",
    "postimage",
    "postimageSha256",
    "projectId",
    "projectIdentity",
    "projectIdentitySha256",
    "projectPath",
    "provider",
    "queryType",
    "recoveryReady",
    "retrieval",
    "returnedCount",
    "scan",
    "scanBinding",
    "scanHash",
    "scanSha256",
    "schema",
    "sourceRefs",
    "sourceThreadId",
    "source_refs",
    "takeover",
    "threadId",
    "tokenBudget",
    "tokenEstimate",
    "verifiedMemoryStateHash",
    "version",
    "warnings",
    "workspace",
}
FORBIDDEN_TAKEOVER_CONTENT_KEYS = {
    "apikey",
    "base64",
    "body",
    "chat",
    "cold",
    "coldbody",
    "coldrawbody",
    "completelog",
    "content",
    "credential",
    "credentials",
    "database",
    "databasebody",
    "databasepath",
    "fulllog",
    "historybody",
    "imagebase64",
    "imagebody",
    "inputimage",
    "logs",
    "messages",
    "rawchat",
    "rawsession",
    "secret",
    "session",
    "sessionbody",
    "sqlite",
    "text",
    "transcript",
}
ALLOWED_TAKEOVER_LAYERS = {"hot", "warm", "continuity", "graph", "source_ref", "source_refs"}


def read_json(path: Optional[Path]) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def as_int(value: Any) -> int:
    if isinstance(value, bool) or value is None or value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def positive_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


def default_state(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "taskId": event.get("taskId"),
        "threadId": event.get("threadId"),
        "turnCount": 0,
        "cumulativeInputTokens": 0,
        "memoryAttempts": 0,
        "fallbackCount": 0,
        "duplicateInjectionCount": 0,
        "injectedGenerationIds": [],
        "lastGenerationBasis": {},
        "taskInjectionLedger": {},
        "freeze": {
            "triggered": False,
            "receiptEmitted": False,
            "reason": None,
            "oldThreadStopReason": None,
            "harvestDriverStatus": "active",
        },
    }


def find_forbidden_payload(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}"
            if key in FORBIDDEN_KEYS:
                findings.append(f"forbidden key {key_path}")
            findings.extend(find_forbidden_payload(item, key_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(find_forbidden_payload(item, f"{path}[{index}]"))
    elif isinstance(value, str) and FORBIDDEN_VALUE_RE.search(value):
        findings.append(f"forbidden payload marker at {path}")
    return findings


def normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def find_forbidden_takeover_content(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        layer = str(value.get("layer") or value.get("memoryLayer") or "").strip().lower()
        if layer and layer not in ALLOWED_TAKEOVER_LAYERS:
            findings.append(f"forbidden takeover layer {path}.layer={layer}")
        for key, item in value.items():
            key_path = f"{path}.{key}"
            if normalized_key(key) in FORBIDDEN_TAKEOVER_CONTENT_KEYS and item not in (None, False, "", [], {}):
                findings.append(f"forbidden takeover content key {key_path}")
            findings.extend(find_forbidden_takeover_content(item, key_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(find_forbidden_takeover_content(item, f"{path}[{index}]"))
    return findings


def normalize_memory(memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "memoryMode": str(memory.get("memoryMode") or memory.get("mode") or ""),
        "status": str(memory.get("status") or memory.get("memoryCoreStatus") or ""),
        "current": as_bool(memory.get("current")),
        "recoveryReady": as_bool(memory.get("recoveryReady")),
        "projectIdentityResult": str(memory.get("projectIdentityResult") or ""),
        "authorityVerification": str(memory.get("authorityVerification") or ""),
    }


def memory_fail_reason(memory: dict[str, Any]) -> str | None:
    normalized = normalize_memory(memory)
    if normalized["memoryMode"] in FAIL_CLOSED_MEMORY_MODES:
        return "fallback_stale"
    if normalized["status"] in FAIL_CLOSED_STATUSES:
        return normalized["status"]
    if normalized["projectIdentityResult"] in FAIL_CLOSED_STATUSES:
        return normalized["projectIdentityResult"]
    if normalized["current"] is False:
        return "current_false"
    if normalized["recoveryReady"] is False:
        return "recovery_not_ready"
    if normalized["authorityVerification"] == "unavailable" and memory.get("authorityRequired", True):
        return "authority_unavailable_for_claim"
    return None


def task_key(event: dict[str, Any], state: dict[str, Any]) -> str:
    value = event.get("taskId") or state.get("taskId") or event.get("threadId") or state.get("threadId") or "default"
    return str(value)


def task_ledger(state: dict[str, Any], key: str) -> dict[str, Any]:
    ledgers = state.setdefault("taskInjectionLedger", {})
    if not isinstance(ledgers, dict):
        ledgers = {}
        state["taskInjectionLedger"] = ledgers
    ledger = ledgers.setdefault(
        key,
        {
            "injectedGenerationIds": [],
            "lastGenerationBasis": {},
            "invalidatedGenerationIds": [],
        },
    )
    if not isinstance(ledger, dict):
        ledger = {"injectedGenerationIds": [], "lastGenerationBasis": {}, "invalidatedGenerationIds": []}
        ledgers[key] = ledger
    if not ledger.get("injectedGenerationIds") and state.get("injectedGenerationIds"):
        ledger["injectedGenerationIds"] = list(state.get("injectedGenerationIds") or [])
    if not ledger.get("lastGenerationBasis") and state.get("lastGenerationBasis"):
        ledger["lastGenerationBasis"] = dict(state.get("lastGenerationBasis") or {})
    ledger.setdefault("invalidatedGenerationIds", [])
    return ledger


def pressure_reasons(event: dict[str, Any], state: dict[str, Any], limits: dict[str, int]) -> list[str]:
    reasons: list[str] = []
    input_tokens = as_int(event.get("inputTokens"))
    context_tokens = as_int(event.get("estimatedContextTokens") or event.get("contextTokens"))
    context_bytes = as_int(event.get("estimatedContextBytes") or event.get("sessionBytes"))
    cumulative = as_int(state.get("cumulativeInputTokens"))

    if input_tokens >= limits["inputTokenLimit"]:
        reasons.append("input_token_limit")
    if context_tokens >= limits["contextTokenLimit"]:
        reasons.append("context_token_limit")
    if context_bytes >= limits["contextBytesLimit"]:
        reasons.append("context_bytes_limit")
    if cumulative >= limits["cumulativeInputLimit"]:
        reasons.append("cumulative_input_limit")
    return reasons


def get_dotted(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def first_present(data: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        value = get_dotted(data, path)
        if value is not None:
            return value
    return None


def generation_basis(data: dict[str, Any]) -> dict[str, str]:
    paths = {
        "head": ("head", "HEAD", "baselineHead", "projectIdentity.baselineHead", "scanBinding.baselineHead"),
        "scanHash": (
            "scanHash",
            "scanSha256",
            "currentScanSha256",
            "scanBinding.currentScanSha256",
            "scan.currentScanSha256",
            "exactScan.currentScanSha256",
        ),
        "projectIdentitySha256": (
            "projectIdentitySha256",
            "projectIdentity.projectIdentitySha256",
            "identity.projectIdentitySha256",
        ),
        "postimageSha256": ("postimageSha256", "postimage.sha256", "postimage.hash"),
        "verifiedMemoryStateHash": (
            "verifiedMemoryStateHash",
            "checkpointSha256",
            "authorityCheckpointSha256",
            "continuity.manifestFingerprint",
            "scanBinding.authorizedCheckpointId",
        ),
    }
    basis: dict[str, str] = {}
    for key, candidates in paths.items():
        value = first_present(data, *candidates)
        if value not in (None, ""):
            basis[key] = str(value)
    return basis


def basis_changed(previous: dict[str, str], current: dict[str, str]) -> list[str]:
    changed: list[str] = []
    for key in CRITICAL_BASIS_KEYS:
        if previous.get(key) and current.get(key) and previous.get(key) != current.get(key):
            changed.append(key)
    return sorted(changed)


def is_non_memory_event(event: dict[str, Any]) -> bool:
    event_type = str(event.get("eventType") or event.get("lifecycleEvent") or event.get("type") or "")
    return event_type in NON_MEMORY_EVENT_TYPES


def requires_stable_basis(event: dict[str, Any]) -> bool:
    event_type = str(event.get("eventType") or event.get("lifecycleEvent") or event.get("type") or "")
    return bool(event.get("dispatchRequested") or event.get("providerCallRequested") or event_type in DISPATCH_EVENT_TYPES)


def accepted_receipt(event: dict[str, Any]) -> Any:
    return event.get("acceptedEvidenceReceipt") or event.get("acceptedReceipt") or event.get("qaAcceptReceipt")


def accepted_receipt_id(event: dict[str, Any]) -> str | None:
    receipt = accepted_receipt(event)
    if isinstance(receipt, str):
        return receipt.strip() or None
    if isinstance(receipt, dict):
        value = receipt.get("receiptId") or receipt.get("id")
        return str(value).strip() if value not in (None, "") else None
    return None


def has_formal_acceptance(event: dict[str, Any]) -> bool:
    receipt = accepted_receipt(event)
    if not accepted_receipt_id(event):
        return False
    if isinstance(receipt, dict):
        decision = str(receipt.get("decision") or "").strip().lower()
        return decision in {"accept", "accepted"}
    return True


def exact_scan(event: dict[str, Any]) -> dict[str, Any] | None:
    scan = event.get("exactScan") or event.get("scan")
    return scan if isinstance(scan, dict) else None


def scan_changed(event: dict[str, Any], scan: dict[str, Any] | None) -> bool | None:
    source = scan or event
    explicit = as_bool(first_present(source, "changed", "scanChanged", "canonicalSourcesChanged"))
    if explicit is not None:
        return explicit
    previous = first_present(source, "previousScanSha256", "previousScanHash")
    current = first_present(source, "currentScanSha256", "currentScanHash", "scanHash")
    if previous and current:
        return str(previous) != str(current)
    return None


def refresh_binding_request(event: dict[str, Any], scan: dict[str, Any] | None, previous_basis: dict[str, str]) -> dict[str, Any]:
    source = scan or {}
    memory = event.get("memory") if isinstance(event.get("memory"), dict) else {}
    packet = event.get("takeoverPacket") if isinstance(event.get("takeoverPacket"), dict) else {}
    evidence_source = event.get("acceptedEvidence") if isinstance(event.get("acceptedEvidence"), dict) else {}
    if not evidence_source and isinstance(event.get("evidence"), dict):
        evidence_source = event["evidence"]
    changed_paths = event.get("changedPaths") or source.get("changedPaths") or []
    source_refs = evidence_source.get("sourceRefs") or source.get("sourceRefs") or event.get("sourceRefs") or []
    lane = event.get("lane") or event.get("laneId") or event.get("module") or event.get("moduleId")
    lane = lane or packet.get("lane") or packet.get("laneId") or packet.get("module") or packet.get("moduleId") or None
    return {
        "operation": "refresh_binding",
        "workspace": event.get("workspace") or packet.get("workspace") or None,
        "execute": True,
        "expectedProjectIdentitySha256": first_present(event, "projectIdentitySha256", "projectIdentity.projectIdentitySha256")
        or first_present(memory, "projectIdentity.projectIdentitySha256")
        or first_present(packet, "projectIdentitySha256", "projectIdentity.projectIdentitySha256")
        or previous_basis.get("projectIdentitySha256")
        or None,
        "expectedScanSha256": first_present(source, "currentScanSha256", "currentScanHash", "scanSha256")
        or first_present(memory, "scanBinding.currentScanSha256")
        or first_present(packet, "scanHash", "scanSha256", "scanBinding.currentScanSha256")
        or None,
        "previousCheckpointId": first_present(source, "previousCheckpointId")
        or first_present(memory, "scanBinding.authorizedCheckpointId")
        or first_present(packet, "previousCheckpointId")
        or first_present(packet, "checkpointId")
        or previous_basis.get("verifiedMemoryStateHash")
        or None,
        "acceptedEvidenceReceipt": accepted_receipt_id(event),
        "acceptedChangedPaths": changed_paths,
        "lane": lane,
        "evidence": {
            "decision": "accept",
            "phase": evidence_source.get("phase") or event.get("phase") or "accepted change",
            "summary": evidence_source.get("summary") or event.get("acceptedSummary") or "Accepted evidence advanced the exact workspace binding.",
            "sourceRefs": source_refs,
        },
    }


def source_refs_out_of_scope(packet: dict[str, Any], event: dict[str, Any]) -> bool:
    expected_project = first_present(event, "projectIdentitySha256", "projectIdentity.projectIdentitySha256")
    packet_project = first_present(packet, "projectIdentitySha256", "projectIdentity.projectIdentitySha256")
    if expected_project and packet_project and str(expected_project) != str(packet_project):
        return True

    expected_lane = str(event.get("lane") or event.get("laneId") or "")
    expected_module = str(event.get("module") or event.get("moduleId") or "")
    packet_lane = str(packet.get("lane") or packet.get("laneId") or "")
    packet_module = str(packet.get("module") or packet.get("moduleId") or "")
    if expected_lane and packet_lane and expected_lane != packet_lane:
        return True
    if expected_module and packet_module and expected_module != packet_module:
        return True

    workspace = str(event.get("workspace") or packet.get("workspace") or "")
    source_refs = packet.get("sourceRefs") or packet.get("source_refs") or []
    if source_refs is None:
        source_refs = []
    if not isinstance(source_refs, list):
        return True
    root = Path(workspace).resolve() if workspace else None
    for ref in source_refs:
        if not isinstance(ref, dict):
            return True
        ref_lane = str(ref.get("lane") or ref.get("laneId") or "")
        ref_module = str(ref.get("module") or ref.get("moduleId") or "")
        if expected_lane and ref_lane and ref_lane != expected_lane:
            return True
        if expected_module and ref_module and ref_module != expected_module:
            return True
        ref_path = ref.get("path") or ref.get("file") or ref.get("sourcePath")
        if not ref_path:
            continue
        text_path = str(ref_path)
        if any(marker in text_path.lower() for marker in ("session", "sqlite", "base64", "data:image")):
            return True
        candidate = Path(text_path)
        if candidate.is_absolute() and root is not None:
            try:
                candidate.resolve().relative_to(root)
            except ValueError:
                return True
    return False


def validate_takeover_packet(
    packet: dict[str, Any], event: dict[str, Any], ledger: dict[str, Any], token_limit: int
) -> tuple[str, str]:
    token_estimate = positive_int(packet.get("tokenEstimate"))
    if token_estimate is None:
        return "block", "invalid_takeover_token_estimate"
    if token_estimate > token_limit:
        return "block", "takeover_packet_over_budget"
    if packet.get("containsRawChat") or packet.get("containsImagePayload") or packet.get("containsFullLog"):
        return "block", "forbidden_takeover_payload"
    if packet.get("containsColdBody") or packet.get("coldBodyIncluded"):
        return "block", "cold_body_forbidden"

    unknown_keys = sorted(str(key) for key in packet if key not in ALLOWED_TAKEOVER_TOP_LEVEL_KEYS)
    if unknown_keys:
        return "block", "takeover_packet_schema_invalid"
    if find_forbidden_takeover_content(packet):
        return "block", "forbidden_takeover_payload"
    if source_refs_out_of_scope(packet, event):
        return "block", "source_refs_out_of_scope"

    memory_mode = str(first_present(packet, "memoryMode", "memory.memoryMode") or "")
    if memory_mode == "fallback_stale":
        return "block", "fallback_stale"
    if memory_mode != REQUIRED_TAKEOVER_MEMORY_MODE:
        return "block", "memory_mode_not_app_owned"

    authority = str(first_present(packet, "authorityVerification", "memory.authorityVerification") or "")
    if authority == "unavailable":
        return "block", "authority_unavailable_for_claim"
    if authority != REQUIRED_AUTHORITY_VERIFICATION:
        return "block", "authority_not_app_owned_verified"

    current = as_bool(first_present(packet, "current", "memory.current"))
    if current is not True:
        return "block", "current_not_true"

    recovery_ready = as_bool(first_present(packet, "recoveryReady", "memory.recoveryReady"))
    if recovery_ready is not True:
        return "block", "recovery_not_ready"

    returned_count = as_int(
        first_present(packet, "returnedCount", "retrieval.returnedCount", "takeover.returnedCount", "memory.returnedCount")
    )
    if returned_count <= 0:
        return "block", "retrieval_empty"

    should_inject = as_bool(first_present(packet, "takeover.shouldInject", "shouldInject"))
    if should_inject is not True:
        return "block", "should_inject_not_true"

    generation_id = str(packet.get("contextGenerationId") or "")
    if not generation_id:
        return "block", "missing_context_generation_id"

    current_basis = generation_basis(packet)
    if REQUIRED_TAKEOVER_BASIS_KEYS - current_basis.keys():
        return "block", "missing_generation_basis"

    injected = set(str(item) for item in ledger.get("injectedGenerationIds", []))
    if generation_id in injected:
        if basis_changed(ledger.get("lastGenerationBasis", {}), current_basis):
            return "block", "rotate_generation_required"
        return "block", "duplicate_context_generation"
    if injected and not basis_changed(ledger.get("lastGenerationBasis", {}), current_basis):
        return "block", "generation_basis_unchanged"
    return "allow", "inject_takeover_packet"


def block_result(
    state: dict[str, Any],
    reason: str,
    metrics: dict[str, Any],
    *,
    next_action: str,
    scope: str = "project_context",
    allow_old_thread_execution: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "schema": SCHEMA,
        "ok": True,
        "decision": "block",
        "reason": reason,
        "allowOldThreadExecution": allow_old_thread_execution,
        "allowToolCalls": False,
        "allowProviderCalls": False,
        "unbindHarvestDriver": False,
        "nextAction": next_action,
        "blocker": {
            "code": reason,
            "scope": scope,
            "message": "Fail closed: project memory binding must be verified before dispatch or provider calls.",
            "nextAction": next_action,
        },
        "messagePolicy": {
            "sendCodexDelegation": False,
            "target": "none",
            "compactOnly": True,
            "forbidden": ["nested_codex_delegation", "raw_chat", "full_runtime_json", "complete_history"],
        },
        "metrics": metrics,
        "state": state,
    }
    if extra:
        result.update(extra)
    return result


def freeze_result(state: dict[str, Any], reason: str, metrics: dict[str, Any]) -> dict[str, Any]:
    receipt_already_emitted = bool(state.get("freeze", {}).get("receiptEmitted"))
    next_action = "stop_old_task_no_repeat" if receipt_already_emitted else "emit_freeze_receipt_and_unbind_harvest_driver"
    metrics["oldThreadStopReason"] = reason

    state.setdefault("freeze", {})
    state["freeze"].update(
        {
            "triggered": True,
            "receiptEmitted": True,
            "reason": reason,
            "oldThreadStopReason": reason,
            "harvestDriverStatus": "unbind_required",
        }
    )

    return {
        "schema": SCHEMA,
        "ok": True,
        "decision": "freeze",
        "reason": reason,
        "emitFreezeReceipt": not receipt_already_emitted,
        "allowOldThreadExecution": False,
        "allowToolCalls": False,
        "allowProviderCalls": False,
        "unbindHarvestDriver": True,
        "nextAction": next_action,
        "blocker": {
            "code": reason,
            "scope": "project_context",
            "message": "Fail closed: old CEO task is no longer a safe execution surface.",
            "nextAction": next_action,
        },
        "prepareTakeover": {
            "required": True,
            "hook": "prepare_takeover",
            "maxTokens": DEFAULT_TAKEOVER_TOKEN_LIMIT,
            "allowedLayers": ["hot", "warm", "continuity", "graph", "sourceRefs"],
            "forbidden": ["raw_chat", "image_base64", "full_logs", "cold_body", "credentials", "sqlite"],
        },
        "metrics": metrics,
        "state": state,
    }


def evaluate(event: dict[str, Any], previous_state: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    state = deepcopy(previous_state) if previous_state else default_state(event)
    state.setdefault("schema", SCHEMA)
    state.setdefault("injectedGenerationIds", [])
    state.setdefault("taskInjectionLedger", {})
    state.setdefault("freeze", default_state(event)["freeze"])
    key = task_key(event, state)
    ledger = task_ledger(state, key)

    forbidden = find_forbidden_payload(event)
    input_tokens = as_int(event.get("inputTokens"))
    state["turnCount"] = as_int(state.get("turnCount")) + 1
    state["cumulativeInputTokens"] = as_int(state.get("cumulativeInputTokens")) + input_tokens

    packet = event.get("takeoverPacket")
    memory = event.get("memory")
    memory_reason = None
    if isinstance(memory, dict) and memory:
        state["memoryAttempts"] = as_int(state.get("memoryAttempts")) + 1
        memory_reason = memory_fail_reason(memory)
        if memory_reason:
            state["fallbackCount"] = as_int(state.get("fallbackCount")) + 1
    elif isinstance(packet, dict) and packet:
        state["memoryAttempts"] = as_int(state.get("memoryAttempts")) + 1

    fallback_rate = 0.0
    if as_int(state.get("memoryAttempts")):
        fallback_rate = as_int(state.get("fallbackCount")) / as_int(state.get("memoryAttempts"))

    metrics = {
        "turnCount": state["turnCount"],
        "inputTokens": input_tokens,
        "estimatedContextTokens": as_int(event.get("estimatedContextTokens") or event.get("contextTokens")),
        "estimatedContextBytes": as_int(event.get("estimatedContextBytes") or event.get("sessionBytes")),
        "cumulativeInputTokens": state["cumulativeInputTokens"],
        "fallbackRate": round(fallback_rate, 4),
        "takeoverGeneration": event.get("takeoverPacket", {}).get("contextGenerationId")
        if isinstance(event.get("takeoverPacket"), dict)
        else None,
        "duplicateInjectionCount": as_int(state.get("duplicateInjectionCount")),
        "oldThreadStopReason": state.get("freeze", {}).get("oldThreadStopReason"),
    }

    if state.get("freeze", {}).get("triggered"):
        frozen_reason = str(state.get("freeze", {}).get("reason") or "old_task_frozen")
        return freeze_result(state, frozen_reason, metrics)

    if forbidden:
        return freeze_result(state, "forbidden_context_payload", metrics | {"forbiddenFindings": forbidden})

    pressure = pressure_reasons(event, state, limits)
    if pressure:
        return freeze_result(state, pressure[0], metrics)

    if is_non_memory_event(event) and not isinstance(packet, dict) and not isinstance(memory, dict):
        metrics["memoryRuntimeAction"] = "skip"
        return {
            "schema": SCHEMA,
            "ok": True,
            "decision": "allow",
            "reason": "non_memory_event_no_retrieval",
            "allowOldThreadExecution": True,
            "allowToolCalls": True,
            "allowProviderCalls": True,
            "unbindHarvestDriver": False,
            "nextAction": "continue_without_memory_retrieval_or_injection",
            "metrics": metrics,
            "state": state,
        }

    scan = exact_scan(event)
    changed = scan_changed(event, scan)
    current_basis = generation_basis(event)
    previous_basis = ledger.get("lastGenerationBasis", {})
    changed_basis_keys = basis_changed(previous_basis, current_basis)
    if changed_basis_keys:
        injected = [str(item) for item in ledger.get("injectedGenerationIds", [])]
        ledger["invalidatedGenerationIds"] = sorted(set(ledger.get("invalidatedGenerationIds", []) + injected))
        state["invalidatedGenerationIds"] = ledger["invalidatedGenerationIds"]
        metrics["invalidatedGenerationCount"] = len(ledger["invalidatedGenerationIds"])

    binding_changed = changed is True or bool(changed_basis_keys)
    validation_failed = memory_reason is not None
    if validation_failed and changed is False:
        return freeze_result(state, "authority_defect", metrics | {"validationReason": memory_reason})
    if binding_changed and has_formal_acceptance(event):
        request = refresh_binding_request(event, scan, previous_basis)
        return block_result(
            state,
            "refresh_binding_required",
            metrics | {"changedBasisKeys": changed_basis_keys},
            next_action="run_direct_refresh_binding_driver",
            scope="lane_or_module",
            extra={"refreshBindingRequest": request},
        )
    if binding_changed:
        return freeze_result(
            state,
            "unaccepted_project_change",
            metrics | {"changedBasisKeys": changed_basis_keys, "scanChanged": changed},
        )
    if memory_reason:
        return block_result(
            state,
            memory_reason,
            metrics,
            next_action="run_readonly_exact_scan",
            scope="memory_runtime_verify",
        )

    if requires_stable_basis(event) and previous_basis and not current_basis and not isinstance(packet, dict):
        return block_result(
            state,
            "missing_generation_basis",
            metrics,
            next_action="run_verify_and_readonly_exact_scan_before_dispatch",
        )

    if event.get("takeoverRequired") and not isinstance(packet, dict):
        return block_result(
            state,
            "prepare_takeover_required",
            metrics,
            next_action="request_prepare_takeover_packet",
        ) | {"unbindHarvestDriver": True}

    if isinstance(packet, dict) and packet:
        verdict, reason = validate_takeover_packet(packet, event, ledger, limits["takeoverTokenLimit"])
        if verdict == "block":
            if reason == "duplicate_context_generation":
                state["duplicateInjectionCount"] = as_int(state.get("duplicateInjectionCount")) + 1
                metrics["duplicateInjectionCount"] = state["duplicateInjectionCount"]
            next_actions = {
                "duplicate_context_generation": "skip_duplicate_context_injection",
                "generation_basis_unchanged": "reuse_existing_generation_without_reinjection",
                "rotate_generation_required": "request_new_context_generation_after_refresh",
                "missing_generation_basis": "run_verify_and_readonly_exact_scan_before_dispatch",
            }
            next_action = next_actions.get(reason, "run_readonly_exact_scan")
            allow_old = reason == "duplicate_context_generation"
            return block_result(
                state,
                reason,
                metrics,
                next_action=next_action,
                scope="takeover_packet",
                allow_old_thread_execution=allow_old,
            )

        generation_id = str(packet["contextGenerationId"])
        packet_basis = generation_basis(packet)
        if ledger.get("injectedGenerationIds") and basis_changed(ledger.get("lastGenerationBasis", {}), packet_basis):
            prior_generations = [str(item) for item in ledger.get("injectedGenerationIds", [])]
            ledger["invalidatedGenerationIds"] = sorted(
                set(ledger.get("invalidatedGenerationIds", []) + prior_generations)
            )
            state["invalidatedGenerationIds"] = ledger["invalidatedGenerationIds"]
            metrics["invalidatedGenerationCount"] = len(ledger["invalidatedGenerationIds"])
        ledger["injectedGenerationIds"].append(generation_id)
        ledger["lastGenerationBasis"] = packet_basis
        state["injectedGenerationIds"] = ledger["injectedGenerationIds"]
        state["lastGenerationBasis"] = ledger["lastGenerationBasis"]
        metrics["takeoverGeneration"] = generation_id
        return {
            "schema": SCHEMA,
            "ok": True,
            "decision": "allow",
            "reason": reason,
            "allowOldThreadExecution": True,
            "allowToolCalls": True,
            "allowProviderCalls": True,
            "unbindHarvestDriver": False,
            "nextAction": "inject_takeover_packet_once",
            "contextInjectionMode": "replace_long_thread_context",
            "metrics": metrics,
            "state": state,
        }

    return {
        "schema": SCHEMA,
        "ok": True,
        "decision": "allow",
        "reason": "within_budget",
        "allowOldThreadExecution": True,
        "allowToolCalls": True,
        "allowProviderCalls": True,
        "unbindHarvestDriver": False,
        "nextAction": "continue_bounded_execution",
        "metrics": metrics,
        "state": state,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate CEO Flow context-governor state.")
    parser.add_argument("event", type=Path, help="Compact JSON event; raw chat/log/session payloads are forbidden")
    parser.add_argument("--state", type=Path, help="Optional compact JSON state file")
    parser.add_argument("--write-state", action="store_true", help="Persist updated compact state to --state")
    parser.add_argument("--input-token-limit", type=int, default=DEFAULT_INPUT_TOKEN_LIMIT)
    parser.add_argument("--context-token-limit", type=int, default=DEFAULT_CONTEXT_TOKEN_LIMIT)
    parser.add_argument("--cumulative-input-limit", type=int, default=DEFAULT_CUMULATIVE_INPUT_LIMIT)
    parser.add_argument("--context-bytes-limit", type=int, default=DEFAULT_CONTEXT_BYTES_LIMIT)
    parser.add_argument("--takeover-token-limit", type=int, default=DEFAULT_TAKEOVER_TOKEN_LIMIT)
    args = parser.parse_args()

    event = read_json(args.event)
    state = read_json(args.state) if args.state else {}
    limits = {
        "inputTokenLimit": args.input_token_limit,
        "contextTokenLimit": args.context_token_limit,
        "cumulativeInputLimit": args.cumulative_input_limit,
        "contextBytesLimit": args.context_bytes_limit,
        "takeoverTokenLimit": args.takeover_token_limit,
    }
    result = evaluate(event, state, limits)
    if args.write_state:
        if not args.state:
            raise SystemExit("--write-state requires --state")
        write_json(args.state, result["state"])
    print(json.dumps({k: v for k, v in result.items() if k != "state"}, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
