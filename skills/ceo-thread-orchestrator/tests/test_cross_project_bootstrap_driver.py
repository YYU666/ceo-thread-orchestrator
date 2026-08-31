#!/usr/bin/env python3
from __future__ import annotations

import sys
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import cross_project_bootstrap_driver as driver  # noqa: E402


def projects() -> list[dict[str, object]]:
    return [
        {"projectKey": "alpha", "workspace": "/projects/Alpha"},
        {"projectKey": "beta", "workspace": "/projects/Beta"},
    ]


def packet(workspace: str, project_id: str, generation: str) -> dict[str, object]:
    return {
        "workspace": workspace,
        "projectId": project_id,
        "contextGenerationId": generation,
        "tokenEstimate": 1000,
        "memoryMode": "app_owned_memory_core",
        "authorityVerification": "app_owned_verified",
        "current": True,
        "recoveryReady": True,
        "returnedCount": 4,
        "takeover": {"shouldInject": True},
        "head": f"head-{project_id}",
        "scanHash": f"scan-{project_id}",
        "projectIdentitySha256": f"identity-{project_id}",
        "verifiedMemoryStateHash": f"checkpoint-{project_id}",
        "sourceRefs": [{"path": f"{workspace}/docs/goal.md", "projectId": project_id}],
    }


class FakeRuntime:
    def __init__(
        self,
        stale: set[str] | None = None,
        invalid_prepare: set[str] | None = None,
        verify_mismatch: set[str] | None = None,
        helper_verify: set[str] | None = None,
    ) -> None:
        self.stale = stale or set()
        self.invalid_prepare = invalid_prepare or set()
        self.verify_mismatch = verify_mismatch or set()
        self.helper_verify = helper_verify or set()
        self.calls: list[dict[str, object]] = []

    def __call__(self, request: dict[str, object]) -> dict[str, object]:
        self.calls.append(request)
        workspace = str(request["workspace"])
        if request["operation"] == "verify":
            if workspace in self.stale:
                return {
                    "memoryMode": "fallback_stale",
                    "authorityVerification": "unavailable",
                    "current": False,
                    "recoveryReady": False,
                }
            return {
                "operation": "not_verify" if workspace in self.helper_verify else "verify",
                "memoryMode": "helper_only" if workspace in self.helper_verify else "app_owned_memory_core",
                "authorityVerification": "helper_verified"
                if workspace in self.helper_verify
                else "app_owned_verified",
                "current": True,
                "recoveryReady": True,
                "projectIdentity": {
                    "projectId": "project-alpha" if workspace.endswith("Alpha") else "project-beta",
                    "projectIdentitySha256": "identity-project-alpha" if workspace.endswith("Alpha") else "identity-project-beta",
                    "canonicalRoot": "/projects/WRONG" if workspace in self.verify_mismatch else workspace,
                },
                "scanBinding": {
                    "matched": True,
                    "authorizedCheckpointId": "checkpoint-project-alpha"
                    if workspace.endswith("Alpha")
                    else "checkpoint-project-beta",
                },
            }
        if workspace in self.invalid_prepare:
            return {
                "workspace": workspace,
                "memoryMode": "fallback_stale",
                "authorityVerification": "unavailable",
                "current": False,
                "recoveryReady": False,
                "returnedCount": 0,
                "takeover": {"shouldInject": False},
                "tokenEstimate": 100,
            }
        key = "alpha" if workspace.endswith("Alpha") else "beta"
        return packet(workspace, f"project-{key}", "same-generation")


class DeepRuntime(FakeRuntime):
    def __call__(self, request: dict[str, object]) -> dict[str, object]:
        if request["operation"] == "verify":
            return super().__call__(request)
        nested: dict[str, object] = {}
        cursor = nested
        for _ in range(2000):
            child: dict[str, object] = {}
            cursor["next"] = child
            cursor = child
        return nested


