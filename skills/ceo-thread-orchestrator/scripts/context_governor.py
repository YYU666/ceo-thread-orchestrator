#!/usr/bin/env python3
"""CEO Flow context pressure and memory-freeze governor.

This helper evaluates structured metrics only. It must not read raw chats, raw
sessions, full logs, SQLite databases, credentials, API keys, image bodies, or
base64 payloads. Use it to make CEO Flow freeze/takeover decisions idempotent
and auditable from compact state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atomic_state

SCHEMA = "ceo_context_governor_v1"
DEFAULT_INPUT_TOKEN_LIMIT = 120_000
DEFAULT_CONTEXT_TOKEN_LIMIT = 120_000
DEFAULT_CUMULATIVE_INPUT_LIMIT = 10_000_000
DEFAULT_CONTEXT_BYTES_LIMIT = 50 * 1024 * 1024
DEFAULT_TAKEOVER_TOKEN_LIMIT = 10_000
DEFAULT_TAKEOVER_PREFERRED_TOKENS = 2_200
DEFAULT_PREFLIGHT_FREEZE_RATIO = 0.90
DEFAULT_CLEAN_TAKEOVER_RETAINED_CONTEXT_LIMIT = 30_000
DEFAULT_CONTEXT_COMPACTION_ROTATION_LIMIT = 2
HOST_TELEMETRY_SCHEMA = "ceo_host_context_telemetry_v1"
HOST_TELEMETRY_SOURCE = "codex_host"
HOST_TELEMETRY_SCOPE = "current_post_compaction_context"
HOST_COMPACTION_SOURCE = "codex_host_turn_summaries"
HOST_TELEMETRY_MAX_AGE = timedelta(minutes=5)
MAX_EVENT_SERIALIZED_BYTES = 1024 * 1024
MAX_STATE_SERIALIZED_BYTES = 8 * 1024 * 1024
MAX_TAKEOVER_SERIALIZED_BYTES = 256 * 1024
MAX_STRUCTURE_DEPTH = 64
MAX_STRUCTURE_NODES = 50_000
MAX_CONTAINER_WIDTH = 4_096
MAX_STRING_BYTES = 1024 * 1024
MAX_SOURCE_REFS = 256
GLOBAL_BLOCK_RECEIPT_MAX_AGE = timedelta(days=7)
GLOBAL_BLOCK_RECEIPT_SCOPE = "program_goal"
RFC3339_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{2}:\d{2}:\d{2})"
    r"(?P<fraction>\.\d{1,6})?(?P<zone>Z|[+-]\d{2}:\d{2})$"
)


class _DriverCapability:
    def __deepcopy__(self, memo: dict[int, Any]) -> "_DriverCapability":
        return self


APP_OWNED_BOOTSTRAP_DRIVER_CAPABILITY = _DriverCapability()
GLOBAL_BLOCK_AUDIT_CAPABILITY = _DriverCapability()
GLOBAL_BLOCK_RECOVERY_CAPABILITY = _DriverCapability()
HOST_TELEMETRY_CAPABILITY = _DriverCapability()

FAIL_CLOSED_MEMORY_MODES = {"fallback_stale"}
REQUIRED_TAKEOVER_MEMORY_MODE = "app_owned_memory_core"
REQUIRED_AUTHORITY_VERIFICATION = "app_owned_verified"
NON_MEMORY_EVENT_TYPES = {"heartbeat", "tool_result", "commentary", "wake_check", "status_poll"}
DISPATCH_EVENT_TYPES = {"task_start", "resume", "direction_switch", "pre_dispatch", "dispatch"}
MODEL_REQUEST_PREFLIGHT_EVENT = "model_request_preflight"
ORDINARY_CODEX_LANE_DISPATCH_EVENT = "codex_lane_dispatch"
ORDINARY_CODEX_ROUTING_SURFACES = {"visible_thread", "subagent"}
USER_AUTHORIZATION_FLAGS = {
    "credentialAccessRequested",
    "destructiveActionRequested",
    "irreversibleActionRequested",
    "legalDecisionRequested",
    "productScopeChangeRequested",
    "securityBoundaryChangeRequested",
    "explicitRiskAcceptanceRequired",
    "hostApprovalRequired",
}
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
    "authorityReceiptId",
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
    "memoryCoreProjectId",
    "memoryMode",
    "module",
    "moduleId",
    "ok",
    "operation",
    "partial",
    "packetBytes",
    "packetLimitBytes",
    "performance",
    "postimage",
    "postimageSha256",
    "projectId",
    "projectIdentity",
    "projectIdentitySha256",
    "projectPath",
    "projectBootstrapReceipt",
    "provider",
    "request",
    "queryType",
    "receiptId",
    "recoveryReady",
    "retrieval",
    "returnedCount",
    "scan",
    "scanBinding",
    "scanHash",
    "scanSha256",
    "schema",
    "schemaVersion",
    "semanticGraph",
    "safety",
    "sourceRefs",
    "sourceThreadId",
    "source_refs",
    "status",
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


class ControlPayloadError(ValueError):
    """Compact structured control input exceeded a hard parsing boundary."""


def read_json(path: Optional[Path], *, max_bytes: int = MAX_STATE_SERIALIZED_BYTES) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return {}
    if len(payload) > max_bytes:
        raise ControlPayloadError("serialized_bytes_exceeded")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ControlPayloadError("invalid_or_excessively_nested_json") from exc
    if not isinstance(data, dict):
        raise ControlPayloadError("control_input_must_be_object")
    return data


def read_confirmed_state_json(
    path: Optional[Path], *, max_bytes: int = MAX_STATE_SERIALIZED_BYTES
) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        data = atomic_state.read_confirmed_json(path)
    except (atomic_state.StateDurabilityError, atomic_state.StatePermissionError) as exc:
        raise ControlPayloadError(f"durable_state_unavailable:{exc}") from exc
    valid, reason, serialized_bytes = inspect_control_structure(data, max_bytes=max_bytes)
    if not valid:
        raise ControlPayloadError(f"state_{reason}:{serialized_bytes}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_state.atomic_write_json(path, data)


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
    owner_key = event.get("taskId") or event.get("threadId") or "default"
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
        "legacyInjectionOwnerKey": str(owner_key),
        "taskInjectionLedger": {},
        "taskRuntimeLedger": {},
        "callbackSliceLedger": {},
        "hostReplacementLedger": {},
        "projectWorkspacesByTask": {},
        "projectInjectionLedger": {},
        "frozenTaskKeys": [],
        "freezeReceiptsByTask": {},
        "freezeByTask": {},
        "recoveryTransitions": [],
        "programBlockAuditLedger": {},
        "programGlobalBlock": {"active": False},
        "freeze": {
            "triggered": False,
            "receiptEmitted": False,
            "reason": None,
            "oldThreadStopReason": None,
            "harvestDriverStatus": "active",
            "ownerTaskKey": None,
        },
    }


def inspect_control_structure(value: Any, *, max_bytes: int) -> tuple[bool, str, int]:
    """Bound shape before deepcopy/recursive business logic, then count real JSON bytes."""

    stack: list[tuple[Any, int, bool]] = [(value, 0, False)]
    active_containers: set[int] = set()
    nodes = 0
    string_bytes = 0
    source_refs = 0
    while stack:
        item, depth, leaving = stack.pop()
        if leaving:
            active_containers.discard(id(item))
            continue
        nodes += 1
        if nodes > MAX_STRUCTURE_NODES:
            return False, "structure_node_limit_exceeded", 0
        if depth > MAX_STRUCTURE_DEPTH:
            return False, "structure_depth_limit_exceeded", 0
        if isinstance(item, str):
            string_bytes += len(item.encode("utf-8"))
            if string_bytes > MAX_STRING_BYTES:
                return False, "string_bytes_limit_exceeded", 0
            continue
        if isinstance(item, dict):
            identity = id(item)
            if identity in active_containers:
                return False, "cyclic_control_structure", 0
            active_containers.add(identity)
            if len(item) > MAX_CONTAINER_WIDTH:
                return False, "container_width_limit_exceeded", 0
            stack.append((item, depth, True))
            for key, child in item.items():
                if not isinstance(key, str):
                    return False, "non_string_object_key", 0
                string_bytes += len(key.encode("utf-8"))
                if string_bytes > MAX_STRING_BYTES:
                    return False, "string_bytes_limit_exceeded", 0
                if key in {"sourceRefs", "source_refs"} and isinstance(child, list):
                    source_refs += len(child)
                    if source_refs > MAX_SOURCE_REFS:
                        return False, "source_refs_limit_exceeded", 0
                stack.append((child, depth + 1, False))
            continue
        if isinstance(item, (list, tuple)):
            identity = id(item)
            if identity in active_containers:
                return False, "cyclic_control_structure", 0
            active_containers.add(identity)
            if len(item) > MAX_CONTAINER_WIDTH:
                return False, "container_width_limit_exceeded", 0
            stack.append((item, depth, True))
            stack.extend((child, depth + 1, False) for child in item)
            continue
        if item is not None and not isinstance(item, (bool, int, float, _DriverCapability)):
            return False, "unsupported_control_value", 0
    try:
        serialized = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=lambda item: "__trusted_capability__"
            if isinstance(item, _DriverCapability)
            else (_ for _ in ()).throw(TypeError(type(item).__name__)),
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        return False, f"control_serialization_failed:{type(exc).__name__}", 0
    if len(serialized) > max_bytes:
        return False, "serialized_bytes_exceeded", len(serialized)
    return True, "ok", len(serialized)


def _iter_nodes(value: Any, path: str = "$") -> Any:
    stack: list[tuple[Any, str]] = [(value, path)]
    while stack:
        item, item_path = stack.pop()
        yield item, item_path
        if isinstance(item, dict):
            stack.extend(
                (child, f"{item_path}.{key}") for key, child in reversed(list(item.items()))
            )
        elif isinstance(item, list):
            stack.extend(
                (child, f"{item_path}[{index}]")
                for index, child in reversed(list(enumerate(item)))
            )


def find_forbidden_payload(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    for item, item_path in _iter_nodes(value, path):
        if isinstance(item, dict):
            for key in item:
                key_path = f"{item_path}.{key}"
                if key in FORBIDDEN_KEYS:
                    findings.append(f"forbidden key {key_path}")
        elif isinstance(item, str) and FORBIDDEN_VALUE_RE.search(item):
            findings.append(f"forbidden payload marker at {item_path}")
    return findings


def normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def find_forbidden_takeover_content(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    for item, item_path in _iter_nodes(value, path):
        if not isinstance(item, dict):
            continue
        layer = str(item.get("layer") or item.get("memoryLayer") or "").strip().lower()
        if layer and layer not in ALLOWED_TAKEOVER_LAYERS:
            findings.append(f"forbidden takeover layer {item_path}.layer={layer}")
        for key, child in item.items():
            if normalized_key(key) in FORBIDDEN_TAKEOVER_CONTENT_KEYS and child not in (None, False, "", [], {}):
                findings.append(f"forbidden takeover content key {item_path}.{key}")
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
    value = event.get("taskId") or event.get("threadId") or state.get("taskId") or state.get("threadId") or "default"
    return str(value)


def legacy_owner_matches(state: dict[str, Any], event: dict[str, Any], key: str) -> bool:
    explicit_owner = state.get("legacyInjectionOwnerKey")
    if explicit_owner not in (None, ""):
        owner_ids = {str(explicit_owner)}
    else:
        owner_ids = {str(value) for value in (state.get("taskId"), state.get("threadId")) if value not in (None, "")}
    current_ids = {str(key)}
    current_ids.update(
        str(value) for value in (event.get("taskId"), event.get("threadId")) if value not in (None, "")
    )
    return bool(owner_ids and owner_ids.intersection(current_ids))


def task_ledger(state: dict[str, Any], event: dict[str, Any], key: str) -> dict[str, Any]:
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
    migrate_legacy = legacy_owner_matches(state, event, key)
    if migrate_legacy and not ledger.get("injectedGenerationIds") and state.get("injectedGenerationIds"):
        ledger["injectedGenerationIds"] = list(state.get("injectedGenerationIds") or [])
    if migrate_legacy and not ledger.get("lastGenerationBasis") and state.get("lastGenerationBasis"):
        ledger["lastGenerationBasis"] = dict(state.get("lastGenerationBasis") or {})
    ledger.setdefault("invalidatedGenerationIds", [])
    return ledger


def all_injected_generation_ids(state: dict[str, Any]) -> set[str]:
    generations = {str(item) for item in state.get("injectedGenerationIds", [])}
    for ledger_group in ("taskInjectionLedger", "projectInjectionLedger"):
        ledgers = state.get(ledger_group)
        if not isinstance(ledgers, dict):
            continue
        stack = list(ledgers.values())
        while stack:
            item = stack.pop()
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("injectedGenerationIds"), list):
                generations.update(str(value) for value in item["injectedGenerationIds"])
            else:
                stack.extend(item.values())
    return generations


def normalized_project_workspaces(value: Any) -> tuple[list[dict[str, Any]], str | None]:
    if value is None:
        return [], None
    if not isinstance(value, list) or not value:
        return [], "invalid_project_workspaces"
    normalized: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    seen_roots: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            return [], "invalid_project_workspaces"
        project_key = str(item.get("projectKey") or item.get("key") or "").strip()
        workspace = str(item.get("workspace") or item.get("projectPath") or "").strip()
        if not project_key or not workspace or not Path(workspace).is_absolute():
            return [], "invalid_project_workspaces"
        resolved = str(Path(workspace).resolve())
        if project_key in seen_keys or resolved in seen_roots:
            return [], "duplicate_project_workspace"
        seen_keys.add(project_key)
        seen_roots.add(resolved)
        project_id = item.get("projectId")
        normalized.append(
            {
                "projectKey": project_key,
                "workspace": resolved,
                "projectId": str(project_id) if project_id not in (None, "") else None,
            }
        )
    return normalized, None


def project_workspace_context(
    state: dict[str, Any], event: dict[str, Any], key: str
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str | None]:
    by_task = state.setdefault("projectWorkspacesByTask", {})
    supplied, error = normalized_project_workspaces(event.get("projectWorkspaces"))
    if error:
        return [], None, error
    stored = by_task.get(key)
    if supplied:
        if stored and stored != supplied:
            return [], None, "project_workspaces_changed"
        by_task[key] = supplied
        stored = supplied
    projects = stored if isinstance(stored, list) else []
    if not projects:
        return [], None, None

    ledgers = state.setdefault("projectInjectionLedger", {}).setdefault(key, {})
    for project in projects:
        ledger = ledgers.setdefault(
            project["projectKey"],
            {
                "workspace": project["workspace"],
                "projectId": project.get("projectId"),
                "bootstrapStatus": "pending",
                "injectedGenerationIds": [],
                "lastGenerationBasis": {},
                "invalidatedGenerationIds": [],
                "authority": {},
            },
        )
        if ledger.get("workspace") != project["workspace"]:
            return projects, None, "project_workspace_scope_changed"
        configured_id = project.get("projectId")
        if configured_id and ledger.get("projectId") not in (None, configured_id):
            return projects, None, "project_identity_scope_changed"
        if configured_id:
            ledger["projectId"] = configured_id

    requested_key = str(event.get("activeProjectKey") or "").strip()
    if requested_key:
        active = next((item for item in projects if item["projectKey"] == requested_key), None)
        if active is None:
            return projects, None, "unknown_active_project_workspace"
        return projects, active, None
    for project in projects:
        if ledgers[project["projectKey"]].get("bootstrapStatus") == "pending":
            return projects, project, None
    for project in projects:
        if ledgers[project["projectKey"]].get("bootstrapStatus") != "ready":
            return projects, project, None
    return projects, None, "active_project_workspace_required"


def remaining_project_keys(state: dict[str, Any], task: str, projects: list[dict[str, Any]], active: str) -> list[str]:
    ledgers = state.get("projectInjectionLedger", {}).get(task, {})
    return [
        project["projectKey"]
        for project in projects
        if project["projectKey"] != active
        and ledgers.get(project["projectKey"], {}).get("bootstrapStatus") != "ready"
    ]


def runtime_ledger(state: dict[str, Any], key: str) -> dict[str, Any]:
    ledgers = state.setdefault("taskRuntimeLedger", {})
    if not isinstance(ledgers, dict):
        ledgers = {}
        state["taskRuntimeLedger"] = ledgers
    ledger = ledgers.setdefault(
        key,
        {
            "turnCount": 0,
            "cumulativeInputTokens": 0,
            "consumedPreflightRequestIds": [],
            "consumedHostTelemetryReceiptIds": [],
            "lastContextCompactionCount": 0,
        },
    )
    if not isinstance(ledger, dict):
        ledger = {
            "turnCount": 0,
            "cumulativeInputTokens": 0,
            "consumedPreflightRequestIds": [],
            "consumedHostTelemetryReceiptIds": [],
            "lastContextCompactionCount": 0,
        }
        ledgers[key] = ledger
    ledger["turnCount"] = as_int(ledger.get("turnCount"))
    ledger["cumulativeInputTokens"] = as_int(ledger.get("cumulativeInputTokens"))
    ledger["lastContextCompactionCount"] = as_int(ledger.get("lastContextCompactionCount"))
    consumed = ledger.get("consumedPreflightRequestIds")
    ledger["consumedPreflightRequestIds"] = (
        [str(item) for item in consumed if isinstance(item, str) and item]
        if isinstance(consumed, list)
        else []
    )
    telemetry_receipts = ledger.get("consumedHostTelemetryReceiptIds")
    ledger["consumedHostTelemetryReceiptIds"] = (
        [str(item) for item in telemetry_receipts if isinstance(item, str) and item]
        if isinstance(telemetry_receipts, list)
        else []
    )
    return ledger


def exact_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def host_telemetry_receipt_sha256(receipt: dict[str, Any]) -> str:
    canonical = {
        key: receipt.get(key)
        for key in (
            "schema",
            "telemetrySource",
            "metricScope",
            "capturedAt",
            "taskId",
            "lastRequestInputTokens",
            "currentPostCompactionContextTokens",
            "projectedNextRequestInputTokens",
            "estimatedContextBytes",
            "modelContextWindowTokens",
            "reservedOutputTokens",
            "cumulativeInputTokens",
            "contextCompactionCount",
            "compactionCountSource",
        )
    }
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def validate_host_telemetry(
    event: dict[str, Any], task_runtime: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    if event.get("_hostTelemetryCapability") is not HOST_TELEMETRY_CAPABILITY:
        return None, "host_context_telemetry_unavailable"
    receipt = event.get("hostTelemetryReceipt")
    if not isinstance(receipt, dict):
        return None, "host_context_telemetry_receipt_required"
    if receipt.get("schema") != HOST_TELEMETRY_SCHEMA:
        return None, "host_context_telemetry_schema_invalid"
    if receipt.get("telemetrySource") != HOST_TELEMETRY_SOURCE:
        return None, "host_context_telemetry_source_invalid"
    if receipt.get("metricScope") != HOST_TELEMETRY_SCOPE:
        return None, "host_context_telemetry_scope_invalid"
    task_id = str(event.get("taskId") or event.get("threadId") or "")
    if not task_id or receipt.get("taskId") != task_id:
        return None, "host_context_telemetry_task_mismatch"
    captured_at = parse_rfc3339(receipt.get("capturedAt"))
    now = parse_rfc3339(event.get("evaluationTime")) or datetime.now(timezone.utc)
    if captured_at is None or captured_at > now or now - captured_at > HOST_TELEMETRY_MAX_AGE:
        return None, "host_context_telemetry_stale_or_invalid"
    required_ints = (
        "lastRequestInputTokens",
        "currentPostCompactionContextTokens",
        "projectedNextRequestInputTokens",
        "estimatedContextBytes",
        "modelContextWindowTokens",
        "reservedOutputTokens",
        "cumulativeInputTokens",
        "contextCompactionCount",
    )
    values: dict[str, int] = {}
    for field in required_ints:
        parsed = exact_nonnegative_int(receipt.get(field))
        if parsed is None:
            return None, f"host_context_telemetry_invalid_{field}"
        values[field] = parsed
    if values["modelContextWindowTokens"] <= values["reservedOutputTokens"]:
        return None, "host_context_telemetry_invalid_context_window"
    if receipt.get("compactionCountSource") != HOST_COMPACTION_SOURCE:
        return None, "host_context_compaction_source_invalid"
    if values["contextCompactionCount"] < as_int(task_runtime.get("lastContextCompactionCount")):
        return None, "host_context_compaction_count_regressed"
    if values["projectedNextRequestInputTokens"] < values["currentPostCompactionContextTokens"]:
        return None, "host_context_telemetry_projection_below_current_context"
    receipt_id = receipt.get("hostTelemetryReceiptId")
    if not isinstance(receipt_id, str) or not re.fullmatch(r"[0-9a-f]{64}", receipt_id):
        return None, "host_context_telemetry_receipt_id_invalid"
    if receipt_id != host_telemetry_receipt_sha256(receipt):
        return None, "host_context_telemetry_receipt_digest_mismatch"
    if receipt_id in task_runtime.get("consumedHostTelemetryReceiptIds", []):
        return None, "duplicate_host_context_telemetry_receipt"
    return dict(receipt), None


def model_request_preflight(
    event: dict[str, Any], task_runtime: dict[str, Any], limits: dict[str, int]
) -> tuple[dict[str, Any] | None, str | None]:
    if event.get("eventType") != MODEL_REQUEST_PREFLIGHT_EVENT:
        return None, None
    request_id = event.get("requestId")
    if not isinstance(request_id, str) or not request_id.strip():
        return None, "pressure_preflight_request_id_required"
    if not (event.get("taskId") or event.get("threadId")):
        return None, "pressure_preflight_task_id_required"
    consumed = task_runtime.get("consumedPreflightRequestIds", [])
    if request_id in consumed:
        return None, "duplicate_pressure_preflight_request"
    telemetry, telemetry_reason = validate_host_telemetry(event, task_runtime)
    if telemetry is None:
        return None, telemetry_reason
    values = {
        "inputTokens": telemetry["projectedNextRequestInputTokens"],
        "estimatedContextTokens": telemetry["currentPostCompactionContextTokens"],
        "estimatedContextBytes": telemetry["estimatedContextBytes"],
        "projectedContextTokens": telemetry["projectedNextRequestInputTokens"],
        "modelContextWindowTokens": telemetry["modelContextWindowTokens"],
        "reservedOutputTokens": telemetry["reservedOutputTokens"],
        "lastRequestInputTokens": telemetry["lastRequestInputTokens"],
        "hostTelemetryReceiptId": telemetry["hostTelemetryReceiptId"],
        "telemetrySource": telemetry["telemetrySource"],
        "metricScope": telemetry["metricScope"],
        "capturedAt": telemetry["capturedAt"],
        "contextCompactionCount": telemetry["contextCompactionCount"],
        "compactionCountSource": telemetry["compactionCountSource"],
    }
    policy_limit = int(limits["contextTokenLimit"] * DEFAULT_PREFLIGHT_FREEZE_RATIO)
    model_limit = values["modelContextWindowTokens"] - values["reservedOutputTokens"]
    values.update(
        {
            "requestId": request_id,
            "policyPreflightLimit": policy_limit,
            "modelAvailableInputLimit": model_limit,
            "effectivePreflightLimit": min(policy_limit, model_limit),
        }
    )
    return values, None


def pressure_reasons(
    event: dict[str, Any], state: dict[str, Any], limits: dict[str, int], task_runtime: dict[str, Any]
) -> list[str]:
    reasons: list[str] = []
    input_tokens = as_int(event.get("inputTokens"))
    context_tokens = as_int(event.get("estimatedContextTokens") or event.get("contextTokens"))
    context_bytes = as_int(event.get("estimatedContextBytes") or event.get("sessionBytes"))

    if input_tokens >= limits["inputTokenLimit"]:
        reasons.append("input_token_limit")
    if context_tokens >= limits["contextTokenLimit"]:
        reasons.append("context_token_limit")
    if context_bytes >= limits["contextBytesLimit"]:
        reasons.append("context_bytes_limit")
    preflight = event.get("_validatedPressurePreflight")
    if isinstance(preflight, dict) and preflight["projectedContextTokens"] >= preflight["effectivePreflightLimit"]:
        reasons.append("projected_context_pressure_limit")
    if (
        isinstance(preflight, dict)
        and (event.get("recoveryRequested") is True or event.get("replacementForTaskId"))
        and preflight["estimatedContextTokens"] > DEFAULT_CLEAN_TAKEOVER_RETAINED_CONTEXT_LIMIT
    ):
        reasons.insert(0, "clean_takeover_retained_context_limit")
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


def ordinary_codex_lane_dispatch_contract(event: dict[str, Any]) -> tuple[bool, str | None]:
    """Recognize native Codex lane creation without granting lifecycle authority."""

    event_type = str(event.get("eventType") or "")
    if event_type != ORDINARY_CODEX_LANE_DISPATCH_EVENT:
        return False, None
    if event.get("dispatchRequested") is not True:
        return False, "codex_lane_dispatch_flag_required"
    if event.get("routingSurface") not in ORDINARY_CODEX_ROUTING_SURFACES:
        return False, "codex_lane_dispatch_surface_invalid"
    if event.get("executionBackend") != "codex_native":
        return False, "codex_lane_dispatch_backend_invalid"
    forbidden_flags = (
        "providerCallRequested",
        "paidProviderRequested",
        "externalHarnessRequested",
        "recoveryRequested",
        "takeoverRequired",
        "goalTransferRequested",
        "contextReplacementRequested",
        "archiveRequested",
    )
    if any(event.get(field) is True for field in forbidden_flags):
        return False, "codex_lane_dispatch_scope_invalid"
    if event.get("replacementForTaskId") not in (None, ""):
        return False, "codex_lane_dispatch_scope_invalid"
    if event.get("takeoverPacket") not in (None, {}):
        return False, "codex_lane_dispatch_scope_invalid"
    return True, None


def user_authorization_reason(event: dict[str, Any]) -> str | None:
    for field in sorted(USER_AUTHORIZATION_FLAGS):
        if as_bool(event.get(field)) is True:
            return field
    if as_bool(event.get("paidProviderRequested")) is True and as_bool(event.get("spendingAuthorized")) is not True:
        return "spending_authorization_required"
    return None


def parse_rfc3339(value: Any) -> datetime | None:
    if not isinstance(value, str) or RFC3339_RE.fullmatch(value) is None:
        return None
    text = value
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def global_block_receipt_digest(receipt: dict[str, Any]) -> str:
    source = receipt.get("sourceRef") if isinstance(receipt.get("sourceRef"), dict) else {}
    canonical = {
        "receiptId": receipt.get("receiptId"),
        "authorityId": receipt.get("authorityId"),
        "issuer": receipt.get("issuer"),
        "sourceRoot": receipt.get("sourceRoot"),
        "sourceRef": {
            "path": source.get("path"),
            "hash": source.get("hash"),
            "auditSeriesId": source.get("auditSeriesId"),
        },
        "observedAt": receipt.get("observedAt"),
        "workspace": receipt.get("workspace"),
        "scope": receipt.get("scope"),
        "blockerCode": receipt.get("blockerCode"),
        "sequence": receipt.get("sequence"),
        "previousReceiptSha256": receipt.get("previousReceiptSha256"),
        "safeReadyLaneCount": receipt.get("safeReadyLaneCount"),
        "rerouteAvailable": receipt.get("rerouteAvailable"),
        "externalStateChangeRequired": receipt.get("externalStateChangeRequired"),
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def exact_global_impasse_fields(value: dict[str, Any]) -> bool:
    safe_count = value.get("safeReadyLaneCount")
    return (
        isinstance(safe_count, int)
        and not isinstance(safe_count, bool)
        and safe_count == 0
        and type(value.get("rerouteAvailable")) is bool
        and value["rerouteAvailable"] is False
        and type(value.get("externalStateChangeRequired")) is bool
        and value["externalStateChangeRequired"] is True
    )


def canonical_authority_tuple(
    receipt: dict[str, Any], authority_registry: dict[str, Any], workspace_root: Path
) -> dict[str, str] | None:
    authority_id = receipt.get("authorityId")
    issuer = receipt.get("issuer")
    source = receipt.get("sourceRef")
    source_root_value = receipt.get("sourceRoot")
    if (
        not isinstance(authority_id, str)
        or not authority_id.strip()
        or not isinstance(issuer, str)
        or not issuer.strip()
        or not isinstance(source, dict)
        or not isinstance(source.get("auditSeriesId"), str)
        or not source["auditSeriesId"].strip()
        or not isinstance(source_root_value, str)
        or not source_root_value.strip()
        or not Path(source_root_value).is_absolute()
    ):
        return None
    authority = authority_registry.get(authority_id)
    if not isinstance(authority, dict):
        return None
    registry_root_value = authority.get("sourceRoot")
    if not isinstance(registry_root_value, str) or not registry_root_value.strip() or not Path(registry_root_value).is_absolute():
        return None
    try:
        source_root = Path(source_root_value).resolve(strict=True)
        registry_root = Path(registry_root_value).resolve(strict=True)
        source_root.relative_to(workspace_root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None
    if (
        not source_root.is_dir()
        or source_root != registry_root
        or authority.get("issuer") != issuer
        or authority.get("auditSeriesId") != source["auditSeriesId"]
    ):
        return None
    return {
        "authorityId": authority_id,
        "issuer": issuer,
        "auditSeriesId": source["auditSeriesId"],
        "sourceRoot": str(source_root),
    }


def replay_global_block_receipt(
    receipt: dict[str, Any],
    *,
    blocker_code: str,
    workspace_root: Path,
    authority_registry: dict[str, Any],
    expected_authority: dict[str, str] | None,
    expected_sequence: int,
    previous_digest: str | None,
    previous_observed_at: datetime | None,
    evaluation_time: datetime,
) -> tuple[dict[str, Any], dict[str, str], datetime] | None:
    source = receipt.get("sourceRef")
    receipt_workspace_value = receipt.get("workspace")
    if (
        not blocker_code
        or not isinstance(source, dict)
        or not isinstance(receipt_workspace_value, str)
        or not receipt_workspace_value.strip()
        or not Path(receipt_workspace_value).is_absolute()
    ):
        return None
    receipt_workspace = receipt_workspace_value
    try:
        receipt_root = Path(receipt_workspace).resolve(strict=True)
        source_path_value = source.get("path")
        if not isinstance(source_path_value, str) or not source_path_value.strip():
            return None
        source_path = Path(source_path_value)
        resolved_source = (workspace_root / source_path).resolve(strict=True) if not source_path.is_absolute() else source_path.resolve(strict=True)
        resolved_source.relative_to(workspace_root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None
    if receipt_root != workspace_root or not resolved_source.is_file():
        return None
    expected_source_hash = str(source.get("hash") or "").strip().lower()
    authority_tuple = canonical_authority_tuple(receipt, authority_registry, workspace_root)
    if not re.fullmatch(r"[0-9a-f]{64}", expected_source_hash) or authority_tuple is None:
        return None
    if expected_authority is not None and authority_tuple != expected_authority:
        return None
    try:
        authority_root = Path(authority_tuple["sourceRoot"])
        resolved_source.relative_to(authority_root)
    except ValueError:
        return None
    if hashlib.sha256(resolved_source.read_bytes()).hexdigest() != expected_source_hash:
        return None
    try:
        source_record = json.loads(resolved_source.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(source_record, dict):
        return None

    observed_at = parse_rfc3339(receipt.get("observedAt"))
    if observed_at is None or observed_at > evaluation_time or evaluation_time - observed_at > GLOBAL_BLOCK_RECEIPT_MAX_AGE:
        return None
    sequence = receipt.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence <= 0:
        return None
    source_matches_receipt = (
        source_record.get("receiptId") == receipt.get("receiptId")
        and source_record.get("authorityId") == authority_tuple["authorityId"]
        and source_record.get("issuer") == authority_tuple["issuer"]
        and source_record.get("auditSeriesId") == authority_tuple["auditSeriesId"]
        and source_record.get("sourceRoot") == authority_tuple["sourceRoot"]
        and source_record.get("observedAt") == receipt.get("observedAt")
        and source_record.get("scope") == GLOBAL_BLOCK_RECEIPT_SCOPE
        and source_record.get("blockerCode") == blocker_code
        and source_record.get("sequence") == sequence
        and source_record.get("previousReceiptSha256") == previous_digest
        and exact_global_impasse_fields(source_record)
        and source_record.get("safeReadyLaneCount") == receipt.get("safeReadyLaneCount")
        and source_record.get("rerouteAvailable") is receipt.get("rerouteAvailable")
        and source_record.get("externalStateChangeRequired") is receipt.get("externalStateChangeRequired")
    )
    if (
        not str(receipt.get("receiptId") or "").strip()
        or not source_matches_receipt
        or not exact_global_impasse_fields(receipt)
        or receipt.get("scope") != GLOBAL_BLOCK_RECEIPT_SCOPE
        or receipt.get("blockerCode") != blocker_code
        or sequence != expected_sequence
        or receipt.get("previousReceiptSha256") != previous_digest
        or str(receipt.get("receiptSha256") or "") != global_block_receipt_digest(receipt)
        or (previous_observed_at is not None and observed_at <= previous_observed_at)
    ):
        return None
    canonical = {
        "receiptId": receipt.get("receiptId"),
        "authorityId": authority_tuple["authorityId"],
        "issuer": authority_tuple["issuer"],
        "sourceRoot": authority_tuple["sourceRoot"],
        "receiptSha256": receipt.get("receiptSha256"),
        "sourceRef": {
            "path": source_path_value,
            "resolvedPath": str(resolved_source),
            "hash": expected_source_hash,
            "auditSeriesId": authority_tuple["auditSeriesId"],
        },
        "workspace": str(workspace_root),
        "observedAt": receipt.get("observedAt"),
        "scope": GLOBAL_BLOCK_RECEIPT_SCOPE,
        "blockerCode": blocker_code,
        "sequence": sequence,
        "previousReceiptSha256": previous_digest,
        "safeReadyLaneCount": 0,
        "rerouteAvailable": False,
        "externalStateChangeRequired": True,
    }
    return canonical, authority_tuple, observed_at


def verified_global_block_receipt(
    assessment: dict[str, Any], event: dict[str, Any], ledger: dict[str, Any]
) -> dict[str, Any] | None:
    receipt = assessment.get("auditReceipt")
    if not isinstance(receipt, dict) or not exact_global_impasse_fields(assessment):
        return None
    blocker_code = str(assessment.get("blockerCode") or assessment.get("code") or "").strip()
    workspace = str(event.get("workspace") or event.get("canonicalWorkspace") or "").strip()
    authority_registry = event.get("_programBlockAuthorityRegistry")
    if not blocker_code or not workspace or not isinstance(authority_registry, dict):
        return None
    try:
        workspace_root = Path(workspace).resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None
    receipts = ledger.get("receipts") if isinstance(ledger.get("receipts"), list) else []
    expected_authority = ledger.get("authorityTuple") if isinstance(ledger.get("authorityTuple"), dict) else None
    evaluation_time = datetime.now(timezone.utc)
    previous_digest = None
    previous_observed_at = None
    replayed: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    for expected_sequence, prior in enumerate(receipts, 1):
        if not isinstance(prior, dict):
            return None
        verified = replay_global_block_receipt(
            prior,
            blocker_code=blocker_code,
            workspace_root=workspace_root,
            authority_registry=authority_registry,
            expected_authority=expected_authority,
            expected_sequence=expected_sequence,
            previous_digest=previous_digest,
            previous_observed_at=previous_observed_at,
            evaluation_time=evaluation_time,
        )
        if verified is None:
            return None
        canonical, authority_tuple, previous_observed_at = verified
        if canonical["receiptId"] in seen_ids or canonical["sourceRef"]["resolvedPath"] in seen_sources:
            return None
        expected_authority = authority_tuple
        previous_digest = str(canonical["receiptSha256"])
        seen_ids.add(str(canonical["receiptId"]))
        seen_sources.add(str(canonical["sourceRef"]["resolvedPath"]))
        replayed.append(canonical)
    verified = replay_global_block_receipt(
        receipt,
        blocker_code=blocker_code,
        workspace_root=workspace_root,
        authority_registry=authority_registry,
        expected_authority=expected_authority,
        expected_sequence=len(replayed) + 1,
        previous_digest=previous_digest,
        previous_observed_at=previous_observed_at,
        evaluation_time=evaluation_time,
    )
    if verified is None:
        return None
    canonical, authority_tuple, _ = verified
    if canonical["receiptId"] in seen_ids or canonical["sourceRef"]["resolvedPath"] in seen_sources:
        return None
    ledger["receipts"] = replayed
    ledger["authorityTuple"] = authority_tuple
    return canonical


def global_block_is_proven(state: dict[str, Any], event: dict[str, Any]) -> bool:
    if event.get("_globalBlockAuditCapability") is not GLOBAL_BLOCK_AUDIT_CAPABILITY:
        return False
    assessment = event.get("programBlockAssessment")
    if not isinstance(assessment, dict):
        return False
    qualifies = exact_global_impasse_fields(assessment)
    blocker_code = str(assessment.get("blockerCode") or assessment.get("code") or "").strip()
    if not qualifies or not blocker_code:
        return False
    ledgers = state.setdefault("programBlockAuditLedger", {})
    authority_registry = state.get("programBlockAuthorityRegistry")
    if not isinstance(authority_registry, dict) or not authority_registry:
        return False
    event["_programBlockAuthorityRegistry"] = deepcopy(authority_registry)
    workspace = str(event.get("workspace") or event.get("canonicalWorkspace") or "").strip()
    ledger_key = hashlib.sha256(f"{workspace}\0{blocker_code}".encode("utf-8")).hexdigest()
    ledger = ledgers.get(ledger_key)
    if not isinstance(ledger, dict):
        ledger = {"blockerCode": blocker_code, "workspace": workspace, "receipts": []}
    receipt = verified_global_block_receipt(assessment, event, ledger)
    if receipt is None:
        return False
    ledgers[ledger_key] = ledger
    ledger.setdefault("receipts", []).append(receipt)
    ledger["lastAssessment"] = {
        "safeReadyLaneCount": 0,
        "rerouteAvailable": False,
        "externalStateChangeRequired": True,
    }
    proven = len(ledger["receipts"]) >= 3
    if proven:
        proof = ledger["receipts"][-1]
        state["programGlobalBlock"] = {
            "active": True,
            "ledgerKey": ledger_key,
            "workspace": ledger["workspace"],
            "blockerCode": blocker_code,
            "authorityTuple": deepcopy(ledger["authorityTuple"]),
            "proofReceiptSha256": proof["receiptSha256"],
            "activatedAt": proof["observedAt"],
            "activatedByTaskKey": task_key(event, state),
            "knownGenerationIds": sorted(all_injected_generation_ids(state)),
        }
    return proven


def global_block_recovery_is_authorized(state: dict[str, Any], event: dict[str, Any], key: str) -> bool:
    if event.get("_globalBlockRecoveryCapability") is not GLOBAL_BLOCK_RECOVERY_CAPABILITY:
        return False
    active = state.get("programGlobalBlock")
    receipt = event.get("programBlockRecoveryReceipt")
    packet = event.get("takeoverPacket")
    if not isinstance(active, dict) or active.get("active") is not True:
        return False
    if not isinstance(receipt, dict) or not isinstance(packet, dict):
        return False
    observed_at = parse_rfc3339(receipt.get("observedAt"))
    activated_at = parse_rfc3339(active.get("activatedAt"))
    now = datetime.now(timezone.utc)
    generation_id = packet.get("contextGenerationId")
    known_generations = {str(item) for item in active.get("knownGenerationIds", [])}
    canonical_recovery = {
        field: receipt.get(field)
        for field in (
            "recoveryId",
            "ledgerKey",
            "proofReceiptSha256",
            "workspace",
            "blockerCode",
            "replacementTaskKey",
            "contextGenerationId",
            "observedAt",
        )
    }
    recovery_digest = hashlib.sha256(
        json.dumps(canonical_recovery, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return (
        isinstance(receipt.get("recoveryId"), str)
        and bool(receipt["recoveryId"].strip())
        and receipt.get("ledgerKey") == active.get("ledgerKey")
        and receipt.get("proofReceiptSha256") == active.get("proofReceiptSha256")
        and receipt.get("workspace") == active.get("workspace")
        and receipt.get("blockerCode") == active.get("blockerCode")
        and receipt.get("replacementTaskKey") == key
        and receipt.get("contextGenerationId") == generation_id
        and receipt.get("recoveryReceiptSha256") == recovery_digest
        and isinstance(generation_id, str)
        and bool(generation_id.strip())
        and generation_id not in known_generations
        and observed_at is not None
        and activated_at is not None
        and activated_at < observed_at <= now
        and now - observed_at <= GLOBAL_BLOCK_RECEIPT_MAX_AGE
    )


def global_block_result(state: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    result = block_result(
        state,
        "program_blocked_global",
        metrics,
        next_action="wait_for_fresh_verified_replacement_or_external_state_change",
        scope="program_goal",
        lifecycle_state="program_blocked_global",
    )
    return result | {
        "programGoalBlocked": True,
        "unrelatedLanesMayContinue": False,
        "allowOldThreadExecution": False,
        "allowToolCalls": False,
        "allowProjectToolCalls": False,
        "allowProviderCalls": False,
    }


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


def accepted_receipt_digest(event: dict[str, Any]) -> str | None:
    receipt = accepted_receipt(event)
    candidates = [
        event.get("acceptedEvidenceReceiptDigest"),
        receipt.get("acceptedEvidenceReceiptDigest") if isinstance(receipt, dict) else None,
        receipt.get("receiptDigest") if isinstance(receipt, dict) else None,
    ]
    for value in candidates:
        normalized = str(value or "").strip().lower()
        if re.fullmatch(r"[0-9a-f]{64}", normalized):
            return normalized
    return None


def has_formal_acceptance(event: dict[str, Any]) -> bool:
    receipt = accepted_receipt(event)
    if (
        not isinstance(receipt, dict)
        or not accepted_receipt_id(event)
        or not accepted_receipt_digest(event)
    ):
        return False
    decision = str(receipt.get("decision") or "").strip().lower()
    return decision in {"accept", "accepted"}


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
        "projectKey": event.get("activeProjectKey") or None,
        "projectId": event.get("expectedProjectId") or event.get("projectId") or None,
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
        "acceptedEvidenceReceiptDigest": accepted_receipt_digest(event),
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

    expected_project_id = event.get("expectedProjectId") or event.get("projectId")
    packet_project_id = packet.get("projectId") or first_present(packet, "projectIdentity.projectId")
    if expected_project_id and packet_project_id and str(expected_project_id) != str(packet_project_id):
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
    packet_workspace = str(packet.get("workspace") or packet.get("projectPath") or "")
    if as_bool(event.get("projectWorkspaceScopeRequired")) is True:
        if not packet_workspace or not packet_project_id:
            return True
        if str(Path(packet_workspace).resolve()) != str(Path(workspace).resolve()):
            return True
    source_refs = packet.get("sourceRefs") or packet.get("source_refs") or []
    if source_refs is None:
        source_refs = []
    if not isinstance(source_refs, list):
        return True
    root = Path(workspace).resolve() if workspace else None
    for ref in source_refs:
        if not isinstance(ref, dict):
            return True
        ref_project_id = ref.get("projectId")
        if as_bool(event.get("projectWorkspaceScopeRequired")) is True and not ref_project_id:
            return True
        if packet_project_id and ref_project_id and str(packet_project_id) != str(ref_project_id):
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
        if re.match(r"^[a-z][a-z0-9+.-]*://", text_path, re.IGNORECASE):
            if not text_path.startswith(("git://", "memory-runtime://")):
                return True
            continue
        candidate = Path(text_path)
        if root is not None:
            try:
                scoped = candidate if candidate.is_absolute() else root / candidate
                scoped.resolve().relative_to(root)
            except ValueError:
                return True
    return False


def accepted_evidence_out_of_scope(event: dict[str, Any]) -> bool:
    refs: list[Any] = []
    writeback = event.get("writebackEvidence")
    if isinstance(writeback, dict):
        expected_workspace = str(event.get("workspace") or "")
        writeback_workspace = str(writeback.get("workspace") or "")
        expected_project_id = str(event.get("expectedProjectId") or event.get("projectId") or "")
        writeback_project_id = str(writeback.get("projectId") or "")
        if not writeback_workspace or str(Path(writeback_workspace).resolve()) != str(Path(expected_workspace).resolve()):
            return True
        if not writeback_project_id or writeback_project_id != expected_project_id:
            return True
        receipt = writeback.get("receipt")
        if not isinstance(receipt, dict):
            return True
        receipt_id = receipt.get("receiptId") or receipt.get("id")
        receipt_workspace = str(receipt.get("workspace") or "")
        receipt_project_id = str(receipt.get("projectId") or "")
        if not receipt_id:
            return True
        if str(Path(receipt_workspace).resolve()) != str(Path(expected_workspace).resolve()):
            return True
        if receipt_project_id != expected_project_id:
            return True
        source_refs = writeback.get("sourceRefs")
        if not isinstance(source_refs, list) or not source_refs:
            return True
    for source in (
        event,
        event.get("acceptedEvidence"),
        event.get("evidence"),
        event.get("exactScan"),
        event.get("scan"),
        writeback,
    ):
        if isinstance(source, dict) and isinstance(source.get("sourceRefs"), list):
            refs.extend(source["sourceRefs"])
    if not refs:
        return False
    return source_refs_out_of_scope(
        {
            "workspace": event.get("workspace"),
            "projectId": event.get("expectedProjectId") or event.get("projectId"),
            "sourceRefs": refs,
        },
        event,
    )


def project_bootstrap_receipt_sha256(receipt: dict[str, Any]) -> str:
    payload = {
        "workspace": str(Path(str(receipt.get("workspace") or "")).resolve()),
        "projectId": str(receipt.get("projectId") or ""),
        "projectIdentitySha256": str(receipt.get("projectIdentitySha256") or ""),
        "authorizedCheckpointId": str(receipt.get("authorizedCheckpointId") or ""),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


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

    if as_bool(event.get("projectWorkspaceScopeRequired")) is True:
        receipt = packet.get("projectBootstrapReceipt")
        if not isinstance(receipt, dict):
            return "block", "missing_project_bootstrap_receipt"
        if receipt.get("_driverCapability") is not APP_OWNED_BOOTSTRAP_DRIVER_CAPABILITY:
            return "block", "project_bootstrap_driver_authority_missing"
        required_receipt = {
            "workspace",
            "projectId",
            "projectIdentitySha256",
            "authorizedCheckpointId",
            "verifyReceiptSha256",
        }
        if any(receipt.get(field) in (None, "") for field in required_receipt):
            return "block", "incomplete_project_bootstrap_receipt"
        if str(receipt["verifyReceiptSha256"]) != project_bootstrap_receipt_sha256(receipt):
            return "block", "project_bootstrap_receipt_hash_invalid"
        expected_workspace = str(event.get("workspace") or "")
        packet_workspace = str(packet.get("workspace") or packet.get("projectPath") or "")
        packet_project_id = str(packet.get("projectId") or first_present(packet, "projectIdentity.projectId") or "")
        packet_identity = str(first_present(packet, "projectIdentitySha256", "projectIdentity.projectIdentitySha256") or "")
        packet_checkpoint = str(first_present(packet, "checkpointSha256", "authorityCheckpointSha256", "scanBinding.authorizedCheckpointId", "verifiedMemoryStateHash") or "")
        if str(Path(str(receipt["workspace"])).resolve()) != str(Path(expected_workspace).resolve()):
            return "block", "project_bootstrap_receipt_scope_mismatch"
        if str(Path(packet_workspace).resolve()) != str(Path(expected_workspace).resolve()):
            return "block", "project_bootstrap_receipt_scope_mismatch"
        if str(receipt["projectId"]) != packet_project_id:
            return "block", "project_bootstrap_receipt_identity_mismatch"
        if str(receipt["projectIdentitySha256"]) != packet_identity:
            return "block", "project_bootstrap_receipt_identity_mismatch"
        if str(receipt["authorizedCheckpointId"]) != packet_checkpoint:
            return "block", "project_bootstrap_receipt_checkpoint_mismatch"

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
    lifecycle_state: str = "lane_paused_recoverable",
    user_authorization_required: bool = False,
    recovery_control_tools: list[str] | None = None,
) -> dict[str, Any]:
    control_tools = list(recovery_control_tools or [])
    result = {
        "schema": SCHEMA,
        "ok": True,
        "decision": "block",
        "reason": reason,
        "currentTaskId": metrics.get("taskKey"),
        "frozenTaskId": None,
        "rebindHarvestDriverToTaskId": None,
        "allowOldThreadExecution": allow_old_thread_execution,
        "allowToolCalls": False,
        "allowProjectToolCalls": False,
        "allowProviderCalls": False,
        "allowRecoveryControlTools": bool(control_tools),
        "recoveryControlToolAllowlist": control_tools,
        "unbindHarvestDriver": False,
        "programGoalBlocked": False,
        "unrelatedLanesMayContinue": True,
        "lifecycleState": lifecycle_state,
        "userAuthorizationRequired": user_authorization_required,
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


def freeze_result(
    state: dict[str, Any], reason: str, metrics: dict[str, Any], owner_key: str | None = None
) -> dict[str, Any]:
    receipt_key = owner_key or str(state.get("freeze", {}).get("ownerTaskKey") or "default")
    receipts = state.setdefault("freezeReceiptsByTask", {})
    freezes = state.setdefault("freezeByTask", {})
    existing = freezes.get(receipt_key) if isinstance(freezes.get(receipt_key), dict) else {}
    effective_reason = str(existing.get("reason") or reason)
    receipt_already_emitted = bool(receipts.get(receipt_key))
    next_action = "stop_old_task_no_repeat" if receipt_already_emitted else "emit_freeze_receipt_and_unbind_harvest_driver"
    metrics["oldThreadStopReason"] = effective_reason

    state.setdefault("freeze", {})
    frozen_keys = state.setdefault("frozenTaskKeys", [])
    if owner_key and owner_key not in frozen_keys:
        frozen_keys.append(owner_key)
    receipts[receipt_key] = True
    freezes[receipt_key] = {"reason": effective_reason, "receiptEmitted": True}
    state["freeze"].update(
        {
            "triggered": True,
            "receiptEmitted": True,
            "reason": effective_reason,
            "oldThreadStopReason": effective_reason,
            "harvestDriverStatus": "unbind_required",
            "ownerTaskKey": owner_key or state.get("freeze", {}).get("ownerTaskKey"),
        }
    )

    return {
        "schema": SCHEMA,
        "ok": True,
        "decision": "freeze",
        "reason": effective_reason,
        "currentTaskId": receipt_key,
        "frozenTaskId": receipt_key,
        "rebindHarvestDriverToTaskId": None,
        "emitFreezeReceipt": not receipt_already_emitted,
        "allowOldThreadExecution": False,
        "allowToolCalls": False,
        "allowProjectToolCalls": False,
        "allowProviderCalls": False,
        "allowRecoveryControlTools": False,
        "recoveryControlToolAllowlist": [],
        "unbindHarvestDriver": True,
        "programGoalBlocked": False,
        "unrelatedLanesMayContinue": True,
        "lifecycleState": "task_context_frozen_replace_required",
        "userAuthorizationRequired": False,
        "nextAction": next_action,
        "blocker": {
            "code": effective_reason,
            "scope": "project_context",
            "message": "Fail closed: old CEO task is no longer a safe execution surface.",
            "nextAction": next_action,
        },
        "prepareTakeover": {
            "required": True,
            "hook": "prepare_takeover",
            "preferredTokens": DEFAULT_TAKEOVER_PREFERRED_TOKENS,
            "maxTokens": DEFAULT_TAKEOVER_TOKEN_LIMIT,
            "allowedLayers": ["hot", "warm", "continuity", "graph", "sourceRefs"],
            "forbidden": ["raw_chat", "image_base64", "full_logs", "cold_body", "credentials", "sqlite"],
        },
        "metrics": metrics,
        "state": state,
    }


def malformed_control_result(reason: str, *, serialized_bytes: int = 0) -> dict[str, Any]:
    state = default_state({})
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
        "ok": False,
        "decision": "freeze",
        "reason": reason,
        "emitFreezeReceipt": True,
        "allowOldThreadExecution": False,
        "allowToolCalls": False,
        "allowProjectToolCalls": False,
        "allowProviderCalls": False,
        "allowRecoveryControlTools": False,
        "recoveryControlToolAllowlist": [],
        "unbindHarvestDriver": True,
        "programGoalBlocked": False,
        "unrelatedLanesMayContinue": True,
        "lifecycleState": "task_context_frozen_replace_required",
        "userAuthorizationRequired": False,
        "nextAction": "replace_with_bounded_typed_control_packet",
        "blocker": {
            "code": reason,
            "scope": "task_context",
            "nextAction": "replace_with_bounded_typed_control_packet",
        },
        "metrics": {"serializedBytes": serialized_bytes},
        "state": state,
    }


def evaluate(event: dict[str, Any], previous_state: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    event_valid, event_reason, event_bytes = inspect_control_structure(
        event, max_bytes=MAX_EVENT_SERIALIZED_BYTES
    )
    if not event_valid:
        return malformed_control_result(f"event_{event_reason}", serialized_bytes=event_bytes)
    state_valid, state_reason, state_bytes = inspect_control_structure(
        previous_state or {}, max_bytes=MAX_STATE_SERIALIZED_BYTES
    )
    if not state_valid:
        return malformed_control_result(f"state_{state_reason}", serialized_bytes=state_bytes)
    packet_candidate = event.get("takeoverPacket")
    if packet_candidate is not None:
        packet_valid, packet_reason, packet_bytes = inspect_control_structure(
            packet_candidate, max_bytes=MAX_TAKEOVER_SERIALIZED_BYTES
        )
        if not packet_valid:
            return malformed_control_result(
                f"takeover_packet_{packet_reason}", serialized_bytes=packet_bytes
            )
    event = deepcopy(event)
    state = deepcopy(previous_state) if previous_state else default_state(event)
    state.setdefault("schema", SCHEMA)
    state.setdefault("injectedGenerationIds", [])
    state.setdefault("taskInjectionLedger", {})
    state.setdefault("taskRuntimeLedger", {})
    state.setdefault("callbackSliceLedger", {})
    state.setdefault("hostReplacementLedger", {})
    state.setdefault("projectWorkspacesByTask", {})
    state.setdefault("projectInjectionLedger", {})
    state.setdefault("frozenTaskKeys", [])
    state.setdefault("freezeReceiptsByTask", {})
    state.setdefault("freezeByTask", {})
    state.setdefault("recoveryTransitions", [])
    state.setdefault("programBlockAuditLedger", {})
    state.setdefault("programGlobalBlock", {"active": False})
    state.setdefault("freeze", default_state(event)["freeze"])
    key = task_key(event, state)
    projects, active_project, project_config_error = project_workspace_context(state, event, key)
    multi_project = bool(projects)
    if multi_project and active_project:
        event["workspace"] = active_project["workspace"]
        ledger = state["projectInjectionLedger"][key][active_project["projectKey"]]
        event["expectedProjectId"] = ledger.get("projectId") or active_project.get("projectId")
        event["projectWorkspaceScopeRequired"] = True
    else:
        ledger = task_ledger(state, event, key)
    task_runtime = runtime_ledger(state, key)
    ordinary_lane_dispatch, ordinary_lane_dispatch_reason = ordinary_codex_lane_dispatch_contract(event)
    preflight, preflight_reason = model_request_preflight(event, task_runtime, limits)
    if preflight is not None:
        event["_validatedPressurePreflight"] = preflight
        task_runtime["rotationRecommended"] = (
            preflight["contextCompactionCount"] >= DEFAULT_CONTEXT_COMPACTION_ROTATION_LIMIT
        )
        task_runtime["rotationNextAction"] = (
            "finish_current_slice_then_prepare_verified_takeover"
            if task_runtime["rotationRecommended"] else None
        )

    # Migrate the legacy single sticky-freeze bit into a task-scoped freeze.
    # A different clean task may recover with a fresh verified generation, but
    # the unsafe old execution surface remains frozen permanently.
    if state.get("freeze", {}).get("triggered") and not state["frozenTaskKeys"]:
        legacy_owner = str(
            state.get("freeze", {}).get("ownerTaskKey")
            or state.get("taskId")
            or state.get("threadId")
            or key
        )
        state["frozenTaskKeys"].append(legacy_owner)
        state["freezeByTask"][legacy_owner] = {
            "reason": str(state.get("freeze", {}).get("reason") or "old_task_frozen"),
            "receiptEmitted": bool(state.get("freeze", {}).get("receiptEmitted")),
        }
        legacy_ledger = state.get("taskInjectionLedger", {}).setdefault(
            legacy_owner,
            {"injectedGenerationIds": [], "lastGenerationBasis": {}, "invalidatedGenerationIds": []},
        )
        if legacy_owner_matches(state, {"taskId": legacy_owner}, legacy_owner):
            if not legacy_ledger.get("injectedGenerationIds") and state.get("injectedGenerationIds"):
                legacy_ledger["injectedGenerationIds"] = list(state.get("injectedGenerationIds") or [])
            if not legacy_ledger.get("lastGenerationBasis") and state.get("lastGenerationBasis"):
                legacy_ledger["lastGenerationBasis"] = dict(state.get("lastGenerationBasis") or {})
        legacy_ledger.setdefault("invalidatedGenerationIds", [])

    forbidden = find_forbidden_payload(event)
    input_tokens = preflight["inputTokens"] if isinstance(preflight, dict) else 0
    state["turnCount"] = as_int(state.get("turnCount")) + 1
    task_runtime["turnCount"] += 1

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
        "taskKey": key,
        "turnCount": task_runtime["turnCount"],
        "inputTokens": input_tokens,
        "estimatedContextTokens": preflight["estimatedContextTokens"] if isinstance(preflight, dict) else 0,
        "estimatedContextBytes": preflight["estimatedContextBytes"] if isinstance(preflight, dict) else 0,
        "cumulativeInputTokens": task_runtime["cumulativeInputTokens"],
        "fallbackRate": round(fallback_rate, 4),
        "takeoverGeneration": event.get("takeoverPacket", {}).get("contextGenerationId")
        if isinstance(event.get("takeoverPacket"), dict)
        else None,
        "duplicateInjectionCount": as_int(state.get("duplicateInjectionCount")),
        "oldThreadStopReason": state.get("freeze", {}).get("oldThreadStopReason"),
        "pressurePreflight": preflight,
        "contextCompactionCount": preflight["contextCompactionCount"] if isinstance(preflight, dict) else 0,
        "contextCompactionRotationLimit": DEFAULT_CONTEXT_COMPACTION_ROTATION_LIMIT,
        "rotationRecommended": task_runtime.get("rotationRecommended", False),
        "rotationNextAction": task_runtime.get("rotationNextAction"),
    }
    if multi_project:
        metrics.update(
            {
                "artifactRoot": event.get("artifactRoot"),
                "activeProjectKey": active_project.get("projectKey") if active_project else None,
                "projectWorkspaceCount": len(projects),
            }
        )

    global_recovery_authorized = False
    if state.get("programGlobalBlock", {}).get("active") is True:
        packet_for_recovery = event.get("takeoverPacket")
        recovery_verdict = ("block", "missing_takeover_packet")
        if isinstance(packet_for_recovery, dict):
            recovery_verdict = validate_takeover_packet(
                packet_for_recovery, event, ledger, limits["takeoverTokenLimit"]
            )
        if (
            recovery_verdict[0] == "allow"
            and global_block_recovery_is_authorized(state, event, key)
        ):
            global_recovery_authorized = True
        else:
            return global_block_result(state, metrics)

    if project_config_error:
        return block_result(
            state,
            project_config_error,
            metrics,
            next_action="use_explicit_ordered_project_workspaces_and_select_one_project",
            scope="cross_project_bootstrap",
        )

    if multi_project and active_project and accepted_evidence_out_of_scope(event):
        return block_result(
            state,
            "cross_project_evidence_scope_mismatch",
            metrics,
            next_action="provide_source_refs_only_from_active_project_workspace",
            scope="project_workspace",
        )

    if multi_project and active_project:
        project_ledger = state["projectInjectionLedger"][key][active_project["projectKey"]]
        packet_present = isinstance(event.get("takeoverPacket"), dict) and bool(event.get("takeoverPacket"))
        memory_present = isinstance(event.get("memory"), dict) and bool(event.get("memory"))
        pending_healthy_memory = memory_present and memory_fail_reason(event["memory"]) is None
        if project_ledger.get("bootstrapStatus") == "pending" and not packet_present and (
            not memory_present or pending_healthy_memory
        ):
            return block_result(
                state,
                "project_workspace_bootstrap_required",
                metrics,
                next_action="verify_then_prepare_takeover_for_active_project_workspace",
                scope="project_workspace",
                recovery_control_tools=["verify_project", "prepare_takeover"],
                extra={
                    "projectBootstrap": {
                        "mode": "lazy_ordered",
                        "artifactRootIsIdentity": False,
                        "activeProjectKey": active_project["projectKey"],
                        "workspace": active_project["workspace"],
                        "projectId": active_project.get("projectId"),
                        "remainingProjectKeys": remaining_project_keys(
                            state, key, projects, active_project["projectKey"]
                        ),
                    }
                },
            )

    if key in state.get("frozenTaskKeys", []):
        task_freeze = state.get("freezeByTask", {}).get(key, {})
        frozen_reason = str(
            (task_freeze.get("reason") if isinstance(task_freeze, dict) else None)
            or state.get("freeze", {}).get("reason")
            or "old_task_frozen"
        )
        return freeze_result(state, frozen_reason, metrics, key)

    if forbidden:
        return freeze_result(state, "forbidden_context_payload", metrics | {"forbiddenFindings": forbidden}, key)

    if ordinary_lane_dispatch_reason:
        return block_result(
            state,
            ordinary_lane_dispatch_reason,
            metrics,
            next_action="use_strict_native_codex_lane_dispatch_contract",
            scope="codex_lane_dispatch",
            lifecycle_state="lane_paused_recoverable",
        )

    if preflight_reason:
        return block_result(
            state,
            preflight_reason,
            metrics,
            next_action="collect_strict_host_pressure_metrics_before_model_request",
            scope="model_request_preflight",
            lifecycle_state="lane_paused_recoverable",
        )

    if isinstance(preflight, dict):
        telemetry_receipt_id = preflight["hostTelemetryReceiptId"]
        task_runtime["consumedHostTelemetryReceiptIds"].append(telemetry_receipt_id)
        task_runtime["consumedPreflightRequestIds"].append(preflight["requestId"])
        task_runtime["lastContextCompactionCount"] = preflight["contextCompactionCount"]
        last_request_input = preflight["lastRequestInputTokens"]
        task_runtime["cumulativeInputTokens"] += last_request_input
        state["cumulativeInputTokens"] = as_int(state.get("cumulativeInputTokens")) + last_request_input
        metrics["cumulativeInputTokens"] = task_runtime["cumulativeInputTokens"]
        metrics["cumulativeInputAdvisoryExceeded"] = (
            task_runtime["cumulativeInputTokens"] >= limits["cumulativeInputLimit"]
        )

    pressure = pressure_reasons(event, state, limits, task_runtime)
    if pressure:
        return freeze_result(state, pressure[0], metrics, key)

    authorization_reason = user_authorization_reason(event)
    if authorization_reason:
        return block_result(
            state,
            authorization_reason,
            metrics,
            next_action="request_one_compact_user_authorization",
            scope="requested_action",
            lifecycle_state="lane_paused_user_authorization",
            user_authorization_required=True,
        )

    if global_block_is_proven(state, event):
        return global_block_result(state, metrics)

    if as_bool(event.get("approvalRequested")) is True:
        metrics["approvalDisposition"] = "routine_in_scope_no_user_authorization"

    if is_non_memory_event(event) and not isinstance(packet, dict) and not isinstance(memory, dict):
        metrics["memoryRuntimeAction"] = "skip"
        return {
            "schema": SCHEMA,
            "ok": True,
            "decision": "allow",
            "reason": "non_memory_event_no_retrieval",
            "allowOldThreadExecution": True,
            "allowToolCalls": False,
            "allowProjectToolCalls": False,
            "allowProviderCalls": False,
            "allowRecoveryControlTools": False,
            "recoveryControlToolAllowlist": [],
            "unbindHarvestDriver": False,
            "programGoalBlocked": False,
            "unrelatedLanesMayContinue": True,
            "lifecycleState": "active",
            "userAuthorizationRequired": False,
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
        if multi_project and active_project:
            ledger["bootstrapStatus"] = "stale"
            ledger["authority"] = {"status": memory_reason}
        return block_result(
            state,
            "authority_defect",
            metrics | {"validationReason": memory_reason},
            next_action="run_one_bounded_readonly_verify_then_replace_context_if_healthy",
            scope="memory_runtime_verify",
            recovery_control_tools=["verify_project", "scan_workspace"],
            extra={
                "projectBootstrap": {
                    "activeProjectKey": active_project["projectKey"],
                    "workspace": active_project["workspace"],
                    "status": "stale",
                    "otherProjectsMayContinue": True,
                    "remainingProjectKeys": remaining_project_keys(
                        state, key, projects, active_project["projectKey"]
                    ),
                }
            }
            if multi_project and active_project
            else None,
        )
    if binding_changed and has_formal_acceptance(event):
        request = refresh_binding_request(event, scan, previous_basis)
        return block_result(
            state,
            "refresh_binding_required",
            metrics | {"changedBasisKeys": changed_basis_keys},
            next_action="run_direct_refresh_binding_driver",
            scope="lane_or_module",
            recovery_control_tools=["refresh_binding_driver"],
            extra={"refreshBindingRequest": request},
        )
    if binding_changed:
        return block_result(
            state,
            "unaccepted_project_change",
            metrics | {"changedBasisKeys": changed_basis_keys, "scanChanged": changed},
            next_action="await_formal_acceptance_while_unrelated_lanes_continue",
            scope="lane_or_module",
            lifecycle_state="lane_paused_pending_acceptance",
        )
    if memory_reason:
        if multi_project and active_project:
            ledger["bootstrapStatus"] = "stale"
            ledger["authority"] = {"status": memory_reason}
        return block_result(
            state,
            memory_reason,
            metrics,
            next_action="run_readonly_exact_scan",
            scope="memory_runtime_verify",
            recovery_control_tools=["scan_workspace", "verify_project"],
            extra={
                "projectBootstrap": {
                    "activeProjectKey": active_project["projectKey"],
                    "workspace": active_project["workspace"],
                    "status": "stale",
                    "otherProjectsMayContinue": True,
                    "remainingProjectKeys": remaining_project_keys(
                        state, key, projects, active_project["projectKey"]
                    ),
                }
            }
            if multi_project and active_project
            else None,
        )

    if requires_stable_basis(event) and previous_basis and not current_basis and not isinstance(packet, dict):
        return block_result(
            state,
            "missing_generation_basis",
            metrics,
            next_action="run_verify_and_readonly_exact_scan_before_dispatch",
            recovery_control_tools=["verify_project", "scan_workspace"],
        )

    if event.get("takeoverRequired") and not isinstance(packet, dict):
        return block_result(
            state,
            "prepare_takeover_required",
            metrics,
            next_action="request_prepare_takeover_packet",
            recovery_control_tools=["prepare_takeover"],
        ) | {"unbindHarvestDriver": True}

    if ordinary_lane_dispatch:
        metrics["hostPreflightDisposition"] = "not_required_for_native_lane_creation"
        return {
            "schema": SCHEMA,
            "ok": True,
            "decision": "allow",
            "reason": "ordinary_codex_lane_dispatch_allowed",
            "executionClass": "ordinary_codex_lane_dispatch",
            "currentTaskId": key,
            "frozenTaskId": None,
            "rebindHarvestDriverToTaskId": None,
            "allowOldThreadExecution": True,
            "allowToolCalls": True,
            "allowProjectToolCalls": True,
            "allowProviderCalls": False,
            "allowRecoveryControlTools": False,
            "recoveryControlToolAllowlist": [],
            "unbindHarvestDriver": False,
            "programGoalBlocked": False,
            "unrelatedLanesMayContinue": True,
            "lifecycleState": "active",
            "userAuthorizationRequired": False,
            "nextAction": "dispatch_bounded_native_codex_lane",
            "metrics": metrics,
            "state": state,
        }

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
        replacement_for = str(event.get("replacementForTaskId") or "")
        recovery_requested = as_bool(event.get("recoveryRequested")) is True
        recovery_ready = recovery_requested and replacement_for in state.get("frozenTaskKeys", [])
        if recovery_requested and not recovery_ready:
            return block_result(
                state,
                "replacement_target_not_frozen",
                metrics,
                next_action="bind_recovery_to_exact_frozen_task",
                scope="takeover_packet",
            )
        if recovery_ready:
            frozen_ledger = state.get("taskInjectionLedger", {}).get(replacement_for, {})
            frozen_generations = set(str(item) for item in frozen_ledger.get("injectedGenerationIds", []))
            if generation_id in frozen_generations:
                return block_result(
                    state,
                    "replacement_generation_not_fresh",
                    metrics,
                    next_action="request_fresh_context_generation_for_replacement",
                    scope="takeover_packet",
                )
        if ledger.get("injectedGenerationIds") and basis_changed(ledger.get("lastGenerationBasis", {}), packet_basis):
            prior_generations = [str(item) for item in ledger.get("injectedGenerationIds", [])]
            ledger["invalidatedGenerationIds"] = sorted(
                set(ledger.get("invalidatedGenerationIds", []) + prior_generations)
            )
            state["invalidatedGenerationIds"] = ledger["invalidatedGenerationIds"]
            metrics["invalidatedGenerationCount"] = len(ledger["invalidatedGenerationIds"])
        if multi_project and active_project:
            packet_project_id = packet.get("projectId") or first_present(packet, "projectIdentity.projectId")
            known_project_id = ledger.get("projectId")
            if known_project_id and packet_project_id and str(known_project_id) != str(packet_project_id):
                return block_result(
                    state,
                    "project_identity_scope_changed",
                    metrics,
                    next_action="verify_exact_active_project_workspace_identity",
                    scope="project_workspace",
                )
        ledger["injectedGenerationIds"].append(generation_id)
        ledger["lastGenerationBasis"] = packet_basis
        if multi_project and active_project:
            ledger["projectId"] = str(packet_project_id) if packet_project_id else known_project_id
            ledger["bootstrapStatus"] = "ready"
            ledger["authority"] = {
                "memoryMode": first_present(packet, "memoryMode", "memory.memoryMode"),
                "authorityVerification": first_present(
                    packet, "authorityVerification", "memory.authorityVerification"
                ),
                "current": True,
                "recoveryReady": True,
                "checkpoint": packet["projectBootstrapReceipt"]["authorizedCheckpointId"],
                "verifyReceipt": packet["projectBootstrapReceipt"]["verifyReceiptSha256"],
                "authorityReceipt": first_present(packet, "authorityReceiptId", "receiptId"),
            }
        else:
            verified_workspace = event.get("workspace") or packet.get("workspace")
            if isinstance(verified_workspace, str) and Path(verified_workspace).is_absolute():
                canonical_workspace = str(Path(verified_workspace).resolve())
                existing_workspace = ledger.get("workspace")
                if existing_workspace and existing_workspace != canonical_workspace:
                    return block_result(
                        state,
                        "single_project_workspace_changed",
                        metrics,
                        next_action="start_explicit_project_scoped_task_or_restore_verified_workspace",
                        scope="takeover_packet",
                    )
                ledger["workspace"] = canonical_workspace
            state["injectedGenerationIds"] = ledger["injectedGenerationIds"]
            state["lastGenerationBasis"] = ledger["lastGenerationBasis"]
            state["legacyInjectionOwnerKey"] = key
        if global_recovery_authorized:
            active_block = state["programGlobalBlock"]
            recovery_receipt = event["programBlockRecoveryReceipt"]
            state["programGlobalBlock"] = active_block | {
                "active": False,
                "clearedAt": recovery_receipt["observedAt"],
                "clearedByTaskKey": key,
                "recoveryId": recovery_receipt["recoveryId"],
                "recoveryGenerationId": generation_id,
            }
            state["recoveryTransitions"].append(
                {
                    "fromState": "program_blocked_global",
                    "toTaskKey": key,
                    "contextGenerationId": generation_id,
                    "status": "verified_global_replacement_ready",
                    "proofReceiptSha256": active_block["proofReceiptSha256"],
                }
            )
        if recovery_ready:
            transition = {
                "fromTaskKey": replacement_for,
                "toTaskKey": key,
                "contextGenerationId": generation_id,
                "status": "verified_replacement_ready",
            }
            if transition not in state["recoveryTransitions"]:
                state["recoveryTransitions"].append(transition)
        metrics["takeoverGeneration"] = generation_id
        execution_preflight_ready = preflight is not None
        return {
            "schema": SCHEMA,
            "ok": True,
            "decision": "allow",
            "reason": reason,
            "currentTaskId": key,
            "frozenTaskId": replacement_for if recovery_ready else None,
            "rebindHarvestDriverToTaskId": key if recovery_ready else None,
            "allowOldThreadExecution": execution_preflight_ready,
            "allowToolCalls": execution_preflight_ready,
            "allowProjectToolCalls": execution_preflight_ready,
            "allowProviderCalls": execution_preflight_ready,
            "allowRecoveryControlTools": False,
            "recoveryControlToolAllowlist": [],
            "unbindHarvestDriver": recovery_ready,
            "programGoalBlocked": False,
            "unrelatedLanesMayContinue": True,
            "lifecycleState": "active",
            "userAuthorizationRequired": False,
            "resumeProgramGoal": (recovery_ready or global_recovery_authorized) and execution_preflight_ready,
            "clearHistoricalGoalBlocked": (recovery_ready or global_recovery_authorized) and execution_preflight_ready,
            "nextAction": (
                "inject_takeover_packet_once_then_lazy_bootstrap_next_project"
                if multi_project
                and active_project
                and remaining_project_keys(state, key, projects, active_project["projectKey"])
                else "inject_takeover_packet_once_and_resume_program_goal"
                if recovery_ready and execution_preflight_ready
                else "inject_takeover_packet_once_then_run_model_request_preflight"
                if recovery_ready
                else "inject_takeover_packet_once"
            ),
            "contextInjectionMode": "replace_long_thread_context",
            "projectBootstrap": {
                "mode": "lazy_ordered",
                "activeProjectKey": active_project["projectKey"],
                "workspace": active_project["workspace"],
                "status": "ready",
                "remainingProjectKeys": remaining_project_keys(
                    state, key, projects, active_project["projectKey"]
                ),
            }
            if multi_project and active_project
            else None,
            "metrics": metrics,
            "state": state,
        }

    if preflight is None:
        return block_result(
            state,
            "model_request_preflight_required",
            metrics,
            next_action="run_strict_model_request_preflight_before_execution",
            scope="model_request_preflight",
            lifecycle_state="lane_paused_recoverable",
        )

    return {
        "schema": SCHEMA,
        "ok": True,
        "decision": "allow",
        "reason": "within_budget",
        "currentTaskId": key,
        "frozenTaskId": None,
        "rebindHarvestDriverToTaskId": None,
        "allowOldThreadExecution": True,
        "allowToolCalls": True,
        "allowProjectToolCalls": True,
        "allowProviderCalls": True,
        "allowRecoveryControlTools": False,
        "recoveryControlToolAllowlist": [],
        "unbindHarvestDriver": False,
        "programGoalBlocked": False,
        "unrelatedLanesMayContinue": True,
        "lifecycleState": "active",
        "userAuthorizationRequired": False,
        "nextAction": "continue_bounded_execution",
        "metrics": metrics,
        "state": state,
    }


def evaluate_program_block_audit(
    event: dict[str, Any], previous_state: dict[str, Any], limits: dict[str, int]
) -> dict[str, Any]:
    """Trusted control entry point for a pre-registered neutral audit receipt."""

    trusted_event = dict(event)
    trusted_event["_globalBlockAuditCapability"] = GLOBAL_BLOCK_AUDIT_CAPABILITY
    return evaluate(trusted_event, previous_state, limits)


def evaluate_program_block_recovery(
    event: dict[str, Any], previous_state: dict[str, Any], limits: dict[str, int]
) -> dict[str, Any]:
    """Trusted control entry point for a fresh verified global replacement."""

    trusted_event = dict(event)
    trusted_event["_globalBlockRecoveryCapability"] = GLOBAL_BLOCK_RECOVERY_CAPABILITY
    return evaluate(trusted_event, previous_state, limits)


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

    try:
        event = read_json(args.event, max_bytes=MAX_EVENT_SERIALIZED_BYTES)
        state = read_confirmed_state_json(
            args.state, max_bytes=MAX_STATE_SERIALIZED_BYTES
        ) if args.state else {}
    except ControlPayloadError as exc:
        result = malformed_control_result(str(exc))
        print(json.dumps({k: v for k, v in result.items() if k != "state"}, indent=2, sort_keys=True))
        return 1
    state_sha256 = atomic_state.state_sha256(state)
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
        try:
            atomic_state.atomic_write_json(args.state, result["state"], expected_sha256=state_sha256)
        except atomic_state.StateConflictError as exc:
            raise SystemExit(str(exc)) from exc
    print(json.dumps({k: v for k, v in result.items() if k != "state"}, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
