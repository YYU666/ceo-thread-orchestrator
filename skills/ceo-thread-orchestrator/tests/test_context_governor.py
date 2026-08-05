#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "context_governor.py"
SPEC = importlib.util.spec_from_file_location("context_governor", SCRIPT)
context_governor = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(context_governor)


def limits() -> dict[str, int]:
    return {
        "inputTokenLimit": 120_000,
        "contextTokenLimit": 120_000,
        "cumulativeInputLimit": 10_000_000,
        "contextBytesLimit": 50 * 1024 * 1024,
        "takeoverTokenLimit": 3_000,
    }


def valid_takeover_packet(generation_id: str = "gen-1") -> dict[str, object]:
    return {
        "contextGenerationId": generation_id,
        "tokenEstimate": 1000,
        "memoryMode": "app_owned_memory_core",
        "authorityVerification": "app_owned_verified",
        "current": True,
        "recoveryReady": True,
        "returnedCount": 6,
        "takeover": {"shouldInject": True},
        "head": "a",
        "scanHash": "b",
        "projectIdentitySha256": "project-123",
        "verifiedMemoryStateHash": "c",
        "sourceRefs": [{"path": "docs/PRD.md", "lane": "impl", "module": "docs"}],
    }


class ContextGovernorTest(unittest.TestCase):
    def test_pressure_freeze_emits_once_then_stops_without_repeat(self) -> None:
        first = context_governor.evaluate({"taskId": "old-task", "inputTokens": 145_000}, {}, limits())
        self.assertEqual(first["decision"], "freeze")
        self.assertTrue(first["emitFreezeReceipt"])
        self.assertFalse(first["allowToolCalls"])
        self.assertEqual(first["nextAction"], "emit_freeze_receipt_and_unbind_harvest_driver")

        second = context_governor.evaluate(
            {"taskId": "old-task", "eventType": "heartbeat", "inputTokens": 0},
            first["state"],
            limits(),
        )
        self.assertEqual(second["decision"], "freeze")
        self.assertFalse(second["emitFreezeReceipt"])
        self.assertFalse(second["allowOldThreadExecution"])
        self.assertFalse(second["allowToolCalls"])
        self.assertEqual(second["nextAction"], "stop_old_task_no_repeat")

        third = context_governor.evaluate(
            {"taskId": "old-task", "inputTokens": 10, "takeoverPacket": valid_takeover_packet()},
            second["state"],
            limits(),
        )
        self.assertEqual(third["decision"], "freeze")
        self.assertFalse(third["emitFreezeReceipt"])
        self.assertEqual(third["nextAction"], "stop_old_task_no_repeat")

    def test_memory_fail_closed_returns_single_structured_next_action(self) -> None:
        result = context_governor.evaluate(
            {
                "inputTokens": 1_000,
                "memory": {
                    "memoryMode": "fallback_stale",
                    "status": "project_unresolved",
                    "current": False,
                    "recoveryReady": False,
                    "authorityVerification": "unavailable",
                },
            },
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "fallback_stale")
        self.assertEqual(result["blocker"]["nextAction"], result["nextAction"])
        self.assertEqual(result["metrics"]["fallbackRate"], 1.0)
        self.assertEqual(result["nextAction"], "run_readonly_exact_scan")

    def test_takeover_packet_budget_and_payload_gate(self) -> None:
        over_budget = context_governor.evaluate(
            {
                "inputTokens": 500,
                "takeoverPacket": {
                    "contextGenerationId": "gen-1",
                    "tokenEstimate": 3001,
                },
            },
            {},
            limits(),
        )
        self.assertEqual(over_budget["decision"], "block")
        self.assertEqual(over_budget["reason"], "takeover_packet_over_budget")

        cold = context_governor.evaluate(
            {
                "inputTokens": 500,
                "takeoverPacket": {
                    "contextGenerationId": "gen-1",
                    "tokenEstimate": 1000,
                    "containsColdBody": True,
                },
            },
            {},
            limits(),
        )
        self.assertEqual(cold["reason"], "cold_body_forbidden")

    def test_takeover_packet_requires_positive_token_estimate(self) -> None:
        packet = valid_takeover_packet()
        packet.pop("tokenEstimate")
        missing = context_governor.evaluate(
            {"inputTokens": 500, "takeoverPacket": packet},
            {},
            limits(),
        )
        self.assertEqual(missing["decision"], "block")
        self.assertEqual(missing["reason"], "invalid_takeover_token_estimate")

        packet["tokenEstimate"] = 0
        zero = context_governor.evaluate(
            {"inputTokens": 500, "takeoverPacket": packet},
            {},
            limits(),
        )
        self.assertEqual(zero["reason"], "invalid_takeover_token_estimate")

    def test_takeover_packet_rejects_unflagged_cold_or_raw_body(self) -> None:
        cold = valid_takeover_packet()
        cold["items"] = [{"layer": "cold", "body": "short cold body"}]
        cold_result = context_governor.evaluate(
            {"inputTokens": 500, "takeoverPacket": cold},
            {},
            limits(),
        )
        self.assertEqual(cold_result["decision"], "block")
        self.assertEqual(cold_result["reason"], "forbidden_takeover_payload")

        raw = valid_takeover_packet()
        raw["messages"] = [{"content": "short raw chat"}]
        raw_result = context_governor.evaluate(
            {"inputTokens": 500, "takeoverPacket": raw},
            {},
            limits(),
        )
        self.assertEqual(raw_result["decision"], "block")
        self.assertEqual(raw_result["reason"], "takeover_packet_schema_invalid")

    def test_context_generation_id_is_injected_once(self) -> None:
        event = {
            "inputTokens": 500,
            "workspace": "/repo",
            "lane": "impl",
            "module": "docs",
            "projectIdentitySha256": "project-123",
            "takeoverPacket": valid_takeover_packet(),
        }
        first = context_governor.evaluate(event, {}, limits())
        self.assertEqual(first["decision"], "allow")
        self.assertEqual(first["nextAction"], "inject_takeover_packet_once")

        duplicate = context_governor.evaluate(event, first["state"], limits())
        self.assertEqual(duplicate["decision"], "block")
        self.assertEqual(duplicate["reason"], "duplicate_context_generation")
        self.assertEqual(duplicate["metrics"]["duplicateInjectionCount"], 1)
        self.assertEqual(duplicate["nextAction"], "skip_duplicate_context_injection")

    def test_forbidden_raw_payload_shape_freezes(self) -> None:
        result = context_governor.evaluate(
            {
                "inputTokens": 500,
                "rawChat": "not allowed",
            },
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "freeze")
        self.assertEqual(result["reason"], "forbidden_context_payload")
        self.assertIn("forbiddenFindings", result["metrics"])

    def test_same_generation_with_changed_basis_requires_new_generation(self) -> None:
        first = context_governor.evaluate(
            {
                "inputTokens": 500,
                "takeoverPacket": valid_takeover_packet(),
            },
            {},
            limits(),
        )
        changed_packet = valid_takeover_packet()
        changed_packet["head"] = "new-head"
        changed = context_governor.evaluate(
            {
                "inputTokens": 500,
                "takeoverPacket": changed_packet,
            },
            first["state"],
            limits(),
        )
        self.assertEqual(changed["decision"], "block")
        self.assertEqual(changed["reason"], "rotate_generation_required")

    def test_new_generation_requires_changed_verified_basis(self) -> None:
        first_event = {"taskId": "clean-task", "inputTokens": 500, "takeoverPacket": valid_takeover_packet()}
        first = context_governor.evaluate(first_event, {}, limits())

        unchanged = valid_takeover_packet("gen-2")
        blocked = context_governor.evaluate(
            {"taskId": "clean-task", "inputTokens": 500, "takeoverPacket": unchanged},
            first["state"],
            limits(),
        )
        self.assertEqual(blocked["decision"], "block")
        self.assertEqual(blocked["reason"], "generation_basis_unchanged")
        self.assertEqual(blocked["nextAction"], "reuse_existing_generation_without_reinjection")

        changed = valid_takeover_packet("gen-2")
        changed["verifiedMemoryStateHash"] = "verified-state-new"
        allowed = context_governor.evaluate(
            {"taskId": "clean-task", "inputTokens": 500, "takeoverPacket": changed},
            blocked["state"],
            limits(),
        )
        self.assertEqual(allowed["decision"], "allow")
        self.assertEqual(allowed["nextAction"], "inject_takeover_packet_once")
        self.assertIn("gen-1", allowed["state"]["invalidatedGenerationIds"])

    def test_realistic_zhixia_fallback_takeover_packet_fails_closed(self) -> None:
        result = context_governor.evaluate(
            {
                "inputTokens": 500,
                "takeoverPacket": {
                    "contextGenerationId": "rgs-fallback-1",
                    "tokenEstimate": 557,
                    "memoryMode": "fallback_stale",
                    "authorityVerification": "unavailable",
                    "current": False,
                    "recoveryReady": False,
                    "returnedCount": 0,
                    "takeover": {"shouldInject": False},
                    "head": "ac63d62c",
                    "scanHash": "scan-rgs",
                    "verifiedMemoryStateHash": "unverified",
                },
            },
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "fallback_stale")
        self.assertFalse(result["allowToolCalls"])
        self.assertFalse(result["allowProviderCalls"])
        self.assertEqual(result["nextAction"], "run_readonly_exact_scan")

    def test_takeover_packet_rejects_authority_shape_without_fail_open(self) -> None:
        packet = valid_takeover_packet()
        packet["memoryMode"] = "app_owned_memory_core"
        packet["authorityVerification"] = "unavailable"
        packet["current"] = True
        packet["recoveryReady"] = True
        packet["returnedCount"] = 6
        packet["takeover"] = {"shouldInject": True}
        result = context_governor.evaluate(
            {"inputTokens": 500, "takeoverPacket": packet},
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "authority_unavailable_for_claim")

    def test_takeover_packet_requires_non_empty_should_inject_true(self) -> None:
        empty_packet = valid_takeover_packet()
        empty_packet["returnedCount"] = 0
        empty_result = context_governor.evaluate(
            {"inputTokens": 500, "takeoverPacket": empty_packet},
            {},
            limits(),
        )
        self.assertEqual(empty_result["decision"], "block")
        self.assertEqual(empty_result["reason"], "retrieval_empty")

        no_inject_packet = valid_takeover_packet()
        no_inject_packet["takeover"] = {"shouldInject": False}
        no_inject_result = context_governor.evaluate(
            {"inputTokens": 500, "takeoverPacket": no_inject_packet},
            {},
            limits(),
        )
        self.assertEqual(no_inject_result["decision"], "block")
        self.assertEqual(no_inject_result["reason"], "should_inject_not_true")

    def test_takeover_packet_requires_current_and_recovery_ready(self) -> None:
        cases = [
            ("current", False, "current_not_true"),
            ("recoveryReady", False, "recovery_not_ready"),
        ]
        for field, value, reason in cases:
            with self.subTest(field=field):
                packet = valid_takeover_packet()
                packet[field] = value
                result = context_governor.evaluate(
                    {"inputTokens": 500, "takeoverPacket": packet},
                    {},
                    limits(),
                )
                self.assertEqual(result["decision"], "block")
                self.assertEqual(result["reason"], reason)

    def test_scan_unchanged_after_failed_verify_freezes_authority_defect(self) -> None:
        result = context_governor.evaluate(
            {
                "inputTokens": 500,
                "memory": {
                    "memoryMode": "fallback_stale",
                    "current": False,
                    "recoveryReady": False,
                    "authorityVerification": "unavailable",
                },
                "exactScan": {
                    "changed": False,
                    "previousScanSha256": "scan-a",
                    "currentScanSha256": "scan-a",
                },
            },
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "freeze")
        self.assertEqual(result["reason"], "authority_defect")
        self.assertEqual(result["metrics"]["validationReason"], "fallback_stale")

    def test_head_or_scan_change_invalidates_old_generation(self) -> None:
        first = context_governor.evaluate(
            {
                "inputTokens": 500,
                "workspace": "/repo",
                "lane": "impl",
                "module": "docs",
                "projectIdentitySha256": "project-123",
                "takeoverPacket": valid_takeover_packet(),
            },
            {},
            limits(),
        )
        changed = context_governor.evaluate(
            {
                "inputTokens": 500,
                "dispatchRequested": True,
                "head": "new-head",
                "scanHash": "b",
                "projectIdentitySha256": "project-123",
            },
            first["state"],
            limits(),
        )
        self.assertEqual(changed["decision"], "freeze")
        self.assertEqual(changed["reason"], "unaccepted_project_change")
        self.assertIn("gen-1", changed["state"]["invalidatedGenerationIds"])

    def test_heartbeat_and_tool_result_do_not_retrieve_or_inject(self) -> None:
        for event_type in ("heartbeat", "tool_result"):
            with self.subTest(event_type=event_type):
                result = context_governor.evaluate({"inputTokens": 20, "eventType": event_type}, {}, limits())
                self.assertEqual(result["decision"], "allow")
                self.assertEqual(result["reason"], "non_memory_event_no_retrieval")
                self.assertEqual(result["metrics"]["memoryRuntimeAction"], "skip")

    def test_accepted_single_file_scan_change_builds_refresh_request(self) -> None:
        first = context_governor.evaluate(
            {
                "inputTokens": 500,
                "workspace": "/repo",
                "lane": "impl",
                "module": "docs",
                "projectIdentitySha256": "project-123",
                "takeoverPacket": valid_takeover_packet(),
            },
            {},
            limits(),
        )
        result = context_governor.evaluate(
            {
                "inputTokens": 500,
                "dispatchRequested": True,
                "workspace": "/repo",
                "projectIdentitySha256": "project-123",
                "lane": "impl",
                "module": "docs",
                "acceptedEvidenceReceipt": {"receiptId": "qa-1", "decision": "accept"},
                "exactScan": {
                    "previousCheckpointId": "checkpoint-1",
                    "previousScanSha256": "b",
                    "currentScanSha256": "scan-new",
                    "changedPaths": ["docs/PRD.md"],
                },
            },
            first["state"],
            limits(),
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "refresh_binding_required")
        self.assertEqual(result["nextAction"], "run_direct_refresh_binding_driver")
        self.assertFalse(result["messagePolicy"]["sendCodexDelegation"])
        request = result["refreshBindingRequest"]
        self.assertEqual(request["operation"], "refresh_binding")
        self.assertEqual(request["workspace"], "/repo")
        self.assertTrue(request["execute"])
        self.assertEqual(request["previousCheckpointId"], "checkpoint-1")
        self.assertEqual(request["expectedProjectIdentitySha256"], "project-123")
        self.assertEqual(request["expectedScanSha256"], "scan-new")
        self.assertEqual(request["acceptedEvidenceReceipt"], "qa-1")
        self.assertEqual(request["acceptedChangedPaths"], ["docs/PRD.md"])
        self.assertNotIn("history", json.dumps(request).lower())

    def test_unaccepted_scan_change_freezes(self) -> None:
        for receipt in (None, {"receiptId": "qa-revise-1", "decision": "revise"}):
            with self.subTest(receipt=receipt):
                result = context_governor.evaluate(
                    {
                        "inputTokens": 500,
                        "dispatchRequested": True,
                        "acceptedEvidenceReceipt": receipt,
                        "exactScan": {
                            "previousScanSha256": "scan-old",
                            "currentScanSha256": "scan-new",
                            "changedPaths": ["src/index.ts"],
                        },
                    },
                    {},
                    limits(),
                )
                self.assertEqual(result["decision"], "freeze")
                self.assertEqual(result["reason"], "unaccepted_project_change")

    def test_packet_source_refs_must_match_project_lane_and_workspace(self) -> None:
        packet = valid_takeover_packet()
        packet["sourceRefs"] = [{"path": "/tmp/other/secret.md", "lane": "other", "module": "docs"}]
        result = context_governor.evaluate(
            {
                "inputTokens": 500,
                "workspace": "/repo",
                "lane": "impl",
                "module": "docs",
                "projectIdentitySha256": "project-123",
                "takeoverPacket": packet,
            },
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "source_refs_out_of_scope")

    def test_cli_updates_compact_state_without_yaml_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            event = tmp_path / "event.json"
            state = tmp_path / "state.json"
            event.write_text(json.dumps({"inputTokens": 1000}), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(event), "--state", str(state), "--write-state"],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["decision"], "allow")
            self.assertTrue(state.exists())
            saved = json.loads(state.read_text())
            self.assertEqual(saved["cumulativeInputTokens"], 1000)


if __name__ == "__main__":
    unittest.main()
