#!/usr/bin/env python3
"""Emit a bounded CEO Flow/Zhixia/CMMD compatibility diagnosis.

The doctor is intentionally read-only.  It does not launch Electron, initialize
Memory Core, start CMMD, mutate project memory, or claim behavioral readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[3]
SOURCE_SKILL = SCRIPT.parents[1]
HASH_EXCLUDES = {"__pycache__", ".DS_Store"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str | None:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError:
        return None


def tree_sha256(root: Path) -> tuple[str | None, int]:
    if not root.is_dir():
        return None, 0
    rows: list[bytes] = []
    count = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or any(part in HASH_EXCLUDES for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        digest = file_sha256(path)
        if digest is None:
            continue
        rows.append(f"{rel}\0{digest}\n".encode("utf-8"))
        count += 1
    return sha256_bytes(b"".join(rows)), count


def run_git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def normalize_path(path: Path) -> str:
    return os.path.normcase(os.path.realpath(path))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def project_identity(canonical_root: Path, workspace_root: Path, project_id: str | None) -> dict[str, Any]:
    canonical = Path(os.path.realpath(canonical_root))
    workspace = Path(os.path.realpath(workspace_root))
    remote = run_git(canonical, "config", "--get", "remote.origin.url") or "local-only"
    git_top = run_git(canonical, "rev-parse", "--show-toplevel")
    baseline = run_git(workspace, "rev-parse", "HEAD") or run_git(canonical, "rev-parse", "HEAD")
    repo_material = {"canonicalRoot": normalize_path(canonical), "remote": remote}
    canonical_repo_id = "repo_" + sha256_bytes(canonical_json(repo_material).encode("utf-8"))[:24]
    resolved_project_id = project_id or "project_" + sha256_bytes(canonical_repo_id.encode("utf-8"))[:24]
    envelope = {
        "projectId": resolved_project_id,
        "canonicalRepoId": canonical_repo_id,
        "canonicalRoot": str(canonical),
        "worktreeRoot": str(workspace),
        "baselineHead": baseline,
    }
    envelope["projectIdentitySha256"] = sha256_bytes(canonical_json(envelope).encode("utf-8"))
    envelope["workspaceIsCanonical"] = normalize_path(canonical) == normalize_path(workspace)
    envelope["gitTopLevel"] = git_top
    return envelope


def iso_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("memory result must be a JSON object")
    return value


def probe_memory(helper: Path, project_root: Path, token_budget: int) -> tuple[dict[str, Any] | None, str | None]:
    if not helper.is_file():
        return None, "zhixia_helper_missing"
    command = [
        "node", str(helper), str(project_root), "--runtime-context",
        "--task-goal", "CEO Flow stack readiness", "--query-type", "project_resume",
        "--token-budget", str(token_budget), "--limit", "6", "--json",
    ]
    try:
        result = subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, f"memory_probe_unavailable:{type(error).__name__}"
    if result.returncode != 0:
        return None, f"memory_probe_exit_{result.returncode}"
    try:
        return json.loads(result.stdout or ""), None
    except (json.JSONDecodeError, TypeError):
        return None, "memory_probe_invalid_json"


def memory_diagnostics(packet: dict[str, Any] | None, now: datetime, stale_days: int) -> dict[str, Any]:
    if packet is None:
        return {
            "reportedMemoryMode": None,
            "effectiveMemoryMode": "unavailable",
            "currentStateClaimAllowed": False,
            "recoveryReadyClaimAllowed": False,
            "diagnostics": ["memory_result_unavailable"],
        }
    fact_status = packet.get("memoryFactSidecar", {}).get("status")
    core_status = packet.get("memoryCoreSidecar", {}).get("status")
    diagnostics: list[str] = []
    unavailable = {None, "missing", "unavailable", "schema_unavailable", "sqlite_unavailable", "not_opened"}
    if fact_status in unavailable:
        diagnostics.append(f"memory_fact_sidecar_{fact_status or 'unknown'}")
    if core_status in unavailable:
        diagnostics.append(f"memory_core_sidecar_{core_status or 'unknown'}")

    ids: dict[str, int] = {}
    stale_refs: list[dict[str, Any]] = []
    threshold_seconds = stale_days * 86400
    for item in packet.get("items", []):
        item_id = item.get("id")
        if item_id:
            ids[item_id] = ids.get(item_id, 0) + 1
        for ref in item.get("sourceRefs", []):
            updated = iso_time(ref.get("updatedAt"))
            if updated and (now - updated.astimezone(timezone.utc)).total_seconds() > threshold_seconds:
                stale_refs.append({"id": item_id, "path": ref.get("path"), "updatedAt": ref.get("updatedAt")})
    duplicate_ids = sorted(item_id for item_id, count in ids.items() if count > 1)
    if duplicate_ids:
        diagnostics.append("duplicate_memory_item_ids")
    if stale_refs:
        diagnostics.append("stale_packet_claimed_current")
    sidecar_missing = fact_status in unavailable or core_status in unavailable
    effective_mode = "fallback_stale" if sidecar_missing or stale_refs else packet.get("memoryMode", "unknown")
    if packet.get("memoryMode") != effective_mode:
        diagnostics.append("provider_memory_mode_overridden_by_doctor")
    safe = effective_mode not in {"fallback_stale", "unavailable", "unknown"} and not duplicate_ids
    compact_refs = []
    for ref in packet.get("sourceRefs", [])[:12]:
        compact_refs.append({
            key: ref.get(key)
            for key in ("kind", "path", "hash", "sha256", "updatedAt")
            if ref.get(key) is not None
        })
    return {
        "reportedMemoryMode": packet.get("memoryMode"),
        "effectiveMemoryMode": effective_mode,
        "memoryFactSidecarStatus": fact_status,
        "memoryCoreSidecarStatus": core_status,
        "duplicateItemIds": duplicate_ids,
        "staleSourceRefs": stale_refs[:12],
        "currentStateClaimAllowed": safe,
        "recoveryReadyClaimAllowed": safe and packet.get("recoveryReady") is True,
        "diagnostics": diagnostics,
        "sourceRefs": compact_refs,
    }


def cmmd_diagnostics(control_path: Path | None, schema_root: Path) -> dict[str, Any]:
    schema_hashes = {}
    if schema_root.is_dir():
        for path in sorted(schema_root.glob("*.schema.json")):
            schema_hashes[path.name] = file_sha256(path)
    if control_path is None:
        return {
            "controlStatus": "unavailable",
            "skippedReason": "cmmd_control_path_not_configured",
            "R0Ready": False,
            "R1Ready": False,
            "schemaHashes": schema_hashes,
        }
    exists = control_path.is_file()
    return {
        "controlStatus": "available_unprobed" if exists else "unavailable",
        "controlPath": str(control_path),
        "skippedReason": "doctor_does_not_start_or_probe_cmmd" if exists else "cmmd_control_missing",
        "R0Ready": False,
        "R1Ready": False,
        "schemaHashes": schema_hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only CEO Flow stack doctor")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--canonical-root", type=Path)
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--project-id")
    parser.add_argument("--ceoflow-skill", type=Path, default=SOURCE_SKILL)
    parser.add_argument("--installed-skill", type=Path, default=Path.home() / ".codex" / "skills" / "ceo-thread-orchestrator")
    parser.add_argument("--zhixia-skill", type=Path, default=Path.home() / ".codex" / "skills" / "zhixia-local-docs")
    parser.add_argument("--cmmd-control", type=Path, default=Path(os.environ["CMMD_CONTROL_PATH"]) if os.environ.get("CMMD_CONTROL_PATH") else None)
    parser.add_argument("--memory-json", type=Path, help="Use a captured bounded helper result instead of executing the helper")
    parser.add_argument("--no-memory-probe", action="store_true")
    parser.add_argument("--token-budget", type=int, default=800)
    parser.add_argument("--stale-days", type=int, default=7)
    parser.add_argument("--now", help="ISO timestamp for deterministic testing")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when current/recovery claims are unsafe")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    canonical_root = (args.canonical_root or project_root).resolve()
    workspace_root = (args.workspace_root or project_root).resolve()
    now = iso_time(args.now) or datetime.now(timezone.utc)
    source_hash, source_count = tree_sha256(args.ceoflow_skill.resolve())
    installed_hash, installed_count = tree_sha256(args.installed_skill.resolve())
    zhixia_helper = args.zhixia_skill.resolve() / "scripts" / "read-project-knowledge.cjs"

    packet = None
    probe_error = None
    if args.memory_json:
        try:
            packet = load_json(args.memory_json.resolve())
        except (OSError, ValueError, json.JSONDecodeError) as error:
            probe_error = f"memory_capture_invalid:{type(error).__name__}"
    elif not args.no_memory_probe:
        packet, probe_error = probe_memory(zhixia_helper, project_root, args.token_budget)
    memory = memory_diagnostics(packet, now, args.stale_days)
    if probe_error:
        memory["probeError"] = probe_error

    manifest_path = REPO_ROOT / ".codex-plugin" / "plugin.json"
    manifest = load_json(manifest_path) if manifest_path.is_file() else {}
    identity = project_identity(canonical_root, workspace_root, args.project_id)
    cmmd = cmmd_diagnostics(args.cmmd_control.resolve() if args.cmmd_control else None, args.ceoflow_skill.resolve() / "schemas" / "cmmd")
    ceo_sync = bool(source_hash and installed_hash and source_hash == installed_hash)
    result = {
        "schema": "ceoflow.stack_doctor.v1",
        "generatedAt": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "readOnly": True,
        "projectIdentity": identity,
        "ceoFlow": {
            "version": manifest.get("version", "unknown"),
            "sourceSkill": str(args.ceoflow_skill.resolve()),
            "sourceHash": source_hash,
            "sourceFileCount": source_count,
            "installedSkill": str(args.installed_skill.resolve()),
            "installedHash": installed_hash,
            "installedFileCount": installed_count,
            "installedMatchesSource": ceo_sync,
        },
        "zhixia": {
            "skillStatus": "available" if args.zhixia_skill.is_dir() else "unavailable",
            "skillHash": tree_sha256(args.zhixia_skill.resolve())[0],
            "helperStatus": "available" if zhixia_helper.is_file() else "unavailable",
            "helperHash": file_sha256(zhixia_helper),
            "memory": memory,
        },
        "cmmd": cmmd,
        "readiness": {
            "codexInternal": "ready" if ceo_sync else "revise",
            "memoryCurrent": "ready" if memory["currentStateClaimAllowed"] else "blocked",
            "projectRecovery": "ready" if memory["recoveryReadyClaimAllowed"] else "partial",
            "cmmdR0": "unverified",
            "cmmdR1": "blocked",
            "skippedReasons": [
                reason for reason in [probe_error, cmmd.get("skippedReason")] if reason
            ],
        },
        "claims": {
            "staticChecksProveBehavior": False,
            "recoveryReady": memory["recoveryReadyClaimAllowed"],
            "cmmdR1Enabled": False,
        },
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"CEO Flow stack doctor: codexInternal={result['readiness']['codexInternal']} memory={result['readiness']['memoryCurrent']} recovery={result['readiness']['projectRecovery']} cmmdR1=blocked")
        for item in memory.get("diagnostics", []):
            print(f"- memory diagnostic: {item}")
        for reason in result["readiness"]["skippedReasons"]:
            print(f"- skipped: {reason}")
    return 2 if args.strict and (not ceo_sync or not memory["currentStateClaimAllowed"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
