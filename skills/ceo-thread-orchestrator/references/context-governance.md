# Context And Takeover Governance

Use this reference for context pressure, sticky freeze, strict app-owned takeover validation, generation idempotency, exact scan, and refresh binding. Execute deterministic checks with `scripts/context_governor.py` using compact JSON only.

## Contents

- Context Pressure Gate
- Memory Recovery Freeze Gate
- Prepare Takeover contract
- Generation idempotency
- Verify, exact scan, and refresh binding
- Ownership and exit rules

## Cross-Project Lazy Bootstrap

When a task has a neutral cwd, `projectId=null`, or multiple explicit targets, require an ordered `projectWorkspaces` list of `{projectKey, workspace, projectId?}`. The cwd may be an `artifactRoot` only; do not pass it to Memory Runtime or guess a repository from it.

Maintain one task+project ledger per root for workspace, resolved project id, generations/basis, authority, checkpoint, and bootstrap status. Run `scripts/cross_project_bootstrap_driver.py` as the unique local integration driver: it verifies and prepares only the active project, returns at most one validated compact packet, then lazily advances on the next call. A packet must name that workspace and resolved project id, and source refs must remain below that root. Cross-project writeback requires a non-empty sourceRefs array plus a structured receipt whose id, workspace, and projectId bind to the active root. Cross-root project identity, checkpoint, receipt, source refs, refresh, or writeback evidence fails closed before ledger mutation. A stale project pauses only that project's lanes; other ready projects continue and `programGoalBlocked=false`.

## Context Pressure Gate

Run the governor for large/program work, takeover/recovery, active runtime Goals, heartbeat harvest, or an old CEO task that may be carrying excessive context.

Default hard thresholds are task-scoped:

```text
per-turn input tokens >= 120000
estimated context tokens >= 120000
per-task cumulative input tokens: advisory/accounting only; never current-context evidence
estimated context/session bytes >= 50 MB
```

Every model-bound execution must enter through `scripts/task_lifecycle_driver.py` with `eventType=model_request_preflight` and a unique task-scoped `requestId`. Pressure metrics are accepted only from a process-local Host capability plus a content-addressed `ceo_host_context_telemetry_v1` receipt with `telemetrySource=codex_host`, `metricScope=current_post_compaction_context`, strict `capturedAt`, exact task id, and verified digest. The receipt separates the last real request input, current post-compaction context, projected next request, model window, reserved output, cumulative input, and Host-observed compaction count. Count compactions only from paginated `thread/turns/list` summary items whose type is `contextCompaction`; record `compactionCountSource=codex_host_turn_summaries`, de-duplicate item ids, and never load raw turn bodies for this metric. Goal `tokensUsed`, account usage, reasoning/output usage, caller estimates, cumulative totals, and the number of compactions must never substitute for current retained context. Missing, stale, caller-forged, duplicate, inconsistent, or idle-without-snapshot Host telemetry returns `lane_paused_recoverable` without freezing, Host apply, or model-input accounting. `thread/resume` is not a telemetry query and an idle task's lack of `thread/tokenUsage/updated` must never be interpreted as zero or guessed context.

The driver freezes before dispatch when the Host-projected next request reaches the smaller of 90% of the configured context threshold or the model window minus reserved output. It also rotates an old task at the next preflight after its second Host-confirmed compaction, using `context_compaction_rotation_limit`: finish the current bounded slice, stop further dispatch, create a new empty task, inject only the compact recovery packet, transfer the Goal/harvest driver, and leave the old task permanently frozen. Compaction count is task-scoped, monotonic, and source-backed; a lower later count for the same task returns recoverable `host_context_compaction_count_regressed` rather than postponing rotation. A clean replacement starts from its own Host count and never inherits the old count. A clean takeover also has a hard retained-context ceiling of 30000 tokens.

Host pressure preflight governs the current task's measured context and every lifecycle operation that can freeze/replace a CEO, transfer a Goal or harvest driver, replace context, or archive during takeover. A takeover packet cannot open project or Provider calls until a fresh preflight passes.

When one of those Host-backed current-task or lifecycle operations lacks a valid fresh receipt, return the typed lane-local reason `model_request_preflight_required`; do not infer telemetry or claim that a lifecycle action ran.

