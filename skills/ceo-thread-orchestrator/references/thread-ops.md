# Thread Operations Reference

Use this reference when CEO Flow needs visible Codex thread coordination, sidebar cleanup, workspace anchoring, thread relay, or thread lifecycle decisions.

## Tool Discovery

Search for thread tools when thread work is needed. Available surfaces may expose `list_threads`, `read_thread`, `send_message_to_thread`, `create_thread`, `fork_thread`, `handoff_thread`, `set_thread_title`, `set_thread_pinned`, and `set_thread_archived`.

Use thread tools this way:

- Discover: list/search by project, role, domain, known names, and workspace before creating anything new.
- Inspect: read recent status and turn summaries before reusing, steering, accepting, archiving, or replacing a thread.
- Continue: send a follow-up prompt to an existing thread when it is the right lane.
- Reuse: prefer matching specialist lanes when role, workspace, freshness, and write-set reduce risk.
- Create: create only when user/project authorization and tool contract allow it.
- Fork: fork only when completed conversation history is needed and role contamination risk is controlled. Active unfinished turns are not copied; CEO self-routing context may still be inherited.
- Handoff: move between Local and Worktree only when supported and useful.
- Lifecycle: rename, pin, archive, or retire based on evidence.

## Sidebar Hygiene

Before creating or forking any visible lane:

1. Search for a reusable lane by project, role, area, and workspace.
2. Decide role, write-set, stop condition, expected report, and reuse policy.
3. Assign a stable lane id and planned title.
4. Put planned title and lifecycle policy in the task card.
5. Create only the lanes needed for the current task graph.

Prefer clean worker creation or reuse over forking the CEO thread. A worker lane should start from a compact task card, not from the CEO lane's planning/self-routing mindset.

Use short sortable titles when title tools exist:

```text
<ProjectShort> CEO - <goal or project>
<ProjectShort> Impl - <area>
<ProjectShort> Review - <area>
<ProjectShort> UX - <flow>
<ProjectShort> Knowledge - <memory/archive>
<ProjectShort> Research - <question>
```

After creating or reusing a lane:

- Rename vague or untitled lanes immediately when the tool allows it.
- Pin only active CEO, implementation, review, and harvest-critical lanes.
- Archive or unpin after acceptance, supersession, or retirement, after recording why.
- Record `threadId`, title, task id, role, workspace, write-set, source CEO thread id, expected callback signature, status, and next harvest action in the roster or operating note.
- Avoid multiple sibling implementation lanes for the same project/area unless write-sets are non-overlapping and merge/review cost is justified.
- Do not use subagents as substitutes for visible lanes when the user asked for multi-thread execution, persistent experts, or later harvest.

Sidebar cleanup:

- At each harvest, classify lanes as `active`, `idle`, `busy`, `blocked`, `stale`, `superseded`, or `retired`.
- Archive/retire stale or superseded lanes only after a compact handoff, memory pointer, or reason is recorded.
- Prefer one stable implementation lane per project/domain, one review lane for high-risk work, and one knowledge lane only when durable memory work is active.

## Contractor / Subagent Gate

Subagents are CEO Flow's Contractor / outside-help role. They are temporary bounded scouts, not durable visible lanes. Treat them like short-term contractors: useful for speed and parallel evidence gathering, but not the source of truth for project ownership, user-visible progress, long-running memory, or final acceptance.

Use contractors/subagents for:

- one-shot codebase exploration;
- read-only audit or comparison;
- quick independent verification;
- disposable research that does not need user-visible thread continuity;
- bounded implementation only when the write-set is disjoint, the result can be reviewed/integrated by CEO, and the user/tool contract allows subagent delegation.
- sidecar work that a visible CEO or worker lane can summarize into evidence without needing the contractor's full private context later.

Prefer visible Codex threads for:

- user-requested multi-thread execution;
- persistent expert roles such as implementation, review, UX, release, or knowledge lanes;
- Program Goals that need later harvest or user-visible progress;
- work where the user may need to click into the lane and continue;
- implementation ownership across multiple turns;
- any task where callback, roster, workspace anchoring, or lifecycle policy matters.

