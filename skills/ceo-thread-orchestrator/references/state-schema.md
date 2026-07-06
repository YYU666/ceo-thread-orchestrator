# CEO Flow State Schema

Use this reference when CEO Flow needs a compact, durable state contract for Program Goals, lane rosters, harvest drivers, decisions, recovery packets, and memory writeback. These schemas are lightweight Markdown contracts, not a workflow runtime or database.

## Principles

1. Keep state document-first and source-backed.
2. Store only the minimum fields needed to resume, harvest, review, and accept/revise/block.
3. Program Goal Brief is the source of truth; runtime Codex Goal is continuity support only.
4. Terminal states require evidence or an explicit scoped blocker.
5. Do not recreate legacy task pools, leases, supervisors, review queues, or completion ledgers unless the project explicitly enables a configured workflow.

## Program Goal Brief

```text
Program goal:
Canonical project root:
Outcome / launch definition:
Done criteria:
Non-goals:
Phases:
Completion dashboard: see schema below
Task graph:
Lane roster / thread ids: see schema below
Current blockers:
Next execution wave:
Primary harvest driver: see schema below
Acceptance evidence:
Memory Runtime result:
  provider:
  hook:
  queryType:
  query:
  tokenBudget:
  memoryMode:
  memoryLayers:
    hot:
    warm:
    skill:
    cold:
  recallPlan:
    defaultReadOrder:
    coldLayer.defaultRead:
  top memory items:
  retrieved sourceRefs:
  skipped/unavailable reason:
Autopilot Startup Card:
Staffing Plan:
Long-Term Memory Anchor Gate:
Proof Loop Fuse:
Memory / knowledge writeback:
Lightweight state discipline:
  State source of truth:
  Last accepted state transition:
  Terminal evidence required:
  Blocker level: none | lane_local | module_only | project | external
Last updated:
```

## Completion Dashboard

```text
Phase:
Percent complete:
Active lanes:
Blocked lanes:
Paused/deferred lanes:
Accepted work:
Rejected/superseded work:
Next task:
Ready parallel tasks:
Ready-but-undispatched tasks and reason:
Evidence refs:
Visual artifact refs, if any:
Residual risk:
```

Rules:

- Update after every harvest or accepted/revised/blocking decision.
- MVP acceptance inside a full-product goal is a phase transition, not final closure.
- A module/subline pause is not a project pause if other safe product-progress waves remain.

## Lane Roster Entry

```text
Lane ID:
Thread ID or pending target:
Planned title:
Primary role: CEO/PM/Architect | Implementation | Review/QA | Product/UX | Knowledge/Memory | Research/Docs | Contractor/Subagent
Workspace:
Canonical project root:
Worktree readiness: ready | repo_baseline_required | local_single_writer_only | not_applicable
Allowed write-set:
Do not touch:
Task card path or summary:
Thread operation permission: worker-only | review-only | may-create-route-fork | read-only
Contractor/subagent policy:
Callback policy:
Stop condition:
Status: planned | dispatched | running | waitingOnApproval | review | accepted | revise | blocked | superseded | stale | role_contamination | stale_lane_reference | stale_no_evidence
Last evidence ref:
Last harvest time:
Next harvest action:
Supersedes / superseded by:
```

Rules:

- Default thread operation permission is `worker-only`, `review-only`, or `read-only`; only CEO/router lanes may create, fork, or route unless explicitly granted.
- Missing thread ids are `stale_lane_reference` until locator fallback runs.
- Worker self-routing, delegating, waiting on another worker, or inspecting CEO state without permission is `role_contamination`.
- Contractor/subagent use is denied by default for durable lanes unless the task card grants bounded outside help and requires a contractor trace.

## Harvest Driver

```text
Program Goal ID:
Primary driver: runtime_goal | immediate_sync | explicit_next_time | heartbeat
Runtime Goal ID/status:
Heartbeat/automation ID if any:
Scope: program_main | worker_local | external_reminder | fallback
Expected reports:
Evidence to inspect:
Next harvest trigger:
Duplicate driver status: none | superseded_by_runtime_goal | local_only | external_only
Stop condition:
```

Rules:

- One Program Goal should have one primary harvest driver.
- Active runtime Goal bound to the Program Goal Brief can be primary; do not also run a co-primary project-main heartbeat.
- Heartbeats are for lane callbacks or fallback, not the project source of truth.

## Decision Record

```text
Decision: accept | revise | block | supersede
Scope: lane | module | phase | program
Reason/subreason: broken_ceo_thread | role_contamination | stale_lane_reference | stale_no_evidence | insufficient_evidence | out_of_scope | conflict | blocker | none
Evidence inspected:
Tests or artifacts checked:
Files or write-set reviewed:
Residual risk:
Next owner:
Next action:
Memory writeback candidate or skipped reason:
Timestamp:
```