Creating an ordinary native Codex implementation or review lane is a separate control path. It does not require the Desktop Host socket or a context telemetry snapshot. Use `eventType=codex_lane_dispatch`, `dispatchRequested=true`, `executionBackend=codex_native`, and `routingSurface=visible_thread|subagent`. This path authorizes only bounded native lane creation: Provider/external-Harness calls, paid dispatch, takeover/replacement, Goal transfer, context replacement, and archive controls are rejected. A frozen CEO, sticky global block, authority drift, forbidden payload, or unaccepted source change still fails closed. Legacy ambiguous `dispatchRequested` events continue to require preflight so callers cannot relabel lifecycle or external work as an ordinary lane.

If the Desktop Host socket is unavailable, disable automatic context rotation, Goal transfer, context replacement, and takeover archive operations for the affected CEO lifecycle. Do not block unrelated native Codex implementation or review lanes that satisfy the strict dispatch contract.

Projects may lower thresholds. Raising them requires a bounded explicit reason and never bypasses raw/Cold gates.

Record input tokens, estimated context tokens/bytes, cumulative input, fallback rate, takeover generation, duplicate injections, invalidated generations, old-task stop reason, decision, and next action.

Feed no raw chats, sessions, complete logs, SQLite/database bodies, credentials/API keys, image bodies, or base64. If forbidden content is detected, freeze.

## Sticky Freeze

Reserve `freeze` for an unsafe execution surface: context pressure or forbidden payload. Authority drift, a failed binding refresh, and unaccepted source changes are recoverable lane pauses, not sticky task freezes.

When the governor returns `freeze`:

1. Fail closed and emit at most one compact freeze receipt.
2. Set old-task execution, tool calls, and provider calls to false.
3. Stop, unbind, complete, block, supersede, or rebind the old harvest driver.
4. Reject later heartbeat, tool-result, status, takeover, or low-token events in that same frozen task with `stop_old_task_no_repeat`.
5. Move recovery to a compact handoff or clean replacement task. Preserve the old task in `frozenTaskKeys`; do not carry its cumulative-token counter into the replacement.
6. A different task explicitly declaring `recoveryRequested=true` and `replacementForTaskId=<frozen task>` may automatically resume the Program Goal after a fresh packet passes all six authority gates and generation checks. The generation must not have been injected in the frozen task. Record one `verified_replacement_ready` transition, clear historical Host Goal `blocked` when the host supports it, and never unfreeze the old task. An ordinary worker packet cannot clear an unrelated task freeze.

Runtime Goals, heartbeats, monitors, automations, and 5-7 second wakeups must not keep producing paused/status responses from the frozen task.

The production Host executor must support both lifecycle phases. `create_clean_replacement` creates the empty task, injects the compact recovery packet, transfers the Goal without overlap, archives the old task, and returns a digest-bound ACK. Persist the exact frozen-task/replacement-task pair plus creation plan and action-receipt digests in `hostReplacementLedger`. After a fresh takeover passes, `activate_clean_replacement` must match that ledger and reload the completed creation journal before revalidating exact old/current task ids, old Goal absence, current Goal activity, compact ingress receipt, retained-context ceiling, archive state/action, and harvest binding. An unrelated active task cannot substitute for the created replacement. Activation creates no second task and copies no history. FakeHost-only support is not acceptance evidence.

`decision=block` also fails closed for the affected product dispatch and Provider lane. Keep legacy `allowToolCalls=false`; use `allowProjectToolCalls=false` plus `allowProviderCalls=false` for that boundary. Only `allowRecoveryControlTools=true` with an explicit `recoveryControlToolAllowlist` may authorize the one structured control action, such as `verify_project`, `scan_workspace`, `prepare_takeover`, or `refresh_binding_driver`. This never authorizes shell/project writes or model/Provider calls. Heartbeat, tool-result, commentary, wake-check, and status-poll events are read-only control receipts: they do not retrieve/inject memory and never authorize project or Provider calls. A distinct worker/task may continue an unrelated safe lane, but it cannot claim `resumeProgramGoal`, clear a frozen task, or replace that task without naming it and passing the fresh takeover gate.

## Memory Recovery Freeze Gate

