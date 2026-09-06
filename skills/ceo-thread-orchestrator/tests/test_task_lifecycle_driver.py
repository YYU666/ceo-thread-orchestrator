from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import task_lifecycle_driver as driver  # noqa: E402
from test_context_governor import valid_takeover_packet  # noqa: E402


def limits() -> dict[str, int]:
    return {
        "inputTokenLimit": 120_000,
        "contextTokenLimit": 120_000,
        "cumulativeInputLimit": 10_000_000,
        "contextBytesLimit": 50 * 1024 * 1024,
        "takeoverTokenLimit": 10_000,
    }


def preflight(
    task_id: str,
    request_id: str,
    *,
    projected: int = 20_000,
    compaction_count: int = 0,
) -> dict:
    receipt = {
        "schema": driver.context_governor.HOST_TELEMETRY_SCHEMA,
        "telemetrySource": "codex_host",
        "metricScope": "current_post_compaction_context",
        "capturedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "taskId": task_id,
        "lastRequestInputTokens": 1_000,
        "currentPostCompactionContextTokens": 18_000,
        "projectedNextRequestInputTokens": projected,
        "estimatedContextBytes": 80_000,
        "modelContextWindowTokens": 200_000,
        "reservedOutputTokens": 8_000,
        "cumulativeInputTokens": 1_000,
        "contextCompactionCount": compaction_count,
        "compactionCountSource": driver.context_governor.HOST_COMPACTION_SOURCE,
    }
    receipt["hostTelemetryReceiptId"] = driver.context_governor.host_telemetry_receipt_sha256(receipt)
    return {
        "taskId": task_id,
        "eventType": "model_request_preflight",
        "requestId": request_id,
        "hostTelemetryReceipt": receipt,
        "_hostTelemetryCapability": driver.context_governor.HOST_TELEMETRY_CAPABILITY,
    }


class FakeHost:
    def __init__(self, *, tamper: bool = False, incomplete_lifecycle: bool = False) -> None:
        self.plans: list[dict] = []
        self.tamper = tamper
        self.incomplete_lifecycle = incomplete_lifecycle

    def capture_context_telemetry(self, event: dict) -> dict | None:
        receipt = event.get("hostTelemetryReceipt")
        return dict(receipt) if isinstance(receipt, dict) else None

    def capture_context_ingress(self, event: dict, telemetry: dict) -> dict:
        receipt = {
            "schema": driver.context_ingress_gateway.SCHEMA,
            "taskId": event.get("taskId") or event.get("threadId"),
            "retainedContextTokens": telemetry["currentPostCompactionContextTokens"],
            "threadHistoryMode": "recovery_packet_only",
            "fullThreadHistoryLoaded": False,
            "newFocusedReferences": [],
            "toolOutputs": [],
        }
        receipt["receiptSha256"] = driver.context_ingress_gateway.receipt_sha256(receipt)
        return receipt

    def apply(self, plan: dict) -> dict:
        self.plans.append(plan)
        actions = plan["controlReceipt"]["actions"]
        current = actions.get("currentTask") or {}
        frozen = actions.get("frozenTask") or {}
        harvest = actions.get("harvestDriver") or {}
        replacement = plan.get("replacement") or {}
        if replacement.get("action") == "create_clean_replacement":
            replacement_task_id = f"replacement-for-{frozen.get('taskId')}"
            current_task_id = replacement_task_id
            harvest_action = "rebind"
        elif replacement.get("action") == "activate_clean_replacement":
            replacement_task_id = replacement.get("replacementTaskId")
            current_task_id = current.get("taskId")
            harvest_action = harvest.get("action")
        else:
            replacement_task_id = None
            current_task_id = current.get("taskId")
            harvest_action = harvest.get("action")
        receipts = (
            {
                "oldTaskExecutionStopped": True,
                "oldGoalPausedBeforeReplacement": True,
                "oldGoalCleared": True,
                "oldGoalWakeupsStopped": True,
                "replacementCreated": True,
                "compactRecoveryPacketInjected": True,
                "replacementGoalBound": True,
                "replacementGoalActive": True,
                "oldTaskArchived": True,
                "harvestDriverTransferred": True,
                "contextMode": "replace",
                "replacementTaskId": replacement_task_id,
                "activeGoalCount": 1,
                "retainedContextTokens": 2_200,
            }
            if replacement
            else {"noOp": True}
        )
        if self.incomplete_lifecycle and replacement:
            receipts["oldGoalCleared"] = False
        ack = {
            "schema": driver.HOST_ACK_SCHEMA,
            "planSha256": "0" * 64 if self.tamper else plan["planSha256"],
            "actionsApplied": True,
            "currentTaskId": current_task_id,
            "frozenTaskId": frozen.get("taskId"),
            "replacementTaskId": replacement_task_id,
            "harvestDriverAction": harvest_action,
            "actionReceipts": receipts,
            "actionReceiptsSha256": driver.host_action_receipts_sha256(receipts),
        }
        return ack


