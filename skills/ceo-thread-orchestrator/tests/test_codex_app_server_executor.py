from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import atomic_state  # noqa: E402
import callback_gateway  # noqa: E402
import codex_app_server_executor as app_executor  # noqa: E402
import context_governor  # noqa: E402
import task_lifecycle_driver  # noqa: E402


class FakeTransport:
    def __init__(self, *, telemetry_available: bool = True, compaction_count: int = 0) -> None:
        self.notifications: list[dict] = []
        self.token_usage = (
            {
                "last": {
                    "inputTokens": 35_000,
                    "cachedInputTokens": 0,
                    "outputTokens": 100,
                    "reasoningOutputTokens": 50,
                    "totalTokens": 35_150,
                },
                "total": {
                    "inputTokens": 106_712,
                    "cachedInputTokens": 0,
                    "outputTokens": 500,
                    "reasoningOutputTokens": 200,
                    "totalTokens": 107_412,
                },
                "modelContextWindow": 200_000,
            }
            if telemetry_available
            else None
        )
        self.calls: list[tuple[str, dict]] = []
        self.goals: dict[str, dict | None] = {
            "old-ceo": {
                "threadId": "old-ceo",
                "objective": "Finish the program",
                "status": "active",
                "tokenBudget": 500_000,
                "tokensUsed": 106_712,
                "createdAt": 1,
                "updatedAt": 2,
                "timeUsedSeconds": 100,
            }
        }
        self.archived: set[str] = set()
        self.injected: dict[str, list] = {}
        self.compaction_count = compaction_count
        self.thread_profiles: dict[str, dict] = {}

    def request(self, method: str, params: dict | None = None) -> dict:
        params = params or {}
        self.calls.append((method, dict(params)))
        thread_id = params.get("threadId")
        if method == "thread/read":
            thread = {"id": thread_id}
            thread.update(self.thread_profiles.get(str(thread_id), {}))
            if self.token_usage is not None:
                thread["tokenUsage"] = self.token_usage
            return {"thread": thread}
        if method == "thread/resume":
            return {
                "thread": {
                    "id": thread_id,
                    "cwd": "/repo",
                    "model": "gpt-test",
                    "modelProvider": "openai",
                    "approvalPolicy": "never",
                    "approvalsReviewer": "user",
                    "runtimeWorkspaceRoots": ["/repo"],
                    "serviceTier": None,
                }
            }
        if method == "thread/turns/list":
            if params.get("itemsView") == "summary":
                return {
                    "data": [
                        {
                            "id": "turn-summary",
                            "status": "completed",
                            "items": [
                                {"id": f"compact-{index}", "type": "contextCompaction"}
                                for index in range(self.compaction_count)
                            ],
                        }
                    ]
                }
            return {"data": []}
        if method == "thread/goal/get":
            return {"goal": self.goals.get(str(thread_id))}
        if method == "thread/goal/set":
            existing = self.goals.get(str(thread_id)) or {}
            self.goals[str(thread_id)] = existing | {
                "threadId": thread_id,
                "objective": params.get("objective"),
                "status": params.get("status"),
                "tokenBudget": params.get("tokenBudget"),
            }
            return {"goal": self.goals[str(thread_id)]}
        if method == "thread/goal/clear":
            self.goals[str(thread_id)] = None
            return {"goal": None}
        if method == "thread/start":
            self.goals["clean-ceo"] = None
            return {"thread": {"id": "clean-ceo"}}
        if method == "thread/inject_items":
            self.injected[str(thread_id)] = list(params.get("items") or [])
            return {}
        if method == "thread/archive":
            self.archived.add(str(thread_id))
            return {}
        if method == "turn/interrupt":
            return {}
        raise AssertionError(f"unexpected RPC {method}")

    def wait_notification(self, method: str, *, timeout: float) -> dict | None:
        for index, notification in enumerate(self.notifications):
            if notification.get("method") == method:
                return self.notifications.pop(index)
        return None

    def close(self) -> None:
        pass