Trigger fail-closed memory handling for a required large/program continuation, takeover, recovery, or major direction correction when any condition holds:

- `memoryMode=fallback_stale`;
- `current=false` or `recoveryReady=false`;
- `authorityVerification!=app_owned_verified` for app-owned takeover;
- `project_unresolved`, scope/identity mismatch, incompatible schema, invalid cursor, missing pages, or missing current ProjectBrain;
- `returnedCount<=0` or `takeover.shouldInject!=true`;
- changed HEAD, scan hash, project identity, postimage, or verified memory state without accepted refresh evidence;
- takeover packet missing/invalid/over the configured ceiling (never above 10000 tokens), contains forbidden payloads, or violates generation rules.

Consequences for authority/binding defects are `lane_paused_recoverable`: one bounded read-only verify/scan, then refresh only with formal accepted evidence. Unrelated lanes continue and `programGoalBlocked=false`. Context pressure or forbidden payload still uses sticky task freeze and replacement.

General consequences:

- switch to `memory repair / fresh takeover`;
- stop product implementation, repeated polling, and old-task harvest/tool loops;
- do not claim current state, recovery readiness, completion, or remembered blockers from the failed provider;
- do not compensate with full chat/history, giant knowledge files, screenshots/base64, or complete worker logs;
- output one structured blocker with one `nextAction`;
- build a compact ThreadRecoveryPacket from canonical docs, Program Goal state, accepted evidence, source refs, and clearly advisory stale summaries.

Exit automatically after the provider is current enough for the requested claim or recovery moves to a clean verified takeover. User authorization is not required for ordinary verify, exact scan, formal accepted refresh, bounded local tests, neutral QA, or an already-approved fallback inside the task card.

## Prepare Takeover Contract

Request:

```text
prepare_takeover(projectPath, projectId, sourceThreadId,
                 queryType=thread_recovery, tokenBudget=2200,
                 maxTokenBudget<=10000)
```

Accept only a compact packet containing Hot/Warm memory, required continuity, graph/task state, source refs, generation basis, warnings, and authority fields. `tokenEstimate` must be a positive integer no greater than 10000. Structured freeze output must expose `preferredTokens=2200` separately from `maxTokens=10000`. Treat 2200 as the preferred takeover starting budget, not a completeness target; allow bounded growth only when the minimum authority-backed anchors do not fit. A fixed-cost caller may require `strictTokenBudget=true`; never default to requesting 10000.

The six mandatory app-owned injection conditions are immutable:

```text
memoryMode == app_owned_memory_core
authorityVerification == app_owned_verified
current == true
recoveryReady == true
returnedCount > 0
takeover.shouldInject == true
```

Reject missing authority fields, helper-only authority, raw chat/session, messages/transcripts, body/content/text payloads, image/base64/data:image/input_image, full logs, complete knowledge bodies, Cold/raw bodies, credentials/API keys, SQLite/database bodies, out-of-scope source refs, and unknown content sections.

Use `replace_long_thread_context`; never append a takeover packet after long old context. The old task remains a read-only evidence source, while the clean task runs verify/prepare before execution.

## Generation Idempotency

Require `contextGenerationId` plus generation basis containing at least HEAD, scan hash, and verified memory state hash. Track injected and invalidated generations per task, and per task+project for cross-project work.

- Inject one generation at most once per task.
- A deterministic generation may be injected once in multiple distinct `taskId` ledgers, for example once in CEO task A and once in Worker task B.
- Never compare a Worker generation against a CEO generation as a project-global ban; generation idempotency is task-scoped.
- Never merge generations across two project ledgers in one task; the same value may be injected once per project after each packet independently passes authority and scope gates.
- Same generation again: block with `duplicate_context_generation` and skip injection.
- Same generation with changed basis: block with `rotate_generation_required`.
- New generation with unchanged basis: block with `generation_basis_unchanged`.
- Permit a new generation only after HEAD, scan, project identity, postimage, or verified memory state changes and the new packet passes all authority/content checks.
- Invalidate prior generations after an accepted basis change.

Legacy top-level `injectedGenerationIds` and `lastGenerationBasis` migrate into a per-task ledger only when their recorded task/thread owner matches the current task. Unknown or different ownership never migrates across tasks.

