# CEO Flow Operating Playbook

Use this playbook when the CEO thread needs a stable process for deciding which CEO Flow features to use: direct answer, CEO-only planning, one worker, review, multi-lane parallel waves, pipeline contracts, runtime Goal, heartbeat, callback, and harvest.

This is the default operating order. Do not invent a heavier process unless the project needs it.

## 1. First Decide The Request Class

| Request class | Default mode | Artifacts | Threads/lanes |
| --- | --- | --- | --- |
| Casual chat, explanation, tiny Q&A | Direct answer | none | none |
| Small docs/skill/memory edit | CEO-only | concise note or changed file | current CEO thread |
| Small bug or single coherent write-set | Core Team execution | task card | 1 implementation lane or direct fallback only if allowed |
| Risky small change | Core Team execution | task card + review gate | 1 implementation lane + 1 review lane |
| Accepted PRD with multiple modules | Core Team execution | Program Goal Brief + wave plan | parallel lanes when safe |
| Complete product / multi-phase program | Core Team execution + Goal Loop | Program Goal Brief + Completion Dashboard | lanes by wave |
| Broad separable PRD needing unattended work | Core Team execution + pipeline contract | Program Goal Brief + `pipeline.yaml` or section | N lanes + review |
| Worker/reviewer task card from another CEO | Bounded worker/reviewer | report/handoff only | do not self-promote to CEO |

If the task is not substantial, do not force CEO ceremony.

## 2. Goal Mode Trigger

Create or bind a runtime Codex Goal when the user asks to:

- finish a whole product/project;
- drive an accepted PRD to completion;
- keep progressing beyond one bounded task;
- run a multi-phase roadmap;
- maintain a long-running Program Goal.

Runtime Goal rules:

- The runtime Goal references the Program Goal Brief path.
- It keeps continuity toward completion.
- It does not replace the Program Goal Brief.
- It does not allow CEO to implement substantial work alone.
- It does not replace harvest, evidence review, or accept/revise/block.
- A bound active runtime Goal can be the harvest driver, so separate heartbeat/fixed-time harvest is optional while the Goal remains active.

If goal tooling is unavailable, record `runtime_goal_unavailable` and continue with Program Goal Brief plus ordinary harvest.

## 3. Choose The Execution Shape

Use the smallest shape that can safely finish the next objective.

```text
Is this tiny/direct?
  yes -> direct answer or CEO-only.
  no -> continue.

Is there an accepted PRD/task graph or user asked to implement?
  no -> CEO-only planning/audit.
  yes -> Core Team execution.

Is there exactly one coherent write-set?
  yes -> 1 implementation lane.

Is the change risky/user-facing?
  yes -> add independent review lane.

Are there multiple independent ready tasks?
  yes -> parallel wave if gates pass.

Is the PRD broad/multi-module/unattended?
  yes -> add lightweight pipeline contract.
```

## 4. Parallel Gate

Parallel execution is allowed only when all are true:

- dependencies are independent;
- write-sets do not overlap, or worktrees/owners isolate them;
- shared contracts are stable or one owner is assigned;
- verification is isolated;
- command approvals are planned;
- resource conflicts are known, such as ports, databases, browsers, devices, or external quotas;
- CEO has harvest/review capacity;
- rollback baseline and stop conditions exist.

If any item is unclear, use one lane, serial waves, or a single integration owner.

Do not select only one workstream from a ready independent wave unless there is a recorded reason:

- dependency blocked;
- write-set conflict;
- shared process/resource conflict;
- approval limit;
- missing thread tools;
- missing harvest/review capacity;
- user explicitly requested single-thread execution.

## 5. Pipeline Contract Gate

Use `pipeline.yaml`, `workflow.yaml`, or an equivalent Program Goal section only when it reduces ambiguity.

Use pipeline contract for:

- broad accepted PRD;
- multiple ready implementation lanes;
- unattended or long-running execution;
- fan-out/fan-in review;
- write-set/resource conflict risk;
- typed handoff or Scorecard needed.

Do not use pipeline contract for:

- tiny fixes;
- one coherent write-set;
- one-off docs;
- exploratory product thinking;
- tasks where YAML costs more than it saves.

Minimum pipeline fields:

```text
pipeline id:
goal brief:
lanes/nodes:
depends on:
parallel with:
write-set owner:
environment profile:
handoff schema:
required verification:
review/scorecard gate:
stop condition:
```

## 6. Communication And Callback Rules

Visible Codex threads are work lanes, not shared memory.

CEO dispatches compact task cards. Worker lanes report in their own lane and, when thread messaging exists, send a compact callback to the CEO thread.

Callback is a signal, not proof. CEO still harvests evidence before acceptance.

Small task callback may be compact:

```text
Status:
Changed files:
Commands run:
Result:
Risks:
Blockers:
Next action:
```

Pipeline task callback should point to typed handoff:

```text
Lane ID:
Handoff path or summary:
Status:
Evidence refs:
Needs CEO decision:
```

When pipeline artifacts exist, CEO should run or request the bundled validators when practical:

```text
validate_pipeline.py for pipeline/workflow files
scorecard_handoff.py for worker/review handoffs
```

Workers ask CEO, not the user, for routine in-scope questions. Escalate to the user only for out-of-scope changes, destructive actions, credentials, spending, legal/security/product-direction decisions, missing business facts, or changed done criteria.

## 7. Worker Report / Handoff Rules

Never accept a bare "done" report for implementation work.

Minimum worker report:

```text
Status: complete | partial | blocked | approval_stalled | failed
Files changed:
Write-set compliance:
Commands run:
Results:
Evidence/artifacts:
Risks/assumptions:
Recommended next action:
Memory candidates:
```

Pipeline workers should use `typed_handoff_v1`.

Review lanes should use `review_handoff_v1` or equivalent fields:

```text
Decision: accept | revise | block
Evidence inspected:
Reasons:
Missing evidence:
Required fixes:
Residual risk:
Confidence:
```

## 8. Harvest Driver Selection

After dispatching any implementation/review lane, record one harvest driver:

| Harvest driver | Use when |
| --- | --- |
| Immediate synchronous harvest | The worker is expected to return in the same turn/session |
| Explicit next harvest time | User is present or short planned wait is enough |
| Heartbeat automation | Work may run unattended and no runtime Goal is active |
| Active runtime Codex Goal | Program Goal is active and the Goal is bound to the Program Goal Brief |

If runtime Goal is active and bound, separate heartbeat/fixed-time harvest is optional.

Still record:

- lane roster;
- expected report;
- callback policy;
- stop condition;
- next harvest trigger;
- evidence to inspect.

## 9. CEO Harvest Procedure

At every harvest:

1. Read callbacks/reports.
2. Read typed handoffs when present.
3. Inspect diff, changed files, test output, screenshots, logs, or artifacts as risk requires.
4. Check write-set and dependency conflicts.
5. Classify each lane: `accepted`, `revise`, `blocked`, `superseded`, `still_running`, or `stale`.
6. For accepted work, update Program Goal/Completion Dashboard and start next unblocked task.
7. For revise work, send a bounded revision card.
8. For blocked work, resolve as CEO, reroute, or escalate only if truly necessary.
9. Record memory candidates only when evidence-backed.

Do not final after dispatch unless a harvest driver exists.

## 10. Approval Stall Handling

Worker lanes should not ask the user for routine in-scope command approvals.

If host approval blocks a routine in-scope action:

1. Worker reports `approval_stall` to CEO.
2. CEO checks whether the command fits the task card approval profile.
3. If in profile, CEO sends continuation/approval guidance.
4. If host UI still requires manual approval, mark lane `approval_stalled`.
5. Continue other safe ready work.

Approval stalls are lane-local, not program-global.

## 11. Completion Rules

CEO can close a task/program only when:

- newest user request is satisfied;
- done criteria are met;
- evidence is sufficient for risk;
- open lanes are accepted, blocked by real external dependency, superseded, or intentionally stopped;
- Program Goal and Completion Dashboard are updated when present;
- runtime Goal is marked complete only after Program Goal acceptance evidence is sufficient.

Use explicit decision:

```text
Decision: accept | revise | block | supersede
Evidence inspected:
Residual risk:
Next owner:
Memory update needed:
```

## 12. Simplification Rule

If CEO Flow feels heavy, reduce the process before adding more agents:

```text
pipeline -> parallel wave -> one implementation lane + review -> one implementation lane -> CEO-only
```

If implementation quality slips, strengthen review and typed handoff before increasing lane count.
