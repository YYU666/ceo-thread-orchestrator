#!/usr/bin/env python3
"""Fail-closed compatibility checks for a CMMD v2 task/receipt exchange.

This is intentionally a small, fail-closed CEO-side guard. CMMD remains
responsible for full JSON Schema admission and Host enforcement. The checker
verifies the identity, routing, risk, lease, budget, and receipt invariants CEO
Flow must inspect before treating a CMMD result as acceptance evidence. Full
schema validation uses ``jsonschema`` and fails closed when it is unavailable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import ntpath
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:  # pragma: no cover - exercised by deployment environments
    Draft202012Validator = None
    FormatChecker = None

HERE = Path(__file__).resolve().parent
SCHEMA_DIR = HERE.parent / "schemas" / "cmmd"

SCHEMA_HASHES = {
    "ceoflow.external_execution_task.v2.schema.json": "db5734568af3859e507486e3fabb2ddba9d77b84c13d8ab85a6c6b963811feda",
    "ceoflow.external_execution_receipt.v2.schema.json": "688691fa93d89fce12191b1d9a00d81883e1dbca596ed9330738b95cc96c5ab2",
    "ceoflow.authorization_lease.v1.schema.json": "8472ea35fda0ba8166c7f2fe9471d7fd029c7450d835c24cba0264f5fc9b1b89",
    "cmmd.context_view.v1.schema.json": "3d3e93e568677c12f5ab5c55e7e4a8223690b72b62eb1a285bdc9e9ce046b1f3",
}

IDENTITY_FIELDS = (
    "taskId",
    "taskSha256",
    "projectId",
    "projectIdentitySha256",
    "laneRole",
    "projectRoleThreadId",
    "runId",
    "executionEpoch",
    "runReservationId",
    "contextViewId",
    "contextViewSha256",
)

FORBIDDEN_TEXT = re.compile(r"data:image|;base64,|\binput_image\b", re.IGNORECASE)
BASE64_BLOB = re.compile(r"(?:[A-Za-z0-9+/]{4}){32,}(?:==|=)?")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def schema(name: str) -> dict[str, Any]:
    return read_json(SCHEMA_DIR / name)


def _scan_payload(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if FORBIDDEN_TEXT.search(str(key)):
                errors.append(f"forbidden payload key at {path}.{key}")
            errors.extend(_scan_payload(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_scan_payload(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        if FORBIDDEN_TEXT.search(value) or BASE64_BLOB.search(value):
            errors.append(f"forbidden image/base64 payload at {path}")
    return errors


def _shape_errors(value: dict[str, Any], schema_name: str) -> list[str]:
    contract = schema(schema_name)
    errors: list[str] = []
    for field in contract.get("required", []):
        if field not in value:
            errors.append(f"missing required field: {field}")
    allowed = set(contract.get("properties", {}))
    for field in sorted(set(value) - allowed):
        errors.append(f"unexpected top-level field: {field}")
    return errors


def _schema_errors(value: dict[str, Any], schema_name: str) -> list[str]:
    if Draft202012Validator is None or FormatChecker is None:
        return ["jsonschema dependency unavailable; full CMMD contract validation cannot run"]
    contract = schema(schema_name)
    validator = Draft202012Validator(contract, format_checker=FormatChecker())
    errors = []
    for failure in sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path)):
        location = "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in failure.absolute_path)
        errors.append(f"{schema_name} invalid at {location}: {failure.message}")
    return errors


def _canonical(value: Any) -> str:
    if value is None or isinstance(value, (bool, int, float, str)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(_canonical(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            json.dumps(key, ensure_ascii=False) + ":" + _canonical(value[key]) for key in sorted(value)
        ) + "}"
    raise TypeError(f"unsupported canonical value: {type(value)!r}")


def _sha256_canonical(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def compute_project_identity_sha256(task: dict[str, Any]) -> str:
    root = str(task.get("canonicalRoot", "")).replace("/", "\\")
    if root.startswith("\\\\?\\"):
        root = root[4:]
    root = ntpath.normpath(root)
    if len(root) >= 2 and root[1] == ":":
        root = root[0].lower() + root[1:]
    if len(root) > 3:
        root = root.rstrip("\\")
    return _sha256_canonical({"canonicalRoot": root, "projectId": task.get("projectId")})


def compute_task_sha256(task: dict[str, Any]) -> str:
    basis = {key: value for key, value in task.items() if key != "taskSha256"}
    if basis.get("riskTier") == "R1":
        basis = dict(basis)
        basis["writeSet"] = sorted(basis.get("writeSet", []))
        basis["commandAllowlist"] = sorted(basis.get("commandAllowlist", []), key=_canonical)
    return _sha256_canonical(basis)


def compute_context_view_sha256(context_view: dict[str, Any]) -> str:
    basis = json.loads(json.dumps(context_view))
    basis.pop("contextViewSha256", None)
    identity = basis.get("identity")
    if isinstance(identity, dict):
        identity.pop("taskSha256", None)
    payload = "cmmd.context_view.commitment.v1\x00" + _canonical(basis)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def verify_schema_snapshot() -> list[str]:
    errors: list[str] = []
    for name, expected in SCHEMA_HASHES.items():
        path = SCHEMA_DIR / name
        if not path.is_file():
            errors.append(f"missing CMMD schema snapshot: {name}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"CMMD schema snapshot hash mismatch: {name}")
    return errors


def validate_task(task: dict[str, Any]) -> list[str]:
    errors = _shape_errors(task, "ceoflow.external_execution_task.v2.schema.json")
    errors.extend(_schema_errors(task, "ceoflow.external_execution_task.v2.schema.json"))
    if task.get("schema") != "ceoflow.external_execution_task.v2":
        errors.append("new live CMMD runs require task schema v2")
    if task.get("projectIdentitySha256") != compute_project_identity_sha256(task):
        errors.append("task projectIdentitySha256 does not bind canonicalRoot and projectId")
    if task.get("taskSha256") != compute_task_sha256(task):
        errors.append("taskSha256 does not bind the canonical task envelope")
    if task.get("forbiddenPayloadsPresent") is not False:
        errors.append("task forbiddenPayloadsPresent must be false")

    route = task.get("route") if isinstance(task.get("route"), dict) else {}
    if route.get("fallback") != "deny" or route.get("retry") != 0:
        errors.append("CMMD v2 task must use fallback=deny and retry=0")
    if not route.get("provider") or not route.get("model"):
        errors.append("task route requires a concrete provider and model")

    provider_context = task.get("providerContextPolicy")
    if provider_context != {
        "authority": "cmmd_compiled_view",
        "nativeMemory": "disabled-required",
        "conversationReuse": "per-run-none",
    }:
        errors.append("task must disable Provider native memory and conversation reuse")
    visible_thread = task.get("visibleThreadPolicy")
    if visible_thread != {"archiveAfterReceipt": False, "terminalClosesVisibleThread": False}:
        errors.append("terminal run must not archive or close the visible project-role thread")

    risk = task.get("riskTier")
    write_set = task.get("writeSet")
    commands = task.get("commandAllowlist", [])
    if risk == "R0":
        if write_set != []:
            errors.append("R0 task writeSet must be empty")
        if task.get("authorizationLeaseRequired") is not False or "authorizationLeaseId" in task:
            errors.append("R0 task must not request an authorization lease")
        if commands not in ([], None):
            errors.append("R0 task commandAllowlist must be empty")
    elif risk == "R1":
        if not isinstance(write_set, list) or not write_set:
            errors.append("R1 task requires a non-empty writeSet")
        if task.get("authorizationLeaseRequired") is not True or not task.get("authorizationLeaseId"):
            errors.append("R1 task requires a bound authorization lease id")
        if not isinstance(commands, list) or not commands:
            errors.append("R1 task requires a Host command allowlist")
        elif not any(isinstance(item, dict) and item.get("purpose") == "verification" for item in commands):
            errors.append("R1 task requires at least one verification command")
    else:
        errors.append("riskTier must be R0 or R1")

    errors.extend(_scan_payload(task))
    return sorted(set(errors))


def validate_context_view(task: dict[str, Any], context_view: dict[str, Any] | None) -> list[str]:
    if context_view is None:
        return ["CMMD exchange requires the exact bounded Context View artifact"]
    errors = _shape_errors(context_view, "cmmd.context_view.v1.schema.json")
    errors.extend(_schema_errors(context_view, "cmmd.context_view.v1.schema.json"))
    if context_view.get("schema") != "cmmd.context_view.v1":
        errors.append("Context View schema must be cmmd.context_view.v1")
    if task.get("riskTier") != "R0":
        errors.append("current CMMD Context View snapshot is R0-only; R1 is not admissible")

    identity = context_view.get("identity") if isinstance(context_view.get("identity"), dict) else {}
    identity_pairs = {
        "projectRoleThreadId": "projectRoleThreadId",
        "taskId": "taskId",
        "taskSha256": "taskSha256",
        "runId": "runId",
        "executionEpoch": "executionEpoch",
        "contextViewId": "contextViewId",
        "contextViewCompiledAt": "contextViewCompiledAt",
    }
    for context_key, task_key in identity_pairs.items():
        if identity.get(context_key) != task.get(task_key):
            errors.append(f"task/Context View identity mismatch: {context_key}")
    if context_view.get("compiledAt") != task.get("contextViewCompiledAt"):
        errors.append("Context View compiledAt does not match task")
    if context_view.get("contextViewSha256") != task.get("contextViewSha256"):
        errors.append("Context View SHA-256 does not match task")
    if context_view.get("contextViewSha256") != compute_context_view_sha256(context_view):
        errors.append("Context View SHA-256 does not bind the canonical Context View")
    if context_view.get("providerContextPolicy") != task.get("providerContextPolicy"):
        errors.append("Context View Provider policy does not match task")
    if context_view.get("forbiddenPayloadsPresent") is not False:
        errors.append("Context View forbiddenPayloadsPresent must be false")

    layers = context_view.get("layers")
    task_projection = None
    if isinstance(layers, list) and layers and isinstance(layers[0], dict):
        task_projection = layers[0].get("payload")
    if not isinstance(task_projection, dict):
        errors.append("Context View task layer is missing")
    else:
        for field in (
            "projectRoleThreadId", "taskId", "runId", "executionEpoch",
            "contextViewId", "contextViewCompiledAt", "objective", "acceptance",
            "riskTier", "route", "sourceRefs", "readContract", "writeSet",
            "providerContextPolicy", "forbiddenPayloadsPresent",
        ):
            if task_projection.get(field) != task.get(field):
                errors.append(f"task/Context View projection mismatch: {field}")
        permissions = task_projection.get("permissions")
        expected_permissions = {
            "sourceRefAllowlist": task.get("readContract", {}).get("sourceRefAllowlist"),
            "writeSet": task.get("writeSet"),
            "authorizationLeaseRequired": task.get("authorizationLeaseRequired"),
        }
        if permissions != expected_permissions:
            errors.append("task/Context View permissions mismatch")

    if isinstance(layers, list) and len(layers) == 7:
        workspace_projection = layers[1].get("payload") if isinstance(layers[1], dict) else None
        if not isinstance(workspace_projection, dict) or workspace_projection.get("baseline") != task.get("workspace", {}).get("baseline"):
            errors.append("task/Context View workspace baseline mismatch")
        current_run = layers[6].get("payload") if isinstance(layers[6], dict) else None
        if not isinstance(current_run, dict):
            errors.append("Context View current-run layer is missing")
        else:
            for field in (
                "projectRoleThreadId", "taskId", "runId", "executionEpoch",
                "contextViewId", "contextViewCompiledAt",
            ):
                if current_run.get(field) != task.get(field):
                    errors.append(f"task/Context View current-run mismatch: {field}")

        estimates = context_view.get("estimates") if isinstance(context_view.get("estimates"), dict) else {}
        layer_estimates = estimates.get("layers") if isinstance(estimates.get("layers"), list) else []
        expected_layer_bytes = [len(_canonical(layer).encode("utf-8")) for layer in layers]
        if len(layer_estimates) == len(layers):
            for index, expected_bytes in enumerate(expected_layer_bytes):
                entry = layer_estimates[index]
                if not isinstance(entry, dict) or entry.get("bytes") != expected_bytes or entry.get("estimatedTokens") != expected_bytes:
                    errors.append(f"Context View layer estimate mismatch at index {index}")
        if estimates.get("bytes") != sum(expected_layer_bytes):
            errors.append("Context View total layer-byte estimate is inconsistent")
        delivered_bytes = len(_canonical(context_view).encode("utf-8"))
        if estimates.get("deliveredBytes") != delivered_bytes or estimates.get("estimatedTokens") != delivered_bytes:
            errors.append("Context View delivered byte/token estimate is inconsistent")
        budget_keys = ("taskBytes", "workspaceBytes", "hotBytes", "warmBytes", "skillBytes", "coldRefsBytes", "currentRunBytes")
        budgets = context_view.get("budgets") if isinstance(context_view.get("budgets"), dict) else {}
        for index, budget_key in enumerate(budget_keys):
            if isinstance(budgets.get(budget_key), int) and expected_layer_bytes[index] > budgets[budget_key]:
                errors.append(f"Context View layer exceeds {budget_key}")
        if isinstance(budgets.get("totalBytes"), int) and delivered_bytes > budgets["totalBytes"]:
            errors.append("Context View exceeds totalBytes")

    errors.extend(_scan_payload(context_view))
    return sorted(set(errors))


def validate_lease(
    task: dict[str, Any],
    lease: dict[str, Any] | None,
    *,
    expected_status: str = "active",
    now: datetime | None = None,
) -> list[str]:
    if task.get("riskTier") == "R0":
        return [] if lease is None else ["R0 task must not include an authorization lease"]
    if lease is None:
        return ["R1 exchange requires the authorization lease artifact"]
    errors = _shape_errors(lease, "ceoflow.authorization_lease.v1.schema.json")
    errors.extend(_schema_errors(lease, "ceoflow.authorization_lease.v1.schema.json"))
    if lease.get("schema") != "ceoflow.authorization_lease.v1":
        errors.append("R1 lease schema must be ceoflow.authorization_lease.v1")
    for field in (
        "taskId",
        "taskSha256",
        "projectId",
        "projectIdentitySha256",
        "projectRoleThreadId",
        "runId",
        "executionEpoch",
    ):
        if lease.get(field) != task.get(field):
            errors.append(f"authorization lease mismatch: {field}")
    if lease.get("leaseId") != task.get("authorizationLeaseId"):
        errors.append("authorization lease mismatch: leaseId")
    if lease.get("authority") != "host-only":
        errors.append("authorization lease must use the CMMD host-only authority")
    normalized_write_set = sorted(task.get("writeSet", []))
    normalized_allowlist = sorted(task.get("commandAllowlist", []), key=_canonical)
    if lease.get("writeSetSha256") != _sha256_canonical(normalized_write_set):
        errors.append("authorization lease writeSetSha256 does not bind the task write-set")
    if lease.get("commandAllowlistSha256") != _sha256_canonical(normalized_allowlist):
        errors.append("authorization lease commandAllowlistSha256 does not bind the task allowlist")
    issued_at = _parse_datetime(lease.get("issuedAt"))
    expires_at = _parse_datetime(lease.get("expiresAt"))
    if issued_at is None or expires_at is None or expires_at <= issued_at:
        errors.append("authorization lease time window is invalid")
    if lease.get("status") != expected_status:
        errors.append(f"authorization lease status must be {expected_status}")
    current = now or datetime.now(timezone.utc)
    if expected_status == "active" and expires_at is not None and current >= expires_at:
        errors.append("authorization lease is expired")
    if expected_status == "active" and lease.get("consumedAt") is not None:
        errors.append("active authorization lease consumedAt must be null")
    if expected_status == "consumed":
        consumed_at = _parse_datetime(lease.get("consumedAt"))
        if consumed_at is None or issued_at is None or expires_at is None or not (issued_at <= consumed_at < expires_at):
            errors.append("consumed authorization lease has an invalid consumedAt")
    errors.extend(_scan_payload(lease))
    return sorted(set(errors))


def validate_readiness(
    task: dict[str, Any],
    readiness: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> list[str]:
    if readiness is None:
        return ["CMMD readiness evidence packet is required"]
    errors = _shape_errors(readiness, "ceoflow.cmmd_readiness_evidence.v1.schema.json")
    errors.extend(_schema_errors(readiness, "ceoflow.cmmd_readiness_evidence.v1.schema.json"))
    if readiness.get("projectId") != task.get("projectId"):
        errors.append("CMMD readiness projectId does not match task")
    if readiness.get("projectIdentitySha256") != task.get("projectIdentitySha256"):
        errors.append("CMMD readiness project identity does not match task")
    route = task.get("route") if isinstance(task.get("route"), dict) else {}
    if readiness.get("provider") != route.get("provider") or readiness.get("model") != route.get("model"):
        errors.append("CMMD readiness Provider/model does not match task route")
    expected_snapshot = {
        "taskV2": SCHEMA_HASHES["ceoflow.external_execution_task.v2.schema.json"],
        "receiptV2": SCHEMA_HASHES["ceoflow.external_execution_receipt.v2.schema.json"],
        "authorizationLeaseV1": SCHEMA_HASHES["ceoflow.authorization_lease.v1.schema.json"],
        "contextViewV1": SCHEMA_HASHES["cmmd.context_view.v1.schema.json"],
    }
    if readiness.get("contractSnapshot") != expected_snapshot:
        errors.append("CMMD readiness contract snapshot does not match the vendored schemas")
    observed_at = _parse_datetime(readiness.get("observedAt"))
    expires_at = _parse_datetime(readiness.get("expiresAt"))
    if observed_at is None or expires_at is None or expires_at <= observed_at:
        errors.append("CMMD readiness evidence time window is invalid")
    current = now or datetime.now(timezone.utc)
    if expires_at is not None and current >= expires_at:
        errors.append("CMMD readiness evidence is expired")
    errors.extend(_scan_payload(readiness))
    return sorted(set(errors))


def validate_receipt(task: dict[str, Any], receipt: dict[str, Any]) -> list[str]:
    errors = _shape_errors(receipt, "ceoflow.external_execution_receipt.v2.schema.json")
    errors.extend(_schema_errors(receipt, "ceoflow.external_execution_receipt.v2.schema.json"))
    if receipt.get("schema") != "ceoflow.external_execution_receipt.v2":
        errors.append("new live CMMD runs require receipt schema v2")
    for field in IDENTITY_FIELDS:
        if receipt.get(field) != task.get(field):
            errors.append(f"task/receipt identity mismatch: {field}")
    if receipt.get("forbiddenPayloadsPresent") is not False:
        errors.append("receipt forbiddenPayloadsPresent must be false")

    requested = task.get("route") if isinstance(task.get("route"), dict) else {}
    actual = receipt.get("route") if isinstance(receipt.get("route"), dict) else {}
    if actual.get("requestedProvider") != requested.get("provider"):
        errors.append("receipt requestedProvider does not match task")
    if actual.get("requestedModel") != requested.get("model"):
        errors.append("receipt requestedModel does not match task")
    if actual.get("fallback") != "deny" or actual.get("retry") != 0:
        errors.append("receipt reports forbidden fallback or retry")

    succeeded = receipt.get("terminalStatus") == "succeeded"
    if succeeded:
        if actual.get("actualProvider") != requested.get("provider"):
            errors.append("successful receipt actualProvider differs from requested provider")
        if actual.get("actualModel") != requested.get("model"):
            errors.append("successful receipt actualModel differs from requested model")
        if receipt.get("failure") is not None:
            errors.append("successful receipt failure must be null")
        if not isinstance(receipt.get("sourceRefs"), list) or not receipt.get("sourceRefs"):
            errors.append("successful receipt requires sourceRefs")
        else:
            expected_refs = []
            for source_ref in task.get("sourceRefs", []):
                projected = {
                    "id": source_ref.get("id"),
                    "path": source_ref.get("path"),
                    "sha256": source_ref.get("sha256"),
                    "ranges": [],
                }
                for source_range in source_ref.get("ranges", []):
                    projected["ranges"].append({
                        "id": source_range.get("id"),
                        "startLine": source_range.get("startLine"),
                        "lineCount": source_range.get("endLine", 0) - source_range.get("startLine", 0) + 1,
                    })
                expected_refs.append(projected)
            if receipt.get("sourceRefs") != expected_refs:
                errors.append("successful receipt sourceRefs do not exactly project the task source ranges")
        fingerprint = receipt.get("workspaceFingerprint")
        if not isinstance(fingerprint, dict) or fingerprint.get("status") != "available":
            errors.append("successful receipt requires an available workspace fingerprint")

    risk = task.get("riskTier")
    changed_files = receipt.get("changedFiles")
    lease = receipt.get("authorizationLease")
    if risk == "R0":
        if succeeded and changed_files != []:
            errors.append("successful R0 receipt must report changedFiles=[]")
        fingerprint = receipt.get("workspaceFingerprint")
        if succeeded and isinstance(fingerprint, dict) and fingerprint.get("before") != fingerprint.get("after"):
            errors.append("successful R0 receipt requires identical before/after workspace fingerprints")
        if lease != {"required": False, "leaseId": None, "status": "not-issued"}:
            errors.append("R0 receipt must report no authorization lease")
    elif risk == "R1":
        if succeeded and (not isinstance(changed_files, list) or not changed_files):
            errors.append("successful R1 receipt requires Host-observed changed files")
        if not isinstance(lease, dict) or lease.get("required") is not True:
            errors.append("R1 receipt must report a required authorization lease")
        else:
            if lease.get("leaseId") != task.get("authorizationLeaseId"):
                errors.append("R1 receipt authorization lease id mismatch")
            if succeeded and lease.get("status") != "consumed":
                errors.append("successful R1 receipt requires a consumed lease")
        if succeeded:
            declared = set(task.get("writeSet", []))
            if not set(changed_files or []).issubset(declared):
                errors.append("R1 receipt changedFiles exceed the declared task write-set")
            compliance = receipt.get("writeSetCompliance")
            expected_declared = sorted(task.get("writeSet", []))
            if not isinstance(compliance, dict) or compliance.get("status") != "compliant":
                errors.append("successful R1 receipt requires compliant Host write-set evidence")
            else:
                if sorted(compliance.get("declaredPaths", [])) != expected_declared:
                    errors.append("R1 receipt declaredPaths do not match the task write-set")
                if compliance.get("violationPaths") != []:
                    errors.append("successful R1 receipt must have no write-set violations")
            tests = receipt.get("tests")
            if not isinstance(tests, list) or not tests:
                errors.append("successful R1 receipt requires Host-observed verification")
            elif any(not isinstance(item, dict) or item.get("hostObserved") is not True or item.get("exitCode") != 0 for item in tests):
                errors.append("successful R1 verification must be Host-observed with exitCode=0")
            expected_commands = {
                tuple([entry["executable"], *entry["args"]])
                for entry in task.get("commandAllowlist", [])
                if entry.get("purpose") == "command"
            }
            expected_tests = {
                tuple([entry["executable"], *entry["args"]])
                for entry in task.get("commandAllowlist", [])
                if entry.get("purpose") == "verification"
            }
            actual_commands = {tuple(item.get("argv", [])) for item in receipt.get("commands", []) if isinstance(item, dict)}
            actual_tests = {tuple(item.get("argv", [])) for item in receipt.get("tests", []) if isinstance(item, dict)}
            if not actual_commands.issubset(expected_commands):
                errors.append("R1 receipt command trace exceeds the Host allowlist")
            if not actual_tests or not actual_tests.issubset(expected_tests):
                errors.append("R1 receipt verification trace does not match the Host allowlist")

    run = receipt.get("run")
    if not isinstance(run, dict) or run.get("closed") is not True or not run.get("closedAt"):
        errors.append("terminal receipt must close the isolated run")
    else:
        cleanup = run.get("ephemeralCleanup")
        if not isinstance(cleanup, dict) or cleanup.get("rawToolBodiesStored") is not False:
            errors.append("terminal receipt must prove ephemeral cleanup without raw tool bodies")
    if receipt.get("visibleThread") != {"archiveState": "active", "archivedAt": None}:
        errors.append("terminal receipt must keep the visible project-role thread active")

    usage = receipt.get("usage")
    required_usage = {
        "providerCallCount",
        "inputTokens",
        "outputTokens",
        "cachedInputTokens",
        "uncachedInputTokens",
        "grossTokens",
        "toolCallCount",
        "deliveredToolResultBytes",
        "cost",
    }
    if not isinstance(usage, dict) or not required_usage.issubset(usage):
        errors.append("receipt usage/budget evidence is incomplete")
    budget = receipt.get("budget")
    if not isinstance(budget, dict) or budget.get("class") != risk:
        errors.append("receipt budget class does not match task risk tier")
    elif budget.get("limits") != task.get("budgets"):
        errors.append("receipt budget limits do not match the task")
    else:
        used = budget.get("used") if isinstance(budget.get("used"), dict) else {}
        remaining = budget.get("remaining") if isinstance(budget.get("remaining"), dict) else {}
        bindings = (
            ("modelRequests", "maxModelRequests"),
            ("toolCalls", "maxToolCalls"),
            ("inputTokens", "maxCumulativeInputTokens"),
            ("toolResultBytes", "maxCumulativeToolResultBytes"),
            ("wallTimeMs", "maxWallTimeMs"),
        )
        for used_key, limit_key in bindings:
            limit = task.get("budgets", {}).get(limit_key)
            used_value = used.get(used_key)
            if not isinstance(limit, int) or not isinstance(used_value, int) or used_value > limit:
                errors.append(f"receipt budget used.{used_key} exceeds or lacks its task limit")
            elif remaining.get(used_key) != limit - used_value:
                errors.append(f"receipt budget remaining.{used_key} arithmetic is inconsistent")
        if isinstance(usage, dict):
            usage_bindings = (
                ("providerCallCount", "modelRequests"),
                ("toolCallCount", "toolCalls"),
                ("inputTokens", "inputTokens"),
                ("deliveredToolResultBytes", "toolResultBytes"),
            )
            for usage_key, used_key in usage_bindings:
                if usage.get(usage_key) != used.get(used_key):
                    errors.append(f"receipt usage.{usage_key} does not match budget used.{used_key}")

    errors.extend(_scan_payload(receipt))
    return sorted(set(errors))


def validate_exchange(
    task: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    lease: dict[str, Any] | None = None,
    context_view: dict[str, Any] | None = None,
    readiness: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    errors = verify_schema_snapshot()
    errors.extend(validate_task(task))
    errors.extend(validate_context_view(task, context_view))
    errors.extend(validate_readiness(task, readiness, now=now))
    readiness_state = readiness.get("state") if isinstance(readiness, dict) else None
    admitted_tiers = readiness.get("admittedRiskTiers") if isinstance(readiness, dict) else None
    if not isinstance(admitted_tiers, list) or task.get("riskTier") not in admitted_tiers:
        errors.append("CMMD readiness evidence does not admit the task risk tier")
    if task.get("riskTier") == "R0":
        if readiness_state not in {"live_smoke_ready", "production_acceptance_ready"}:
            errors.append("CMMD R0 requires live_smoke_ready evidence")
    elif task.get("riskTier") == "R1":
        if readiness_state != "production_acceptance_ready":
            errors.append("CMMD R1 requires production_acceptance_ready evidence")
    expected_lease_status = "consumed" if receipt is not None else "active"
    errors.extend(validate_lease(task, lease, expected_status=expected_lease_status, now=now))
    if receipt is not None:
        errors.extend(validate_receipt(task, receipt))
    return {
        "ok": not errors,
        "decision": "candidate_for_ceo_review" if not errors and receipt is not None else ("task_admissible" if not errors else "block"),
        "errors": sorted(set(errors)),
        "note": "Schema/contract success is not CEO acceptance.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CEO Flow <-> CMMD v2 exchange invariants")
    parser.add_argument("--task", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--lease", type=Path)
    parser.add_argument("--context-view", type=Path)
    parser.add_argument("--readiness-evidence", type=Path)
    parser.add_argument("--check-schemas", action="store_true", help="Only verify vendored CMMD schema hashes")
    args = parser.parse_args()
    if args.check_schemas:
        errors = verify_schema_snapshot()
        result = {"ok": not errors, "errors": errors}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    if args.task is None:
        parser.error("--task is required unless --check-schemas is used")
    task = read_json(args.task)
    receipt = read_json(args.receipt) if args.receipt else None
    lease = read_json(args.lease) if args.lease else None
    context_view = read_json(args.context_view) if args.context_view else None
    readiness = read_json(args.readiness_evidence) if args.readiness_evidence else None
    result = validate_exchange(task, receipt, lease, context_view, readiness)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