class CrossProjectBootstrapDriverTest(unittest.TestCase):
    def event(self) -> dict[str, object]:
        return {
            "taskId": "neutral-audit",
            "projectId": None,
            "artifactRoot": "/neutral/artifacts",
            "projectWorkspaces": projects(),
            "taskGoal": "audit Alpha then Beta",
            "inputTokens": 100,
        }

    def test_deep_runtime_packet_blocks_without_recursion_error(self) -> None:
        result = driver.run(self.event(), {}, DeepRuntime())
        self.assertEqual(result["decision"], "block")
        self.assertFalse(result["programGoalBlocked"])

    def test_lazy_driver_bootstraps_one_root_per_call_in_order(self) -> None:
        runtime = FakeRuntime()
        first = driver.run(self.event(), {}, runtime)
        self.assertEqual(first["decision"], "allow")
        self.assertEqual(first["activeProjectKey"], "alpha")
        self.assertEqual([call["workspace"] for call in runtime.calls], ["/projects/Alpha", "/projects/Alpha"])
        self.assertFalse(first["combinedProjectPacket"])
        self.assertNotIn("_driverCapability", json.dumps(first["takeoverPacket"]))

        runtime.calls.clear()
        second = driver.run(self.event(), first["governorState"], runtime)
        self.assertEqual(second["decision"], "allow")
        self.assertEqual(second["activeProjectKey"], "beta")
        self.assertEqual([call["workspace"] for call in runtime.calls], ["/projects/Beta", "/projects/Beta"])
        ledgers = second["governorState"]["projectInjectionLedger"]["neutral-audit"]
        self.assertEqual(ledgers["alpha"]["injectedGenerationIds"], ["same-generation"])
        self.assertEqual(ledgers["beta"]["injectedGenerationIds"], ["same-generation"])

    def test_stale_first_root_is_local_and_next_call_advances(self) -> None:
        runtime = FakeRuntime(stale={"/projects/Alpha"})
        first = driver.run(self.event(), {}, runtime)
        self.assertEqual(first["decision"], "block")
        self.assertFalse(first["programGoalBlocked"])
        self.assertTrue(first["unrelatedProjectsMayContinue"])
        self.assertEqual(len(runtime.calls), 1)

        runtime.calls.clear()
        second = driver.run(self.event(), first["governorState"], runtime)
        self.assertEqual(second["decision"], "allow")
        self.assertEqual(second["activeProjectKey"], "beta")
        self.assertEqual([call["workspace"] for call in runtime.calls], ["/projects/Beta", "/projects/Beta"])

    def test_prepare_budget_is_preferred_2200_with_hard_ceiling_10000(self) -> None:
        runtime = FakeRuntime()
        driver.run(self.event(), {}, runtime)
        prepare = runtime.calls[1]
        self.assertEqual(prepare["tokenBudget"], 2200)
        self.assertEqual(prepare["maxTokenBudget"], 10000)

    def test_internal_runtime_steps_do_not_count_as_host_model_input(self) -> None:
        runtime = FakeRuntime()
        result = driver.run(self.event(), {}, runtime)
        task_runtime = result["governorState"]["taskRuntimeLedger"]["neutral-audit"]
        self.assertEqual(task_runtime["cumulativeInputTokens"], 0)

    def test_invalid_prepare_packet_pauses_only_that_project_and_advances(self) -> None:
        runtime = FakeRuntime(invalid_prepare={"/projects/Alpha"})
        first = driver.run(self.event(), {}, runtime)
        self.assertEqual(first["decision"], "block")
        self.assertFalse(first["programGoalBlocked"])
        self.assertTrue(first["unrelatedProjectsMayContinue"])
        alpha = first["governorState"]["projectInjectionLedger"]["neutral-audit"]["alpha"]
        self.assertEqual(alpha["bootstrapStatus"], "stale")

        runtime.calls.clear()
        second = driver.run(self.event(), first["governorState"], runtime)
        self.assertEqual(second["decision"], "allow")
        self.assertEqual(second["activeProjectKey"], "beta")

    def test_verify_workspace_mismatch_never_prepares_or_marks_ready(self) -> None:
        runtime = FakeRuntime(verify_mismatch={"/projects/Alpha"})
        result = driver.run(self.event(), {}, runtime)
        self.assertEqual(result["reason"], "verify_workspace_mismatch")
        self.assertEqual(len(runtime.calls), 1)
        ledger = result["governorState"]["projectInjectionLedger"]["neutral-audit"]["alpha"]
        self.assertEqual(ledger["bootstrapStatus"], "stale")

    def test_artifact_root_is_never_used_as_runtime_workspace(self) -> None:
        runtime = FakeRuntime()
        driver.run(self.event(), {}, runtime)
        self.assertNotIn("/neutral/artifacts", [call["workspace"] for call in runtime.calls])

    def test_helper_or_wrong_operation_verify_never_prepares_or_marks_ready(self) -> None:
        runtime = FakeRuntime(helper_verify={"/projects/Alpha"})
        result = driver.run(self.event(), {}, runtime)
        self.assertIn(result["reason"], {"verify_operation_mismatch", "verify_memory_mode_not_app_owned"})
        self.assertEqual(len(runtime.calls), 1)
        ledger = result["governorState"]["projectInjectionLedger"]["neutral-audit"]["alpha"]
        self.assertEqual(ledger["bootstrapStatus"], "stale")

    def test_cli_tampered_state_blocks_before_runtime_or_any_call_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_path = root / "event.json"
            state_path = root / "state.json"
            event_path.write_text(json.dumps(self.event()), encoding="utf-8")
            driver.atomic_state.atomic_write_json(state_path, {})
            state_path.write_text(json.dumps({"allowProviderCalls": True}), encoding="utf-8")
            state_path.chmod(0o600)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "cross_project_bootstrap_driver.py"),
                    str(event_path),
                    "--state",
                    str(state_path),
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
