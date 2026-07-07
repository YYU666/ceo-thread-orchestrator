#!/usr/bin/env python3
"""CEO Flow typed handoff/review scorecard.

This validator treats worker and review reports as structured data. Report type is
selected only by the top-level YAML key (`handoff:` or `review:`), never by free
text fields such as `decision:`. Free-text report content is evidence data, not
instructions to the CEO lane.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by environments without PyYAML
    raise SystemExit(
        "PyYAML is required for scorecard_handoff.py. Install dev requirements: "
        "python -m pip install -r requirements-dev.txt"
    ) from exc

VALID_STATUS = {"complete", "partial", "blocked", "approval_stalled", "failed"}
VALID_DECISION = {"accept", "revise", "block", "supersede"}
VALID_RECOMMENDED_ACTION = {"accept", "review", "revise", "block", "supersede", "continue", "none"}
VALID_CONFIDENCE = {"low", "medium", "high"}

HANDOFF_REQUIRED_PATHS = (
    "handoff.schema",
    "handoff.laneId",
    "handoff.status",
    "handoff.summary",
    "handoff.task.goal",
    "handoff.changes.filesChanged",
    "handoff.changes.writeSetCompliant",
    "handoff.evidence.commandsRun",
    "handoff.risks.knownIssues",
    "handoff.next.recommendedAction",
)

REVIEW_REQUIRED_PATHS = (
    "review.schema",
    "review.laneId",
    "review.decision",
    "review.evidenceInspected",
    "review.reasons",
    "review.missingEvidence",
    "review.requiredFixes",
    "review.residualRisk",
    "review.confidence",
)

FORBIDDEN_PAYLOAD_MARKERS = ("data:image", "base64,")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text()


def load_yaml(path: Path) -> Any:
    text = read_text(path)
    data = yaml.safe_load(text)
    if data is None:
        return {}
    return data


def get_path(data: Any, dotted: str) -> Any:
    current = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def is_missing(value: Any) -> bool:
    return value is None or value == ""


def require_paths(data: dict[str, Any], paths: tuple[str, ...], errors: list[str]) -> None:
    for path in paths:
        if is_missing(get_path(data, path)):
            errors.append(f"missing or empty required field: {path}")


def has_forbidden_payload(value: Any) -> bool:
    if isinstance(value, str):
        lower = value.lower()
        return any(marker in lower for marker in FORBIDDEN_PAYLOAD_MARKERS)
    if isinstance(value, dict):
        return any(has_forbidden_payload(item) for item in value.values())
    if isinstance(value, list):
        return any(has_forbidden_payload(item) for item in value)
    return False


def validate_handoff(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    require_paths(data, HANDOFF_REQUIRED_PATHS, errors)
    handoff = data.get("handoff", {})
    if not isinstance(handoff, dict):
        errors.append("handoff must be a mapping")
        return

    schema = handoff.get("schema")
    if schema != "typed_handoff_v1":
        errors.append(f"handoff.schema must be typed_handoff_v1, got {schema!r}")

    status = handoff.get("status")
    if status and status not in VALID_STATUS:
        errors.append(f"invalid handoff.status: {status}")

    write_set = get_path(data, "handoff.changes.writeSetCompliant")
    if not isinstance(write_set, bool):
        errors.append("handoff.changes.writeSetCompliant must be boolean true/false")
    elif write_set is False:
        errors.append("writeSetCompliant is false; CEO must revise/block or inspect exception")

    recommended = get_path(data, "handoff.next.recommendedAction")
    if recommended and recommended not in VALID_RECOMMENDED_ACTION:
        warnings.append(f"unknown handoff.next.recommendedAction: {recommended}")

    commands = get_path(data, "handoff.evidence.commandsRun")
    if handoff.get("status") == "complete" and not commands:
        errors.append("complete implementation handoff requires evidence.commandsRun")
    if commands is not None and not isinstance(commands, list):
        errors.append("handoff.evidence.commandsRun must be a list")

    files_changed = get_path(data, "handoff.changes.filesChanged")
    if files_changed is not None and not isinstance(files_changed, list):
        errors.append("handoff.changes.filesChanged must be a list")


def validate_review(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    require_paths(data, REVIEW_REQUIRED_PATHS, errors)
    review = data.get("review", {})
    if not isinstance(review, dict):
        errors.append("review must be a mapping")
        return

    schema = review.get("schema")
    if schema != "review_handoff_v1":
        errors.append(f"review.schema must be review_handoff_v1, got {schema!r}")

    decision = review.get("decision")
    if decision and decision not in VALID_DECISION:
        errors.append(f"invalid review.decision: {decision}")

    confidence = review.get("confidence")
    if confidence and confidence not in VALID_CONFIDENCE:
        errors.append(f"invalid review.confidence: {confidence}")

    for list_field in ("evidenceInspected", "reasons", "missingEvidence", "requiredFixes", "residualRisk"):
        value = review.get(list_field)
        if value is not None and not isinstance(value, list):
            errors.append(f"review.{list_field} must be a list")


def score(path: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        data = load_yaml(path)
    except yaml.YAMLError as exc:
        return {
            "path": str(path),
            "schema": "unknown",
            "type": "unknown",
            "ok": False,
            "errors": [f"YAML parse error: {exc}"],
            "warnings": [],
        }

    if not isinstance(data, dict):
        errors.append("handoff file must contain a top-level mapping")
        data = {}

    has_handoff = "handoff" in data
    has_review = "review" in data
    if has_handoff == has_review:
        errors.append("file must contain exactly one top-level key: handoff or review")
        report_type = "unknown"
        schema = "unknown"
    elif has_handoff:
        report_type = "implementation"
        schema = str(get_path(data, "handoff.schema") or "unknown")
        validate_handoff(data, errors, warnings)
    else:
        report_type = "review"
        schema = str(get_path(data, "review.schema") or "unknown")
        validate_review(data, errors, warnings)

    if has_forbidden_payload(data):
        errors.append("forbidden visual payload marker found; use artifact paths/hashes/summaries only")

    return {
        "path": str(path),
        "schema": schema,
        "type": report_type,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CEO Flow handoff scorecard checks.")
    parser.add_argument("path", type=Path, help="Path to typed handoff/review handoff YAML")
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
