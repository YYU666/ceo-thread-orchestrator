from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import atomic_state  # noqa: E402
import context_governor  # noqa: E402
import current_source_work_driver as driver  # noqa: E402


class CurrentSourceWorkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "source.py").write_text("value = 1\n", encoding="utf-8")
        self.state = self.root / "governor.json"
        self.request = {
            "taskId": "ceo-1", "workspace": str(self.root), "scopeId": "scope-1",
            "taskGoal": "Fix current source", "sourceRefs": [{
                "path": "source.py",
                "sha256": hashlib.sha256((self.root / "source.py").read_bytes()).hexdigest(),
            }], "allowedWritePaths": ["source.py"],
        }

    def test_stale_memory_does_not_ban_scoped_source_work(self) -> None:
        result = driver.run(self.request, self.state)
        self.assertTrue(result["allowScopedSourceWork"])
        self.assertTrue(result["statePersisted"])
        for gate in ("allowMemoryInjection", "allowProjectToolCalls", "allowProviderCalls"):
            self.assertFalse(result[gate])
        self.assertEqual(driver.run(self.request, self.state)["decision"], "allow")

    def test_source_change_and_scope_reuse_fail_closed(self) -> None:
        self.assertTrue(driver.run(self.request, self.state)["allowScopedSourceWork"])
        changed = dict(self.request, taskGoal="Different goal")
        self.assertEqual(driver.run(changed, self.state)["reason"], "current_source_scope_changed_or_full")
        (self.root / "source.py").write_text("value = 2\n", encoding="utf-8")
        self.assertEqual(driver.run(self.request, self.state)["reason"], "source_work_anchor_changed")

    def test_symlink_write_path_is_rejected(self) -> None:
        (self.root / "alias.py").symlink_to(self.root / "source.py")
        self.request["allowedWritePaths"] = ["alias.py"]
        self.assertEqual(driver.run(self.request, self.state)["reason"], "source_path_symlink")

    def test_frozen_task_and_global_block_remain_closed(self) -> None:
        self.assertTrue(driver.run(self.request, self.state)["allowScopedSourceWork"])
        state = atomic_state.read_confirmed_json(self.state)
        state["frozenTaskKeys"] = ["ceo-1"]
        atomic_state.atomic_write_json(self.state, state)
        self.assertFalse(driver.run(self.request, self.state)["allowScopedSourceWork"])
        state = atomic_state.read_confirmed_json(self.state)
        state["frozenTaskKeys"] = []
        state["programGlobalBlock"] = {"active": True}
        atomic_state.atomic_write_json(self.state, state)
        self.assertFalse(driver.run(self.request, self.state)["allowScopedSourceWork"])

    def test_unconfirmed_state_and_persist_failure_cannot_allow(self) -> None:
        self.assertTrue(driver.run(self.request, self.state)["allowScopedSourceWork"])
        atomic_state.confirmation_path(self.state).unlink()
        self.assertFalse(driver.run(self.request, self.state)["allowScopedSourceWork"])
        other = self.root / "other-state.json"
        with patch.object(atomic_state, "atomic_write_json", side_effect=atomic_state.StateDurabilityError("fsync_failed")):
            self.assertFalse(driver.run(self.request, other)["allowScopedSourceWork"])

    def test_forged_event_and_forbidden_operations_fail(self) -> None:
        event = driver.event_from_request(self.request)
        event.pop("_currentSourceWorkCapability")
        result = context_governor.evaluate(event, {}, {
            "inputTokenLimit": 120000, "contextTokenLimit": 120000,
            "cumulativeInputLimit": 10000000, "contextBytesLimit": 50 * 1024 * 1024,
            "takeoverTokenLimit": 10000,
        })
        self.assertFalse(result.get("allowScopedSourceWork", False))
        event = driver.event_from_request(self.request)
        event["providerCallRequested"] = True
        result = context_governor.evaluate(event, {}, {
            "inputTokenLimit": 120000, "contextTokenLimit": 120000,
            "cumulativeInputLimit": 10000000, "contextBytesLimit": 50 * 1024 * 1024,
            "takeoverTokenLimit": 10000,
        })
        self.assertFalse(result.get("allowScopedSourceWork", False))

    def test_explicit_stale_memory_is_not_injected(self) -> None:
        event = driver.event_from_request(self.request)
        event["memory"] = {"memoryMode": "fallback_stale"}
        result = context_governor.evaluate(event, {}, {
            "inputTokenLimit": 120000, "contextTokenLimit": 120000,
            "cumulativeInputLimit": 10000000, "contextBytesLimit": 50 * 1024 * 1024,
            "takeoverTokenLimit": 10000,
        })
        self.assertTrue(result["allowScopedSourceWork"])
        self.assertFalse(result["allowMemoryInjection"])
        self.assertFalse(result["allowProjectToolCalls"])

    def test_cross_project_scope_is_not_accepted(self) -> None:
        event = driver.event_from_request(self.request)
        event["projectWorkspaces"] = [{"projectKey": "a", "workspace": str(self.root)}]
        result = context_governor.evaluate(event, {}, {
            "inputTokenLimit": 120000, "contextTokenLimit": 120000,
            "cumulativeInputLimit": 10000000, "contextBytesLimit": 50 * 1024 * 1024,
            "takeoverTokenLimit": 10000,
        })
        self.assertFalse(result.get("allowScopedSourceWork", False))


if __name__ == "__main__":
    unittest.main()
