from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "ceo-thread-orchestrator" / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


scorecard = load_module("scorecard_handoff", SCRIPTS / "scorecard_handoff.py")
pipeline = load_module("validate_pipeline", SCRIPTS / "validate_pipeline.py")


class ValidatorTests(unittest.TestCase):
    def write_temp(self, text: str) -> Path:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".yaml", encoding="utf-8", delete=False)
        tmp.write(text)
        tmp.close()
        return Path(tmp.name)

    def test_implementation_handoff_decision_field_cannot_bypass_write_set_failure(self):
        path = self.write_temp(
            """
handoff:
  schema: typed_handoff_v1
  laneId: backend-api
  status: complete
  summary: done with evidence
  decision: accept
  task:
    goal: bounded task
  changes:
    filesChanged:
      - path: src/api/example.ts
        changeType: modified
    writeSetCompliant: false
  evidence:
    commandsRun:
      - command: npm test
        result: pass
  risks:
    knownIssues: []
  next:
    recommendedAction: review
"""
        )
        result = scorecard.score(path)
        self.assertFalse(result["ok"])
        self.assertEqual(result["type"], "implementation")
        self.assertTrue(any("writeSetCompliant is false" in err for err in result["errors"]))

    def test_review_done_criteria_is_not_bare_done_false_positive(self):
        path = self.write_temp(
            """
review:
  schema: review_handoff_v1
  laneId: integration-review
  decision: accept
  evidenceInspected:
    - task card
    - diff
  reasons:
    - All done criteria met.
  missingEvidence: []
  requiredFixes: []
  residualRisk: []
  confidence: medium
"""
        )
        result = scorecard.score(path)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["type"], "review")

    def test_review_confidence_value_is_validated(self):
        path = self.write_temp(
            """
review:
  schema: review_handoff_v1
  laneId: integration-review
  decision: accept
  evidenceInspected: [diff]
  reasons: [ok]
  missingEvidence: []
  requiredFixes: []
  residualRisk: []
  confidence: banana
"""
        )
        result = scorecard.score(path)
        self.assertFalse(result["ok"])
        self.assertTrue(any("invalid review.confidence" in err for err in result["errors"]))

    def test_pipeline_dependency_cycle_is_error_and_prefix_overlap_warns(self):
        path = self.write_temp(
            """
pipeline:
  id: cycle
lanes:
  - id: lane-a
    role: implementation
    dependsOn:
      - lane-b
    parallelWith: []
    writeSet:
      - src/a/**
    environmentProfile: project-default
    reportFormat: typed_handoff_v1
    requiredVerification:
      - npm test
  - id: lane-b
    role: implementation
    dependsOn:
      - lane-a
    parallelWith: []
    writeSet:
      - src/a/sub/**
    environmentProfile: project-default
    reportFormat: typed_handoff_v1
    requiredVerification:
      - npm test
"""
        )
        result = pipeline.validate(path)
        self.assertFalse(result["ok"])
        self.assertTrue(any("dependency cycle" in err for err in result["errors"]))
        self.assertTrue(any("write-set overlap" in warn for warn in result["warnings"]))

    def test_pipeline_two_space_list_indent_and_unknown_references_are_checked(self):
        path = self.write_temp(
            """
pipeline:
  id: indent2
lanes:
  - id: lane-a
    role: implementation
    dependsOn:
      - ghost-lane
    parallelWith:
      - ghost-peer
    writeSet:
      - src/a/**
    environmentProfile: project-default
    reportFormat: typed_handoff_v1
    requiredVerification:
      - npm test
"""
        )
        result = pipeline.validate(path)
        self.assertFalse(result["ok"])
        self.assertTrue(any("dependsOn unknown lane ghost-lane" in err for err in result["errors"]))
        self.assertTrue(any("parallelWith unknown lane ghost-peer" in err for err in result["errors"]))

    def test_bundled_templates_validate(self):
        self.assertTrue(scorecard.score(ROOT / "skills/ceo-thread-orchestrator/templates/typed_handoff.yaml")["ok"])
        self.assertTrue(scorecard.score(ROOT / "skills/ceo-thread-orchestrator/templates/review_handoff.yaml")["ok"])
        result = pipeline.validate(ROOT / "skills/ceo-thread-orchestrator/templates/pipeline.yaml")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["laneCount"], 4)


if __name__ == "__main__":
    unittest.main()
