# CEO Flow State Schema

Use this reference when CEO Flow needs a compact, durable state contract for Program Goals, lane rosters, harvest drivers, decisions, recovery packets, and memory writeback. These schemas are lightweight Markdown contracts, not a workflow runtime or database.

## Contents

- Program Goal, dashboard, roster, harvest driver, decision, and recovery packet
- Evidence/memory candidate and full task-card field catalog
- Project scale, Autopilot, bootstrap, staffing, and proof-loop records
- Memory, context, continuity, receipt, repo, and Slice Closure gate records

## Principles

1. Keep state document-first and source-backed.
2. Store only the minimum fields needed to resume, harvest, review, and accept/revise/block.
3. Program Goal Brief is the source of truth; runtime Codex Goal is continuity support only.
4. Terminal states require evidence or an explicit scoped blocker.
5. Do not recreate legacy task pools, leases, supervisors, review queues, or completion ledgers unless the project explicitly enables a configured workflow.

## Program Goal Brief

For a cross-project task, pair the brief with the workspace-set record below instead of treating its cwd as a canonical project root.

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
Context Governor:
  inputTokens:
  estimatedContextTokens:
  estimatedContextBytes:
  cumulativeInputTokens:
  fallbackRate:
  takeoverGeneration:
  duplicateInjectionCount:
  oldThreadStopReason:
  decision:
  nextAction:
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
Project Continuity Gate:
  triggered/reason/role coverage:
  exact projectPath/projectId:
  required slots:
  pages read / pagination complete:
  mandatory returned/total:
  partial/recoveryReady:
  sourceRefs:
Memory Runtime trigger receipts:
  retrieve_context:
  retrieve_precedent:
  writeback_evidence:
Runtime event observations:
Autopilot Startup Card:
Staffing Plan:
Long-Term Memory Anchor Gate:
Proof Loop Fuse:
Memory Recovery Freeze Gate:
Repo Baseline Gate:
Memory / knowledge writeback:
Lightweight state discipline:
  State source of truth:
  Last accepted state transition:
  Terminal evidence required:
  Blocker level: none | lane_local | module_only | project | external
Last updated:
```

## Cross-Project Workspace Set

```text
Artifact root: absolute output path; not a project identity
Project workspaces, ordered:
  - projectKey: stable task-local key
    workspace: exact absolute project root
    projectId: known id or null until that root verifies
Active projectKey:
Bootstrap mode: lazy_ordered
Per-project status: pending | ready | stale | blocked
Per-project ledger ref:
```

Freeze the ordered list at task start. `projectId=null` on the host task is neutral and never authorizes repo inference from cwd. Verify, retrieve/prepare, generation, authority, checkpoint, receipt, source refs, refresh, and writeback remain independent per `projectKey`; never merge or compare them across projects. Bootstrap one project at a time, inject only its compact packet, and then advance lazily. A stale project pauses only its lanes while other verified projects and neutral artifact work continue.

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
Worktree readiness: ready | repo_baseline_required | local_single_writer_only | read_only_only | not_applicable
Repo baseline / dirty budget:
File ownership:
Allowed write-set:
Do not touch:
Task card path or summary:
Thread operation permission: worker-only | review-only | may-create-route-fork | read-only
Interaction surface: CEO-only | user-visible-by-request
Lane visibility: durable-visible | background-contractor
User contact policy: CEO-mediated
Escalation route: callback-to-CEO
Contractor/subagent policy:
Model routing mode: inherit | auto-class | pinned | host-auto
Routing surface:
Mapping source:
Available class candidates / reasoning levels:
Unsupported controls:
Model requirement: preferred | exact
Reasoning requirement: preferred | exact
Required capability: inherit | fast | balanced | frontier
Requested model or class:
Requested reasoning:
Routing reason / fallback order:
Cost/latency priority:
Spending authorization source / budget ceiling:
Dispatch/candidate attempt budget:
Actual model/reasoning used:
Model routing result: applied | inherited | degraded | unavailable
Model routing reason code: none | model_route_unavailable | reasoning_route_unavailable | spending_not_authorized | mapping_insufficient
External Harness adapter policy id/digest:
External Harness selection surface: web_session | cli_profile | cli_patch | unsupported
External Harness selector / requested capability class:
External Harness requested/actual model and reasoning:
External Harness identity proof / route applied / route verified / global-default inherited:
External Harness usage / elapsed / cost availability and source-backed price observation:
External Harness stop reason / task success / changed paths / commands / diff / tests:
External Harness fallback receipt / CEO invariant receipt:
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
Status after context/memory freeze: active | unbind_required | unbound | superseded | rebound_to_takeover
Old thread stop reason:
Stop condition:
```

