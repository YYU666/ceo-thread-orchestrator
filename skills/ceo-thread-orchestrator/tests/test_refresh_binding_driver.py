#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import context_governor  # noqa: E402
import refresh_binding_driver as driver  # noqa: E402


def limits() -> dict[str, int]:
    return {
        "inputTokenLimit": 120_000,
        "contextTokenLimit": 120_000,
        "cumulativeInputLimit": 10_000_000,
        "contextBytesLimit": 50 * 1024 * 1024,
        "takeoverTokenLimit": 3_000,
    }


def old_binding_state() -> dict[str, object]:
    packet = {
        "contextGenerationId": "context-old",
        "tokenEstimate": 900,
        "memoryMode": "app_owned_memory_core",
        "authorityVerification": "app_owned_verified",
        "current": True,
        "recoveryReady": True,
        "returnedCount": 4,
        "takeover": {"shouldInject": True},
        "head": "head-old",
        "scanHash": "scan-old",
        "projectIdentitySha256": "project-123",
        "verifiedMemoryStateHash": "checkpoint-old",
        "sourceRefs": [{"path": "docs/current-task.md", "lane": "module-core"}],
    }
    return context_governor.evaluate(
        {
            "taskId": "ceo-clean",
            "inputTokens": 500,
            "workspace": "/repo",
            "lane": "module-core",
            "projectIdentitySha256": "project-123",
            "takeoverPacket": packet,
        },
        {},
        limits(),
    )["state"]


def accepted_change_event() -> dict[str, object]:
    return {
        "taskId": "ceo-clean",
        "inputTokens": 500,
        "dispatchRequested": True,
        "workspace": "/repo",
        "taskGoal": "continue module core",
        "projectIdentitySha256": "project-123",
        "lane": "module-core",
        "acceptedEvidenceReceipt": {"receiptId": "qa-accept-0001", "decision": "accept"},
        "acceptedEvidence": {
            "phase": "core implementation",
            "summary": "The current task document passed QA.",
            "sourceRefs": [{"path": "/repo/docs/current-task.md", "hash": "source-hash"}],
        },
        "exactScan": {
            "changed": True,
            "previousCheckpointId": "checkpoint-old",
            "previousScanSha256": "scan-old",
            "currentScanSha256": "scan-new",
            "changedPaths": ["docs/current-task.md"],
            "sourceRefs": [{"path": "/repo/docs/current-task.md", "hash": "source-hash"}],
        },
    }


def refresh_response() -> dict[str, object]:
    return {
        "operation": "refresh_binding",
        "status": "verified",
        "memoryMode": "app_owned_memory_core",
        "authorityVerification": "app_owned_verified",
        "current": True,
        "recoveryReady": True,
        "scanSha256": "scan-new",
        "projectIdentity": {"projectIdentitySha256": "project-123"},
        "previousCheckpointId": "checkpoint-old",
        "authorizedCheckpointId": "checkpoint-new",
        "receiptId": "authority-decision-0001",
        "contextGenerationId": "context-new",
        "acceptedEvidenceReceipt": "qa-accept-0001",
        "acceptedChangedPaths": ["docs/current-task.md"],
        "takeover": {"shouldInject": True},
    }


def verify_response(*, matched: bool = True) -> dict[str, object]:
    return {
        "operation": "verify",
        "status": "verified" if matched else "not_ready",
        "memoryMode": "app_owned_memory_core" if matched else "fallback_stale",
        "authorityVerification": "app_owned_verified" if matched else "unavailable",
        "current": matched,
        "recoveryReady": matched,
        "projectIdentity": {"projectIdentitySha256": "project-123"},
        "scanBinding": {
            "matched": matched,
            "currentScanSha256": "scan-new",
            "authorizedCheckpointId": "checkpoint-new",
        },
    }


class FakeRuntime:
    def __init__(self, *, matched: bool = True, fail_refresh: bool = False) -> None:
        self.matched = matched
        self.fail_refresh = fail_refresh
        self.calls: list[dict[str, object]] = []

    def __call__(self, request: dict[str, object]) -> dict[str, object]:
        self.calls.append(request)
        if request["operation"] == "refresh_binding":
            if self.fail_refresh:
                raise RuntimeError("refresh_binding_previous_checkpoint_mismatch")
            return refresh_response()
        return verify_response(matched=self.matched)


