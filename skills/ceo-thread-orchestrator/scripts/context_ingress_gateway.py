#!/usr/bin/env python3
"""Validate compact model-bound ingress for a clean CEO takeover."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any


SCHEMA = "ceo_context_ingress_receipt_v1"
MAX_RETAINED_CONTEXT_TOKENS = 30_000
MAX_TOOL_OUTPUT_SUMMARY_TOKENS = 2_200
MAX_TOOL_OUTPUT_SERIALIZED_BYTES = 16 * 1024
MAX_NEW_FOCUSED_REFERENCES = 1
ALLOWED_HISTORY_MODES = {"none", "compact_wait_threads", "recovery_packet_only"}
HEX64 = re.compile(r"[0-9a-f]{64}")


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def receipt_sha256(receipt: dict[str, Any]) -> str:
    return canonical_sha256({key: value for key, value in receipt.items() if key != "receiptSha256"})


def safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def exact_nonnegative_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def validate(
    receipt: Any,
    *,
    task_id: str,
    previously_loaded_reference_sha256s: list[str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(receipt, dict):
        errors.append("context_ingress_receipt_required")
        receipt = {}
    if receipt.get("schema") != SCHEMA:
        errors.append("context_ingress_schema_invalid")
    if receipt.get("taskId") != task_id:
        errors.append("context_ingress_task_mismatch")
    retained = exact_nonnegative_int(receipt.get("retainedContextTokens"))
    if retained is None or retained > MAX_RETAINED_CONTEXT_TOKENS:
        errors.append("clean_takeover_retained_context_limit")
    if receipt.get("threadHistoryMode") not in ALLOWED_HISTORY_MODES:
        errors.append("full_thread_history_forbidden")
    if receipt.get("fullThreadHistoryLoaded") is not False:
        errors.append("full_thread_history_forbidden")
    references = receipt.get("newFocusedReferences")
    if not isinstance(references, list) or len(references) > MAX_NEW_FOCUSED_REFERENCES:
        errors.append("focused_reference_limit_exceeded")
        references = []
    previous = set(previously_loaded_reference_sha256s or [])
    added: list[str] = []
    for reference in references:
        if not isinstance(reference, dict):
            errors.append("focused_reference_invalid")
            continue
        digest = reference.get("sha256")
        if not safe_relative_path(reference.get("path")) or not isinstance(digest, str) or not HEX64.fullmatch(digest):
            errors.append("focused_reference_invalid")
            continue
        if digest in previous or digest in added:
            errors.append("duplicate_reference_sha_load")
            continue
        added.append(digest)
    outputs = receipt.get("toolOutputs")
    if not isinstance(outputs, list) or len(outputs) > 16:
        errors.append("tool_output_manifest_invalid")
        outputs = []
    for output in outputs:
        if not isinstance(output, dict):
            errors.append("tool_output_manifest_invalid")
            continue
        summary_tokens = exact_nonnegative_int(output.get("summaryTokens"))
        serialized_bytes = exact_nonnegative_int(output.get("serializedBytes"))
        artifact = output.get("artifactSha256")
        if output.get("rawBytesIncluded") is not False:
            errors.append("raw_tool_output_forbidden")
        if summary_tokens is None or summary_tokens > MAX_TOOL_OUTPUT_SUMMARY_TOKENS:
            errors.append("tool_output_summary_limit_exceeded")
        if serialized_bytes is None:
            errors.append("tool_output_manifest_invalid")
        elif serialized_bytes > MAX_TOOL_OUTPUT_SERIALIZED_BYTES and (
            not isinstance(artifact, str) or not HEX64.fullmatch(artifact)
        ):
            errors.append("oversized_tool_output_requires_artifact")
    expected_digest = receipt.get("receiptSha256")
    if not isinstance(expected_digest, str) or expected_digest != receipt_sha256(receipt):
        errors.append("context_ingress_receipt_digest_mismatch")
    return {
        "schema": "ceo_context_ingress_validation_v1",
        "ok": not errors,
        "decision": "allow" if not errors else "block",
        "reason": "clean_context_ingress_verified" if not errors else errors[0],
        "errors": errors,
        "retainedContextTokens": retained,
        "newReferenceSha256s": added if not errors else [],
        "updatedReferenceSha256s": sorted(previous | set(added)) if not errors else sorted(previous),
    }
