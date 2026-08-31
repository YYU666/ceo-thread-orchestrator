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

import host_control_adapter as adapter  # noqa: E402


def control(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "decision": "block",
        "lifecycleState": "lane_paused_recoverable",
        "allowOldThreadExecution": False,
        "allowToolCalls": False,
        "allowProjectToolCalls": False,
        "allowProviderCalls": False,
        "allowRecoveryControlTools": True,
        "recoveryControlToolAllowlist": ["refresh_binding_driver"],
        "unbindHarvestDriver": False,
        "programGoalBlocked": False,
        "unrelatedLanesMayContinue": True,
        "currentTaskId": "lane-a",
        "frozenTaskId": None,
        "rebindHarvestDriverToTaskId": None,
    }
    value.update(changes)
    return value


class HostControlAdapterTest(unittest.TestCase):
    def test_recovery_control_opens_only_exact_allowlisted_tool(self) -> None:
        result = adapter.adapt(control())
        self.assertTrue(result["ok"])
        self.assertEqual(result["actions"]["recoveryTools"], ["refresh_binding_driver"])
        self.assertEqual(result["actions"]["projectTools"], "deny")
        self.assertEqual(result["actions"]["providerCalls"], "deny")

    def test_verified_replacement_maps_context_replace_and_goal_clear(self) -> None:
        result = adapter.adapt(
            control(
                decision="allow",
                lifecycleState="active",
                allowOldThreadExecution=True,
                allowToolCalls=True,
                allowProjectToolCalls=True,
                allowProviderCalls=True,
                allowRecoveryControlTools=False,
                recoveryControlToolAllowlist=[],
                resumeProgramGoal=True,
                clearHistoricalGoalBlocked=True,
                contextInjectionMode="replace_long_thread_context",
                currentTaskId="clean-ceo",
                frozenTaskId="old-ceo",
                rebindHarvestDriverToTaskId="clean-ceo",
                unbindHarvestDriver=True,
            )
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["actions"]["context"], "replace")
        self.assertEqual(result["actions"]["programGoal"], "clear_and_resume")
        self.assertEqual(result["actions"]["currentTask"], {"taskId": "clean-ceo", "execution": "allow"})
        self.assertEqual(result["actions"]["frozenTask"], {"taskId": "old-ceo", "execution": "deny"})
        self.assertEqual(
            result["actions"]["harvestDriver"],
            {"action": "rebind", "fromTaskId": "old-ceo", "toTaskId": "clean-ceo"},
        )

    def test_frozen_task_requires_exact_target_and_unbind(self) -> None:
        accepted = adapter.adapt(
            control(
                decision="freeze",
                lifecycleState="task_context_frozen_replace_required",
                allowRecoveryControlTools=False,
                recoveryControlToolAllowlist=[],
                unbindHarvestDriver=True,
                currentTaskId="old-ceo",
                frozenTaskId="old-ceo",
            )
        )
        self.assertTrue(accepted["ok"], accepted)
        self.assertEqual(accepted["actions"]["currentTask"]["execution"], "deny")
        self.assertEqual(accepted["actions"]["frozenTask"]["taskId"], "old-ceo")

        missing_target = adapter.adapt(
            control(
                decision="freeze",
                lifecycleState="task_context_frozen_replace_required",
                allowRecoveryControlTools=False,
                recoveryControlToolAllowlist=[],
                unbindHarvestDriver=True,
                frozenTaskId=None,
            )
        )
        self.assertFalse(missing_target["ok"])

    def test_unknown_controls_and_non_boolean_values_fail_closed(self) -> None:
        for value in (
            control(allowProviderCalls="false"),
            control(allowMysteryCalls=True),
            control(frozenTaskOverride="old-ceo"),
            control(recoveryControlToolAllowlist=["unknown_tool"]),
            control(allowProjectToolCalls=True),
            control(
                decision="allow",
                lifecycleState="active",
                allowProviderCalls=True,
                allowRecoveryControlTools=False,
                recoveryControlToolAllowlist=[],
            ),
        ):
            with self.subTest(value=value):
                result = adapter.adapt(value)
                self.assertFalse(result["ok"])
                self.assertEqual(result["actions"]["providerCalls"], "deny")
                self.assertEqual(result["actions"]["projectTools"], "deny")

    def test_unknown_lifecycle_and_context_mode_fail_closed(self) -> None:
        for value in (
            control(lifecycleState="future_state"),
            control(contextInjectionMode="append_to_old_thread"),
        ):
            result = adapter.adapt(value)
            self.assertFalse(result["ok"])
            self.assertEqual(result["actions"]["currentTask"]["execution"], "deny")

    def test_cli_rejects_tampered_governor_controls_before_host_allow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "governor-result.json"
            adapter.context_governor.atomic_state.atomic_write_json(
                path,
                control(
                    decision="allow",
                    lifecycleState="active",
                    allowOldThreadExecution=True,
                    allowToolCalls=True,
                    allowProjectToolCalls=True,
                    allowProviderCalls=True,
                    allowRecoveryControlTools=False,
                    recoveryControlToolAllowlist=[],
                ),
            )
            path.write_text(json.dumps(control(allowProviderCalls=True)), encoding="utf-8")
            path.chmod(0o600)
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "host_control_adapter.py"), str(path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 2)
            result = json.loads(completed.stdout)
            self.assertFalse(result["ok"])
            self.assertEqual(result["actions"]["providerCalls"], "deny")
            self.assertEqual(result["actions"]["projectTools"], "deny")
            self.assertEqual(result["actions"]["currentTask"]["execution"], "deny")


if __name__ == "__main__":
    unittest.main()
