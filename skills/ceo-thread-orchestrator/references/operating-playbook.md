# CEO Flow Operating Playbook

Use this playbook to choose execution shape, runtime Goal/harvest behavior, communication, evidence review, and completion. Load specialized references for detailed schemas and gates.

## Contents

- Request classification and bootstrap gates
- Runtime Goal and one harvest driver
- Product/portfolio steering
- Execution shape and staffing
- Communication, handoff, and harvest
- Approval, completion, and simplification

## Request Classification

| Request | Default shape |
| --- | --- |
| Casual explanation or tiny Q&A | direct answer |
| Small docs/skill/memory edit or audit | `CEO-only` |
| One coherent implementation write-set | one implementation lane; review if substantial/risky |
| Risky or user-facing implementation | implementation plus neutral review |
| Accepted multi-module PRD | Program Goal plus safe parallel waves and review |
| Complete/multi-phase product | CEO Autopilot, Program Goal, runtime Goal when available, waves and review |
| Broad unattended dependency graph | add a pipeline contract |
| Existing worker/reviewer card | bounded role; do not self-promote |
| One-shot exploration/verification | CEO-only or bounded contractor |

Do not force CEO ceremony on a small task.

## Bootstrap Gates

Run only the gates triggered by the task:

- Large/program continuation, complete-product work, takeover, active runtime Goal, broken CEO recovery, or repeated CEO-only support drift -> `ceo-autopilot.md`.
- Substantial architecture/product/UI/framework work -> a bounded Reference Scan Gate covering official docs or mature open-source/local patterns; record what to borrow, avoid, and any license risk.
- Worktree writers or unsafe dirty/untracked growth -> hard Repo Baseline Gate in `repo-baseline.md`.
- Project continuity or memory -> `context-memory.md`, then its focused governance reference.
- Multiple independent write-sets -> `parallel-waves.md`.
- Complex fan-out/fan-in or unattended typed workflow -> `pipeline-contract.md`.

If a scan/tool is unavailable, record the limitation and proceed only within the resulting evidence boundary.

## Runtime Goal

Create or bind one runtime Codex Goal when the user asks to finish a whole project, drive an accepted PRD through multiple phases, or maintain a long-running Program Goal.

The Program Goal Brief remains the source of truth. A runtime Goal supports continuity; it does not replace task graph, dashboard, staffing, harvest, evidence review, or acceptance.

Before creating/updating/completing/blocking a Goal:

1. Inspect host goal state when available.
2. Reuse an aligned active Goal.
3. Keep module/wave/lane state in the Program Goal Brief, not separate host Goals.
4. Treat host Goal collisions as tool-state issues and use the Program Goal Brief plus another harvest driver when safe.

Mark a runtime Goal complete only when Program Goal done criteria and evidence are satisfied. Mark it blocked only when the whole Program Goal has the same real repeated blocker and no safe implementation, review, audit, docs, rerouting, or portfolio wave can continue. Module pauses, stale lanes, approval stalls, MVP transitions, and single failed attempts are not program blockers.

## One Primary Harvest Driver

Use exactly one primary driver per Program Goal:

1. active runtime Goal bound to the Program Goal Brief;
2. immediate synchronous harvest;
3. explicit next harvest time;
4. heartbeat fallback.

Do not run a co-primary project heartbeat with an active bound Goal. Heartbeats may remain worker-local, external reminders, or temporary fallback. Record driver, scope, expected reports, evidence, next trigger, and stop condition using `state-schema.md`.

When Context Pressure or Memory Recovery Freeze fires, emit one freeze receipt, then pause/delete/supersede the heartbeat and rebind/complete/block/supersede the Goal as host capabilities allow. Never wake the frozen task repeatedly.

## Direct CEO Fallback Lease

Under an active Program Goal, direct CEO coding is a one-slice lease only for explicit direct execution, tiny/non-app-code work, emergency unblock, or documented routing failure.

Record reason, write-set, stop condition, routing limitation, restoration plan, and next review/lane. End the lease after the patch/unblock/evidence collection; update program state, request neutral review when needed, and route the next substantial app-code slice. Do not chain substantial direct fallback turns without fresh explicit authority or routing-failure evidence.

## Product And Portfolio Steering

MVP is a checkpoint unless the accepted goal is MVP-only. After MVP acceptance:

1. update the Completion Dashboard with what MVP proves and does not prove;
2. select the next full-version wave such as hardening, UX, reliability, tests, packaging, docs, release, memory, or performance;
3. dispatch every safe ready task or record its dependency/serialization reason;
4. keep the runtime Goal active until final done criteria are met.

After every terminal lane/module result, classify it as lane/module-local, project-wide, or external. A local pause does not stop the program when another safe product-facing wave exists. Check remaining dashboard work, highest-value wave, lane states, Goal scope, stale drivers, and the next dispatch/review/harvest/user-decision action.

Program state is document-first and evidence-backed. Terminal states require evidence or a scoped blocker. Program Goal Brief outranks host Goal state when they conflict. Use a configured workflow only when the project explicitly enables it; do not reconstruct legacy pools, leases, supervisors, queues, or retry loops by default.