Rules:

- One Program Goal should have one primary harvest driver.
- Active runtime Goal bound to the Program Goal Brief can be primary; do not also run a co-primary project-main heartbeat.
- Heartbeats are for lane callbacks or fallback, not the project source of truth.
- After Context Pressure Gate or Memory Recovery Freeze Gate fires, the old driver must be unbound, superseded, completed, blocked, or rebound to a clean takeover; it must not keep waking the old task.

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
Context generation ID:
Duplicate injection count:
Old thread stop reason:
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

## Model Request Preflight

```text
Event type: model_request_preflight
Task/thread id:
Unique request id:
Host telemetry schema/source/scope: ceo_host_context_telemetry_v1 / codex_host / current_post_compaction_context
Captured at / content-addressed Host telemetry receipt id:
Host transport mode: existing_host_proxy | standalone_test_server
Host connection state: connected | desktop_host_connection_unavailable
Host telemetry state: current_snapshot | host_telemetry_snapshot_unavailable | host_telemetry_snapshot_invalid
Last real request input tokens:
Current post-compaction context tokens / bytes:
Projected next-request input tokens:
Model context window tokens / reserved output tokens:
Cumulative input tokens: accounting/advisory only; never current-context input
Context compaction count / source: non-negative integer / codex_host_turn_summaries
Task compaction rotation limit: 2; count is task-scoped and never inherited by replacement
Effective preflight limit: min(90% configured threshold, model window - reserved output)
Consumed request id ledger:
Decision / freeze reason:
```

One request id authorizes at most one Host-measured current-task model execution or lifecycle transition. Missing or invalid telemetry cannot open replacement, Goal-transfer, context-replacement, takeover-archive, or external Provider execution. Takeover validation alone is not model-execution authorization.

## Native Codex Lane Dispatch

```text
Event type: codex_lane_dispatch
Dispatch requested: true
Execution backend: codex_native
Routing surface: visible_thread | subagent
Parent CEO task / bounded lane role / exact write-set:
External Harness / paid Provider / lifecycle controls: false
Decision / allowLaneDispatch / Host required=false:
```

This event authorizes only creation of a bounded native Codex implementation or review lane through the built-in task/subagent surface. It does not authorize a model request inside the current CEO, an external Harness, paid Provider, takeover/replacement, Goal transfer, context replacement, or archive operation. Frozen-task, sticky-global-block, source-authority, and forbidden-payload gates still apply. Ambiguous legacy dispatch events remain on the strict preflight path.

## Clean Context Ingress Receipt

```text
Schema: ceo_context_ingress_receipt_v1
Task id / receipt SHA-256:
Retained context tokens: <=30000
Thread history mode: none | compact_wait_threads | recovery_packet_only
Full thread history loaded: false
New focused references: <=1 / path / SHA-256
Previously loaded reference SHA ledger: task-scoped; duplicates denied
Tool outputs: summary tokens / serialized bytes / rawBytesIncluded=false / artifact SHA when oversized
Decision / typed blocker:
```

## Host Lifecycle ACK

```text
Schema: ceo_host_execution_ack_v1
Plan SHA-256 / actionReceiptsSha256:
Frozen task / replacement task:
Old execution stopped / old Goal paused / old Goal cleared / wakeups stopped:
Replacement created / compact packet injected / contextMode=replace:
Replacement Goal bound and active / activeGoalCount=1:
Old task archived / harvest driver transferred:
Retained context tokens: <=30000
Host replacement ledger: frozen task / replacement task / creation plan SHA-256 / action receipt SHA-256
```

All lifecycle booleans are backed by actual App Server responses and postcondition reads. `actionsApplied=true` without the complete digest-bound action receipt is invalid.

## Compact Callback Receipt

```text
Schema: ceo_compact_callback_v1
Task/status/summary:
Handoff and content-addressed artifact refs:
Changed paths / commands / evidence refs / risks:
Requested model/thinking / actual model/thinking:
Routing result / proof source / content-addressed receipt id:
Trusted route receipt schema / selection surface / process-local validation:
Risk tier / verification profile:
CEO verification / neutral review / revision / process update counts:
Registered slice id / slice basis SHA-256:
Registered callback worker task id:
Callback sequence / prior callback SHA-256 / durable cumulative ledger:
Verification evidence receipt id / command receipt refs and SHA-256:
Next action / needs CEO decision:
Declared and conservative token estimate:
Serialized bytes / callback SHA-256:
Allow callback injection: yes/no
Allow candidate acceptance / acceptance gaps / slice budget exhausted:
```

