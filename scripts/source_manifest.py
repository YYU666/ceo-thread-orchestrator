#!/usr/bin/env python3
"""Build or verify a deterministic source/candidate SHA-256 manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

IGNORED_PARTS = {"__pycache__", ".git"}
IGNORED_SUFFIXES = {".pyc"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest(root: Path) -> dict[str, str]:
    resolved = root.resolve()
    files: dict[str, str] = {}
    for path in sorted(resolved.rglob("*")):
        if IGNORED_PARTS.intersection(path.parts) or path.suffix in IGNORED_SUFFIXES:
            continue
        relative = path.relative_to(resolved).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            files[relative] = sha256_bytes(os.readlink(path).encode("utf-8", "surrogateescape"))
        elif stat.S_ISREG(mode):
            files[relative] = sha256_bytes(path.read_bytes())
    return files


def manifest_digest(files: dict[str, str]) -> str:
    return sha256_bytes(canonical_json(files))


def git_output(repo: Path, *args: str, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=not binary,
    )
    if completed.returncode != 0:
        stderr = completed.stderr if isinstance(completed.stderr, str) else completed.stderr.decode("utf-8", "replace")
        raise ValueError(f"git_command_failed:{' '.join(args)}:{stderr.strip()[:300]}")
    return completed.stdout


def git_candidate(repo: Path, files: dict[str, str], expected_head: str | None = None) -> dict[str, Any]:
    canonical_repo = Path(str(git_output(repo, "rev-parse", "--show-toplevel")).strip()).resolve()
    if canonical_repo != repo.resolve():
        raise ValueError("candidate_root_must_equal_git_toplevel")

    head = str(git_output(repo, "rev-parse", "HEAD")).strip()
    tree = str(git_output(repo, "rev-parse", "HEAD^{tree}")).strip()
    if expected_head and head != expected_head:
        raise ValueError("candidate_head_mismatch")

    status = str(git_output(repo, "status", "--porcelain=v1", "--untracked-files=all"))
    if status:
        raise ValueError("candidate_worktree_not_clean")

    tracked_raw = git_output(repo, "ls-files", "-z", binary=True)
    assert isinstance(tracked_raw, bytes)
    tracked_paths = sorted(
        path.decode("utf-8", "surrogateescape").replace(os.sep, "/")
        for path in tracked_raw.split(b"\0")
        if path
    )
    if tracked_paths != sorted(files):
        raise ValueError("candidate_manifest_does_not_match_tracked_files")

    tracked_files = {path: files[path] for path in tracked_paths}
    return {
        "schema": "ceo_git_candidate_v1",
        "headSha": head,
        "treeSha": tree,
        "clean": True,
        "trackedFileCount": len(tracked_paths),
        "trackedFilesSha256": manifest_digest(tracked_files),
    }


def build_result(
    root: Path,
    *,
    compare: Path | None = None,
    verify_self: bool = False,
    require_clean_git: bool = False,
    expected_head: str | None = None,
) -> dict[str, Any]:
    first = manifest(root)
    if verify_self and first != manifest(root):
        raise ValueError("source_manifest_nondeterministic")
    result: dict[str, Any] = {
        "schema": "ceo_source_manifest_v2",
        "root": str(root.resolve()),
        "fileCount": len(first),
        "manifestSha256": manifest_digest(first),
        "files": first,
    }
    if compare:
        second = manifest(compare)
        result["compareRoot"] = str(compare.resolve())
        result["compareManifestSha256"] = manifest_digest(second)
        result["equivalent"] = first == second
    if require_clean_git:
        result["gitCandidate"] = git_candidate(root, first, expected_head)
        result["candidateSha256"] = sha256_bytes(canonical_json({
            "manifestSha256": result["manifestSha256"],
            "gitCandidate": result["gitCandidate"],
        }))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--verify-self", action="store_true")
    parser.add_argument("--require-clean-git", action="store_true")
    parser.add_argument("--expected-head")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = build_result(
            args.root,
            compare=args.compare,
            verify_self=args.verify_self,
            require_clean_git=args.require_clean_git,
            expected_head=args.expected_head,
        )
    except ValueError as exc:
        print(json.dumps({"schema": "ceo_source_manifest_error_v1", "error": str(exc)}, sort_keys=True))
        return 2
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result.get("equivalent", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
