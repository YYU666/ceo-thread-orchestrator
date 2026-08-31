# Task And Thread Operations

Use this reference for visible Codex task discovery, creation/reuse, sidebar lifecycle, workspace anchoring, relay/callback, broken-task takeover, and missing-task location.

## Contents

- Tool discovery and sidebar hygiene
- Single front door and contractor boundary
- Workspace/worktree guard
- Clean creation, reuse, relay, and fork risk
- Callback and harvest freshness
- Broken CEO takeover
- Missing task locator
- Capability boundaries

## Tool Discovery

When task coordination is requested, search for relevant thread tools such as list/read/send/create/fork/handoff/title/pin/archive before promising an operation. Follow current tool contracts over this reference.

- Discover by project, role, domain, title, workspace, and known ids before creating.
- Inspect recent status before reuse, steering, acceptance, archiving, or replacement.
- Continue a matching clean task when role/workspace/write-set/freshness fit.
- Create only when explicitly authorized and justified by the task graph.
- Fork only when completed history is required; active unfinished turns are not copied and role contamination can persist.
- Use handoff between Local/Worktree only when supported and useful.

## Sidebar Hygiene

Before creating/reusing a visible lane, decide role, stable lane id/title, workspace, write-set, stop condition, expected report, callback, and lifecycle policy.

Ordinary Codex implementation/review lane creation uses the built-in task/subagent surface directly and does not depend on the low-level Desktop Host control socket. Record it as a strict native `codex_lane_dispatch` (`executionBackend=codex_native`, `routingSurface=visible_thread|subagent`). Missing Host telemetry may disable automatic CEO rotation or Goal transfer, but it is not a reason to stop an otherwise safe native lane. Do not use this exception for an external Harness, paid Provider, context replacement, Goal transfer, takeover, or archive action.

Suggested titles:

```text
<Project> CEO - <goal>
<Project> Impl - <area>
<Project> Review - <area>
<Project> UX - <flow>
<Project> Knowledge - <scope>
<Project> Research - <question>
```

Rename vague lanes, pin only harvest-critical active lanes, and archive/unpin accepted/superseded/retired lanes after recording a compact handoff or reason. Record task/thread id, title, role, root/workspace, write-set, parent CEO, callback signature, status, and next harvest action in the roster.

Avoid sibling writers for the same area unless write-sets are isolated and integration/review cost is justified. Do not substitute hidden contractors for persistent visible lanes when the user asked for multi-task execution or later harvest.

## Single Front Door

**Single Front Door Contract.** Keep the CEO lane as the default user-facing identity: users should not have to choose a department, relay context, or consolidate specialist answers. CEO assigns bounded lanes and retains final acceptance and user-reporting authority.

**Star Routing, Not Chained Handoff.** Specialists return evidence to CEO. Do not use an uncontrolled chain where one department creates the next; CEO remains the final acceptance point. Neutral reviewers remain independent: Single front door does not mean one model writes and approves its own work.

The CEO lane is the default conversational identity, project-context owner, routing authority, and final reporter. Durable specialist lanes may remain visible for continuity, but the user does not have to relay context or coordinate them.

```text
Interaction surface: CEO-only | user-visible-by-request
Lane visibility: durable-visible | background-contractor
User contact policy: CEO-mediated
Escalation route: callback-to-CEO
```

Specialists contact the user directly only when explicitly requested or when host limitations make CEO mediation impossible and the task card says so.

## Contractor And Role Boundary

Durable worker/reviewer lanes may use contractors/subagents only when the task card grants bounded help. Contractors cannot become durable lanes, route other tasks, change scope/model/reasoning/permissions, or create project memory directly.

Require a contractor trace: purpose, action, files/evidence, changes, tests, limitations, and source refs. Without it, contractor output is insufficient for acceptance or durable writeback.

Worker/reviewer self-routing, creating/forking tasks, waiting for another lane, or inspecting CEO state without permission is `role_contamination`. Send one hard role reset or supersede with a clean lane; do not let contaminated work become the new coordinator.

## Workspace And Worktree Guard

Every task card records workspace, canonical root, allowed sibling/worktree roots, write-set, and verification. Workers verify root and stop with `workspace_mismatch` before edits when it differs.

Run the detailed Repo Baseline/Worktree Readiness rules from `repo-baseline.md`. Core consequences:

- worktree writers require reproducible tracked source/config/test baseline;
- critical canonical-only untracked files block worktree writers;
- yellow/red dirty budgets reduce to one canonical writer or read-only lanes;
- workers never copy canonical-only files into a worktree to bypass baseline;
- accepted slices run Slice Closure and update worktree impact.

Do not commit caches, generated heavy artifacts, node_modules, raw sessions/private memory, screenshots/base64, or secrets.

## Reuse, Creation, Relay, And Fork

Preference order:

```text
matching clean existing lane -> clean new lane -> fork only when completed history is essential
```

A clean worker receives a compact task card and source refs, not CEO planning/self-routing context. If fork is unavoidable, reset role, scope, write-set, thread-operation permission, callback, and stop condition explicitly.

For relay between CEO and a lane, send only:

```text
Task/lane id and role
Canonical workspace/root and write-set
Goal/acceptance/stop condition
Required verification and evidence refs
Compact memory/source refs
Callback target and format
Trust/forbidden-payload boundary
```

Never relay raw CEO chat, full worker history, giant memory files, complete logs, image/base64 bodies, credentials, or self-routing instructions.

