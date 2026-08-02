from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "skills" / "ceo-thread-orchestrator" / "references" / "visual-evidence.md"


class VisualTransportPolicyTests(unittest.TestCase):
    def test_view_image_is_not_treated_as_zero_payload_local_inspection(self):
        reference = REFERENCE.read_text(encoding="utf-8")
        self.assertIn("`view_image` is not a zero-payload local viewer", reference)
        self.assertIn("Do not call `view_image`", reference)
        self.assertIn("Never batch or loop multiple `view_image`/`image(...)` results", reference)
        self.assertIn("Visual transport mode: zero-payload-local-analysis | bounded-model-vision", reference)
        self.assertIn("Model-visible image budget: 0 by default", reference)

    def test_bounded_model_vision_is_short_lived_non_forked_and_one_image(self):
        reference = REFERENCE.read_text(encoding="utf-8")
        self.assertIn("fresh short-lived visual worker with no forked parent context", reference)
        self.assertIn("recommended below 800 KB", reference)
        self.assertIn("Use at most one model-visible image per turn", reference)
        self.assertIn("Do not forward them to subagents", reference)
        self.assertIn("even when the session is below 50 MB", reference)

    def test_visual_transport_smoke_cases_are_present(self):
        cases = json.loads((ROOT / "examples" / "smoke-eval-cases.json").read_text(encoding="utf-8"))
        ids = {case["id"] for case in cases}
        self.assertTrue(
            {
                "view-image-is-model-visible-transport",
                "bounded-model-vision-short-lived-worker",
                "user-image-not-relayed-to-subagent",
                "visual-payload-growth-below-50mb-fuses",
            }.issubset(ids)
        )

    def test_main_skill_exposes_visual_transport_receipt(self):
        skill = (ROOT / "skills" / "ceo-thread-orchestrator" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Treat `view_image`, `image(...)`", skill)
        self.assertIn("Visual transport mode: zero-payload-local-analysis | bounded-model-vision", skill)
        self.assertIn("Visual transport receipt: mode / modelVisibleImagesUsed", skill)


if __name__ == "__main__":
    unittest.main()
