#!/usr/bin/env python3
from __future__ import annotations

import sys
import hashlib
import tempfile
import unittest
import json
import subprocess
from unittest import mock
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


TEST_WORKSPACE: Path | None = None
ACCEPTED_RECEIPT_DIGEST = "a" * 64
OUTCOME_DIGEST = "b" * 64


def workspace() -> Path:
    global TEST_WORKSPACE
    if TEST_WORKSPACE is None:
        TEST_WORKSPACE = Path(tempfile.mkdtemp(prefix="ceoflow-refresh-test-"))
        source = TEST_WORKSPACE / "docs/current-task.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("accepted task evidence\n", encoding="utf-8")
    return TEST_WORKSPACE


def source_hash() -> str:
    return hashlib.sha256((workspace() / "docs/current-task.md").read_bytes()).hexdigest()


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
            "workspace": str(workspace()),
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
        "workspace": str(workspace()),
        "taskGoal": "continue module core",
        "projectIdentitySha256": "project-123",
        "lane": "module-core",
        "acceptedEvidenceReceipt": {
            "receiptId": "qa-accept-0001",
            "decision": "accept",
            "acceptedEvidenceReceiptDigest": ACCEPTED_RECEIPT_DIGEST,
        },
        "acceptedEvidence": {
            "phase": "core implementation",
            "summary": "The current task document passed QA.",
            "sourceRefs": [{"path": "docs/current-task.md", "hash": source_hash()}],
        },
        "exactScan": {
            "changed": True,
            "previousCheckpointId": "checkpoint-old",
            "previousScanSha256": "scan-old",
            "currentScanSha256": "scan-new",
            "changedPaths": ["docs/current-task.md"],
            "sourceRefs": [{"path": "docs/current-task.md", "hash": source_hash()}],
        },
    }


def refresh_response(request: dict[str, object] | None = None) -> dict[str, object]:
    if request is None:
        request = context_governor.evaluate(
            accepted_change_event(), old_binding_state(), limits()
        )["refreshBindingRequest"]
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
        "acceptedEvidenceReceiptDigest": ACCEPTED_RECEIPT_DIGEST,
        "acceptedChangedPaths": ["docs/current-task.md"],
        "acceptedPathDigest": driver.accepted_path_digest(["docs/current-task.md"]),
        "lane": "module-core",
        "refreshKey": driver.refresh_key(request),
        "outcomeDigest": OUTCOME_DIGEST,
        "outcomeVerification": "app_owned_authenticated",
        "takeover": {"shouldInject": True},
    }


