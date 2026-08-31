from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_external_harness_route.py"
TEMPLATES = ROOT / "templates"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_external_harness_route", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


router = load_module()


class ExternalHarnessRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = {
            "schema": "external_harness_adapter_v1",
            "adapterPolicyId": "fixture-policy-v1",
            "mappingSource": "accepted-project-policy",
            "globalDefaultModel": "provider-default",
            "routes": {
                "fast": {
                    "selectionSurface": "cli_profile",
                    "selector": {"profile": "fixture-fast", "patch": "reasoning=low"},
                    "model": "fixture-fast-model",
                    "reasoning": "low",
                    "directModelOverride": False,
                    "identityProofMethods": ["cli_dispatch_receipt"],
                },
                "balanced": {
                    "selectionSurface": "cli_patch",
                    "selector": {"config": "fixture-balanced", "patch": "reasoning=medium"},
                    "model": "fixture-balanced-model",
                    "reasoning": "medium",
                    "directModelOverride": False,
                    "identityProofMethods": ["cli_dispatch_receipt"],
                },
                "frontier": {
                    "selectionSurface": "web_session",
                    "selector": {"modelSelector": "fixture-frontier", "reasoningSelector": "high"},
                    "model": "fixture-frontier-model",
                    "reasoning": "high",
                    "directModelOverride": True,
                    "identityProofMethods": ["web_session_metadata"],
                },
            },
            "retryPolicy": {"defaultRetries": 0, "authorizedMaxRetries": 0},
            "pricing": {"status": "unavailable"},
        }

    def make_dispatch(self, capability: str = "fast") -> dict:
        route = self.adapter["routes"][capability]
        return {
            "schema": "external_harness_dispatch_v1",
            "dispatchId": f"dispatch-{capability}",
            "adapterPolicyId": self.adapter["adapterPolicyId"],
            "adapterPolicyDigest": router.canonical_sha256(self.adapter),
            "requestedCapabilityClass": capability,
            "requestedModel": route["model"],
            "requestedReasoning": route["reasoning"],
            "selectionSurface": route["selectionSurface"],
            "selector": copy.deepcopy(route["selector"]),
            "explicitRoute": True,
            "allowGlobalDefaultInheritance": False,
            "retryCount": 0,
            "guard": {
                "allowedTools": ["read", "glob", "grep", "edit"],
                "exactWriteSet": ["src/example.py", "tests/**"],
                "allowedCommands": ["python -m unittest"],
                "isolatedWorkspace": True,
                "independentCodexReviewRequired": True,
            },
            "fallback": {
                "declared": True,
                "routeId": "declared-codex-fallback",
                "owner": "ceo",
            },
            "ceoInvariant": {
                "model": "ceo-model-opaque",
                "reasoning": "ceo-reasoning-opaque",
                "permissionsDigest": "permissions-opaque",
            },
        }

    def make_receipt(self, dispatch: dict) -> dict:
        capability = dispatch["requestedCapabilityClass"]
        route = self.adapter["routes"][capability]
        proof_method = route["identityProofMethods"][0]
        return {
            "schema": "external_harness_receipt_v1",
            "dispatchId": dispatch["dispatchId"],
            "adapterPolicyId": dispatch["adapterPolicyId"],
            "adapterPolicyDigest": dispatch["adapterPolicyDigest"],
            "requestedCapabilityClass": capability,
            "requestedModel": route["model"],
            "actualModel": route["model"],
            "requestedReasoning": route["reasoning"],
            "actualReasoning": route["reasoning"],
            "selectionSurface": route["selectionSurface"],
            "appliedSelector": copy.deepcopy(route["selector"]),
            "routeApplied": True,
            "routeVerified": True,
            "globalDefaultInherited": False,
            "modelIdentityProof": {
                "status": "verified",
                "method": proof_method,
                "selectionSurface": route["selectionSurface"],
                "model": route["model"],
                "reasoning": route["reasoning"],
                "evidenceRef": "artifacts/route.json",
            },
            "usage": {
                "status": "available",
                "inputTokens": 100,
                "outputTokens": 20,
                "cacheTokens": 40,
                "reasoningTokens": 5,
                "totalTokens": 125,
            },
            "elapsed": {"status": "available", "milliseconds": 1200},
            "cost": {"status": "unavailable"},
            "processExitCode": 0,
            "cliExit": 0,
            "taskCompleted": True,
            "stopReason": "completed",
            "taskSuccess": True,
            "timedOut": False,
            "turns": 1,
            "modelCalls": 1,
            "toolPolicyCompliant": True,
            "changedPaths": ["src/example.py", "tests/test_example.py"],
            "commandsExecuted": ["python -m unittest"],
            "writeSetCompliant": True,
            "commandGuardCompliant": True,
            "diffEvidence": ["artifacts/patch.diff"],
            "tests": ["python -m unittest: pass"],
            "independentReview": {
                "reviewer": "codex",
                "status": "accepted",
                "evidenceRef": "artifacts/review.json",
            },
            "retryCount": dispatch["retryCount"],
            "ceoInvariantAfter": copy.deepcopy(dispatch["ceoInvariant"]),
            "fallbackReceipt": None,
        }

    def evaluate(self, capability: str = "fast"):
        dispatch = self.make_dispatch(capability)
        receipt = self.make_receipt(dispatch)
        return router.evaluate(self.adapter, dispatch, receipt), dispatch, receipt

    def test_fast_balanced_frontier_mapping_is_resolved_and_proved(self) -> None:
        for capability in ("fast", "balanced", "frontier"):
            with self.subTest(capability=capability):
                result, _, _ = self.evaluate(capability)
                self.assertTrue(result["ok"], result)
                self.assertEqual(result["decision"], "allow")
                self.assertEqual(result["resolvedCapabilityClass"], capability)
                self.assertEqual(result["actualModel"], self.adapter["routes"][capability]["model"])

    def test_provider_default_reasoning_requires_verified_default_policy(self) -> None:
        adapter = copy.deepcopy(self.adapter)
        adapter["routes"]["fast"]["reasoning"] = "provider_default"
        dispatch = self.make_dispatch("fast")
        dispatch["requestedReasoning"] = "provider_default"
        dispatch["adapterPolicyDigest"] = router.canonical_sha256(adapter)
        receipt = self.make_receipt(dispatch)
        receipt["requestedReasoning"] = "provider_default"
        receipt["actualReasoning"] = "unavailable"
        receipt["modelIdentityProof"].pop("reasoning")
        receipt["reasoningPolicyProof"] = {
            "status": "verified",
            "method": "request_header_reasoning_effort_omitted",
            "requestedReasoning": "provider_default",
            "defaultPolicyApplied": True,
            "concreteEffortKnown": False,
        }
        result = router.evaluate(adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "allow", result)
        self.assertEqual(result["actualReasoning"], "unavailable")

        receipt["actualReasoning"] = "high"
        receipt["reasoningPolicyProof"] = {
            "status": "verified",
            "method": "request_header_adapter_default_reasoning_effort",
            "requestedReasoning": "provider_default",
            "defaultPolicyApplied": True,
            "concreteEffortKnown": True,
            "adapterDefaultField": "reasoningEffort",
            "actualReasoning": "high",
        }
        result = router.evaluate(adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "allow", result)
        self.assertEqual(result["actualReasoning"], "high")

        receipt["reasoningPolicyProof"].pop("adapterDefaultField")
        result = router.evaluate(adapter, dispatch, receipt)
        self.assertEqual(result["reason"], "model_route_unavailable", result)
        self.assertFalse(result["allowExternalHarnessOutput"])

        receipt.pop("reasoningPolicyProof")
        result = router.evaluate(adapter, dispatch, receipt)
        self.assertEqual(result["reason"], "model_route_unavailable", result)
        self.assertFalse(result["allowExternalHarnessOutput"])

    def test_cli_without_model_override_uses_profile_or_patch(self) -> None:
        for capability in ("fast", "balanced"):
            route = self.adapter["routes"][capability]
            self.assertFalse(route["directModelOverride"])
            self.assertNotIn("model", route["selector"])
            result, _, _ = self.evaluate(capability)
            self.assertEqual(result["decision"], "allow")

    def test_cli_rejects_direct_model_override_when_unsupported(self) -> None:
        adapter = copy.deepcopy(self.adapter)
        adapter["routes"]["fast"]["selector"]["model"] = "forbidden-direct-override"
        dispatch = self.make_dispatch("fast")
        dispatch["adapterPolicyDigest"] = router.canonical_sha256(adapter)
        dispatch["selector"] = copy.deepcopy(adapter["routes"]["fast"]["selector"])
        receipt = self.make_receipt(dispatch)
        receipt["appliedSelector"] = copy.deepcopy(dispatch["selector"])
        result = router.evaluate(adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "block")
        self.assertTrue(any("unsupported direct model override" in error for error in result["errors"]))

    def test_web_session_selector_is_verified(self) -> None:
        result, dispatch, receipt = self.evaluate("frontier")
        self.assertEqual(dispatch["selectionSurface"], "web_session")
        self.assertIn("modelSelector", dispatch["selector"])
        self.assertEqual(receipt["modelIdentityProof"]["method"], "web_session_metadata")
        self.assertEqual(result["decision"], "allow")

    def test_unsupported_selection_surface_routes_to_declared_fallback(self) -> None:
        adapter = copy.deepcopy(self.adapter)
        route = adapter["routes"]["fast"]
        route["selectionSurface"] = "unsupported"
        route["selector"] = {}
        dispatch = self.make_dispatch("fast")
        dispatch["adapterPolicyDigest"] = router.canonical_sha256(adapter)
        dispatch["selectionSurface"] = "unsupported"
        dispatch["selector"] = {}
        receipt = self.make_receipt(dispatch)
        receipt["selectionSurface"] = "unsupported"
        receipt["appliedSelector"] = {}
        receipt["modelIdentityProof"]["selectionSurface"] = "unsupported"
        result = router.evaluate(adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "fallback_required")
        self.assertEqual(result["reason"], "model_route_unavailable")
        self.assertFalse(result["allowExternalHarnessOutput"])

    def test_unverifiable_actual_model_fails_closed_to_declared_fallback(self) -> None:
        _, dispatch, receipt = self.evaluate("fast")
        receipt["routeVerified"] = False
        receipt["modelIdentityProof"]["status"] = "unavailable"
        result = router.evaluate(self.adapter, dispatch, receipt)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["decision"], "fallback_required")
        self.assertEqual(result["reason"], "model_route_unavailable")
        self.assertFalse(result["allowExternalHarnessOutput"])
        self.assertEqual(result["fallbackRoute"], dispatch["fallback"]["routeId"])

    def test_requested_actual_model_mismatch_never_allows_external_output(self) -> None:
        _, dispatch, receipt = self.evaluate("balanced")
        receipt["actualModel"] = "unexpected-model"
        result = router.evaluate(self.adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "fallback_required")
        self.assertFalse(result["allowExternalHarnessOutput"])

    def test_explicit_route_cannot_silently_inherit_global_default(self) -> None:
        _, dispatch, receipt = self.evaluate("fast")
        receipt["globalDefaultInherited"] = True
        receipt["actualModel"] = self.adapter["globalDefaultModel"]
        result = router.evaluate(self.adapter, dispatch, receipt)
        self.assertEqual(result["reason"], "model_route_unavailable")
        self.assertFalse(result["allowExternalHarnessOutput"])
        self.assertTrue(any("global/default" in error for error in result["routeErrors"]))

    def test_missing_usage_elapsed_and_cost_are_unavailable_not_fabricated(self) -> None:
        _, dispatch, receipt = self.evaluate("fast")
        receipt["usage"] = {"status": "unavailable"}
        receipt["elapsed"] = {"status": "unavailable"}
        receipt["cost"] = {"status": "unavailable"}
        result = router.evaluate(self.adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "allow")

        receipt["cost"] = {"status": "unavailable", "amount": 0.0}
        result = router.evaluate(self.adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "block")
        self.assertTrue(any("unavailable fields" in error for error in result["errors"]))

    def test_exit_completion_and_stop_reason_must_all_prove_success(self) -> None:
        cases = (
            ({"processExitCode": 124, "cliExit": 124, "taskCompleted": False,
              "taskSuccess": False, "stopReason": "wall_timeout", "timedOut": True},
             "timed out"),
            ({"processExitCode": 125, "cliExit": 125, "taskCompleted": False,
              "taskSuccess": False, "stopReason": "max_turns_reached"},
             "stopReason"),
            ({"taskCompleted": False, "taskSuccess": False}, "complete the task"),
            ({"stopReason": "cancelled"}, "stopReason"),
        )
        for changes, expected in cases:
            with self.subTest(changes=changes):
                _, dispatch, receipt = self.evaluate("fast")
                receipt.update(changes)
                result = router.evaluate(self.adapter, dispatch, receipt)
                self.assertEqual(result["decision"], "fallback_required", result)
                self.assertEqual(result["reason"], "external_harness_execution_incomplete")
                self.assertFalse(result["allowExternalHarnessOutput"])
                self.assertTrue(any(expected in error for error in result["executionErrors"]))

    def test_process_exit_must_match_harness_cli_exit(self) -> None:
        _, dispatch, receipt = self.evaluate("fast")
        receipt["processExitCode"] = 143
        result = router.evaluate(self.adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "block")
        self.assertTrue(any("caller-observed" in error for error in result["errors"]))

    def test_tool_policy_violation_cannot_integrate_even_after_claimed_success(self) -> None:
        _, dispatch, receipt = self.evaluate("fast")
        receipt["toolPolicyCompliant"] = False
        result = router.evaluate(self.adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "fallback_required")
        self.assertFalse(result["allowExternalHarnessOutput"])
        self.assertTrue(any("tool policy" in error for error in result["executionErrors"]))

    def test_available_cost_requires_dated_source_backing(self) -> None:
        adapter = copy.deepcopy(self.adapter)
        adapter["pricing"] = {
            "status": "available",
            "sourceRef": "adapter-policy/pricing-source",
            "observedAt": "2026-08-14T00:00:00Z",
            "inputs": {"scheduleId": "dated-schedule-v1"},
        }
        dispatch = self.make_dispatch("fast")
        dispatch["adapterPolicyDigest"] = router.canonical_sha256(adapter)
        receipt = self.make_receipt(dispatch)
        receipt["cost"] = {
            "status": "available",
            "amount": 0.01,
            "currency": "USD",
            "priceSourceRef": adapter["pricing"]["sourceRef"],
            "priceObservedAt": adapter["pricing"]["observedAt"],
            "pricingPolicyDigest": router.canonical_sha256(adapter["pricing"]),
        }
        accepted = router.evaluate(adapter, dispatch, receipt)
        self.assertEqual(accepted["decision"], "allow", accepted)
        receipt["cost"]["priceSourceRef"] = ""
        receipt["cost"]["priceObservedAt"] = "2026-08-14 00:00:00"
        result = router.evaluate(adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "block")
        self.assertTrue(any("source-backed" in error for error in result["errors"]))
        self.assertTrue(any("strict RFC3339" in error for error in result["errors"]))

    def test_matching_fallback_receipt_is_typed_and_ceo_invariants_stay_fixed(self) -> None:
        _, dispatch, receipt = self.evaluate("fast")
        receipt["routeVerified"] = False
        receipt["fallbackReceipt"] = {
            "invoked": True,
            "reason": "model_route_unavailable",
            "routeId": dispatch["fallback"]["routeId"],
            "receiptId": "fallback-receipt-001",
            "owner": dispatch["fallback"]["owner"],
            "evidenceRef": "artifacts/fallback-review.json",
        }
        result = router.evaluate(self.adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "fallback")
        self.assertTrue(result["allowFallbackOutput"])
        self.assertFalse(result["allowExternalHarnessOutput"])
        self.assertEqual(result["fallbackReceipt"]["receiptId"], "fallback-receipt-001")
        self.assertEqual(receipt["ceoInvariantAfter"], dispatch["ceoInvariant"])

    def test_ceo_model_reasoning_or_permissions_change_blocks_every_output(self) -> None:
        _, dispatch, receipt = self.evaluate("fast")
        receipt["ceoInvariantAfter"]["model"] = "worker-requested-ceo-model"
        result = router.evaluate(self.adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "block")
        self.assertFalse(result["allowExternalHarnessOutput"])
        self.assertFalse(result["allowFallbackOutput"])

    def test_write_set_command_guard_and_review_are_mandatory(self) -> None:
        _, dispatch, receipt = self.evaluate("fast")
        receipt["changedPaths"].append("../outside.txt")
        receipt["commandsExecuted"].append("unapproved command")
        receipt["independentReview"]["status"] = "pending"
        result = router.evaluate(self.adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "block")
        joined = "\n".join(result["errors"])
        self.assertIn("exact write-set", joined)
        self.assertIn("command guard", joined)
        self.assertIn("independent Codex review", joined)

    def test_retry_defaults_to_zero_without_project_policy_authorization(self) -> None:
        dispatch = self.make_dispatch("fast")
        dispatch["retryCount"] = 1
        receipt = self.make_receipt(dispatch)
        result = router.evaluate(self.adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "block")
        self.assertTrue(any("retry exceeds" in error for error in result["errors"]))

    def test_bundled_templates_validate_without_provider_specific_assumptions(self) -> None:
        adapter = json.loads((TEMPLATES / "external-harness-adapter.json").read_text())
        dispatch = json.loads((TEMPLATES / "external-harness-dispatch.json").read_text())
        receipt = json.loads((TEMPLATES / "external-harness-receipt.json").read_text())
        self.assertEqual(dispatch["adapterPolicyDigest"], router.canonical_sha256(adapter))
        result = router.evaluate(adapter, dispatch, receipt)
        self.assertEqual(result["decision"], "allow", result)


if __name__ == "__main__":
    unittest.main()