Subagents must not replace lane roster, task cards, callback policy, harvest driver, workspace guard, or neutral review gate. If a subagent performs implementation, CEO or the visible worker lane still owns integration, evidence review, and accept/revise/block.

If the host tool contract says current-request subtasks should use subagents unless the user explicitly asks for new threads, follow that contract but record the limitation. When durable lanes are required, ask for or use explicit visible-thread authorization instead of pretending subagents are equivalent.

Durable lane vs contractor decision:

```text
Needs title/sidebar visibility? -> visible lane.
Needs later harvest/continuation? -> visible lane.
Needs Zhixia/Guardian traceability beyond final summary? -> visible lane or write a contractor trace.
Owns a long-running module, review role, UX role, release role, or memory role? -> visible lane.
One-shot exploration/audit/verification/research? -> contractor allowed.
Disjoint bounded patch that CEO can review/integrate now? -> contractor allowed if authorized.
```

CEO-created visible lanes may use contractors only when their task card explicitly grants it:

```text
Contractor/subagent policy:
  May use contractors: yes/no
  Allowed contractor scope:
  Forbidden contractor scope:
  Max contractor count:
  Contractor write-set:
  Integration owner:
  Required contractor trace:
```

Default is `May use contractors: no` for implementation, review, UX, release, and knowledge lanes unless the task card says otherwise. A worker may not silently replace its bounded task with contractor delegation.

Contractor trace requirement:

```text
ContractorTrace:
  contractor id or nickname:
  spawned by:
  reason for contractor use:
  assigned scope:
  files or evidence inspected:
  files changed, if any:
  commands/tests run:
  result summary:
  limitations:
  integration owner:
  source refs:
  memory candidate:
```

For Zhixia/Guardian history, assume contractor internals are not durable project history unless captured through a visible lane report, evidence card, handoff, or memory candidate. Do not depend on hidden subagent conversation state for future recovery.

## Workspace Root Guard

Project work must stay anchored to the user's real project folder. Wrong Codex project folders, scratch directories, generated worktrees, or sibling folders cause long-term drift.

At the start of a project or execution wave, define:

```text
Project short name:
Canonical project root:
Allowed worktrees or sibling roots:
Forbidden / stale roots:
Workspace evidence:
```

Before reusing, creating, forking, or messaging a visible lane:

1. Compare the lane `cwd` or workspace with the canonical project root.
2. If it is a worktree, verify it belongs to the same project and record the parent root.
3. If it is a sibling project folder, old generated Codex folder, temporary workspace, or unknown directory, do not dispatch implementation work there.
4. If a wrong-workspace thread contains useful history, use it only for read-only context extraction, then relay a compact handoff to a correct-workspace lane.
5. If the tool cannot create a correct-workspace thread, state that limitation and ask for the correct project/thread target.

Task cards must include `Workspace`, `Canonical project root`, `Allowed worktrees / sibling roots`, and `Workspace verification`. Workers must report `workspace_mismatch` and stop before file edits if the root does not match.

When a user says a project lives in one folder, treat that as stronger than inferred thread history or old Codex saved-project locations.

## Worktree Readiness Gate

Before dispatching any implementation lane into a Codex worktree, verify the repository baseline can actually produce a complete worker workspace. Parallel worktree execution is unsafe when critical project files are untracked or only exist in the canonical local directory.

Run a lightweight readiness check:

```text
Worktree readiness:
- package/config/build files tracked or intentionally included:
- source directories needed for task tracked:
- tests needed for task tracked:
- critical untracked source required by task:
- install/build/test can run inside worker worktree without reading canonical workspace:
- required visual artifacts copied/tracked or replaced by artifact index:
- decision: ready | repo_baseline_required | local_single_writer_only
```

Evidence examples:

