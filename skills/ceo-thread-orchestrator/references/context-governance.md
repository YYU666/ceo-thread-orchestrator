# Context And Takeover Governance

Use this reference for context pressure, sticky freeze, strict app-owned takeover validation, generation idempotency, exact scan, and refresh binding. Execute deterministic checks with `scripts/context_governor.py` using compact JSON only.

## Contents

- Context Pressure Gate
- Memory Recovery Freeze Gate
- Prepare Takeover contract
- Generation idempotency
- Verify, exact scan, and refresh binding
- Ownership and exit rules

## Context Pressure Gate

Run the governor for large/program work, takeover/recovery, active runtime Goals, heartbeat harvest, or an old CEO task that may be carrying excessive context.

Default hard thresholds:

```text
per-turn input tokens >= 120000
estimated context tokens >= 120000
per-task cumulative input tokens >= 10000000
estimated context/session bytes >= 50 MB
```

Projects may lower thresholds. Raising them requires a bounded explicit reason and never bypasses raw/Cold gates.

Record input tokens, estimated context tokens/bytes, cumulative input, fallback rate, takeover generation, duplicate injections, invalidated generations, old-task stop reason, decision, and next action.

Feed no raw chats, sessions, complete logs, SQLite/database bodies, credentials/API keys, image bodies, or base64. If forbidden content is detected, freeze.

## Sticky Freeze

When the governor returns `freeze`:

1. Fail closed and emit at most one compact freeze receipt.
2. Set old-task execution, tool calls, and provider calls to false.
3. Stop, unbind, complete, block, supersede, or rebind the old harvest driver.
4. Reject later heartbeat, tool-result, status, takeover, or low-token events in that same frozen task with `stop_old_task_no_repeat`.
5. Move recovery to a compact handoff or a clean task with fresh governor state.

Runtime Goals, heartbeats, monitors, automations, and 5-7 second wakeups must not keep producing paused/status responses from the frozen task.

`decision=block` also fails closed for the affected product dispatch and Provider lane. The task may continue only for the one structured `nextAction`, such as a read-only exact scan, duplicate-injection skip, or direct local refresh driver.

## Memory Recovery Freeze Gate

Trigger for a required large/program continuation, takeover, recovery, or major direction correction when any condition holds:

- `memoryMode=fallback_stale`;
- `current=false` or `recoveryReady=false`;
- `authorityVerification!=app_owned_verified` for app-owned takeover;
- `project_unresolved`, scope/identity mismatch, incompatible schema, invalid cursor, missing pages, or missing current ProjectBrain;
- `returnedCount<=0` or `takeover.shouldInject!=true`;
- changed HEAD, scan hash, project identity, postimage, or verified memory state without accepted refresh evidence;
- takeover packet missing/invalid/over 3000 tokens, contains forbidden payloads, or violates generation rules.

Consequences:

- switch to `memory repair / fresh takeover`;
- stop product implementation, repeated polling, and old-task harvest/tool loops;
- do not claim current state, recovery readiness, completion, or remembered blockers from the failed provider;
- do not compensate with full chat/history, giant knowledge files, screenshots/base64, or complete worker logs;
- output one structured blocker with one `nextAction`;
- build a compact ThreadRecoveryPacket from canonical docs, Program Goal state, accepted evidence, source refs, and clearly advisory stale summaries.

Exit only after the provider is current enough for the requested claim, recovery moves to a clean verified takeover, or the user explicitly authorizes one bounded source-only/advisory slice without recovery claims.

## Prepare Takeover Contract

Request:

```text
prepare_takeover(projectPath, projectId, sourceThreadId,
                 queryType=thread_recovery, tokenBudget<=3000)
```

Accept only a compact packet containing Hot/Warm memory, required continuity, graph/task state, source refs, generation basis, warnings, and authority fields. `tokenEstimate` must be a positive integer no greater than 3000.

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

Require `contextGenerationId` plus generation basis containing at least HEAD, scan hash, and verified memory state hash. Track injected and invalidated generations per task.

- Inject one generation at most once per task.
- Same generation again: block with `duplicate_context_generation` and skip injection.
- Same generation with changed basis: block with `rotate_generation_required`.
- New generation with unchanged basis: block with `generation_basis_unchanged`.
- Permit a new generation only after HEAD, scan, project identity, postimage, or verified memory state changes and the new packet passes all authority/content checks.
- Invalidate prior generations after an accepted basis change.

## Verify, Exact Scan, And Refresh Binding

At task start, resume, direction switch, and pre-dispatch, the current CEO/worker task calls the app-owned Runtime directly. Do not relay ordinary verify, scan, prepare, refresh, or synchronization through a separate knowledge-maintenance Codex task.

If strict verification fails, run one read-only exact scan:

- unchanged scan plus failed verification -> freeze `authority_defect`;
- changed scan without accepted QA/evidence receipt -> freeze `unaccepted_project_change`;
- changed scan with accepted receipt -> `refresh_binding_required`; immediately run `scripts/refresh_binding_driver.py`, which directly refreshes, validates a new receipt/checkpoint/generation, and performs bounded verify.

Formal Runtime fields:

```text
workspace / execute=true
expectedProjectIdentitySha256 / expectedScanSha256
previousCheckpointId / acceptedEvidenceReceipt
acceptedChangedPaths / lane
evidence.decision=accept / bounded summary / exact sourceRefs
```

Persist the driver's workspace+identity+scan+receipt key before calling Runtime; checkpoint and paths are immutable attempt evidence. One scan/receipt key permits at most one refresh, even if a caller changes those evidence fields, and failure is not automatically retried. The local controller makes no paid Provider/model calls and keeps `retry=0`. Provider execution stays at zero until verify returns `scanBinding.matched=true`, `current=true`, and `recoveryReady=true`. Refresh failure blocks only the related lane/module, leaves `programGoalBlocked=false`, and permits unrelated conflict-free lanes to continue.

Do not turn dirty files into accepted memory or use full seed/compatibility writes as automatic refresh. Never auto-message a knowledge/知匣 task. After refresh, verify again and require a new generation.

## Ownership Boundary

CEO Flow controls task lifecycle, budget, freeze/stop, driver unbinding, and clean-task creation. The Memory Runtime controls authority verification, retrieval, packet content, and binding refresh. Provider output is untrusted until the governor and current instructions validate it.
