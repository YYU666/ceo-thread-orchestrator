#!/usr/bin/env python3
"""Verify a bounded local source scope before optional current-source work."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

import atomic_state
import context_governor
import task_lifecycle_driver

MAX_REQUEST_BYTES = 16 * 1024
MAX_ANCHORS = 8
MAX_WRITE_PATHS = 16
FORBIDDEN_PARTS = {".git", ".codex-knowledge", "sessions", "credentials", "keychain"}


def bounded_path(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value or len(value) > 512 or "\\" in value or "://" in value:
        raise ValueError("invalid_source_path")
    relative = PurePosixPath(value)
    if not relative.parts or relative.is_absolute() or ".." in relative.parts or FORBIDDEN_PARTS.intersection(relative.parts):
        raise ValueError("source_path_out_of_scope")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("source_path_symlink")
    target = (root / value).resolve()
    if not target.is_relative_to(root):
        raise ValueError("source_path_escape")
    return target


def sha256_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(256 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def event_from_request(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("source_work_request_invalid")
    allowed_keys = {"taskId", "workspace", "scopeId", "taskGoal", "sourceRefs", "allowedWritePaths"}
    if set(request) != allowed_keys:
        raise ValueError("source_work_request_fields_invalid")
    for field in ("taskId", "scopeId", "taskGoal"):
        value = request[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 600:
            raise ValueError(f"source_work_{field}_invalid")
    raw_root = Path(request["workspace"])
    if not raw_root.is_absolute() or not raw_root.is_dir() or str(raw_root.resolve()) != str(raw_root):
        raise ValueError("source_work_workspace_not_canonical")
    refs = request["sourceRefs"]
    writes = request["allowedWritePaths"]
    if not isinstance(refs, list) or not 1 <= len(refs) <= MAX_ANCHORS:
        raise ValueError("source_work_anchor_count_invalid")
    if not isinstance(writes, list) or not 1 <= len(writes) <= MAX_WRITE_PATHS:
        raise ValueError("source_work_write_set_invalid")
    if len(writes) != len(set(str(item) for item in writes)):
        raise ValueError("source_work_duplicate_write_path")
    for path in writes:
        bounded_path(raw_root, path)
    verified_refs = []
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {"path", "sha256"}:
            raise ValueError("source_work_anchor_invalid")
        path = bounded_path(raw_root, ref["path"])
        if not path.is_file() or path.is_symlink():
            raise ValueError("source_work_anchor_not_regular_file")
        expected = ref["sha256"]
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("source_work_anchor_digest_invalid")
        if sha256_file(path) != expected:
            raise ValueError("source_work_anchor_changed")
        verified_refs.append(ref)
    scope = {"taskId": request["taskId"], "workspace": str(raw_root),
             "scopeId": request["scopeId"], "taskGoal": request["taskGoal"],
             "writePaths": writes, "sourceRefs": verified_refs}
    receipt = {"schema": "ceo_current_source_work_receipt_v1", **scope,
               "sourceSha256": atomic_state.state_sha256(scope)}
    return {"eventType": context_governor.CURRENT_SOURCE_WORK_EVENT,
            "taskId": request["taskId"], "workspace": str(raw_root),
            "scopeId": request["scopeId"], "allowedWritePaths": writes,
            "taskGoal": request["taskGoal"], "currentSourceWorkReceipt": receipt,
            "_currentSourceWorkCapability": context_governor.CURRENT_SOURCE_WORK_CAPABILITY}


def run(request: dict[str, Any], state_path: Path) -> dict[str, Any]:
    try:
        event = event_from_request(request)
        result = task_lifecycle_driver.run_persisted(
            event, state_path, {
                "inputTokenLimit": context_governor.DEFAULT_INPUT_TOKEN_LIMIT,
                "contextTokenLimit": context_governor.DEFAULT_CONTEXT_TOKEN_LIMIT,
                "cumulativeInputLimit": context_governor.DEFAULT_CUMULATIVE_INPUT_LIMIT,
                "contextBytesLimit": context_governor.DEFAULT_CONTEXT_BYTES_LIMIT,
                "takeoverTokenLimit": context_governor.DEFAULT_TAKEOVER_TOKEN_LIMIT,
            }, None)
        result.pop("state", None)
        result.pop("governor", None)
        return result
    except (ValueError, TypeError, OSError, atomic_state.StateDurabilityError,
            atomic_state.StatePermissionError, atomic_state.StateConflictError,
            context_governor.ControlPayloadError) as exc:
        return {"schema": "ceo_current_source_work_result_v1", "decision": "block",
                "reason": str(exc)[:180], "allowScopedSourceWork": False,
                "allowedWritePaths": [], "allowMemoryInjection": False,
                "allowProviderCalls": False, "programGoalBlocked": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = args.request.read_bytes()
        if len(raw) > MAX_REQUEST_BYTES:
            raise ValueError("source_work_request_too_large")
        request = json.loads(raw)
        result = run(request, args.state)
    except (ValueError, OSError, RecursionError) as exc:
        result = {"decision": "block", "reason": str(exc)[:180],
                  "allowScopedSourceWork": False, "allowMemoryInjection": False,
                  "allowProviderCalls": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("allowScopedSourceWork") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
