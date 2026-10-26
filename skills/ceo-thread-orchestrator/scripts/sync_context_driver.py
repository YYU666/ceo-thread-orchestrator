#!/usr/bin/env python3
"""Read-only Zhixia sync at explicit boundaries; durable at-most-once packet emission."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import atomic_state
import context_governor

CONTROL = Path.home() / ".codex/skills/zhixia-local-docs/scripts/codex-control-mcp.cjs"
BOUNDARIES = {"startup", "before_dispatch", "after_accepted_refresh"}


def invoke_sync(request):
    # Use the installed control adapter: sync_context is not a low-level Runtime operation.
    code = "const fs=require('fs');const a=JSON.parse(fs.readFileSync(0,'utf8'));const m=require(process.argv[1]);Promise.resolve(m.callTool('sync_context',a)).then(r=>process.stdout.write(JSON.stringify(r))).catch(()=>process.exit(2));"
    done = subprocess.run(["node", "-e", code, str(CONTROL)], input=json.dumps(request),
                          capture_output=True, text=True, timeout=45, check=False)
    if done.returncode or len(done.stdout.encode()) > 48000:
        raise ValueError("sync_transport_unavailable")
    return json.loads(done.stdout)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 600


def query_key(goal, query_type):
    data = json.dumps([query_type, goal.strip()], ensure_ascii=False, separators=(",", ":"))
    return "query-" + hashlib.sha256(data.encode()).hexdigest()


def validate_packet(packet, workspace, project_id, query, budget):
    valid, _, _ = context_governor.inspect_control_structure(packet, max_bytes=48000)
    if not valid or not isinstance(packet, dict):
        raise ValueError("sync_packet_invalid")
    if context_governor.find_forbidden_payload(packet) or context_governor.find_forbidden_takeover_content(packet):
        raise ValueError("sync_forbidden_payload")
    if (packet.get("schemaVersion") != "zhixia.sync_context.v1"
            or packet.get("operation") != "sync_context"
            or packet.get("readOnly") is not True or packet.get("writeAuthority") is not False
            or packet.get("workspace") != workspace or packet.get("contextQueryKey") != query):
        raise ValueError("sync_envelope_mismatch")
    identity = packet.get("projectIdentity")
    if (not isinstance(identity, dict) or identity.get("projectId") != project_id
            or identity.get("canonicalRoot") != workspace):
        raise ValueError("sync_project_identity_mismatch")
    if packet.get("status") == "stale":
        raise ValueError("sync_stale")
    if (packet.get("memoryMode") != "app_owned_memory_core"
            or packet.get("authorityVerification") != "app_owned_verified"
            or packet.get("current") is not True or packet.get("recoveryReady") is not True
            or not isinstance(packet.get("scanBinding"), dict)
            or packet["scanBinding"].get("matched") is not True
            or not nonempty(packet["scanBinding"].get("authorizedCheckpointId"))
            or not re.fullmatch(r"context-[a-zA-Z0-9_-]{1,180}", str(packet.get("contextGenerationId", "")))):
        raise ValueError("sync_authority_invalid")
    items, refs = packet.get("items"), packet.get("sourceRefs")
    count, estimate = packet.get("returnedCount"), packet.get("tokenEstimate")
    if (not isinstance(items, list) or not isinstance(refs, list) or type(count) is not int
            or type(estimate) is not int or not 0 <= estimate <= budget):
        raise ValueError("sync_payload_invalid")
    if packet["status"] == "unchanged":
        if items or refs or count or estimate:
            raise ValueError("unchanged_contains_payload")
        return
    if packet["status"] != "ready_new" or not items or not refs or count < len(items) or not estimate:
        raise ValueError("sync_empty_or_unknown")
    for item in items:
        if (not isinstance(item, dict) or item.get("projectId") != project_id
                or str(item.get("layer", "")).lower() not in {"hot", "warm"}):
            raise ValueError("sync_item_scope_invalid")
        refs = refs + item.get("sourceRefs", [])
    for ref in refs:
        if not isinstance(ref, dict) or ref.get("projectId") != project_id:
            raise ValueError("sync_source_scope_invalid")
        path = ref.get("path")
        if not isinstance(path, str) or not path or "://" in path:
            raise ValueError("sync_source_path_invalid")
        resolved = (Path(workspace) / path).resolve()
        if not resolved.is_relative_to(Path(workspace)):
            raise ValueError("sync_source_path_escape")


def run(event, state_path, invoke=invoke_sync):
    result = {"schema": "ceo_sync_context_receipt_v1", "allowContextInjection": False,
              "allowProjectToolCalls": False, "allowProviderCalls": False,
              "writeAuthority": False, "programGoalBlocked": False,
              "hostTriggerVerified": False, "lifecycleGatesUnchanged": True}
    try:
        if event.get("boundary") not in BOUNDARIES:
            raise ValueError("sync_boundary_not_supported")
        for key in ("taskId", "projectId", "eventId", "taskGoal", "workspace"):
            if not nonempty(event.get(key)):
                raise ValueError("sync_event_incomplete")
        if not Path(event["workspace"]).is_absolute():
            raise ValueError("workspace_must_be_explicit_absolute")
        workspace = str(Path(event["workspace"]).resolve())
        if workspace != event["workspace"]:
            raise ValueError("workspace_must_be_canonical")
        budget = event.get("tokenBudget", 1200)
        if type(budget) is not int or not 800 <= budget <= 10000:
            raise ValueError("sync_budget_invalid")
        query_type = "project_resume" if event["boundary"] == "startup" else "task_dispatch"
        query = query_key(event["taskGoal"], query_type)
        key = hashlib.sha256(json.dumps([workspace, event["projectId"], event["taskId"]]).encode()).hexdigest()
        event_basis = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
        def update(state):
            valid, _, _ = context_governor.inspect_control_structure(state, max_bytes=512000)
            if not valid:
                raise ValueError("sync_ledger_invalid")
            ledger = state.setdefault("syncProjectsTasks", {}).setdefault(key, {"pairs": [], "events": {}})
            if event["eventId"] in ledger["events"]:
                if ledger["events"][event["eventId"]] != event_basis:
                    raise ValueError("sync_event_id_reused")
                result.update(status="duplicate_boundary", decision="skip")
                return state
            if len(ledger["events"]) >= 256 or len(ledger["pairs"]) >= 256:
                raise ValueError("sync_task_ledger_budget_exceeded")
            request = dict(workspace=workspace, taskGoal=event["taskGoal"], queryType=query_type,
                           tokenBudget=budget, limit=6, showApp=False)
            if ledger.get("generation"):
                request.update(knownContextGenerationId=ledger["generation"], knownContextQueryKey=ledger["query"])
            # Record failures too: unchanged boundary events must not become polling loops.
            ledger["events"][event["eventId"]] = event_basis
            try:
                packet = invoke(request)
                validate_packet(packet, workspace, event["projectId"], query, budget)
                pair = [packet["contextGenerationId"], packet["contextQueryKey"]]
                if packet["status"] == "unchanged" and pair not in ledger["pairs"]:
                    raise ValueError("unchanged_without_prior_emission")
                if pair in ledger["pairs"]:
                    result.update(status="unchanged", decision="skip")
                else:
                    ledger["pairs"].append(pair)
                    result.update(status="ready_new", decision="emit", packet=packet,
                                  allowContextInjection=True)
                ledger.update(generation=pair[0], query=pair[1])
            except Exception:
                result.update(status="stale_or_unavailable", decision="block",
                              nextAction="inspect_exact_authority_at_next_safe_boundary")
            return state
        atomic_state.locked_update_json(Path(state_path), update)
        return result
    except Exception:
        result.pop("packet", None)
        return result | {"allowContextInjection": False, "decision": "block",
                         "status": "sync_control_or_durability_unavailable",
                         "nextAction": "reconcile_sync_control_state_without_replaying_injection"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event", type=Path)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    try:
        event = context_governor.read_json(args.event, max_bytes=16000)
    except Exception:
        print(json.dumps({"decision": "block", "status": "invalid_sync_event",
                          "allowContextInjection": False, "writeAuthority": False}))
        return 2
    result = run(event, args.state)
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result["decision"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