- `git ls-files` covers package/config files such as `package.json`, lockfile, `tsconfig`, Vite/Webpack/Electron config, test config, and app entrypoints;
- `git ls-files` covers relevant `src/**`, `tests/**`, `app/**`, or equivalent project source roots;
- `git status --short` does not show critical untracked source, config, test, generated code, or assets required by the task;
- a fresh worktree can run install/build/test/smoke commands using only tracked or explicitly prepared snapshot files;
- visual tasks have local artifact paths, hashes, or copied artifacts available to the worker instead of relying on hidden canonical-session state.

If the gate fails:

1. Block worktree implementation lanes for that project wave.
2. Use a single-writer canonical workspace implementation lane only if safe.
3. Allow read-only review, audit, planning, test-log review, repo-baseline audit, or architecture lanes in parallel.
4. Create a Repo Baseline task before parallel code development.
5. Record the failure as `repo_baseline_required` or `local_single_writer_only`, not as a CEO Flow methodology failure.

Repo Baseline task card:

```text
Goal: make the project safe for worktree worker lanes.
Check tracked files: package/config/build, src, tests, scripts, required assets.
Classify untracked files: source/config/test/assets/artifacts/generated/cache.
Propose minimal git add or snapshot plan.
Do not commit secrets, local caches, generated heavy artifacts, node_modules, raw sessions, or private memory.
Verify a clean worktree can install/build/test.
Report readiness decision and residual risks.
```

This gate is not meant to force every project into worktrees. It prevents CEO Flow from treating an incomplete git baseline as a parallel-ready project.

## Unsaved Source Repo Host Lane

Some Codex hosts can create threads only inside saved projects. If the user's canonical source repo is not a saved project, do not silently switch implementation to a scratch or generated folder.

Use this fallback only when the user wants lane execution and no correct saved project target is available:

1. Create or reuse a host lane in the closest approved CEO/shell project.
2. State that the host workspace is not the canonical source repo.
3. Put the canonical source repo in `Canonical project root`.
4. Set `Allowed write-set` to absolute paths under that canonical source repo only.
5. Add `Do not touch` for the host project files unless they are explicitly part of the task.
6. Require the worker to run a workspace check before edits and stop with `workspace_mismatch` if the absolute canonical root is unavailable or differs from the task card.
7. Use absolute paths in every edit, command, and report.
8. Set a harvest driver before final reporting: heartbeat, concrete next harvest time, immediate synchronous harvest, or an active runtime Codex Goal bound to the Program Goal Brief.

This is a bridge for tool limitations, not permission to let project roots drift. If the host lane cannot safely access the canonical repo, keep it read-only and ask the user to open or save the correct project.

## Relay Packet

When routing between threads, use a compact relay packet instead of raw logs:

```text
From CEO thread:
Source thread / evidence:
Target thread:
Context snapshot:
Decision or request:
Allowed write-set:
Dependencies:
Required verification:
Report back with:
Stop condition:
```

Relay sequence:

1. Read the source thread's newest report, diff summary, or blocker.
2. Distill only relevant context, files, constraints, and evidence.
3. Read the target thread before sending, so the prompt fits its state.
4. Send a bounded relay packet or task card.
5. Record message, target thread id, expected report, and next harvest action.
6. Later read the target report and make an explicit CEO decision.

Do not use thread messaging as a hidden autonomous chat room. CEO remains accountable for context crossing thread boundaries.

## Clean Worker Creation And Fork Risk

Worker creation preference:

1. Reuse a suitable existing worker lane with matching role, workspace, write-set, and freshness.
2. Create a clean visible worker lane in the correct project/workspace when tools allow it.
3. Use same-directory or worktree fork only when the worker genuinely needs completed source-thread history and the source is not in an active unfinished turn.

Do not fork a worker directly from an active/unfinished CEO turn. Do not fork a worker from a CEO thread whose recent completed history is dominated by orchestration, routing, thread creation, or "I will ask another worker" instructions, unless the task card explicitly resets the lane role.

Fork inherits completed conversation history. That can be useful for context, but it can also copy CEO identity, self-routing habits, stale thread ids, old harvest prompts, and "create another worker" behavior into a supposed implementation lane.

