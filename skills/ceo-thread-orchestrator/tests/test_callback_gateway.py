from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "callback_gateway.py"


def load_module():
    spec = importlib.util.spec_from_file_location("callback_gateway", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gateway = load_module()


class CallbackGatewayTests(unittest.TestCase):
    def valid_callback(self) -> dict:
        value = json.loads((ROOT / "templates" / "compact_callback.json").read_text())
        value["declaredTokenEstimate"] = gateway.compact_token_estimate(value) + 20
        return value

    def routing_receipt(self, callback: dict) -> dict:
        receipt = {
            "schema": gateway.ROUTING_RECEIPT_SCHEMA,
            "source": callback["routingProofSource"],
            "taskId": callback["taskId"],
            "requestedModel": callback["requestedModel"],
            "requestedThinking": callback["requestedThinking"],
            "actualModel": callback["actualModel"],
            "actualThinking": callback["actualThinking"],
            "selectionSurface": "subagent",
        }
        receipt["receiptSha256"] = gateway.routing_receipt_sha256(receipt)
        callback["routingReceiptId"] = receipt["receiptSha256"]
        callback["declaredTokenEstimate"] = gateway.compact_token_estimate(callback) + 20
        return receipt

    def evidence_receipt(self, callback: dict) -> dict:
        receipt = {
            "schema": gateway.EVIDENCE_RECEIPT_SCHEMA,
            "taskId": callback["taskId"],
            "sliceId": callback["sliceId"],
            "sliceBasisSha256": callback["sliceBasisSha256"],
            "verificationProfile": callback["verificationProfile"],
            "changedPaths": callback["changedPaths"],
            "commands": callback["commands"],
            "evidenceRefs": callback["evidenceRefs"],
        }
        receipt["receiptSha256"] = gateway.evidence_receipt_sha256(receipt)
        callback["verificationEvidenceReceiptId"] = receipt["receiptSha256"]
        callback["declaredTokenEstimate"] = gateway.compact_token_estimate(callback) + 20
        return receipt

    def test_bundled_compact_callback_is_allowed(self) -> None:
        callback = self.valid_callback()
        callback["ceoVerificationCount"] = 1
        receipt = self.routing_receipt(callback)
        evidence = self.evidence_receipt(callback)
        result = gateway.validate(
            callback,
            trusted_routing_receipt=receipt,
            routing_proof_capability=gateway.ROUTING_PROOF_CAPABILITY,
            trusted_evidence_receipt=evidence,
            evidence_proof_capability=gateway.EVIDENCE_PROOF_CAPABILITY,
            expected_task_id=callback["taskId"],
            expected_slice_id=callback["sliceId"],
            expected_slice_basis_sha256=callback["sliceBasisSha256"],
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["allowCallbackInjection"])
        self.assertTrue(result["allowCandidateAcceptance"])
        self.assertTrue(result["modelRouteVerified"])

    def test_native_unknown_route_accepts_only_verified_evidence_and_nonexact_policy(self):
        callback = self.valid_callback()
        callback.update(actualModel="unknown", actualThinking="unknown",
                        routingResult="unknown", routingProofSource="unavailable",
                        routingReceiptId=None, ceoVerificationCount=1)
        evidence = self.evidence_receipt(callback)
        kwargs = dict(native_codex_review=True, exact_model_required=False,
                      trusted_evidence_receipt=evidence,
                      evidence_proof_capability=gateway.EVIDENCE_PROOF_CAPABILITY,
                      expected_task_id=callback["taskId"], expected_slice_id=callback["sliceId"],
                      expected_slice_basis_sha256=callback["sliceBasisSha256"])
        result = gateway.validate(callback, **kwargs)
        self.assertTrue(result["allowCandidateAcceptance"], result)
        self.assertFalse(result["modelRouteVerified"])
        self.assertFalse(gateway.validate(callback, **(kwargs | {"exact_model_required": True}))["allowCandidateAcceptance"])
        self.assertFalse(gateway.validate(callback, **(kwargs | {"trusted_evidence_receipt": None}))["allowCandidateAcceptance"])
        self.assertFalse(gateway.validate(callback, **(kwargs | {"native_codex_review": False}))["allowCandidateAcceptance"])

    def test_new_verified_evidence_allows_one_recheck_but_same_evidence_does_not(self):
        callback = self.valid_callback()
        callback["ceoVerificationCount"] = 1
        route = self.routing_receipt(callback)
        evidence = self.evidence_receipt(callback)
        kwargs = dict(trusted_routing_receipt=route, routing_proof_capability=gateway.ROUTING_PROOF_CAPABILITY,
                      trusted_evidence_receipt=evidence, evidence_proof_capability=gateway.EVIDENCE_PROOF_CAPABILITY,
                      expected_task_id=callback["taskId"], expected_slice_id=callback["sliceId"],
                      expected_slice_basis_sha256=callback["sliceBasisSha256"])
        first = gateway.validate(callback, **kwargs)
        callback.update(callbackSequence=2, priorCallbackSha256=first["sliceLedgerEntry"]["lastCallbackSha256"], ceoVerificationCount=2)
        kwargs["slice_ledger"] = {first["sliceLedgerKey"]: first["sliceLedgerEntry"]}
        callback["declaredTokenEstimate"] = gateway.compact_token_estimate(callback) + 20
        self.assertFalse(gateway.validate(callback, **kwargs)["allowCandidateAcceptance"])
        callback["evidenceRefs"] = ["artifacts/recheck.json#sha256=" + "a" * 64]
        kwargs["trusted_evidence_receipt"] = self.evidence_receipt(callback)
        self.assertTrue(gateway.validate(callback, **kwargs)["allowCandidateAcceptance"])

    def test_native_cli_checks_local_evidence_without_host(self):
        import hashlib
        callback = self.valid_callback()
        callback.update(actualModel="unknown", actualThinking="unknown", routingResult="unknown",
                        routingProofSource="unavailable", routingReceiptId=None, ceoVerificationCount=1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            refs = []
            for index, command in enumerate(callback["commands"]):
                command_receipt = {key: callback[key] for key in
                                   ("taskId", "sliceId", "sliceBasisSha256", "verificationProfile")}
                command_receipt.update(schema="ceo_verification_command_receipt_v1", command=command,
                                       exitCode=0, status="passed", summary="Focused tests passed")
                raw = json.dumps(command_receipt).encode()
                (root / f"test-{index}.json").write_bytes(raw)
                refs.append(f"test-{index}.json#sha256=" + hashlib.sha256(raw).hexdigest())
            callback["evidenceRefs"] = refs
            self.evidence_receipt(callback)
            callback_path = root / "callback.json"
            callback_path.write_text(json.dumps(callback))
            command = [sys.executable, str(SCRIPT), str(callback_path), "--native-review-workspace", tmp,
                       "--task-id", callback["taskId"], "--slice-id", callback["sliceId"],
                       "--slice-basis", callback["sliceBasisSha256"]]
            def run(extra=()):
                result = subprocess.run(command + list(extra), capture_output=True, text=True, check=True)
                return json.loads(result.stdout)
            self.assertTrue(run()["allowCandidateAcceptance"])
            self.assertFalse(run(["--exact-model-required"])["allowCandidateAcceptance"])
            (root / "test-0.json").write_text("{}")
            self.assertFalse(run()["allowCandidateAcceptance"])

    def test_unbound_or_forged_routing_digest_never_authorizes_acceptance(self) -> None:
        callback = self.valid_callback()
        callback["ceoVerificationCount"] = 1
        callback["routingReceiptId"] = "0" * 64
        unbound = gateway.validate(callback)
        self.assertTrue(unbound["allowCallbackInjection"], unbound)
        self.assertFalse(unbound["modelRouteVerified"])
        self.assertFalse(unbound["allowCandidateAcceptance"])

        receipt = self.routing_receipt(callback)
        receipt["actualModel"] = "different-model"
        forged = gateway.validate(
            callback,
            trusted_routing_receipt=receipt,
            routing_proof_capability=gateway.ROUTING_PROOF_CAPABILITY,
        )
        self.assertFalse(forged["modelRouteVerified"])
        self.assertIn("trusted_routing_receipt_mismatch", forged["acceptanceGaps"])

    def test_unknown_or_inherited_actual_model_cannot_be_claimed_as_verified(self) -> None:
        callback = self.valid_callback()
        callback.update(
            {
                "actualModel": "unknown",
                "actualThinking": "inherited",
                "routingResult": "unknown",
                "routingProofSource": "unavailable",
                "routingReceiptId": None,
            }
        )
        result = gateway.validate(callback)
        self.assertTrue(result["allowCallbackInjection"], result)
        self.assertFalse(result["modelRouteVerified"])
        self.assertFalse(result["allowCandidateAcceptance"])

        inherited = self.valid_callback()
        inherited.update(
            {
                "requestedModel": "inherit",
                "requestedThinking": "inherit",
                "actualModel": "inherited",
                "actualThinking": "inherited",
                "routingResult": "inherited",
                "routingProofSource": "unavailable",
                "routingReceiptId": None,
                "ceoVerificationCount": 1,
            }
        )
        inherited_result = gateway.validate(inherited)
        self.assertTrue(inherited_result["allowCallbackInjection"], inherited_result)
        self.assertFalse(inherited_result["modelRouteVerified"])
        self.assertFalse(inherited_result["allowCandidateAcceptance"])

        callback.update(
            {
                "actualModel": callback["requestedModel"],
                "actualThinking": callback["requestedThinking"],
                "routingResult": "verified",
            }
        )
        forged = gateway.validate(callback)
        self.assertFalse(forged["allowCallbackInjection"])
        self.assertTrue(any("content-addressed" in error for error in forged["errors"]))

    def test_risk_tier_and_review_budgets_control_acceptance_without_hiding_callback(self) -> None:
        callback = self.valid_callback()
        callback["riskTier"] = "high"
        callback["verificationProfile"] = "full"
        callback["neutralReviewCount"] = 0
        result = gateway.validate(callback)
        self.assertTrue(result["allowCallbackInjection"], result)
        self.assertFalse(result["allowCandidateAcceptance"])
        self.assertIn("high_risk_slice_requires_exactly_one_neutral_review", result["acceptanceGaps"])

        callback["neutralReviewCount"] = 2
        callback["revisionCount"] = 2
        callback["processUpdateCount"] = 4
        exhausted = gateway.validate(callback)
        self.assertTrue(exhausted["allowCallbackInjection"], exhausted)
        self.assertTrue(exhausted["sliceBudgetExhausted"])
        self.assertEqual(exhausted["nextAction"], "shrink_slice_or_change_approach")

    def test_acceptance_requires_real_evidence_and_ceo_verification(self) -> None:
        callback = self.valid_callback()
        receipt = self.routing_receipt(callback)
        callback["riskTier"] = "high"
        callback["verificationProfile"] = "full"
        callback["neutralReviewCount"] = 1
        callback["ceoVerificationCount"] = 0
        callback["commands"] = []
        callback["evidenceRefs"] = []
        result = gateway.validate(
            callback,
            trusted_routing_receipt=receipt,
            routing_proof_capability=gateway.ROUTING_PROOF_CAPABILITY,
        )
        self.assertFalse(result["allowCandidateAcceptance"])
        self.assertIn("slice_requires_exactly_one_ceo_verification", result["acceptanceGaps"])
        self.assertIn("slice_verification_commands_required", result["acceptanceGaps"])
        self.assertIn("slice_evidence_refs_required", result["acceptanceGaps"])

    def test_slice_ledger_prevents_counter_reset_or_chain_replay(self) -> None:
        first = self.valid_callback()
        first["ceoVerificationCount"] = 1
        first_receipt = self.routing_receipt(first)
        first_evidence = self.evidence_receipt(first)
        accepted = gateway.validate(
            first,
            trusted_routing_receipt=first_receipt,
            routing_proof_capability=gateway.ROUTING_PROOF_CAPABILITY,
            trusted_evidence_receipt=first_evidence,
            evidence_proof_capability=gateway.EVIDENCE_PROOF_CAPABILITY,
            expected_task_id=first["taskId"],
            expected_slice_id=first["sliceId"],
            expected_slice_basis_sha256=first["sliceBasisSha256"],
        )
        ledger = {accepted["sliceLedgerKey"]: accepted["sliceLedgerEntry"]}

        second = copy.deepcopy(first)
        second["callbackSequence"] = 2
        second["priorCallbackSha256"] = accepted["callbackSha256"]
        second["ceoVerificationCount"] = 0
        second["processUpdateCount"] = 0
        second_receipt = self.routing_receipt(second)
        second_evidence = self.evidence_receipt(second)
        reset = gateway.validate(
            second,
            trusted_routing_receipt=second_receipt,
            routing_proof_capability=gateway.ROUTING_PROOF_CAPABILITY,
            trusted_evidence_receipt=second_evidence,
            evidence_proof_capability=gateway.EVIDENCE_PROOF_CAPABILITY,
            slice_ledger=ledger,
            expected_task_id=first["taskId"],
            expected_slice_id=first["sliceId"],
            expected_slice_basis_sha256=first["sliceBasisSha256"],
        )
        self.assertFalse(reset["allowCandidateAcceptance"])
        self.assertIn("callback_slice_counts_regressed", reset["acceptanceGaps"])

    def test_registered_worker_task_id_prevents_ledger_alias_reset(self) -> None:
        callback = self.valid_callback()
        callback["ceoVerificationCount"] = 1
        route = self.routing_receipt(callback)
        evidence = self.evidence_receipt(callback)
        result = gateway.validate(
            callback,
            trusted_routing_receipt=route,
            routing_proof_capability=gateway.ROUTING_PROOF_CAPABILITY,
            trusted_evidence_receipt=evidence,
            evidence_proof_capability=gateway.EVIDENCE_PROOF_CAPABILITY,
            expected_task_id="registered-worker",
            expected_slice_id=callback["sliceId"],
            expected_slice_basis_sha256=callback["sliceBasisSha256"],
        )
        self.assertFalse(result["allowCallbackInjection"])
        self.assertTrue(any("registered worker" in error for error in result["errors"]))

    def test_full_design_or_log_fields_are_rejected(self) -> None:
        for field in ("fullDesign", "fullReport", "completeLog", "rawChat"):
            callback = self.valid_callback()
            callback[field] = "long body"
            result = gateway.validate(callback)
            self.assertFalse(result["allowCallbackInjection"])

    def test_large_summary_must_move_to_artifact(self) -> None:
        callback = self.valid_callback()
        callback["summary"] = "x" * 3000
        callback["declaredTokenEstimate"] = 1500
        result = gateway.validate(callback)
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "callback_payload_exceeded")
        self.assertEqual(result["nextAction"], "store_full_detail_as_artifact_then_emit_compact_callback")

    def test_understated_token_estimate_is_rejected(self) -> None:
        callback = self.valid_callback()
        callback["declaredTokenEstimate"] = 1
        result = gateway.validate(callback)
        self.assertFalse(result["ok"])
        self.assertTrue(any("understates" in error for error in result["errors"]))

    def test_forbidden_payload_and_unsafe_paths_are_rejected(self) -> None:
        callback = self.valid_callback()
        callback["summary"] = "data:image/png;base64,AAAA"
        callback["changedPaths"] = ["../outside.txt"]
        result = gateway.validate(callback)
        self.assertFalse(result["allowCallbackInjection"])
        self.assertTrue(any("forbidden" in error for error in result["errors"]))
        self.assertTrue(any("project-relative" in error for error in result["errors"]))

    def test_artifact_reference_requires_sha256(self) -> None:
        callback = self.valid_callback()
        callback.pop("artifactSha256")
        result = gateway.validate(callback)
        self.assertFalse(result["ok"])
        self.assertTrue(any("requires artifactSha256" in error for error in result["errors"]))

    def test_cli_rejects_oversized_input_before_json_parse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "callback.json"
            path.write_text("{" + "x" * (gateway.MAX_CALLBACK_SERIALIZED_BYTES + 1), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2)
            result = json.loads(completed.stdout)
            self.assertEqual(result["reason"], "callback_payload_exceeded")


if __name__ == "__main__":
    unittest.main()