def freeze_plan() -> dict:
    state = context_governor.default_state({"taskId": "old-ceo"})
    governor = context_governor.freeze_result(
        state,
        "projected_context_pressure_limit",
        {"taskKey": "old-ceo"},
        "old-ceo",
    )
    return task_lifecycle_driver.build_plan(
        {
            "taskId": "old-ceo",
            "workspace": "/repo",
            "programGoalId": "program-1",
            "programGoalBriefRef": "docs/PROGRAM_GOAL.md",
        },
        governor,
    )


def takeover_packet(generation_id: str) -> dict:
    return {
        "contextGenerationId": generation_id,
        "tokenEstimate": 1_000,
        "memoryMode": "app_owned_memory_core",
        "authorityVerification": "app_owned_verified",
        "current": True,
        "recoveryReady": True,
        "returnedCount": 3,
        "takeover": {"shouldInject": True},
        "head": "head-1",
        "scanHash": "scan-1",
        "projectIdentitySha256": "project-1",
        "verifiedMemoryStateHash": "memory-1",
        "sourceRefs": [{"path": "docs/PROGRAM_GOAL.md", "lane": "impl"}],
    }


class CodexAppServerExecutorTests(unittest.TestCase):
    def test_default_command_connects_existing_host_proxy_without_starting_server(self) -> None:
        self.assertEqual(
            app_executor.existing_host_proxy_command("/path/to/codex"),
            ["/path/to/codex", "app-server", "proxy"],
        )
        self.assertEqual(
            app_executor.existing_host_proxy_command("codex", Path("/tmp/host.sock")),
            ["codex", "app-server", "proxy", "--sock", "/tmp/host.sock"],
        )
        self.assertEqual(
            app_executor.standalone_test_server_command("codex"),
            ["codex", "app-server", "--stdio"],
        )

    def test_connect_transport_defaults_to_proxy_and_never_falls_back(self) -> None:
        args = SimpleNamespace(
            standalone_test_server=False,
            codex="codex",
            host_socket=None,
            host_timeout=3.0,
        )
        with patch.object(
            app_executor,
            "StdioAppServerTransport",
            side_effect=app_executor.AppServerError("app_server_closed"),
        ) as transport:
            with self.assertRaises(app_executor.AppServerError):
                app_executor.connect_transport(args)
        transport.assert_called_once_with(
            ["codex", "app-server", "proxy"], timeout=3.0
        )

    def test_host_usage_last_is_context_and_total_is_cumulative_only(self) -> None:
        transport = FakeTransport()
        with tempfile.TemporaryDirectory() as tmp:
            executor = app_executor.CodexAppServerExecutor(transport, Path(tmp))
            receipt = executor.capture_context_telemetry(
                {"taskId": "old-ceo", "eventType": "model_request_preflight", "requestId": "next"}
            )
        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(receipt["currentPostCompactionContextTokens"], 35_000)
        self.assertEqual(receipt["lastRequestInputTokens"], 35_000)
        self.assertEqual(receipt["cumulativeInputTokens"], 106_712)
        self.assertEqual(receipt["contextCompactionCount"], 0)
        self.assertLess(receipt["projectedNextRequestInputTokens"], 40_000)
        self.assertEqual(
            receipt["hostTelemetryReceiptId"], context_governor.host_telemetry_receipt_sha256(receipt)
        )
        self.assertEqual(
            [method for method, _ in transport.calls],
            ["thread/read", "thread/turns/list"],
        )

    def test_production_route_capture_uses_child_thread_actual_profile(self) -> None:
        transport = FakeTransport()
        transport.thread_profiles["worker-1"] = {
            "model": "worker-model",
            "reasoningEffort": "medium",
        }
        callback = {
            "taskId": "worker-1",
            "requestedModel": "worker-model",
            "requestedThinking": "medium",
            "actualModel": "worker-model",
            "actualThinking": "medium",
            "routingProofSource": "codex_host",
        }
        with tempfile.TemporaryDirectory() as tmp:
            executor = app_executor.CodexAppServerExecutor(transport, Path(tmp))
            receipt = executor.capture_model_route_receipt(callback)
            self.assertIsNotNone(receipt)
            assert receipt is not None
            self.assertEqual(
                receipt["receiptSha256"], callback_gateway.routing_receipt_sha256(receipt)
            )
            callback["actualModel"] = "claimed-other-model"
            self.assertIsNone(executor.capture_model_route_receipt(callback))

    def test_production_evidence_capture_hashes_structured_command_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifacts" / "focused.json"
            artifact.parent.mkdir()
            callback = json.loads((ROOT / "templates" / "compact_callback.json").read_text())
            command_receipt = {
                "schema": app_executor.VERIFICATION_COMMAND_RECEIPT_SCHEMA,
                "taskId": callback["taskId"],
                "sliceId": callback["sliceId"],
                "sliceBasisSha256": callback["sliceBasisSha256"],
                "verificationProfile": callback["verificationProfile"],
                "command": callback["commands"][0],
                "exitCode": 0,
                "status": "passed",
                "summary": "Focused tests passed.",
            }
            artifact.write_text(json.dumps(command_receipt), encoding="utf-8")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            callback["evidenceRefs"] = [f"artifacts/focused.json#sha256={digest}"]
            transport = FakeTransport()
            executor = app_executor.CodexAppServerExecutor(transport, root / "journal")
            with patch.object(Path, "read_text", side_effect=AssertionError("second read forbidden")):
                receipt = executor.capture_verification_evidence_receipt(
                    callback, {"workspace": str(root)}
                )
            self.assertIsNotNone(receipt)
            assert receipt is not None
            self.assertEqual(
                receipt["receiptSha256"], callback_gateway.evidence_receipt_sha256(receipt)
            )
            callback["evidenceRefs"] = [f"artifacts/focused.json#sha256={'0' * 64}"]
            self.assertIsNone(
                executor.capture_verification_evidence_receipt(
                    callback, {"workspace": str(root)}
                )
            )

    def test_production_entry_binds_route_evidence_and_slice_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            callback = json.loads((ROOT / "templates" / "compact_callback.json").read_text())
            callback["ceoVerificationCount"] = 1
            artifact = root / "artifacts" / "focused.json"
            artifact.parent.mkdir()
            artifact.write_text(
                json.dumps(
                    {
                        "schema": app_executor.VERIFICATION_COMMAND_RECEIPT_SCHEMA,
                        "taskId": callback["taskId"],
                        "sliceId": callback["sliceId"],
                        "sliceBasisSha256": callback["sliceBasisSha256"],
                        "verificationProfile": callback["verificationProfile"],
                        "command": callback["commands"][0],
                        "exitCode": 0,
                        "status": "passed",
                        "summary": "Focused tests passed.",
                    }
                ),
                encoding="utf-8",
            )
            callback["evidenceRefs"] = [
                "artifacts/focused.json#sha256=" + hashlib.sha256(artifact.read_bytes()).hexdigest()
            ]
            transport = FakeTransport()
            transport.thread_profiles[callback["taskId"]] = {
                "model": callback["actualModel"],
                "reasoningEffort": callback["actualThinking"],
            }
            executor = app_executor.CodexAppServerExecutor(transport, root / "journal")
            route_receipt = executor.capture_model_route_receipt(callback)
            evidence_receipt = executor.capture_verification_evidence_receipt(
                callback, {"workspace": str(root)}
            )
            assert route_receipt is not None and evidence_receipt is not None
            callback["routingReceiptId"] = route_receipt["receiptSha256"]
            callback["verificationEvidenceReceiptId"] = evidence_receipt["receiptSha256"]
            callback["declaredTokenEstimate"] = callback_gateway.compact_token_estimate(callback) + 20
            result = app_executor.execute_lifecycle_entry(
                {
                    "taskId": "ceo",
                    "eventType": "model_request_preflight",
                    "requestId": "callback-acceptance",
                    "workspace": str(root),
                    "callbackTaskId": callback["taskId"],
                    "sliceId": callback["sliceId"],
                    "sliceBasisSha256": callback["sliceBasisSha256"],
                },
                root / "state.json",
                {
                    "inputTokenLimit": 120_000,
                    "contextTokenLimit": 120_000,
                    "cumulativeInputLimit": 10_000_000,
                    "contextBytesLimit": 50 * 1024 * 1024,
                    "takeoverTokenLimit": 10_000,
                },
                executor,
                callback=callback,
            )
        self.assertTrue(result["allowModelRequest"], result)
        self.assertTrue(result["callbackReceipt"]["modelRouteVerified"], result)
        self.assertTrue(result["callbackReceipt"]["verificationEvidenceVerified"], result)
        self.assertTrue(result["callbackReceipt"]["allowCandidateAcceptance"], result)
        self.assertIn(
            result["callbackReceipt"]["sliceLedgerKey"], result["state"]["callbackSliceLedger"]
        )

    def test_idle_thread_without_host_snapshot_pauses_without_resume_or_writer_takeover(self) -> None:
        transport = FakeTransport(telemetry_available=False)
        with tempfile.TemporaryDirectory() as tmp:
            executor = app_executor.CodexAppServerExecutor(
                transport, Path(tmp), telemetry_timeout=0
            )
            receipt = executor.capture_context_telemetry(
                {"taskId": "old-ceo", "eventType": "model_request_preflight", "requestId": "idle"}
            )
        self.assertIsNone(receipt)
        self.assertEqual(executor.telemetry_failure_reason, "host_telemetry_snapshot_unavailable")
        self.assertEqual([method for method, _ in transport.calls], ["thread/read"])

    def test_compaction_summary_paginates_and_counts_unique_markers(self) -> None:
        class PaginatedTransport(FakeTransport):
            def request(self, method: str, params: dict | None = None) -> dict:
                params = params or {}
                if method != "thread/turns/list":
                    return super().request(method, params)
                self.calls.append((method, dict(params)))
                if params.get("cursor") is None:
                    return {
                        "data": [
                            {
                                "id": "turn-new",
                                "items": [
                                    {"id": "compact-2", "type": "contextCompaction"},
                                    {"id": "message-1", "type": "agentMessage"},
                                ],
                            }
                        ],
                        "nextCursor": "page-2",
                    }
                self.assert_cursor(params.get("cursor"))
                return {
                    "data": [
                        {
                            "id": "turn-old",
                            "items": [
                                {"id": "compact-2", "type": "contextCompaction"},
                                {"id": "compact-1", "type": "contextCompaction"},
                            ],
                        }
                    ]
                }

            @staticmethod
            def assert_cursor(cursor: object) -> None:
                if cursor != "page-2":
                    raise AssertionError(f"unexpected cursor {cursor}")

        transport = PaginatedTransport()
        with tempfile.TemporaryDirectory() as tmp:
            executor = app_executor.CodexAppServerExecutor(transport, Path(tmp))
            receipt = executor.capture_context_telemetry(
                {"taskId": "old-ceo", "eventType": "model_request_preflight", "requestId": "paged"}
            )
        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(receipt["contextCompactionCount"], 2)
        self.assertEqual(
            [params.get("cursor") for method, params in transport.calls if method == "thread/turns/list"],
            [None, "page-2"],
        )

    def test_malformed_or_repeated_compaction_cursor_is_typed_unavailable(self) -> None:
        class BadSummaryTransport(FakeTransport):
            def __init__(self, mode: str) -> None:
                super().__init__()
                self.mode = mode

            def request(self, method: str, params: dict | None = None) -> dict:
                params = params or {}
                if method != "thread/turns/list":
                    return super().request(method, params)
                self.calls.append((method, dict(params)))
                if self.mode == "malformed":
                    return {"data": [{"id": "turn", "items": "not-a-list"}]}
                return {"data": [], "nextCursor": "same-cursor"}

        for mode in ("malformed", "repeated"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                transport = BadSummaryTransport(mode)
                executor = app_executor.CodexAppServerExecutor(transport, Path(tmp))
                receipt = executor.capture_context_telemetry(
                    {"taskId": "old-ceo", "eventType": "model_request_preflight", "requestId": mode}
                )
                self.assertIsNone(receipt)
                self.assertEqual(
                    executor.telemetry_failure_reason, "host_compaction_summary_unavailable"
                )

    def test_real_action_sequence_transfers_goal_without_overlap(self) -> None:
        transport = FakeTransport()
        plan = freeze_plan()
        with tempfile.TemporaryDirectory() as tmp:
            executor = app_executor.CodexAppServerExecutor(transport, Path(tmp))
            ack = executor.apply(plan)
        self.assertTrue(ack["actionsApplied"], ack)
        self.assertTrue(task_lifecycle_driver.validate_host_ack(plan, ack)[0])
        self.assertIsNone(transport.goals["old-ceo"])
        self.assertEqual(transport.goals["clean-ceo"]["status"], "active")
        self.assertIn("old-ceo", transport.archived)
        self.assertTrue(transport.injected["clean-ceo"])
        methods = [method for method, _ in transport.calls]
        pause_index = next(
            index
            for index, (method, params) in enumerate(transport.calls)
            if method == "thread/goal/set" and params.get("threadId") == "old-ceo"
        )
        create_index = methods.index("thread/start")
        clear_index = methods.index("thread/goal/clear")
        activate_index = next(
            index
            for index, (method, params) in enumerate(transport.calls)
            if method == "thread/goal/set"
            and params.get("threadId") == "clean-ceo"
            and params.get("status") == "active"
        )
        self.assertLess(pause_index, create_index)
        self.assertLess(clear_index, activate_index)

    def test_ambiguous_thread_start_is_never_replayed(self) -> None:
        transport = FakeTransport()
        plan = freeze_plan()
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            journal = {
                "schema": app_executor.EXECUTOR_SCHEMA,
                "planSha256": plan["planSha256"],
                "phase": "replacement_create_started",
                "oldTaskId": "old-ceo",
            }
            atomic_state.atomic_write_json(
                journal_dir / f"{plan['planSha256']}.json",
                journal,
                expected_sha256=atomic_state.state_sha256({}),
            )
            executor = app_executor.CodexAppServerExecutor(transport, journal_dir)
            ack = executor.apply(plan)
        self.assertFalse(ack["actionsApplied"])
        self.assertIn("host_reconciliation_required", ack["reason"])
        self.assertNotIn("thread/start", [method for method, _ in transport.calls])

    def test_full_entry_runs_telemetry_governor_lifecycle_ack_and_state_commit(self) -> None:
        transport = FakeTransport()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executor = app_executor.CodexAppServerExecutor(transport, root / "journal")
            result = app_executor.execute_lifecycle_entry(
                {
                    "taskId": "old-ceo",
                    "eventType": "model_request_preflight",
                    "requestId": "desktop-pressure",
                    "workspace": "/repo",
                    "programGoalId": "program-1",
                    "programGoalBriefRef": "docs/PROGRAM_GOAL.md",
                },
                root / "state.json",
                {
                    "inputTokenLimit": 120_000,
                    "contextTokenLimit": 38_000,
                    "cumulativeInputLimit": 10_000_000,
                    "contextBytesLimit": 50 * 1024 * 1024,
                    "takeoverTokenLimit": 10_000,
                },
                executor,
            )
        self.assertEqual(result["decision"], "freeze", result)
        self.assertTrue(result["hostAcknowledged"], result)
        self.assertTrue(result["statePersisted"], result)
        self.assertEqual(
            [method for method, _ in transport.calls].count("thread/start"),
            1,
        )
        self.assertIsNone(transport.goals["old-ceo"])
        self.assertEqual(transport.goals["clean-ceo"]["status"], "active")

    def test_full_entry_rotates_after_two_host_compactions(self) -> None:
        transport = FakeTransport(compaction_count=2)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executor = app_executor.CodexAppServerExecutor(transport, root / "journal")
            result = app_executor.execute_lifecycle_entry(
                {
                    "taskId": "old-ceo",
                    "eventType": "model_request_preflight",
                    "requestId": "desktop-two-compactions",
                    "workspace": "/repo",
                    "programGoalId": "program-1",
                    "programGoalBriefRef": "docs/PROGRAM_GOAL.md",
                },
                root / "state.json",
                {
                    "inputTokenLimit": 120_000,
                    "contextTokenLimit": 120_000,
                    "cumulativeInputLimit": 10_000_000,
                    "contextBytesLimit": 50 * 1024 * 1024,
                    "takeoverTokenLimit": 10_000,
                },
                executor,
            )
        self.assertEqual(result["decision"], "freeze", result)
        self.assertEqual(result["governor"]["reason"], "context_compaction_rotation_limit")
        self.assertTrue(result["hostAcknowledged"], result)
        self.assertEqual([method for method, _ in transport.calls].count("thread/start"), 1)

    def test_production_executor_activates_verified_existing_replacement(self) -> None:
        transport = FakeTransport(compaction_count=2)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "state.json"
            executor = app_executor.CodexAppServerExecutor(transport, root / "journal")
            limits = {
                "inputTokenLimit": 120_000,
                "contextTokenLimit": 120_000,
                "cumulativeInputLimit": 10_000_000,
                "contextBytesLimit": 50 * 1024 * 1024,
                "takeoverTokenLimit": 10_000,
            }
            frozen = app_executor.execute_lifecycle_entry(
                {
                    "taskId": "old-ceo",
                    "eventType": "model_request_preflight",
                    "requestId": "freeze-two-compactions",
                    "workspace": "/repo",
                    "programGoalId": "program-1",
                    "programGoalBriefRef": "docs/PROGRAM_GOAL.md",
                },
                state_path,
                limits,
                executor,
            )
            self.assertEqual(frozen["decision"], "freeze", frozen)
            transport.compaction_count = 0
            assert transport.token_usage is not None
            transport.token_usage["last"]["inputTokens"] = 10_000
            transport.token_usage["last"]["totalTokens"] = 10_150
            transport.goals["rogue-ceo"] = {
                "threadId": "rogue-ceo",
                "objective": "Unrelated goal",
                "status": "active",
            }
            rogue = app_executor.execute_lifecycle_entry(
                {
                    "taskId": "rogue-ceo",
                    "eventType": "model_request_preflight",
                    "requestId": "rogue-activation",
                    "workspace": "/repo",
                    "lane": "impl",
                    "recoveryRequested": True,
                    "replacementForTaskId": "old-ceo",
                    "takeoverPacket": takeover_packet("rogue-generation"),
                },
                state_path,
                limits,
                executor,
            )
            self.assertEqual(rogue["reason"], "host_replacement_identity_unbound")
            self.assertFalse(rogue["allowModelRequest"])
            activated = app_executor.execute_lifecycle_entry(
                {
                    "taskId": "clean-ceo",
                    "eventType": "model_request_preflight",
                    "requestId": "activate-clean",
                    "workspace": "/repo",
                    "lane": "impl",
                    "recoveryRequested": True,
                    "replacementForTaskId": "old-ceo",
                    "takeoverPacket": takeover_packet("fresh-clean-generation"),
                    "programGoalId": "program-1",
                    "programGoalBriefRef": "docs/PROGRAM_GOAL.md",
                },
                state_path,
                limits,
                executor,
            )
        self.assertEqual(activated["decision"], "allow", activated)
        self.assertTrue(activated["hostAcknowledged"], activated)
        self.assertTrue(activated["allowModelRequest"], activated)
        self.assertEqual(
            activated["hostPlan"]["replacement"]["action"],
            "activate_clean_replacement",
        )
        self.assertEqual(activated["hostAck"]["currentTaskId"], "clean-ceo")
        self.assertEqual([method for method, _ in transport.calls].count("thread/start"), 1)


if __name__ == "__main__":
    unittest.main()
