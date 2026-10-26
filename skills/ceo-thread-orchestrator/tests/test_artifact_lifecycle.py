from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import delivery_policy as policy  # noqa: E402


class ArtifactLifecycleTests(unittest.TestCase):
    def build_request(self, **changes):
        identity = {"command": "build-runtime", "inputsSha256": "a" * 64,
                    "environmentSha256": "b" * 64}
        return {"operation": "build", "triggerReason": "Validate changed map route",
                "validationTarget": "affected_check", "changeKind": "content",
                "requiredChecks": ["runtime-smoke", "route-play"],
                "artifact": {"checkIdentity": {"previous": {**identity, "status": "passed", "exitCode": 0},
                            "current": dict(identity), "independentlyVerified": True,
                            "dependencyCoverageComplete": True, "flaky": False, "newConcern": False},
                            "expectedSha256": "c" * 64, "observedSha256": "c" * 64,
                            "exists": True, "independentlyVerified": True,
                            "coveredChecks": ["runtime-smoke"]}, **changes}

    def cleanup_request(self, **changes):
        return {"operation": "cleanup", "path": "/fixture/build/old-scratch",
                "category": "scratch", "userAuthorizedTemporaryPaths": ["/fixture/build/old-scratch"],
                "authorizationSource": "user-approved fixture temporary paths",
                "activeReferencesChecked": True, "activeReferenceCount": 0,
                "canonicalPathVerified": True, "contentIdentityVerified": True,
                "recoveryChecked": True, "rebuildVerified": True,
                "temporaryRetentionExceeded": True, **changes}

    def test_content_reuses_runtime_but_does_not_claim_new_route_verified(self):
        result = policy.evaluate(self.build_request())
        self.assertEqual(result["action"], "reuse_artifact_run_missing_checks")
        self.assertEqual(result["checksToRun"], ["route-play"])
        self.assertFalse(result["contentChangeRequiresEngineRebuild"])
        self.assertFalse(result["allowProductCompletion"])

    def test_exact_verified_artifact_can_cover_milestone_without_repackaging(self):
        request = self.build_request(validationTarget="milestone_delivery")
        request["artifact"]["coveredChecks"].append("route-play")
        result = policy.evaluate(request)
        self.assertEqual(result["action"], "reuse_verified_artifact")
        self.assertEqual(result["checksToRun"], [])

    def test_source_config_dependency_toolchain_changes_invalidate_affected_reuse(self):
        for field in ("inputsSha256", "environmentSha256", "command"):
            request = self.build_request(changeKind="source")
            request["artifact"]["checkIdentity"]["current"][field] = "d" * 64
            result = policy.evaluate(request)
            self.assertFalse(result["reuseArtifact"])
            self.assertEqual(result["action"], "incremental_affected_validation")
            self.assertEqual(result["checksToRun"], request["requiredChecks"])

    def test_missing_tampered_flaky_or_uncovered_artifact_is_not_reused(self):
        base = self.build_request()
        mutations = [
            lambda a: a.update(exists=False),
            lambda a: a.update(observedSha256="f" * 64),
            lambda a: a.update(independentlyVerified=False),
            lambda a: a["checkIdentity"].update(flaky=True),
            lambda a: a["checkIdentity"].update(dependencyCoverageComplete=False),
            lambda a: a["checkIdentity"].update(newConcern=True),
        ]
        for mutate in mutations:
            request = copy.deepcopy(base)
            mutate(request["artifact"])
            self.assertFalse(policy.evaluate(request)["reuseArtifact"])

    def test_full_package_requires_declared_native_or_milestone_target(self):
        for target in ("affected_native_check", "milestone_delivery"):
            request = self.build_request(validationTarget=target)
            request.pop("artifact")
            self.assertEqual(policy.evaluate(request)["action"], "full_package_for_declared_target")
        request = self.build_request()
        request.pop("artifact")
        self.assertEqual(policy.evaluate(request)["action"], "incremental_affected_validation")
        self.assertFalse(policy.evaluate(self.build_request(triggerReason=""))["ok"])

    def test_exact_authorized_temporary_candidate_never_grants_deletion(self):
        result = policy.evaluate(self.cleanup_request())
        self.assertTrue(result["cleanupCandidate"])
        self.assertFalse(result["allowDeletion"])
        self.assertFalse(result["evidenceVerified"])

    def test_protected_data_never_becomes_a_temporary_cleanup_candidate(self):
        for category in ("release", "rollback", "unique_evidence", "user_project", "generated_asset", "unknown_recovery"):
            result = policy.evaluate(self.cleanup_request(category=category))
            self.assertFalse(result["cleanupCandidate"])
            self.assertEqual(result["action"], "retain_artifact")

    def test_parent_allowlist_age_size_or_missing_live_checks_cannot_authorize_cleanup(self):
        for changes in ({"userAuthorizedTemporaryPaths": ["/fixture/build"]},
                        {"authorizationSource": ""}, {"activeReferencesChecked": False},
                        {"activeReferenceCount": 1}, {"canonicalPathVerified": False},
                        {"contentIdentityVerified": False}, {"recoveryChecked": False},
                        {"rebuildVerified": False}, {"temporaryRetentionExceeded": False}):
            result = policy.evaluate(self.cleanup_request(**changes, ageDays=90, sizeBytes=100000000))
            self.assertFalse(result["cleanupCandidate"])
            self.assertFalse(result["allowDeletion"])

    def test_wildcard_parent_relative_and_root_paths_fail_without_global_block(self):
        for path in ("/", "/fixture", "scratch/file", "/fixture/../data", "/fixture/build/*", "/fixture/build//copy"):
            result = policy.evaluate(self.cleanup_request(path=path))
            self.assertFalse(result["ok"])
            self.assertFalse(result["allowDeletion"])
            self.assertNotIn("programGoalBlocked", result)

    def test_invalid_boolean_or_count_cannot_create_cleanup_candidate(self):
        for field, value in (("activeReferenceCount", False), ("activeReferenceCount", -1),
                             ("recoveryChecked", "yes"), ("rebuildVerified", 1)):
            result = policy.evaluate(self.cleanup_request(**{field: value}))
            self.assertFalse(result["ok"])
            self.assertFalse(result["cleanupCandidate"])


if __name__ == "__main__":
    unittest.main()
