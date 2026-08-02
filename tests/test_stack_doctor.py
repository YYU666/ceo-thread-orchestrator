from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "ceo-thread-orchestrator" / "scripts" / "stack_doctor.py"


def load_module():
    spec = importlib.util.spec_from_file_location("stack_doctor", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["stack_doctor"] = module
    spec.loader.exec_module(module)
    return module


doctor = load_module()


class StackDoctorTests(unittest.TestCase):
    def test_missing_sidecars_old_fresh_packet_and_duplicate_ids_fail_closed(self):
        packet = {
            "memoryMode": "layered",
            "memoryFactSidecar": {"status": "missing"},
            "memoryCoreSidecar": {"status": "missing"},
            "items": [
                {"id": "same", "freshness": "fresh", "sourceRefs": [{"path": "old.md", "updatedAt": "2026-06-01T00:00:00Z"}]},
                {"id": "same", "freshness": "fresh", "sourceRefs": [{"path": "old.md", "updatedAt": "2026-06-01T00:00:00Z"}]},
            ],
        }
        result = doctor.memory_diagnostics(packet, datetime(2026, 7, 28, tzinfo=timezone.utc), 7)
        self.assertEqual(result["reportedMemoryMode"], "layered")
        self.assertEqual(result["effectiveMemoryMode"], "fallback_stale")
        self.assertEqual(result["duplicateItemIds"], ["same"])
        self.assertFalse(result["currentStateClaimAllowed"])
        self.assertFalse(result["recoveryReadyClaimAllowed"])
        self.assertIn("stale_packet_claimed_current", result["diagnostics"])

    def test_available_current_unique_memory_can_be_current_but_not_recovery_ready_without_proof(self):
        packet = {
            "memoryMode": "layered",
            "memoryFactSidecar": {"status": "available"},
            "memoryCoreSidecar": {"status": "available"},
            "items": [{"id": "one", "sourceRefs": [{"updatedAt": "2026-07-28T00:00:00Z"}]}],
            "recoveryReady": False,
        }
        result = doctor.memory_diagnostics(packet, datetime(2026, 7, 28, tzinfo=timezone.utc), 7)
        self.assertTrue(result["currentStateClaimAllowed"])
        self.assertFalse(result["recoveryReadyClaimAllowed"])

    def test_project_id_is_stable_across_worktrees(self):
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory) / "repo"
            canonical.mkdir()
            worktree_a = Path(directory) / "wt-a"
            worktree_b = Path(directory) / "wt-b"
            worktree_a.mkdir()
            worktree_b.mkdir()
            first = doctor.project_identity(canonical, worktree_a, None)
            second = doctor.project_identity(canonical, worktree_b, None)
            self.assertEqual(first["projectId"], second["projectId"])
            self.assertEqual(first["canonicalRepoId"], second["canonicalRepoId"])
            self.assertNotEqual(first["projectIdentitySha256"], second["projectIdentitySha256"])

    def test_cli_emits_strict_json_and_never_enables_cmmd_r1(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            source = root / "source-skill"
            installed = root / "installed-skill"
            zhixia = root / "zhixia"
            for path in (project, source, installed, zhixia):
                path.mkdir()
            (source / "SKILL.md").write_text("same", encoding="utf-8")
            (installed / "SKILL.md").write_text("same", encoding="utf-8")
            memory = root / "memory.json"
            memory.write_text(json.dumps({
                "memoryMode": "layered",
                "memoryFactSidecar": {"status": "missing"},
                "memoryCoreSidecar": {"status": "missing"},
                "items": [],
            }), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(SCRIPT), "--project-root", str(project),
                "--ceoflow-skill", str(source), "--installed-skill", str(installed),
                "--zhixia-skill", str(zhixia), "--memory-json", str(memory),
                "--now", "2026-07-28T00:00:00Z", "--json",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema"], "ceoflow.stack_doctor.v1")
            self.assertTrue(payload["ceoFlow"]["installedMatchesSource"])
            self.assertEqual(payload["zhixia"]["memory"]["effectiveMemoryMode"], "fallback_stale")
            self.assertFalse(payload["claims"]["cmmdR1Enabled"])
            self.assertFalse(payload["claims"]["staticChecksProveBehavior"])


class PolicyContractTests(unittest.TestCase):
    def test_task_card_profiles_are_bundled_and_r1_is_fail_closed(self):
        templates = ROOT / "skills" / "ceo-thread-orchestrator" / "templates"
        for name in ("task-card-minimal.md", "task-card-standard.md", "task-card-r1.md"):
            self.assertTrue((templates / name).is_file(), name)
        r1 = (templates / "task-card-r1.md").read_text(encoding="utf-8")
        self.assertIn("Accepted R1 readiness evidence", r1)
        cmmd = (ROOT / "skills" / "ceo-thread-orchestrator" / "references" / "cmmd-execution.md").read_text(encoding="utf-8")
        self.assertIn("future/gated path", cmmd)

    def test_static_smoke_is_explicitly_not_behavioral_proof(self):
        text = (ROOT / "skills" / "ceo-thread-orchestrator" / "references" / "forward-testing.md").read_text(encoding="utf-8")
        self.assertIn("does not call Codex", text)
        self.assertIn("must not be converted into a passing behavioral claim", text)

    def test_evidence_driven_coding_discipline_is_compact_default_off_and_r1_neutral(self):
        reference = (ROOT / "skills" / "ceo-thread-orchestrator" / "references" / "coding-discipline.md").read_text(encoding="utf-8")
        standard = (ROOT / "skills" / "ceo-thread-orchestrator" / "templates" / "task-card-standard.md").read_text(encoding="utf-8")
        r1 = (ROOT / "skills" / "ceo-thread-orchestrator" / "templates" / "task-card-r1.md").read_text(encoding="utf-8")
        self.assertIn("evidence-driven-coding-discipline-v1", reference)
        self.assertIn("Default enabled: false", reference)
        self.assertIn("not an official Karpathy skill", reference)
        self.assertIn("does not authorize an R1 writer", reference)
        self.assertIn("Coding Discipline Gate, when triggered", standard)
        self.assertIn("Coding Discipline Profile ID/state/SHA-256, when triggered", r1)

    def test_view_image_is_not_treated_as_zero_payload_local_inspection(self):
        reference = (ROOT / "skills" / "ceo-thread-orchestrator" / "references" / "visual-evidence.md").read_text(encoding="utf-8")
        standard = (ROOT / "skills" / "ceo-thread-orchestrator" / "templates" / "task-card-standard.md").read_text(encoding="utf-8")
        self.assertIn("`view_image` is not a zero-payload local viewer", reference)
        self.assertIn("Do not call `view_image`", reference)
        self.assertIn("Never batch or loop multiple `view_image`/`image(...)` results", reference)
        self.assertIn("Visual transport mode: zero-payload-local-analysis | bounded-model-vision", reference)
        self.assertIn("Model-visible image budget: 0 by default", reference)
        self.assertIn("Visual evidence policy / transport mode / model-visible image budget", standard)

    def test_bounded_model_vision_is_short_lived_non_forked_and_one_image(self):
        reference = (ROOT / "skills" / "ceo-thread-orchestrator" / "references" / "visual-evidence.md").read_text(encoding="utf-8")
        self.assertIn("fresh short-lived visual worker with no forked parent context", reference)
        self.assertIn("recommended below 800 KB", reference)
        self.assertIn("Use at most one model-visible image per turn", reference)
        self.assertIn("Do not forward them to subagents", reference)
        self.assertIn("even when the session is below 50 MB", reference)

    def test_visual_transport_smoke_cases_are_present(self):
        cases = json.loads((ROOT / "examples" / "smoke-eval-cases.json").read_text(encoding="utf-8"))
        ids = {case["id"] for case in cases}
        self.assertTrue({
            "view-image-is-model-visible-transport",
            "bounded-model-vision-short-lived-worker",
            "user-image-not-relayed-to-subagent",
            "visual-payload-growth-below-50mb-fuses",
        }.issubset(ids))

    def test_visual_transport_requires_real_forward_evidence(self):
        forward = (ROOT / "skills" / "ceo-thread-orchestrator" / "references" / "forward-testing.md").read_text(encoding="utf-8")
        self.assertIn("Visual Transport Forward Test", forward)
        self.assertIn("modelVisibleImagesUsed=0", forward)
        self.assertIn("Any `view_image` call in zero-payload mode", forward)
        self.assertIn("prevents a behavioral claim", forward)


if __name__ == "__main__":
    unittest.main()
