# CEO Flow Operating Playbook

Use this playbook when the CEO thread needs a stable process for deciding which CEO Flow features to use: direct answer, CEO-only planning, one worker, review, multi-lane parallel waves, pipeline contracts, runtime Goal, heartbeat, callback, and harvest.

This is the default operating order. Do not invent a heavier process unless the project needs it.

## 1. First Decide The Request Class

| Request class | Default mode | Artifacts | Threads/lanes |
| --- | --- | --- | --- |
| Casual chat, explanation, tiny Q&A | Direct answer | none | none |
| Small docs/skill/memory edit | CEO-only | concise note or changed file | current CEO thread |
| Small bug or single coherent write-set | Core Team execution | task card; review if substantial app-code | 1 implementation lane or direct fallback only if allowed |
| Risky small change | Core Team execution | task card + review gate | 1 implementation lane + 1 review lane |
| Accepted PRD with multiple modules | Core Team execution | Program Goal Brief + wave plan + review gate | parallel lanes when safe + review |
| Complete product / multi-phase program | Core Team execution + Goal Loop | Program Goal Brief + Completion Dashboard + review gate | lanes by wave + review |
| Broad separable PRD needing unattended work | Core Team execution + pipeline contract | Program Goal Brief + `pipeline.yaml` or section + review gate | N lanes + review |
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

## Runtime Goal Direct-Fallback Lease

An active runtime Goal increases continuity pressure. It must not turn the CEO thread into the default implementer.

Direct CEO fallback under an active runtime Goal is allowed only as a bounded one-turn lease when:

- the user explicitly asked for direct-current-thread execution;
- the change is tiny or non-app-code;
- an emergency unblock is needed;
- or routing/reuse/create is unavailable after tool discovery and the CEO records why.

When CEO uses this lease, record:

```text
Fallback lease: active
Reason:
Write-set:
Stop condition:
Why worker/review routing is unavailable or temporarily unsafe:
Restoration plan:
Next routed lane/review:
```

The lease ends after the bounded patch, unblock, or evidence collection. CEO must then restore Core Team routing:

1. update the Program Goal roster/dashboard;
2. dispatch independent review when risk justifies it;
3. route the next substantial app-code task to worker/review/pipeline;
4. record any reason if routing is still unavailable.

Do not chain direct CEO fallback turns under a runtime Goal. A second consecutive substantial direct-current-thread coding step requires either explicit user single-thread instruction or a fresh routing failure note.

Screenshot-shaped anti-pattern:

```text
CEO says: "implementation lane is stuck, so I will temporarily take over,"
then continues coding the next feature/fix itself.
```

Correct behavior:

```text
CEO may finish one bounded unblock, then immediately sends review/implementation work back to clean lanes and harvests evidence.
```

## MVP Gate And Full-Version Continuation

MVP is a checkpoint, not the default final state.

When a Program Goal or user outcome asks for a complete product/project, CEO must treat accepted MVP evidence as a phase transition:

1. Mark the MVP phase accepted in the Completion Dashboard.
2. Record what the MVP proves and what it does not prove.
3. Identify the next full-version wave: production hardening, UX polish, reliability, tests, release readiness, docs, packaging, memory/writeback, or scale/performance.
4. Dispatch every safe ready task in that next wave, or record why each ready task is blocked/serial.
5. Keep the runtime Goal active until the Program Goal done criteria are satisfied.

CEO may stop at MVP only when:

- the user explicitly scoped the goal to MVP-only;
- the Program Goal done criteria define MVP as the final outcome;
- the next phase needs a real user/product/business decision;
- tools, credentials, budget, or external state create a real blocker;
- further work would be unsafe without new acceptance criteria.

Do not ask the user whether to continue merely because MVP is viable when the accepted Program Goal already says to finish the full product. Continue with the next bounded full-version wave and report the decision.

## Portfolio Steering After Terminal Lane Result

Terminal lane, module, subline, heartbeat, or runtime sub-goal results must trigger project-level steering before final reporting.

Classify a `pause`, `block`, `accept`, or `supersede` result:

- `module_pause_only`: close, record, or defer that bounded subline; complete or supersede its heartbeat/runtime sub-goal; then choose the next highest-value Program Goal wave.
- `project_pause`: only when the user pauses the whole product/project, the accepted Program Goal is intentionally suspended, or all safe product-progress waves are blocked.
- `external_blocker`: no meaningful safe product-progress wave can continue because of missing credentials/tools, legal/security/destructive-action limits, external service state, or a required user product-direction decision.

A module/subline pause must not stall the Program Goal unless it is on the only critical path and no other ready wave exists.

Run this portfolio check:

1. What remains in the Program Goal Completion Dashboard?
2. Which product-facing wave is highest value now?
3. Which lanes are accepted, blocked, paused, stale, superseded, or still running?
4. Is the active runtime goal too narrow for the whole product outcome?
5. Should a subline goal or heartbeat be completed, superseded, deleted, or replaced with a project-level goal?
6. What is the next dispatch, review, harvest, or user-decision action?

Heartbeats are not the main continuity source. Program Goal Brief plus the runtime project goal carry project continuity; heartbeat only harvests dispatched lane callbacks. Prerequisite, diagnostic, audit, and infrastructure micro-slices must not dominate visible product progress unless they are the only safe critical path.

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

