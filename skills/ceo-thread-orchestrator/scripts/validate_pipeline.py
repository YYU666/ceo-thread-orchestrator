#!/usr/bin/env python3
"""CEO Flow pipeline contract validator.

Validates the machine-checkable parts of a CEO Flow `pipeline.yaml` contract:
required fields, lane references, dependency cycles, parallelWith references, and
obvious write-set overlap. This is a scorecard helper, not a workflow engine.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import PurePosixPath, Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by environments without PyYAML
    raise SystemExit(
        "PyYAML is required for validate_pipeline.py. Install dev requirements: "
        "python -m pip install -r requirements-dev.txt"
    ) from exc

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
VALID_REPORT_FORMATS = {"typed_handoff_v1", "review_handoff_v1"}
READ_ONLY_ROLES = {"review", "reviewer", "qa", "audit", "auditor", "product", "ux", "docs_review"}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text()


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(read_text(path)) or {}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_path_pattern(pattern: str) -> str:
    pattern = pattern.strip().replace("\\", "/").strip("'\"")
    while pattern.startswith("./"):
        pattern = pattern[2:]
    return re.sub(r"/+$", "", pattern)


def write_base(pattern: str) -> str:
    pattern = normalize_path_pattern(pattern)
    if not pattern:
        return ""
    parts = []
    for part in PurePosixPath(pattern).parts:
        if any(ch in part for ch in "*?["):
            break
        parts.append(part)
    base = "/".join(parts)
    if base:
        return base
    if pattern in {"*", "**", "**/*"}:
        return ""
    return pattern


def overlap(a: str, b: str) -> bool:
    a_norm = normalize_path_pattern(a)
    b_norm = normalize_path_pattern(b)
    if not a_norm or not b_norm:
        return True
    if a_norm == b_norm:
        return True
    a_base = write_base(a_norm)
    b_base = write_base(b_norm)
    if not a_base or not b_base:
        return True
    return a_base == b_base or a_base.startswith(b_base + "/") or b_base.startswith(a_base + "/")


def is_writing_lane(lane: dict[str, Any]) -> bool:
    role = str(lane.get("role", "")).lower()
    report_format = str(lane.get("reportFormat", ""))
    return bool(as_list(lane.get("writeSet"))) and report_format != "review_handoff_v1" and role not in READ_ONLY_ROLES


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node: str) -> list[str] | None:
        visiting.add(node)
        stack.append(node)
        for dep in graph.get(node, []):
            if dep not in graph:
                continue
            if dep in visiting:
                idx = stack.index(dep)
                return stack[idx:] + [dep]
            if dep not in visited:
                cycle = dfs(dep)
                if cycle:
                    return cycle
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for node in graph:
        if node not in visited:
            cycle = dfs(node)
            if cycle:
                return cycle
    return None


def validate(path: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        data = load_yaml(path)
    except yaml.YAMLError as exc:
        return {
            "path": str(path),
            "ok": False,
            "laneCount": 0,
            "lanes": [],
            "errors": [f"YAML parse error: {exc}"],
            "warnings": [],
        }

    if not isinstance(data, dict):
        errors.append("pipeline file must contain a top-level mapping")
        data = {}

    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(f"missing top-level key: {key}")

    lanes_raw = data.get("lanes", [])
    if not isinstance(lanes_raw, list) or not lanes_raw:
        errors.append("lanes must be a non-empty list")
        lanes: list[dict[str, Any]] = []
    else:
        lanes = [lane for lane in lanes_raw if isinstance(lane, dict)]
        if len(lanes) != len(lanes_raw):
            errors.append("every lane entry must be a mapping")

    ids = [str(lane.get("id", "")) for lane in lanes]
    for index, lane_id in enumerate(ids):
        if not lane_id:
            errors.append(f"lane at index {index}: missing id")
    duplicates = sorted({lane_id for lane_id in ids if lane_id and ids.count(lane_id) > 1})
    for lane_id in duplicates:
        errors.append(f"duplicate lane id: {lane_id}")

    id_set = {lane_id for lane_id in ids if lane_id}
    dependency_graph: dict[str, list[str]] = {}

    for lane in lanes:
        lane_id = str(lane.get("id", "<missing>"))
        for key in REQUIRED_LANE_KEYS:
            if key not in lane:
                errors.append(f"lane {lane_id}: missing key {key}")

        report_format = lane.get("reportFormat")
        if report_format and report_format not in VALID_REPORT_FORMATS:
            warnings.append(f"lane {lane_id}: unknown reportFormat {report_format}")

        depends = [str(dep) for dep in as_list(lane.get("dependsOn")) if str(dep)]
        parallel = [str(peer) for peer in as_list(lane.get("parallelWith")) if str(peer)]
        dependency_graph[lane_id] = depends

        for dep in depends:
            if dep not in id_set:
                errors.append(f"lane {lane_id}: dependsOn unknown lane {dep}")
        for peer in parallel:
            if peer not in id_set:
                errors.append(f"lane {lane_id}: parallelWith unknown lane {peer}")
            if peer == lane_id:
                errors.append(f"lane {lane_id}: parallelWith references itself")

        for list_key in ("dependsOn", "parallelWith", "writeSet", "requiredVerification"):
            if list_key in lane and not isinstance(lane[list_key], list):
                errors.append(f"lane {lane_id}: {list_key} must be a list")

    cycle = find_cycle(dependency_graph)
    if cycle:
        errors.append("dependency cycle detected: " + " -> ".join(cycle))

    writing_lanes = [lane for lane in lanes if is_writing_lane(lane)]
    for i, lane_a in enumerate(writing_lanes):
        id_a = str(lane_a.get("id"))
        for lane_b in writing_lanes[i + 1 :]:
            id_b = str(lane_b.get("id"))
            for pattern_a in [str(p) for p in as_list(lane_a.get("writeSet")) if str(p)]:
                for pattern_b in [str(p) for p in as_list(lane_b.get("writeSet")) if str(p)]:
                    if overlap(pattern_a, pattern_b):
                        warnings.append(
                            f"write-set overlap between {id_a} ({pattern_a}) and {id_b} ({pattern_b})"
                        )

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