Use `scripts/callback_gateway.py`; detailed reports and logs remain artifacts and never enter the CEO callback body.

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
- History-provider tools may provide provenance but do not own project memory.

## Task Card State Fields

Use these fields when a task card needs resumable state:

```text
Parent Program Goal ID:
Lane ID:
Thread operation:
Interaction surface: CEO-only | user-visible-by-request
Lane visibility: durable-visible | background-contractor
User contact policy: CEO-mediated
Escalation route: callback-to-CEO
Worktree readiness:
Contractor/subagent policy:
Model routing mode:
Routing surface / mapping source:
Available class candidates / reasoning levels / unsupported controls:
Model requirement: preferred | exact
Reasoning requirement: preferred | exact
Required capability:
Requested model or class / reasoning:
Routing reason / fallback order / cost-latency priority:
Spending authorization / ceiling / dispatch-attempt budget:
Actual model/reasoning / routing result / reason code or skipped reason:
Callback policy:
Locator anchors:
Knowledge provider mode:
Memory Runtime query:
Memory Runtime result:
  memoryMode:
  memoryLayers:
  recallPlan:
Memory Runtime skipped/unavailable reason:
Project Continuity requirement:
  triggered/reason/role coverage:
  required slots:
  exact projectPath/projectId:
  module scope / page size / max pages / token budget:
  full recovery claim allowed:
Project Continuity result:
  covered/missing/conflict/stale/review slots:
  pages / pagination complete / mandatory returned-total:
  authority verification / partial / recoveryReady:
  bounded stop reason / sourceRefs:
Memory Recovery Freeze Gate:
  triggered / reason:
  provider status:
  memoryMode / current / recoveryReady:
  project identity result:
  authority verification:
  freeze action:
  allowed evidence:
  forbidden context expansion:
  freeze receipt emitted:
  old harvest driver unbound:
  exit condition:
MemoryRuntimeTriggerReceipt:
  hook / verification / receipt id-time:
  returnedCount / tokenEstimate / durationMs / partial / warnings:
  sourceRefs / unavailable reason:
Runtime event observation:
  event type / project identity / affected thread or checkpoint:
  receipt / sourceRefs / unavailable reason:
Context/history budget:
Context Governor:
  inputTokens / estimatedContextTokens / estimatedContextBytes:
  cumulativeInputTokens:
  fallbackRate:
  takeoverGeneration:
  duplicateInjectionCount:
  invalidatedGenerationCount:
  oldThreadStopReason:
  decision / nextAction:
Context Injection Ledger:
  taskId:
  injectedGenerationIds:
  lastGenerationBasis:
  invalidatedGenerationIds:
  legacyInjectionOwnerKey: compatibility owner; migrate top-level fields only on matching task/thread
  taskRuntimeLedger: task-scoped turn and cumulative-token counters
  frozenTaskKeys: unsafe old execution surfaces; never remove to resume them
  freezeReceiptsByTask: at most one compact freeze receipt per task
  freezeByTask: task-scoped immutable freeze reason and receipt state
  recoveryTransitions: replacementForTaskId / fresh generation / replacement task / verified_replacement_ready
  programBlockAuditLedger: workspace+blocker key / exact authority tuple / fully replayed source-backed envelopes / three consecutive verified receipts / last qualifying assessment
  programGlobalBlock: sticky active / ledgerKey / workspace / blocker / authority tuple / proof digest / activation / known generations / trusted recovery evidence
  Global blocker authority registry: authorityId / issuer / auditSeriesId / sourceRoot; configured outside untrusted event JSON
  Global blocker receipt: trusted control entry / authorityId+issuer+explicit sourceRoot / in-workspace JSON sourceRef path+sha256+auditSeriesId / workspace / strict RFC3339 observedAt / scope=program_goal / blockerCode / exact integer safeReadyLaneCount=0 / exact boolean reroute+external-state fields / sequence / previousReceiptSha256 / receiptSha256
  Global blocker recovery: trusted process-local entry / exact proof+workspace+blocker+replacement task / fresh verified contextGenerationId / recoveryReceiptSha256 / clear only after task-ledger commit
Direct Refresh Binding:
  driver: scripts/refresh_binding_driver.py
  workspace / lane or module:
  previousCheckpointId:
  expectedProjectIdentitySha256:
  expectedScanSha256:
  acceptedEvidenceReceipt:
  acceptedEvidenceReceiptDigest: app-owned 64-hex digest; persist before Runtime call
  acceptedChangedPaths / acceptedPathDigest / exact sourceRefs:
  lane:
  refresh idempotency key: sha256(canonical workspace + identity + scan + prior checkpoint + receipt ID + receipt digest + sorted-path digest + lane)
  outcome: refreshKey / outcomeDigest 64-hex / outcomeVerification=app_owned_authenticated
  refresh call count:
  refresh namespace: registered projectWorkspaces key or single-project sha256(canonical workspace + verified identity); never caller label
  receiptId / authorizedCheckpointId / contextGenerationId:
  verifiedRefresh governor commit: refreshKey / generation / scan / checkpoint / authorityReceiptId
  durability confirmation: ceo_refresh_durability_v1 / refreshKey / exact driver+governor commitDigest / status=confirmed
  transaction receipts per governor/driver/confirmation file: pending .uncertain v1 -> persistent .confirmed v2 / outcome=committed_postimage / target / previousSha256 / intendedSha256 / committedSha256=intendedSha256 / transactionId; previousSha256 is never an authorized completed outcome; all authorization reads require exact committed target bytes, and only target+sidecars all absent means empty initial state
  restart reconciliation: marker preimage-or-postimage confirmation / blocked turn / zero Runtime refresh / exact three-ledger coherence before resume
  started-at-Runtime-boundary: one exact read-only query_refresh_outcome / never replay refresh / absent or invalid query remains lane-local no-poll
  verify matched / current / recoveryReady:
  lifecycleState: active | lane_paused_recoverable | lane_paused_pending_acceptance | lane_paused_user_authorization | task_context_frozen_replace_required | program_blocked_global
  userAuthorizationRequired / autoRecoveryEligible / resumeProgramGoal / clearHistoricalGoalBlocked:
  lane status / programGoalBlocked / unrelated lanes:
  knowledge task messages / paid Provider calls / retry:
  allowToolCalls: legacy conservative aggregate; false while blocked
  allowProjectToolCalls / allowProviderCalls:
  allowRecoveryControlTools / recoveryControlToolAllowlist:
  state persistence: advisory lock / unique temp / file fsync / durable uncertainty marker / atomic replace / directory fsync / CAS digest / explicit fail-closed durability error
  state privacy: new file 0600 / preserve existing owner-only mode / reject group-or-other access / native ACL verification required per platform
  control payload limits: actual serialized bytes / max depth / nodes / width / aggregate string bytes / sourceRefs; inspect before deepcopy
Host Control Receipt:
  adapter: scripts/host_control_adapter.py
  known typed booleans / lifecycle / decision / recovery tool allowlist:
  projectTools / providerCalls / recoveryTools:
  programGoal: no_change | keep_blocked | clear_and_resume
  context: no_change | replace
  currentTask: exact task id / allow-or-deny
  frozenTask: exact task id / deny only
  harvestDriver: keep | unbind | rebind / exact fromTaskId / exact toTaskId
  lifecycle driver: scripts/task_lifecycle_driver.py / action-plan SHA-256 / exact Host ACK
  governorControlSha256:
Visual evidence policy:
Visual transport mode: zero-payload-local-analysis | bounded-model-vision
Model-visible image budget:
Forbidden visual tools/returns:
Visual transport receipt: mode / modelVisibleImagesUsed / modelVisibleImageBytes / worker-thread id / reason
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
Artifact root (cross-project only):
Ordered projectWorkspaces / active projectKey (cross-project only):
Program Goal Brief:
Runtime Goal:
Memory Runtime result:
Context Governor:
Long-Term Memory Anchor Gate:
Memory Recovery Freeze Gate:
Current phase:
Completion Dashboard:
Ready task graph:
Worktree readiness:
Repo Baseline Gate / dirty budget:
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
Next mode: Core Team execution | Core Team harvest | CEO-only bounded | configured workflow | memory repair / fresh takeover | direct CEO fallback
Why not continue CEO-only:
If CEO-only continues, reason:
Memory readiness:
If memory is stale/unresolved, freeze action:
Staffing check required:
Next routed lane/review:
Stop condition:
```

