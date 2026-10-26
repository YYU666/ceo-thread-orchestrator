#!/usr/bin/env python3
"""Bounded caller-side delivery decisions; no Host, execution, or authority proof."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath


HIGH_RISKS = {"security", "permissions", "payment", "persistence", "shared_contract",
              "deployment", "unresolved"}
MAX_BYTES = 16 * 1024


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("invalid_integer")
    return value


def flag(value):
    if type(value) is not bool:
        raise ValueError("invalid_boolean")
    return value


def strings(value, *, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError("invalid_list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("invalid_string")
    if len(value) != len(set(value)):
        raise ValueError("duplicate_items")
    return value


def digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("invalid_digest")
    return value


def plan(request):
    risks = strings(request["riskFlags"])
    if set(risks) - HIGH_RISKS:
        raise ValueError("unknown_risk")
    count = integer(request["changedFileCount"], 1)
    explicit_review = flag(request["independentReviewRequired"])
    quick = count <= 2 and not risks and flag(request["localReversible"])
    # Validate the field even when another condition has already ruled out quick work.
    flag(request["localReversible"])
    mode = "high_risk" if risks else "quick" if quick else "delivery_loop"
    minutes = request.get("budgetMinutes", {"quick": 10, "delivery_loop": 30, "high_risk": 60}[mode])
    result = {"mode": mode, "implementationOwners": 1,
            "newTaskRequired": False, "independentReviewRequired": bool(risks) or explicit_review,
            "budgetMinutes": integer(minutes, 1),
            "verificationProfile": {"quick": "focused", "delivery_loop": "typecheck_build", "high_risk": "full"}[mode],
            "firstCheckpoint": "affected_user_path_before_expansion"}
    result["staffing"] = staffing(request["staffing"]) if "staffing" in request else {
        "action": "direct_quick_path" if mode == "quick" else "assess_independent_work",
        "additionalLanes": 0, "visibleTaskRequired": False,
        "delegationAuthorized": False,
    }
    return result


def staffing(request):
    """Recommend bounded execution capacity, never grant tool or write authority."""
    if not isinstance(request, dict):
        raise ValueError("invalid_staffing")
    ready = integer(request["independentReadyCount"])
    active = integer(request["activeChildLanes"])
    limit = integer(request["maxChildLanes"], 1)
    authorized = flag(request["delegationAuthorized"])
    available = flag(request["delegationAvailable"])
    single = flag(request["singleThreadRequested"])
    worthwhile = flag(request["handoffWorthwhile"])
    trigger = request["checkpoint"]
    if trigger not in {"slice_start", "slice_complete", "scope_expanded", "takeover_complete"}:
        raise ValueError("invalid_staffing_checkpoint")
    reason = request.get("serialReason")
    if reason is not None and (not isinstance(reason, str) or not reason.strip() or len(reason) > 500):
        raise ValueError("invalid_serial_reason")
    if single:
        action = "respect_single_thread_request"
    elif not authorized or not available:
        action = "continue_safe_local_work_no_delegation"
    elif active >= limit:
        action = "reuse_or_harvest_existing_lanes"
    elif ready > 0 and worthwhile:
        action = "delegate_one_independent_unit"
    elif reason:
        action = "continue_serial_until_next_checkpoint"
    else:
        action = "record_concrete_serial_reason"
    return {"action": action, "additionalLanes": int(action == "delegate_one_independent_unit"),
            "activeChildLanes": active, "maxChildLanes": limit,
            "deliveryOwners": 1, "visibleTaskRequired": False,
            "delegationAuthorized": False, "advisoryOnly": True,
            "nextAssessment": "next_slice_boundary_or_scope_change",
            "serialReason": reason, "checkpoint": trigger}


def wait_decision(request):
    elapsed = integer(request["elapsedSeconds"])
    budget = integer(request["budgetSeconds"], 1)
    stopped = flag(request["writerStoppedConfirmed"])
    changed = flag(request["meaningfulProgressChanged"])
    timeout_action_issued = flag(request["timeoutActionIssued"])
    handle = request.get("runningHandle")
    if not stopped and (not isinstance(handle, str) or not handle.strip()):
        return {"action": "locate_existing_writer_once", "allowReplacementWriter": False}
    return {"action": "review_partial_then_shrink_or_handoff" if stopped else
            "await_stop_or_partial_event_no_repeat" if elapsed >= budget and timeout_action_issued else
            "request_partial_and_safe_stop_once" if elapsed >= budget else
            "inspect_changed_evidence" if changed else "bounded_event_wait",
            "allowReplacementWriter": stopped, "retainRunningHandle": not stopped,
            "recordTimeoutActionIssued": not stopped and elapsed >= budget,
            "deadlineResetAllowed": False}


def reuse(request):
    previous, current = request["previous"], request["current"]
    if not isinstance(previous, dict) or not isinstance(current, dict):
        raise ValueError("invalid_check_identity")
    for check in (previous, current):
        for field in ("command", "environmentSha256", "inputsSha256"):
            if not isinstance(check.get(field), str) or not check[field].strip():
                raise ValueError("missing_check_identity")
        digest(check["environmentSha256"])
        digest(check["inputsSha256"])
    matched = all(previous[key] == current[key] for key in
                  ("command", "environmentSha256", "inputsSha256"))
    verified = flag(request["independentlyVerified"])
    complete = flag(request["dependencyCoverageComplete"])
    concern = flag(request["newConcern"])
    flaky = flag(request["flaky"])
    passed = previous.get("status") == "passed" and type(previous.get("exitCode")) is int and previous["exitCode"] == 0
    reusable = matched and verified and complete and not concern and not flaky and passed
    return {"reuseCheck": reusable, "action": "inspect_existing_evidence" if reusable else "rerun_affected_check"}


def build(request):
    reason = request["triggerReason"]
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValueError("build_trigger_reason_required")
    target = request["validationTarget"]
    if target not in {"affected_check", "affected_native_check", "milestone_delivery"}:
        raise ValueError("invalid_build_validation_target")
    change = request["changeKind"]
    if change not in {"content", "source", "config", "dependencies", "toolchain", "unknown"}:
        raise ValueError("invalid_build_change_kind")
    required = strings(request["requiredChecks"], nonempty=True)
    artifact = request.get("artifact")
    reusable, covered = False, []
    if artifact is not None:
        if not isinstance(artifact, dict):
            raise ValueError("invalid_build_artifact")
        identity_matches = reuse(artifact["checkIdentity"])["reuseCheck"]
        expected = digest(artifact["expectedSha256"])
        observed = digest(artifact["observedSha256"])
        exists = flag(artifact["exists"])
        verified = flag(artifact["independentlyVerified"])
        covered = strings(artifact["coveredChecks"])
        reusable = identity_matches and exists and verified and expected == observed
    remaining = [check for check in required if not reusable or check not in covered]
    action = (
        "reuse_verified_artifact" if reusable and not remaining else
        "reuse_artifact_run_missing_checks" if reusable else
        "full_package_for_declared_target" if target != "affected_check" else
        "incremental_affected_validation"
    )
    return {"action": action, "triggerReason": reason, "validationTarget": target,
            "changeKind": change, "reuseArtifact": reusable, "checksToRun": remaining,
            "contentChangeRequiresEngineRebuild": False,
            "evidenceVerified": False, "allowProductCompletion": False}


def exact_cleanup_path(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 1024:
        raise ValueError("invalid_cleanup_path")
    path = PurePosixPath(value)
    if (not path.is_absolute() or len(path.parts) < 3 or str(path) != value
            or ".." in path.parts or any(char in value for char in "\\*?[]")
            or any(ord(char) < 32 for char in value)):
        raise ValueError("invalid_cleanup_path")
    return value


def cleanup(request):
    path = exact_cleanup_path(request["path"])
    category = request["category"]
    temporary = {"rebuildable_cache", "scratch", "superseded_copy"}
    protected = {"release", "rollback", "unique_evidence", "user_project",
                 "generated_asset", "unknown_recovery"}
    if category not in temporary | protected:
        raise ValueError("unknown_artifact_category")
    paths = strings(request["userAuthorizedTemporaryPaths"])
    for item in paths:
        exact_cleanup_path(item)
    source = request["authorizationSource"]
    if not isinstance(source, str) or len(source) > 500:
        raise ValueError("invalid_cleanup_authorization_source")
    references_checked = flag(request["activeReferencesChecked"])
    references = integer(request["activeReferenceCount"])
    canonical = flag(request["canonicalPathVerified"])
    identity = flag(request["contentIdentityVerified"])
    recovery = flag(request["recoveryChecked"])
    rebuild = flag(request["rebuildVerified"])
    expired = flag(request["temporaryRetentionExceeded"])
    candidate = (category in temporary and path in paths and bool(source.strip())
                 and references_checked and references == 0 and canonical
                 and identity and recovery and rebuild and expired)
    return {"action": "review_exact_authorized_cleanup_candidate" if candidate else "retain_artifact",
            "path": path, "category": category, "cleanupCandidate": candidate,
            "allowDeletion": False, "evidenceVerified": False,
            "reason": "protected_or_unclassified_data" if category in protected else
            "exact_temporary_candidate_ready_for_callsite_checks" if candidate else
            "authorization_identity_reference_or_recovery_check_missing"}


def ui(request):
    expected, observed = request["expectedTarget"], request["observedTarget"]
    keys = {"app", "window", "document"}
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        raise ValueError("invalid_target")
    if set(expected) != keys or set(observed) != keys:
        raise ValueError("incomplete_target_identity")
    if any(not isinstance(value, str) or not value.strip() for value in (*expected.values(), *observed.values())):
        raise ValueError("empty_target_identity")
    actions = strings(request["allowedActions"], nonempty=True)
    deviated = flag(request["deviationObserved"])
    allowed = expected == observed and request["action"] in actions and not deviated
    return {"allowUiAction": allowed,
            "action": "perform_one_scoped_action" if allowed else "stop_ui_and_record_deviation"}


def outcome(request):
    required = strings(request["requiredScenarios"], nonempty=True)
    observations = request["observations"]
    basis = digest(request["candidateSha256"])
    if not isinstance(observations, dict):
        raise ValueError("invalid_observations")
    missing = []
    for scenario in required:
        item = observations.get(scenario)
        if not (isinstance(item, dict) and item.get("candidateSha256") == basis
                and item.get("status") == "observed_pass"
                and isinstance(item.get("evidenceRef"), str)
                and safe_evidence_ref(item["evidenceRef"])):
            missing.append(scenario)
    return {"outcomeReadyForReview": not missing, "unverifiedScenarios": missing,
            "evidenceVerified": False,
            "allowProductCompletion": False}  # Final acceptance remains the CEO's job.


def safe_evidence_ref(value):
    if not re.fullmatch(r"[^#]+#sha256=[0-9a-f]{64}", value):
        return False
    path = value.split("#", 1)[0]
    return not (PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts
                or "\\" in path or ":" in path or any(ord(char) < 32 for char in path))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def evaluate(request):
    try:
        if not isinstance(request, dict):
            raise ValueError("request_must_be_object")
        operations = {"plan": plan, "staffing": staffing, "wait": wait_decision,
                      "reuse": reuse, "build": build, "cleanup": cleanup,
                      "ui": ui, "outcome": outcome}
        operation = request.get("operation")
        if not isinstance(operation, str) or operation not in operations:
            raise ValueError("unknown_operation")
        return {"ok": True, "advisoryOnly": True, **operations[operation](request)}
    except (KeyError, ValueError, TypeError) as exc:
        return {"ok": False, "decision": "block", "reason": str(exc),
                "allowUiAction": False, "allowReplacementWriter": False,
                "reuseCheck": False, "reuseArtifact": False, "cleanupCandidate": False,
                "allowDeletion": False, "allowProductCompletion": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    try:
        with args.request.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("request_too_large")
        result = evaluate(json.loads(raw, object_pairs_hook=unique_object))
    except (OSError, ValueError, RecursionError) as exc:
        result = {"ok": False, "decision": "block", "reason": str(exc),
                  "allowUiAction": False, "allowReplacementWriter": False,
                  "reuseCheck": False, "reuseArtifact": False, "cleanupCandidate": False,
                  "allowDeletion": False, "allowProductCompletion": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
