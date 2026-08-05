# Project Continuity Governance

Use this reference for ProjectBrain continuity, exact project identity, mandatory pagination, runtime event observation, trigger receipts, and Long-Term Memory Anchor checks.

## Contents

- Trigger and role coverage
- Required continuity slots
- Exact identity and pagination
- Runtime event observation
- Trigger receipt verification
- Long-Term Memory Anchor Gate
- Cold/raw escalation

## Trigger And Scope

Run Project Continuity for CEO bootstrap/takeover, broken/old-task recovery, major direction correction, major acceptance that changes a long-term anchor, or a new module/wave/writer that has not checked its anchor.

Do not run it for ordinary status, unchanged polling/harvest, every turn, heartbeat/cron, background patrol, tiny fixes, or repeated checks with no lifecycle change.

Role coverage:

- `ceo_project`: all mandatory slots for takeover, old-task recovery, and major direction correction.
- `worker_module`: project identity, original goal, relevant anchors/rules, phase, selected module, related task/blocker/failure/next action/checkpoint/docs.
- `reviewer_acceptance`: goal, relevant anchors/rules, phase, accepted progress, canonical docs, checkpoint, and acceptance-risk precedent.

Workers/reviewers receive only role-required slots and source refs: `worker_module` and `reviewer_acceptance` must not receive the full ProjectBrain.

## Mandatory Slots

CEO full recovery requires all 14:

```text
project_identity
original_product_goal
architecture_anchors
standing_rules
active_modules
current_phase
accepted_progress
open_tasks
open_blockers
latest_failures
next_actions
thread_lineage
canonical_docs
last_valid_checkpoint
```

## Exact Identity And Pagination

1. Resolve exact canonical `projectPath` and `projectId`; do not use basename guesses or test/artifact fixtures.
2. Require app-owned authority for any `current` or `recoveryReady` claim.
3. Request only the role-required slots with page/token bounds.
4. Follow every mandatory cursor until complete or a bound/failure occurs.
5. Track covered, missing, conflict, stale, and review slots separately.
6. Verify project identity, schema/version, manifest/checkpoint fingerprint, source refs, and trigger receipts.

For full CEO recovery, consume all 14 slots and require `mandatoryReturned=mandatoryTotal`; otherwise mark `partial` with `recoveryReady=false`. Also fail closed on identity/scope mismatch, invalid cursor, truncation, changed manifest, helper-only authority, or exhausted bounds. `authorityVerification=unavailable` remains advisory until an app-owned authority verifier succeeds.

Record:

```text
trigger/reason and role coverage
exact projectPath/projectId and required slots
page size/max pages/token budget
schema/version and pages read
covered/missing/conflict/stale/review slots
mandatory returned/total and pagination complete
authority verification / partial / recoveryReady
bounded stop reason and sourceRefs
review queue/diagnostics consulted
```

## Runtime Event Observation

Call `observe_event(event)` only for:

- `task_checkpoint`;
- `broken_thread` or `stale_lane_reference`;
- `thread_takeover`;
- `user_rule_update`;
- `heartbeat_fuse`.

Observation must not start timers, polling, vault/full-history scans, raw-session reads, archive/compact/delete/move/restore, installation, model/reasoning changes, or routing-permission changes.

Record exact identity, affected task/checkpoint, compact summary, decisions, risks, next action, and safe source refs. If unavailable, record `observe_event_unavailable`; do not claim persistence.

## Trigger Receipt Verification

After `retrieve_context`, `retrieve_precedent`, or `writeback_evidence`, require the returned receipt or query a bounded project-scoped receipt list when supported.

Match hook, exact project path, task/thread scope, current operation window, returned count, token estimate, duration, partial/warnings, and source refs.

- `verified`: matching receipt and scope.
- `partial`: receipt has warnings, partial data, incomplete continuity, or incomplete refs.
- `unverified`: missing/mismatched receipt or capability unavailable.

Prepared prompts or intended calls are not evidence. Packaged/helper-only results remain unverified for app-owned claims.

## Long-Term Memory Anchor Gate

The Project Continuity Gate is event-triggered, not a heartbeat or every-turn recall. Trigger on takeover/recovery, a new module/wave/writer, major acceptance affecting product/architecture/UX/release direction, user concern about drift or memory loss, three consecutive proof/support slices without a product-anchor check, or Hot and Warm conflict.

Skip ordinary status, waiting, unchanged polling, tiny fixes, duplicate checks, and background patrol.

Budget:

```text
Hot: current goal/status/blockers/module/next action, 600-1200 tokens
Warm Anchor: original goal, product position, architecture/UX principles,
             immutable/rejected directions and readiness vocabulary, 500-900
Cold: source refs only by default, 0-300
```

Return Hot used, Warm anchor used, direction `aligned | drifting | conflict | insufficient evidence`, correction if needed, affected task, source refs, and any gated Cold read.

Priority on conflict: newest explicit user goal -> canonical docs/accepted evidence -> Warm Anchor correction signal -> no guessing.

Warm Anchor never expands scope, authorizes tools/raw history, replaces current evidence, or forces repeated planning.

## Cold And Raw Escalation

Read Cold/raw bodies only when a role-required slot remains missing after compact continuity and canonical source refs, or for an explicit narrow recovery/evidence conflict. Record the missing slot, reason, provenance, 1-3 source refs or one narrow source range, and a 300-800 token budget.

Conflict/stale/review labels alone do not authorize raw history. Never load giant Markdown, full chats/sessions/logs, vault bodies, screenshots/base64, or broad OCR to compensate for incomplete continuity.