Rules:

- `block` at program scope requires a real repeated blocker and no safe product-progress, review, audit, docs, rerouting, or portfolio wave.
- `pause` or `block` at lane/module scope must trigger a Program Goal portfolio check.
- Callback is a signal, not acceptance evidence by itself.

## ThreadRecoveryPacket

Use this when a CEO/project-main thread or long heartbeat target is broken, context-exhausted, unreadable, or repeatedly empty.

```text
Broken thread ID:
Thread title:
Canonical project root:
Broken reason:
Paused automation/heartbeat ID:
Recommended read order:
Current Program Goal Brief path:
Compact project memory refs:
Known active worker/review thread ids:
Latest accepted decisions:
Open risks/blockers:
Vault/sourceRefs pointers:
Visual artifact index:
Raw/cold evidence gate:
Replacement CEO thread ID or placeholder:
Next safe action:
Receipt/evidence card path:
```

Rules:

- Do not fork the broken thread.
- Do not copy the full old chat.
- New takeover thread reads compact packet/project docs first; raw/vault session remains cold evidence under gate.

## Evidence / Memory Candidate

```text
Candidate ID:
Type: decision | handoff | bug | experience | knowledge | preference | tool-skill | cross-project | contractor-trace | visual-evidence
Lesson / claim:
Applies to:
Do not apply to:
Source refs:
Visual artifact refs, if any:
Evidence inspected:
Visual evidence inspected: paths + hashes + summaries only; no image bytes/base64/data:image
Tests or artifacts:
Contractor trace, if applicable:
Confidence: low | medium | high
Status: candidate | active | rejected | archived
Promotion boundary:
Owner: CEO | memory provider | user-confirmed
```

Promotion rules:

- Source-backed accepted low-risk evidence may become active/curated through the memory provider policy.
- Heuristic, history-derived, user-preference, tool-skill, cross-project, security/privacy, archive/compact/restore, or executable/install lessons remain candidate/review unless confirmed.
- Guardian/equivalent history tools may provide provenance but do not own project memory.

## Task Card State Fields

Use these fields when a task card needs resumable state:

```text
Parent Program Goal ID:
Lane ID:
Thread operation:
Worktree readiness:
Contractor/subagent policy:
Callback policy:
Locator anchors:
Knowledge provider mode:
Memory Runtime query:
Memory Runtime result:
  memoryMode:
  memoryLayers:
  recallPlan:
Memory Runtime skipped/unavailable reason:
Context/history budget:
Visual evidence policy:
Image budget:
Retrieved source refs:
Top memory items:
Writeback target:
Promotion boundary:
Harvest driver:
Stop condition:
```


## Project Scale Record

```text
Project scale: tiny | small | medium | large | program
Task scale: tiny | small | medium | large | program
Scale evidence:
Operating consequence:
  Goal required:
  Memory Runtime required:
  Warm Anchor required:
  Staffing Plan required:
  Lane count target:
  Harvest driver:
```

## Autopilot Startup Card

```text
Project scale:
Task scale:
Canonical project root:
Program Goal Brief:
Runtime Goal:
Memory Runtime result:
Long-Term Memory Anchor Gate:
Current phase:
Completion Dashboard:
Ready task graph:
Worktree readiness:
Lane reuse candidates:
Lane count decision:
Staffing Plan:
Harvest driver:
Review / audit plan:
Memory writeback plan:
Bootstrap exit decision:
```

## Bootstrap Exit Decision

```text
Next mode: Core Team execution | Core Team harvest | CEO-only bounded | configured workflow | direct CEO fallback
Why not continue CEO-only:
If CEO-only continues, reason:
Staffing check required:
Next routed lane/review:
Stop condition:
```

## Staffing Plan

```text
CEO role:
Implementation lanes:
Review lanes:
UX/Product lanes:
QA/Test lanes:
Memory/Knowledge lane:
Contractor/subagent use:
Lane count decision: 0 | 1 | 2 | 3 | 3-5 | pipeline
Why not more lanes:
Why not fewer lanes:
Thread reuse:
New thread needed:
Worktree/canonical mode:
```

## Proof Loop Fuse Record

```text
Consecutive CEO-only proof/support count:
Last product-facing wave:
Current proof value:
Risk of local optimization:
Staffing check:
Warm Anchor required:
Next product-facing action:
Neutral review needed:
CEO-only continuation reason:
Max one-slice stop condition:
Next staffing checkpoint:
```

## Long-Term Memory Anchor Gate Record

```text
Hot memory used:
Warm anchor used:
Direction check: aligned | drifting | conflict | insufficient evidence
Correction if drifting:
Blocked or revised task:
Source refs:
Cold history read: yes/no
Cold read reason/source range/token budget:
```
