#!/usr/bin/env python3
"""Prepare relevant project-domain excerpts; never grant execution authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

import atomic_state
from context_ingress_gateway import canonical_sha256, safe_relative_path
from context_governor import find_forbidden_payload
from delivery_policy import unique_object


PROFILE_SCHEMA = "ceo_project_domain_v1"
STATE_SCHEMA = "ceo_project_domain_load_state_v1"
DEFAULT_PROFILE = ".ceo-flow/domain.json"
MAX_PROFILE_BYTES = 16 * 1024
MAX_DOCUMENT_BYTES = 64 * 1024
MAX_CONTEXT_BYTES = 12 * 1024
MAX_STATE_BYTES = 256 * 1024
MAX_ENTRIES = 32
MAX_SELECTED = 8
MAX_PREPARED = 256
PENDING_SPEC = "<!-- specification-pending -->"
IDENTIFIER = re.compile(r"[a-z][a-z0-9_-]{0,63}")
FORBIDDEN_PARTS = {".git", ".codex-knowledge", "sessions", "credentials", "keychain"}


def local_path(root: Path, relative: Any, suffix: str) -> Path:
    if not safe_relative_path(relative) or len(relative) > 512 or ":" in relative:
        raise ValueError("domain_path_invalid")
    parts = Path(relative).parts
    if not parts or FORBIDDEN_PARTS.intersection(parts) or Path(relative).suffix != suffix:
        raise ValueError("domain_path_invalid")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("domain_path_symlink")
    if not path.resolve().is_relative_to(root):
        raise ValueError("domain_path_escape")
    return path


def read_bounded(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("domain_file_too_large")
    return raw


def names(value: Any) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise ValueError("domain_selector_invalid")
    if any(not isinstance(item, str) or not IDENTIFIER.fullmatch(item) for item in value):
        raise ValueError("domain_selector_invalid")
    if len(set(value)) != len(value):
        raise ValueError("domain_selector_duplicate")
    return value


def validate_profile(profile: Any, root: Path) -> list[dict[str, Any]]:
    if not isinstance(profile, dict) or set(profile) != {"schema", "domain", "entries"}:
        raise ValueError("domain_profile_fields_invalid")
    if profile["schema"] != PROFILE_SCHEMA or not isinstance(profile["domain"], str) or not IDENTIFIER.fullmatch(profile["domain"]):
        raise ValueError("domain_profile_identity_invalid")
    entries = profile["entries"]
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise ValueError("domain_entry_count_invalid")
    ids = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "id", "kind", "path", "section", "workKinds", "topics", "required",
        }:
            raise ValueError("domain_entry_fields_invalid")
        if not isinstance(entry["id"], str) or not IDENTIFIER.fullmatch(entry["id"]) or entry["id"] in ids:
            raise ValueError("domain_entry_id_invalid")
        ids.add(entry["id"])
        if entry["kind"] not in {"rules", "spec"} or type(entry["required"]) is not bool:
            raise ValueError("domain_entry_kind_invalid")
        if entry["kind"] == "rules" and entry["required"]:
            raise ValueError("optional_domain_rule_cannot_be_required")
        if not isinstance(entry["section"], str) or not entry["section"].strip() or len(entry["section"]) > 120 or "\n" in entry["section"]:
            raise ValueError("domain_section_invalid")
        # Validate every pointer, but read bodies only for the selected entries.
        local_path(root, entry["path"], ".md")
        names(entry["workKinds"])
        names(entry["topics"])
    return entries


def uncomment(line: str, inside_comment: bool) -> tuple[str, bool, bool]:
    pieces, position, pending = [], 0, False
    while position < len(line):
        if inside_comment:
            end = line.find("-->", position)
            if end < 0:
                break
            inside_comment, position = False, end + 3
        else:
            start = line.find("<!--", position)
            if start < 0:
                pieces.append(line[position:])
                break
            pieces.append(line[position:start])
            pending = pending or line.startswith(PENDING_SPEC, start)
            inside_comment, position = True, start + 4
    ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
    return "".join(pieces).rstrip("\r\n") + ending, inside_comment, pending


def section_excerpt(raw: bytes, section: str, *, specification: bool = False) -> str:
    lines = raw.decode("utf-8").splitlines(keepends=True)
    headings, visible_lines, pending_lines = [], [], []
    fence = None
    inside_comment = False
    for index, line in enumerate(lines):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if marker and not inside_comment:
            run, tail = marker.groups()
            if fence is None:
                fence = (run[0], len(run))
            elif run[0] == fence[0] and len(run) >= fence[1] and not tail.strip():
                fence = None
            visible_lines.append(line)
            pending_lines.append(False)
            continue
        if fence is not None:
            visible_lines.append(line)
            pending_lines.append(False)
            continue
        started_in_comment = inside_comment
        visible, inside_comment, pending = uncomment(line, inside_comment)
        visible_lines.append(visible)
        pending_lines.append(pending)
        # Stripping a comment must not manufacture a heading from its hidden text.
        if not started_in_comment and re.match(r"^ {0,3}#{1,2}[ \t]+", line):
            heading = re.match(r"^ {0,3}(#{1,2})[ \t]+(.+)$", visible.rstrip("\r\n"))
            if heading:
                title = re.sub(r"[ \t]+#+[ \t]*$", "", heading[2]).strip()
                headings.append((index, len(heading[1]), title))
    selected = [position for position, (_, level, title) in enumerate(headings) if level == 2 and title == section]
    if len(selected) != 1:
        raise ValueError("domain_section_missing_or_ambiguous")
    position = selected[0]
    start = headings[position][0]
    end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
    if specification and any(pending_lines[start:end]):
        raise ValueError("project_specification_pending")
    body = "".join(visible_lines[start:end]).strip()
    if not "".join(visible_lines[start + 1:end]).strip():
        raise ValueError("domain_section_empty")
    return body


def result_base() -> dict[str, Any]:
    return {"schema": "ceo_project_domain_context_v1", "advisoryOnly": True,
            "authorityScope": "domain_guidance_only", "executionPolicyChanged": False,
            "context": [], "taskCard": {}, "warnings": [], "missingSpecs": []}


def prepare(workspace: Path, task_id: str, work_kind: str, topics: list[str],
            state_path: Path, *, profile_path: str = DEFAULT_PROFILE) -> dict[str, Any]:
    result = result_base()
    try:
        root = workspace.resolve()
        if not workspace.is_absolute() or str(workspace) != str(root) or not root.is_dir():
            raise ValueError("domain_workspace_not_canonical")
        if not isinstance(task_id, str) or not task_id.strip() or len(task_id) > 200:
            raise ValueError("domain_task_id_invalid")
        names([work_kind])
        names(topics)
        config = local_path(root, profile_path, ".json")
        if not config.exists():
            return {**result, "ok": True, "domainStatus": "not_configured"}
        profile_raw = read_bounded(config, MAX_PROFILE_BYTES)
        profile = json.loads(profile_raw, object_pairs_hook=unique_object)
        entries = validate_profile(profile, root)
        selected = [entry for entry in entries if work_kind in entry["workKinds"]
                    and set(topics).intersection(entry["topics"])]
        if len(selected) > MAX_SELECTED:
            raise ValueError("domain_selection_too_broad")
        if not selected:
            return {**result, "ok": True, "domainStatus": "not_applicable"}
        documents: dict[str, bytes] = {}
        references, excerpts = [], []
        for entry in selected:
            pointer = {key: entry[key] for key in ("id", "kind", "path", "section")}
            try:
                if entry["path"] not in documents:
                    documents[entry["path"]] = read_bounded(local_path(root, entry["path"], ".md"), MAX_DOCUMENT_BYTES)
                raw = documents[entry["path"]]
                body = section_excerpt(raw, entry["section"], specification=entry["kind"] == "spec")
                if find_forbidden_payload(body):
                    raise ValueError("domain_payload_forbidden_use_source_pointer")
                reference = {**pointer, "fileSha256": hashlib.sha256(raw).hexdigest(),
                             "excerptSha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}
                references.append(reference)
                excerpts.append({**reference, "text": body})
            except (OSError, ValueError) as exc:
                item = {**pointer, "reason": str(exc)[:160]}
                result["missingSpecs" if entry["required"] else "warnings"].append(item)
        result["taskCard"] = {"workspace": str(root), "domain": profile["domain"], "workKind": work_kind,
                              "topics": topics, "ruleRefs": [ref for ref in references if ref["kind"] == "rules"],
                              "specRefs": [ref for ref in references if ref["kind"] == "spec"]}
        if result["missingSpecs"]:
            return {**result, "ok": True, "domainStatus": "needs_specification"}
        if not excerpts:
            return {**result, "ok": True, "domainStatus": "optional_unavailable"}

        if state_path.exists() and state_path.stat().st_size > MAX_STATE_BYTES:
            raise ValueError("domain_state_too_large")
        state = atomic_state.read_confirmed_json(state_path)
        old_hash = atomic_state.state_sha256(state)
        if state and (set(state) != {"schema", "preparedByTask"} or state["schema"] != STATE_SCHEMA):
            raise ValueError("domain_state_schema_invalid")
        ledgers = state.get("preparedByTask", {})
        if not isinstance(ledgers, dict) or len(ledgers) > 128:
            raise ValueError("domain_state_ledger_invalid")
        for ledger in ledgers.values():
            if not isinstance(ledger, list) or len(ledger) > MAX_PREPARED or any(
                not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in ledger
            ):
                raise ValueError("domain_state_ledger_invalid")
        key = canonical_sha256({"workspace": str(root), "taskId": task_id})
        previous = set(ledgers.get(key, []))
        new = []
        for excerpt in excerpts:
            if excerpt["excerptSha256"] not in previous:
                new.append(excerpt)
                previous.add(excerpt["excerptSha256"])
        if len(previous) > MAX_PREPARED or (key not in ledgers and len(ledgers) >= 128):
            raise ValueError("domain_state_ledger_full")
        if len(json.dumps(new, ensure_ascii=False).encode("utf-8")) > MAX_CONTEXT_BYTES:
            raise ValueError("domain_context_too_large_narrow_topics")
        if new:
            ledgers[key] = sorted(previous)
            atomic_state.atomic_write_json(state_path, {"schema": STATE_SCHEMA, "preparedByTask": ledgers}, expected_sha256=old_hash)
        return {**result, "ok": True, "domainStatus": "prepared" if new else "references_only",
                "context": new, "profileSha256": hashlib.sha256(profile_raw).hexdigest()}
    except (OSError, ValueError, TypeError, RecursionError,
            atomic_state.StateConflictError, atomic_state.StateDurabilityError) as exc:
        return {**result_base(), "ok": False, "domainStatus": "unavailable",
                "reason": str(exc)[:160]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--work-kind", required=True)
    parser.add_argument("--topics", nargs="+", required=True)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.workspace, args.task_id, args.work_kind, args.topics,
                     args.state, profile_path=args.profile)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
