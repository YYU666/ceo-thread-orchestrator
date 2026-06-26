#!/usr/bin/env python3
"""Static smoke-eval harness for CEO Flow prompt coverage.

This script does not call an LLM and does not judge model behavior. It validates
that smoke cases are well-formed and that the skill/reference corpus contains the
policy terms each case is meant to exercise. Use it as a cheap regression guard
before human/agent forward testing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

DEFAULT_CASES = Path("examples/smoke-eval-cases.json")
DEFAULT_CORPUS = [
    Path("skills/ceo-thread-orchestrator/SKILL.md"),
    Path("skills/ceo-thread-orchestrator/references"),
    Path("examples/smoke-prompts.md"),
]

REQUIRED_CASE_FIELDS = {
    "id",
    "title",
    "prompt",
    "expected_labels",
    "forbidden_labels",
    "coverage_terms",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iter_markdown_files(path: Path) -> Iterable[Path]:
    if path.is_dir():
        yield from sorted(path.rglob("*.md"))
    elif path.exists():
        yield path


def load_corpus(root: Path, paths: List[Path]) -> str:
    chunks: List[str] = []
    for rel in paths:
        path = root / rel
        for file in iter_markdown_files(path):
            chunks.append(f"\n\n--- FILE: {file.relative_to(root)} ---\n")
            chunks.append(read_text(file))
    return "".join(chunks).lower()


def validate_case(case: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    missing = REQUIRED_CASE_FIELDS - set(case)
    if missing:
        errors.append(f"missing fields: {', '.join(sorted(missing))}")
    for field in ["id", "title", "prompt"]:
        if not isinstance(case.get(field), str) or not case.get(field, "").strip():
            errors.append(f"{field} must be a non-empty string")
    for field in ["expected_labels", "forbidden_labels", "coverage_terms"]:
        value = case.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            errors.append(f"{field} must be a list of non-empty strings")
    if isinstance(case.get("coverage_terms"), list) and not case.get("coverage_terms"):
        errors.append("coverage_terms must not be empty")
    return errors


def evaluate(root: Path, cases_path: Path, corpus_paths: List[Path]) -> Dict[str, Any]:
    raw_cases = json.loads(read_text(cases_path))
    if not isinstance(raw_cases, list):
        raise ValueError("smoke cases file must contain a JSON array")
    corpus = load_corpus(root, corpus_paths)
    results = []
    passed = 0
    for case in raw_cases:
        if not isinstance(case, dict):
            results.append({"id": "<invalid>", "ok": False, "errors": ["case must be an object"]})
            continue
        errors = validate_case(case)
        missing_terms = [term for term in case.get("coverage_terms", []) if term.lower() not in corpus]
        if missing_terms:
            errors.append("coverage terms absent from corpus: " + ", ".join(missing_terms))
        ok = not errors
        if ok:
            passed += 1
        results.append({
            "id": case.get("id", "<missing>"),
            "title": case.get("title", "<missing>"),
            "ok": ok,
            "errors": errors,
        })
    return {
        "ok": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CEO Flow smoke-eval cases against local skill docs.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES, help="Path to smoke-eval JSON cases")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--json", action="store_true", help="Emit JSON result")
    args = parser.parse_args()

    root = args.root.resolve()
    cases_path = args.cases if args.cases.is_absolute() else root / args.cases
    result = evaluate(root, cases_path, DEFAULT_CORPUS)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if result["ok"] else "FAIL"
        print(f"smoke-eval: {status} ({result['passed']}/{result['total']} cases)")
        for item in result["results"]:
            marker = "PASS" if item["ok"] else "FAIL"
            print(f"- {marker} {item['id']}: {item.get('title', '')}")
            for error in item.get("errors", []):
                print(f"  - {error}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