def started_attempt(request: dict[str, object]) -> dict[str, object]:
    paths = driver.canonical_changed_paths(request["acceptedChangedPaths"])
    return {
        "status": "started",
        "workspace": driver.canonical_workspace(request["workspace"]),
        "projectIdentitySha256": request["expectedProjectIdentitySha256"],
        "scanSha256": request["expectedScanSha256"],
        "acceptedEvidenceReceipt": request["acceptedEvidenceReceipt"],
        "acceptedEvidenceReceiptDigest": request["acceptedEvidenceReceiptDigest"],
        "previousCheckpointId": request["previousCheckpointId"],
        "acceptedChangedPaths": paths,
        "acceptedPathDigest": driver.accepted_path_digest(paths),
        "lane": request["lane"],
        "refreshKey": driver.refresh_key(request),
        "refreshCallCount": 1,
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
            return refresh_response(request)
        return verify_response(matched=self.matched)


class RefreshBindingDriverTest(unittest.TestCase):
    def test_v2_refresh_key_binds_complete_tuple_and_fresh_request(self) -> None:
        event = accepted_change_event()
        request = context_governor.evaluate(
            event, old_binding_state(), limits()
        )["refreshBindingRequest"]
        key = driver.refresh_key(request)
        self.assertEqual(
            driver.refresh_key(request | {"acceptedChangedPaths": list(reversed(request["acceptedChangedPaths"]))}),
            key,
        )
        mutations = {
            "workspace": str(workspace() / "other"),
            "expectedProjectIdentitySha256": "project-other",
            "expectedScanSha256": "scan-other",
            "previousCheckpointId": "checkpoint-other",
            "acceptedEvidenceReceipt": "qa-accept-other",
            "acceptedEvidenceReceiptDigest": "c" * 64,
            "acceptedChangedPaths": ["docs/other.md"],
            "lane": "module-other",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                self.assertNotEqual(driver.refresh_key(request | {field: value}), key)

        runtime_request = driver.runtime_refresh_request(request)
        self.assertEqual(runtime_request["refreshKey"], key)
        self.assertEqual(
            runtime_request["acceptedPathDigest"],
            driver.accepted_path_digest(request["acceptedChangedPaths"]),
        )
        self.assertEqual(runtime_request["lane"], "module-core")
        self.assertEqual(
            runtime_request["acceptedEvidenceReceiptDigest"], ACCEPTED_RECEIPT_DIGEST
        )

    def test_legacy_started_attempt_cannot_replay_after_v2_upgrade(self) -> None:
        event = accepted_change_event()
        governor = old_binding_state()
        request = context_governor.evaluate(event, governor, limits())["refreshBindingRequest"]
        legacy_key = driver.legacy_refresh_key(request)
        state = {
            "schema": driver.LEGACY_SCHEMA,
            "refreshAttempts": {
                legacy_key: {
                    "status": "started",
                    "workspace": request["workspace"],
                    "scanSha256": request["expectedScanSha256"],
                    "acceptedEvidenceReceipt": request["acceptedEvidenceReceipt"],
                    "refreshCallCount": 1,
                }
            },
            "laneRecovery": {},
        }
        runtime = FakeRuntime()
        result = driver.run(
            event,
            governor,
            state,
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            runtime_outcome_query=runtime,
        )
        self.assertEqual(
            result["reason"], "legacy_refresh_attempt_v2_reconciliation_required"
        )
        self.assertFalse(result["allowProviderCalls"])
        self.assertEqual(result["legacyRefreshKey"], legacy_key)
        self.assertEqual(runtime.calls, [])

    def test_receipt_digest_is_persisted_before_fresh_runtime_call(self) -> None:
        snapshots: list[dict[str, object]] = []
        runtime = FakeRuntime(fail_refresh=True)
        result = driver.run(
            accepted_change_event(),
            old_binding_state(),
            {},
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            persist_driver_state=lambda value: snapshots.append(json.loads(json.dumps(value))),
        )
        self.assertEqual(result["reason"], "refresh_binding_failed")
        started = next(iter(snapshots[0]["refreshAttempts"].values()))
        self.assertEqual(started["status"], "started")
        self.assertEqual(started["refreshKey"], driver.refresh_key(runtime.calls[0]))
        self.assertEqual(
            started["acceptedEvidenceReceiptDigest"], ACCEPTED_RECEIPT_DIGEST
        )
        self.assertEqual(started["lane"], "module-core")
        self.assertEqual(
            started["acceptedPathDigest"],
            driver.accepted_path_digest(["docs/current-task.md"]),
        )

    def test_missing_or_malformed_receipt_digest_never_reaches_runtime(self) -> None:
        for name, digest in (("missing", None), ("malformed", "not-a-sha256")):
            with self.subTest(name=name):
                event = accepted_change_event()
                receipt = dict(event["acceptedEvidenceReceipt"])
                if digest is None:
                    receipt.pop("acceptedEvidenceReceiptDigest", None)
                else:
                    receipt["acceptedEvidenceReceiptDigest"] = digest
                event["acceptedEvidenceReceipt"] = receipt
                runtime = FakeRuntime()
                result = driver.run(
                    event,
                    old_binding_state(),
                    {},
                    runtime,
                    limits=limits(),
                    verify_delay_seconds=0,
                )
                self.assertEqual(result["reason"], "unaccepted_project_change")
                self.assertFalse(result["allowProviderCalls"])
                self.assertEqual(runtime.calls, [])

    def test_started_attempt_requires_read_only_outcome_query_and_never_replays_refresh(self) -> None:
        event = accepted_change_event()
        governor = old_binding_state()
        request = context_governor.evaluate(event, governor, limits())["refreshBindingRequest"]
        key = driver.refresh_key(request)
        state = driver.default_driver_state()
        state["refreshAttempts"][key] = started_attempt(request)
        runtime = FakeRuntime()
        blocked = driver.run(event, governor, state, runtime, limits=limits(), verify_delay_seconds=0)
        self.assertEqual(blocked["reason"], "runtime_outcome_query_required")
        self.assertFalse(blocked["allowProviderCalls"])
        self.assertEqual(runtime.calls, [])

        query_calls: list[dict[str, object]] = []

        def query(request_payload: dict[str, object]) -> dict[str, object]:
            query_calls.append(request_payload)
            return refresh_response() | {
                "operation": "query_refresh_outcome",
                "refreshKey": key,
            }

        reconciled = driver.run(
            event,
            governor,
            state,
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            runtime_outcome_query=query,
        )
        self.assertEqual(reconciled["decision"], "allow")
        self.assertEqual(query_calls[0]["operation"], "query_refresh_outcome")
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 0)
        self.assertEqual(sum(call["operation"] == "verify" for call in runtime.calls), 1)

    def test_started_outcome_query_is_bounded_and_invalid_receipt_stays_closed(self) -> None:
        event = accepted_change_event()
        governor = old_binding_state()
        request = context_governor.evaluate(event, governor, limits())["refreshBindingRequest"]
        key = driver.refresh_key(request)
        state = driver.default_driver_state()
        state["refreshAttempts"][key] = started_attempt(request)
        runtime = FakeRuntime()
        queries = 0

        def invalid_query(_: dict[str, object]) -> dict[str, object]:
            nonlocal queries
            queries += 1
            return {"operation": "query_refresh_outcome", "status": "unknown"}

        first = driver.run(
            event,
            governor,
            state,
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            runtime_outcome_query=invalid_query,
        )
        second = driver.run(
            event,
            first["governorState"],
            first["driverState"],
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            runtime_outcome_query=invalid_query,
        )
        self.assertEqual(first["reason"], "runtime_outcome_receipt_invalid_no_poll")
        self.assertEqual(second["reason"], "runtime_outcome_query_exhausted_no_poll")
        self.assertFalse(second["allowProjectToolCalls"])
        self.assertEqual(queries, 1)
        self.assertEqual(runtime.calls, [])

    def test_started_outcome_requires_explicit_operation_and_exact_refresh_key(self) -> None:
        event = accepted_change_event()
        governor = old_binding_state()
        request = context_governor.evaluate(event, governor, limits())["refreshBindingRequest"]
        key = driver.refresh_key(request)
        for name, mutation in (
            ("missing_operation", {"operation": None, "refreshKey": key}),
            ("missing_key", {"operation": "query_refresh_outcome", "refreshKey": None}),
            ("wrong_key", {"operation": "query_refresh_outcome", "refreshKey": "wrong"}),
        ):
            with self.subTest(name=name):
                state = driver.default_driver_state()
                state["refreshAttempts"][key] = started_attempt(request)
                runtime = FakeRuntime()
                result = driver.run(
                    event,
                    governor,
                    state,
                    runtime,
                    limits=limits(),
                    verify_delay_seconds=0,
                    runtime_outcome_query=lambda _: refresh_response() | mutation,
                )
                self.assertEqual(result["reason"], "runtime_outcome_receipt_invalid_no_poll")
                self.assertFalse(result["allowProviderCalls"])
                self.assertEqual(runtime.calls, [])

    def test_started_outcome_rejects_wrong_v2_authentication_tuple(self) -> None:
        event = accepted_change_event()
        governor = old_binding_state()
        request = context_governor.evaluate(event, governor, limits())["refreshBindingRequest"]
        key = driver.refresh_key(request)
        mutations = (
            ("receipt_digest", {"acceptedEvidenceReceiptDigest": "c" * 64}),
            ("lane", {"lane": "module-other"}),
            ("key", {"refreshKey": "d" * 64}),
            ("outcome_digest", {"outcomeDigest": "not-a-sha256"}),
            ("authentication", {"outcomeVerification": "unverified"}),
        )
        for name, mutation in mutations:
            with self.subTest(name=name):
                state = driver.default_driver_state()
                state["refreshAttempts"][key] = started_attempt(request)
                runtime = FakeRuntime()
                queries = 0

                def query(_: dict[str, object]) -> dict[str, object]:
                    nonlocal queries
                    queries += 1
                    return refresh_response(request) | {
                        "operation": "query_refresh_outcome",
                        **mutation,
                    }

                result = driver.run(
                    event,
                    governor,
                    state,
                    runtime,
                    limits=limits(),
                    verify_delay_seconds=0,
                    runtime_outcome_query=query,
                )
                self.assertEqual(result["reason"], "runtime_outcome_receipt_invalid_no_poll")
                self.assertFalse(result["allowProviderCalls"])
                self.assertEqual(queries, 1)
                self.assertEqual(runtime.calls, [])

    def test_started_query_commits_governor_and_restart_never_replays_runtime(self) -> None:
        event = accepted_change_event()
        governor = old_binding_state()
        request = context_governor.evaluate(event, governor, limits())["refreshBindingRequest"]
        key = driver.refresh_key(request)
        state = driver.default_driver_state()
        state["refreshAttempts"][key] = started_attempt(request)
        runtime = FakeRuntime()
        queries: list[dict[str, object]] = []

        def query(payload: dict[str, object]) -> dict[str, object]:
            queries.append(payload)
            return refresh_response(request) | {"operation": "query_refresh_outcome"}

        recovered = driver.run(
            event,
            governor,
            state,
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            runtime_outcome_query=query,
        )
        self.assertEqual(recovered["decision"], "allow")
        committed = recovered["governorState"]["taskInjectionLedger"]["ceo-clean"]["verifiedRefresh"]
        self.assertEqual(committed["refreshKey"], key)
        self.assertEqual(committed["contextGenerationId"], "context-new")
        self.assertTrue(
            recovered["driverState"]["refreshAttempts"][key]["reconciledFromStarted"]
        )

        restarted = driver.run(
            event,
            recovered["governorState"],
            recovered["driverState"],
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
        )
        self.assertEqual(restarted["decision"], "allow")
        self.assertEqual(restarted["reason"], "refresh_binding_already_verified_no_poll")
        self.assertEqual(len(queries), 1)
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 0)
        self.assertEqual(sum(call["operation"] == "verify" for call in runtime.calls), 1)

    def test_deep_driver_and_durability_state_fail_closed_before_copy(self) -> None:
        nested: dict[str, object] = {}
        cursor = nested
        for _ in range(2000):
            child: dict[str, object] = {}
            cursor["next"] = child
            cursor = child
        for name, driver_state, confirmations in (
            ("driver", nested, {}),
            ("durability", {}, nested),
        ):
            with self.subTest(name=name):
                runtime = FakeRuntime()
                result = driver.run(
                    accepted_change_event(),
                    old_binding_state(),
                    driver_state,
                    runtime,
                    limits=limits(),
                    durability_confirmations=confirmations,
                )
                self.assertEqual(result["decision"], "block")
                self.assertIn("structure_depth_limit_exceeded", result["reason"])
                self.assertFalse(result["allowProviderCalls"])
                self.assertEqual(runtime.calls, [])

    def test_post_replace_driver_ambiguity_reconciles_without_second_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            driver_path = root / "driver.json"
            governor_path = root / "governor.json"
            confirmation_path = root / "durability.json"
            driver.atomic_state.atomic_write_json(driver_path, {})
            driver.atomic_state.atomic_write_json(governor_path, old_binding_state())
            runtime = FakeRuntime()
            driver_sha = driver.atomic_state.state_sha256({})
            governor_sha = driver.atomic_state.state_sha256(old_binding_state())
            write_count = 0

            def persist_driver(value: dict[str, object]) -> None:
                nonlocal driver_sha, write_count
                write_count += 1
                fail_final = write_count == 4
                if fail_final:
                    real_sync = driver.atomic_state.fsync_directory
                    sync_calls = 0

                    def fail_target_sync(path: Path) -> bool:
                        nonlocal sync_calls
                        sync_calls += 1
                        if sync_calls == 2:
                            raise driver.atomic_state.StateDurabilityError(
                                "simulated_final_driver_directory_fsync"
                            )
                        return real_sync(path)

                    with mock.patch.object(
                        driver.atomic_state, "fsync_directory", side_effect=fail_target_sync
                    ):
                        driver_sha = driver.atomic_state.atomic_write_json(
                            driver_path, value, expected_sha256=driver_sha
                        )
                else:
                    driver_sha = driver.atomic_state.atomic_write_json(
                        driver_path, value, expected_sha256=driver_sha
                    )

            def persist_governor(value: dict[str, object]) -> None:
                nonlocal governor_sha
                governor_sha = driver.atomic_state.atomic_write_json(
                    governor_path, value, expected_sha256=governor_sha
                )

            confirmation_sha = driver.atomic_state.state_sha256({})

            def persist_confirmation(value: dict[str, object]) -> None:
                nonlocal confirmation_sha
                confirmation_sha = driver.atomic_state.atomic_write_json(
                    confirmation_path, value, expected_sha256=confirmation_sha
                )

            with self.assertRaises(driver.atomic_state.StateDurabilityError):
                driver.run(
                    accepted_change_event(),
                    driver.atomic_state.read_json(governor_path),
                    driver.atomic_state.read_json(driver_path),
                    runtime,
                    limits=limits(),
                    verify_delay_seconds=0,
                    persist_driver_state=persist_driver,
                    persist_governor_state=persist_governor,
                    durability_confirmations={},
                    persist_durability_confirmation=persist_confirmation,
                )
            self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)
            self.assertTrue(
                driver.atomic_state.has_uncertainty(driver_path)
                or driver.atomic_state.has_confirmation(driver_path)
            )
            self.assertFalse(confirmation_path.exists())

            filesystem = driver.reconcile_marked_state_files(
                [governor_path, driver_path, confirmation_path]
            )
            self.assertEqual(
                filesystem["reason"], "filesystem_state_reconciled_retry_required", filesystem
            )
            self.assertFalse(filesystem["allowProviderCalls"])

            persisted_driver = driver.atomic_state.read_json(driver_path)
            persisted_governor = driver.atomic_state.read_json(governor_path)
            confirmations: dict[str, object] = {}
            driver_sha = driver.atomic_state.state_sha256(persisted_driver)
            governor_sha = driver.atomic_state.state_sha256(persisted_governor)
            confirmation_sha = driver.atomic_state.state_sha256(confirmations)
            reconciled = driver.run(
                accepted_change_event(),
                persisted_governor,
                persisted_driver,
                runtime,
                limits=limits(),
                verify_delay_seconds=0,
                persist_driver_state=persist_driver,
                persist_governor_state=persist_governor,
                durability_confirmations=confirmations,
                persist_durability_confirmation=persist_confirmation,
            )
            self.assertEqual(reconciled["reason"], "refresh_durability_reconciled_retry_required")
            self.assertFalse(reconciled["allowProviderCalls"])
            self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)

            allowed = driver.run(
                accepted_change_event(),
                driver.atomic_state.read_json(governor_path),
                driver.atomic_state.read_json(driver_path),
                runtime,
                limits=limits(),
                verify_delay_seconds=0,
                durability_confirmations=driver.atomic_state.read_json(confirmation_path),
            )
            self.assertEqual(allowed["reason"], "refresh_binding_already_verified_no_poll")
            self.assertTrue(allowed["allowProviderCalls"])
            self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)

    def test_post_replace_confirmation_ambiguity_blocks_then_reconciles_without_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            driver_path = root / "driver.json"
            governor_path = root / "governor.json"
            confirmation_path = root / "driver.json.durability.json"
            initial_governor = old_binding_state()
            driver.atomic_state.atomic_write_json(driver_path, {})
            driver.atomic_state.atomic_write_json(governor_path, initial_governor)
            runtime = FakeRuntime()
            driver_sha = driver.atomic_state.state_sha256({})
            governor_sha = driver.atomic_state.state_sha256(initial_governor)
            confirmation_sha = driver.atomic_state.state_sha256({})

            def persist_driver(value: dict[str, object]) -> None:
                nonlocal driver_sha
                driver_sha = driver.atomic_state.atomic_write_json(
                    driver_path, value, expected_sha256=driver_sha
                )

            def persist_governor(value: dict[str, object]) -> None:
                nonlocal governor_sha
                governor_sha = driver.atomic_state.atomic_write_json(
                    governor_path, value, expected_sha256=governor_sha
                )

            def persist_confirmation(value: dict[str, object]) -> None:
                nonlocal confirmation_sha

                def crash_after_replace(_: Path) -> None:
                    raise RuntimeError("simulated_confirmation_after_replace")

                confirmation_sha = driver.atomic_state.atomic_write_json(
                    confirmation_path,
                    value,
                    expected_sha256=confirmation_sha,
                    after_replace=crash_after_replace,
                )

            with self.assertRaisesRegex(RuntimeError, "confirmation_after_replace"):
                driver.run(
                    accepted_change_event(),
                    initial_governor,
                    {},
                    runtime,
                    limits=limits(),
                    verify_delay_seconds=0,
                    persist_driver_state=persist_driver,
                    persist_governor_state=persist_governor,
                    durability_confirmations={},
                    persist_durability_confirmation=persist_confirmation,
                )
            self.assertTrue(driver.atomic_state.has_uncertainty(confirmation_path))
            self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)

            filesystem = driver.reconcile_marked_state_files(
                [governor_path, driver_path, confirmation_path]
            )
            self.assertEqual(
                filesystem["reason"], "filesystem_state_reconciled_retry_required", filesystem
            )
            self.assertFalse(filesystem["allowProviderCalls"])
            self.assertFalse(filesystem["allowProjectToolCalls"])

            allowed = driver.run(
                accepted_change_event(),
                driver.atomic_state.read_json(governor_path),
                driver.atomic_state.read_json(driver_path),
                runtime,
                limits=limits(),
                verify_delay_seconds=0,
                durability_confirmations=driver.atomic_state.read_json(confirmation_path),
            )
            self.assertEqual(allowed["reason"], "refresh_binding_already_verified_no_poll")
            self.assertTrue(allowed["allowProviderCalls"])
            self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)

    def test_governor_post_replace_ambiguity_has_reachable_local_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            driver_path = root / "driver.json"
            governor_path = root / "governor.json"
            confirmation_path = root / "durability.json"
            initial_governor = old_binding_state()
            driver.atomic_state.atomic_write_json(driver_path, {})
            driver.atomic_state.atomic_write_json(governor_path, initial_governor)
            runtime = FakeRuntime()
            driver_sha = driver.atomic_state.state_sha256({})
            governor_sha = driver.atomic_state.state_sha256(initial_governor)
            confirmation_sha = driver.atomic_state.state_sha256({})
            fail_governor_once = True

            def persist_driver(value: dict[str, object]) -> None:
                nonlocal driver_sha
                driver_sha = driver.atomic_state.atomic_write_json(
                    driver_path, value, expected_sha256=driver_sha
                )

            def persist_governor(value: dict[str, object]) -> None:
                nonlocal governor_sha, fail_governor_once
                if fail_governor_once:
                    fail_governor_once = False
                    real_sync = driver.atomic_state.fsync_directory
                    sync_calls = 0

                    def fail_target_sync(path: Path) -> bool:
                        nonlocal sync_calls
                        sync_calls += 1
                        if sync_calls == 2:
                            raise driver.atomic_state.StateDurabilityError(
                                "simulated_governor_directory_fsync"
                            )
                        return real_sync(path)

                    with mock.patch.object(
                        driver.atomic_state, "fsync_directory", side_effect=fail_target_sync
                    ):
                        governor_sha = driver.atomic_state.atomic_write_json(
                            governor_path, value, expected_sha256=governor_sha
                        )
                else:
                    governor_sha = driver.atomic_state.atomic_write_json(
                        governor_path, value, expected_sha256=governor_sha
                    )

            def persist_confirmation(value: dict[str, object]) -> None:
                nonlocal confirmation_sha
                confirmation_sha = driver.atomic_state.atomic_write_json(
                    confirmation_path, value, expected_sha256=confirmation_sha
                )

            first = driver.run(
                accepted_change_event(),
                initial_governor,
                {},
                runtime,
                limits=limits(),
                verify_delay_seconds=0,
                persist_driver_state=persist_driver,
                persist_governor_state=persist_governor,
                durability_confirmations={},
                persist_durability_confirmation=persist_confirmation,
            )
            self.assertEqual(first["reason"], "refresh_state_reconciliation_required")
            self.assertFalse(first["allowProviderCalls"])
            self.assertTrue(
                driver.atomic_state.has_uncertainty(governor_path)
                or driver.atomic_state.has_confirmation(governor_path)
            )
            self.assertEqual(driver.atomic_state.read_json(driver_path)["refreshAttempts"].popitem()[1]["status"], "governor_commit_failed")

            filesystem = driver.reconcile_marked_state_files(
                [governor_path, driver_path, confirmation_path]
            )
            self.assertEqual(filesystem["reason"], "filesystem_state_reconciled_retry_required")
            disk_driver = driver.atomic_state.read_json(driver_path)
            disk_governor = driver.atomic_state.read_json(governor_path)
            driver_sha = driver.atomic_state.state_sha256(disk_driver)
            governor_sha = driver.atomic_state.state_sha256(disk_governor)
            confirmed = driver.run(
                accepted_change_event(),
                disk_governor,
                disk_driver,
                runtime,
                limits=limits(),
                verify_delay_seconds=0,
                persist_driver_state=persist_driver,
                persist_governor_state=persist_governor,
                durability_confirmations={},
                persist_durability_confirmation=persist_confirmation,
            )
            self.assertIn(
                confirmed["reason"],
                {
                    "refresh_state_reconciled_retry_required",
                    "refresh_durability_reconciled_retry_required",
                },
            )
            self.assertFalse(confirmed["allowProviderCalls"])
            if confirmed["reason"] == "refresh_state_reconciled_retry_required":
                confirmed = driver.run(
                    accepted_change_event(),
                    driver.atomic_state.read_json(governor_path),
                    driver.atomic_state.read_json(driver_path),
                    runtime,
                    limits=limits(),
                    verify_delay_seconds=0,
                    persist_driver_state=persist_driver,
                    persist_governor_state=persist_governor,
                    durability_confirmations={},
                    persist_durability_confirmation=persist_confirmation,
                )
                self.assertEqual(
                    confirmed["reason"], "refresh_durability_reconciled_retry_required"
                )
                self.assertFalse(confirmed["allowProviderCalls"])
            allowed = driver.run(
                accepted_change_event(),
                driver.atomic_state.read_json(governor_path),
                driver.atomic_state.read_json(driver_path),
                runtime,
                limits=limits(),
                verify_delay_seconds=0,
                durability_confirmations=driver.atomic_state.read_json(confirmation_path),
            )
            self.assertTrue(allowed["allowProviderCalls"])
            self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)

    def test_governor_cas_conflict_reconciles_without_duplicate_or_second_refresh(self) -> None:
        runtime = FakeRuntime()
        disk_driver: dict[str, object] = {}
        disk_governor = old_binding_state()
        fail_once = True

        def persist_driver(value: dict[str, object]) -> None:
            nonlocal disk_driver
            disk_driver = json.loads(json.dumps(value))

        def persist_governor(value: dict[str, object]) -> None:
            nonlocal disk_governor, fail_once
            if fail_once:
                fail_once = False
                raise driver.atomic_state.StateConflictError("simulated_real_cas_conflict")
            disk_governor = json.loads(json.dumps(value))

        confirmations: dict[str, object] = {}

        def persist_confirmation(value: dict[str, object]) -> None:
            nonlocal confirmations
            confirmations = json.loads(json.dumps(value))

        first = driver.run(
            accepted_change_event(),
            disk_governor,
            disk_driver,
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            persist_driver_state=persist_driver,
            persist_governor_state=persist_governor,
            durability_confirmations=confirmations,
            persist_durability_confirmation=persist_confirmation,
        )
        self.assertEqual(first["reason"], "refresh_state_reconciliation_required")
        repaired = driver.run(
            accepted_change_event(),
            disk_governor,
            disk_driver,
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            persist_driver_state=persist_driver,
            persist_governor_state=persist_governor,
            durability_confirmations=confirmations,
            persist_durability_confirmation=persist_confirmation,
        )
        self.assertEqual(repaired["reason"], "refresh_state_reconciled_retry_required")
        confirmed = driver.run(
            accepted_change_event(),
            disk_governor,
            disk_driver,
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            persist_driver_state=persist_driver,
            persist_governor_state=persist_governor,
            durability_confirmations=confirmations,
            persist_durability_confirmation=persist_confirmation,
        )
        self.assertEqual(confirmed["reason"], "refresh_durability_reconciled_retry_required")
        allowed = driver.run(
            accepted_change_event(),
            disk_governor,
            disk_driver,
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            durability_confirmations=confirmations,
        )
        self.assertTrue(allowed["allowProviderCalls"])
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)
    def test_refresh_identity_ignores_caller_labels_and_aliases_cannot_repeat_runtime(self) -> None:
        baseline = accepted_change_event()
        request = context_governor.evaluate(baseline, old_binding_state(), limits())["refreshBindingRequest"]
        aliases = []
        for project_key, project_id in (("forged-A", "A"), ("forged-B", "B"), ("forged-C", "C")):
            aliased = dict(request, projectKey=project_key, projectId=project_id)
            aliases.append(driver.refresh_key(aliased))
        self.assertEqual(len(set(aliases + [driver.refresh_key(request)])), 1)

        runtime = FakeRuntime()
        first = driver.run(
            baseline,
            old_binding_state(),
            {},
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
        )
        self.assertEqual(first["decision"], "allow")

        state = first["driverState"]
        governor = first["governorState"]
        for field, values in (
            ("activeProjectKey", ("forged-A", "forged-B", "forged-C")),
            ("projectId", ("A", "B")),
        ):
            for value in values:
                with self.subTest(field=field, value=value):
                    event = accepted_change_event() | {field: value}
                    result = driver.run(
                        event,
                        governor,
                        state,
                        runtime,
                        limits=limits(),
                        verify_delay_seconds=0,
                    )
                    self.assertEqual(result["reason"], "refresh_project_namespace_unregistered")
                    self.assertFalse(result["allowProviderCalls"])
                    self.assertEqual(result["decision"], "block")
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)

    def test_single_project_refresh_requires_governor_verified_workspace_and_identity(self) -> None:
        for name, mutate in (
            ("missing_workspace", lambda state: state["taskInjectionLedger"]["ceo-clean"].pop("workspace")),
            (
                "wrong_workspace",
                lambda state: state["taskInjectionLedger"]["ceo-clean"].update(workspace="/tmp/other-project"),
            ),
            (
                "wrong_identity",
                lambda state: state["taskInjectionLedger"]["ceo-clean"]["lastGenerationBasis"].update(
                    projectIdentitySha256="project-other"
                ),
            ),
        ):
            with self.subTest(name=name):
                governor = old_binding_state()
                mutate(governor)
                runtime = FakeRuntime()
                result = driver.run(
                    accepted_change_event(),
                    governor,
                    {},
                    runtime,
                    limits=limits(),
                    verify_delay_seconds=0,
                )
                self.assertEqual(result["reason"], "refresh_single_project_identity_mismatch")
                self.assertFalse(result["allowProviderCalls"])
                self.assertEqual(runtime.calls, [])

    def test_registered_project_refresh_uses_exact_governor_namespace(self) -> None:
        root = str(workspace().resolve())
        governor = old_binding_state()
        governor["projectWorkspacesByTask"] = {
            "ceo-clean": [{"projectKey": "alpha", "workspace": root, "projectId": "project-alpha"}]
        }
        governor["projectInjectionLedger"] = {
            "ceo-clean": {
                "alpha": {
                    "workspace": root,
                    "projectId": "project-alpha",
                    "bootstrapStatus": "ready",
                    "injectedGenerationIds": ["context-old"],
                    "lastGenerationBasis": {
                        "head": "head-old",
                        "scanHash": "scan-old",
                        "projectIdentitySha256": "project-123",
                        "verifiedMemoryStateHash": "checkpoint-old",
                    },
                    "invalidatedGenerationIds": [],
                    "authority": {},
                }
            }
        }
        event = accepted_change_event() | {
            "activeProjectKey": "alpha",
        }
        event["acceptedEvidence"] = dict(event["acceptedEvidence"])
        event["acceptedEvidence"]["sourceRefs"] = [
            {
                "path": "docs/current-task.md",
                "hash": source_hash(),
                "projectId": "project-alpha",
            }
        ]
        event["exactScan"] = dict(event["exactScan"])
        event["exactScan"]["sourceRefs"] = event["acceptedEvidence"]["sourceRefs"]
        runtime = FakeRuntime()
        result = driver.run(
            event,
            governor,
            {},
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
        )
        self.assertEqual(result["decision"], "allow")
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)
        ledger = result["governorState"]["projectInjectionLedger"]["ceo-clean"]["alpha"]
        self.assertEqual(ledger["verifiedRefresh"]["namespace"], "registered:alpha")

    def test_durability_failure_before_runtime_never_reopens_provider(self) -> None:
        runtime = FakeRuntime()

        def fail_driver_persist(_: dict[str, object]) -> None:
            raise driver.atomic_state.StateDurabilityError("directory_fsync_failed")

        with self.assertRaises(driver.atomic_state.StateDurabilityError):
            driver.run(
                accepted_change_event(),
                old_binding_state(),
                {},
                runtime,
                limits=limits(),
                verify_delay_seconds=0,
                persist_driver_state=fail_driver_persist,
            )
        self.assertEqual(runtime.calls, [])

    def test_governor_directory_durability_failure_blocks_provider_reopen(self) -> None:
        runtime = FakeRuntime()

        def fail_governor_persist(_: dict[str, object]) -> None:
            raise driver.atomic_state.StateDurabilityError("directory_fsync_failed")

        result = driver.run(
            accepted_change_event(),
            old_binding_state(),
            {},
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            persist_governor_state=fail_governor_persist,
        )
        self.assertEqual(result["reason"], "refresh_state_reconciliation_required")
        self.assertFalse(result["allowProviderCalls"])
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)

    def test_refresh_request_rejects_cross_project_absolute_source_ref(self) -> None:
        request = {
            "projectKey": "alpha",
            "projectId": "project-alpha",
            "workspace": "/projects/Alpha",
            "execute": True,
            "expectedProjectIdentitySha256": "identity-alpha",
            "expectedScanSha256": "scan-alpha",
            "previousCheckpointId": "checkpoint-alpha",
            "acceptedEvidenceReceipt": "qa-accept-alpha-001",
            "acceptedChangedPaths": ["docs/acceptance.md"],
            "lane": "audit",
            "evidence": {
                "decision": "accept",
                "sourceRefs": [
                    {
                        "path": "/projects/Beta/docs/acceptance.md",
                        "hash": "wrong-root",
                        "projectId": "project-beta",
                    }
                ],
            },
        }
        missing = driver.validate_refresh_request(request)
        self.assertIn("cross-project evidence.sourceRefs", missing)

        request["evidence"]["sourceRefs"] = [
            {"path": "../Beta/docs/acceptance.md", "hash": "wrong-root", "projectId": "project-alpha"}
        ]
        missing = driver.validate_refresh_request(request)
        self.assertIn("cross-project evidence.sourceRefs", missing)

    def test_project_routing_metadata_is_not_sent_to_runtime(self) -> None:
        request = {
            "projectKey": "alpha",
            "projectId": "project-alpha",
            "workspace": "/projects/Alpha",
            "operation": "refresh_binding",
        }
        runtime_request = driver.runtime_refresh_request(request)
        self.assertEqual(runtime_request["workspace"], "/projects/Alpha")
        self.assertNotIn("projectKey", runtime_request)
        self.assertNotIn("projectId", runtime_request)

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
        ledger = result["governorState"]["taskInjectionLedger"]["ceo-clean"]
        self.assertIn("context-new", ledger["injectedGenerationIds"])
        self.assertEqual(ledger["lastGenerationBasis"]["scanHash"], "scan-new")
        self.assertEqual(ledger["lastGenerationBasis"]["verifiedMemoryStateHash"], "checkpoint-new")

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
        attempt["previousCheckpointId"] = "checkpoint-tampered"
        tampered = driver.run(
            accepted_change_event(),
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
        self.assertFalse(result["allowToolCalls"])
        self.assertFalse(result["allowProjectToolCalls"])
        self.assertFalse(result["allowRecoveryControlTools"])
        self.assertEqual(result["recoveryControlToolAllowlist"], [])
        self.assertEqual(result["paidProviderCalls"], 0)
        self.assertEqual(result["providerCallsBeforeMatched"], 0)
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)

    def test_same_refresh_key_runs_one_bounded_verify_sequence_then_no_poll(self) -> None:
        runtime = FakeRuntime(matched=False)
        first = driver.run(
            accepted_change_event(),
            old_binding_state(),
            {},
            runtime,
            limits=limits(),
            verify_attempts=6,
            max_verify_calls_per_key=3,
            verify_delay_seconds=0,
        )
        second = driver.run(
            accepted_change_event(),
            first["governorState"],
            first["driverState"],
            runtime,
            limits=limits(),
            verify_attempts=6,
            max_verify_calls_per_key=3,
            verify_delay_seconds=0,
        )
        third = driver.run(
            accepted_change_event(),
            second["governorState"],
            second["driverState"],
            runtime,
            limits=limits(),
            verify_attempts=6,
            max_verify_calls_per_key=3,
            verify_delay_seconds=0,
        )
        self.assertEqual(first["reason"], "post_refresh_verify_not_ready")
        self.assertEqual(second["reason"], "verify_retry_exhausted_no_poll")
        self.assertFalse(second["allowRecoveryControlTools"])
        self.assertEqual(second["recoveryControlToolAllowlist"], [])
        self.assertEqual(third["reason"], "verify_retry_exhausted_no_poll")
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)
        self.assertEqual(sum(call["operation"] == "verify" for call in runtime.calls), 3)

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
        self.assertEqual(result["lifecycleState"], "lane_paused_recoverable")
        self.assertTrue(result["autoRecoveryEligible"])
        self.assertFalse(result["userAuthorizationRequired"])
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

    def test_new_scan_and_formal_receipt_get_one_new_bounded_attempt(self) -> None:
        failing = FakeRuntime(fail_refresh=True)
        first = driver.run(
            accepted_change_event(), old_binding_state(), {}, failing, limits=limits(), verify_delay_seconds=0
        )
        event = accepted_change_event()
        event["acceptedEvidenceReceipt"] = {
            "receiptId": "qa-accept-0002",
            "decision": "accept",
            "acceptedEvidenceReceiptDigest": "c" * 64,
        }
        event["exactScan"] = dict(event["exactScan"], currentScanSha256="scan-newer")

        class NewRuntime(FakeRuntime):
            def __call__(self, request: dict[str, object]) -> dict[str, object]:
                self.calls.append(request)
                if request["operation"] == "refresh_binding":
                    response = refresh_response(request)
                    response["scanSha256"] = "scan-newer"
                    response["acceptedEvidenceReceipt"] = "qa-accept-0002"
                    response["acceptedEvidenceReceiptDigest"] = "c" * 64
                    response["contextGenerationId"] = "context-newer"
                    return response
                response = verify_response()
                response["scanBinding"]["currentScanSha256"] = "scan-newer"
                return response

        recovered_runtime = NewRuntime()
        recovered = driver.run(
            event,
            first["governorState"],
            first["driverState"],
            recovered_runtime,
            limits=limits(),
            verify_delay_seconds=0,
        )
        self.assertEqual(recovered["decision"], "allow")
        self.assertEqual(recovered["lifecycleState"], "active")
        self.assertTrue(recovered["resumeProgramGoal"])
        self.assertTrue(recovered["clearHistoricalGoalBlocked"])
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in recovered_runtime.calls), 1)

    def test_verified_refresh_can_clear_historical_host_block_without_repeating_refresh(self) -> None:
        event = accepted_change_event() | {"historicalProgramGoalBlocked": True}
        runtime = FakeRuntime()
        result = driver.run(event, old_binding_state(), {}, runtime, limits=limits(), verify_delay_seconds=0)
        self.assertEqual(result["decision"], "allow")
        self.assertTrue(result["resumeProgramGoal"])
        self.assertTrue(result["clearHistoricalGoalBlocked"])

    def test_verified_driver_state_without_governor_commit_fails_closed(self) -> None:
        runtime = FakeRuntime()
        first = driver.run(
            accepted_change_event(), old_binding_state(), {}, runtime, limits=limits(), verify_delay_seconds=0
        )
        stale_governor = old_binding_state()
        second = driver.run(
            accepted_change_event(),
            stale_governor,
            first["driverState"],
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
        )
        self.assertEqual(second["reason"], "refresh_state_reconciled_retry_required")
        self.assertFalse(second["allowProviderCalls"])
        self.assertEqual(sum(call["operation"] == "refresh_binding" for call in runtime.calls), 1)

    def test_governor_commit_failure_never_opens_provider_or_verified_fast_path(self) -> None:
        runtime = FakeRuntime()

        def fail_commit(_: dict[str, object]) -> None:
            raise driver.atomic_state.StateConflictError("simulated governor CAS conflict")

        result = driver.run(
            accepted_change_event(),
            old_binding_state(),
            {},
            runtime,
            limits=limits(),
            verify_delay_seconds=0,
            persist_governor_state=fail_commit,
        )
        self.assertEqual(result["reason"], "refresh_state_reconciliation_required")
        self.assertFalse(result["allowProviderCalls"])
        attempt = next(iter(result["driverState"]["refreshAttempts"].values()))
        self.assertEqual(attempt["status"], "governor_commit_failed")

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

    def test_cli_tampered_state_blocks_before_runtime_or_any_call_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_path = root / "event.json"
            governor_path = root / "governor.json"
            driver_path = root / "driver.json"
            durability_path = root / "durability.json"
            event_path.write_text(json.dumps(accepted_change_event()), encoding="utf-8")
            driver.atomic_state.atomic_write_json(governor_path, old_binding_state())
            driver.atomic_state.atomic_write_json(driver_path, {})
            driver.atomic_state.atomic_write_json(durability_path, {})
            governor_path.write_text(json.dumps({"allowProviderCalls": True}), encoding="utf-8")
            governor_path.chmod(0o600)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "refresh_binding_driver.py"),
                    str(event_path),
                    "--governor-state",
                    str(governor_path),
                    "--driver-state",
                    str(driver_path),
                    "--durability-state",
                    str(durability_path),
                    "--runtime",
                    str(root / "must-not-run.cjs"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 2)
            result = json.loads(completed.stdout)
            self.assertEqual(result["decision"], "block")
            self.assertFalse(result["allowToolCalls"])
            self.assertFalse(result["allowProjectToolCalls"])
            self.assertFalse(result["allowProviderCalls"])
            self.assertFalse(result["allowOldThreadExecution"])


if __name__ == "__main__":
    unittest.main()
