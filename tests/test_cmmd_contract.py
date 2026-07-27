from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "ceo-thread-orchestrator" / "scripts" / "validate_cmmd_exchange.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_cmmd_exchange", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_cmmd_exchange"] = module
    spec.loader.exec_module(module)
    return module


cmmd = load_module()
SHA = "a" * 64


def r0_task() -> dict:
    task = {
        "schema": "ceoflow.external_execution_task.v2",
        "taskId": "task-r0",
        "taskSha256": SHA,
        "projectId": "project-a",
        "projectIdentitySha256": SHA,
        "laneRole": "review",
        "projectRoleThreadId": "thread-review",
        "runId": "run-1",
        "executionEpoch": 1,
        "runReservationId": "reservation-1",
        "contextViewId": "view-1",
        "contextViewSha256": SHA,
        "contextViewCompiledAt": "2026-07-27T00:00:00.000Z",
        "canonicalRoot": "C:\\project",
        "workspace": {"mode": "registered-readonly", "baseline": "abc123"},
        "riskTier": "R0",
        "route": {"provider": "moonshot", "model": "kimi-k3", "fallback": "deny", "retry": 0},
        "objective": "Inspect one bounded source range.",
        "acceptance": ["Return two evidence-backed verdicts."],
        "sourceRefs": [{"id": "src-1", "path": "src/a.ts", "sha256": SHA, "ranges": [{"id": "r-1", "startLine": 1, "endLine": 20}]}],
        "readContract": {"sourceRefAllowlist": ["src-1"], "maxFiles": 1, "maxRanges": 1, "maxSearchMatches": 10, "maxBytesPerToolResult": 4000, "maxTotalSourceBytes": 8000, "searchFirst": True},
        "budgets": {"maxModelRequests": 1, "maxToolCalls": 2, "maxInputTokensPerRequest": 8000, "maxCumulativeInputTokens": 12000, "maxCumulativeToolResultBytes": 8000, "maxWallTimeMs": 120000},
        "writeSet": [],
        "authorizationLeaseRequired": False,
        "commandAllowlist": [],
        "providerContextPolicy": {"authority": "cmmd_compiled_view", "nativeMemory": "disabled-required", "conversationReuse": "per-run-none"},
        "visibleThreadPolicy": {"archiveAfterReceipt": False, "terminalClosesVisibleThread": False},
        "forbiddenPayloadsPresent": False,
    }
    task["projectIdentitySha256"] = cmmd.compute_project_identity_sha256(task)
    task["contextViewSha256"] = cmmd.compute_context_view_sha256(r0_context_view(task))
    task["taskSha256"] = cmmd.compute_task_sha256(task)
    return task


