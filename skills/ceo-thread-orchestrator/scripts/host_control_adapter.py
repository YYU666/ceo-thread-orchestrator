#!/usr/bin/env python3
"""Strict local adapter from CEO Flow governor output to Host control actions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import context_governor

SCHEMA = "ceo_host_control_receipt_v1"
KNOWN_RECOVERY_TOOLS = {
    "context_governor",
    "cross_project_bootstrap_driver",
    "refresh_binding_driver",
}
CONTROL_KEYS = {
    "allowOldThreadExecution",
    "allowToolCalls",
    "allowProjectToolCalls",
    "allowProviderCalls",
    "allowRecoveryControlTools",
    "recoveryControlToolAllowlist",
    "resumeProgramGoal",
    "clearHistoricalGoalBlocked",
    "contextInjectionMode",
    "unbindHarvestDriver",
    "programGoalBlocked",
    "unrelatedLanesMayContinue",
    "decision",
    "lifecycleState",
    "currentTaskId",
    "frozenTaskId",
    "rebindHarvestDriverToTaskId",
}
CONTROL_PREFIXES = (
    "allow",
    "resume",
    "clear",
    "contextInjection",
    "programGoal",
    "currentTask",
    "frozenTask",
    "rebindHarvest",
)


def fail_closed(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "ok": False,
        "decision": "block",
        "reason": reason,
        "actions": {
            "projectTools": "deny",
            "providerCalls": "deny",
            "recoveryTools": [],
            "programGoal": "keep_blocked",
            "context": "no_change",
            "currentTask": {"taskId": None, "execution": "deny"},
            "frozenTask": None,
            "harvestDriver": {"action": "unbind", "fromTaskId": None, "toTaskId": None},
        },
    }


def adapt(governor_result: dict[str, Any]) -> dict[str, Any]:
    valid, reason, serialized_bytes = context_governor.inspect_control_structure(
        governor_result, max_bytes=context_governor.MAX_EVENT_SERIALIZED_BYTES
    )
    if not valid:
        return fail_closed(f"governor_result_{reason}")
    unknown_controls = sorted(
        key
        for key in governor_result
        if key not in CONTROL_KEYS and key.startswith(CONTROL_PREFIXES)
    )
    if unknown_controls:
        return fail_closed("unknown_host_control_field")
    required_bools = (
        "allowOldThreadExecution",
        "allowToolCalls",
        "allowProjectToolCalls",
        "allowProviderCalls",
        "allowRecoveryControlTools",
        "unbindHarvestDriver",
        "programGoalBlocked",
        "unrelatedLanesMayContinue",
    )
    if any(type(governor_result.get(field)) is not bool for field in required_bools):
        return fail_closed("invalid_or_missing_host_control_boolean")
    for optional in ("resumeProgramGoal", "clearHistoricalGoalBlocked"):
        if optional in governor_result and type(governor_result[optional]) is not bool:
            return fail_closed("invalid_host_transition_boolean")
    decision = governor_result.get("decision")
    lifecycle = governor_result.get("lifecycleState")
    if decision not in {"allow", "block", "freeze"}:
        return fail_closed("unknown_host_decision")
    if lifecycle not in {
        "active",
        "lane_paused_recoverable",
        "lane_paused_pending_acceptance",
        "lane_paused_user_authorization",
        "task_context_frozen_replace_required",
        "program_blocked_global",
    }:
        return fail_closed("unknown_host_lifecycle_state")
    allowlist = governor_result.get("recoveryControlToolAllowlist")
    if not isinstance(allowlist, list) or any(not isinstance(item, str) for item in allowlist):
        return fail_closed("invalid_recovery_tool_allowlist")
    if set(allowlist) - KNOWN_RECOVERY_TOOLS:
        return fail_closed("unknown_recovery_control_tool")
    recovery_enabled = governor_result["allowRecoveryControlTools"]
    if recovery_enabled != bool(allowlist):
        return fail_closed("recovery_tool_gate_mismatch")
    if recovery_enabled and (
        governor_result["allowProjectToolCalls"] or governor_result["allowProviderCalls"]
    ):
        return fail_closed("recovery_tools_cannot_open_project_or_provider_calls")
    if decision != "allow" and (
        governor_result["allowProjectToolCalls"] or governor_result["allowProviderCalls"]
    ):
        return fail_closed("blocked_decision_cannot_open_execution")
    if (
        governor_result["allowProjectToolCalls"] or governor_result["allowProviderCalls"]
    ) and not governor_result["allowToolCalls"]:
        return fail_closed("legacy_tool_gate_conflicts_with_execution_gate")
    resume = governor_result.get("resumeProgramGoal", False)
    clear = governor_result.get("clearHistoricalGoalBlocked", False)
    if resume != clear:
        return fail_closed("goal_transition_mismatch")
    injection_mode = governor_result.get("contextInjectionMode")
    if injection_mode not in (None, "replace_long_thread_context"):
        return fail_closed("unknown_context_injection_mode")
    if injection_mode and decision != "allow":
        return fail_closed("blocked_decision_cannot_replace_context")
    if resume and (decision != "allow" or lifecycle != "active"):
        return fail_closed("goal_resume_requires_active_allow")
    current_task = governor_result.get("currentTaskId")
    frozen_task = governor_result.get("frozenTaskId")
    rebind_task = governor_result.get("rebindHarvestDriverToTaskId")
    for name, value in (
        ("currentTaskId", current_task),
        ("frozenTaskId", frozen_task),
        ("rebindHarvestDriverToTaskId", rebind_task),
    ):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            return fail_closed(f"invalid_{name}")
    if lifecycle == "task_context_frozen_replace_required":
        if not current_task or frozen_task != current_task or not governor_result["unbindHarvestDriver"]:
            return fail_closed("frozen_task_requires_exact_unbind_target")
        if governor_result["allowOldThreadExecution"]:
            return fail_closed("frozen_task_execution_cannot_be_allowed")
    if frozen_task is not None and frozen_task == current_task and governor_result["allowOldThreadExecution"]:
        return fail_closed("current_task_cannot_equal_allowed_frozen_task")
    if rebind_task is not None:
        if not governor_result["unbindHarvestDriver"] or rebind_task != current_task or not frozen_task:
            return fail_closed("harvest_driver_rebind_targets_invalid")
    if resume and (not frozen_task or rebind_task != current_task):
        return fail_closed("goal_resume_requires_exact_frozen_and_rebind_targets")

    canonical_controls = {key: governor_result.get(key) for key in sorted(CONTROL_KEYS)}
    digest = hashlib.sha256(
        json.dumps(canonical_controls, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if rebind_task is not None:
        harvest_action = "rebind"
    elif governor_result["unbindHarvestDriver"]:
        harvest_action = "unbind"
    else:
        harvest_action = "keep"
    return {
        "schema": SCHEMA,
        "ok": True,
        "decision": decision,
        "reason": "typed_host_controls_accepted",
        "governorControlSha256": digest,
        "serializedBytes": serialized_bytes,
        "actions": {
            "projectTools": "allow" if governor_result["allowProjectToolCalls"] else "deny",
            "providerCalls": "allow" if governor_result["allowProviderCalls"] else "deny",
            "recoveryTools": allowlist if recovery_enabled else [],
            "programGoal": "clear_and_resume" if resume else "keep_blocked" if governor_result["programGoalBlocked"] else "no_change",
            "context": "replace" if injection_mode == "replace_long_thread_context" else "no_change",
            "currentTask": {
                "taskId": current_task,
                "execution": "allow" if governor_result["allowOldThreadExecution"] else "deny",
            },
            "frozenTask": {"taskId": frozen_task, "execution": "deny"} if frozen_task else None,
            "harvestDriver": {
                "action": harvest_action,
                "fromTaskId": frozen_task if harvest_action in {"unbind", "rebind"} else None,
                "toTaskId": rebind_task if harvest_action == "rebind" else None,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CEO Flow Host controls fail closed.")
    parser.add_argument("governor_result", type=Path)
    args = parser.parse_args()
    try:
        value = context_governor.read_confirmed_state_json(
            args.governor_result, max_bytes=context_governor.MAX_EVENT_SERIALIZED_BYTES
        )
    except context_governor.ControlPayloadError as exc:
        result = fail_closed(str(exc))
    else:
        result = adapt(value)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
