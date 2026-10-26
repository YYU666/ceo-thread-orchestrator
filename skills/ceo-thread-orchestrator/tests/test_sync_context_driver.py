import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sync_context_driver as driver


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = str(Path(self.temp.name).resolve())
        self.state = Path(self.root) / "ledger.json"
        self.event = dict(boundary="before_dispatch", eventId="dispatch-1", workspace=self.root,
                          projectId="project-a", taskId="task-a", taskGoal="implement panel")
        self.calls = []

    def invoke(self, request):
        self.calls.append(request)
        return dict(schemaVersion="zhixia.sync_context.v1", operation="sync_context",
                    readOnly=True, writeAuthority=False, workspace=request["workspace"],
                    projectIdentity=dict(projectId="project-a", canonicalRoot=request["workspace"]),
                    scanBinding=dict(matched=True, authorizedCheckpointId="checkpoint-a"),
                    memoryMode="app_owned_memory_core", authorityVerification="app_owned_verified",
                    current=True, recoveryReady=True, contextGenerationId="context-abc",
                    contextQueryKey=driver.query_key(request["taskGoal"], request["queryType"]),
                    status="ready_new", returnedCount=1, tokenEstimate=100,
                    items=[dict(projectId="project-a", layer="hot", summary="compact memory", sourceRefs=[])],
                    sourceRefs=[dict(projectId="project-a", path="src/panel.ts")])

    def run_event(self, **changes):
        return driver.run(self.event | changes, self.state, self.invoke)

    def test_once_and_restart_no_boundary_poll(self):
        self.assertTrue(self.run_event()["allowContextInjection"])
        self.assertFalse(self.run_event()["allowContextInjection"])
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(self.run_event(eventId="dispatch-2")["allowContextInjection"])
        self.assertEqual(self.calls[-1]["knownContextGenerationId"], "context-abc")

    def test_goal_change_same_generation_and_separate_tasks(self):
        self.run_event()
        self.assertTrue(self.run_event(eventId="dispatch-2", taskGoal="review panel")["allowContextInjection"])
        self.assertTrue(self.run_event(taskId="task-b")["allowContextInjection"])

    def test_workspace_ledgers_are_independent(self):
        self.run_event()
        other = Path(self.root) / "second"
        other.mkdir()
        self.assertTrue(self.run_event(workspace=str(other))["allowContextInjection"])

    def test_unchanged_does_not_inject(self):
        self.run_event()
        def unchanged(req):
            p = self.invoke(req)
            p.update(status="unchanged", returnedCount=0, tokenEstimate=0, items=[], sourceRefs=[])
            return p
        result = driver.run(self.event | dict(eventId="next"), self.state, unchanged)
        self.assertEqual(result["status"], "unchanged")
        self.assertNotIn("packet", result)

    def test_stale_unknown_scope_and_forbidden_payloads_stay_closed(self):
        for field, value in (("current", False), ("status", "stale"), ("writeAuthority", True),
                             ("contextQueryKey", "query-wrong"), ("tokenEstimate", 1201),
                             ("rawChat", "forbidden"), ("items", [dict(projectId="project-a", layer="cold")]),
                             ("sourceRefs", [dict(projectId="project-a", path="../escape")]),
                             ("projectIdentity", dict(projectId="other", canonicalRoot=self.root))):
            with self.subTest(field=field):
                def bad(req):
                    return self.invoke(req) | {field: value}
                event = self.event | dict(eventId="bad-" + field)
                r = driver.run(event, self.state, bad)
                self.assertFalse(r["allowContextInjection"])
                self.assertFalse(r["programGoalBlocked"])
                self.assertNotIn("packet", r)

    def test_invalid_boundary_and_event_alias_make_no_runtime_calls(self):
        self.assertFalse(self.run_event(boundary="model_response")["allowContextInjection"])
        self.assertEqual(self.calls, [])
        self.run_event()
        self.assertFalse(self.run_event(taskGoal="changed with reused id")["allowContextInjection"])
        self.assertEqual(len(self.calls), 1)

    def test_durability_failure_suppresses_output(self):
        real = driver.atomic_state.locked_update_json
        def ambiguous(path, update):
            real(path, update)
            raise RuntimeError("injected_after_commit")
        with patch.object(driver.atomic_state, "locked_update_json", ambiguous):
            r = self.run_event()
        self.assertFalse(r["allowContextInjection"])
        self.assertNotIn("packet", r)
        self.assertFalse(self.run_event()["allowContextInjection"])
        self.assertEqual(len(self.calls), 1)

    def test_fresh_unknown_unchanged_is_rejected(self):
        def bad(req):
            return self.invoke(req) | dict(status="unchanged", items=[], sourceRefs=[], returnedCount=0, tokenEstimate=0)
        self.assertFalse(driver.run(self.event, self.state, bad)["allowContextInjection"])

    def test_concurrent_duplicate_event_emits_once(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.run_event(), range(2)))
        self.assertEqual(sum(r["allowContextInjection"] for r in results), 1)
        self.assertEqual(len(self.calls), 1)

    def test_new_generation_after_refresh_emits_without_refreshing_runtime(self):
        self.run_event()
        def fresh(req):
            return self.invoke(req) | dict(contextGenerationId="context-new")
        r = driver.run(self.event | dict(eventId="refresh-1", boundary="after_accepted_refresh"), self.state, fresh)
        self.assertTrue(r["allowContextInjection"])
        self.assertFalse(r["writeAuthority"])
        self.assertFalse(r["hostTriggerVerified"])

    def test_transport_failure_is_recorded_and_not_polled(self):
        calls = []
        def unavailable(req):
            calls.append(req)
            raise RuntimeError("unavailable")
        for _ in range(2):
            self.assertFalse(driver.run(self.event, self.state, unavailable)["allowContextInjection"])
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
