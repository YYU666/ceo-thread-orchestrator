#!/usr/bin/env python3
"""Lightweight CEO Flow pipeline contract validator.

This script intentionally avoids third-party dependencies. It performs a
conservative text/shape validation that works for the bundled YAML templates and
simple project pipeline files. It is a scorecard helper, not a workflow engine.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_TOP_KEYS = ("pipeline", "lanes")
REQUIRED_LANE_KEYS = (
    "id",
    "role",
    "dependsOn",
    "writeSet",
    "environmentProfile",
    "reportFormat",
    "requiredVerification",
)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text()


def line_has_key(text: str, key: str) -> bool:
    return re.search(rf"(?m)^\s*{re.escape(key)}\s*:", text) is not None


def extract_lanes(text: str) -> list[dict[str, object]]:
    lanes_match = re.search(r"(?ms)^lanes\s*:\s*(.*?)(?:\n\S|\Z)", text)
    if not lanes_match:
        return []

    block = lanes_match.group(1)
    lane_chunks = re.split(r"(?m)^\s*-\s+id\s*:\s*", block)
    lanes: list[dict[str, object]] = []

    for chunk in lane_chunks[1:]:
        first_line, _, rest = chunk.partition("\n")
        lane_id = first_line.strip().strip("'\"")
        lane_text = f"id: {lane_id}\n{rest}"
        lane = {"id": lane_id, "_text": lane_text}
        lanes.append(lane)

    return lanes


def extract_inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return []
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]


def extract_depends(lane_text: str) -> list[str]:
    m = re.search(r"(?m)^\s*dependsOn\s*:\s*(.*)$", lane_text)
    if not m:
        return []
    inline = extract_inline_list(m.group(1))
    if inline:
        return inline
    if m.group(1).strip() == "[]":
        return []

    deps: list[str] = []
    after = lane_text[m.end() :]
    for line in after.splitlines():
        if re.match(r"^\s{4,}\-\s+", line):
            deps.append(re.sub(r"^\s*-\s*", "", line).strip().strip("'\""))
            continue
        if re.match(r"^\s{2,}\w", line):
            break
    return [dep for dep in deps if dep]


def extract_block_list(lane_text: str, key: str) -> list[str]:
    m = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*(.*)$", lane_text)
    if not m:
        return []

    inline = extract_inline_list(m.group(1))
    if inline:
        return inline
    if m.group(1).strip() == "[]":
        return []

    values: list[str] = []
    after = lane_text[m.end() :]
    for line in after.splitlines():
        if re.match(r"^\s{4,}-\s+", line):
            values.append(re.sub(r"^\s*-\s*", "", line).strip().strip("'\""))
            continue
        if re.match(r"^\s{2,}\w", line):
            break
    return [value for value in values if value]


def validate(path: Path) -> dict[str, object]:
    text = read_text(path)
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_TOP_KEYS:
        if not line_has_key(text, key):
            errors.append(f"missing top-level key: {key}")

    lanes = extract_lanes(text)
    if not lanes:
        errors.append("no lanes found; expected lanes with '- id: ...'")

    ids = [str(lane["id"]) for lane in lanes]
    duplicates = sorted({lane_id for lane_id in ids if ids.count(lane_id) > 1})
    for lane_id in duplicates:
        errors.append(f"duplicate lane id: {lane_id}")

    id_set = set(ids)
    write_set_owners: dict[str, str] = {}

    for lane in lanes:
        lane_id = str(lane["id"])
        lane_text = str(lane["_text"])

        for key in REQUIRED_LANE_KEYS:
            if not line_has_key(lane_text, key):
                errors.append(f"lane {lane_id}: missing key {key}")

        report_match = re.search(r"(?m)^\s*reportFormat\s*:\s*(\S+)", lane_text)
        if report_match:
            report_format = report_match.group(1).strip("'\"")
            if report_format not in {"typed_handoff_v1", "review_handoff_v1"}:
                warnings.append(f"lane {lane_id}: unknown reportFormat {report_format}")

        for dep in extract_depends(lane_text):
            if dep not in id_set:
                errors.append(f"lane {lane_id}: dependsOn unknown lane {dep}")

        for pattern in extract_block_list(lane_text, "writeSet"):
            if not pattern or pattern.startswith("review "):
                continue
            if pattern in write_set_owners and write_set_owners[pattern] != lane_id:
                warnings.append(
                    f"write-set pattern {pattern!r} appears in lanes "
                    f"{write_set_owners[pattern]} and {lane_id}"
                )
            else:
                write_set_owners[pattern] = lane_id

    return {
        "path": str(path),
        "ok": not errors,
        "laneCount": len(lanes),
        "lanes": ids,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a CEO Flow pipeline contract.")
    parser.add_argument("path", type=Path, help="Path to pipeline.yaml/workflow.yaml")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    result = validate(args.path)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Pipeline: {result['path']}")
        print(f"OK: {result['ok']}")
        print(f"Lanes: {result['laneCount']} ({', '.join(result['lanes'])})")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        for error in result["errors"]:
            print(f"ERROR: {error}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
