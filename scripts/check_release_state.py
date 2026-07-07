#!/usr/bin/env python3
"""Check public release-state consistency for CEO Flow.

Main may carry development changes, but the plugin manifest should say so. A
plain released version such as `0.2.6` should have a matching git tag; otherwise
use a dev suffix such as `0.2.7-dev` until the release is frozen.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
DEV_SUFFIX = re.compile(r"[-.]dev\d*$|-(alpha|beta|rc)\d*$", re.IGNORECASE)


def git_tags() -> set[str]:
    try:
        output = subprocess.check_output(["git", "tag", "--list"], cwd=ROOT, text=True)
    except Exception:
        return set()
    return {line.strip() for line in output.splitlines() if line.strip()}


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    version = str(data.get("version", ""))
    if not version:
        print("ERROR: plugin manifest missing version")
        return 1
    if DEV_SUFFIX.search(version):
        print(f"release-state: development version {version}; matching tag not required")
        return 0
    expected = f"v{version}"
    tags = git_tags()
    if expected not in tags:
        print(f"ERROR: manifest version {version} has no matching git tag {expected}; use a dev suffix or create the release tag")
        return 1
    print(f"release-state: manifest version {version} matches tag {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