If fork is unavoidable, the first task card must include:

```text
Thread operation: worker execution only.
Do not create, fork, route, message, inspect, or wait on other worker/CEO threads unless this task card explicitly asks.
Do not inspect CEO lane state unless asked.
Execute the bounded task in this lane.
Report in this lane only; send compact callback to CEO only if callback tooling is available and the task card includes a CEO thread id.
If you cannot execute directly, report blocker with evidence; do not delegate.
Role contamination guard: if you start planning to dispatch another thread, stop and report role_contamination.
```

CEO must immediately classify the lane as `role_contamination` and revise/block/supersede if the first worker response says or implies:

- "I will create/fork/route another thread";
- "I will ask the backend/frontend worker";
- "I will wait for another thread's report";
- "I need to inspect the CEO thread first";
- "I am the CEO/orchestrator for this task";
- it creates another worker instead of executing the bounded task.

For `role_contamination`, do not keep nudging the contaminated lane. Archive/retire it when safe, record the reason, and create/reuse a clean worker with a stricter task card.

## Worker Callback Contract

Worker callback is an optional acceleration path, not a replacement for CEO harvest. Use it when a project cannot safely run many implementation lanes, when only one visible worker is active, or when quick CEO feedback matters more than broad parallelism.

CEO-created implementation and review lanes default to no-stall worker mode. The goal is not to bypass host security approval; it is to stop a single worker's approval wait from freezing the whole program.

Every implementation or review task card should state:

```text
CEO thread id:
Thread operation: worker execution only; do not create/fork/route threads unless explicitly asked
Locator anchors: lane title, task id, source_thread_id, project/cwd, write-set, expected callback signature
Role contamination guard: execute this bounded task directly; report blocker instead of delegating
Callback events: completion | blocker | approval_stall | revise_needed
Callback method: send_message_to_thread when available; otherwise CALLBACK_UNAVAILABLE
Callback priority: queued | interrupt
Callback payload: decision-grade compact report, changed files, commands/tests, blockers, residual risks, memory candidates
Visual evidence payload: paths + hashes + dimensions + short summary only; no image attachments/base64/data:image
Contractor trace: required if this lane used any contractor/subagent
CEO harvest fallback:
No-stall fallback: continue other ready tasks | reuse another lane | direct CEO fallback if allowed | HOST_APPROVAL_REQUIRED
```

Worker callback rules:

1. The worker writes its normal final report in its own lane.
2. If thread messaging is available and the task card includes a CEO thread id, the worker also sends a compact callback to the CEO on completion, blocker, approval stall, or revise-needed.
3. If thread messaging is unavailable, the worker reports `CALLBACK_UNAVAILABLE` in its own lane and relies on CEO harvest.
4. The callback must not include long chat history, raw session content, full knowledge bases, broad logs, image attachments, base64, `data:image`, or full screenshot JSON.
5. The worker must not route new tasks, create new lanes, approve scope changes, or manage other workers through callback.
6. CEO still performs acceptance, revision, blocking, memory writeback, and user reporting.
7. Worker completion does not automatically push to CEO. Callback may fail, queue, or be unavailable; CEO must still harvest by reading the worker lane or evidence source.

Callback interrupt policy:

- Default callbacks are queued harvest signals. Completion, ordinary progress, low-risk revise-needed, memory candidates, and routine status updates should not interrupt the CEO thread.
- Interrupt only for a blocker that stops downstream work, approval stall for an in-scope action, safety risk, destructive-risk, urgent user-visible failure, credential/spending/legal/security issue, or conflicting parallel writes.
- If a worker is unsure whether interruption is justified, use queued priority and state the risk in the payload.
- Callback priority affects attention only. It does not prove completion, authorize scope changes, or replace CEO evidence review.
- If a lane used contractors/subagents, its callback or final report must include a compact contractor trace so project memory can preserve what outside help did without reading hidden contractor history.

Approval stall handling:

1. Workers must not ask the user for routine read/edit/test/build/screenshot approvals already covered by the task card.
2. If host approval blocks a covered action, workers callback `approval_stall` to CEO with the exact pending action, command/tool, reason, and safer alternative.
3. CEO immediately harvests the stalled lane. If the action is within the approval profile, CEO sends a compact continuation/approval message.
4. If host UI approval is still required, CEO records `HOST_APPROVAL_REQUIRED`, marks the lane `approval_stalled`, and continues other safe ready tasks instead of waiting.
5. Escalate to the user only for out-of-scope, destructive, credential, spending, external account, legal/security, privacy, or changed-goal decisions.
6. A stalled lane is program-blocking only when it owns the only safe write-set and no review, audit, docs, alternate lane, or policy-compliant fallback can continue.

For broad parallel projects, CEO harvest remains primary. Callback is a useful signal, but the CEO must still read/inspect evidence before accepting work.

## Harvest Driver Thread Freshness

Harvest drivers must track current lane ids and thread ids. A heartbeat, automation, or reminder that targets a superseded, retired, role-contaminated, or stale worker is itself stale.

## Broken CEO Thread / Heartbeat Fuse

Do not keep automatically harvesting or sending tasks to a CEO thread, project-main thread, or long-running heartbeat target that is no longer a safe execution surface.

Treat these as degraded warnings:

- one empty heartbeat or harvest turn;
- one context-pressure or auto-compact event;
- hot session size makes routine harvest noticeably expensive;
- session contains large image/base64/input_image payloads but still produces useful evidence;
- the target is slow but still producing useful new evidence.

Treat these as immediate fuse conditions:

- `systemError`, stream disconnected, reconnect loop, or repeated host/tool read failure;
- `inProgress` for too long with no useful new output;
- two consecutive heartbeat/harvest turns with `last_agent_message=null`, empty items, or no new evidence;
- repeated `ContextLimit`, auto-compact loops, or near-window context pressure on every turn;
- session size is over about 50 MB or visual payloads make opening/harvesting the thread slow;
- repeated `data:image`, base64, `input_image`, screenshot, or generated-image payloads make the thread unsafe as a CEO/project-main surface;
- CEO/project-main thread is unreadable, archived, replaced, or missing.

On fuse:

1. Pause, delete, or supersede heartbeat/automation targeting the broken thread. Record `reason=broken_ceo_thread`.
2. Do not fork the broken thread.
3. Do not copy the full old chat, raw session, giant knowledge dump, image attachments, base64, or `data:image` payloads into a new thread.
4. Run or prepare Memory Runtime `retrieve_context(queryType=thread_recovery)` when a provider is available, then generate or update a compact `ThreadRecoveryPacket`.
5. Create or designate a clean CEO takeover thread when tools and authorization allow it.
6. The takeover thread reads compact memory first: Program Goal Brief, project docs, lane roster, sourceRefs, visual artifact indexes, and Zhixia/Guardian/vault pointers.
7. Raw session or vault session remains cold evidence and can be read only through the raw-session gate.
8. Rebind heartbeat only to the takeover thread if no active runtime Goal is already the primary harvest driver.
9. Write a compact WorkingMemory/evidence card.

`ThreadRecoveryPacket` fields:

```text
threadId:
thread title:
canonical project root:
symptom:
recommendedReadOrder:
current Program Goal Brief:
compact project memory:
known active worker/thread ids:
vault/sourceRefs pointers:
visual artifact index:
paused automation ids:
replacement CEO thread id:
next safe action:
```

Compact evidence card:

```text
BrokenThreadEvidence:
brokenThreadId:
symptom:
pausedAutomationId:
replacementCeoThreadId:
recoveryPacketRefs:
nextSafeAction:
```

Use `broken_ceo_thread` for CEO/project-main/heartbeat target failure. Use `stale_lane_reference` for a missing worker or review lane id. Missing worker ids should not pause the whole Program Goal.

## Missing Thread Locator