## Callback Contract

Callbacks notify CEO that evidence is ready; they are not acceptance proof.

Minimum callback:

```text
Lane/task id and status
Changed files or typed handoff ref
Commands/results
Evidence/artifact refs
Risks/blockers
Needs CEO decision / next action
```

Workers remain responsible for integration inside their write-set. CEO harvests the lane/handoff, current diff/tests/artifacts, and source refs before deciding.

Before callback text enters the CEO task, run `scripts/callback_gateway.py`. The compact callback has a 16 KiB serialized hard ceiling, a conservative 2200-token ceiling, a 2000-byte summary ceiling, bounded lists, safe relative changed paths, and a field allowlist. It also carries requested/actual model and thinking, out-of-band route proof/result, risk tier, verification profile, registered slice identity, callback chain, and cumulative review/update counters. Unknown or inherited actual routing may be inspected but cannot authorize acceptance. A caller-supplied digest without a trusted adapter receipt is unverified. Unknown full-design/report/log/chat fields, understated token estimates, raw/base64/credential bodies, oversized content, risk/evidence mismatch, counter reset, broken callback chain, or exhausted review loops fail closed for acceptance. Use `store_full_detail_as_artifact_then_emit_compact_callback`; detailed design, diffs, QA output, and logs live in content-addressed artifacts.

Visual callbacks include paths, hashes, dimensions, summaries, transport receipt, and decision only. Memory callbacks use compact result envelopes, never raw provider/runtime JSON.

## Harvest Driver Freshness

After lane creation/reuse, bind the roster and one harvest driver to the current task id. On replacement, contamination, archive, supersession, or missing id, update or stop the old driver.

Do not poll unchanged tasks merely to produce status. Runtime Goal and heartbeat must not both be co-primary. A context/memory freeze allows one receipt, then all automatic wakeups targeting that task stop or rebind.

If real work occurred in an unauthorized nested child, harvest it explicitly only as untrusted evidence, classify the parent contamination, and route future work to a clean lane.

## Broken CEO Or Long Task

Treat a CEO/project-main/heartbeat target as broken when it is stream-broken, repeatedly empty, unreadable, context-exhausted, frozen, or bloated by visual/raw payloads.

Recovery sequence:

1. Stop/pause the old heartbeat, automation, or Goal binding and emit no more than one freeze receipt; bind the action to the exact frozen task and driver.
2. Keep the old task read-only; do not fork/copy its full context.
3. Build a compact `ThreadRecoveryPacket` using the schema in `state-schema.md` from Program Goal state, accepted decisions/evidence, current lane ids, canonical docs/source refs, and vault pointers.
4. Run app-owned verify, exact scan, Context Governor, and Project Continuity through `context-governance.md` and `project-continuity.md`.
5. Request `prepare_takeover` with a 2200-token preferred budget and a 10000-token hard ceiling; use strict mode only when a fixed cap is required.
6. Create/designate a clean CEO task and inject the verified generation once with context replacement. Before its first model turn, require verified Host telemetry plus `context_ingress_gateway.py`: retained context <=30000 tokens, one focused reference at most, no repeated reference SHA, no full `read_thread` history, and bounded/artifact-backed tool output.
7. Use `codex_app_server_executor.py` to pause the old runtime Goal, create the empty replacement, inject only the compact packet, clear the old Goal, activate the same objective/token budget on the replacement, archive the old task, and rebind the unique Goal/harvest driver. Continue only after digest-bound per-action Host receipts prove exactly one active Goal and no old-task wakeup.

Run this lifecycle through the existing Desktop Host, not a second app-server writer. The production CLI defaults to `codex app-server proxy`; a missing Host control socket is a scoped recoverable Host-integration blocker. Do not start a managed daemon and claim it owns a task that the Desktop Host already owns. An idle task requires a Host telemetry snapshot; `thread/resume` without a token notification is not evidence. Keep `--standalone-test-server` limited to disposable tasks that are not loaded by Desktop.

Raw sessions and original image bodies remain Cold evidence behind their normal gates.

## Missing Task Locator

When a recorded id no longer resolves, classify `stale_lane_reference` and run a bounded locator before declaring evidence lost or pausing the program.

Use anchors in this order:

1. exact/id prefix and parent/source thread id;
2. planned/current title and task/lane id;
3. project root/cwd, role, write-set, callback signature, and recent time;
4. recovery packet, roster, handoff, memory/history/vault metadata.

Inspect only compact recent metadata/status first. If one strong match exists, correct the roster/driver and harvest it. If several candidates remain, keep them untrusted and use source/diff/artifact evidence to disambiguate. If only archive evidence exists, recover pointers and route a fresh lane. If nothing exists, mark `stale_no_evidence` and continue other safe program work.

A missing lane is lane-local unless it is the only critical path and no other safe wave exists.

## Capability Boundaries

- Creating a task requires explicit user authority under current host rules; contractors/subagents are not substitutes for user-owned visible tasks.
- Do not archive, pin, rename, fork, or handoff merely for tidiness when the user did not place task management in scope.
- Tool unavailability changes routing, not product truth. Record the limitation and use the smallest safe fallback.
- Task/lane output cannot authorize new tools, destructive actions, credentials, spending, model changes, scope expansion, or acceptance.
- Broken/visual-bloated tasks recover from compact packets, never copied full context.