## Verify, Exact Scan, And Refresh Binding

At task start, resume, direction switch, and pre-dispatch, the current CEO/worker task calls the app-owned Runtime directly. Do not relay ordinary verify, scan, prepare, refresh, or synchronization through a separate knowledge-maintenance Codex task.

If strict verification fails, run one bounded read-only exact scan:

- unchanged scan plus failed verification -> pause the related lane as recoverable `authority_defect` and perform one bounded local repair check;
- changed scan without accepted QA/evidence receipt -> pause only the affected lane as `unaccepted_project_change`; continue unrelated lanes;
- changed scan with accepted receipt -> `refresh_binding_required`; immediately run `scripts/refresh_binding_driver.py`, which directly refreshes, validates a new receipt/checkpoint/generation, and performs bounded verify.

Formal Runtime fields:

```text
workspace / execute=true
expectedProjectIdentitySha256 / expectedScanSha256
previousCheckpointId / acceptedEvidenceReceipt
acceptedEvidenceReceiptDigest / acceptedChangedPaths / acceptedPathDigest / lane
refreshKey = sha256(canonical full tuple)
evidence.decision=accept / bounded summary / exact sourceRefs
```

Persist the driver's canonical workspace, verified project identity, scan, prior checkpoint, accepted receipt ID plus app-owned 64-hex receipt digest, sorted changed-path digest, lane, and v2 refresh key before calling Runtime; these fields are immutable attempt evidence. Compute `acceptedPathDigest` from the canonical JSON of sorted paths, then compute `refreshKey` from the entire tuple directly. Caller labels such as `activeProjectKey` and `projectId` never alter this Runtime idempotency key. For cross-project work, accept a ledger namespace only from the frozen `projectWorkspaces` registration when key, canonical workspace, registered project id, and verified Runtime identity all match. For single-project work, derive one namespace from the governor-owned canonical workspace and verified identity recorded by the prior six-gate takeover; reject caller-supplied project labels. Never create a ledger with `setdefault` from an unregistered label. One exact v2 key permits at most one refresh. The refresh call is never repeated for that key. Post-refresh read-only verify is bounded to six total calls per key by default; after that the driver returns `verify_retry_exhausted_no_poll` until a genuinely new full tuple creates a new bounded attempt. The local controller makes no paid Provider/model calls and keeps paid retry at zero. Provider execution stays at zero until verify returns `scanBinding.matched=true`, `current=true`, and `recoveryReady=true`. Refresh failure blocks only the related lane/module, leaves `programGoalBlocked=false`, and permits unrelated conflict-free lanes to continue. A later verified refresh transitions that lane to `active` and may clear a stale historical Host Goal block.

## Lifecycle And Authorization Classes

Use exactly these control states:

- `active`: safe execution may continue.
- `lane_paused_recoverable`: local authority/tool/runtime issue; run one bounded recovery action and continue unrelated lanes.
- `lane_paused_pending_acceptance`: changed source lacks formal acceptance; do not authorize it, but do not stop the program.
- `lane_paused_user_authorization`: only credentials, new spending, destructive/irreversible action, legal/security/product-scope decision, explicit risk acceptance, or a real host approval reaches the user.
- `task_context_frozen_replace_required`: old context is unsafe; replace it with a clean task and fresh verified generation.
- `program_blocked_global`: only the trusted `evaluate_program_block_audit()` control entry may advance a pre-registered neutral-audit authority; ordinary evaluator/CLI/worker JSON can never do so. That entry requires three consecutive verified receipts for the same blocker, exact integer `safeReadyLaneCount=0`, exact booleans for no reroute and required external change, and one immutable authority tuple: authority id, issuer, audit series, and explicit absolute registered source root. Each receipt binds a distinct in-workspace JSON source and SHA-256, canonical workspace, strict timezone-qualified RFC3339 observation time, `program_goal` scope, blocker code, integer sequence, prior receipt digest, assessment fields, and its own canonical digest. Before adding a receipt, reload immutable source bytes and fully replay every prior envelope, digest, authority tuple, scope, blocker, sequence, timestamp, chain link, and assessment. Reject missing/string/bool/non-integer counts, inferred source roots, duplicates, stale/future/non-strict times, broken chains, mixed authorities, reused/changed sources, and malformed/content-mismatched evidence.