class TaskLifecycleDriverTests(unittest.TestCase):
    def test_unavailable_host_snapshot_is_recoverable_and_never_calls_host_apply(self) -> None:
        class MissingTelemetryHost(FakeHost):
            telemetry_failure_reason = "host_telemetry_snapshot_unavailable"

            def capture_context_telemetry(self, event: dict) -> None:
                return None

        host = MissingTelemetryHost()
        result = driver.run(preflight("idle-ceo", "request-idle"), {}, limits(), host)
        self.assertEqual(result["reason"], "host_telemetry_snapshot_unavailable")
        self.assertEqual(result["lifecycleState"], "lane_paused_recoverable")
        self.assertFalse(result["programGoalBlocked"])
        self.assertFalse(result["allowModelRequest"])
        self.assertFalse(result["allowProjectToolCalls"])
        self.assertFalse(result["allowProviderCalls"])
        self.assertFalse(result["stateCommitted"])
        self.assertEqual(host.plans, [])

    def test_missing_host_preflight_never_opens_model_request(self) -> None:
        host = FakeHost()
        result = driver.run({"taskId": "ceo", "dispatchRequested": True}, {}, limits(), host)
        self.assertFalse(result["allowModelRequest"])
        self.assertEqual(result["governor"]["reason"], "model_request_preflight_required")

    def test_native_codex_lane_dispatch_needs_no_host_socket(self) -> None:
        result = driver.run(
            {
                "taskId": "ceo",
                "eventType": "codex_lane_dispatch",
                "dispatchRequested": True,
                "routingSurface": "subagent",
                "executionBackend": "codex_native",
            },
            {},
            limits(),
            None,
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["allowLaneDispatch"])
        self.assertFalse(result["allowModelRequest"])
        self.assertFalse(result["allowProviderCalls"])
        self.assertFalse(result["hostRequired"])
        self.assertFalse(result["hostAcknowledged"])
        self.assertNotIn("hostPlan", result)

    def test_external_dispatch_cannot_claim_host_free_native_lane(self) -> None:
        result = driver.run(
            {
                "taskId": "ceo",
                "eventType": "codex_lane_dispatch",
                "dispatchRequested": True,
                "routingSurface": "visible_thread",
                "executionBackend": "codex_native",
                "externalHarnessRequested": True,
            },
            {},
            limits(),
            None,
        )
        self.assertFalse(result["ok"])
        self.assertFalse(result["allowLaneDispatch"])
        self.assertEqual(result["reason"], "codex_lane_dispatch_scope_invalid")
        self.assertFalse(result["hostRequired"])

    def test_callback_slice_ledger_is_task_state_and_cannot_reset(self) -> None:
        callback = json.loads((ROOT / "templates" / "compact_callback.json").read_text())
        callback["declaredTokenEstimate"] = driver.callback_gateway.compact_token_estimate(callback) + 20
        event = preflight("ceo", "callback-one") | {
            "callbackTaskId": callback["taskId"],
            "sliceId": callback["sliceId"],
            "sliceBasisSha256": callback["sliceBasisSha256"],
        }
        first = driver.run(event, {}, limits(), FakeHost(), callback=callback)
        ledger_key = f"{callback['taskId']}::{callback['sliceId']}"
        self.assertIn(ledger_key, first["state"]["callbackSliceLedger"])

        reset = dict(callback)
        reset["callbackSequence"] = 2
        reset["priorCallbackSha256"] = first["callbackReceipt"]["callbackSha256"]
        reset["processUpdateCount"] = 0
        reset["declaredTokenEstimate"] = driver.callback_gateway.compact_token_estimate(reset) + 20
        second = driver.run(
            preflight("ceo", "callback-two")
            | {
                "callbackTaskId": callback["taskId"],
                "sliceId": callback["sliceId"],
                "sliceBasisSha256": callback["sliceBasisSha256"],
            },
            first["state"],
            limits(),
            FakeHost(),
            callback=reset,
        )
        self.assertIn("callback_slice_counts_regressed", second["callbackReceipt"]["acceptanceGaps"])
        self.assertEqual(
            second["state"]["callbackSliceLedger"][ledger_key]["callbackSequence"], 1
        )

    def test_projected_context_freezes_before_hard_limit(self) -> None:
        host = FakeHost()
        event = preflight("old-ceo", "request-1", projected=110_000)
        result = driver.run(event, {}, limits(), host)
        self.assertEqual(result["decision"], "freeze")
        self.assertFalse(result["allowModelRequest"])
        plan = host.plans[0]
        self.assertEqual(plan["replacement"]["action"], "create_clean_replacement")
        self.assertEqual(plan["controlReceipt"]["actions"]["frozenTask"]["taskId"], "old-ceo")
        self.assertEqual(plan["controlReceipt"]["actions"]["harvestDriver"]["action"], "unbind")

    def test_second_compaction_automatically_creates_clean_replacement(self) -> None:
        host = FakeHost()
        result = driver.run(
            preflight("old-ceo", "rotate-after-two", projected=110_000, compaction_count=2),
            {},
            limits(),
            host,
        )
        self.assertEqual(result["decision"], "freeze", result)
        self.assertEqual(result["governor"]["reason"], "projected_context_pressure_limit")
        self.assertTrue(result["hostAcknowledged"], result)
        self.assertEqual(len(host.plans), 1)
        self.assertEqual(host.plans[0]["replacement"]["action"], "create_clean_replacement")
        self.assertEqual(host.plans[0]["replacement"]["replacementForTaskId"], "old-ceo")
        self.assertEqual(result["hostAck"]["replacementTaskId"], "replacement-for-old-ceo")

    def test_clean_replacement_denies_old_task_and_rebinds_driver(self) -> None:
        host = FakeHost()
        frozen = driver.run(preflight("old-ceo", "request-freeze", projected=110_000), {}, limits(), host)
        event = preflight("replacement-for-old-ceo", "request-clean", projected=20_000) | {
            "workspace": "/repo",
            "lane": "impl",
            "recoveryRequested": True,
            "replacementForTaskId": "old-ceo",
            "takeoverPacket": valid_takeover_packet("fresh-generation"),
        }
        replacement = driver.run(event, frozen["state"], limits(), host)
        self.assertTrue(replacement["allowModelRequest"], replacement)
        actions = replacement["hostPlan"]["controlReceipt"]["actions"]
        self.assertEqual(
            actions["currentTask"],
            {"taskId": "replacement-for-old-ceo", "execution": "allow"},
        )
        self.assertEqual(actions["frozenTask"], {"taskId": "old-ceo", "execution": "deny"})
        self.assertEqual(
            actions["harvestDriver"],
            {
                "action": "rebind",
                "fromTaskId": "old-ceo",
                "toTaskId": "replacement-for-old-ceo",
            },
        )
        self.assertEqual(actions["context"], "replace")

    def test_tampered_host_ack_keeps_everything_closed(self) -> None:
        event = preflight("ceo", "request-1")
        result = driver.run(event, {}, limits(), FakeHost(tamper=True))
        self.assertFalse(result["ok"])
        self.assertFalse(result["allowModelRequest"])
        self.assertEqual(result["reason"], "host_ack_plan_digest_mismatch")
        self.assertFalse(result["stateCommitted"])
        retry = driver.run(event, result["state"], limits(), FakeHost())
        self.assertTrue(retry["allowModelRequest"], retry)

    def test_actions_applied_without_complete_lifecycle_receipts_is_rejected(self) -> None:
        result = driver.run(
            preflight("old-ceo", "request-freeze-incomplete", projected=110_000),
            {},
            limits(),
            FakeHost(incomplete_lifecycle=True),
        )
        self.assertFalse(result["hostAcknowledged"])
        self.assertEqual(result["reason"], "host_ack_lifecycle_receipt_incomplete")
        self.assertFalse(result["allowModelRequest"])

    def test_clean_replacement_requires_context_ingress_receipt(self) -> None:
        class MissingIngressHost(FakeHost):
            def capture_context_ingress(self, event: dict, telemetry: dict) -> None:
                return None

        frozen = driver.run(
            preflight("old-ceo", "request-freeze-for-ingress", projected=110_000),
            {},
            limits(),
            FakeHost(),
        )
        event = preflight("replacement-for-old-ceo", "request-clean-missing-ingress") | {
            "workspace": "/repo",
            "lane": "impl",
            "recoveryRequested": True,
            "replacementForTaskId": "old-ceo",
            "takeoverPacket": valid_takeover_packet("fresh-ingress-generation"),
        }
        result = driver.run(event, frozen["state"], limits(), MissingIngressHost())
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "context_ingress_receipt_required")
        self.assertFalse(result["allowModelRequest"])

    def test_no_host_executor_is_not_treated_as_automatic_enforcement(self) -> None:
        result = driver.run(preflight("ceo", "request-1"), {}, limits(), None)
        self.assertEqual(result["reason"], "host_execution_required")
        self.assertFalse(result["allowModelRequest"])
        self.assertFalse(result["stateCommitted"])

    def test_oversized_callback_stops_before_host_or_model(self) -> None:
        host = FakeHost()
        callback = {
            "schema": "ceo_compact_callback_v1",
            "taskId": "worker",
            "status": "complete",
            "summary": "x" * 4000,
            "changedPaths": [],
            "commands": [],
            "evidenceRefs": [],
            "risks": [],
            "nextAction": "review",
            "needsCeoDecision": True,
            "declaredTokenEstimate": 2000,
        }
        result = driver.run(preflight("ceo", "request-1"), {}, limits(), host, callback=callback)
        self.assertFalse(result["allowCallbackInjection"])
        self.assertFalse(result["allowModelRequest"])
        self.assertEqual(host.plans, [])

    def test_confirmed_state_is_persisted_only_after_host_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "lifecycle-state.json"
            failed = driver.run_persisted(
                preflight("ceo", "request-persist"),
                state_path,
                limits(),
                FakeHost(tamper=True),
            )
            self.assertFalse(failed["statePersisted"])
            self.assertFalse(state_path.exists())

            accepted = driver.run_persisted(
                preflight("ceo", "request-persist"),
                state_path,
                limits(),
                FakeHost(),
            )
            self.assertTrue(accepted["statePersisted"])
            confirmed = driver.context_governor.read_confirmed_state_json(state_path)
            self.assertIn("request-persist", confirmed["taskRuntimeLedger"]["ceo"]["consumedPreflightRequestIds"])

    def test_native_lane_dispatch_persists_without_host_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "native-lane-state.json"
            result = driver.run_persisted(
                {
                    "taskId": "ceo",
                    "eventType": "codex_lane_dispatch",
                    "dispatchRequested": True,
                    "routingSurface": "visible_thread",
                    "executionBackend": "codex_native",
                },
                state_path,
                limits(),
                None,
            )
            self.assertTrue(result["allowLaneDispatch"], result)
            self.assertFalse(result["hostRequired"])
            self.assertTrue(result["statePersisted"])
            confirmed = driver.context_governor.read_confirmed_state_json(state_path)
            self.assertEqual(confirmed["taskRuntimeLedger"]["ceo"]["turnCount"], 1)


if __name__ == "__main__":
    unittest.main()
