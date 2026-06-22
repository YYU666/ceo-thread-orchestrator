# CEO Flow Lightweight State Discipline Upgrade

Date: 2026-06-22

## Decision

Accepted and implemented.

CEO Flow should borrow the useful state discipline from legacy automatic workflow systems, but it must not recreate or load a heavyweight workflow runtime by default.

## What Changed

This upgrade adds a lightweight state-discipline layer to CEO Flow:

- Program Goal Brief remains the source of truth for project/program state.
- Completion Dashboard tracks phase progress, accepted work, blockers, next task, and evidence.
- Lane roster tracks implementation/review lane state.
- Terminal states require evidence or a clear blocker explanation.
- `pause` and `blocked` must be scoped by level: lane-local, module-only, project, or external.
- Runtime Codex Goal remains a whole-product continuity helper, not a fine-grained task state machine.

## What It Explicitly Does Not Do

CEO Flow does not load or recreate legacy workflow-runtime machinery by default:

- no task-pool scans;
- no task/workspace lease checks;
- no supervisor health loops;
- no review queue or writeback queue;
- no completion ledger reconstruction;
- no automatic repair/retry loops;
- no legacy AutoFlow/OpenClaw default path.

Those mechanisms may be used only under `configured workflow` when a project explicitly provides and enables that runtime.

## Files Updated

- `skills/ceo-thread-orchestrator/SKILL.md`
  - Added lightweight state discipline to the Program Goal Brief critical path.
  - Added explicit rule not to load/recreate legacy workflow-runtime queues, leases, supervisors, or completion ledgers unless the user chose a configured workflow.

- `skills/ceo-thread-orchestrator/references/operating-playbook.md`
  - Added `Lightweight State Discipline, Not Workflow Runtime`.
  - Defined the minimum state record:
    - program status;
    - phase;
    - lane states;
    - last accepted state transition;
    - terminal evidence required;
    - blocker level;
    - next transition;
    - evidence refs.

- `examples/smoke-prompts.md`
  - Added `Lightweight State Discipline Without Legacy Runtime`.

- `CHANGELOG.md`
  - Added the unreleased upgrade note.

## Test Results

| Check | Result |
| --- | --- |
| Repo skill validator | Pass |
| Installed skill validator | Pass |
| Plugin validator | Pass |
| Privacy/path scan | Pass: no hits |
| Static smoke coverage check | Pass: new state-discipline prompt and guardrail strings found |

## Smoke Coverage Added

New smoke prompt:

```text
Lightweight State Discipline Without Legacy Runtime
```

Expected behavior:

- CEO Flow keeps Program Goal Brief, Completion Dashboard, lane roster, terminal evidence, scoped blockers, and next transition as the project state source.
- CEO Flow avoids loading or recreating legacy workflow-runtime machinery.
- CEO Flow uses legacy workflow ideas only as design reference unless `configured workflow` is explicitly enabled.

## Residual Risk

Existing long-running Codex threads may still carry older hot context. If behavior looks stale after installing this upgrade, refresh/restart Codex or test in a fresh thread before judging the skill behavior.

