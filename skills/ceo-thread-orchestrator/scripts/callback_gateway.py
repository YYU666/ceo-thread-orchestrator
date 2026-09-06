#!/usr/bin/env python3
"""Fail-closed gateway for compact worker/reviewer callbacks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA = "ceo_compact_callback_v1"
ROUTING_RECEIPT_SCHEMA = "ceo_model_route_receipt_v1"
EVIDENCE_RECEIPT_SCHEMA = "ceo_verification_evidence_receipt_v1"
MAX_CALLBACK_SERIALIZED_BYTES = 16 * 1024
MAX_CALLBACK_ESTIMATED_TOKENS = 2_200
MAX_SUMMARY_BYTES = 2_000
MAX_ITEM_BYTES = 768
MAX_CHANGED_PATHS = 64
MAX_COMMANDS = 24
MAX_EVIDENCE_REFS = 48
MAX_RISKS = 24
ROUTING_RESULTS = {"verified", "inherited", "unknown", "mismatch", "unavailable"}
ROUTING_PROOF_SOURCES = {"codex_host", "external_harness_receipt", "unavailable"}
RISK_TIERS = {"low", "medium", "high"}
VERIFICATION_PROFILES = {"focused", "typecheck_build", "full"}
UNKNOWN_ROUTE_VALUES = {"unknown", "inherited"}


class _RoutingProofCapability:
    def __deepcopy__(self, memo: dict[int, Any]) -> "_RoutingProofCapability":
        return self


ROUTING_PROOF_CAPABILITY = _RoutingProofCapability()
EVIDENCE_PROOF_CAPABILITY = _RoutingProofCapability()
ALLOWED_KEYS = {
    "schema",
    "taskId",
    "status",
    "summary",
    "handoffRef",
    "artifactRef",
    "artifactSha256",
    "changedPaths",
    "commands",
    "evidenceRefs",
    "risks",
    "nextAction",
    "needsCeoDecision",
    "declaredTokenEstimate",
    "requestedModel",
    "requestedThinking",
    "actualModel",
    "actualThinking",
    "routingResult",
    "routingProofSource",
    "routingReceiptId",
    "riskTier",
    "verificationProfile",
    "ceoVerificationCount",
    "neutralReviewCount",
    "revisionCount",
    "processUpdateCount",
    "sliceId",
    "sliceBasisSha256",
    "callbackSequence",
    "priorCallbackSha256",
    "verificationEvidenceReceiptId",
}
VALID_STATUS = {"complete", "partial", "blocked", "failed", "review_ready"}
FORBIDDEN_KEYS = {
    "rawchat",
    "rawsession",
    "fullhistory",
    "fulllog",
    "completelog",
    "fullreport",
    "fulldesign",
    "designbody",
    "diffbody",
    "imagebase64",
    "base64",
    "credential",
    "credentials",
    "apikey",
    "sqlite",
}
FORBIDDEN_VALUE_RE = re.compile(
    r"(data:image/[a-z0-9.+-]+|;\s*base64\s*,|[A-Za-z0-9+/]{240,}={0,2})",
    re.IGNORECASE,
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compact_token_estimate(value: Any) -> int:
    payload = canonical_bytes(value)
    return (len(payload) + 2) // 3


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_bytes(value: str) -> int:
    return len(value.encode("utf-8"))


def relative_safe_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    return bool(normalized) and not path.is_absolute() and ".." not in path.parts


def forbidden_payload(value: Any) -> bool:
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
                if normalized in FORBIDDEN_KEYS:
                    return True
                stack.append(child)
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str) and FORBIDDEN_VALUE_RE.search(item):
            return True
    return False


def validate_string_list(
    callback: dict[str, Any], field: str, maximum: int, errors: list[str]
) -> list[str]:
    value = callback.get(field)
    if not isinstance(value, list):
        errors.append(f"callback.{field} must be a list")
        return []
    if len(value) > maximum:
        errors.append(f"callback.{field} exceeds item limit {maximum}")
    valid: list[str] = []
    for index, item in enumerate(value):
        if not nonempty_string(item):
            errors.append(f"callback.{field}[{index}] must be a non-empty string")
        elif string_bytes(item) > MAX_ITEM_BYTES:
            errors.append(f"callback.{field}[{index}] exceeds {MAX_ITEM_BYTES} bytes")
        else:
            valid.append(item)
    return valid


def routing_receipt_sha256(receipt: dict[str, Any]) -> str:
    return hashlib.sha256(
        canonical_bytes({key: value for key, value in receipt.items() if key != "receiptSha256"})
    ).hexdigest()


def evidence_receipt_sha256(receipt: dict[str, Any]) -> str:
    return hashlib.sha256(
        canonical_bytes({key: value for key, value in receipt.items() if key != "receiptSha256"})
    ).hexdigest()


def validate_evidence_receipt(
    callback: dict[str, Any], trusted_receipt: dict[str, Any] | None, proof_capability: Any
) -> tuple[bool, list[str]]:
    gaps: list[str] = []
    receipt_id = callback.get("verificationEvidenceReceiptId")
    if not isinstance(receipt_id, str) or not re.fullmatch(r"[0-9a-f]{64}", receipt_id):
        return False, ["verification_evidence_receipt_id_invalid"]
    if proof_capability is not EVIDENCE_PROOF_CAPABILITY or not isinstance(trusted_receipt, dict):
        return False, ["trusted_verification_evidence_unavailable"]
    expected = {
        "schema": EVIDENCE_RECEIPT_SCHEMA,
        "taskId": callback.get("taskId"),
        "sliceId": callback.get("sliceId"),
        "sliceBasisSha256": callback.get("sliceBasisSha256"),
        "verificationProfile": callback.get("verificationProfile"),
        "changedPaths": callback.get("changedPaths"),
        "commands": callback.get("commands"),
        "evidenceRefs": callback.get("evidenceRefs"),
    }
    trusted_digest = trusted_receipt.get("receiptSha256")
    if (
        any(trusted_receipt.get(key) != value for key, value in expected.items())
        or not isinstance(trusted_digest, str)
        or trusted_digest != evidence_receipt_sha256(trusted_receipt)
        or trusted_digest != receipt_id
    ):
        gaps.append("trusted_verification_evidence_mismatch")
    return not gaps, gaps


def validate_routing(
    callback: dict[str, Any],
    errors: list[str],
    *,
    trusted_receipt: dict[str, Any] | None,
    proof_capability: Any,
) -> tuple[bool, str, list[str]]:
    gaps: list[str] = []
    for field in (
        "requestedModel",
        "requestedThinking",
        "actualModel",
        "actualThinking",
        "routingResult",
        "routingProofSource",
    ):
        if not nonempty_string(callback.get(field)):
            errors.append(f"callback.{field} must be a non-empty string")
    result = callback.get("routingResult")
    source = callback.get("routingProofSource")
    receipt_id = callback.get("routingReceiptId")
    if result not in ROUTING_RESULTS:
        errors.append("callback.routingResult is invalid")
        return False, str(result or "invalid"), []
    if source not in ROUTING_PROOF_SOURCES:
        errors.append("callback.routingProofSource is invalid")
    if receipt_id is not None and (
        not isinstance(receipt_id, str) or not re.fullmatch(r"[0-9a-f]{64}", receipt_id)
    ):
        errors.append("callback.routingReceiptId must be lowercase 64-hex when present")

    requested_model = callback.get("requestedModel")
    requested_thinking = callback.get("requestedThinking")
    actual_model = callback.get("actualModel")
    actual_thinking = callback.get("actualThinking")
    if result == "verified":
        if source not in {"codex_host", "external_harness_receipt"} or receipt_id is None:
            errors.append("verified routing requires a content-addressed Host/Harness receipt")
        if actual_model in UNKNOWN_ROUTE_VALUES or actual_thinking in UNKNOWN_ROUTE_VALUES:
            errors.append("verified routing cannot claim unknown or inherited actual values")
        if requested_model != actual_model or requested_thinking != actual_thinking:
            errors.append("verified routing requested and actual model/thinking must match")
        if proof_capability is not ROUTING_PROOF_CAPABILITY or not isinstance(trusted_receipt, dict):
            gaps.append("trusted_routing_receipt_unavailable")
        else:
            expected = {
                "schema": ROUTING_RECEIPT_SCHEMA,
                "source": source,
                "taskId": callback.get("taskId"),
                "requestedModel": requested_model,
                "requestedThinking": requested_thinking,
                "actualModel": actual_model,
                "actualThinking": actual_thinking,
                "selectionSurface": trusted_receipt.get("selectionSurface"),
            }
            trusted_digest = trusted_receipt.get("receiptSha256")
            if (
                not nonempty_string(trusted_receipt.get("selectionSurface"))
                or any(trusted_receipt.get(key) != value for key, value in expected.items())
                or not isinstance(trusted_digest, str)
                or trusted_digest != routing_receipt_sha256(trusted_receipt)
                or receipt_id != trusted_digest
            ):
                gaps.append("trusted_routing_receipt_mismatch")
    elif result == "inherited":
        if requested_model != "inherit" or requested_thinking != "inherit":
            errors.append("inherited routing must be explicitly requested")
        if actual_model != "inherited" or actual_thinking != "inherited":
            errors.append("inherited routing must not invent concrete actual values")
        gaps.append("inherited_actual_route_unverified")
    elif result in {"unknown", "unavailable"}:
        if actual_model not in UNKNOWN_ROUTE_VALUES or actual_thinking not in UNKNOWN_ROUTE_VALUES:
            errors.append("unverified routing must report actual values as unknown/inherited")
        if source != "unavailable" or receipt_id is not None:
            errors.append("unverified routing cannot carry a fabricated proof receipt")
        gaps.append("actual_route_unverified")
    elif result == "mismatch":
        if requested_model == actual_model and requested_thinking == actual_thinking:
            errors.append("routing mismatch must identify a requested/actual difference")
        gaps.append("requested_actual_route_mismatch")
    return result == "verified" and not errors and not gaps, result, gaps


def validate_slice_governance(
    callback: dict[str, Any],
    changed_paths: list[str],
    commands: list[str],
    evidence_refs: list[str],
    errors: list[str],
    *,
    prior_slice: dict[str, Any] | None,
    expected_slice_id: str | None,
    expected_slice_basis_sha256: str | None,
    expected_task_id: str | None,
) -> tuple[list[str], bool]:
    gaps: list[str] = []
    risk = callback.get("riskTier")
    profile = callback.get("verificationProfile")
    slice_id = callback.get("sliceId")
    slice_basis = callback.get("sliceBasisSha256")
    sequence = callback.get("callbackSequence")
    prior_callback = callback.get("priorCallbackSha256")
    if risk not in RISK_TIERS:
        errors.append("callback.riskTier must be low, medium, or high")
    if profile not in VERIFICATION_PROFILES:
        errors.append("callback.verificationProfile must be focused, typecheck_build, or full")
    if not nonempty_string(slice_id):
        errors.append("callback.sliceId must be a non-empty string")
    if not isinstance(slice_basis, str) or not re.fullmatch(r"[0-9a-f]{64}", slice_basis):
        errors.append("callback.sliceBasisSha256 must be lowercase 64-hex")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        errors.append("callback.callbackSequence must be a positive integer")
    if prior_callback is not None and (
        not isinstance(prior_callback, str) or not re.fullmatch(r"[0-9a-f]{64}", prior_callback)
    ):
        errors.append("callback.priorCallbackSha256 must be lowercase 64-hex when present")
    if expected_slice_id is not None and slice_id != expected_slice_id:
        errors.append("callback.sliceId does not match the registered task slice")
    if expected_slice_basis_sha256 is not None and slice_basis != expected_slice_basis_sha256:
        errors.append("callback.sliceBasisSha256 does not match the registered task slice")
    if expected_task_id is not None and callback.get("taskId") != expected_task_id:
        errors.append("callback.taskId does not match the registered worker task")
    counts: dict[str, int] = {}
    for field in (
        "ceoVerificationCount",
        "neutralReviewCount",
        "revisionCount",
        "processUpdateCount",
    ):
        value = callback.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            errors.append(f"callback.{field} must be a non-negative integer")
        else:
            counts[field] = value
    if errors:
        return gaps, False

    if (
        expected_task_id is None
        or expected_slice_id is None
        or expected_slice_basis_sha256 is None
    ):
        gaps.append("callback_slice_registration_unavailable")

    if prior_slice is None:
        if sequence != 1 or prior_callback is not None:
            gaps.append("callback_slice_chain_must_start_at_one")
    else:
        if (
            prior_slice.get("taskId") != callback.get("taskId")
            or prior_slice.get("sliceId") != slice_id
            or prior_slice.get("sliceBasisSha256") != slice_basis
        ):
            gaps.append("callback_slice_ledger_identity_mismatch")
        if sequence != prior_slice.get("callbackSequence", 0) + 1:
            gaps.append("callback_slice_sequence_invalid")
        if prior_callback != prior_slice.get("lastCallbackSha256"):
            gaps.append("callback_slice_chain_digest_mismatch")
        prior_counts = prior_slice.get("counts")
        if not isinstance(prior_counts, dict):
            gaps.append("callback_slice_prior_counts_invalid")
        elif any(counts[field] < prior_counts.get(field, 0) for field in counts):
            gaps.append("callback_slice_counts_regressed")

    expected_profile = {"low": "focused", "medium": "typecheck_build", "high": "full"}[risk]
    if profile != expected_profile:
        gaps.append(f"{risk}_risk_requires_{expected_profile}_verification")
    if risk == "low" and len(changed_paths) > 2:
        gaps.append("low_risk_slice_exceeds_two_changed_paths")
    evidence_changed = (
        isinstance(prior_slice, dict)
        and isinstance(prior_slice.get("verificationBasis"), str)
        and prior_slice["verificationBasis"] != verification_basis(callback)
    )
    if risk == "low" and counts["neutralReviewCount"] != 0 and not evidence_changed:
        gaps.append("low_risk_slice_neutral_review_over_budget")
    if risk == "high" and counts["neutralReviewCount"] < 1:
        gaps.append("high_risk_slice_requires_exactly_one_neutral_review")
    if counts["ceoVerificationCount"] < 1:
        gaps.append("slice_requires_exactly_one_ceo_verification")
    if not commands:
        gaps.append("slice_verification_commands_required")
    if not evidence_refs:
        gaps.append("slice_evidence_refs_required")
    elif any(not re.fullmatch(r"[^#]+#sha256=[0-9a-f]{64}", ref) for ref in evidence_refs):
        gaps.append("slice_evidence_refs_must_be_content_addressed")

    budget_exhausted = False
    for field, maximum in (
        ("ceoVerificationCount", 1),
        ("neutralReviewCount", 1),
        ("revisionCount", 1),
        ("processUpdateCount", 3),
    ):
        prior_count = (prior_slice or {}).get("counts", {}).get(field, 0)
        justified_recheck = evidence_changed and counts[field] <= max(maximum, prior_count + 1)
        if counts[field] > maximum and not justified_recheck:
            gaps.append(f"{field}_budget_exceeded")
            budget_exhausted = True
    return gaps, budget_exhausted


def verification_basis(callback: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes({
        key: callback.get(key) for key in ("changedPaths", "commands", "evidenceRefs")
    })).hexdigest()


def block(reason: str, errors: list[str], *, serialized_bytes: int, estimated_tokens: int) -> dict[str, Any]:
    return {
        "schema": "ceo_callback_gateway_receipt_v1",
        "ok": False,
        "decision": "block",
        "reason": reason,
        "allowCallbackInjection": False,
        "allowCandidateAcceptance": False,
        "modelRouteVerified": False,
        "nextAction": "store_full_detail_as_artifact_then_emit_compact_callback",
        "serializedBytes": serialized_bytes,
        "estimatedTokens": estimated_tokens,
        "errors": errors,
    }


def validate(
    callback: Any,
    *,
    trusted_routing_receipt: dict[str, Any] | None = None,
    routing_proof_capability: Any = None,
    trusted_evidence_receipt: dict[str, Any] | None = None,
    evidence_proof_capability: Any = None,
    slice_ledger: dict[str, Any] | None = None,
    expected_task_id: str | None = None,
    expected_slice_id: str | None = None,
    expected_slice_basis_sha256: str | None = None,
    native_codex_review: bool = False,
    exact_model_required: bool = True,
) -> dict[str, Any]:
    if not isinstance(callback, dict):
        return block("callback_schema_invalid", ["callback must be an object"], serialized_bytes=0, estimated_tokens=0)
    try:
        payload = canonical_bytes(callback)
    except (TypeError, ValueError, RecursionError):
        return block("callback_schema_invalid", ["callback must be finite JSON"], serialized_bytes=0, estimated_tokens=0)
    serialized_bytes = len(payload)
    estimated_tokens = compact_token_estimate(callback)
    errors: list[str] = []
    unknown = sorted(set(callback) - ALLOWED_KEYS)
    if unknown:
        errors.append("callback contains unknown fields: " + ", ".join(unknown))
    if callback.get("schema") != SCHEMA:
        errors.append(f"callback.schema must be {SCHEMA}")
    for field in ("taskId", "status", "summary", "nextAction"):
        if not nonempty_string(callback.get(field)):
            errors.append(f"callback.{field} must be a non-empty string")
    if callback.get("status") not in VALID_STATUS:
        errors.append("callback.status is invalid")
    summary = callback.get("summary")
    if isinstance(summary, str) and string_bytes(summary) > MAX_SUMMARY_BYTES:
        errors.append(f"callback.summary exceeds {MAX_SUMMARY_BYTES} bytes")
    declared = callback.get("declaredTokenEstimate")
    if isinstance(declared, bool) or not isinstance(declared, int) or declared <= 0:
        errors.append("callback.declaredTokenEstimate must be a positive integer")
    elif declared > MAX_CALLBACK_ESTIMATED_TOKENS:
        errors.append("callback declared token estimate exceeds hard limit")
    if not isinstance(callback.get("needsCeoDecision"), bool):
        errors.append("callback.needsCeoDecision must be boolean")
    changed = validate_string_list(callback, "changedPaths", MAX_CHANGED_PATHS, errors)
    commands = validate_string_list(callback, "commands", MAX_COMMANDS, errors)
    evidence_refs = validate_string_list(callback, "evidenceRefs", MAX_EVIDENCE_REFS, errors)
    validate_string_list(callback, "risks", MAX_RISKS, errors)
    for index, path in enumerate(changed):
        if not relative_safe_path(path):
            errors.append(f"callback.changedPaths[{index}] must be a safe project-relative path")
    for field in ("handoffRef", "artifactRef"):
        value = callback.get(field)
        if value is not None and (not nonempty_string(value) or string_bytes(value) > MAX_ITEM_BYTES):
            errors.append(f"callback.{field} must be a bounded non-empty string when present")
    artifact_sha = callback.get("artifactSha256")
    if artifact_sha is not None and (
        not isinstance(artifact_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", artifact_sha)
    ):
        errors.append("callback.artifactSha256 must be lowercase 64-hex when present")
    if callback.get("artifactRef") is not None and artifact_sha is None:
        errors.append("callback artifactRef requires artifactSha256")
    if forbidden_payload(callback):
        errors.append("callback contains forbidden raw/full/base64/credential payload")
    if serialized_bytes > MAX_CALLBACK_SERIALIZED_BYTES:
        errors.append(f"callback exceeds {MAX_CALLBACK_SERIALIZED_BYTES} serialized bytes")
    if estimated_tokens > MAX_CALLBACK_ESTIMATED_TOKENS:
        errors.append(f"callback conservative estimate exceeds {MAX_CALLBACK_ESTIMATED_TOKENS} tokens")
    if isinstance(declared, int) and not isinstance(declared, bool) and declared < estimated_tokens:
        errors.append("callback declared token estimate understates conservative estimate")
    model_route_verified, routing_result, routing_gaps = validate_routing(
        callback,
        errors,
        trusted_receipt=trusted_routing_receipt,
        proof_capability=routing_proof_capability,
    )
    ledger_key = f"{callback.get('taskId')}::{callback.get('sliceId')}"
    prior_slice = slice_ledger.get(ledger_key) if isinstance(slice_ledger, dict) else None
    acceptance_gaps, slice_budget_exhausted = validate_slice_governance(
        callback,
        changed,
        commands,
        evidence_refs,
        errors,
        prior_slice=prior_slice if isinstance(prior_slice, dict) else None,
        expected_slice_id=expected_slice_id,
        expected_slice_basis_sha256=expected_slice_basis_sha256,
        expected_task_id=expected_task_id,
    )
    evidence_verified, evidence_gaps = validate_evidence_receipt(
        callback, trusted_evidence_receipt, evidence_proof_capability
    )
    # Only an explicitly selected local Codex review can tolerate missing
    # route telemetry. Mismatches and claimed-but-unproven receipts stay closed.
    observational_route = (
        native_codex_review is True
        and exact_model_required is False
        and routing_result in {"unknown", "inherited"}
        and callback.get("routingProofSource") == "unavailable"
        and callback.get("routingReceiptId") is None
    )
    route_acceptable = model_route_verified or observational_route
    acceptance_gaps = ([] if observational_route else routing_gaps) + evidence_gaps + acceptance_gaps
    if errors:
        reason = (
            "callback_payload_exceeded"
            if serialized_bytes > MAX_CALLBACK_SERIALIZED_BYTES
            or estimated_tokens > MAX_CALLBACK_ESTIMATED_TOKENS
            or (isinstance(summary, str) and string_bytes(summary) > MAX_SUMMARY_BYTES)
            else "callback_schema_invalid"
        )
        return block(reason, errors, serialized_bytes=serialized_bytes, estimated_tokens=estimated_tokens)
    digest = hashlib.sha256(payload).hexdigest()
    counts = {
        field: callback[field]
        for field in (
            "ceoVerificationCount",
            "neutralReviewCount",
            "revisionCount",
            "processUpdateCount",
        )
    }
    slice_ledger_entry = {
        "taskId": callback["taskId"],
        "sliceId": callback["sliceId"],
        "sliceBasisSha256": callback["sliceBasisSha256"],
        "callbackSequence": callback["callbackSequence"],
        "lastCallbackSha256": digest,
        "counts": counts,
        "verificationBasis": verification_basis(callback),
    }
    slice_ledger_advance_allowed = not any(
        gap.startswith("callback_slice_") for gap in acceptance_gaps
    )
    return {
        "schema": "ceo_callback_gateway_receipt_v1",
        "ok": True,
        "decision": "allow",
        "reason": "compact_callback_verified",
        "allowCallbackInjection": True,
        "allowCandidateAcceptance": (
            callback.get("status") in {"complete", "review_ready"}
            and route_acceptable
            and evidence_verified
            and not acceptance_gaps
        ),
        "modelRouteVerified": model_route_verified,
        "modelRouteObservational": observational_route,
        "verificationEvidenceVerified": evidence_verified,
        "routingResult": routing_result,
        "acceptanceGaps": acceptance_gaps,
        "sliceBudgetExhausted": slice_budget_exhausted,
        "sliceLedgerKey": ledger_key,
        "sliceLedgerEntry": slice_ledger_entry,
        "sliceLedgerAdvanceAllowed": slice_ledger_advance_allowed,
        "nextAction": (
            "shrink_slice_or_change_approach"
            if slice_budget_exhausted
            else "complete_risk_tier_evidence_before_acceptance"
            if acceptance_gaps or not route_acceptable
            else "ceo_inspect_compact_evidence"
        ),
        "callbackSha256": digest,
        "serializedBytes": serialized_bytes,
        "estimatedTokens": estimated_tokens,
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a compact CEO Flow callback.")
    parser.add_argument("callback", type=Path)
    parser.add_argument("--native-review-workspace", type=Path,
                        help="Review local Codex evidence without a Desktop connection")
    parser.add_argument("--task-id")
    parser.add_argument("--slice-id")
    parser.add_argument("--slice-basis")
    parser.add_argument("--exact-model-required", action="store_true")
    args = parser.parse_args()
    try:
        raw = args.callback.read_bytes()
        if len(raw) > MAX_CALLBACK_SERIALIZED_BYTES:
            result = block(
                "callback_payload_exceeded",
                [f"callback exceeds {MAX_CALLBACK_SERIALIZED_BYTES} input bytes"],
                serialized_bytes=len(raw),
                estimated_tokens=(len(raw) + 2) // 3,
            )
        else:
            callback = json.loads(raw.decode("utf-8"))
            if args.native_review_workspace:
                from codex_app_server_executor import CodexAppServerExecutor
                evidence = CodexAppServerExecutor.capture_verification_evidence_receipt(
                    callback, {"workspace": str(args.native_review_workspace)}
                ) if isinstance(callback, dict) else None
                result = validate(
                    callback,
                    native_codex_review=True,
                    exact_model_required=args.exact_model_required,
                    trusted_evidence_receipt=evidence,
                    evidence_proof_capability=EVIDENCE_PROOF_CAPABILITY,
                    expected_task_id=args.task_id,
                    expected_slice_id=args.slice_id,
                    expected_slice_basis_sha256=args.slice_basis,
                )
            else:
                result = validate(callback)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result = block("callback_unreadable", [str(exc)], serialized_bytes=0, estimated_tokens=0)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
