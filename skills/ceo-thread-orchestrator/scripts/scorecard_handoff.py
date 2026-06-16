#!/usr/bin/env python3
"""Lightweight CEO Flow handoff scorecard.

Checks structured worker/review reports for the minimum evidence CEO Flow needs
before accept/revise/block. No third-party YAML parser is required.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


IMPLEMENTATION_KEYS = (
    "schema",
    "laneId",
    "status",
    "summary",
    "filesChanged",
    "writeSetCompliant",
    "commandsRun",
    "risks",
    "recommendedAction",
)

REVIEW_KEYS = (
    "schema",
    "laneId",
    "decision",
    "evidenceInspected",
    "reasons",
    "missingEvidence",
    "requiredFixes",
    "residualRisk",
    "confidence",
)

VALID_STATUS = {"complete", "partial", "blocked", "approval_stalled", "failed"}
VALID_DECISION = {"accept", "revise", "block", "supersede"}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text()


def has_key(text: str, key: str) -> bool:
    return re.search(rf"(?m)^\s*{re.escape(key)}\s*:", text) is not None


def scalar(text: str, key: str) -> str | None:
    m = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", text)
    if not m:
        return None
    return m.group(1).strip().strip("'\"")


def score(path: Path) -> dict[str, object]:
    text = read_text(path)
    errors: list[str] = []
    warnings: list[str] = []

    schema = scalar(text, "schema") or ""
    is_review = "review_handoff_v1" in schema or has_key(text, "decision")
    required = REVIEW_KEYS if is_review else IMPLEMENTATION_KEYS

    for key in required:
        if not has_key(text, key):
            errors.append(f"missing required key: {key}")

    if is_review:
        decision = scalar(text, "decision")
        if decision and decision not in VALID_DECISION:
            errors.append(f"invalid decision: {decision}")
    else:
        status = scalar(text, "status")
        if status and status not in VALID_STATUS:
            errors.append(f"invalid status: {status}")

        write_set = scalar(text, "writeSetCompliant")
        if write_set and write_set.lower() not in {"true", "false"}:
            warnings.append("writeSetCompliant should be true or false")
        if write_set and write_set.lower() == "false":
            errors.append("writeSetCompliant is false; CEO must revise/block or inspect exception")

    if "not_run" in text and not re.search(r"(?i)not[-_ ]run reason|reason", text):
        warnings.append("verification contains not_run but no obvious reason")

    if re.search(r"(?i)\bdone\b", text) and not has_key(text, "commandsRun"):
        errors.append("bare done-style report without commandsRun evidence")

    return {
        "path": str(path),
        "schema": schema or "unknown",
        "type": "review" if is_review else "implementation",
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CEO Flow handoff scorecard checks.")
    parser.add_argument("path", type=Path, help="Path to typed handoff/review handoff")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    result = score(args.path)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Handoff: {result['path']}")
        print(f"Type: {result['type']}")
        print(f"Schema: {result['schema']}")
        print(f"OK: {result['ok']}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        for error in result["errors"]:
            print(f"ERROR: {error}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
