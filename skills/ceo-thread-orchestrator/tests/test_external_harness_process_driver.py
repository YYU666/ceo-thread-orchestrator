#!/usr/bin/env python3
"""Process-level tests for the bounded external Harness driver."""

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
SCRIPT = ROOT / "scripts" / "execute_external_harness.py"
SPEC = importlib.util.spec_from_file_location("execute_external_harness", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)
router = driver.router


class ExternalHarnessProcessDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name).resolve()
        self.source = root / "source"
        self.workspace = root / "worktree"
        self.source.mkdir()
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.name", "fixture"], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.email", "fixture@example.invalid"], check=True)
        (self.source / "README.md").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.source), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(self.source), "commit", "-qm", "fixture"], check=True)
        subprocess.run(
            ["git", "-C", str(self.source), "worktree", "add", "--detach", "-q", str(self.workspace)],
            check=True,
        )
        self.adapter = {
            "schema": "external_harness_adapter_v1",
            "adapterPolicyId": "fixture-policy",
            "mappingSource": "fixture",
            "globalDefaultModel": "global-default",
            "routes": {
                capability: {
                    "selectionSurface": "cli_profile",
                    "selector": {"profile": f"{capability}-profile", "patch": f"{capability}.patch.yml"},
                    "model": f"fixture-{capability}-model",
                    "reasoning": "high" if capability == "frontier" else "medium",
                    "directModelOverride": False,
                    "identityProofMethods": ["cli_dispatch_receipt"],
                }
                for capability in ("fast", "balanced", "frontier")
            },
            "retryPolicy": {"defaultRetries": 0, "authorizedMaxRetries": 0},
            "pricing": {"status": "unavailable"},
        }
        route = self.adapter["routes"]["fast"]
        self.dispatch = {
            "schema": "external_harness_dispatch_v1",
            "dispatchId": "dispatch-fast",
            "adapterPolicyId": self.adapter["adapterPolicyId"],
            "adapterPolicyDigest": router.canonical_sha256(self.adapter),
            "requestedCapabilityClass": "fast",
            "requestedModel": route["model"],
            "requestedReasoning": route["reasoning"],
            "selectionSurface": route["selectionSurface"],
            "selector": copy.deepcopy(route["selector"]),
            "explicitRoute": True,
            "allowGlobalDefaultInheritance": False,
            "retryCount": 0,
            "guard": {
                "allowedTools": ["read", "edit"],
                "exactWriteSet": ["src/example.py"],
                "allowedCommands": ["python -m unittest"],
                "isolatedWorkspace": True,
                "independentCodexReviewRequired": True,
            },
            "fallback": {"declared": True, "routeId": "codex-fallback", "owner": "ceo"},
            "ceoInvariant": {"model": "ceo", "reasoning": "high", "permissionsDigest": "opaque"},
        }

    def tearDown(self) -> None:
        subprocess.run(
            ["git", "-C", str(self.source), "worktree", "remove", "--force", str(self.workspace)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.temp.cleanup()

    def receipt(self, **changes: object) -> dict:
        route = self.adapter["routes"]["fast"]
        value = {
            "schema": "dsh_headless_result_v1",
            "taskCompleted": True,
            "stopReason": "completed",
            "cliExit": 0,
            "requestedProvider": "fixture-provider",
            "actualProvider": "fixture-provider",
            "requestedModel": route["model"],
            "actualModel": route["model"],
            "requestedReasoning": route["reasoning"],
            "actualReasoning": route["reasoning"],
            "modelIdentityProof": {
                "status": "verified",
                "method": "durable_assistant_message",
                "provider": "fixture-provider",
                "model": route["model"],
            },
            "turns": 1,
            "modelCalls": 1,
            "timedOut": False,
            "usage": {"status": "unavailable"},
            "elapsedMilliseconds": 10,
            "changedPaths": [],
            "commandsExecuted": ["python -m unittest"],
            "toolPolicyCompliant": True,
            "finalText": "candidate",
        }
        value.update(changes)
        return value

    def request(self, receipt: dict, process_exit: int | None = None) -> dict:
        route = self.adapter["routes"]["fast"]
        exit_code = receipt["cliExit"] if process_exit is None else process_exit
        code = f"import json,sys; print(json.dumps({receipt!r})); sys.exit({exit_code})"
        return {
            "schema": "external_harness_process_request_v1",
            "workspace": str(self.workspace),
            "canonicalSourceRoot": str(self.source),
            "isolatedWorkspace": True,
            "argv": [
                sys.executable, "-c", code,
                "--profile", route["selector"]["profile"],
                "--patch", route["selector"]["patch"],
                "--reasoning-policy", route["reasoning"],
                "--json",
                "--max-turns", "8",
                "--timeout", "300",
                "--tool-timeout", "60",
                "--allowed-tools", "read,edit",
                "--write-set", "src/example.py",
                "--allowed-command", "python -m unittest",
            ],
            "internalBudget": {
                "maxTurns": 8,
                "wallTimeoutSeconds": 300,
                "toolTimeoutSeconds": 60,
            },
            "outerTimeoutSeconds": 310,
            "terminationGraceSeconds": 1,
        }

    def test_successful_process_still_requires_independent_codex_review(self) -> None:
        result = driver.execute(self.adapter, self.dispatch, self.request(self.receipt()))
        self.assertEqual(result["decision"], "candidate_review_required", result)
        self.assertFalse(result["allowIntegration"])

    def test_provider_default_reasoning_uses_verified_policy_not_fake_effort(self) -> None:
        route = self.adapter["routes"]["fast"]
        route["reasoning"] = "provider_default"
        self.dispatch["requestedReasoning"] = "provider_default"
        self.dispatch["adapterPolicyDigest"] = router.canonical_sha256(self.adapter)
        proof = {
            "status": "verified",
            "method": "request_header_reasoning_effort_omitted",
            "requestedReasoning": "provider_default",
            "defaultPolicyApplied": True,
            "concreteEffortKnown": False,
        }
        receipt = self.receipt(
            requestedReasoning="provider_default",
            actualReasoning="unavailable",
            reasoningPolicyProof=proof,
        )
        result = driver.execute(self.adapter, self.dispatch, self.request(receipt))
        self.assertEqual(result["decision"], "candidate_review_required", result)

        concrete = self.receipt(
            requestedReasoning="provider_default",
            actualReasoning="high",
            reasoningPolicyProof={
                "status": "verified",
                "method": "request_header_adapter_default_reasoning_effort",
                "requestedReasoning": "provider_default",
                "defaultPolicyApplied": True,
                "concreteEffortKnown": True,
                "adapterDefaultField": "reasoningEffort",
                "actualReasoning": "high",
            },
        )
        concrete_result = driver.execute(
            self.adapter, self.dispatch, self.request(concrete)
        )
        self.assertEqual(concrete_result["decision"], "candidate_review_required", concrete_result)
        self.assertFalse(concrete_result["allowIntegration"])

        unmarked = self.receipt(
            requestedReasoning="provider_default",
            actualReasoning="high",
            reasoningPolicyProof={
                "status": "verified",
                "method": "request_header_adapter_default_reasoning_effort",
                "requestedReasoning": "provider_default",
                "defaultPolicyApplied": True,
                "concreteEffortKnown": True,
                "actualReasoning": "high",
            },
        )
        unmarked_result = driver.execute(
            self.adapter, self.dispatch, self.request(unmarked)
        )
        self.assertEqual(unmarked_result["reason"], "model_route_unavailable", unmarked_result)
        self.assertFalse(unmarked_result["allowIntegration"])

        for invalid_proof in (
            None,
            {**proof, "defaultPolicyApplied": False},
            {**proof, "concreteEffortKnown": True},
            {**proof, "method": "untrusted_default_claim"},
        ):
            with self.subTest(invalid_proof=invalid_proof):
                bad = self.receipt(
                    requestedReasoning="provider_default",
                    actualReasoning="unavailable",
                    reasoningPolicyProof=invalid_proof,
                )
                blocked = driver.execute(self.adapter, self.dispatch, self.request(bad))
                self.assertEqual(blocked["reason"], "model_route_unavailable", blocked)
                self.assertFalse(blocked["allowIntegration"])

    def test_exit_zero_with_incomplete_task_routes_to_fallback(self) -> None:
        receipt = self.receipt(taskCompleted=False, stopReason="max_turns_reached", cliExit=125)
        result = driver.execute(self.adapter, self.dispatch, self.request(receipt))
        self.assertEqual(result["reason"], "external_harness_execution_incomplete", result)
        self.assertFalse(result["allowIntegration"])

    def test_requested_actual_model_mismatch_is_model_route_unavailable(self) -> None:
        receipt = self.receipt(actualModel="global-default")
        result = driver.execute(self.adapter, self.dispatch, self.request(receipt))
        self.assertEqual(result["reason"], "model_route_unavailable", result)
        self.assertFalse(result["allowIntegration"])

    def test_caller_exit_must_match_harness_cli_exit(self) -> None:
        result = driver.execute(self.adapter, self.dispatch, self.request(self.receipt(), process_exit=1))
        self.assertEqual(result["decision"], "block", result)
        self.assertTrue(any("caller-observed" in error for error in result["errors"]))

    def test_stop_reason_exit_and_usage_must_be_semantically_consistent(self) -> None:
        receipt = self.receipt(taskCompleted=False, stopReason="max_turns_reached", cliExit=0)
        result = driver.execute(self.adapter, self.dispatch, self.request(receipt))
        self.assertEqual(result["decision"], "block", result)
        self.assertTrue(any("stopReason" in error for error in result["errors"]))

        receipt = self.receipt(usage={"status": "unavailable", "inputTokens": 0})
        result = driver.execute(self.adapter, self.dispatch, self.request(receipt))
        self.assertEqual(result["decision"], "block", result)
        self.assertTrue(any("fabricated" in error for error in result["errors"]))

    def test_supervisor_timeout_uses_sigterm_receipt_and_never_integrates(self) -> None:
        receipt = self.receipt(
            taskCompleted=False,
            stopReason="sigterm",
            cliExit=143,
            turns=1,
            modelCalls=1,
        )
        route = self.adapter["routes"]["fast"]
        code = (
            "import json,os,signal,time; "
            f"r={receipt!r}; "
            "signal.signal(signal.SIGTERM, lambda *_: (print(json.dumps(r), flush=True), os._exit(143))); "
            "time.sleep(10)"
        )
        request = self.request(receipt)
        request["argv"] = [
            sys.executable, "-c", code,
            "--profile", route["selector"]["profile"],
            "--patch", route["selector"]["patch"],
            "--reasoning-policy", route["reasoning"],
            "--json", "--max-turns", "8", "--timeout", "300", "--tool-timeout", "60",
            "--allowed-tools", "read,edit",
            "--write-set", "src/example.py",
            "--allowed-command", "python -m unittest",
        ]
        request["outerTimeoutSeconds"] = 1.1
        request["internalBudget"]["wallTimeoutSeconds"] = 1
        request["internalBudget"]["toolTimeoutSeconds"] = 1
        request["argv"][request["argv"].index("300")] = "1"
        request["argv"][request["argv"].index("60")] = "1"
        result = driver.execute(self.adapter, self.dispatch, request)
        self.assertEqual(result["reason"], "external_harness_execution_incomplete", result)
        self.assertTrue(result["execution"]["supervisorTimedOut"])
        self.assertFalse(result["execution"]["forcedKill"])

    def test_write_set_escape_blocks_candidate(self) -> None:
        receipt = self.receipt(changedPaths=["../outside.py"])
        result = driver.execute(self.adapter, self.dispatch, self.request(receipt))
        self.assertEqual(result["decision"], "block", result)
        self.assertTrue(any("write-set" in error for error in result["errors"]))

    def test_guard_mismatch_fails_before_process_start(self) -> None:
        marker = self.workspace / "started"
        request = self.request(self.receipt())
        request["argv"][2] = f"from pathlib import Path; Path({str(marker)!r}).write_text('started')"
        request["argv"].remove("read,edit")
        request["argv"].append("read")
        result = driver.execute(self.adapter, self.dispatch, request)
        self.assertEqual(result["reason"], "model_route_unavailable", result)
        self.assertFalse(marker.exists())

    def test_duplicate_or_mismatched_internal_budget_fails_before_process_start(self) -> None:
        marker = self.workspace / "started"
        request = self.request(self.receipt())
        request["argv"][2] = f"from pathlib import Path; Path({str(marker)!r}).write_text('started')"
        request["argv"].extend(["--max-turns", "99"])
        result = driver.execute(self.adapter, self.dispatch, request)
        self.assertEqual(result["reason"], "model_route_unavailable", result)
        self.assertFalse(marker.exists())

    def test_reasoning_policy_must_match_route_before_process_start(self) -> None:
        for mutation in ("missing", "mismatch", "duplicate"):
            with self.subTest(mutation=mutation):
                marker = self.workspace / f"started-{mutation}"
                request = self.request(self.receipt())
                request["argv"][2] = (
                    f"from pathlib import Path; Path({str(marker)!r}).write_text('started')"
                )
                index = request["argv"].index("--reasoning-policy")
                if mutation == "missing":
                    del request["argv"][index:index + 2]
                elif mutation == "mismatch":
                    request["argv"][index + 1] = "high"
                else:
                    request["argv"].extend(["--reasoning-policy", "provider_default"])
                result = driver.execute(self.adapter, self.dispatch, request)
                self.assertEqual(result["reason"], "model_route_unavailable", result)
                self.assertFalse(marker.exists())

    def test_non_worktree_or_dirty_worktree_fails_before_process_start(self) -> None:
        request = self.request(self.receipt())
        (self.workspace / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        result = driver.execute(self.adapter, self.dispatch, request)
        self.assertEqual(result["reason"], "model_route_unavailable", result)
        self.assertTrue(any("clean" in error for error in result["errors"]))

    def test_observed_worktree_diff_must_match_receipt_and_write_set(self) -> None:
        receipt = self.receipt(changedPaths=["outside.py"])
        request = self.request(receipt)
        request["argv"][2] = (
            "from pathlib import Path; import json,sys; "
            "Path('outside.py').write_text('x'); "
            f"print(json.dumps({receipt!r})); sys.exit(0)"
        )
        result = driver.execute(self.adapter, self.dispatch, request)
        self.assertEqual(result["decision"], "block", result)
        self.assertTrue(any("observed worktree diff" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
