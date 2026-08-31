from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import context_ingress_gateway as gateway  # noqa: E402


def receipt(**overrides: object) -> dict:
    value = {
        "schema": gateway.SCHEMA,
        "taskId": "clean-ceo",
        "retainedContextTokens": 20_000,
        "threadHistoryMode": "recovery_packet_only",
        "fullThreadHistoryLoaded": False,
        "newFocusedReferences": [],
        "toolOutputs": [],
    }
    value.update(overrides)
    value["receiptSha256"] = gateway.receipt_sha256(value)
    return value


class ContextIngressGatewayTests(unittest.TestCase):
    def test_compact_clean_ingress_is_allowed(self) -> None:
        result = gateway.validate(receipt(), task_id="clean-ceo")
        self.assertTrue(result["ok"], result)

    def test_retained_context_above_30k_is_blocked(self) -> None:
        result = gateway.validate(
            receipt(retainedContextTokens=30_001), task_id="clean-ceo"
        )
        self.assertEqual(result["reason"], "clean_takeover_retained_context_limit")

    def test_same_reference_sha_cannot_be_loaded_twice(self) -> None:
        digest = "a" * 64
        result = gateway.validate(
            receipt(newFocusedReferences=[{"path": "docs/goal.md", "sha256": digest}]),
            task_id="clean-ceo",
            previously_loaded_reference_sha256s=[digest],
        )
        self.assertEqual(result["reason"], "duplicate_reference_sha_load")

    def test_only_one_focused_reference_may_enter_per_request(self) -> None:
        refs = [
            {"path": "docs/a.md", "sha256": "a" * 64},
            {"path": "docs/b.md", "sha256": "b" * 64},
        ]
        result = gateway.validate(
            receipt(newFocusedReferences=refs), task_id="clean-ceo"
        )
        self.assertEqual(result["reason"], "focused_reference_limit_exceeded")

    def test_full_history_and_raw_tool_output_are_rejected(self) -> None:
        result = gateway.validate(
            receipt(
                threadHistoryMode="full_read_thread",
                fullThreadHistoryLoaded=True,
                toolOutputs=[
                    {
                        "summaryTokens": 100,
                        "serializedBytes": 100,
                        "rawBytesIncluded": True,
                    }
                ],
            ),
            task_id="clean-ceo",
        )
        self.assertIn("full_thread_history_forbidden", result["errors"])
        self.assertIn("raw_tool_output_forbidden", result["errors"])

    def test_large_tool_output_requires_content_addressed_artifact(self) -> None:
        result = gateway.validate(
            receipt(
                toolOutputs=[
                    {
                        "summaryTokens": 100,
                        "serializedBytes": 20_000,
                        "rawBytesIncluded": False,
                    }
                ]
            ),
            task_id="clean-ceo",
        )
        self.assertEqual(result["reason"], "oversized_tool_output_requires_artifact")


if __name__ == "__main__":
    unittest.main()
