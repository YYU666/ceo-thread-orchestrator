from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "delivery_policy.py"
spec = importlib.util.spec_from_file_location("delivery_policy", SCRIPT)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class DeliveryPolicyTests(unittest.TestCase):
    def staffing_request(self, **changes):
        return dict(dict(operation="staffing", independentReadyCount=1, activeChildLanes=0,
                         maxChildLanes=2, delegationAuthorized=True, delegationAvailable=True,
                         singleThreadRequested=False, handoffWorthwhile=True,
                         checkpoint="slice_complete"), **changes)

    def test_independent_ready_work_recommends_one_child_not_visible_task(self):
        result = policy.evaluate(self.staffing_request(independentReadyCount=4))
        self.assertEqual(result["action"], "delegate_one_independent_unit")
        self.assertEqual(result["additionalLanes"], 1)
        self.assertFalse(result["visibleTaskRequired"])
        self.assertFalse(result["delegationAuthorized"])

    def test_capacity_authorization_and_manual_single_thread_are_respected(self):
        for change in (dict(activeChildLanes=2), dict(activeChildLanes=3),
                       dict(delegationAuthorized=False), dict(delegationAvailable=False),
                       dict(singleThreadRequested=True)):
            self.assertEqual(policy.evaluate(self.staffing_request(**change))["additionalLanes"], 0)

    def test_serial_reason_expires_at_next_checkpoint(self):
        result = policy.evaluate(self.staffing_request(independentReadyCount=0))
        self.assertEqual(result["action"], "record_concrete_serial_reason")
        result = policy.evaluate(self.staffing_request(independentReadyCount=0,
                                                       serialReason="shared bootstrap write-set"))
        self.assertEqual(result["action"], "continue_serial_until_next_checkpoint")
        self.assertEqual(result["nextAssessment"], "next_slice_boundary_or_scope_change")

    def test_expansion_and_takeover_completion_reassess_instead_of_permanent_solo(self):
        for trigger in ("scope_expanded", "takeover_complete"):
            result = policy.evaluate(self.staffing_request(checkpoint=trigger))
            self.assertEqual(result["additionalLanes"], 1)

    def test_no_value_handoff_never_forces_parallelism(self):
        result = policy.evaluate(self.staffing_request(handoffWorthwhile=False,
                                                       serialReason="task takes less time than briefing"))
        self.assertEqual(result["additionalLanes"], 0)

    def test_staffing_rejects_ambiguous_counts_flags_and_checkpoints(self):
        for key, value in (("independentReadyCount", True), ("activeChildLanes", -1),
                           ("maxChildLanes", 0), ("delegationAuthorized", "yes"),
                           ("checkpoint", "every_tool_call"), ("serialReason", "")):
            self.assertFalse(policy.evaluate(self.staffing_request(**{key: value}))["ok"])

    def test_nonquick_plan_requires_staffing_assessment_or_uses_explicit_inputs(self):
        request = dict(operation="plan", changedFileCount=6, riskFlags=[],
                       independentReviewRequired=False, localReversible=True)
        self.assertEqual(policy.evaluate(request)["staffing"]["action"], "assess_independent_work")
        request["staffing"] = self.staffing_request()
        self.assertEqual(policy.evaluate(request)["staffing"]["additionalLanes"], 1)

    def plan(self, **changes):
        return policy.evaluate(dict(operation="plan", changedFileCount=2, riskFlags=[],
                                    independentReviewRequired=False, localReversible=True, **changes))

    def test_two_tooltips_use_one_owner_without_mandatory_handoff(self):
        result = self.plan()
        self.assertEqual(result["mode"], "quick")
        self.assertFalse(result["newTaskRequired"])
        self.assertFalse(result["independentReviewRequired"])
        self.assertEqual(result["verificationProfile"], "focused")

    def test_one_file_permission_change_is_not_a_quick_path(self):
        result = policy.evaluate(dict(operation="plan", changedFileCount=1, riskFlags=["permissions"],
                                      independentReviewRequired=False, localReversible=True))
        self.assertEqual(result["mode"], "high_risk")
        self.assertTrue(result["independentReviewRequired"])

    def test_explicit_review_and_time_budget_are_preserved(self):
        result = policy.evaluate(dict(operation="plan", changedFileCount=2, riskFlags=[],
                                      independentReviewRequired=True, localReversible=True, budgetMinutes=20))
        self.assertTrue(result["independentReviewRequired"])
        self.assertEqual(result["budgetMinutes"], 20)

    def test_unknown_risk_and_bool_count_do_not_silently_downgrade(self):
        for key, value in (("riskFlags", ["unknown"]), ("changedFileCount", True),
                           ("localReversible", "yes"), ("budgetMinutes", 0)):
            request = dict(operation="plan", changedFileCount=2, riskFlags=[],
                           localReversible=True, independentReviewRequired=False)
            request[key] = value
            self.assertFalse(policy.evaluate(request)["ok"])

    def test_timeout_preserves_live_writer_and_never_resets_deadline(self):
        result = policy.evaluate(dict(operation="wait", elapsedSeconds=1900, budgetSeconds=1800,
                                      writerStoppedConfirmed=False, runningHandle="worker-1",
                                      meaningfulProgressChanged=True, timeoutActionIssued=False))
        self.assertEqual(result["action"], "request_partial_and_safe_stop_once")
        self.assertFalse(result["allowReplacementWriter"])
        self.assertTrue(result["retainRunningHandle"])
        self.assertFalse(result["deadlineResetAllowed"])

    def test_unchanged_progress_waits_and_missing_handle_locates_not_replaces(self):
        request = dict(operation="wait", elapsedSeconds=30, budgetSeconds=1800,
                       writerStoppedConfirmed=False, runningHandle="worker-1", meaningfulProgressChanged=False,
                       timeoutActionIssued=False)
        self.assertEqual(policy.evaluate(request)["action"], "bounded_event_wait")
        request["runningHandle"] = None
        self.assertFalse(policy.evaluate(request)["allowReplacementWriter"])
        request["writerStoppedConfirmed"] = True
        self.assertEqual(policy.evaluate(request)["action"], "review_partial_then_shrink_or_handoff")

    def test_timeout_reentry_does_not_repeat_partial_request(self):
        result = policy.evaluate(dict(operation="wait", elapsedSeconds=2100, budgetSeconds=1800,
                                      writerStoppedConfirmed=False, runningHandle="worker-1",
                                      meaningfulProgressChanged=False, timeoutActionIssued=True))
        self.assertEqual(result["action"], "await_stop_or_partial_event_no_repeat")
        self.assertFalse(result["allowReplacementWriter"])

    def reuse_request(self):
        check = dict(command="npm test -- focused", inputsSha256="a" * 64, environmentSha256="b" * 64,
                     status="passed", exitCode=0)
        return dict(operation="reuse", previous=check, current=copy.deepcopy(check),
                    independentlyVerified=True, dependencyCoverageComplete=True, newConcern=False, flaky=False)

    def test_same_source_environment_command_reuses_inspected_evidence(self):
        self.assertTrue(policy.evaluate(self.reuse_request())["reuseCheck"])

    def test_changed_dirty_input_environment_or_command_reruns(self):
        for key, value in (("inputsSha256", "c" * 64), ("environmentSha256", "c" * 64),
                           ("command", "npm test -- another")):
            request = self.reuse_request()
            request["current"][key] = value
            self.assertFalse(policy.evaluate(request)["reuseCheck"])

    def test_unknown_coverage_failed_forged_or_new_concern_never_reuses(self):
        for key, value in (("independentlyVerified", False), ("dependencyCoverageComplete", False),
                           ("newConcern", True), ("flaky", True)):
            request = self.reuse_request()
            request[key] = value
            self.assertFalse(policy.evaluate(request)["reuseCheck"])
        for value in (1, False, "0"):
            request = self.reuse_request()
            request["previous"]["exitCode"] = value
            self.assertFalse(policy.evaluate(request)["reuseCheck"])

    def ui_request(self):
        target = dict(app="editor", window="window-1", document="project-1")
        return dict(operation="ui", expectedTarget=target, observedTarget=copy.deepcopy(target),
                    allowedActions=["play", "move_right", "save"], action="move_right", deviationObserved=False)

    def test_exact_target_scoped_action_can_proceed(self):
        self.assertTrue(policy.evaluate(self.ui_request())["allowUiAction"])

    def test_example_navigation_wrong_identity_and_prior_deviation_stop(self):
        request = self.ui_request()
        request["action"] = "open_examples"
        self.assertFalse(policy.evaluate(request)["allowUiAction"])
        for field in ("app", "window", "document"):
            request = self.ui_request()
            request["observedTarget"][field] = "other"
            self.assertFalse(policy.evaluate(request)["allowUiAction"])
        request = self.ui_request()
        request["deviationObserved"] = True
        self.assertFalse(policy.evaluate(request)["allowUiAction"])

    def test_modules_and_key_dispatch_do_not_prove_play_save_reopen(self):
        request = dict(operation="outcome", candidateSha256="a" * 64,
                       requiredScenarios=["play", "save_reopen"], observations={})
        request["observations"]["play"] = dict(status="key_sent", candidateSha256="a" * 64,
                                                evidenceRef="evidence/move.json#sha256=" + "b" * 64)
        result = policy.evaluate(request)
        self.assertEqual(result["unverifiedScenarios"], ["play", "save_reopen"])
        for key in request["requiredScenarios"]:
            request["observations"][key] = dict(status="observed_pass", candidateSha256="a" * 64,
                                                 evidenceRef="evidence/result.json#sha256=" + "b" * 64)
        result = policy.evaluate(request)
        self.assertTrue(result["outcomeReadyForReview"])
        self.assertFalse(result["allowProductCompletion"])
        self.assertFalse(result["evidenceVerified"])
        request["observations"]["play"]["evidenceRef"] = "../escape.json#sha256=" + "b" * 64
        self.assertFalse(policy.evaluate(request)["outcomeReadyForReview"])
        request["candidateSha256"] = "c" * 64
        self.assertFalse(policy.evaluate(request)["outcomeReadyForReview"])

    def test_cli_rejects_large_deep_and_invalid_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "request.json"
            for raw in ("x" * (policy.MAX_BYTES + 1), "[" * 1500 + "]" * 1500,
                        '{"operation":"plan","changedFileCount":2,"localReversible":true,'
                        '"independentReviewRequired":false,"riskFlags":["permissions"],"riskFlags":[]}',
                        json.dumps({"operation": "unknown"})):
                path.write_text(raw)
                result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                value = json.loads(result.stdout)
                self.assertFalse(value["allowUiAction"])
                self.assertFalse(value["allowProductCompletion"])


if __name__ == "__main__":
    unittest.main()