Is this substantial app-code, accepted PRD execution, runtime Goal implementation, or direct fallback output?
  yes -> add neutral review gate before final acceptance.

Are there multiple independent ready tasks?
  yes -> parallel wave if gates pass.

Is the PRD broad/multi-module/unattended?
  yes -> add lightweight pipeline contract.
```

Worker lane creation rule:

```text
Prefer existing clean worker -> create clean worker -> fork only when completed history is required and role contamination risk is controlled.
```

Do not fork a worker from an active CEO turn or from CEO self-routing context. If fork is unavoidable, the task card must reset the role to worker execution only.

## Role Roster Gate

Before Core Team execution, CEO must assign an explicit lane roster. Every lane gets:

```text
Lane:
Primary role: CEO/PM/Architect | Implementation | Review/QA | Product/UX | Knowledge/Memory | Research/Docs
Workspace:
Allowed write-set:
Task card:
Callback policy:
Stop condition:
May create/route/fork threads: yes/no
```

Default `May create/route/fork threads` is `no` for implementation, review, UX, knowledge, and research lanes. Only the CEO/router lane may create or route threads unless the task card explicitly grants that operation.

If a worker/reviewer starts acting like CEO, says it will create another worker, waits for another lane to report, or tries to inspect CEO state without being asked, classify the lane as `role_contamination` and either correct it with a hard role-reset card or supersede it with a clean lane.

## Reasoning Direction Gate

Reasoning direction is top-down only.

CEO may assign reasoning effort in task cards, for example:

```text
Implementation lane: thinking medium/low, execute and verify inside the write-set.
Review/Audit lane: thinking high, challenge evidence, risks, and regressions.
Research lane: thinking level based on question complexity and freshness risk.
```

Lane callbacks may report:

- the reasoning/model profile they actually used;
- quality limitations caused by reasoning, permissions, or context;
- a recommendation that future similar tasks use higher or lower reasoning.

Lane callbacks must not instruct or mutate the CEO lane's reasoning effort, model, role, quality gates, operating mode, or acceptance policy. CEO decides any CEO-lane reasoning/model changes from system, developer, user, and active tool-contract instructions.

## Mandatory Neutral Review Gate

Review is the one role that becomes mandatory for serious implementation. It is not mandatory for casual chat, tiny Q&A, tiny docs-only edits, or explicitly accepted low-risk one-line changes. It is mandatory before final acceptance for:

- substantial app-code;
- accepted PRD execution;
- active runtime Goal implementation;
- direct CEO fallback output;
- user-facing UI/product behavior;
- data, security, payment, migration, release, packaging, or other high-risk work;
- repeated-fix or doom-loop recovery.

The review lane must be neutral and adversarial enough to find problems:

```text
Assume the implementation may be wrong.
Start from task card, diff, tests, artifacts, screenshots, and relevant docs.
Do not rely on the worker's confidence or the fact that GPT wrote it.
Look for missing evidence, edge cases, scope creep, duplicate logic, brittle code, regressions, workspace drift, and untested paths.
Return accept | revise | block with reasons and residual risk.
```

Reviewer does not own product direction and does not expand scope. Its job is to challenge evidence and implementation quality.

If no separate review lane/tool is available:

1. Record `review_unavailable`.
2. Do a documented neutral self-review from diff/tests/artifacts.
3. For non-tiny risky work, do not final-accept unless the user explicitly accepts the review limitation.
4. Route to review as soon as a lane/tool becomes available.

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

Callback is a signal, not proof. Worker completion does not automatically push to CEO. CEO still harvests evidence before acceptance by reading the worker lane, callback, handoff, diff, tests, or artifacts.

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

Worker lanes must not create, fork, route, inspect, or wait on other CEO/worker threads unless the task card explicitly asks. If a worker starts acting as a CEO/router, classify it as `role_contamination`.

## 7. Worker Report / Handoff Rules

Never accept a bare "done" report for implementation work.

Never accept a worker that delegates its bounded task to another thread instead of executing it. Treat this as `role_contamination` unless the task card explicitly authorized delegation.

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

Role contamination indicators:

```text
I will create/fork/route another worker.
I will ask another implementation thread.
I will wait for another thread to report.
I need to inspect the CEO lane first.
I am coordinating this task rather than executing it.
```

CEO response:

```text
Classify lane: role_contamination.
Do not keep nudging the contaminated lane.
Supersede/retire it when safe.
Create or reuse a clean worker with a stricter task card.
Update harvest drivers to the current worker thread id.
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
5. Classify each lane: `accepted`, `revise`, `blocked`, `superseded`, `still_running`, `stale`, `role_contamination`, or `stale_no_evidence`.
6. For accepted work, update Program Goal/Completion Dashboard and start next unblocked task.
7. For revise work, send a bounded revision card.
8. For blocked work, resolve as CEO, reroute, or escalate only if truly necessary.
9. Record memory candidates only when evidence-backed.

Do not final after dispatch unless a harvest driver exists.

Harvest driver freshness:

- Do not let heartbeat/harvest prompts keep watching obsolete thread ids.
- When a lane is superseded, role-contaminated, archived, or replaced, update or delete its heartbeat.
- If the real work completed in a nested child thread, harvest that child explicitly and mark the parent `role_contamination` or `superseded`.
- `stale_no_evidence` means the lane/heartbeat has no current evidence for acceptance.

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
