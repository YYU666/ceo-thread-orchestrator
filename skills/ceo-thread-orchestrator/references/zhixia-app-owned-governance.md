# Zhixia App-Owned Governance

Use this reference when CEO Flow coordinates with the formally installed `/Applications/知匣.app` app-owned Memory Runtime for bootstrap, resume, direction switching, worker dispatch, takeover, or context-pressure recovery.

## Design Card

Goal: make each CEO/worker task verify and refresh its own project memory binding with the app-owned Runtime, replacing long thread context with one bounded generation packet and keeping ordinary memory traffic out of Codex task delegation.

Affected files:

- `SKILL.md`: Critical Path requires direct app-owned Runtime verification before continuity-sensitive dispatch.
- `references/context-memory.md`: compact context router and ownership boundary.
- `references/context-governance.md`: strict verify -> exact scan -> refresh binding, freeze, takeover, and generation rules.
- `references/project-continuity.md`: exact identity, mandatory slots/pagination, receipts, and Warm Anchor.
- `references/memory-runtime.md`: provider hooks, budgets, precedent, and writeback lifecycle.
- `references/state-schema.md`: durable per-task injection ledger and refresh request records.
- `scripts/context_governor.py`: deterministic fail-closed evaluator and formal refresh request builder.
- `scripts/refresh_binding_driver.py`: the only integration driver for direct refresh, receipt/checkpoint validation, bounded verify, and lane resume.
- `tests/`: evaluator and direct-driver regression tests.

Non-goals:

- Do not modify product/provider/model/reasoning/permission code.
- Do not reseed or refresh authority from dirty or unaccepted files.
- Do not treat generated `.codex-knowledge` compatibility files as authority.
- Do not send full Runtime JSON, raw chats, old session bodies, images/base64, credentials, SQLite bodies, or complete logs through task cards or delegation messages.

## State Machine

At task start, resume, direction switch, and before worker/reviewer dispatch:

1. Call the app-owned route directly: `verify`, then `prepare_takeover` only when a replacement context packet is needed.
2. Accept injection only when all strict fields hold: `memoryMode=app_owned_memory_core`, `authorityVerification=app_owned_verified`, `current=true`, `recoveryReady=true`, `returnedCount>0`, and `takeover.shouldInject=true`.
3. If all fields hold, inject exactly one `contextGenerationId` for that Codex task using `replace_long_thread_context`.
4. If any field fails, block dispatch/provider calls and run a read-only exact scan.
5. If exact scan is unchanged and verification still fails, freeze with `authority_defect`.
6. If exact scan changed without a formal QA/accept receipt, freeze with `unaccepted_project_change`.
7. If exact scan changed with a formal receipt, run the local direct refresh driver. It executes `refresh_binding`, validates a new receipt/checkpoint/generation, performs bounded `verify`, and resumes only the affected lane after `matched/current/recoveryReady` are true.

Fail closed for: `fallback_stale`, `authorityVerification!=app_owned_verified`, `current=false`, `recoveryReady=false`, `returnedCount=0`, `takeover.shouldInject=false`, changed HEAD, changed scan, changed project identity, or changed postimage.

## Durable Injection Ledger

Persist `context_governor.py --state <task-state.json> --write-state` per Codex task. The state records:

- `taskInjectionLedger[taskId].injectedGenerationIds`
- `taskInjectionLedger[taskId].lastGenerationBasis`
- `taskInjectionLedger[taskId].invalidatedGenerationIds`

The same generation in the same task is blocked as `duplicate_context_generation`. Heartbeat, tool-result, commentary, and wake-check events must not trigger retrieval or injection. A changed HEAD, scan hash, project identity, postimage, or verified memory state invalidates the old generation until `refresh_binding` plus a new verify returns a new generation. New generation ids with unchanged basis remain blocked; `context-governance.md` is authoritative for takeover idempotency.

## Direct Refresh-Binding Driver

Zhixia exposes high-level app-owned `refresh_binding`. The current CEO/worker calls the formal Runtime directly through `scripts/refresh_binding_driver.py`; no memory-owner or knowledge-maintenance task participates in ordinary refresh:

```json
{
  "operation": "refresh_binding",
  "workspace": "<exact workspace>",
  "execute": true,
  "expectedProjectIdentitySha256": "<project identity>",
  "expectedScanSha256": "<new exact scan>",
  "previousCheckpointId": "<checkpoint-id>",
  "acceptedEvidenceReceipt": "<formal receipt id>",
  "acceptedChangedPaths": ["path/inside/project"],
  "lane": "<lane>",
  "evidence": {
    "decision": "accept",
    "phase": "<phase>",
    "summary": "<bounded summary>",
    "sourceRefs": [{"path": "path/inside/project", "hash": "<sha256>"}]
  }
}
```

The idempotency key binds workspace, project identity, scan, and receipt; changed paths and the previous checkpoint are immutable evidence attached to that attempt, not ways to create another attempt. The driver executes one refresh at most once per scan/receipt key, makes no model or paid Provider call, and never retries a failed refresh automatically. A full seed is not a substitute for refresh binding.

After a valid refresh receipt advances the checkpoint and generation, the driver calls `verify` locally up to the bounded verification limit. Resume the related lane only when `memoryMode=app_owned_memory_core`, `authorityVerification=app_owned_verified`, `scanBinding.matched=true`, `current=true`, `recoveryReady=true`, the scan matches, and the new checkpoint is authorized. Until then Provider calls remain zero. Failure pauses only that lane/module; `programGoalBlocked=false` and unrelated lanes may continue.

## Message Policy

Ordinary `verify`, exact scan, `prepare_takeover`, `refresh_binding`, and synchronization results stay inside the current CEO/worker task. Do not create or message a knowledge/知匣 maintenance task for success, transition, failure, or conflict. Emit one compact local blocker with one next action; any exceptional human escalation is a separate CEO/user decision, not an automatic Runtime side effect. Never nest `codex_delegation`, attach old chat text, or paste full Runtime JSON.
