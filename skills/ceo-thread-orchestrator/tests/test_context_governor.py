#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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


def preflight_fields(
    task_id: str,
    request_id: str,
    *,
    projected: int = 20_000,
    compaction_count: int = 0,
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema": context_governor.HOST_TELEMETRY_SCHEMA,
        "telemetrySource": "codex_host",
        "metricScope": "current_post_compaction_context",
        "capturedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "taskId": task_id,
        "lastRequestInputTokens": 500,
        "currentPostCompactionContextTokens": 18_000,
        "projectedNextRequestInputTokens": projected,
        "estimatedContextBytes": 80_000,
        "modelContextWindowTokens": 200_000,
        "reservedOutputTokens": 8_000,
        "cumulativeInputTokens": 500,
        "contextCompactionCount": compaction_count,
        "compactionCountSource": context_governor.HOST_COMPACTION_SOURCE,
    }
    receipt["hostTelemetryReceiptId"] = context_governor.host_telemetry_receipt_sha256(receipt)
    return {
        "taskId": task_id,
        "eventType": "model_request_preflight",
        "requestId": request_id,
        "hostTelemetryReceipt": receipt,
        "_hostTelemetryCapability": context_governor.HOST_TELEMETRY_CAPABILITY,
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


def scoped_takeover_packet(workspace: str, project_id: str, generation_id: str = "shared-gen") -> dict[str, object]:
    packet = valid_takeover_packet(generation_id)
    packet["workspace"] = workspace
    packet["projectId"] = project_id
    packet["projectIdentitySha256"] = f"identity-{project_id}"
    packet["sourceRefs"] = [
        {"path": f"{workspace}/docs/PROGRAM_GOAL.md", "projectId": project_id, "lane": "audit"}
    ]
    receipt = {
        "workspace": workspace,
        "projectId": project_id,
        "projectIdentitySha256": f"identity-{project_id}",
        "authorizedCheckpointId": "c",
        "_driverCapability": context_governor.APP_OWNED_BOOTSTRAP_DRIVER_CAPABILITY,
    }
    receipt["verifyReceiptSha256"] = context_governor.project_bootstrap_receipt_sha256(receipt)
    packet["projectBootstrapReceipt"] = receipt
    return packet


def global_block_receipt(
    workspace: Path,
    source: Path,
    sequence: int,
    previous: str | None,
    *,
    observed_at: str,
    blocker: str = "external-release-gate",
    authority_id: str = "neutral-qa",
    issuer: str = "neutral_qa_lane",
    audit_series_id: str = "external-release-gate-audit-series",
    source_root: Path | None = None,
) -> dict[str, object]:
    source_root = (source_root or source.parent).resolve()
    source_record = {
        "receiptId": f"audit-global-{sequence}",
        "authorityId": authority_id,
        "issuer": issuer,
        "auditSeriesId": audit_series_id,
        "sourceRoot": str(source_root),
        "observedAt": observed_at,
        "scope": "program_goal",
        "blockerCode": blocker,
        "sequence": sequence,
        "previousReceiptSha256": previous,
        "safeReadyLaneCount": 0,
        "rerouteAvailable": False,
        "externalStateChangeRequired": True,
    }
    source.write_text(json.dumps(source_record, sort_keys=True) + "\n", encoding="utf-8")
    receipt: dict[str, object] = {
        "receiptId": f"audit-global-{sequence}",
        "authorityId": authority_id,
        "issuer": issuer,
        "sourceRoot": str(source_root),
        "sourceRef": {
            "path": str(source.relative_to(workspace)),
            "hash": hashlib.sha256(source.read_bytes()).hexdigest(),
            "auditSeriesId": audit_series_id,
        },
        "observedAt": observed_at,
        "workspace": str(workspace),
        "scope": "program_goal",
        "blockerCode": blocker,
        "sequence": sequence,
        "previousReceiptSha256": previous,
        "safeReadyLaneCount": 0,
        "rerouteAvailable": False,
        "externalStateChangeRequired": True,
    }
    receipt["receiptSha256"] = context_governor.global_block_receipt_digest(receipt)
    return receipt


class ContextGovernorTest(unittest.TestCase):
    def test_project_id_null_two_roots_lazy_bootstrap_is_project_scoped(self) -> None:
        roots = [
            {"projectKey": "alpha", "workspace": "/projects/Alpha"},
            {"projectKey": "beta", "workspace": "/projects/Beta"},
        ]
        start = context_governor.evaluate(
            {
                "taskId": "cross-project-audit",
                "projectId": None,
                "artifactRoot": "/neutral/audit-artifacts",
                "projectWorkspaces": roots,
                "inputTokens": 100,
                "lane": "audit",
            },
            {},
            limits(),
        )
        self.assertEqual(start["reason"], "project_workspace_bootstrap_required")
        self.assertEqual(start["projectBootstrap"]["activeProjectKey"], "alpha")
        self.assertEqual(start["projectBootstrap"]["workspace"], "/projects/Alpha")
        self.assertFalse(start["projectBootstrap"]["artifactRootIsIdentity"])

        alpha = context_governor.evaluate(
            {
                "taskId": "cross-project-audit",
                "projectId": None,
                "artifactRoot": "/neutral/audit-artifacts",
                "projectWorkspaces": roots,
                "activeProjectKey": "alpha",
                "inputTokens": 100,
                "lane": "audit",
                "takeoverPacket": scoped_takeover_packet("/projects/Alpha", "project-alpha"),
            },
            start["state"],
            limits(),
        )
        self.assertEqual(alpha["decision"], "allow")
        self.assertEqual(alpha["nextAction"], "inject_takeover_packet_once_then_lazy_bootstrap_next_project")
        self.assertEqual(alpha["projectBootstrap"]["remainingProjectKeys"], ["beta"])

        beta = context_governor.evaluate(
            {
                "taskId": "cross-project-audit",
                "projectId": None,
                "artifactRoot": "/neutral/audit-artifacts",
                "projectWorkspaces": roots,
                "activeProjectKey": "beta",
                "inputTokens": 100,
                "lane": "audit",
                "takeoverPacket": scoped_takeover_packet("/projects/Beta", "project-beta"),
            },
            alpha["state"],
            limits(),
        )
        self.assertEqual(beta["decision"], "allow")
        ledgers = beta["state"]["projectInjectionLedger"]["cross-project-audit"]
        self.assertEqual(ledgers["alpha"]["injectedGenerationIds"], ["shared-gen"])
        self.assertEqual(ledgers["beta"]["injectedGenerationIds"], ["shared-gen"])
        self.assertNotEqual(ledgers["alpha"]["projectId"], ledgers["beta"]["projectId"])

        duplicate_beta = context_governor.evaluate(
            {
                "taskId": "cross-project-audit",
                "projectWorkspaces": roots,
                "activeProjectKey": "beta",
                "inputTokens": 100,
                "lane": "audit",
                "takeoverPacket": scoped_takeover_packet("/projects/Beta", "project-beta"),
            },
            beta["state"],
            limits(),
        )
        self.assertEqual(duplicate_beta["reason"], "duplicate_context_generation")

    def test_stale_project_does_not_downgrade_other_project(self) -> None:
        roots = [
            {"projectKey": "alpha", "workspace": "/projects/Alpha"},
            {"projectKey": "beta", "workspace": "/projects/Beta"},
        ]
        state: dict[str, object] = {}
        for key, root, project_id in (
            ("alpha", "/projects/Alpha", "project-alpha"),
            ("beta", "/projects/Beta", "project-beta"),
        ):
            result = context_governor.evaluate(
                {
                    "taskId": "audit",
                    "projectWorkspaces": roots,
                    "activeProjectKey": key,
                    "inputTokens": 100,
                    "lane": "audit",
                    "takeoverPacket": scoped_takeover_packet(root, project_id, f"gen-{key}"),
                },
                state,
                limits(),
            )
            state = result["state"]

        stale = context_governor.evaluate(
            {
                "taskId": "audit",
                "projectWorkspaces": roots,
                "activeProjectKey": "alpha",
                "inputTokens": 100,
                "memory": {
                    "memoryMode": "fallback_stale",
                    "current": False,
                    "recoveryReady": False,
                    "authorityVerification": "unavailable",
                },
            },
            state,
            limits(),
        )
        self.assertEqual(stale["decision"], "block")
        self.assertFalse(stale["programGoalBlocked"])
        self.assertTrue(stale["projectBootstrap"]["otherProjectsMayContinue"])
        ledgers = stale["state"]["projectInjectionLedger"]["audit"]
        self.assertEqual(ledgers["alpha"]["bootstrapStatus"], "stale")
        self.assertEqual(ledgers["beta"]["bootstrapStatus"], "ready")

    def test_lazy_bootstrap_advances_past_stale_project_to_next_pending_root(self) -> None:
        roots = [
            {"projectKey": "alpha", "workspace": "/projects/Alpha"},
            {"projectKey": "beta", "workspace": "/projects/Beta"},
        ]
        stale = context_governor.evaluate(
            {
                "taskId": "audit",
                "projectWorkspaces": roots,
                "activeProjectKey": "alpha",
                "inputTokens": 100,
                "memory": {"memoryMode": "fallback_stale", "current": False, "recoveryReady": False},
            },
            {},
            limits(),
        )
        next_project = context_governor.evaluate(
            {"taskId": "audit", "projectWorkspaces": roots, "inputTokens": 100},
            stale["state"],
            limits(),
        )
        self.assertEqual(next_project["reason"], "project_workspace_bootstrap_required")
        self.assertEqual(next_project["projectBootstrap"]["activeProjectKey"], "beta")

    def test_cross_project_packet_and_source_refs_fail_closed_before_ledger_write(self) -> None:
        roots = [
            {"projectKey": "alpha", "workspace": "/projects/Alpha"},
            {"projectKey": "beta", "workspace": "/projects/Beta"},
        ]
        packet = scoped_takeover_packet("/projects/Alpha", "project-alpha")
        result = context_governor.evaluate(
            {
                "taskId": "audit",
                "projectWorkspaces": roots,
                "activeProjectKey": "beta",
                "inputTokens": 100,
                "lane": "audit",
                "takeoverPacket": packet,
            },
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "source_refs_out_of_scope")
        ledger = result["state"]["projectInjectionLedger"]["audit"]["beta"]
        self.assertEqual(ledger["injectedGenerationIds"], [])
        self.assertEqual(ledger["authority"], {})

    def test_pending_project_cannot_dispatch_with_unscoped_healthy_memory(self) -> None:
        roots = [
            {"projectKey": "alpha", "workspace": "/projects/Alpha"},
            {"projectKey": "beta", "workspace": "/projects/Beta"},
        ]
        result = context_governor.evaluate(
            {
                "taskId": "audit",
                "projectWorkspaces": roots,
                "activeProjectKey": "beta",
                "dispatchRequested": True,
                "inputTokens": 100,
                "memory": {
                    "memoryMode": "app_owned_memory_core",
                    "authorityVerification": "app_owned_verified",
                    "current": True,
                    "recoveryReady": True,
                },
            },
            {},
            limits(),
        )
        self.assertEqual(result["reason"], "project_workspace_bootstrap_required")
        self.assertFalse(result["allowProviderCalls"])

    def test_relative_parent_source_ref_cannot_escape_active_project(self) -> None:
        roots = [
            {"projectKey": "alpha", "workspace": "/projects/Alpha"},
            {"projectKey": "beta", "workspace": "/projects/Beta"},
        ]
        packet = scoped_takeover_packet("/projects/Alpha", "project-alpha")
        packet["sourceRefs"] = [{"path": "../Beta/docs/goal.md", "projectId": "project-alpha"}]
        result = context_governor.evaluate(
            {
                "taskId": "audit",
                "projectWorkspaces": roots,
                "activeProjectKey": "alpha",
                "inputTokens": 100,
                "takeoverPacket": packet,
            },
            {},
            limits(),
        )
        self.assertEqual(result["reason"], "source_refs_out_of_scope")
        self.assertEqual(result["state"]["projectInjectionLedger"]["audit"]["alpha"]["injectedGenerationIds"], [])

    def test_symlink_source_ref_cannot_escape_active_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            alpha = base / "Alpha"
            beta = base / "Beta"
            alpha.mkdir()
            beta.mkdir()
            (alpha / "linked-beta").symlink_to(beta, target_is_directory=True)
            roots = [
                {"projectKey": "alpha", "workspace": str(alpha)},
                {"projectKey": "beta", "workspace": str(beta)},
            ]
            packet = scoped_takeover_packet(str(alpha), "project-alpha")
            packet["sourceRefs"] = [{"path": "linked-beta/goal.md", "projectId": "project-alpha"}]
            result = context_governor.evaluate(
                {
                    "taskId": "audit",
                    "projectWorkspaces": roots,
                    "activeProjectKey": "alpha",
                    "inputTokens": 100,
                    "takeoverPacket": packet,
                },
                {},
                limits(),
            )
            self.assertEqual(result["reason"], "source_refs_out_of_scope")

    def test_project_ready_requires_complete_matching_verify_receipt(self) -> None:
        roots = [{"projectKey": "alpha", "workspace": "/projects/Alpha"}]
        for mutation, expected in (
            ("missing", "missing_project_bootstrap_receipt"),
            ("checkpoint", "project_bootstrap_receipt_checkpoint_mismatch"),
            ("identity", "project_bootstrap_receipt_identity_mismatch"),
        ):
            with self.subTest(mutation=mutation):
                packet = scoped_takeover_packet("/projects/Alpha", "project-alpha")
                if mutation == "missing":
                    packet.pop("projectBootstrapReceipt")
                elif mutation == "checkpoint":
                    packet["projectBootstrapReceipt"]["authorizedCheckpointId"] = "wrong"
                    packet["projectBootstrapReceipt"]["verifyReceiptSha256"] = (
                        context_governor.project_bootstrap_receipt_sha256(packet["projectBootstrapReceipt"])
                    )
                else:
                    packet["projectBootstrapReceipt"]["projectIdentitySha256"] = "wrong"
                    packet["projectBootstrapReceipt"]["verifyReceiptSha256"] = (
                        context_governor.project_bootstrap_receipt_sha256(packet["projectBootstrapReceipt"])
                    )
                result = context_governor.evaluate(
                    {
                        "taskId": "audit",
                        "projectWorkspaces": roots,
                        "activeProjectKey": "alpha",
                        "inputTokens": 100,
                        "takeoverPacket": packet,
                    },
                    {},
                    limits(),
                )
                self.assertEqual(result["reason"], expected)
                self.assertEqual(result["state"]["projectInjectionLedger"]["audit"]["alpha"]["bootstrapStatus"], "pending")

        packet = scoped_takeover_packet("/projects/Alpha", "project-alpha")
        packet["projectBootstrapReceipt"]["verifyReceiptSha256"] = "0" * 64
        result = context_governor.evaluate(
            {
                "taskId": "audit",
                "projectWorkspaces": roots,
                "activeProjectKey": "alpha",
                "inputTokens": 100,
                "takeoverPacket": packet,
            },
            {},
            limits(),
        )
        self.assertEqual(result["reason"], "project_bootstrap_receipt_hash_invalid")

    def test_cross_project_writeback_evidence_is_project_scoped(self) -> None:
        roots = [
            {"projectKey": "alpha", "workspace": "/projects/Alpha", "projectId": "project-alpha"},
            {"projectKey": "beta", "workspace": "/projects/Beta", "projectId": "project-beta"},
        ]
        result = context_governor.evaluate(
            {
                "taskId": "audit",
                "projectWorkspaces": roots,
                "activeProjectKey": "alpha",
                "inputTokens": 100,
                "writebackEvidence": {
                    "workspace": "/projects/Beta",
                    "projectId": "project-beta",
                    "receipt": {
                        "receiptId": "beta-writeback-001",
                        "workspace": "/projects/Beta",
                        "projectId": "project-beta",
                    },
                    "sourceRefs": [
                        {"path": "/projects/Beta/docs/acceptance.md", "projectId": "project-beta"}
                    ],
                },
            },
            {},
            limits(),
        )
        self.assertEqual(result["reason"], "cross_project_evidence_scope_mismatch")

    def test_cross_project_writeback_requires_nonempty_refs_and_bound_receipt(self) -> None:
        roots = [{"projectKey": "alpha", "workspace": "/projects/Alpha", "projectId": "project-alpha"}]
        base_writeback = {
            "workspace": "/projects/Alpha",
            "projectId": "project-alpha",
            "receipt": {
                "receiptId": "alpha-writeback-001",
                "workspace": "/projects/Alpha",
                "projectId": "project-alpha",
            },
            "sourceRefs": [
                {"path": "/projects/Alpha/docs/acceptance.md", "projectId": "project-alpha"}
            ],
        }
        cases = []
        for invalid_refs in (None, [], {}, "docs/acceptance.md"):
            writeback = dict(base_writeback)
            writeback["sourceRefs"] = invalid_refs
            cases.append(writeback)
        wrong_receipt = dict(base_writeback)
        wrong_receipt["receipt"] = {
            "receiptId": "beta-writeback-001",
            "workspace": "/projects/Beta",
            "projectId": "project-beta",
        }
        cases.append(wrong_receipt)
        for writeback in cases:
            with self.subTest(writeback=writeback):
                result = context_governor.evaluate(
                    {
                        "taskId": "audit",
                        "projectWorkspaces": roots,
                        "activeProjectKey": "alpha",
                        "inputTokens": 100,
                        "writebackEvidence": writeback,
                    },
                    {},
                    limits(),
                )
                self.assertEqual(result["reason"], "cross_project_evidence_scope_mismatch")

    def test_project_workspace_order_and_roots_are_immutable_per_task(self) -> None:
        roots = [
            {"projectKey": "alpha", "workspace": "/projects/Alpha"},
            {"projectKey": "beta", "workspace": "/projects/Beta"},
        ]
        first = context_governor.evaluate(
            {"taskId": "audit", "projectWorkspaces": roots, "inputTokens": 100}, {}, limits()
        )
        changed = context_governor.evaluate(
            {"taskId": "audit", "projectWorkspaces": list(reversed(roots)), "inputTokens": 100},
            first["state"],
            limits(),
        )
        self.assertEqual(changed["reason"], "project_workspaces_changed")

    def test_cross_project_refresh_evidence_cannot_use_another_root(self) -> None:
        roots = [
            {"projectKey": "alpha", "workspace": "/projects/Alpha"},
            {"projectKey": "beta", "workspace": "/projects/Beta"},
        ]
        seeded = context_governor.evaluate(
            {
                "taskId": "audit",
                "projectWorkspaces": roots,
                "activeProjectKey": "alpha",
                "inputTokens": 100,
                "lane": "audit",
                "takeoverPacket": scoped_takeover_packet("/projects/Alpha", "project-alpha", "alpha-old"),
            },
            {},
            limits(),
        )
        result = context_governor.evaluate(
            {
                "taskId": "audit",
                "projectWorkspaces": roots,
                "activeProjectKey": "alpha",
                "inputTokens": 100,
                "lane": "audit",
                "acceptedEvidenceReceipt": {
                    "receiptId": "qa-accept-alpha",
                    "decision": "accept",
                    "acceptedEvidenceReceiptDigest": "a" * 64,
                },
                "acceptedEvidence": {
                    "sourceRefs": [
                        {
                            "path": "/projects/Beta/docs/acceptance.md",
                            "hash": "wrong-root",
                            "projectId": "project-alpha",
                        }
                    ]
                },
                "exactScan": {
                    "changed": True,
                    "previousCheckpointId": "c",
                    "currentScanSha256": "alpha-new-scan",
                    "changedPaths": ["docs/acceptance.md"],
                },
            },
            seeded["state"],
            limits(),
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "cross_project_evidence_scope_mismatch")
        before = seeded["state"]["projectInjectionLedger"]["audit"]["alpha"]
        after = result["state"]["projectInjectionLedger"]["audit"]["alpha"]
        self.assertEqual(after, before)

    def test_cross_project_source_ref_requires_explicit_project_id(self) -> None:
        roots = [{"projectKey": "alpha", "workspace": "/projects/Alpha"}]
        packet = scoped_takeover_packet("/projects/Alpha", "project-alpha")
        packet["sourceRefs"] = [{"path": "git://repo/head/docs/goal.md"}]
        result = context_governor.evaluate(
            {
                "taskId": "audit",
                "projectWorkspaces": roots,
                "activeProjectKey": "alpha",
                "inputTokens": 100,
                "takeoverPacket": packet,
            },
            {},
            limits(),
        )
        self.assertEqual(result["reason"], "source_refs_out_of_scope")

    def test_pressure_freeze_emits_once_then_stops_without_repeat(self) -> None:
        first = context_governor.evaluate({"taskId": "old-task", "inputTokens": 145_000}, {}, limits())
        self.assertEqual(first["decision"], "freeze")
        self.assertTrue(first["emitFreezeReceipt"])
        self.assertFalse(first["allowToolCalls"])
        self.assertEqual(first["nextAction"], "emit_freeze_receipt_and_unbind_harvest_driver")
        self.assertEqual(first["prepareTakeover"]["preferredTokens"], 2_200)
        self.assertEqual(first["prepareTakeover"]["maxTokens"], 10_000)

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

    def test_model_request_preflight_requires_strict_complete_metrics(self) -> None:
        base = preflight_fields("ceo", "request-strict")
        for field, invalid in (
            ("currentPostCompactionContextTokens", None),
            ("estimatedContextBytes", "80000"),
            ("projectedNextRequestInputTokens", True),
            ("modelContextWindowTokens", -1),
            ("reservedOutputTokens", None),
            ("contextCompactionCount", None),
            ("contextCompactionCount", "2"),
            ("contextCompactionCount", True),
        ):
            with self.subTest(field=field):
                event = dict(base)
                event["hostTelemetryReceipt"] = dict(base["hostTelemetryReceipt"])
                event["hostTelemetryReceipt"][field] = invalid
                result = context_governor.evaluate(event, {}, limits())
                self.assertEqual(result["decision"], "block")
                self.assertFalse(result["allowProjectToolCalls"])
                self.assertFalse(result["allowProviderCalls"])
                self.assertIn("host_context_telemetry", result["reason"])

        event = preflight_fields("ceo", "request-source")
        receipt = dict(event["hostTelemetryReceipt"])
        receipt["compactionCountSource"] = "caller_estimate"
        receipt["hostTelemetryReceiptId"] = context_governor.host_telemetry_receipt_sha256(receipt)
        event["hostTelemetryReceipt"] = receipt
        result = context_governor.evaluate(event, {}, limits())
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "host_context_compaction_source_invalid")

    def test_second_host_compaction_recommends_rotation_without_freezing(self) -> None:
        first = context_governor.evaluate(
            preflight_fields("ceo", "after-first-compaction", compaction_count=1),
            {},
            limits(),
        )
        self.assertEqual(first["decision"], "allow", first)
        self.assertEqual(first["metrics"]["contextCompactionCount"], 1)

        second = context_governor.evaluate(
            preflight_fields("ceo", "after-second-compaction", compaction_count=2),
            first["state"],
            limits(),
        )
        self.assertEqual(second["decision"], "allow", second)
        self.assertNotIn("ceo", second["state"]["frozenTaskKeys"])
        self.assertTrue(second["state"]["taskRuntimeLedger"]["ceo"]["rotationRecommended"])

    def test_host_compaction_count_cannot_regress_within_task(self) -> None:
        first = context_governor.evaluate(
            preflight_fields("ceo", "compaction-one", compaction_count=1), {}, limits()
        )
        regressed = context_governor.evaluate(
            preflight_fields("ceo", "compaction-regressed", compaction_count=0),
            first["state"],
            limits(),
        )
        self.assertEqual(regressed["decision"], "block")
        self.assertEqual(regressed["reason"], "host_context_compaction_count_regressed")
        self.assertEqual(regressed["lifecycleState"], "lane_paused_recoverable")
        self.assertFalse(regressed["allowProviderCalls"])

    def test_clean_replacement_has_task_scoped_compaction_count(self) -> None:
        frozen = context_governor.evaluate(
            preflight_fields("old", "old-second-compaction", projected=110_000, compaction_count=2),
            {},
            limits(),
        )
        clean = context_governor.evaluate(
            preflight_fields("clean", "clean-first-request", compaction_count=0)
            | {
                "workspace": "/repo",
                "lane": "impl",
                "recoveryRequested": True,
                "replacementForTaskId": "old",
                "takeoverPacket": valid_takeover_packet("fresh-after-compaction"),
            },
            frozen["state"],
            limits(),
        )
        self.assertEqual(clean["decision"], "allow", clean)
        self.assertEqual(clean["metrics"]["contextCompactionCount"], 0)
        self.assertEqual(
            clean["state"]["taskRuntimeLedger"]["clean"]["lastContextCompactionCount"], 0
        )
        self.assertEqual(
            clean["state"]["taskRuntimeLedger"]["old"]["lastContextCompactionCount"], 2
        )

    def test_goal_cumulative_usage_never_substitutes_for_current_context(self) -> None:
        event = preflight_fields("ceo", "request-post-compact", projected=43_000)
        receipt = dict(event["hostTelemetryReceipt"])
        receipt.update(
            {
                "lastRequestInputTokens": 35_000,
                "currentPostCompactionContextTokens": 35_000,
                "projectedNextRequestInputTokens": 43_000,
                "cumulativeInputTokens": 106_712,
            }
        )
        receipt["hostTelemetryReceiptId"] = context_governor.host_telemetry_receipt_sha256(receipt)
        event["hostTelemetryReceipt"] = receipt
        event["goalTokensUsed"] = 106_712
        result = context_governor.evaluate(event, {}, limits())
        self.assertEqual(result["decision"], "allow", result)
        self.assertEqual(result["metrics"]["estimatedContextTokens"], 35_000)
        self.assertEqual(result["metrics"]["pressurePreflight"]["projectedContextTokens"], 43_000)

    def test_untrusted_caller_metrics_pause_recoverably_without_freeze(self) -> None:
        result = context_governor.evaluate(
            {
                "taskId": "ceo",
                "eventType": "model_request_preflight",
                "requestId": "forged",
                "inputTokens": 190_000,
                "estimatedContextTokens": 190_000,
                "projectedContextTokens": 190_000,
            },
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "host_context_telemetry_unavailable")
        self.assertEqual(result["lifecycleState"], "lane_paused_recoverable")
        self.assertNotIn("ceo", result["state"]["frozenTaskKeys"])
        self.assertEqual(result["state"]["taskRuntimeLedger"]["ceo"]["cumulativeInputTokens"], 0)

    def test_projected_context_freezes_before_configured_hard_limit(self) -> None:
        result = context_governor.evaluate(
            preflight_fields("ceo", "request-near-limit", projected=108_000), {}, limits()
        )
        self.assertEqual(result["decision"], "freeze")
        self.assertEqual(result["reason"], "projected_context_pressure_limit")
        self.assertEqual(result["metrics"]["pressurePreflight"]["effectivePreflightLimit"], 108_000)

    def test_clean_takeover_retained_context_has_30k_hard_limit(self) -> None:
        event = preflight_fields("clean", "clean-over-budget", projected=40_000)
        receipt = dict(event["hostTelemetryReceipt"])
        receipt["currentPostCompactionContextTokens"] = 31_000
        receipt["projectedNextRequestInputTokens"] = 40_000
        receipt["hostTelemetryReceiptId"] = context_governor.host_telemetry_receipt_sha256(receipt)
        event.update(
            {
                "hostTelemetryReceipt": receipt,
                "recoveryRequested": True,
                "replacementForTaskId": "old",
            }
        )
        result = context_governor.evaluate(event, {}, limits())
        self.assertEqual(result["decision"], "freeze")
        self.assertEqual(result["reason"], "clean_takeover_retained_context_limit")

    def test_preflight_request_id_is_consumed_once(self) -> None:
        event = preflight_fields("ceo", "request-once")
        first = context_governor.evaluate(event, {}, limits())
        self.assertEqual(first["decision"], "allow")
        duplicate = context_governor.evaluate(event, first["state"], limits())
        self.assertEqual(duplicate["decision"], "block")
        self.assertEqual(duplicate["reason"], "duplicate_pressure_preflight_request")

    def test_takeover_without_model_preflight_cannot_open_execution(self) -> None:
        result = context_governor.evaluate(
            {
                "taskId": "clean",
                "inputTokens": 100,
                "workspace": "/repo",
                "lane": "impl",
                "takeoverPacket": valid_takeover_packet("takeover-only"),
            },
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "allow")
        self.assertFalse(result["allowProjectToolCalls"])
        self.assertFalse(result["allowProviderCalls"])

    def test_dispatch_without_preflight_is_fail_closed(self) -> None:
        result = context_governor.evaluate(
            {"taskId": "ceo", "dispatchRequested": True, "inputTokens": 100}, {}, limits()
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "model_request_preflight_required")

    def test_native_codex_lane_dispatch_does_not_require_host_preflight(self) -> None:
        result = context_governor.evaluate(
            {
                "taskId": "ceo",
                "eventType": "codex_lane_dispatch",
                "dispatchRequested": True,
                "routingSurface": "subagent",
                "executionBackend": "codex_native",
            },
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "allow", result)
        self.assertEqual(result["reason"], "ordinary_codex_lane_dispatch_allowed")
        self.assertTrue(result["allowProjectToolCalls"])
        self.assertFalse(result["allowProviderCalls"])
        self.assertEqual(
            result["metrics"]["hostPreflightDisposition"],
            "not_required_for_native_lane_creation",
        )

    def test_native_lane_dispatch_cannot_smuggle_external_or_lifecycle_work(self) -> None:
        forbidden = (
            {"providerCallRequested": True},
            {"externalHarnessRequested": True},
            {"recoveryRequested": True},
            {"replacementForTaskId": "old-ceo"},
            {"goalTransferRequested": True},
        )
        for extra in forbidden:
            with self.subTest(extra=extra):
                result = context_governor.evaluate(
                    {
                        "taskId": "ceo",
                        "eventType": "codex_lane_dispatch",
                        "dispatchRequested": True,
                        "routingSurface": "visible_thread",
                        "executionBackend": "codex_native",
                    }
                    | extra,
                    {},
                    limits(),
                )
                self.assertEqual(result["decision"], "block")
                self.assertEqual(result["reason"], "codex_lane_dispatch_scope_invalid")
                self.assertFalse(result["allowProjectToolCalls"])
                self.assertFalse(result["allowProviderCalls"])

    def test_frozen_ceo_cannot_use_native_lane_dispatch_bypass(self) -> None:
        frozen = context_governor.evaluate(
            {"taskId": "old-ceo", "inputTokens": 145_000}, {}, limits()
        )
        result = context_governor.evaluate(
            {
                "taskId": "old-ceo",
                "eventType": "codex_lane_dispatch",
                "dispatchRequested": True,
                "routingSurface": "subagent",
                "executionBackend": "codex_native",
            },
            frozen["state"],
            limits(),
        )
        self.assertEqual(result["decision"], "freeze")
        self.assertFalse(result["allowProjectToolCalls"])
        self.assertFalse(result["allowProviderCalls"])

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

    def test_same_generation_is_allowed_once_per_distinct_task(self) -> None:
        ceo_event = {
            "taskId": "ceo-task-a",
            "inputTokens": 500,
            "workspace": "/repo",
            "lane": "impl",
            "takeoverPacket": valid_takeover_packet(),
        }
        ceo = context_governor.evaluate(ceo_event, {}, limits())
        self.assertEqual(ceo["decision"], "allow")

        worker_event = {
            "taskId": "worker-task-b",
            "inputTokens": 500,
            "workspace": "/repo",
            "lane": "impl",
            "takeoverPacket": valid_takeover_packet(),
        }
        worker = context_governor.evaluate(worker_event, ceo["state"], limits())
        self.assertEqual(worker["decision"], "allow")
        self.assertEqual(worker["nextAction"], "inject_takeover_packet_once")
        self.assertEqual(worker["state"]["taskInjectionLedger"]["ceo-task-a"]["injectedGenerationIds"], ["gen-1"])
        self.assertEqual(worker["state"]["taskInjectionLedger"]["worker-task-b"]["injectedGenerationIds"], ["gen-1"])

        duplicate = context_governor.evaluate(worker_event, worker["state"], limits())
        self.assertEqual(duplicate["decision"], "block")
        self.assertEqual(duplicate["reason"], "duplicate_context_generation")

    def test_legacy_top_level_generation_migrates_only_to_matching_owner(self) -> None:
        legacy = {
            "schema": "ceo_context_governor_v1",
            "taskId": "legacy-ceo",
            "injectedGenerationIds": ["gen-1"],
            "lastGenerationBasis": {
                "head": "a",
                "scanHash": "b",
                "projectIdentitySha256": "project-123",
                "verifiedMemoryStateHash": "c",
            },
            "taskInjectionLedger": {},
        }
        same_owner = context_governor.evaluate(
            {"taskId": "legacy-ceo", "inputTokens": 500, "takeoverPacket": valid_takeover_packet()},
            legacy,
            limits(),
        )
        self.assertEqual(same_owner["reason"], "duplicate_context_generation")

        different_owner = context_governor.evaluate(
            {"taskId": "fresh-worker", "inputTokens": 500, "takeoverPacket": valid_takeover_packet()},
            legacy,
            limits(),
        )
        self.assertEqual(different_owner["decision"], "allow")
        self.assertEqual(different_owner["nextAction"], "inject_takeover_packet_once")

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
                    "contextGenerationId": "beta-fallback-1",
                    "tokenEstimate": 557,
                    "memoryMode": "fallback_stale",
                    "authorityVerification": "unavailable",
                    "current": False,
                    "recoveryReady": False,
                    "returnedCount": 0,
                    "takeover": {"shouldInject": False},
                    "head": "ac63d62c",
                    "scanHash": "scan-beta",
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

    def test_scan_unchanged_after_failed_verify_pauses_recoverably(self) -> None:
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
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "authority_defect")
        self.assertEqual(result["lifecycleState"], "lane_paused_recoverable")
        self.assertFalse(result["programGoalBlocked"])
        self.assertTrue(result["unrelatedLanesMayContinue"])
        self.assertFalse(result["userAuthorizationRequired"])
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
        self.assertEqual(changed["decision"], "block")
        self.assertEqual(changed["reason"], "unaccepted_project_change")
        self.assertEqual(changed["lifecycleState"], "lane_paused_pending_acceptance")
        self.assertFalse(changed["programGoalBlocked"])
        self.assertIn("gen-1", changed["state"]["invalidatedGenerationIds"])

    def test_heartbeat_and_tool_result_do_not_retrieve_or_inject(self) -> None:
        for event_type in ("heartbeat", "tool_result"):
            with self.subTest(event_type=event_type):
                result = context_governor.evaluate({"inputTokens": 20, "eventType": event_type}, {}, limits())
                self.assertEqual(result["decision"], "allow")
                self.assertEqual(result["reason"], "non_memory_event_no_retrieval")
                self.assertEqual(result["metrics"]["memoryRuntimeAction"], "skip")
                self.assertFalse(result["allowProjectToolCalls"])
                self.assertFalse(result["allowProviderCalls"])

    def test_status_poll_cannot_smuggle_dispatch_or_scan_change(self) -> None:
        result = context_governor.evaluate(
            {
                "taskId": "poll",
                "inputTokens": 10,
                "eventType": "status_poll",
                "providerCallRequested": True,
                "exactScan": {"changed": True},
            },
            {},
            limits(),
        )
        self.assertEqual(result["reason"], "non_memory_event_no_retrieval")
        self.assertFalse(result["allowToolCalls"])
        self.assertFalse(result["allowProjectToolCalls"])
        self.assertFalse(result["allowProviderCalls"])

    def test_direct_cross_project_packet_without_driver_capability_fails_closed(self) -> None:
        packet = scoped_takeover_packet("/projects/Alpha", "project-alpha")
        result = context_governor.evaluate(
            {
                "taskId": "untrusted",
                "projectWorkspaces": [{"projectKey": "alpha", "workspace": "/projects/Alpha"}],
                "activeProjectKey": "alpha",
                "inputTokens": 100,
                "takeoverPacket": json.loads(json.dumps(packet, default=str)),
            },
            {},
            limits(),
        )
        self.assertEqual(result["reason"], "project_bootstrap_driver_authority_missing")
        self.assertFalse(result["allowProviderCalls"])

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
                "acceptedEvidenceReceipt": {
                    "receiptId": "qa-1",
                    "decision": "accept",
                    "acceptedEvidenceReceiptDigest": "a" * 64,
                },
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
        self.assertFalse(result["allowToolCalls"])
        self.assertFalse(result["allowProjectToolCalls"])
        self.assertFalse(result["allowProviderCalls"])
        self.assertTrue(result["allowRecoveryControlTools"])
        self.assertEqual(result["recoveryControlToolAllowlist"], ["refresh_binding_driver"])
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

    def test_unaccepted_scan_change_pauses_only_related_lane(self) -> None:
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
                self.assertEqual(result["decision"], "block")
                self.assertEqual(result["reason"], "unaccepted_project_change")
                self.assertEqual(result["lifecycleState"], "lane_paused_pending_acceptance")
                self.assertFalse(result["programGoalBlocked"])
                self.assertTrue(result["unrelatedLanesMayContinue"])

    def test_frozen_old_task_recovers_through_fresh_verified_replacement(self) -> None:
        frozen = context_governor.evaluate(
            {"taskId": "beta-old", "inputTokens": 145_000}, {}, limits()
        )
        self.assertEqual(frozen["lifecycleState"], "task_context_frozen_replace_required")

        packet = valid_takeover_packet("context-beta-fresh")
        replacement = context_governor.evaluate(
            preflight_fields("beta-clean-replacement", "replacement-request-1") | {
                "workspace": "/repo",
                "lane": "impl",
                "recoveryRequested": True,
                "replacementForTaskId": "beta-old",
                "takeoverPacket": packet,
            },
            frozen["state"],
            limits(),
        )
        self.assertEqual(replacement["decision"], "allow")
        self.assertEqual(replacement["lifecycleState"], "active")
        self.assertTrue(replacement["resumeProgramGoal"])
        self.assertTrue(replacement["clearHistoricalGoalBlocked"])
        self.assertEqual(replacement["nextAction"], "inject_takeover_packet_once_and_resume_program_goal")

        old_again = context_governor.evaluate(
            {"taskId": "beta-old", "inputTokens": 1}, replacement["state"], limits()
        )
        self.assertEqual(old_again["decision"], "freeze")
        self.assertFalse(old_again["allowOldThreadExecution"])

    def test_thread_id_only_clean_replacement_does_not_inherit_old_task_identity(self) -> None:
        frozen = context_governor.evaluate(
            {"taskId": "old-beta", "inputTokens": 145_000}, {}, limits()
        )
        replacement = context_governor.evaluate(
            (preflight_fields("new-beta-thread", "replacement-request-2") | {
                "taskId": None,
                "threadId": "new-beta-thread",
                "workspace": "/repo",
                "lane": "impl",
                "recoveryRequested": True,
                "replacementForTaskId": "old-beta",
                "takeoverPacket": valid_takeover_packet("fresh-thread-generation"),
            }),
            frozen["state"],
            limits(),
        )
        self.assertEqual(replacement["decision"], "allow")
        self.assertTrue(replacement["resumeProgramGoal"])
        self.assertIn("new-beta-thread", replacement["state"]["taskInjectionLedger"])
        self.assertIn("old-beta", replacement["state"]["frozenTaskKeys"])

    def test_old_task_cumulative_pressure_does_not_poison_clean_task(self) -> None:
        frozen = context_governor.evaluate(
            preflight_fields("old", "old-pressure", projected=110_000), {}, limits()
        )
        clean = context_governor.evaluate(
            preflight_fields("clean", "clean-replacement")
            | {
                "workspace": "/repo",
                "lane": "impl",
                "recoveryRequested": True,
                "replacementForTaskId": "old",
                "takeoverPacket": valid_takeover_packet("context-clean"),
            },
            frozen["state"],
            limits(),
        )
        self.assertEqual(clean["decision"], "allow")
        self.assertEqual(clean["metrics"]["cumulativeInputTokens"], 500)

    def test_ordinary_worker_packet_does_not_clear_unrelated_frozen_task(self) -> None:
        frozen = context_governor.evaluate({"taskId": "old", "inputTokens": 145_000}, {}, limits())
        worker = context_governor.evaluate(
            {
                "taskId": "worker",
                "inputTokens": 100,
                "workspace": "/repo",
                "lane": "impl",
                "takeoverPacket": valid_takeover_packet("context-worker"),
            },
            frozen["state"],
            limits(),
        )
        self.assertEqual(worker["decision"], "allow")
        self.assertFalse(worker["resumeProgramGoal"])
        self.assertFalse(worker["clearHistoricalGoalBlocked"])

    def test_replacement_requires_fresh_generation_and_exact_frozen_target(self) -> None:
        seeded = context_governor.evaluate(
            {
                "taskId": "old",
                "inputTokens": 100,
                "workspace": "/repo",
                "lane": "impl",
                "takeoverPacket": valid_takeover_packet("context-old"),
            },
            {},
            limits(),
        )
        frozen = context_governor.evaluate(
            {"taskId": "old", "inputTokens": 145_000}, seeded["state"], limits()
        )
        reused = context_governor.evaluate(
            {
                "taskId": "clean",
                "inputTokens": 100,
                "workspace": "/repo",
                "lane": "impl",
                "recoveryRequested": True,
                "replacementForTaskId": "old",
                "takeoverPacket": valid_takeover_packet("context-old"),
            },
            frozen["state"],
            limits(),
        )
        self.assertEqual(reused["reason"], "replacement_generation_not_fresh")

        wrong_target = context_governor.evaluate(
            {
                "taskId": "clean",
                "inputTokens": 100,
                "workspace": "/repo",
                "lane": "impl",
                "recoveryRequested": True,
                "replacementForTaskId": "not-frozen",
                "takeoverPacket": valid_takeover_packet("context-fresh"),
            },
            frozen["state"],
            limits(),
        )
        self.assertEqual(wrong_target["reason"], "replacement_target_not_frozen")

    def test_legacy_frozen_task_generation_cannot_be_reused_by_replacement(self) -> None:
        legacy_state = {
            "schema": "ceo_context_governor_v1",
            "taskId": "legacy-frozen",
            "injectedGenerationIds": ["legacy-generation"],
            "lastGenerationBasis": {
                "head": "a",
                "scanHash": "b",
                "projectIdentitySha256": "project-123",
                "verifiedMemoryStateHash": "c",
            },
            "taskInjectionLedger": {},
            "freeze": {
                "triggered": True,
                "receiptEmitted": True,
                "reason": "input_token_limit",
                "ownerTaskKey": "legacy-frozen",
            },
        }
        replacement = context_governor.evaluate(
            {
                "taskId": "fresh-replacement",
                "inputTokens": 500,
                "workspace": "/repo",
                "lane": "impl",
                "recoveryRequested": True,
                "replacementForTaskId": "legacy-frozen",
                "takeoverPacket": valid_takeover_packet("legacy-generation"),
            },
            legacy_state,
            limits(),
        )
        self.assertEqual(replacement["decision"], "block")
        self.assertEqual(replacement["reason"], "replacement_generation_not_fresh")

    def test_routine_approval_is_not_escalated_to_user(self) -> None:
        result = context_governor.evaluate(
            preflight_fields("alpha", "routine-approval") | {"approvalRequested": True}, {}, limits()
        )
        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["lifecycleState"], "active")
        self.assertEqual(result["metrics"]["approvalDisposition"], "routine_in_scope_no_user_authorization")

    def test_real_privilege_or_spending_boundary_requires_user_authorization(self) -> None:
        credential = context_governor.evaluate(
            {"taskId": "alpha", "inputTokens": 100, "credentialAccessRequested": True}, {}, limits()
        )
        self.assertEqual(credential["lifecycleState"], "lane_paused_user_authorization")
        self.assertTrue(credential["userAuthorizationRequired"])
        self.assertFalse(credential["programGoalBlocked"])

        paid = context_governor.evaluate(
            {"taskId": "alpha", "inputTokens": 100, "paidProviderRequested": True}, {}, limits()
        )
        self.assertEqual(paid["reason"], "spending_authorization_required")
        self.assertTrue(paid["userAuthorizationRequired"])

    def test_program_block_requires_proven_global_impasse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve()
            audit_root = workspace / "audit-receipts"
            audit_root.mkdir()
            now = datetime.now(timezone.utc)
            timestamps = [
                (now - timedelta(seconds=3 - index)).isoformat().replace("+00:00", "Z")
                for index in range(3)
            ]
            state: dict[str, object] = {}
            previous = None
            results = []
            for sequence, observed_at in enumerate(timestamps, 1):
                source = audit_root / f"audit-source-{sequence}.json"
                receipt = global_block_receipt(
                    workspace, source, sequence, previous, observed_at=observed_at
                )
                result = context_governor.evaluate_program_block_audit(
                    {
                        "taskId": "alpha",
                        "workspace": str(workspace),
                        "inputTokens": 100,
                        "programBlockAssessment": {
                            "blockerCode": "external-release-gate",
                            "auditReceipt": receipt,
                            "safeReadyLaneCount": 0,
                            "rerouteAvailable": False,
                            "externalStateChangeRequired": True,
                        },
                    },
                    state
                    | {
                        "programBlockAuthorityRegistry": {
                            "neutral-qa": {
                                "issuer": "neutral_qa_lane",
                                "auditSeriesId": "external-release-gate-audit-series",
                                "sourceRoot": str(audit_root),
                            }
                        }
                    },
                    limits(),
                )
                results.append(result)
                state = result["state"]
                previous = str(receipt["receiptSha256"])
            self.assertFalse(results[0]["programGoalBlocked"])
            self.assertFalse(results[1]["programGoalBlocked"])
            self.assertEqual(results[2]["lifecycleState"], "program_blocked_global")
            self.assertTrue(results[2]["programGoalBlocked"])
            self.assertFalse(results[2]["unrelatedLanesMayContinue"])

            state_path = workspace / "governor-state.json"
            context_governor.atomic_state.atomic_write_json(state_path, state)
            stale_sha = context_governor.atomic_state.state_sha256(state)
            restarted_state = context_governor.atomic_state.read_json(state_path)

            ordinary = context_governor.evaluate(
                {
                    "taskId": "alpha-worker",
                    "workspace": str(workspace),
                    "inputTokens": 1,
                    "clearProgramGlobalBlock": True,
                },
                restarted_state,
                limits(),
            )
            self.assertEqual(ordinary["lifecycleState"], "program_blocked_global")
            self.assertTrue(ordinary["programGoalBlocked"])
            self.assertFalse(ordinary["allowProjectToolCalls"])
            self.assertFalse(ordinary["allowProviderCalls"])
            state = ordinary["state"]
            context_governor.atomic_state.atomic_write_json(
                state_path, state, expected_sha256=stale_sha
            )
            with self.assertRaises(context_governor.atomic_state.StateConflictError):
                context_governor.atomic_state.atomic_write_json(
                    state_path,
                    {**state, "programGlobalBlock": {"active": False}},
                    expected_sha256=stale_sha,
                )
            self.assertTrue(
                context_governor.atomic_state.read_json(state_path)["programGlobalBlock"]["active"]
            )

            (audit_root / "audit-source-1.json").write_text("{}\n", encoding="utf-8")
            fourth_source = audit_root / "audit-source-4.json"
            fourth = global_block_receipt(
                workspace,
                fourth_source,
                4,
                previous,
                observed_at=(datetime.now(timezone.utc) - timedelta(milliseconds=1)).isoformat(),
            )
            tampered_history = context_governor.evaluate_program_block_audit(
                {
                    "taskId": "alpha",
                    "workspace": str(workspace),
                    "inputTokens": 100,
                    "programBlockAssessment": {
                        "blockerCode": "external-release-gate",
                        "auditReceipt": fourth,
                        "safeReadyLaneCount": 0,
                        "rerouteAvailable": False,
                        "externalStateChangeRequired": True,
                    },
                },
                state,
                limits(),
            )
            ledger = next(iter(tampered_history["state"]["programBlockAuditLedger"].values()))
            self.assertEqual(len(ledger["receipts"]), 3)

    def test_global_block_assessment_requires_exact_typed_zero_safe_lanes(self) -> None:
        invalid_values = (None, False, "0", 0.0, -1, 1)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve()
            audit_root = workspace / "audit"
            audit_root.mkdir()
            registry = {
                "neutral-qa": {
                    "issuer": "neutral_qa_lane",
                    "auditSeriesId": "external-release-gate-audit-series",
                    "sourceRoot": str(audit_root),
                }
            }
            for index, invalid in enumerate(invalid_values):
                with self.subTest(value=invalid):
                    receipt = global_block_receipt(
                        workspace,
                        audit_root / f"invalid-{index}.json",
                        1,
                        None,
                        observed_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
                    )
                    assessment = {
                        "blockerCode": "external-release-gate",
                        "auditReceipt": receipt,
                        "safeReadyLaneCount": invalid,
                        "rerouteAvailable": False,
                        "externalStateChangeRequired": True,
                    }
                    if invalid is None:
                        assessment.pop("safeReadyLaneCount")
                    result = context_governor.evaluate_program_block_audit(
                        {
                            "taskId": "audit",
                            "workspace": str(workspace),
                            "inputTokens": 1,
                            "programBlockAssessment": assessment,
                        },
                        {"programBlockAuthorityRegistry": registry},
                        limits(),
                    )
                    self.assertFalse(result["programGoalBlocked"])
                    self.assertTrue(
                        all(not item.get("receipts") for item in result["state"]["programBlockAuditLedger"].values())
                    )

    def test_global_block_chain_requires_one_exact_registered_authority_tuple(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve()
            root_a = workspace / "audit-a"
            root_b = workspace / "audit-b"
            root_a.mkdir()
            root_b.mkdir()
            registry = {
                "authority-a": {
                    "issuer": "issuer-a",
                    "auditSeriesId": "series-a",
                    "sourceRoot": str(root_a),
                },
                "authority-b": {
                    "issuer": "issuer-b",
                    "auditSeriesId": "series-b",
                    "sourceRoot": str(root_b),
                },
            }
            first = global_block_receipt(
                workspace,
                root_a / "one.json",
                1,
                None,
                observed_at=(datetime.now(timezone.utc) - timedelta(seconds=3)).isoformat().replace("+00:00", "Z"),
                authority_id="authority-a",
                issuer="issuer-a",
                audit_series_id="series-a",
                source_root=root_a,
            )
            state = context_governor.evaluate_program_block_audit(
                {
                    "taskId": "audit",
                    "workspace": str(workspace),
                    "inputTokens": 1,
                    "programBlockAssessment": {
                        "blockerCode": "external-release-gate",
                        "auditReceipt": first,
                        "safeReadyLaneCount": 0,
                        "rerouteAvailable": False,
                        "externalStateChangeRequired": True,
                    },
                },
                {"programBlockAuthorityRegistry": registry},
                limits(),
            )["state"]
            mixed = global_block_receipt(
                workspace,
                root_b / "two.json",
                2,
                str(first["receiptSha256"]),
                observed_at=(datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat().replace("+00:00", "Z"),
                authority_id="authority-b",
                issuer="issuer-b",
                audit_series_id="series-b",
                source_root=root_b,
            )
            result = context_governor.evaluate_program_block_audit(
                {
                    "taskId": "audit",
                    "workspace": str(workspace),
                    "inputTokens": 1,
                    "programBlockAssessment": {
                        "blockerCode": "external-release-gate",
                        "auditReceipt": mixed,
                        "safeReadyLaneCount": 0,
                        "rerouteAvailable": False,
                        "externalStateChangeRequired": True,
                    },
                },
                state,
                limits(),
            )
            ledger = next(iter(result["state"]["programBlockAuditLedger"].values()))
            self.assertEqual(len(ledger["receipts"]), 1)

            for name, field, value in (
                ("missing_source_root", "sourceRoot", None),
                ("relative_source_root", "sourceRoot", "relative/audit"),
                ("changed_issuer", "issuer", "issuer-b"),
                ("changed_series", "auditSeriesId", "series-b"),
            ):
                with self.subTest(name=name):
                    bad = json.loads(json.dumps(first))
                    if field == "auditSeriesId":
                        bad["sourceRef"][field] = value
                    elif value is None:
                        bad.pop(field)
                    else:
                        bad[field] = value
                    bad["receiptSha256"] = context_governor.global_block_receipt_digest(bad)
                    rejected = context_governor.evaluate_program_block_audit(
                        {
                            "taskId": "audit-new",
                            "workspace": str(workspace),
                            "inputTokens": 1,
                            "programBlockAssessment": {
                                "blockerCode": "external-release-gate",
                                "auditReceipt": bad,
                                "safeReadyLaneCount": 0,
                                "rerouteAvailable": False,
                                "externalStateChangeRequired": True,
                            },
                        },
                        {"programBlockAuthorityRegistry": registry},
                        limits(),
                    )
                    self.assertFalse(rejected["programGoalBlocked"])

    def test_global_block_replays_full_prior_receipt_envelopes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve()
            audit_root = workspace / "audit"
            audit_root.mkdir()
            registry = {
                "neutral-qa": {
                    "issuer": "neutral_qa_lane",
                    "auditSeriesId": "external-release-gate-audit-series",
                    "sourceRoot": str(audit_root),
                }
            }
            first = global_block_receipt(
                workspace,
                audit_root / "one.json",
                1,
                None,
                observed_at=(datetime.now(timezone.utc) - timedelta(seconds=3)).isoformat().replace("+00:00", "Z"),
            )
            base_state = context_governor.evaluate_program_block_audit(
                {
                    "taskId": "audit",
                    "workspace": str(workspace),
                    "inputTokens": 1,
                    "programBlockAssessment": {
                        "blockerCode": "external-release-gate",
                        "auditReceipt": first,
                        "safeReadyLaneCount": 0,
                        "rerouteAvailable": False,
                        "externalStateChangeRequired": True,
                    },
                },
                {"programBlockAuthorityRegistry": registry},
                limits(),
            )["state"]
            second = global_block_receipt(
                workspace,
                audit_root / "two.json",
                2,
                str(first["receiptSha256"]),
                observed_at=(datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat().replace("+00:00", "Z"),
            )
            for name, tamper in (
                ("ledger_envelope", lambda state: next(iter(state["programBlockAuditLedger"].values()))["receipts"][0].update(receiptId="fabricated")),
                ("source_hash_only", lambda state: next(iter(state["programBlockAuditLedger"].values()))["receipts"][0].update(safeReadyLaneCount="0")),
            ):
                with self.subTest(name=name):
                    state = json.loads(json.dumps(base_state))
                    tamper(state)
                    result = context_governor.evaluate_program_block_audit(
                        {
                            "taskId": "audit",
                            "workspace": str(workspace),
                            "inputTokens": 1,
                            "programBlockAssessment": {
                                "blockerCode": "external-release-gate",
                                "auditReceipt": second,
                                "safeReadyLaneCount": 0,
                                "rerouteAvailable": False,
                                "externalStateChangeRequired": True,
                            },
                        },
                        state,
                        limits(),
                    )
                    ledger = next(iter(result["state"]["programBlockAuditLedger"].values()))
                    self.assertEqual(len(ledger["receipts"]), 1)

            source_path = audit_root / "one.json"
            source_data = json.loads(source_path.read_text(encoding="utf-8"))
            source_data["issuer"] = "tampered-source"
            source_path.write_text(json.dumps(source_data, sort_keys=True) + "\n", encoding="utf-8")
            hash_only_state = json.loads(json.dumps(base_state))
            prior = next(iter(hash_only_state["programBlockAuditLedger"].values()))["receipts"][0]
            prior["sourceRef"]["hash"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
            prior["receiptSha256"] = context_governor.global_block_receipt_digest(prior)
            rejected = context_governor.evaluate_program_block_audit(
                {
                    "taskId": "audit",
                    "workspace": str(workspace),
                    "inputTokens": 1,
                    "programBlockAssessment": {
                        "blockerCode": "external-release-gate",
                        "auditReceipt": second,
                        "safeReadyLaneCount": 0,
                        "rerouteAvailable": False,
                        "externalStateChangeRequired": True,
                    },
                },
                hash_only_state,
                limits(),
            )
            ledger = next(iter(rejected["state"]["programBlockAuditLedger"].values()))
            self.assertEqual(len(ledger["receipts"]), 1)

    def test_global_block_timestamps_use_strict_rfc3339(self) -> None:
        invalid = (
            "2026-08-13 00:00:00Z",
            "2026-08-13T00:00:00z",
            "2026-08-13T00:00:00",
            "2026-08-13",
            "2026-08-13T00:00:00+8:00",
            "2026-08-13T00:00:00.1234567Z",
        )
        for value in invalid:
            with self.subTest(value=value):
                self.assertIsNone(context_governor.parse_rfc3339(value))

    def test_global_block_rejects_reused_source_through_path_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve()
            audit_root = workspace / "audit"
            audit_root.mkdir()
            registry = {
                "neutral-qa": {
                    "issuer": "neutral_qa_lane",
                    "auditSeriesId": "external-release-gate-audit-series",
                    "sourceRoot": str(audit_root),
                }
            }
            first = global_block_receipt(
                workspace,
                audit_root / "same.json",
                1,
                None,
                observed_at=(datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat().replace("+00:00", "Z"),
            )
            state = context_governor.evaluate_program_block_audit(
                {
                    "taskId": "audit",
                    "workspace": str(workspace),
                    "inputTokens": 1,
                    "programBlockAssessment": {
                        "blockerCode": "external-release-gate",
                        "auditReceipt": first,
                        "safeReadyLaneCount": 0,
                        "rerouteAvailable": False,
                        "externalStateChangeRequired": True,
                    },
                },
                {"programBlockAuthorityRegistry": registry},
                limits(),
            )["state"]
            source_record = json.loads((audit_root / "same.json").read_text(encoding="utf-8"))
            source_record.update(
                receiptId="audit-global-2",
                sequence=2,
                previousReceiptSha256=first["receiptSha256"],
                observedAt=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
            )
            (audit_root / "same.json").write_text(json.dumps(source_record, sort_keys=True) + "\n", encoding="utf-8")
            second = {
                "receiptId": "audit-global-2",
                "authorityId": "neutral-qa",
                "issuer": "neutral_qa_lane",
                "sourceRoot": str(audit_root),
                "sourceRef": {
                    "path": "audit/../audit/same.json",
                    "hash": hashlib.sha256((audit_root / "same.json").read_bytes()).hexdigest(),
                    "auditSeriesId": "external-release-gate-audit-series",
                },
                "observedAt": source_record["observedAt"],
                "workspace": str(workspace),
                "scope": "program_goal",
                "blockerCode": "external-release-gate",
                "sequence": 2,
                "previousReceiptSha256": first["receiptSha256"],
                "safeReadyLaneCount": 0,
                "rerouteAvailable": False,
                "externalStateChangeRequired": True,
            }
            second["receiptSha256"] = context_governor.global_block_receipt_digest(second)
            result = context_governor.evaluate_program_block_audit(
                {
                    "taskId": "audit",
                    "workspace": str(workspace),
                    "inputTokens": 1,
                    "programBlockAssessment": {
                        "blockerCode": "external-release-gate",
                        "auditReceipt": second,
                        "safeReadyLaneCount": 0,
                        "rerouteAvailable": False,
                        "externalStateChangeRequired": True,
                    },
                },
                state,
                limits(),
            )
            ledger = next(iter(result["state"]["programBlockAuditLedger"].values()))
            self.assertEqual(len(ledger["receipts"]), 1)

    def test_only_trusted_fresh_verified_replacement_clears_global_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve()
            audit_root = workspace / "audit"
            audit_root.mkdir()
            registry = {
                "neutral-qa": {
                    "issuer": "neutral_qa_lane",
                    "auditSeriesId": "external-release-gate-audit-series",
                    "sourceRoot": str(audit_root),
                }
            }
            state: dict[str, object] = {"programBlockAuthorityRegistry": registry}
            previous = None
            for sequence in range(1, 4):
                receipt = global_block_receipt(
                    workspace,
                    audit_root / f"proof-{sequence}.json",
                    sequence,
                    previous,
                    observed_at=(datetime.now(timezone.utc) - timedelta(seconds=4 - sequence)).isoformat().replace("+00:00", "Z"),
                )
                result = context_governor.evaluate_program_block_audit(
                    {
                        "taskId": "audit",
                        "workspace": str(workspace),
                        "inputTokens": 1,
                        "programBlockAssessment": {
                            "blockerCode": "external-release-gate",
                            "auditReceipt": receipt,
                            "safeReadyLaneCount": 0,
                            "rerouteAvailable": False,
                            "externalStateChangeRequired": True,
                        },
                    },
                    state,
                    limits(),
                )
                state = result["state"]
                previous = str(receipt["receiptSha256"])
            active = state["programGlobalBlock"]
            packet = valid_takeover_packet("fresh-global-generation")
            recovered_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            recovery_receipt = {
                "recoveryId": "global-recovery-1",
                "ledgerKey": active["ledgerKey"],
                "proofReceiptSha256": active["proofReceiptSha256"],
                "workspace": active["workspace"],
                "blockerCode": active["blockerCode"],
                "replacementTaskKey": "clean-global-replacement",
                "contextGenerationId": packet["contextGenerationId"],
                "observedAt": recovered_at,
            }
            recovery_receipt["recoveryReceiptSha256"] = hashlib.sha256(
                json.dumps(recovery_receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            event = preflight_fields("clean-global-replacement", "global-recovery-request") | {
                "workspace": str(workspace),
                "lane": "impl",
                "takeoverPacket": packet,
                "programBlockRecoveryReceipt": recovery_receipt,
            }

            ordinary = context_governor.evaluate(event, state, limits())
            self.assertTrue(ordinary["programGoalBlocked"])
            self.assertTrue(ordinary["state"]["programGlobalBlock"]["active"])

            invalid = dict(event)
            invalid["programBlockRecoveryReceipt"] = dict(event["programBlockRecoveryReceipt"])
            invalid["programBlockRecoveryReceipt"]["proofReceiptSha256"] = "0" * 64
            still_blocked = context_governor.evaluate_program_block_recovery(invalid, state, limits())
            self.assertTrue(still_blocked["programGoalBlocked"])
            self.assertTrue(still_blocked["state"]["programGlobalBlock"]["active"])

            recovered = context_governor.evaluate_program_block_recovery(event, state, limits())
            self.assertEqual(recovered["decision"], "allow")
            self.assertTrue(recovered["resumeProgramGoal"])
            self.assertTrue(recovered["clearHistoricalGoalBlocked"])
            self.assertFalse(recovered["state"]["programGlobalBlock"]["active"])
            self.assertEqual(
                recovered["state"]["recoveryTransitions"][-1]["status"],
                "verified_global_replacement_ready",
            )

    def test_fabricated_or_unverifiable_global_block_receipts_never_advance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve()
            source = workspace / "audit-source.json"
            source.write_text('{"status":"blocked"}\n', encoding="utf-8")
            base_event = {
                "taskId": "alpha",
                "workspace": str(workspace),
                "inputTokens": 100,
                "programBlockAssessment": {
                    "blockerCode": "external-release-gate",
                    "safeReadyLaneCount": 0,
                    "rerouteAvailable": False,
                    "externalStateChangeRequired": True,
                },
            }
            fabricated = json.loads(json.dumps(base_event))
            fabricated["programBlockAssessment"]["auditReceiptId"] = "three-strings-are-not-proof"
            result = context_governor.evaluate(fabricated, {}, limits())
            self.assertFalse(result["programGoalBlocked"])
            self.assertEqual(result["state"]["programBlockAuditLedger"], {})

            valid_looking = global_block_receipt(
                workspace,
                workspace / "audit-source-valid-looking.json",
                1,
                None,
                observed_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            )
            direct = json.loads(json.dumps(base_event))
            direct["programBlockAssessment"]["auditReceipt"] = valid_looking
            direct_state = {
                "programBlockAuthorityRegistry": {
                    "neutral-qa": {
                        "issuer": "neutral_qa_lane",
                        "auditSeriesId": "external-release-gate-audit-series",
                        "sourceRoot": str(workspace),
                    }
                }
            }
            direct_result = context_governor.evaluate(direct, direct_state, limits())
            self.assertFalse(direct_result["programGoalBlocked"])
            self.assertEqual(direct_result["state"]["programBlockAuditLedger"], {})

            cases = []
            for name, mutate in (
                ("bad_hash", lambda receipt: receipt["sourceRef"].update(hash="0" * 64)),
                (
                    "stale",
                    lambda receipt: receipt.update(
                        observedAt=(datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
                    ),
                ),
                (
                    "future",
                    lambda receipt: receipt.update(
                        observedAt=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
                    ),
                ),
                ("scope", lambda receipt: receipt.update(scope="lane")),
                ("sequence", lambda receipt: receipt.update(sequence=2)),
                ("source", lambda receipt: receipt["sourceRef"].update(path="missing.json")),
            ):
                receipt = global_block_receipt(
                    workspace,
                    source,
                    1,
                    None,
                    observed_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                )
                mutate(receipt)
                receipt["receiptSha256"] = context_governor.global_block_receipt_digest(receipt)
                cases.append((name, receipt))
            receipt = global_block_receipt(
                workspace,
                source,
                1,
                None,
                observed_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            )
            receipt["receiptSha256"] = "f" * 64
            cases.append(("receipt_digest", receipt))

            for name, receipt in cases:
                with self.subTest(name=name):
                    event = json.loads(json.dumps(base_event))
                    event["programBlockAssessment"]["auditReceipt"] = receipt
                    result = context_governor.evaluate(event, {}, limits())
                    self.assertFalse(result["programGoalBlocked"])
                    ledgers = result["state"]["programBlockAuditLedger"]
                    self.assertTrue(all(not ledger.get("receipts") for ledger in ledgers.values()))

    def test_recovery_control_allowlist_never_enables_project_or_provider_tools(self) -> None:
        result = context_governor.evaluate(
            {
                "taskId": "alpha",
                "inputTokens": 100,
                "memory": {
                    "memoryMode": "fallback_stale",
                    "current": False,
                    "recoveryReady": False,
                    "authorityVerification": "unavailable",
                },
            },
            {},
            limits(),
        )
        self.assertFalse(result["allowToolCalls"])
        self.assertFalse(result["allowProjectToolCalls"])
        self.assertFalse(result["allowProviderCalls"])
        self.assertTrue(result["allowRecoveryControlTools"])
        self.assertEqual(result["recoveryControlToolAllowlist"], ["scan_workspace", "verify_project"])

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

    def test_actual_takeover_bytes_override_fabricated_low_token_estimate(self) -> None:
        packet = valid_takeover_packet()
        packet["tokenEstimate"] = 1
        packet["continuity"] = ["x" * (2 * 1024 * 1024)]
        result = context_governor.evaluate(
            {"taskId": "oversized", "inputTokens": 1, "takeoverPacket": packet},
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "freeze")
        self.assertEqual(result["reason"], "event_string_bytes_limit_exceeded")
        self.assertFalse(result["allowProjectToolCalls"])
        self.assertFalse(result["allowProviderCalls"])

    def test_actual_takeover_serialized_bytes_have_independent_hard_limit(self) -> None:
        packet = valid_takeover_packet()
        packet["tokenEstimate"] = 1
        packet["continuity"] = ["x" * 70 for _ in range(4000)]
        result = context_governor.evaluate(
            {"taskId": "serialized-oversized", "inputTokens": 1, "takeoverPacket": packet},
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "freeze")
        self.assertEqual(result["reason"], "takeover_packet_serialized_bytes_exceeded")
        self.assertGreater(result["metrics"]["serializedBytes"], 256 * 1024)

    def test_excessive_nesting_returns_typed_freeze_without_recursion_error(self) -> None:
        nested: dict[str, object] = {}
        cursor = nested
        for _ in range(2000):
            child: dict[str, object] = {}
            cursor["next"] = child
            cursor = child
        result = context_governor.evaluate(
            {"taskId": "deep", "inputTokens": 1, "takeoverPacket": nested},
            {},
            limits(),
        )
        self.assertEqual(result["decision"], "freeze")
        self.assertEqual(result["reason"], "event_structure_depth_limit_exceeded")
        self.assertFalse(result["allowToolCalls"])

    def test_cli_cannot_forge_host_context_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            event = tmp_path / "event.json"
            state = tmp_path / "state.json"
            cli_event = preflight_fields("cli-task", "cli-request")
            cli_event.pop("_hostTelemetryCapability")
            event.write_text(json.dumps(cli_event), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(event), "--state", str(state), "--write-state"],
                check=False,
                capture_output=True,
                text=True,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(result["decision"], "block")
            self.assertEqual(result["reason"], "host_context_telemetry_unavailable")
            self.assertTrue(state.exists())
            saved = json.loads(state.read_text())
            self.assertEqual(saved["cumulativeInputTokens"], 0)

    def test_cli_authorization_state_requires_exact_durable_confirmation(self) -> None:
        mutations = ("tampered_target", "missing", "malformed", "forged", "cleanup_ambiguity")
        for mutation in mutations:
            for write_state in (False, True):
                with self.subTest(mutation=mutation, write_state=write_state), tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    event = tmp_path / "event.json"
                    state = tmp_path / "state.json"
                    event.write_text(json.dumps({"inputTokens": 1}), encoding="utf-8")
                    context_governor.atomic_state.atomic_write_json(
                        state,
                        {
                            "schema": context_governor.SCHEMA,
                            "cumulativeInputTokens": 1,
                            "programGlobalBlock": {"active": False},
                        },
                    )
                    confirmed = context_governor.atomic_state.confirmation_path(state)
                    if mutation == "tampered_target":
                        state.write_text(json.dumps({"allowProviderCalls": True}), encoding="utf-8")
                        state.chmod(0o600)
                    elif mutation == "missing":
                        confirmed.unlink()
                    elif mutation == "malformed":
                        confirmed.write_text("[]", encoding="utf-8")
                        confirmed.chmod(0o600)
                    elif mutation == "forged":
                        receipt = json.loads(confirmed.read_text(encoding="utf-8"))
                        receipt["previousSha256"] = "1" * 64
                        receipt["intendedSha256"] = "2" * 64
                        confirmed.write_text(json.dumps(receipt), encoding="utf-8")
                        confirmed.chmod(0o600)
                    else:
                        pending = context_governor.atomic_state.uncertainty_path(state)
                        pending.write_text(confirmed.read_text(encoding="utf-8"), encoding="utf-8")
                        pending.chmod(0o600)
                    command = [sys.executable, str(SCRIPT), str(event), "--state", str(state)]
                    if write_state:
                        command.append("--write-state")
                    completed = subprocess.run(command, capture_output=True, text=True)
                    self.assertNotEqual(completed.returncode, 0)
                    result = json.loads(completed.stdout)
                    self.assertEqual(result["decision"], "freeze")
                    self.assertFalse(result["allowToolCalls"])
                    self.assertFalse(result["allowProjectToolCalls"])
                    self.assertFalse(result["allowProviderCalls"])
                    self.assertFalse(result["allowOldThreadExecution"])

    def test_cli_completed_sticky_block_cannot_rollback_to_receipt_preimage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            event = tmp_path / "event.json"
            state = tmp_path / "state.json"
            event.write_text(
                json.dumps({"taskId": "ordinary-after-restart", "inputTokens": 1}),
                encoding="utf-8",
            )
            before = context_governor.default_state({"taskId": "ceo"})
            after = json.loads(json.dumps(before))
            after["programGlobalBlock"] = {
                "active": True,
                "blockerCode": "external-global-stop",
                "knownGenerationIds": ["generation-before-block"],
            }
            context_governor.atomic_state.atomic_write_json(state, before)
            context_governor.atomic_state.atomic_write_json(state, after)
            state.write_bytes(context_governor.atomic_state.canonical_json(before))
            state.chmod(0o600)

            for write_state in (False, True):
                command = [sys.executable, str(SCRIPT), str(event), "--state", str(state)]
                if write_state:
                    command.append("--write-state")
                completed = subprocess.run(command, capture_output=True, text=True)
                self.assertNotEqual(completed.returncode, 0)
                result = json.loads(completed.stdout)
                self.assertEqual(result["decision"], "freeze")
                self.assertFalse(result["allowToolCalls"])
                self.assertFalse(result["allowProjectToolCalls"])
                self.assertFalse(result["allowProviderCalls"])
                self.assertFalse(result["allowOldThreadExecution"])


if __name__ == "__main__":
    unittest.main()