## Memory Recovery Freeze Gate Record

```text
Triggered: yes/no
Reason: fallback_stale | current_false | recovery_not_ready | project_unresolved | project_scope_mismatch | authority_unavailable_for_claim | schema_or_cursor_failure | none
Project scale / task scale:
Provider:
Provider status:
MemoryMode:
Current:
RecoveryReady:
Project identity result:
Authority verification:
Allowed evidence while frozen:
Forbidden context expansion:
Freeze receipt emitted:
Old harvest driver unbound:
Next action: memory repair | fresh CEO takeover | compact handoff | bounded source audit | user decision
Exit condition:
```

Rules:

- For large/program continuation, takeover, recovery, or major direction correction, stale/unresolved memory is an execution-routing event, not a soft warning.
- Do not continue product implementation, polling, or old-thread harvest loops from a bloated CEO/project-main thread while this gate is triggered.
- Emit one freeze receipt only; subsequent wakeups must stop, unbind, or route to the clean takeover instead of repeating pause status.
- If execution must proceed before repair, limit it to one bounded source-backed slice and do not claim current memory or recovery readiness.

## Context Governor Record

```text
Schema: ceo_context_governor_v1
Thread ID:
Task ID:
Input tokens:
Estimated context tokens:
Estimated context bytes:
Cumulative input tokens:
Fallback rate:
Takeover generation:
Duplicate injection count:
Old thread stop reason:
Decision: allow | block | freeze
Reason:
Allow old thread execution: yes/no
Allow tool calls: yes/no
Allow provider calls: yes/no
Unbind harvest driver: yes/no
Next action:
Blocker:
```

