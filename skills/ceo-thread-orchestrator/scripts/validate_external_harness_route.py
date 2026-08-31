#!/usr/bin/env python3
"""Validate an external coding Harness route and its dispatch receipt.

The contract is provider-neutral. Concrete model names, selectors, pricing, and
fallbacks come from the adapter and project-policy inputs, never this module.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


CAPABILITY_CLASSES = {"fast", "balanced", "frontier"}
SELECTION_SURFACES = {"web_session", "cli_profile", "cli_patch", "unsupported"}
STATUS_VALUES = {"available", "unavailable"}
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$"
)


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_plain_dict(value: Any) -> bool:
    return isinstance(value, dict)


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def strict_rfc3339(value: Any) -> bool:
    if not is_nonempty_string(value) or not RFC3339_RE.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def require_fields(mapping: Any, fields: tuple[str, ...], prefix: str, errors: list[str]) -> None:
    if not is_plain_dict(mapping):
        errors.append(f"{prefix} must be an object")
        return
    for field in fields:
        if field not in mapping:
            errors.append(f"missing required field: {prefix}.{field}")


def validate_adapter(adapter: Any) -> list[str]:
    errors: list[str] = []
    require_fields(
        adapter,
        (
            "schema",
            "adapterPolicyId",
            "mappingSource",
            "routes",
            "globalDefaultModel",
            "retryPolicy",
            "pricing",
        ),
        "adapter",
        errors,
    )
    if errors:
        return errors
    if adapter["schema"] != "external_harness_adapter_v1":
        errors.append("adapter.schema must be external_harness_adapter_v1")
    for field in ("adapterPolicyId", "mappingSource"):
        if not is_nonempty_string(adapter.get(field)):
            errors.append(f"adapter.{field} must be a non-empty string")
    routes = adapter.get("routes")
    if not is_plain_dict(routes):
        errors.append("adapter.routes must be an object")
        return errors
    missing_classes = CAPABILITY_CLASSES - set(routes)
    if missing_classes:
        errors.append("adapter.routes missing classes: " + ", ".join(sorted(missing_classes)))
    for capability in sorted(CAPABILITY_CLASSES & set(routes)):
        route = routes[capability]
        prefix = f"adapter.routes.{capability}"
        require_fields(
            route,
            ("selectionSurface", "selector", "model", "reasoning", "identityProofMethods"),
            prefix,
            errors,
        )
        if not is_plain_dict(route):
            continue
        surface = route.get("selectionSurface")
        selector = route.get("selector")
        if surface not in SELECTION_SURFACES:
            errors.append(f"{prefix}.selectionSurface is unsupported")
        if not is_plain_dict(selector):
            errors.append(f"{prefix}.selector must be an object")
            selector = {}
        if not is_nonempty_string(route.get("model")):
            errors.append(f"{prefix}.model must be a non-empty adapter-policy value")
        if not is_nonempty_string(route.get("reasoning")):
            errors.append(f"{prefix}.reasoning must be a non-empty adapter-policy value")
        methods = route.get("identityProofMethods")
        if not isinstance(methods, list) or not methods or not all(is_nonempty_string(v) for v in methods):
            errors.append(f"{prefix}.identityProofMethods must be a non-empty string list")
        if surface == "web_session" and not is_nonempty_string(selector.get("modelSelector")):
            errors.append(f"{prefix}.selector.modelSelector is required for web_session")
        if surface == "cli_profile" and not is_nonempty_string(selector.get("profile")):
            errors.append(f"{prefix}.selector.profile is required for cli_profile")
        if surface == "cli_patch" and not any(
            is_nonempty_string(selector.get(field)) for field in ("patch", "config")
        ):
            errors.append(f"{prefix}.selector.patch or config is required for cli_patch")
        if surface in {"cli_profile", "cli_patch"} and route.get("directModelOverride") is False:
            forbidden = {"model", "--model", "modelOverride"} & set(selector)
            if forbidden:
                errors.append(f"{prefix}.selector uses unsupported direct model override")

    retry = adapter.get("retryPolicy")
    require_fields(retry, ("defaultRetries", "authorizedMaxRetries"), "adapter.retryPolicy", errors)
    if is_plain_dict(retry):
        for field in ("defaultRetries", "authorizedMaxRetries"):
            value = retry.get(field)
            if not is_int(value) or value < 0:
                errors.append(f"adapter.retryPolicy.{field} must be a non-negative integer")
        if is_int(retry.get("defaultRetries")) and retry["defaultRetries"] != 0:
            errors.append("adapter.retryPolicy.defaultRetries must be 0")
    pricing = adapter.get("pricing")
    require_fields(pricing, ("status",), "adapter.pricing", errors)
    if is_plain_dict(pricing):
        status = pricing.get("status")
        if status not in STATUS_VALUES:
            errors.append("adapter.pricing.status must be available or unavailable")
        elif status == "available":
            for field in ("sourceRef", "observedAt", "inputs"):
                if field not in pricing:
                    errors.append(f"missing required field: adapter.pricing.{field}")
            if not is_nonempty_string(pricing.get("sourceRef")):
                errors.append("adapter.pricing.sourceRef must be non-empty")
            if not strict_rfc3339(pricing.get("observedAt")):
                errors.append("adapter.pricing.observedAt must be strict RFC3339")
            if not is_plain_dict(pricing.get("inputs")) or not pricing.get("inputs"):
                errors.append("adapter.pricing.inputs must be a non-empty source-backed object")
    return errors


def route_for(adapter: dict[str, Any], dispatch: Any, errors: list[str]) -> dict[str, Any] | None:
    require_fields(
        dispatch,
        (
            "schema",
            "dispatchId",
            "adapterPolicyId",
            "adapterPolicyDigest",
            "requestedCapabilityClass",
            "requestedModel",
            "requestedReasoning",
            "selectionSurface",
            "selector",
            "explicitRoute",
            "allowGlobalDefaultInheritance",
            "retryCount",
            "guard",
            "fallback",
            "ceoInvariant",
        ),
        "dispatch",
        errors,
    )
    if not is_plain_dict(dispatch):
        return None
    if dispatch.get("schema") != "external_harness_dispatch_v1":
        errors.append("dispatch.schema must be external_harness_dispatch_v1")
    if dispatch.get("adapterPolicyId") != adapter.get("adapterPolicyId"):
        errors.append("dispatch.adapterPolicyId does not match adapter")
    if dispatch.get("adapterPolicyDigest") != canonical_sha256(adapter):
        errors.append("dispatch.adapterPolicyDigest does not match adapter bytes")
    capability = dispatch.get("requestedCapabilityClass")
    if capability not in CAPABILITY_CLASSES:
        errors.append("dispatch.requestedCapabilityClass must be fast, balanced, or frontier")
        return None
    route = adapter.get("routes", {}).get(capability)
    if not is_plain_dict(route):
        errors.append("requested capability has no adapter route")
        return None
    for dispatch_field, route_field in (
        ("requestedModel", "model"),
        ("requestedReasoning", "reasoning"),
        ("selectionSurface", "selectionSurface"),
        ("selector", "selector"),
    ):
        if dispatch.get(dispatch_field) != route.get(route_field):
            errors.append(f"dispatch.{dispatch_field} does not match the resolved adapter route")
    if dispatch.get("explicitRoute") is not True:
        errors.append("dispatch.explicitRoute must be true for auto-class routing")
    if dispatch.get("allowGlobalDefaultInheritance") is not False:
        errors.append("explicit external Harness routing must forbid global-default inheritance")

    retry_count = dispatch.get("retryCount")
    retry_policy = adapter.get("retryPolicy", {})
    if not is_int(retry_count) or retry_count < 0:
        errors.append("dispatch.retryCount must be a non-negative integer")
    elif retry_count > 0:
        maximum = retry_policy.get("authorizedMaxRetries", 0)
        authorization = dispatch.get("retryAuthorization")
        if not is_int(maximum) or retry_count > maximum or not is_nonempty_string(authorization):
            errors.append("dispatch retry exceeds explicit adapter/project policy authorization")

    validate_guard(dispatch.get("guard"), errors)
    validate_fallback_policy(dispatch.get("fallback"), errors)
    validate_ceo_invariant(dispatch.get("ceoInvariant"), "dispatch.ceoInvariant", errors)
    return route


def validate_guard(guard: Any, errors: list[str]) -> None:
    require_fields(
        guard,
        (
            "allowedTools",
            "exactWriteSet",
            "allowedCommands",
            "isolatedWorkspace",
            "independentCodexReviewRequired",
        ),
        "dispatch.guard",
        errors,
    )
    if not is_plain_dict(guard):
        return
    for field in ("allowedTools", "exactWriteSet", "allowedCommands"):
        value = guard.get(field)
        if not isinstance(value, list) or not all(is_nonempty_string(item) for item in value):
            errors.append(f"dispatch.guard.{field} must be a string list")
    if not isinstance(guard.get("isolatedWorkspace"), bool):
        errors.append("dispatch.guard.isolatedWorkspace must be boolean")
    if guard.get("independentCodexReviewRequired") is not True:
        errors.append("external Harness dispatch requires independent Codex review")


def validate_fallback_policy(fallback: Any, errors: list[str]) -> None:
    require_fields(fallback, ("declared", "routeId", "owner"), "dispatch.fallback", errors)
    if not is_plain_dict(fallback):
        return
    if fallback.get("declared") is not True:
        errors.append("dispatch.fallback.declared must be true")
    for field in ("routeId", "owner"):
        if not is_nonempty_string(fallback.get(field)):
            errors.append(f"dispatch.fallback.{field} must be a non-empty string")


def validate_ceo_invariant(value: Any, prefix: str, errors: list[str]) -> None:
    require_fields(value, ("model", "reasoning", "permissionsDigest"), prefix, errors)
    if is_plain_dict(value):
        for field in ("model", "reasoning", "permissionsDigest"):
            if not is_nonempty_string(value.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty opaque value")


def validate_availability_record(
    value: Any,
    prefix: str,
    available_fields: tuple[str, ...],
    errors: list[str],
) -> None:
    require_fields(value, ("status",), prefix, errors)
    if not is_plain_dict(value):
        return
    status = value.get("status")
    if status not in STATUS_VALUES:
        errors.append(f"{prefix}.status must be available or unavailable")
        return
    if status == "unavailable":
        fabricated = [field for field in available_fields if value.get(field) is not None]
        if fabricated:
            errors.append(f"{prefix} unavailable fields must be null or absent: {', '.join(fabricated)}")


def validate_usage(value: Any, errors: list[str]) -> None:
    fields = ("inputTokens", "outputTokens", "cacheTokens", "reasoningTokens", "totalTokens")
    validate_availability_record(value, "receipt.usage", fields, errors)
    if not is_plain_dict(value) or value.get("status") != "available":
        return
    for field in fields:
        token_count = value.get(field)
        if not is_int(token_count) or token_count < 0:
            errors.append(f"receipt.usage.{field} must be a non-negative integer")
    if all(is_int(value.get(field)) for field in fields):
        expected_total = value["inputTokens"] + value["outputTokens"] + value["reasoningTokens"]
        if value["totalTokens"] != expected_total:
            errors.append("receipt.usage.totalTokens must equal input + output + reasoning tokens")
        if value["cacheTokens"] > value["inputTokens"]:
            errors.append("receipt.usage.cacheTokens cannot exceed inputTokens")


def validate_elapsed(value: Any, errors: list[str]) -> None:
    validate_availability_record(value, "receipt.elapsed", ("milliseconds",), errors)
    if is_plain_dict(value) and value.get("status") == "available":
        milliseconds = value.get("milliseconds")
        if not is_int(milliseconds) or milliseconds < 0:
            errors.append("receipt.elapsed.milliseconds must be a non-negative integer")


def validate_cost(value: Any, adapter: dict[str, Any], errors: list[str]) -> None:
    fields = ("amount", "currency", "priceSourceRef", "priceObservedAt", "pricingPolicyDigest")
    validate_availability_record(value, "receipt.cost", fields, errors)
    if not is_plain_dict(value) or value.get("status") != "available":
        return
    pricing = adapter.get("pricing") if is_plain_dict(adapter.get("pricing")) else {}
    if pricing.get("status") != "available":
        errors.append("receipt.cost cannot be available without adapter/project pricing policy")
        return
    amount = value.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
        errors.append("receipt.cost.amount must be a non-negative number")
    for field in ("currency", "priceSourceRef"):
        if not is_nonempty_string(value.get(field)):
            errors.append(f"receipt.cost.{field} must be source-backed when cost is available")
    if not strict_rfc3339(value.get("priceObservedAt")):
        errors.append("receipt.cost.priceObservedAt must be strict RFC3339")
    if value.get("priceSourceRef") != pricing.get("sourceRef"):
        errors.append("receipt.cost.priceSourceRef does not match adapter/project pricing policy")
    if value.get("priceObservedAt") != pricing.get("observedAt"):
        errors.append("receipt.cost.priceObservedAt does not match adapter/project pricing policy")
    if value.get("pricingPolicyDigest") != canonical_sha256(pricing):
        errors.append("receipt.cost.pricingPolicyDigest does not match adapter/project pricing policy")


def normalized_path(value: str) -> str | None:
    candidate = value.replace("\\", "/")
    path = PurePosixPath(candidate)
    if path.is_absolute() or ".." in path.parts or candidate in {"", "."}:
        return None
    return candidate.lstrip("./")


def path_allowed(path: str, patterns: list[str]) -> bool:
    normalized = normalized_path(path)
    if normalized is None:
        return False
    for pattern in patterns:
        clean_pattern = pattern.replace("\\", "/").lstrip("./")
        if clean_pattern.endswith("/**") and normalized.startswith(clean_pattern[:-3].rstrip("/") + "/"):
            return True
        if fnmatch.fnmatchcase(normalized, clean_pattern) or PurePosixPath(normalized).match(clean_pattern):
            return True
    return False


def validate_fallback_receipt(receipt: Any, dispatch: dict[str, Any]) -> tuple[bool, list[str]]:
    if receipt is None:
        return False, []
    errors: list[str] = []
    require_fields(
        receipt,
        ("invoked", "reason", "routeId", "receiptId", "owner", "evidenceRef"),
        "receipt.fallbackReceipt",
        errors,
    )
    if not is_plain_dict(receipt):
        return False, errors
    if receipt.get("invoked") is not True:
        errors.append("receipt.fallbackReceipt.invoked must be true")
    if receipt.get("reason") != "model_route_unavailable":
        errors.append("receipt.fallbackReceipt.reason must be model_route_unavailable")
    if receipt.get("routeId") != dispatch.get("fallback", {}).get("routeId"):
        errors.append("receipt.fallbackReceipt.routeId does not match declared fallback")
    if not is_nonempty_string(receipt.get("receiptId")):
        errors.append("receipt.fallbackReceipt.receiptId must be non-empty")
    if receipt.get("owner") != dispatch.get("fallback", {}).get("owner"):
        errors.append("receipt.fallbackReceipt.owner does not match declared fallback owner")
    if not is_nonempty_string(receipt.get("evidenceRef")):
        errors.append("receipt.fallbackReceipt.evidenceRef must be non-empty")
    return not errors, errors


def validate_reasoning_policy(
    receipt: dict[str, Any], expected: Any, prefix: str
) -> list[str]:
    """Validate an explicit effort or a proved provider-default request policy."""
    errors: list[str] = []
    if receipt.get("requestedReasoning") != expected:
        errors.append(f"{prefix}.requestedReasoning does not match the resolved route")
    if expected != "provider_default":
        if receipt.get("actualReasoning") != expected:
            errors.append(f"{prefix}.actualReasoning does not match the resolved route")
        return errors

    proof = receipt.get("reasoningPolicyProof")
    require_fields(
        proof,
        (
            "status",
            "method",
            "requestedReasoning",
            "defaultPolicyApplied",
            "concreteEffortKnown",
        ),
        f"{prefix}.reasoningPolicyProof",
        errors,
    )
    if not is_plain_dict(proof):
        return errors
    if proof.get("status") != "verified":
        errors.append(f"{prefix}.reasoningPolicyProof.status must be verified")
    if proof.get("requestedReasoning") != "provider_default":
        errors.append(f"{prefix}.reasoningPolicyProof did not bind provider_default")
    if proof.get("defaultPolicyApplied") is not True:
        errors.append(f"{prefix}.reasoningPolicyProof did not prove default policy application")

    method = proof.get("method")
    actual = receipt.get("actualReasoning")
    if method == "request_header_reasoning_effort_omitted":
        if proof.get("concreteEffortKnown") is not False or actual != "unavailable":
            errors.append(
                f"{prefix}.reasoningPolicyProof omission must preserve unknown actual reasoning"
            )
        if "actualReasoning" in proof:
            errors.append(
                f"{prefix}.reasoningPolicyProof must not invent a concrete default effort"
            )
    elif method == "request_header_adapter_default_reasoning_effort":
        if proof.get("concreteEffortKnown") is not True:
            errors.append(
                f"{prefix}.reasoningPolicyProof materialized default must know the concrete effort"
            )
        if proof.get("adapterDefaultField") != "reasoningEffort":
            errors.append(
                f"{prefix}.reasoningPolicyProof did not bind the adapter default marker"
            )
        if not is_nonempty_string(actual) or actual == "unavailable":
            errors.append(
                f"{prefix}.reasoningPolicyProof materialized default lacks actual reasoning"
            )
        if proof.get("actualReasoning") != actual:
            errors.append(
                f"{prefix}.reasoningPolicyProof actual reasoning does not match the receipt"
            )
    else:
        errors.append(f"{prefix}.reasoningPolicyProof.method is unsupported")
    return errors


def evaluate(adapter: Any, dispatch: Any, receipt: Any) -> dict[str, Any]:
    contract_errors = validate_adapter(adapter)
    route = route_for(adapter if is_plain_dict(adapter) else {}, dispatch, contract_errors)
    if not is_plain_dict(receipt):
        contract_errors.append("receipt must be an object")
        receipt = {}
    if not is_plain_dict(dispatch):
        dispatch = {}

    require_fields(
        receipt,
        (
            "schema",
            "dispatchId",
            "adapterPolicyId",
            "adapterPolicyDigest",
            "requestedCapabilityClass",
            "requestedModel",
            "actualModel",
            "requestedReasoning",
            "actualReasoning",
            "selectionSurface",
            "appliedSelector",
            "routeApplied",
            "routeVerified",
            "globalDefaultInherited",
            "modelIdentityProof",
            "usage",
            "elapsed",
            "cost",
            "processExitCode",
            "cliExit",
            "taskCompleted",
            "stopReason",
            "taskSuccess",
            "timedOut",
            "turns",
            "modelCalls",
            "toolPolicyCompliant",
            "changedPaths",
            "commandsExecuted",
            "writeSetCompliant",
            "commandGuardCompliant",
            "diffEvidence",
            "tests",
            "independentReview",
            "retryCount",
            "ceoInvariantAfter",
        ),
        "receipt",
        contract_errors,
    )
    if receipt.get("schema") != "external_harness_receipt_v1":
        contract_errors.append("receipt.schema must be external_harness_receipt_v1")
    for field in ("dispatchId", "adapterPolicyId", "adapterPolicyDigest", "requestedCapabilityClass"):
        if receipt.get(field) != dispatch.get(field):
            contract_errors.append(f"receipt.{field} does not match dispatch")
    validate_usage(receipt.get("usage"), contract_errors)
    validate_elapsed(receipt.get("elapsed"), contract_errors)
    validate_cost(receipt.get("cost"), adapter if is_plain_dict(adapter) else {}, contract_errors)
    for field in ("processExitCode", "cliExit"):
        value = receipt.get(field)
        if not is_int(value) or value not in {0, 1, 2, 124, 125, 130, 143}:
            contract_errors.append(
                f"receipt.{field} must be one of 0, 1, 2, 124, 125, 130, or 143"
            )
    if receipt.get("processExitCode") != receipt.get("cliExit"):
        contract_errors.append("receipt.cliExit must equal the caller-observed processExitCode")
    if not isinstance(receipt.get("taskCompleted"), bool):
        contract_errors.append("receipt.taskCompleted must be boolean")
    if not is_nonempty_string(receipt.get("stopReason")):
        contract_errors.append("receipt.stopReason must be a non-empty string")
    if not isinstance(receipt.get("taskSuccess"), bool):
        contract_errors.append("receipt.taskSuccess must be boolean")
    if receipt.get("taskCompleted") != receipt.get("taskSuccess"):
        contract_errors.append("receipt.taskCompleted must equal receipt.taskSuccess")
    if not isinstance(receipt.get("timedOut"), bool):
        contract_errors.append("receipt.timedOut must be boolean")
    for field in ("turns", "modelCalls"):
        value = receipt.get(field)
        if not is_int(value) or value < 0:
            contract_errors.append(f"receipt.{field} must be a non-negative integer")
    if receipt.get("turns") != receipt.get("modelCalls"):
        contract_errors.append("receipt.turns must equal receipt.modelCalls for headless model-step budgets")
    if not isinstance(receipt.get("toolPolicyCompliant"), bool):
        contract_errors.append("receipt.toolPolicyCompliant must be boolean")
    for field in ("changedPaths", "commandsExecuted", "diffEvidence", "tests"):
        if not isinstance(receipt.get(field), list):
            contract_errors.append(f"receipt.{field} must be a list")
    if not is_int(receipt.get("retryCount")) or receipt.get("retryCount") != dispatch.get("retryCount"):
        contract_errors.append("receipt.retryCount must equal dispatch.retryCount")
    validate_ceo_invariant(receipt.get("ceoInvariantAfter"), "receipt.ceoInvariantAfter", contract_errors)
    if receipt.get("ceoInvariantAfter") != dispatch.get("ceoInvariant"):
        contract_errors.append("receipt changed the CEO model, reasoning, or permissions")

    guard = dispatch.get("guard", {}) if is_plain_dict(dispatch.get("guard")) else {}
    changed_paths = receipt.get("changedPaths") if isinstance(receipt.get("changedPaths"), list) else []
    allowed_paths = guard.get("exactWriteSet") if isinstance(guard.get("exactWriteSet"), list) else []
    if any(not is_nonempty_string(path) or not path_allowed(path, allowed_paths) for path in changed_paths):
        contract_errors.append("receipt.changedPaths escaped the exact write-set")
    allowed_commands = guard.get("allowedCommands") if isinstance(guard.get("allowedCommands"), list) else []
    commands = receipt.get("commandsExecuted") if isinstance(receipt.get("commandsExecuted"), list) else []
    if any(command not in allowed_commands for command in commands):
        contract_errors.append("receipt.commandsExecuted escaped the command guard")
    if receipt.get("writeSetCompliant") is not True:
        contract_errors.append("receipt.writeSetCompliant must be true")
    if receipt.get("commandGuardCompliant") is not True:
        contract_errors.append("receipt.commandGuardCompliant must be true")
    review = receipt.get("independentReview")
    require_fields(review, ("reviewer", "status", "evidenceRef"), "receipt.independentReview", contract_errors)
    if is_plain_dict(review):
        if review.get("reviewer") != "codex" or review.get("status") != "accepted":
            contract_errors.append("independent Codex review must accept before integration")
        if not is_nonempty_string(review.get("evidenceRef")):
            contract_errors.append("receipt.independentReview.evidenceRef must be non-empty")

    route_errors: list[str] = []
    if route is None or route.get("selectionSurface") == "unsupported":
        route_errors.append("adapter cannot apply the requested route on this surface")
    else:
        expected = {
            "requestedModel": route.get("model"),
            "actualModel": route.get("model"),
            "selectionSurface": route.get("selectionSurface"),
            "appliedSelector": route.get("selector"),
        }
        for field, value in expected.items():
            if receipt.get(field) != value:
                route_errors.append(f"receipt.{field} does not prove the requested adapter route")
        route_errors.extend(validate_reasoning_policy(receipt, route.get("reasoning"), "receipt"))
        if receipt.get("routeApplied") is not True or receipt.get("routeVerified") is not True:
            route_errors.append("external Harness route was not both applied and verified")
        if receipt.get("globalDefaultInherited") is not False:
            route_errors.append("explicit route silently inherited the Harness global/default model")
        proof = receipt.get("modelIdentityProof")
        proof_fields = ["status", "method", "selectionSurface", "model", "evidenceRef"]
        if route.get("reasoning") != "provider_default":
            proof_fields.append("reasoning")
        require_fields(
            proof,
            tuple(proof_fields),
            "receipt.modelIdentityProof",
            route_errors,
        )
        if is_plain_dict(proof):
            if proof.get("status") != "verified":
                route_errors.append("modelIdentityProof.status must be verified")
            if proof.get("method") not in route.get("identityProofMethods", []):
                route_errors.append("modelIdentityProof.method is not allowed by adapter policy")
            proof_expected = [
                ("selectionSurface", route.get("selectionSurface")),
                ("model", route.get("model")),
            ]
            if route.get("reasoning") != "provider_default":
                proof_expected.append(("reasoning", route.get("reasoning")))
            for field, value in proof_expected:
                if proof.get(field) != value:
                    route_errors.append(f"modelIdentityProof.{field} does not match the resolved route")
            if not is_nonempty_string(proof.get("evidenceRef")):
                route_errors.append("modelIdentityProof.evidenceRef must be non-empty")

    if contract_errors:
        return {
            "ok": False,
            "decision": "block",
            "reason": "external_harness_receipt_invalid",
            "allowExternalHarnessOutput": False,
            "allowFallbackOutput": False,
            "errors": contract_errors,
            "routeErrors": route_errors,
        }

    execution_errors: list[str] = []
    if receipt.get("processExitCode") != 0 or receipt.get("cliExit") != 0:
        execution_errors.append("external Harness process did not exit successfully")
    if receipt.get("taskCompleted") is not True or receipt.get("taskSuccess") is not True:
        execution_errors.append("external Harness did not complete the task")
    if receipt.get("stopReason") != "completed":
        execution_errors.append("external Harness stopReason is not completed")
    if receipt.get("timedOut") is not False:
        execution_errors.append("external Harness timed out")
    if receipt.get("toolPolicyCompliant") is not True:
        execution_errors.append("external Harness violated its tool policy")
    if execution_errors:
        return {
            "ok": True,
            "decision": "fallback_required",
            "reason": "external_harness_execution_incomplete",
            "allowExternalHarnessOutput": False,
            "allowFallbackOutput": False,
            "fallbackRoute": dispatch["fallback"]["routeId"],
            "errors": [],
            "routeErrors": route_errors,
            "executionErrors": execution_errors,
        }

    if route_errors:
        fallback_verified, fallback_errors = validate_fallback_receipt(
            receipt.get("fallbackReceipt"), dispatch
        )
        if fallback_errors:
            return {
                "ok": False,
                "decision": "block",
                "reason": "external_harness_receipt_invalid",
                "allowExternalHarnessOutput": False,
                "allowFallbackOutput": False,
                "errors": fallback_errors,
                "routeErrors": route_errors,
            }
        return {
            "ok": True,
            "decision": "fallback" if fallback_verified else "fallback_required",
            "reason": "model_route_unavailable",
            "allowExternalHarnessOutput": False,
            "allowFallbackOutput": fallback_verified,
            "fallbackRoute": dispatch["fallback"]["routeId"],
            "fallbackReceipt": receipt.get("fallbackReceipt") if fallback_verified else None,
            "errors": [],
            "routeErrors": route_errors,
        }

    return {
        "ok": True,
        "decision": "allow",
        "reason": "external_harness_route_verified",
        "allowExternalHarnessOutput": True,
        "allowFallbackOutput": False,
        "resolvedCapabilityClass": dispatch["requestedCapabilityClass"],
        "actualModel": receipt["actualModel"],
        "actualReasoning": receipt["actualReasoning"],
        "errors": [],
        "routeErrors": [],
    }


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an external Harness model-route receipt.")
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--dispatch", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = evaluate(load_json(args.adapter), load_json(args.dispatch), load_json(args.receipt))
    except (OSError, json.JSONDecodeError) as exc:
        result = {
            "ok": False,
            "decision": "block",
            "reason": "external_harness_contract_unreadable",
            "allowExternalHarnessOutput": False,
            "allowFallbackOutput": False,
            "errors": [str(exc)],
            "routeErrors": [],
        }
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Decision: {result['decision']}")
        print(f"Reason: {result['reason']}")
        for error in result.get("errors", []):
            print(f"ERROR: {error}")
        for error in result.get("routeErrors", []):
            print(f"ROUTE: {error}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