def r0_receipt(task: dict) -> dict:
    used = {"modelRequests": 1, "toolCalls": 0, "inputTokens": 6000, "toolResultBytes": 0, "wallTimeMs": 9000}
    remaining = {
        "modelRequests": task["budgets"]["maxModelRequests"] - used["modelRequests"],
        "toolCalls": task["budgets"]["maxToolCalls"] - used["toolCalls"],
        "inputTokens": task["budgets"]["maxCumulativeInputTokens"] - used["inputTokens"],
        "toolResultBytes": task["budgets"]["maxCumulativeToolResultBytes"] - used["toolResultBytes"],
        "wallTimeMs": task["budgets"]["maxWallTimeMs"] - used["wallTimeMs"],
    }
    receipt_refs = copy.deepcopy(task["sourceRefs"])
    for source_ref in receipt_refs:
        for source_range in source_ref["ranges"]:
            source_range["lineCount"] = source_range.pop("endLine") - source_range["startLine"] + 1
    return {
        "schema": "ceoflow.external_execution_receipt.v2",
        **{field: task[field] for field in cmmd.IDENTITY_FIELDS},
        "startedAt": "2026-07-27T00:00:01.000Z",
        "completedAt": "2026-07-27T00:00:10.000Z",
        "attempt": 1,
        "terminalStatus": "succeeded",
        "failure": None,
        "result": "Both claims are not proven by the bounded ranges.",
        "route": {"requestedProvider": "moonshot", "requestedModel": "kimi-k3", "actualProvider": "moonshot", "actualModel": "kimi-k3", "fallback": "deny", "retry": 0, "reasoning": "off", "runtime": "cmmd", "executionLocation": "host"},
        "usage": {"reported": True, "source": "provider", "providerCallCount": 1, "inputTokens": 6000, "outputTokens": 300, "cachedInputTokens": 0, "cacheWriteTokens": 0, "uncachedInputTokens": 6000, "grossTokens": 6300, "serializedInputChars": 20000, "serializedInputBytes": 20000, "toolCallCount": 0, "deliveredToolResultBytes": 0, "cost": {"reported": True, "currency": "CNY", "amount": 0.4}},
        "budget": {"class": "R0", "limits": task["budgets"], "used": used, "remaining": remaining, "fuseTripped": None},
        "sourceRefs": receipt_refs,
        "changedFiles": [],
        "writeSetCompliance": {"status": "compliant", "declaredPaths": [], "violationPaths": []},
        "commands": [],
        "tests": [],
        "artifacts": [],
        "workspaceFingerprint": {"status": "available", "before": SHA, "after": SHA},
        "authorizationLease": {"required": False, "leaseId": None, "status": "not-issued"},
        "provenance": {"authority": "host-owned", "task": "validated-g2", "run": "matching-active-task-run-ledger", "evidence": "terminal-g6a-host-run-evidence-ledger"},
        "forbiddenPayloadsPresent": False,
        "run": {"closed": True, "closedAt": "2026-07-27T00:00:10.000Z", "ephemeralCleanup": {"serializedProviderBodies": True, "providerCallMap": True, "toolCallMap": True, "rawToolBodiesStored": False, "governorInternal": {"requestLedgerEntries": 0, "toolLedgerEntries": 0, "pendingProviderCalls": 0, "pendingToolReservations": 0, "reservedProviderInputTokens": 0, "reservedToolResultBytes": 0, "grossTokenEvents": 0, "sealed": True}}},
        "visibleThread": {"archiveState": "active", "archivedAt": None},
    }


def r0_context_view(task: dict) -> dict:
    current_run = {
        "projectRoleThreadId": task["projectRoleThreadId"],
        "taskId": task["taskId"],
        "runId": task["runId"],
        "executionEpoch": task["executionEpoch"],
        "contextViewId": task["contextViewId"],
        "contextViewCompiledAt": task["contextViewCompiledAt"],
        "messages": [],
        "toolResults": [],
    }
    task_projection = {
        "projectRoleThreadId": task["projectRoleThreadId"],
        "taskId": task["taskId"],
        "runId": task["runId"],
        "executionEpoch": task["executionEpoch"],
        "contextViewId": task["contextViewId"],
        "contextViewCompiledAt": task["contextViewCompiledAt"],
        "objective": task["objective"],
        "acceptance": task["acceptance"],
        "riskTier": task["riskTier"],
        "route": task["route"],
        "sourceRefs": task["sourceRefs"],
        "readContract": task["readContract"],
        "permissions": {
            "sourceRefAllowlist": task["readContract"]["sourceRefAllowlist"],
            "writeSet": task["writeSet"],
            "authorizationLeaseRequired": task["authorizationLeaseRequired"],
        },
        "writeSet": task["writeSet"],
        "providerContextPolicy": task["providerContextPolicy"],
        "forbiddenPayloadsPresent": False,
    }
    layer_kinds = ["task", "workspace", "hot", "warm", "skill", "cold_refs", "current_run"]
    view = {
        "schema": "cmmd.context_view.v1",
        "identity": {
            "contextViewId": task["contextViewId"],
            "contextViewCompiledAt": task["contextViewCompiledAt"],
            "projectRoleThreadId": task["projectRoleThreadId"],
            "runId": task["runId"],
            "taskId": task["taskId"],
            "taskSha256": task["taskSha256"],
            "executionEpoch": task["executionEpoch"],
        },
        "compiledAt": task["contextViewCompiledAt"],
        "layers": [
            {"kind": "task", "payload": task_projection},
            {"kind": "workspace", "payload": {"baseline": task["workspace"]["baseline"], "diff": "", "files": [], "symbols": []}},
            {"kind": "hot", "payload": []},
            {"kind": "warm", "payload": []},
            {"kind": "skill", "payload": []},
            {"kind": "cold_refs", "payload": []},
            {"kind": "current_run", "payload": current_run},
        ],
        "sourceRefs": [],
        "estimates": {
            "bytes": 0,
            "deliveredBytes": 0,
            "estimatedTokens": 0,
            "layers": [{"kind": kind, "bytes": 0, "estimatedTokens": 0} for kind in layer_kinds],
        },
        "budgets": {"taskBytes": 20000, "workspaceBytes": 20000, "hotBytes": 20000, "warmBytes": 20000, "skillBytes": 20000, "coldRefsBytes": 20000, "currentRunBytes": 20000, "totalBytes": 140000},
        "warmAnchorTrigger": None,
        "providerContextPolicy": task["providerContextPolicy"],
        "forbiddenPayloadsPresent": False,
        "contextViewSha256": task["contextViewSha256"],
    }
    layer_bytes = [len(cmmd._canonical(layer).encode("utf-8")) for layer in view["layers"]]
    view["estimates"]["bytes"] = sum(layer_bytes)
    view["estimates"]["layers"] = [
        {"kind": kind, "bytes": size, "estimatedTokens": size}
        for kind, size in zip(layer_kinds, layer_bytes)
    ]
    for _ in range(16):
        view["contextViewSha256"] = cmmd.compute_context_view_sha256(view)
        delivered = len(cmmd._canonical(view).encode("utf-8"))
        if view["estimates"]["deliveredBytes"] == delivered and view["estimates"]["estimatedTokens"] == delivered:
            break
        view["estimates"]["deliveredBytes"] = delivered
        view["estimates"]["estimatedTokens"] = delivered
    return view