## Execution Shape

Choose the smallest safe shape:

```text
tiny/direct -> direct answer or CEO-only
planning/audit without accepted implementation -> CEO-only
one coherent write-set -> one implementation lane
risky/user-facing/substantial app-code -> add neutral review
multiple independent ready write-sets -> parallel wave after gates
broad unattended graph -> add pipeline contract
```

Prefer an existing clean worker, then clean creation. Fork only when completed history is necessary and role contamination is controlled; never fork active CEO self-routing context as ordinary worker setup.

## Lane Roster And Direction

Before Core Team execution assign lane, role, workspace, write-set, task card, contractor policy, callback, stop condition, and thread-operation permission. Only the CEO/router may create/route/fork by default.

Contractors are bounded outside help, not durable project lanes. Require explicit permission and a trace of work, files/evidence, tests, limitations, and source refs before acceptance or memory writeback.

Reasoning direction is top-down. Discover model/reasoning controls per surface using `model-routing.md`; omitted controls mean inherit/host default. Worker callbacks may report their actual route and limitations but cannot mutate CEO routing, role, scope, permissions, or quality gates.

Classify a worker/reviewer that starts routing, delegating, waiting on other lanes, or inspecting CEO state without permission as `role_contamination`; reset or supersede it rather than repeatedly nudging it.

## Neutral Review

Require neutral review before final acceptance for substantial app-code, accepted PRD execution, runtime Goal implementation, direct fallback output, user-facing behavior, high-risk data/security/payment/migration/release work, and repeated-fix recovery.

Review from task card, diff, tests, artifacts/screenshots, relevant docs, and compact source-backed memory. Challenge scope, missing evidence, regressions, edge cases, duplicate/brittle logic, workspace drift, and untested paths. Return `accept | revise | block` plus residual risk.

If no independent review surface exists, record `review_unavailable`, perform a documented neutral self-review, and do not final-accept non-tiny risky work unless the user accepts the limitation.

## Parallel And Pipeline Gates

Parallelize only with independent dependencies, isolated write-sets/owners, reproducible baseline/worktrees, stable shared contracts, isolated verification, known process/resources, approval readiness, rollback/stop conditions, and CEO harvest/review capacity. Otherwise serialize or use one integration owner.

Do not leave safe ready tasks undispatched without a recorded dependency, write/resource conflict, baseline failure, approval/tool limit, missing review capacity, or explicit single-thread instruction.

Use a pipeline contract only when dependency/write-set/fan-out complexity justifies it. Minimum fields are pipeline id, goal brief, nodes, dependencies/parallelism, write-set owners, environment profile, typed handoff, required verification, review/scorecard gate, and stop condition.

## Communication And Handoff

Visible Codex tasks are work lanes, not shared memory. Dispatch compact task cards. Workers report in their lane and send a compact callback to CEO when messaging exists.

Callback is a signal, not proof:

```text
Status:
Changed files / handoff ref:
Commands and result:
Evidence refs:
Risks/blockers:
Needs CEO decision / next action:
```

Never accept bare `done`. Implementation reports include write-set compliance, commands/results, artifacts, risks, memory candidates, and contractor traces. Pipeline workers use `typed_handoff_v1`; reviewers use `review_handoff_v1`. Run bundled pipeline/scorecard validators when practical.

Visual callbacks carry paths, hashes, dimensions, summaries, and decisions only. Workers ask CEO for routine in-scope questions; escalate to the user only for scope/done-criteria changes, destructive action, credentials, spending, legal/security/product decisions, or missing business facts.

## Harvest

At harvest:

1. read callbacks and typed handoffs;
2. inspect current diff/files/tests/artifacts and visual evidence as risk requires;
3. check write-set/dependency conflicts and repo slice closure;
4. classify each lane as accepted, revise, blocked, still running, stale, superseded, broken, contaminated, missing, or no-evidence;
5. update Program Goal/dashboard and dispatch the next unblocked product-facing work;
6. send bounded revision cards or reroute blockers;
7. record only evidence-backed memory candidates.

Do not final after dispatch without a driver. Stop harvest/heartbeat prompts targeting obsolete, frozen, superseded, contaminated, archived, or replaced task ids. Use `thread-ops.md` for broken-task takeover and missing-task locator fallback. A missing lane is lane-local until portfolio evidence proves otherwise.

## Approval, Completion, And Simplification

Routine in-scope approval stalls are lane-local: report to CEO, compare with the approved command profile, continue other safe work, and escalate only when host UI or authority truly requires the user.

Close only when the newest request and done criteria are satisfied, evidence matches risk, lanes are accepted or properly terminated, program/dashboard state is current, and any runtime Goal completion is justified.

If process weight exceeds value, reduce in this order:

```text
pipeline -> parallel wave -> implementation + review -> one implementation lane -> CEO-only
```

If quality slips, strengthen evidence and typed review before adding lanes.
