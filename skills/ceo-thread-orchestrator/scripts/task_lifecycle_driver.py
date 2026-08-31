#!/usr/bin/env python3
"""Integration driver for native lane dispatch and Host-backed lifecycle control.

Native Codex lane creation is locally governed and does not need the Desktop
Host control socket. Context pressure and replacement/Goal/archive lifecycle
authorization open only after the Host acknowledges the exact action plan.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Protocol

import atomic_state
import callback_gateway
import context_ingress_gateway
import context_governor
import host_control_adapter


SCHEMA = "ceo_task_lifecycle_driver_v1"
HOST_ACK_SCHEMA = "ceo_host_execution_ack_v1"


class HostExecutor(Protocol):
    def capture_context_telemetry(self, event: dict[str, Any]) -> dict[str, Any] | None: ...

    def capture_context_ingress(
        self, event: dict[str, Any], telemetry: dict[str, Any]
    ) -> dict[str, Any] | None: ...

    def apply(self, plan: dict[str, Any]) -> dict[str, Any]: ...


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def host_action_receipts_sha256(receipts: Any) -> str:
    return canonical_sha256(receipts)


def closed_state_requires_commit(governor: dict[str, Any]) -> bool:
    return governor.get("decision") == "freeze" or governor.get("lifecycleState") == "program_blocked_global"


def is_native_lane_dispatch_event(event: dict[str, Any]) -> bool:
    return event.get("eventType") == context_governor.ORDINARY_CODEX_LANE_DISPATCH_EVENT


def bounded_strings(value: Any, *, maximum: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:512] for item in value[:maximum] if isinstance(item, str) and item]


def build_thread_recovery_packet(event: dict[str, Any], governor: dict[str, Any]) -> dict[str, Any]:
    frozen_task = str(governor.get("frozenTaskId") or event.get("taskId") or event.get("threadId") or "")
    packet = {
        "schema": "ceo_thread_recovery_packet_v1",
        "brokenTaskId": frozen_task,
        "canonicalProjectRoot": str(event.get("workspace") or ""),
        "brokenReason": str(governor.get("reason") or "context_pressure"),
        "programGoalBriefRef": str(event.get("programGoalBriefRef") or ""),
        "acceptedDecisionRefs": bounded_strings(event.get("acceptedDecisionRefs"), maximum=24),
        "activeLaneIds": bounded_strings(event.get("activeLaneIds"), maximum=24),
        "sourceRefs": bounded_strings(event.get("sourceRefs"), maximum=48),
        "contextGenerationId": None,
        "replacementTaskId": None,
        "nextSafeAction": "create_clean_replacement_then_verify_and_prepare_takeover",
        "rawHistoryIncluded": False,
        "fullCallbackBodiesIncluded": False,
    }
    valid, reason, _ = context_governor.inspect_control_structure(
        packet, max_bytes=callback_gateway.MAX_CALLBACK_SERIALIZED_BYTES
    )
    if not valid:
        raise ValueError(f"recovery_packet_{reason}")
    return packet


def build_plan(event: dict[str, Any], governor: dict[str, Any]) -> dict[str, Any]:
    control = host_control_adapter.adapt(governor)
    recovery_packet = None
    replacement_action: dict[str, Any] | None = None
    if governor.get("decision") == "freeze":
        recovery_packet = build_thread_recovery_packet(event, governor)
        replacement_action = {
            "action": "create_clean_replacement",
            "replacementForTaskId": governor.get("frozenTaskId"),
            "recoveryPacketSha256": canonical_sha256(recovery_packet),
        }
    elif governor.get("frozenTaskId") and governor.get("currentTaskId"):
        ingress = event.get("_validatedContextIngressReceipt")
        binding = event.get("_hostReplacementBinding")
        replacement_action = {
            "action": "activate_clean_replacement",
            "replacementForTaskId": governor["frozenTaskId"],
            "replacementTaskId": governor["currentTaskId"],
            "contextMode": "replace",
            "contextIngressReceiptSha256": (
                ingress.get("receiptSha256") if isinstance(ingress, dict) else None
            ),
            "retainedContextTokens": (
                ingress.get("retainedContextTokens") if isinstance(ingress, dict) else None
            ),
            "creationPlanSha256": (
                binding.get("creationPlanSha256") if isinstance(binding, dict) else None
            ),
            "creationActionReceiptsSha256": (
                binding.get("creationActionReceiptsSha256")
                if isinstance(binding, dict)
                else None
            ),
        }
    frozen_task = governor.get("frozenTaskId")
    goal_transition = None
    thread_lifecycle = None
    if frozen_task:
        goal_transition = {
            "action": "transfer_without_overlap",
            "fromTaskId": frozen_task,
            "toTaskId": governor.get("currentTaskId") if governor.get("currentTaskId") != frozen_task else None,
            "programGoalId": event.get("programGoalId"),
            "programGoalBriefRef": event.get("programGoalBriefRef"),
            "sourceGoal": "read_from_codex_host",
            "pauseOldBeforeCreate": True,
            "clearOldBeforeActivateNew": True,
            "maximumSimultaneousActiveGoals": 1,
        }
        thread_lifecycle = {
            "oldTaskId": frozen_task,
            "stopExecution": True,
            "stopGoalWakeups": True,
            "archiveAfterTransfer": True,
            "replacementMode": "new_empty_thread",
            "contextMode": "replace",
            "injectOnlyRecoveryPacket": True,
            "maximumRetainedContextTokens": 30_000,
            "harvestDriver": "rebind_to_replacement",
        }
    plan = {
        "schema": "ceo_host_action_plan_v1",
        "governorDecision": governor.get("decision"),
        "governorReason": governor.get("reason"),
        "controlReceipt": control,
        "recoveryPacket": recovery_packet,
        "replacement": replacement_action,
        "goalTransition": goal_transition,
        "threadLifecycle": thread_lifecycle,
    }
    plan["planSha256"] = canonical_sha256(plan)
    return plan


def validate_host_ack(plan: dict[str, Any], ack: Any) -> tuple[bool, str]:
    if not isinstance(ack, dict):
        return False, "host_ack_missing"
    if ack.get("schema") != HOST_ACK_SCHEMA:
        return False, "host_ack_schema_invalid"
    if ack.get("planSha256") != plan.get("planSha256"):
        return False, "host_ack_plan_digest_mismatch"
    if ack.get("actionsApplied") is not True:
        return False, "host_actions_not_applied"
    actions = plan.get("controlReceipt", {}).get("actions", {})
    current = actions.get("currentTask") if isinstance(actions, dict) else None
    frozen = actions.get("frozenTask") if isinstance(actions, dict) else None
    harvest = actions.get("harvestDriver") if isinstance(actions, dict) else None
    replacement = plan.get("replacement") if isinstance(plan.get("replacement"), dict) else None
    replacement_created = replacement and replacement.get("action") == "create_clean_replacement"
    expected_current = (current or {}).get("taskId")
    if replacement_created:
        if (
            not isinstance(ack.get("replacementTaskId"), str)
            or not ack["replacementTaskId"].strip()
            or ack["replacementTaskId"] == (frozen or {}).get("taskId")
            or ack.get("currentTaskId") != ack.get("replacementTaskId")
        ):
            return False, "host_ack_replacement_task_invalid"
    elif ack.get("currentTaskId") != expected_current:
        return False, "host_ack_current_task_mismatch"
    if ack.get("frozenTaskId") != (frozen or {}).get("taskId"):
        return False, "host_ack_frozen_task_mismatch"
    expected_harvest = "rebind" if replacement_created else (harvest or {}).get("action")
    if ack.get("harvestDriverAction") != expected_harvest:
        return False, "host_ack_harvest_action_mismatch"
    receipts = ack.get("actionReceipts")
    receipt_digest = ack.get("actionReceiptsSha256")
    if not isinstance(receipts, dict) or receipt_digest != host_action_receipts_sha256(receipts):
        return False, "host_ack_action_receipts_invalid"
    if replacement or plan.get("goalTransition"):
        required_true = [
            "oldTaskExecutionStopped",
            "oldGoalCleared",
            "oldGoalWakeupsStopped",
            "replacementCreated",
            "compactRecoveryPacketInjected",
            "replacementGoalBound",
            "replacementGoalActive",
            "oldTaskArchived",
            "harvestDriverTransferred",
        ]
        if replacement_created:
            required_true.append("oldGoalPausedBeforeReplacement")
        if any(receipts.get(field) is not True for field in required_true):
            return False, "host_ack_lifecycle_receipt_incomplete"
        if receipts.get("contextMode") != "replace":
            return False, "host_ack_context_not_replaced"
        if receipts.get("replacementTaskId") != ack.get("replacementTaskId"):
            return False, "host_ack_replacement_receipt_mismatch"
        if receipts.get("activeGoalCount") != 1:
            return False, "host_ack_goal_overlap_or_loss"
        if receipts.get("retainedContextTokens", 30_001) > 30_000:
            return False, "host_ack_clean_context_budget_exceeded"
    return True, "host_actions_confirmed"


def run(
    event: dict[str, Any],
    previous_state: dict[str, Any],
    limits: dict[str, int],
    host: HostExecutor | None,
    *,
    callback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = deepcopy(event)
    event.pop("_hostTelemetryCapability", None)
    if event.get("recoveryRequested") is True or event.get("replacementForTaskId"):
        old_task_id = event.get("replacementForTaskId")
        current_task_id = event.get("taskId") or event.get("threadId")
        binding = previous_state.get("hostReplacementLedger", {}).get(old_task_id)
        if (
            not isinstance(old_task_id, str)
            or not isinstance(current_task_id, str)
            or not isinstance(binding, dict)
            or binding.get("replacementTaskId") != current_task_id
        ):
            return {
                "schema": SCHEMA,
                "ok": False,
                "decision": "block",
                "reason": "host_replacement_identity_unbound",
                "lifecycleState": "lane_paused_recoverable",
                "programGoalBlocked": False,
                "allowModelRequest": False,
                "allowProjectToolCalls": False,
                "allowProviderCalls": False,
                "allowCallbackInjection": False,
                "hostAcknowledged": False,
                "stateCommitted": False,
                "state": previous_state,
            }
        event["_hostReplacementBinding"] = dict(binding)
    ingress_validation = None
    if event.get("eventType") == context_governor.MODEL_REQUEST_PREFLIGHT_EVENT and host is not None:
        receipt = host.capture_context_telemetry(event)
        if not isinstance(receipt, dict):
            reason = getattr(host, "telemetry_failure_reason", None)
            if reason not in {
                "host_telemetry_task_id_invalid",
                "host_telemetry_snapshot_unavailable",
                "host_telemetry_snapshot_invalid",
                "host_compaction_summary_unavailable",
            }:
                reason = "host_telemetry_snapshot_unavailable"
            return {
                "schema": SCHEMA,
                "ok": False,
                "decision": "block",
                "reason": reason,
                "lifecycleState": "lane_paused_recoverable",
                "programGoalBlocked": False,
                "allowModelRequest": False,
                "allowProjectToolCalls": False,
                "allowProviderCalls": False,
                "allowCallbackInjection": False,
                "nextAction": "connect_existing_desktop_host_with_current_telemetry_then_retry",
                "hostAcknowledged": False,
                "stateCommitted": False,
                "state": previous_state,
            }
        event["hostTelemetryReceipt"] = receipt
        event["_hostTelemetryCapability"] = context_governor.HOST_TELEMETRY_CAPABILITY
        if event.get("recoveryRequested") is True or event.get("replacementForTaskId"):
            capture_ingress = getattr(host, "capture_context_ingress", None)
            ingress = capture_ingress(event, receipt) if callable(capture_ingress) else None
            task = str(event.get("taskId") or event.get("threadId") or "")
            previous_refs = (
                previous_state.get("taskRuntimeLedger", {})
                .get(task, {})
                .get("loadedReferenceSha256s", [])
            )
            ingress_validation = context_ingress_gateway.validate(
                ingress,
                task_id=task,
                previously_loaded_reference_sha256s=previous_refs,
            )
            if not ingress_validation["ok"]:
                return {
                    "schema": SCHEMA,
                    "ok": False,
                    "decision": "block",
                    "reason": ingress_validation["reason"],
                    "allowModelRequest": False,
                    "allowCallbackInjection": False,
                    "contextIngressReceipt": ingress_validation,
                    "hostAcknowledged": False,
                    "stateCommitted": False,
                    "state": previous_state,
                }
            event["_validatedContextIngressReceipt"] = {
                "receiptSha256": ingress.get("receiptSha256"),
                "retainedContextTokens": ingress_validation["retainedContextTokens"],
            }
    if callback is not None:
        capture_route = getattr(host, "capture_model_route_receipt", None) if host is not None else None
        trusted_route_receipt = capture_route(callback) if callable(capture_route) else None
        capture_evidence = (
            getattr(host, "capture_verification_evidence_receipt", None)
            if host is not None
            else None
        )
        trusted_evidence_receipt = (
            capture_evidence(callback, event) if callable(capture_evidence) else None
        )
        callback_receipt = callback_gateway.validate(
            callback,
            trusted_routing_receipt=(
                trusted_route_receipt if isinstance(trusted_route_receipt, dict) else None
            ),
            routing_proof_capability=(
                callback_gateway.ROUTING_PROOF_CAPABILITY
                if isinstance(trusted_route_receipt, dict)
                else None
            ),
            trusted_evidence_receipt=(
                trusted_evidence_receipt
                if isinstance(trusted_evidence_receipt, dict)
                else None
            ),
            evidence_proof_capability=(
                callback_gateway.EVIDENCE_PROOF_CAPABILITY
                if isinstance(trusted_evidence_receipt, dict)
                else None
            ),
            slice_ledger=previous_state.get("callbackSliceLedger", {}),
            expected_task_id=event.get("callbackTaskId"),
            expected_slice_id=event.get("sliceId"),
            expected_slice_basis_sha256=event.get("sliceBasisSha256"),
        )
        if not callback_receipt["allowCallbackInjection"]:
            return {
                "schema": SCHEMA,
                "ok": False,
                "decision": "block",
                "reason": callback_receipt["reason"],
                "allowModelRequest": False,
                "allowCallbackInjection": False,
                "callbackReceipt": callback_receipt,
                "hostAcknowledged": False,
                "state": previous_state,
            }
    else:
        callback_receipt = None

    governor = context_governor.evaluate(event, previous_state, limits)
    if callback_receipt and callback_receipt.get("sliceLedgerAdvanceAllowed") is True:
        governor["state"].setdefault("callbackSliceLedger", {})[
            callback_receipt["sliceLedgerKey"]
        ] = callback_receipt["sliceLedgerEntry"]
    if ingress_validation and ingress_validation["ok"]:
        task = str(event.get("taskId") or event.get("threadId") or "")
        runtime = governor["state"].setdefault("taskRuntimeLedger", {}).setdefault(task, {})
        runtime["loadedReferenceSha256s"] = ingress_validation["updatedReferenceSha256s"]
        runtime["lastRetainedContextTokens"] = ingress_validation["retainedContextTokens"]
    if is_native_lane_dispatch_event(event):
        allowed = (
            governor.get("decision") == "allow"
            and governor.get("executionClass") == "ordinary_codex_lane_dispatch"
            and governor.get("allowProjectToolCalls") is True
            and governor.get("allowProviderCalls") is False
        )
        return {
            "schema": SCHEMA,
            "ok": allowed,
            "decision": "allow" if allowed else governor.get("decision", "block"),
            "reason": governor.get("reason"),
            "executionClass": "ordinary_codex_lane_dispatch",
            "allowLaneDispatch": allowed,
            "allowModelRequest": False,
            "allowProjectToolCalls": allowed,
            "allowProviderCalls": False,
            "allowCallbackInjection": bool(
                callback_receipt and callback_receipt["allowCallbackInjection"]
            ),
            "callbackReceipt": callback_receipt,
            "hostRequired": False,
            "hostAcknowledged": False,
            "stateCommitted": True,
            "state": governor["state"],
            "governor": {key: value for key, value in governor.items() if key != "state"},
        }
    plan = build_plan(event, governor)
    if not plan["controlReceipt"].get("ok"):
        return {
            "schema": SCHEMA,
            "ok": False,
            "decision": "block",
            "reason": plan["controlReceipt"].get("reason"),
            "allowModelRequest": False,
            "allowCallbackInjection": bool(callback_receipt and callback_receipt["allowCallbackInjection"]),
            "callbackReceipt": callback_receipt,
            "hostPlan": plan,
            "hostAcknowledged": False,
            "state": governor["state"],
        }
    if host is None:
        state_committed = closed_state_requires_commit(governor)
        return {
            "schema": SCHEMA,
            "ok": False,
            "decision": "block",
            "reason": "host_execution_required",
            "allowModelRequest": False,
            "allowCallbackInjection": bool(callback_receipt and callback_receipt["allowCallbackInjection"]),
            "callbackReceipt": callback_receipt,
            "hostPlan": plan,
            "hostAcknowledged": False,
            "stateCommitted": state_committed,
            "state": governor["state"] if state_committed else previous_state,
            "proposedState": None if state_committed else governor["state"],
        }
    ack = host.apply(plan)
    ack_valid, ack_reason = validate_host_ack(plan, ack)
    if (
        ack_valid
        and isinstance(plan.get("replacement"), dict)
        and plan["replacement"].get("action") == "create_clean_replacement"
    ):
        old_task_id = plan["replacement"].get("replacementForTaskId")
        governor["state"].setdefault("hostReplacementLedger", {})[old_task_id] = {
            "frozenTaskId": old_task_id,
            "replacementTaskId": ack.get("replacementTaskId"),
            "creationPlanSha256": plan.get("planSha256"),
            "creationActionReceiptsSha256": ack.get("actionReceiptsSha256"),
            "status": "created_goal_transferred",
        }
    allow_model = (
        ack_valid
        and governor.get("decision") == "allow"
        and governor.get("allowProjectToolCalls") is True
        and governor.get("allowProviderCalls") is True
    )
    state_committed = ack_valid or closed_state_requires_commit(governor)
    return {
        "schema": SCHEMA,
        "ok": ack_valid,
        "decision": governor.get("decision") if ack_valid else "block",
        "reason": ack_reason if ack_valid else ack_reason,
        "allowModelRequest": allow_model,
        "allowCallbackInjection": bool(callback_receipt and callback_receipt["allowCallbackInjection"]),
        "callbackReceipt": callback_receipt,
        "governor": {key: value for key, value in governor.items() if key != "state"},
        "hostPlan": plan,
        "hostAck": ack,
        "hostAcknowledged": ack_valid,
        "stateCommitted": state_committed,
        "state": governor["state"] if state_committed else previous_state,
        "proposedState": None if state_committed else governor["state"],
    }


def run_persisted(
    event: dict[str, Any],
    state_path: Path,
    limits: dict[str, int],
    host: HostExecutor | None,
    *,
    callback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous_state = context_governor.read_confirmed_state_json(
        state_path, max_bytes=context_governor.MAX_STATE_SERIALIZED_BYTES
    )
    previous_sha256 = atomic_state.state_sha256(previous_state)
    result = run(event, previous_state, limits, host, callback=callback)
    result["statePersisted"] = False
    if result.get("stateCommitted"):
        atomic_state.atomic_write_json(
            state_path,
            result["state"],
            expected_sha256=previous_sha256,
        )
        result["statePersisted"] = True
    return result