def readiness_evidence(task: dict, *tiers: str, state: str = "live_smoke_ready") -> dict:
    return {
        "schema": "ceoflow.cmmd_readiness_evidence.v1",
        "authority": "independent-review",
        "projectId": task["projectId"],
        "projectIdentitySha256": task["projectIdentitySha256"],
        "provider": task["route"]["provider"],
        "model": task["route"]["model"],
        "state": state,
        "admittedRiskTiers": list(tiers),
        "contractSnapshot": {
            "taskV2": cmmd.SCHEMA_HASHES["ceoflow.external_execution_task.v2.schema.json"],
            "receiptV2": cmmd.SCHEMA_HASHES["ceoflow.external_execution_receipt.v2.schema.json"],
            "authorizationLeaseV1": cmmd.SCHEMA_HASHES["ceoflow.authorization_lease.v1.schema.json"],
            "contextViewV1": cmmd.SCHEMA_HASHES["cmmd.context_view.v1.schema.json"],
        },
        "observedAt": "2026-07-27T00:00:00.000Z",
        "expiresAt": "2036-07-27T00:00:00.000Z",
        "evidenceRefs": [{"id": "cmmd-r0-review", "path": "docs/smoke/cmmd-r0.md", "sha256": SHA}],
    }


class CmmdContractTests(unittest.TestCase):
    def test_vendored_schema_snapshot_hashes_match_cmmd_contract(self):
        self.assertEqual(cmmd.verify_schema_snapshot(), [])

    def test_valid_r0_exchange_is_candidate_not_acceptance(self):
        task = r0_task()
        result = cmmd.validate_exchange(
            task, r0_receipt(task), context_view=r0_context_view(task), readiness=readiness_evidence(task, "R0")
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["decision"], "candidate_for_ceo_review")
        self.assertIn("not CEO acceptance", result["note"])

    def test_r0_write_attempt_fails_closed(self):
        task = r0_task()
        task["writeSet"] = ["src/a.ts"]
        receipt = r0_receipt(task)
        receipt["changedFiles"] = ["src/a.ts"]
        result = cmmd.validate_exchange(
            task, receipt, context_view=r0_context_view(task), readiness=readiness_evidence(task, "R0")
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("R0" in error for error in result["errors"]))

    def test_actual_model_mismatch_is_rejected_without_fallback(self):
        task = r0_task()
        receipt = r0_receipt(task)
        receipt["route"]["actualModel"] = "different-model"
        result = cmmd.validate_exchange(
            task, receipt, context_view=r0_context_view(task), readiness=readiness_evidence(task, "R0")
        )
        self.assertFalse(result["ok"])
        self.assertIn("successful receipt actualModel differs from requested model", result["errors"])

    def test_r1_requires_lease_artifact_before_admission(self):
        task = r0_task()
        task.update({
            "riskTier": "R1",
            "writeSet": ["src/a.ts"],
            "authorizationLeaseRequired": True,
            "authorizationLeaseId": "lease-1",
            "commandAllowlist": [{"purpose": "verification", "executable": "node", "args": ["--test", "test/a.test.mjs"]}],
        })
        result = cmmd.validate_exchange(
            task, context_view=r0_context_view(task), readiness=readiness_evidence(task, "R1", state="production_acceptance_ready")
        )
        self.assertFalse(result["ok"])
        self.assertIn("R1 exchange requires the authorization lease artifact", result["errors"])
        self.assertIn("current CMMD Context View snapshot is R0-only; R1 is not admissible", result["errors"])

    def test_receipt_cannot_self_accept_or_change_ceo_controls(self):
        task = r0_task()
        receipt = r0_receipt(task)
        receipt["decision"] = "accept"
        receipt["ceoModel"] = "cheaper"
        result = cmmd.validate_exchange(
            task, receipt, context_view=r0_context_view(task), readiness=readiness_evidence(task, "R0")
        )
        self.assertFalse(result["ok"])
        self.assertIn("unexpected top-level field: decision", result["errors"])
        self.assertIn("unexpected top-level field: ceoModel", result["errors"])

    def test_visual_payload_in_receipt_is_rejected(self):
        task = r0_task()
        receipt = r0_receipt(task)
        receipt["result"] = "data:image/png;base64," + "A" * 256
        result = cmmd.validate_exchange(
            task, receipt, context_view=r0_context_view(task), readiness=readiness_evidence(task, "R0")
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("forbidden image/base64 payload" in error for error in result["errors"]))

    def test_missing_context_view_or_readiness_fails_closed(self):
        task = r0_task()
        receipt = r0_receipt(task)
        missing_context = cmmd.validate_exchange(task, receipt, readiness=readiness_evidence(task, "R0"))
        self.assertFalse(missing_context["ok"])
        self.assertIn("CMMD exchange requires the exact bounded Context View artifact", missing_context["errors"])
        missing_readiness = cmmd.validate_exchange(task, receipt, context_view=r0_context_view(task))
        self.assertFalse(missing_readiness["ok"])
        self.assertIn("CMMD R0 requires live_smoke_ready evidence", missing_readiness["errors"])

    def test_nested_schema_invalid_receipt_is_rejected(self):
        task = r0_task()
        receipt = r0_receipt(task)
        del receipt["usage"]["providerCallCount"]
        result = cmmd.validate_exchange(
            task, receipt, context_view=r0_context_view(task), readiness=readiness_evidence(task, "R0")
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("external_execution_receipt.v2.schema.json invalid" in error for error in result["errors"]))

    def test_task_and_context_commitment_tampering_is_rejected(self):
        task = r0_task()
        tampered_task = copy.deepcopy(task)
        tampered_task["objective"] = "Changed after hashing."
        task_result = cmmd.validate_exchange(
            tampered_task,
            r0_receipt(tampered_task),
            context_view=r0_context_view(tampered_task),
            readiness=readiness_evidence(task, "R0"),
        )
        self.assertIn("taskSha256 does not bind the canonical task envelope", task_result["errors"])

        context_view = r0_context_view(task)
        context_view["layers"][1]["payload"]["diff"] = "tampered"
        context_result = cmmd.validate_exchange(
            task,
            r0_receipt(task),
            context_view=context_view,
            readiness=readiness_evidence(task, "R0"),
        )
        self.assertIn("Context View SHA-256 does not bind the canonical Context View", context_result["errors"])

    def test_receipt_source_ranges_must_exactly_project_task(self):
        task = r0_task()
        receipt = r0_receipt(task)
        receipt["sourceRefs"][0]["ranges"][0]["lineCount"] += 1
        result = cmmd.validate_exchange(
            task, receipt, context_view=r0_context_view(task), readiness=readiness_evidence(task, "R0")
        )
        self.assertFalse(result["ok"])
        self.assertIn("successful receipt sourceRefs do not exactly project the task source ranges", result["errors"])

    def test_r0_workspace_fingerprint_must_not_change(self):
        task = r0_task()
        receipt = r0_receipt(task)
        receipt["workspaceFingerprint"]["after"] = "b" * 64
        result = cmmd.validate_exchange(
            task, receipt, context_view=r0_context_view(task), readiness=readiness_evidence(task, "R0")
        )
        self.assertFalse(result["ok"])
        self.assertIn("successful R0 receipt requires identical before/after workspace fingerprints", result["errors"])

    def test_readiness_is_bound_to_project_route_contract_and_expiry(self):
        task = r0_task()
        readiness = readiness_evidence(task, "R0")
        readiness["model"] = "wrong-model"
        readiness["contractSnapshot"]["contextViewV1"] = "b" * 64
        readiness["expiresAt"] = "2026-07-26T00:00:00.000Z"
        errors = cmmd.validate_readiness(
            task, readiness, now=datetime(2026, 7, 27, tzinfo=timezone.utc)
        )
        self.assertIn("CMMD readiness Provider/model does not match task route", errors)
        self.assertIn("CMMD readiness contract snapshot does not match the vendored schemas", errors)
        self.assertIn("CMMD readiness evidence is expired", errors)

    def test_budget_arithmetic_and_context_size_are_reconciled(self):
        task = r0_task()
        receipt = r0_receipt(task)
        receipt["budget"]["remaining"]["inputTokens"] += 1
        receipt_result = cmmd.validate_exchange(
            task, receipt, context_view=r0_context_view(task), readiness=readiness_evidence(task, "R0")
        )
        self.assertIn("receipt budget remaining.inputTokens arithmetic is inconsistent", receipt_result["errors"])

        context_view = r0_context_view(task)
        context_view["estimates"]["deliveredBytes"] += 1
        context_view["estimates"]["estimatedTokens"] += 1
        context_view["contextViewSha256"] = cmmd.compute_context_view_sha256(context_view)
        context_result = cmmd.validate_exchange(
            task, r0_receipt(task), context_view=context_view, readiness=readiness_evidence(task, "R0")
        )
        self.assertIn("Context View delivered byte/token estimate is inconsistent", context_result["errors"])

    def test_r1_lease_expiry_and_commitments_are_checked(self):
        task = r0_task()
        task.update({
            "riskTier": "R1",
            "writeSet": ["src/a.ts"],
            "authorizationLeaseRequired": True,
            "authorizationLeaseId": "lease-1",
            "commandAllowlist": [{"purpose": "verification", "executable": "node", "args": ["--test", "test/a.test.mjs"]}],
        })
        lease = {
            "schema": "ceoflow.authorization_lease.v1",
            "authority": "host-only",
            "leaseId": "lease-1",
            "taskId": task["taskId"],
            "taskSha256": task["taskSha256"],
            "projectId": task["projectId"],
            "projectIdentitySha256": task["projectIdentitySha256"],
            "projectRoleThreadId": task["projectRoleThreadId"],
            "runId": task["runId"],
            "executionEpoch": task["executionEpoch"],
            "writeSetSha256": cmmd._sha256_canonical(sorted(task["writeSet"])),
            "commandAllowlistSha256": cmmd._sha256_canonical(sorted(task["commandAllowlist"], key=cmmd._canonical)),
            "issuedAt": "2026-07-23T00:00:00.000Z",
            "expiresAt": "2026-07-23T00:05:00.000Z",
            "status": "active",
            "consumedAt": None,
        }
        errors = cmmd.validate_lease(
            task, lease, now=datetime(2026, 7, 27, tzinfo=timezone.utc)
        )
        self.assertIn("authorization lease is expired", errors)
        lease["writeSetSha256"] = "b" * 64
        errors = cmmd.validate_lease(
            task, lease, now=datetime(2026, 7, 23, 0, 1, tzinfo=timezone.utc)
        )
        self.assertIn("authorization lease writeSetSha256 does not bind the task write-set", errors)


if __name__ == "__main__":
    unittest.main()
