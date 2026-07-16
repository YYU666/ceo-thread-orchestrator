# CEO Flow ↔ Zhixia 0.9.0 Memory Core Compatibility Report

Date: 2026-07-16  
Decision: **accept** after audit revision. The probe now proves both a real-project fail-closed recovery and a complete authoritative 14-slot, forced multi-page, `recoveryReady=true` recovery.

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

## Isolated Recovery Probe

The probe creates two isolated scenarios in temporary Electron `userData`, exercises real renderer-to-main IPC, and deletes the temporary data afterward. It does not write the live Zhixia database or mutate the live project.

1. **Real-project safety scenario:** copies a bounded CEO Flow repository snapshot and verifies incomplete/conflicting continuity fails closed.
2. **Authoritative success scenario:** seeds source-backed records for all 14 slots, enough mandatory records to require eight pages, and an app-owned accepted checkpoint.

Command shape:

```powershell
node scripts\zhixia_memory_core_recovery_probe.cjs <zhixia-app-root> <ceo-flow-repo-root>
```

Authoritative success result:

| Check | Result |
|---|---|
| Independent seed project identity | seed ID = status ID = every page ID |
| ProjectBrain slots | `14/14` filled |
| Mandatory pagination | eight pages; returned `32/32` mandatory records |
| First page | `nextCursor` present and `recoveryReady=false` |
| Final page | no missing/stale/conflict; `recoveryReady=true` |
| Wrong projectId | rejected |
| Cross-project path/ID pair | rejected |
| Tampered cursor | `cursorInvalid=true`, recovery not ready |
| Retrieval receipt | exact returned receipt ID, hook, query type, project path, thread scope, operation window, counts, partial flag, and sourceRefs matched |
| Precedent receipt | exact returned receipt ID and full scope matched |
| Decision writeback receipt | exact returned receipt ID and full scope matched; 2 sourceRefs; status `queued` |
| Checkpoint event | `recorded` |
| Thread takeover event | `recorded` |
| Broken-thread event | `recorded` |
| User-rule-update event | `recorded` |
| Initialization receipts | baseline IDs excluded from lifecycle-hook verification |
| Probe compatibility verdict | passed |

Real-project safety result:

```text
partial: yes
recoveryReady: false
paginationComplete: true
```

The real snapshot lacks accepted records for several continuity slots and contains an identity conflict candidate after governance import. The probe independently compares every returned ID against the seed-generated expected ID, consumes the complete available manifest, and refuses to overclaim recovery readiness.

Together, the scenarios prove both sides of the contract:

- incomplete or conflicting memory fails closed;
- complete authoritative memory requires continuation pages and becomes recovery-ready only after all mandatory pages are consumed.

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

The audit revision also closes the three former P2 evidence gaps: successful 14-slot multi-page recovery, independently seeded project identity, and exact per-call trigger-receipt binding.

Residual operational requirement: a live project becomes `recoveryReady` only after Zhixia holds authoritative, source-backed current records for every required ProjectBrain slot. CEO Flow must continue to report missing/conflict/stale/review slots rather than filling them by inference.