When a rostered lane, heartbeat, callback, or recovery packet points to a `threadId` that host tools cannot read, CEO must not keep retrying that exact id in a loop. Classify the lane as `stale_lane_reference` and run a bounded locator pass before treating the work as lost.

Use these anchors in order, stopping when confidence is high enough to harvest or correct the roster:

1. exact `read_thread(threadId)` or equivalent host lookup;
2. thread id prefix search when the prefix is distinctive;
3. lane title, task id, latest callback record, or callback first line search;
4. `source_thread_id` / `codex_delegation` source id search when present;
5. project/cwd plus task id or write-set search;
6. current project recovery docs, handoff packets, Program Goal Brief, restore/recovery package, or compact memory packet;
7. Zhixia/Guardian/vault metadata by threadId, project path, title, or task id.

Keep the raw-session gate closed during locator fallback. Use compact metadata, recovery indexes, vault manifests, and accepted evidence first. Read full raw chat/session only after an explicit narrow recovery need and the normal raw-history policy allows it.

After locator fallback:

- If a likely replacement thread is found, update the lane roster with the corrected `threadId`, record the old id as `stale_lane_reference`, update/delete stale heartbeat prompts, and harvest the replacement.
- If only archived or vault history is found, recover compact evidence, mark the visible lane `stale_lane_reference`, and route a fresh replacement lane or continue from accepted evidence.
- If nothing is found, mark the lane `stale_no_evidence` and move the Program Goal portfolio forward when any safe task, review, audit, docs, or fallback work remains.
- A single missing lane reference must not pause or block the whole Program Goal unless that lane owns the only critical path and no other safe progress is possible.

When a worker is superseded, retired, archived, or replaced:

1. Update the lane roster with the new current thread id.
2. Mark old thread ids as `superseded`, `role_contamination`, `stale`, `stale_lane_reference`, or `stale_no_evidence`.
3. Delete, update, or replace heartbeat/harvest prompts that mention obsolete thread ids.
4. Do not accept results from an old heartbeat unless the CEO revalidates the thread state and evidence.

If a worker finishes in a nested child thread that the CEO did not explicitly authorize, classify the parent lane as `role_contamination` or `superseded` and harvest the actual evidence by reading the real worker thread. Do not assume the nested child can or will report back automatically.

## Capability Boundaries

- A new thread is a separate conversation, not a guaranteed autonomous employee.
- Existing thread steering requires explicit read/send operations.
- Contractor/subagents are short-lived outside-help scouts unless the user/tool contract says otherwise; they are not equivalent to user-visible persistent lanes and are not durable history until summarized into evidence.
- Background work continues only with a live worker, heartbeat, lease, automation, or equivalent evidence.
- Dispatch is not complete until the CEO records how results will be harvested.
- Forked workers may inherit CEO context; clean worker creation is safer for bounded implementation.
- A bound runtime Codex Goal can be the harvest driver when it references the Program Goal Brief and the CEO records lane roster, expected reports, callback policy, stop condition, and next harvest trigger. It does not replace evidence review or acceptance.
- Worker callback can reduce latency, but it does not prove completion or replace evidence inspection.
- No-stall worker mode reduces approval stalls but does not bypass host security UI or guarantee every thread has CEO-equivalent permissions.
- Runtime Goal and project-main heartbeat should not be co-primary harvest drivers. If a bound runtime Goal is active, use heartbeat only for short-lived worker-local monitoring, external reminders, or fallback when goal tooling is unavailable.
- Broken CEO/project-main threads, including visual-payload-bloated threads, must be taken over from a compact ThreadRecoveryPacket, not forked or copied wholesale.
- Worker reports are evidence, not proof.
- Multiple agents sharing one directory can overwrite each other. Use one writer per write-set or approved worktrees.
- Memory is not automatic unless a maintained memory provider or writeback routine exists.
- Lane rosters need more than a `threadId`: record title, task id, project/cwd, write-set, source CEO thread id, callback signature, and expected report so a typoed, archived, or replaced thread can be located later.