Rules:

- Run from compact JSON metrics/state only; do not include raw chat, raw session, full logs, SQLite, credentials, API keys, image bodies, or base64.
- Default hard pressure thresholds are 120000 per-turn input tokens, 120000 estimated context tokens, 10000000 cumulative input tokens per task, or 50 MB estimated context/session bytes.
- Use `contextGenerationId` as an idempotency key; one generation can be injected at most once per task.
- HEAD, scan hash, project identity, postimage, or verified memory state changes invalidate the old generation and require refresh binding plus a new generation before reinjection.
- `replace_long_thread_context` is mandatory for takeover injection; never append takeover packets after a long old context.
- Heartbeat, tool-result, commentary, and wake-check events skip memory retrieval and injection unless the lifecycle gate changed.
- Use `scripts/context_governor.py` for deterministic checks when practical.

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
Repo baseline mode:
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

## Project Continuity Gate Record

```text
Triggered: yes/no
Trigger reason:
Role coverage: ceo_project | worker_module | reviewer_acceptance
Required slots:
Exact projectPath/projectId:
Module scope:
Page size / max pages / token budget:
Schema/version:
Covered/missing/conflict/stale/review slots:
Pages read:
Pagination complete:
Mandatory returned/total:
Authority verification:
Partial: yes/no
Bounded stop/failure reason:
RecoveryReady:
SourceRefs:
Review queue consulted:
Diagnostics consulted:
```

Rules:

- CEO takeover, old-thread recovery, and major direction correction use all 14 mandatory slots.
- Worker/reviewer packets use role-required slots only.
- Incomplete pagination or helper-only advisory results cannot claim `recoveryReady`.
- Project identity mismatch, invalid cursor, changed manifest, truncation, or page/token bound fails closed to partial.

## Memory Runtime Trigger Receipt Record

```text
Hook: retrieve_context | retrieve_precedent | writeback_evidence
Verification: verified | partial | unverified
Receipt ID/time:
Exact projectPath:
Thread/task scope:
Returned count:
Token estimate:
Duration ms:
Partial/warnings:
SourceRefs:
Unavailable reason:
```

Rules:

- Prepared prompts or intended calls are not execution evidence.
- Match receipts by hook, exact project path, operation window, and thread/task scope when present.
- Missing receipt capability remains unverified; do not claim the hook actually executed.

## Runtime Event Observation Record

```text
Event type: task_checkpoint | broken_thread | stale_lane_reference | thread_takeover | user_rule_update | heartbeat_fuse
Exact projectPath/projectId:
Affected thread/checkpoint:
Summary:
Decisions/open risks/next action:
SourceRefs:
Receipt/status:
Unavailable reason:
```


## Repo Baseline Gate Record

```text
Dirty count:
Untracked critical source/config/test count:
Untracked docs/artifacts count:
Tracked baseline covers package/config/build:
Tracked baseline covers task source/test roots:
Worktree can reproduce project without canonical-only files:
Dirty budget state: green | yellow | red
Decision: ready | baseline_required | canonical_single_writer_only | read_only_only
Controlled baseline task needed: yes/no
Reason:
```

## Slice Closure Gate Record

```text
Task ID:
Changed files:
Untracked files:
New untracked source/config/test/docs count:
Allowed write-set compliance:
Shared files touched:
Package/config changed: yes/no
Artifacts/docs are local evidence only: yes/no
Worktree readiness impact: improved | unchanged | worse | unknown
Baseline action needed: none | pathspec proposal | controlled baseline task | block next worktree writer
Evidence refs:
```