Once proven, persist `programGlobalBlock.active=true`; later ordinary evaluation remains globally closed for project/provider calls. Ordinary JSON, user-looking flags, heartbeat, worker packets, and CLI fields cannot clear it. The only exit is `evaluate_program_block_recovery()` with its process-local capability, a canonical-digested recovery receipt bound to the exact proof/workspace/blocker/replacement task, and a fresh takeover generation absent when the block was activated. The packet must pass all six app-owned authority gates and normal content/scope/generation checks; clear the block only after the generation is committed to its task ledger. Failed validation leaves the block sticky.

Persist governor, refresh-driver, and durability-confirmation ledgers through `scripts/atomic_state.py`: advisory lock, unique same-directory temporary file, file flush/fsync, atomic replace, directory fsync, and compare-and-swap when a caller read state before evaluation. Before replacing a control file, durably create its `.uncertain` transaction marker with exact target, preimage hash, postimage hash, and transaction id. After the target directory commit, write a separate durable `.confirmed` v2 receipt with `outcome=committed_postimage` and `committedSha256=intendedSha256`; only then durably remove the pending marker. Never express confirmation only as marker absence, and never authorize `previousSha256` from a completed transaction. A genuine before-replace recovery may remove its pending marker only when the target still matches the prior independently confirmed receipt; it does not promote that pending transaction or create a rollback receipt. Every authorization-relevant read, including evaluate/status/preflight, read-only CLI, write CLI, refresh/bootstrap integration, and Host adaptation, must use the same confirmed-state loader before it can return an allow or open any tool/call gate. Only the complete absence of target, `.uncertain`, and `.confirmed` is an empty initial state; an existing target without a valid matching `.confirmed` receipt is not accepted as legacy state. A pending marker, missing/malformed/forged receipt, target or receipt hash mismatch, stale writer, unsafe read mode/owner/ACL, supported directory open/fsync/close failure, or unsupported directory-fsync result is fail closed and cannot report persistence success or reopen Provider/project calls.

On restart, the integration driver checks all three pending/confirmed receipts before reading ordinary state or invoking Runtime. Reconcile an exact marked intended postimage into a committed-postimage receipt, or discard a before-replace pending transaction only against its prior independently confirmed preimage; return a blocked reconciliation receipt for that turn and make zero refresh calls. Restoring target bytes to a completed receipt's `previousSha256` is rollback/tamper, not reconciliation: confirmed reads, ordinary CLI, CAS writers, Host and Provider gates all remain closed. A confirmed receipt remains alongside the target and is revalidated against exact committed bytes; it is overwritten by the next transaction rather than deleted through another ambiguous cleanup window. A driver `verified` attempt is authorization only when the exact governor `verifiedRefresh` envelope and an independently persisted `ceo_refresh_durability_v1` commit digest match it. Missing or mismatched confirmation runs one bounded local reconciliation and remains blocked for that turn; only a later turn over the confirmed coherent state may resume. A governor CAS conflict or `governor_commit_failed` attempt follows the same reachable local commit/confirmation sequence without another refresh. Never reinterpret bytes from an operation that reported durability failure as a verified fast path merely because they are visible after restart.

If a process stops after persisting `status=started` but before recording the Runtime receipt, never replay `refresh_binding`. Reconcile only through one bounded, existing-only zero-write `query_refresh_outcome` call bound to the exact v2 tuple. Accept a query or fresh refresh outcome only when receipt ID and digest, lane, sorted paths and path digest, recomputed refresh key, 64-hex `outcomeDigest`, and `outcomeVerification=app_owned_authenticated` all match, in addition to the normal authority/checkpoint/generation gates. An absent query capability returns `runtime_outcome_query_required`; an unavailable, invalid, duplicate, tampered, or mismatched outcome returns a no-poll scoped blocker. Zhixia has supplied this as a candidate contract, but CEO Flow must continue to treat it as unavailable in installed production until both candidates freeze and cross-component fixtures pass; never synthesize success from checkpoint/profile/current state.

