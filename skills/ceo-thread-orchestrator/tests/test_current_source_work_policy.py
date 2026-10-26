from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"


class CurrentSourceWorkPolicyTests(unittest.TestCase):
    def test_stale_memory_does_not_mean_global_source_freeze(self) -> None:
        for name in (
            "ceo-autopilot.md",
            "context-governance.md",
            "state-schema.md",
            "zhixia-app-owned-governance.md",
        ):
            with self.subTest(reference=name):
                text = (REFERENCES / name).read_text(encoding="utf-8")
                self.assertIn("current source work" if name == "ceo-autopilot.md" else "current_source_work", text)
                self.assertIn("memory", text.lower())
        autopilot = (REFERENCES / "ceo-autopilot.md").read_text(encoding="utf-8")
        self.assertNotIn("must not exit directly into product implementation from the old CEO thread", autopilot)
        governance = (REFERENCES / "context-governance.md").read_text(encoding="utf-8")
        self.assertIn("A frozen old task", governance)
        self.assertIn("allowProviderCalls=false", governance)


if __name__ == "__main__":
    unittest.main()
