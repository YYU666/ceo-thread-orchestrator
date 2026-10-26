"""Exercise existing domain APIs with an external-rule snapshot, without products."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
CANONICAL = REPO / "skills/ceo-thread-orchestrator"
INSTALLED = Path(os.environ["CEOFLOW_INSTALLED_SKILL"]).resolve() if os.environ.get("CEOFLOW_INSTALLED_SKILL") else None
TARGETS = (CANONICAL, INSTALLED) if INSTALLED else (CANONICAL,)


class DomainSnapshotCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / "project"
        self.upstream = self.base / "external-skill-fixture"
        self.project.mkdir()
        self.upstream.mkdir()
        (self.project / ".ceo-flow").mkdir()
        (self.project / "docs/domain").mkdir(parents=True)
        self.rule_text = (
            "# Shared production guidance\n\n"
            "## Layout\nValidate traversal before decoration; preserve locked areas.\n\n"
            "## QA\nPlay the affected route and check save/reopen when persistence changes.\n\n"
            "## Engine\nDescribe one reproducible tool gap and its focused regression.\n\n"
            "## Audio\nUnrelated audio guidance must not be preloaded.\n"
        )
        self.source = self.upstream / "rules.md"
        self.source.write_text(self.rule_text, encoding="utf-8")
        self.snapshot = self.project / "docs/domain/production-rules.md"
        shutil.copyfile(self.source, self.snapshot)
        self.spec = self.project / "docs/game-spec.md"
        self.spec.write_text(
            "# Current game\n\n## Areas\nConnect the station to the plaza; retain the user's plaza edits.\n\n"
            "## Acceptance\nWalk the full route; save/reopen without changing the locked plaza.\n",
            encoding="utf-8",
        )
        self.import_manifest = {
            "sourceSkill": "game-production-fixture",
            "sourceVersion": "fixture-v1",
            "files": [{"sourcePath": "rules.md", "snapshotPath": "docs/domain/production-rules.md",
                       "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest()}],
            "status": "synthetic_fixture_only",
        }
        self.profile = {"schema": "ceo_project_domain_v1", "domain": "game", "entries": [
            self.entry("layout", "rules", "docs/domain/production-rules.md", "Layout", "game_production", "layout"),
            self.entry("qa", "rules", "docs/domain/production-rules.md", "QA", "game_production", "qa"),
            self.entry("areas", "spec", "docs/game-spec.md", "Areas", "game_production", "layout", required=True),
            self.entry("acceptance", "spec", "docs/game-spec.md", "Acceptance", "game_production", "qa", required=True),
            self.entry("engine", "rules", "docs/domain/production-rules.md", "Engine", "engine_development", "tools"),
        ]}
        self.config = self.project / ".ceo-flow/domain.json"
        self.write_profile()

    @staticmethod
    def entry(name, kind, path, section, work_kind, topic, required=False):
        return {"id": name, "kind": kind, "path": path, "section": section,
                "workKinds": [work_kind], "topics": [topic], "required": required}

    def write_profile(self):
        self.config.write_text(json.dumps(self.profile), encoding="utf-8")

    def run_loader(self, root=CANONICAL, *, task="parent", kind="game_production", topics=("layout", "qa")):
        command = [sys.executable, "-B", str(root / "scripts/load_project_domain.py"),
                   "--workspace", str(self.project), "--task-id", task,
                   "--work-kind", kind, "--topics", *topics,
                   "--state", str(self.base / ("canonical-state.json" if root == CANONICAL else "installed-state.json"))]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.returncode, json.loads(result.stdout)

    def test_project_snapshot_preserves_rule_identity_and_separate_game_spec(self):
        self.assertEqual(self.source.read_bytes(), self.snapshot.read_bytes())
        for root in TARGETS:
            with self.subTest(root=root):
                code, result = self.run_loader(root)
                self.assertEqual(code, 0)
                self.assertEqual(result["domainStatus"], "prepared")
                self.assertEqual({item["id"] for item in result["context"]}, {"layout", "qa", "areas", "acceptance"})
                self.assertNotIn("Unrelated audio", "\n".join(item["text"] for item in result["context"]))
                self.assertNotIn("one reproducible tool gap", "\n".join(item["text"] for item in result["context"]))
                self.assertEqual(len(result["taskCard"]["ruleRefs"]), 2)
                self.assertEqual(len(result["taskCard"]["specRefs"]), 2)
                # Version provenance is a caller task-card attachment, not a loader schema field.
                card = {**result["taskCard"], "domainSnapshot": self.import_manifest}
                self.assertEqual(card["domainSnapshot"]["sourceVersion"], "fixture-v1")
                for ref in card["ruleRefs"]:
                    self.assertEqual(ref["fileSha256"], self.import_manifest["files"][0]["sha256"])
                    item = next(item for item in result["context"] if item["id"] == ref["id"])
                    self.assertEqual(ref["excerptSha256"], hashlib.sha256(item["text"].encode("utf-8")).hexdigest())
                self.assertLessEqual(len(result["context"]), 8)
                self.assertLessEqual(len(json.dumps(result["context"], ensure_ascii=False).encode("utf-8")), 12 * 1024)

    def test_absolute_parent_and_symlink_external_rules_remain_rejected(self):
        link = self.project / "docs/domain/external-link.md"
        link.symlink_to(self.source)
        for path in (str(self.source), "../external-skill-fixture/rules.md", "docs/domain/external-link.md"):
            self.profile["entries"][0]["path"] = path
            self.write_profile()
            for root in TARGETS:
                with self.subTest(path=path, root=root):
                    code, result = self.run_loader(root)
                    self.assertEqual(code, 2)
                    self.assertEqual(result["domainStatus"], "unavailable")
                    self.assertEqual(result["context"], [])
                    self.assertFalse(result["executionPolicyChanged"])

    def test_parent_preparation_is_not_child_reading_and_each_task_deduplicates(self):
        for root in TARGETS:
            with self.subTest(root=root):
                self.assertEqual(self.run_loader(root)[1]["domainStatus"], "prepared")
                repeated = self.run_loader(root)[1]
                self.assertEqual(repeated["domainStatus"], "references_only")
                self.assertEqual(repeated["context"], [])
                child = self.run_loader(root, task="child")[1]
                self.assertEqual(child["domainStatus"], "prepared")
                self.assertEqual(len(child["context"]), 4)
                self.assertTrue(set(child).isdisjoint({"hostDeliveryAck", "childHasRead", "allowProviderCalls"}))
                self.assertEqual(self.run_loader(root, task="child")[1]["context"], [])

    def test_engine_work_uses_only_its_topic_without_game_specs(self):
        self.spec.unlink()
        for root in TARGETS:
            with self.subTest(root=root):
                code, result = self.run_loader(root, kind="engine_development", topics=("tools",))
                self.assertEqual(code, 0)
                self.assertEqual([item["id"] for item in result["context"]], ["engine"])
                self.assertEqual(result["missingSpecs"], [])
                self.assertEqual(result["taskCard"]["specRefs"], [])

    def test_missing_optional_snapshot_or_index_does_not_change_policy(self):
        self.snapshot.unlink()
        for root in TARGETS:
            with self.subTest(root=root):
                result = self.run_loader(root)[1]
                self.assertEqual(result["domainStatus"], "prepared")
                self.assertEqual(len(result["warnings"]), 2)
                self.assertEqual({item["kind"] for item in result["context"]}, {"spec"})
                self.assertFalse(result["executionPolicyChanged"])
        self.config.unlink()
        for root in TARGETS:
            self.assertEqual(self.run_loader(root)[1]["domainStatus"], "not_configured")

    def test_snapshot_change_updates_hashes_without_proving_accepted_version(self):
        for root in TARGETS:
            self.run_loader(root)
        self.snapshot.write_text(self.rule_text.replace("traversal before decoration", "traversal and route feedback before decoration"))
        for root in TARGETS:
            with self.subTest(root=root):
                result = self.run_loader(root)[1]
                self.assertEqual([item["id"] for item in result["context"]], ["layout"])
                for ref in result["taskCard"]["ruleRefs"]:
                    self.assertNotEqual(ref["fileSha256"], self.import_manifest["files"][0]["sha256"])
                self.assertFalse(result["executionPolicyChanged"])
                self.assertNotIn("sourceVersion", result["taskCard"])


if __name__ == "__main__":
    unittest.main()