On a v1-to-v2 driver upgrade, compute the legacy four-field key only for replay detection. If the current full tuple has no v2 attempt but a matching legacy attempt exists, return `legacy_refresh_attempt_v2_reconciliation_required` with zero Runtime calls. Never reinterpret, migrate, or replay an old `started`, failed, refreshed, or verified attempt as a v2 authenticated outcome.

Control inputs are bounded before `deepcopy` or business evaluation. Enforce actual UTF-8 JSON bytes, depth, node count, container width, total string bytes, and sourceRefs count with an iterative walker. The takeover packet has its own actual-byte ceiling; `tokenEstimate` is supporting evidence, not authorization. Any malformed, cyclic, over-deep, over-wide, or oversized control returns a typed task freeze with project/provider calls closed rather than raising recursion/process errors.

`scripts/host_control_adapter.py` converts a governor result into strict Host actions. `scripts/task_lifecycle_driver.py` binds those controls, compact recovery data, Goal transition, context budget, and replacement action into one digest. `scripts/codex_app_server_executor.py --event <event.json> --state <state.json> --journal-dir <dir>` is the complete production entry: it connects through `codex app-server proxy` to the already-running Desktop Host, captures an exact Host telemetry snapshot, evaluates the governor, executes the lifecycle, validates the ACK, and commits confirmed state. It never silently starts another app-server process or falls back after proxy failure; `--standalone-test-server` is explicit and disposable-test-only. An optional `--host-socket` names an already-exposed control socket. The adapter uses `thread/turns/list` without items, `turn/interrupt`, `thread/goal/get|set|clear`, `thread/start`, compact `thread/inject_items`, and `thread/archive`. It pauses the old Goal before replacement creation, clears it before activating the new Goal, and then archives the old task. The ACK must include digest-bound per-action receipts proving stop, Goal transfer, compact replacement, archive, one active Goal, and driver transfer; `actionsApplied=true` alone is invalid. Ambiguous crash windows around thread creation or packet injection are journaled and never replayed because the Host API has no idempotency key for those operations. A missing control socket returns `desktop_host_connection_unavailable`; a connected idle Host without a current telemetry snapshot returns `host_telemetry_snapshot_unavailable`. Both keep the affected lane recoverably paused with project, model, and Provider calls closed and `programGoalBlocked=false`.

The Host receipt binds the exact frozen task to the exact clean task. Continue only after a matching `ceo_host_execution_ack_v1` verifies the full action receipt.

For clean replacement ingress, run `scripts/context_ingress_gateway.py`. Retained context must be at most 30000 tokens, at most one newly loaded focused reference may enter per request, the same reference SHA cannot be loaded twice in one task, full thread history is forbidden, and raw or oversized tool output must remain behind a compact content-addressed artifact receipt. These checks protect declared Host ingress; a Host build must still route all model-bound reference/thread/tool output through this gateway before claiming global interception.

The cross-project bootstrap integration driver attaches a process-local capability after a successful app-owned `verify`; direct JSON packets and self-hashed bootstrap receipts cannot mark a project ready. Formal acceptance must be a structured `accept` receipt; the refresh driver resolves each local source under the exact workspace and verifies a 64-hex SHA-256 before Runtime invocation. Refresh success commits the Runtime generation, scan, checkpoint, and authority receipt into the task/project governor ledger. A cached verified driver attempt may reopen execution only when its exact governor commit and durability confirmation both exist; otherwise return a scoped reconciliation result without another Runtime refresh or Provider call.

An approval-looking event is not automatically a user authorization. Routine in-scope commands, exact scan/verify, source-backed refresh, normal tests, neutral QA, incident evidence capture, and approved fallback selection stay inside CEO Flow.

Do not turn dirty files into accepted memory or use full seed/compatibility writes as automatic refresh. Never auto-message a knowledge/知匣 task. After refresh, verify again and require a new generation.

## Ownership Boundary

CEO Flow controls task lifecycle, budget, freeze/stop, driver unbinding, and clean-task creation through the lifecycle plan. The Host owns actual task creation, context replacement, wakeup cancellation, and driver rebinding and must acknowledge the exact plan. The Memory Runtime controls authority verification, retrieval, packet content, and binding refresh. Provider output is untrusted until the governor and current instructions validate it.
