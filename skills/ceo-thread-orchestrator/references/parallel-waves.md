# Parallel Waves Reference

Use this reference after a PRD, design brief, or task graph is accepted and the user asks to start, continue, or complete implementation.

## Principle

CEO Flow should not serialize an entire PRD through one worker when independent tasks can safely run together. Parallelism is useful only when it reduces delivery time without creating merge, review, workspace, or context debt.

## Parallel Readiness

Create a parallel wave when all are true:

- tasks can complete without waiting on each other's outputs;
- write-sets are non-overlapping or isolated by approved worktrees;
- shared contracts, schemas, routes, generated files, migrations, or design tokens are stable or assigned to one owner;
- each task has its own verification command, screenshot, artifact, or review evidence;
- command approvals are already planned;
- CEO can harvest and reconcile reports before dependent work starts;
- review capacity exists for risky or user-facing changes.

Do not parallelize when tasks:

- touch the same files or unclear ownership;
- share unstable architecture or unresolved API/schema contracts;
- compete for one local server, database, hardware resource, or external quota;
- depend on the same migration, generated artifact, or build output;
- require unplanned command approvals;
- create more merge/review cost than time saved.

## Wave Plan

For broad PRDs, the wave plan may be represented as `pipeline.yaml`, `workflow.yaml`, or an equivalent Program Goal section. Use `references/pipeline-contract.md` when typed handoffs, scorecard checks, environment profiles, or machine-checkable lane dependencies are needed.

```text
Wave ID:
Parallel goal:
Ready tasks:
Blocked / serial tasks:
Lane assignments:
Write-set ownership:
Shared contract owner:
Integration order:
Review plan:
Harvest cadence:
Stop condition:
```

## Dependency Graph

For each task:

```text
Task ID:
Objective:
Owner/lane:
Write-set:
Depends on:
Can run in parallel with:
Acceptance criteria:
Verification evidence:
Risk level:
```

## Lane Count

- 0 new lanes: CEO-only intake, audit, docs/skill/memory edits, quick tests, or explicitly direct-current-thread work.
- 1 implementation lane: one coherent write-set, uncertain dependencies, or ordinary serial coding.
- 2 lanes: implementation plus independent review, or two independent write-sets with clear verification.
- 3-5 active expert lanes: broad phases with separable backend, frontend, UX, QA, research, docs, or knowledge work.

Avoid permanent org charts. Create lanes by demand, not because the role map names them.

## Dispatch Rules

- Dispatch all ready tasks in the current wave, then harvest before starting dependent tasks.
- If a worker finishes early and the next task is independent with the same write-set, queue it to that lane.
- If the next task is independent but the lane is busy, create or reuse another implementation lane only when the write-set is non-overlapping and speed gain justifies coordination cost.
- If two lanes need the same file/module/contract, serialize them or make one lane the integration owner.
- For same-repo parallel work, track one owner per file/module/contract at a time.
- High-risk waves should have a separate read-only review lane.

## Integration

The CEO must explicitly reconcile:

- shared contracts and interfaces;
- generated artifacts;
- migrations;
- test fixtures and snapshots;
- UI copy/design-system changes;
- release notes and docs that depend on accepted implementation evidence.

Docs, release notes, memory cards, and broad screenshots usually run after implementation evidence exists, unless they are themselves independent deliverables.

## Harvest

At harvest:

1. Read each lane report and evidence.
2. Classify `accepted`, `revise`, `blocked`, `superseded`, `still_running`, or `stale`.
3. Detect collisions across files, APIs, generated artifacts, tests, and UX decisions.
4. Send bounded revision cards to the same lane when appropriate.
5. Start dependent tasks only after required upstream evidence is accepted.

If parallel work creates conflict or repeated uncertainty, collapse back to a serial integration owner.
