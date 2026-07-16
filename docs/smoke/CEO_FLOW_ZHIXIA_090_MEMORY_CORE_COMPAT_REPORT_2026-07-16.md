# CEO Flow ↔ Zhixia 0.9.0 Memory Core Compatibility Report

Date: 2026-07-16  
Decision: **accept** for the compatibility contract; the isolated recovery fixture itself correctly returned **partial / recoveryReady=false** because its ProjectBrain lacked accepted continuity state.

## Scope

This closure verifies that CEO Flow can use Zhixia 0.9.0 Memory Core without changing the CEO lane's model, reasoning effort, role, or routing permissions.

Implemented contract:

- Project Continuity Gate is lifecycle-event triggered, not a heartbeat, timer, polling loop, or every-turn recall.
- CEO takeover, old-thread recovery, and major direction correction require exact `projectPath`/`projectId`, all 14 ProjectBrain slots, and complete mandatory pagination.
- Incomplete, conflicting, stale, helper-only, or unverifiable continuity remains `partial`; it cannot claim `recoveryReady`.
- Worker and reviewer packets receive role-required slots only, not the complete CEO ProjectBrain.
- Checkpoint, broken/stale thread, takeover, heartbeat fuse, and durable user-rule changes use bounded `observe_event` records when available.
- `accept | revise | block | supersede` produces compact `writeback_evidence` with preserved `sourceRefs`.
- `retrieve_context`, `retrieve_precedent`, and `writeback_evidence` execution is proven by matching `MemoryRuntimeTriggerReceipt` records rather than prompt intent.

## Changed CEO Flow Surfaces

- `skills/ceo-thread-orchestrator/SKILL.md`
- `skills/ceo-thread-orchestrator/references/memory-runtime.md`
- `skills/ceo-thread-orchestrator/references/context-memory.md`
- `skills/ceo-thread-orchestrator/references/thread-ops.md`
- `skills/ceo-thread-orchestrator/references/state-schema.md`
- `examples/smoke-prompts.md`
- `examples/smoke-eval-cases.json`
- `scripts/zhixia_memory_core_recovery_probe.cjs`

## Zhixia Skill Synchronization

The bundled and installed `zhixia-local-docs` copies were compared by SHA-256 and matched for:

- `SKILL.md`
- `agents/openai.yaml`
- `references/context-bundle.md`
- `references/memory-core-lifecycle.md`
- `scripts/read-project-knowledge.cjs`

Both source and installed skills passed the skill validator.

## Isolated Real-Project Recovery Probe

The probe copies a bounded snapshot of the real CEO Flow repository into temporary storage, seeds the Zhixia Memory Core project backfill into isolated Electron `userData`, exercises real renderer-to-main IPC, and deletes the temporary data afterward. It does not write the live Zhixia database or mutate the live project.

Command shape:

```powershell
node scripts\zhixia_memory_core_recovery_probe.cjs <zhixia-app-root> <ceo-flow-repo-root>
```

Observed result:

| Check | Result |
|---|---|
| Exact project path/id | matched |
| ProjectBrain slot schema | 14 slots |
| Mandatory pagination | complete; returned `1/1` existing mandatory records |
| Retrieval receipt | `retrieve_context`, sourceRefs present |
| Precedent receipt | `retrieve_precedent`, sourceRefs present |
| Decision writeback receipt | `writeback_evidence`, 2 sourceRefs, status `queued` |
| Checkpoint event | `recorded` |
| Thread takeover event | `recorded` |
| Broken-thread event | `recorded` |
| User-rule-update event | `recorded` |
| Required hook receipts | verified |
| Probe compatibility verdict | passed |

The snapshot did not contain accepted Memory Core records for the original product goal, architecture anchors, standing rules, active modules, accepted progress, open tasks/blockers, recent failures, next actions, and thread lineage. Project identity also had a conflict candidate after the governance fixture import. Therefore the correct recovery result was:

```text
partial: yes
recoveryReady: false
paginationComplete: true
```

This is a safety success, not a failed compatibility result: CEO Flow consumed the complete available mandatory manifest and refused to overclaim recovery readiness when the 14-slot continuity ledger was not authoritative and complete.

## Validation Evidence

CEO Flow:

- validator unit tests: `7/7 PASS`
- static smoke eval: `57/57 PASS`
- pipeline and handoff template validators: PASS
- release-state check: PASS
- skill validator: PASS
- plugin validator: PASS

Zhixia 0.9.0:

- `tests/zhixia-local-docs-helper.test.cjs`: PASS
- `tests/memory-runtime-lifecycle-e2e.test.cjs`: PASS
- `tests/electron-ipc-governance-contract.test.cjs`: PASS
- bundled `zhixia-local-docs` skill validator: PASS
- installed `zhixia-local-docs` skill validator: PASS

## Acceptance Decision

**accept**

Reason: the policy, schemas, smoke coverage, installed provider synchronization, lifecycle events, exact-project continuity traversal, writeback provenance, and trigger-receipt verification are closed. The real-project fixture correctly fails closed to partial rather than falsely declaring `recoveryReady`.

Residual operational requirement: a live project becomes `recoveryReady` only after Zhixia holds authoritative, source-backed current records for every required ProjectBrain slot. CEO Flow must continue to report missing/conflict/stale/review slots rather than filling them by inference.