class RefreshBindingDriverTest(unittest.TestCase):
    def test_accepted_change_directly_refreshes_verifies_and_resumes(self) -> None:
        runtime = FakeRuntime()
        result = driver.run(
            accepted_change_event(),
            old_binding_state(),
            {},
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
        )
        self.assertEqual([call["operation"] for call in runtime.calls], ["refresh_binding", "verify"])
        refresh = runtime.calls[0]
        self.assertTrue(refresh["execute"])
        self.assertEqual(refresh["expectedProjectIdentitySha256"], "project-123")
        self.assertEqual(refresh["expectedScanSha256"], "scan-new")
        self.assertEqual(refresh["acceptedChangedPaths"], ["docs/current-task.md"])
        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["nextAction"], "resume_related_lane_after_verified_binding")
        self.assertEqual(result["laneStatus"], "resumed")
        self.assertTrue(result["allowProviderCalls"])
        self.assertEqual(result["providerCallsBeforeMatched"], 0)
        self.assertEqual(result["knowledgeTaskMessages"], 0)
        self.assertFalse(result["sendCodexDelegation"])

    def test_same_scan_and_receipt_refreshes_at_most_once(self) -> None:
        runtime = FakeRuntime()
        first = driver.run(
            accepted_change_event(), old_binding_state(), {}, runtime, limits=limits(), verify_delay_seconds=0
        )
        second = driver.run(
            accepted_change_event(),
            first["governorState"],
            first["driverState"],
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
        )
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)
        self.assertEqual(second["decision"], "allow")
        attempt = next(iter(second["driverState"]["refreshAttempts"].values()))
        self.assertEqual(attempt["refreshCallCount"], 1)
        tampered = driver.run(
            accepted_change_event()
            | {"exactScan": dict(accepted_change_event()["exactScan"], previousCheckpointId="checkpoint-tampered")},
            second["governorState"],
            second["driverState"],
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
        )
        self.assertEqual(tampered["reason"], "refresh_attempt_evidence_changed")
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)

    def test_provider_remains_blocked_until_verify_matched(self) -> None:
        runtime = FakeRuntime(matched=False)
        result = driver.run(
            accepted_change_event(),
            old_binding_state(),
            {},
            runtime,
            limits=limits(),
            verify_attempts=2,
            verify_delay_seconds=0,
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "post_refresh_verify_not_ready")
        self.assertFalse(result["allowProviderCalls"])
        self.assertEqual(result["paidProviderCalls"], 0)
        self.assertEqual(result["providerCallsBeforeMatched"], 0)
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)

    def test_refresh_failure_blocks_only_related_lane(self) -> None:
        runtime = FakeRuntime(fail_refresh=True)
        result = driver.run(
            accepted_change_event(), old_binding_state(), {}, runtime, limits=limits(), verify_delay_seconds=0
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "refresh_binding_failed")
        self.assertEqual(result["scope"], "module-core")
        self.assertFalse(result["programGoalBlocked"])
        self.assertTrue(result["unrelatedLanesMayContinue"])
        self.assertFalse(result["allowProviderCalls"])
        self.assertEqual(result["paidProviderRetry"], 0)
        self.assertEqual(result["knowledgeTaskMessages"], 0)

    def test_failed_refresh_is_not_automatically_retried(self) -> None:
        runtime = FakeRuntime(fail_refresh=True)
        first = driver.run(
            accepted_change_event(), old_binding_state(), {}, runtime, limits=limits(), verify_delay_seconds=0
        )
        second = driver.run(
            accepted_change_event(),
            first["governorState"],
            first["driverState"],
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
        )
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)
        self.assertEqual(second["reason"], "duplicate_refresh_blocked")

    def test_unaccepted_or_stale_change_fails_closed_without_runtime_calls(self) -> None:
        cases = [
            accepted_change_event() | {"acceptedEvidenceReceipt": None},
            accepted_change_event()
            | {
                "acceptedEvidenceReceipt": None,
                "memory": {
                    "memoryMode": "fallback_stale",
                    "current": False,
                    "recoveryReady": False,
                    "authorityVerification": "unavailable",
                },
            },
        ]
        for event in cases:
            with self.subTest(memory=bool(event.get("memory"))):
                runtime = FakeRuntime()
                result = driver.run(event, old_binding_state(), {}, runtime, limits=limits(), verify_delay_seconds=0)
                self.assertIn(result["decision"], {"freeze", "block"})
                self.assertFalse(result["allowProviderCalls"])
                self.assertEqual(runtime.calls, [])
                self.assertEqual(result["knowledgeTaskMessages"], 0)

    def test_missing_exact_source_receipt_never_calls_refresh(self) -> None:
        event = accepted_change_event()
        event["acceptedEvidence"] = {"phase": "core", "summary": "accepted", "sourceRefs": []}
        event["exactScan"] = dict(event["exactScan"], sourceRefs=[])
        runtime = FakeRuntime()
        result = driver.run(event, old_binding_state(), {}, runtime, limits=limits(), verify_delay_seconds=0)
        self.assertEqual(result["reason"], "refresh_binding_request_invalid")
        self.assertEqual(runtime.calls, [])


if __name__ == "__main__":
    unittest.main()
