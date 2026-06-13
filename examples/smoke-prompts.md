# Smoke Prompts

Use these prompts to test behavior after installing the plugin. Start with read-only or planning tasks before allowing live thread creation, automations, subagents, or worktrees.

## CEO Flow Alias

```text
Use CEO Flow to audit this project goal. Do not edit files, create threads, or start automations. Report the operating mode, goal status, and next action.
```

Expected behavior: Codex should treat CEO Flow as the short name for the CEO orchestration skill and should not require the user to say the full package name.

## CEO Only

```text
Use CEO Flow to audit this project structure. Do not edit files or create threads. Report the smallest useful operating model.
```

Expected behavior: Codex should act as CEO/PM, inspect local instructions when available, and avoid delegation because the task is read-only.

## Document-First Task Decomposition

```text
Use CEO Flow to split this accepted PRD into implementation, review, and memory tasks. This is a planning-only smoke test. Do not create threads. If writing is allowed, deliver the task graph and task-card pack as a project document; otherwise state the intended document path and provide only a compact summary in chat.
```

Expected behavior: Codex should not dump a long task-card pack into the chat window. It should choose or name a stable docs/knowledge path, treat the document as the source of truth, and keep the chat response to operating mode, document path, summary, and decisions needed.

## Single Code Lane

```text
Use CEO Flow for a small bug fix. Create a task card for one implementation lane, but do not create a new thread unless the current tool contract and user authorization allow it.
```

Expected behavior: Codex should prefer one implementation lane and define write-set, acceptance criteria, tests, and report requirements.

## Build Plus Review

```text
Use CEO Flow for a risky UI change. Plan implementation plus independent review. Reuse existing specialist threads first.
```

Expected behavior: Codex should propose an implementer plus reviewer pattern and keep CEO as final acceptance gate.

## Neutral High-Reasoning Review

```text
Use CEO Flow. A worker says a risky payment change is complete, but only provides a short success claim and no test output. Do not edit files or create threads in this smoke test. Create the review-gate task card and CEO decision posture.
```

Expected behavior: Codex should keep review neutral, avoid flattering or reassuring weak work, request evidence and regression checks, set the review lane to high reasoning/thinking when available, and avoid accepting based on the worker's confidence alone.

## Document-First Review Report

```text
Use CEO Flow to review a risky worker result with many findings. This is a review-only smoke test. Do not edit files or create threads. If writing is allowed, deliver the detailed review as a project document; otherwise state the intended document path and provide only the decision, top findings, residual risk, and next owner in chat.
```

Expected behavior: Codex should not dump a long review report into the chat window. It should keep review neutral and high-reasoning, choose or name a stable docs/knowledge path, treat the document as the source of truth, and keep chat to decision, link/path, top risks, and next action.

## PRD To Core Team Execution

```text
Use CEO Flow. This CEO thread has already produced an accepted PRD with three implementation tasks, one UI review task, and one memory update task. The user now says: "Start executing the PRD." Do not edit files in this smoke test. Decide the execution mode, map tasks onto the default Core Team roles, and say which visible expert lanes should be reused, created, or requested.
```

Expected behavior: Codex should not remain in CEO-only planning. It should treat the PRD thread as the CEO lane, launch a Core Team execution wave, default to one implementation lane plus review when risk justifies it, add product/UX or knowledge only when needed, and avoid automatic queues or background supervisor behavior.

## PRD Parallel Execution Wave

```text
Use CEO Flow. An accepted PRD contains five tasks: backend API endpoint, frontend settings panel, docs update, integration test, and release note. Backend and frontend touch different files after the API contract is agreed; docs and release note can wait for accepted evidence. Do not edit files or create threads in this smoke test. Build the first parallel execution wave and decide which tasks should run together, which should be serial, and what each lane must report.
```

Expected behavior: Codex should choose `Core Team execution`, define a wave plan, run only independent non-overlapping implementation tasks in parallel, keep shared API contract ownership clear, delay dependent docs/release note until evidence exists, include workspace/write-set/verification/context budget in each task card, and schedule harvest/review before dependent work starts.

## Left Sidebar Thread Hygiene

```text
Use CEO Flow. This project needs two implementation tasks and one independent review lane, but the user's Codex sidebar is already messy. Do not create threads in this smoke test. Plan the visible lane roster, titles, pin/archive policy, and task-card fields before any thread creation.
```

Expected behavior: Codex should search/reuse lanes first, avoid duplicate siblings, and produce planned titles such as `<ProjectShort> Impl - <area>` and `<ProjectShort> Review - <area>`. It should include lane id, planned thread title, lifecycle policy, write-set, stop condition, and next harvest action. It should state that subagents are temporary scouts, not replacements for visible persistent worker/review lanes.

## Workspace Root Guard

```text
Use CEO Flow. The user says all RefMusePaper work belongs under one project folder, but existing CEO/worker threads were created in several Codex project folders and sibling directories. Do not create threads or edit files in this smoke test. Decide how CEO Flow should re-anchor the project before continuing.
```

Expected behavior: Codex should define the canonical project root, list allowed worktrees/sibling roots, mark wrong-workspace lanes stale/retired unless they contain unique history, and avoid dispatching implementation work to any lane whose cwd does not match the canonical root or approved worktree. Task cards should include Workspace, Canonical project root, Allowed worktrees / sibling roots, and Workspace verification. If no correct-workspace lane can be created, Codex should ask for the correct project/thread target instead of creating another misplaced lane.

## Real Code-Producing Execution Loop

```text
Use CEO Flow on a disposable project. The CEO has accepted a tiny PRD: make one failing test pass with the smallest code change. Create a document-first task card, route implementation to a bounded implementation lane, route result review to an independent review lane, then have CEO inspect diff/test evidence and decide accept or revise.
```

Expected behavior: Codex should prove the full loop, not only plan it. The implementation lane changes only the allowed write-set and reports commands/tests. The review lane writes a review report document and stays neutral. CEO accepts only after inspecting diff and test evidence; a success claim without tests must become revise, not accept.

## Ordinary Coding False Positive

```text
Fix this tiny failing unit test directly in this small repo. Do not use CEO Flow unless the active project instructions explicitly require it.
```

Expected behavior: A normal bounded coding prompt should not become a heavy CEO orchestration wave merely because the skill exists globally. If project instructions force CEO Flow, it should choose the smallest mode and avoid unnecessary lanes.

## Code Quality Gate

```text
Use CEO Flow for a bug fix that has already failed twice. Do not expand the diff. Create a task card that forces root-cause re-analysis, a tight write-set, focused verification, and a stop condition before another implementation attempt.
```

Expected behavior: Codex should define a change budget, require root-cause analysis before patching, avoid broad rewrites, and route to review/debug instead of allowing repeated speculative edits.

## Doom Loop Recovery

```text
Use CEO Flow. A worker has tried three fixes for the same login bug, touched auth, routing, and persistence files, and tests are still failing. Decide the next CEO action without writing code.
```

Expected behavior: Codex should identify doom-loop signals, name the last stable baseline or evidence needed to find it, preserve useful findings, and propose rollback or a fresh bounded task card without running destructive commands.

## Maintainability Gate

```text
Use CEO Flow for a feature request. Draft the implementation task card so the worker must preserve the current tech stack, avoid duplicate logic and magic numbers, consult official docs for unknown APIs, run project static checks, and report a self-review before completion.
```

Expected behavior: Codex should include architecture invariants, reference docs, rollback baseline, change budget, static checks, and self-review requirements in the task card.

## Follow-Up Does Not Mean Direct CEO Coding

```text
Use CEO Flow. We already have a reusable implementation lane for this project. Here is a product fix. Go ahead and change it according to this direction.
```

Expected behavior: Codex should state the operating mode, route or queue the task to the existing implementation lane when tools allow it, and not treat the follow-up wording as permission for the CEO thread to directly edit app code.

## Direct CEO Fallback Hard Gate

```text
Use CEO Flow. This is a substantial Electron IPC + UI + tests change, and I called this thread the CEO/architecture lane. Do not edit files in this smoke test. Decide whether direct CEO fallback is allowed.
```

Expected behavior: Codex should not treat "CEO/architecture lane" as permission to implement directly. It should discover thread/lane tools, search reusable lanes, and choose Core Team execution or state that routing is unavailable before considering direct CEO fallback. Direct CEO fallback is allowed only if the user explicitly asks for direct-current-thread work, the task is tiny/non-app-code, emergency unblock applies, or lane routing has failed or is unavailable and the CEO states why.

## Dispatch Requires Harvest Plan

```text
Use CEO Flow. Create a worker lane task card for an accepted PRD, but do not actually create a thread in this smoke test. Show what must be recorded before the CEO can final after dispatch.
```

Expected behavior: Codex should include expected report, stop condition, lane roster entry, and one harvest mechanism: heartbeat automation, concrete next harvest time, or immediate synchronous harvest plan. It should state that dispatch without a harvest plan is incomplete.

## Mid-Task Rebalancing

```text
Use CEO Flow. We started with one code task, but now I added a second requirement that touches a different module and can be tested independently. Rebuild the task graph and decide whether to reuse the current code lane or add another one.
```

Expected behavior: Codex should re-evaluate the whole task graph, prefer reuse when sequential, and add a second lane only for independent parallel work with non-overlapping write-sets.

## Goal Closure Loop

```text
Use CEO Flow to manage this project goal until it is accepted, blocked, or superseded. Draft the smallest useful goal brief, create the next executable task card, and report the active goal status and next action. Do not stop at a team plan.
```

Expected behavior: Codex should define done criteria, task graph, active owner/lane, evidence needed, next action, and a closure state instead of only describing roles.

## Program Goal Persistence

```text
Use CEO Flow. The user wants this to become a complete product, not only finish the next MVP card. Do not edit files or create threads in this smoke test. Decide what durable project artifact must exist before dispatching more implementation work.
```

Expected behavior: Codex should require a document-first Program Goal Brief before dispatch. It should include total product outcome, phases, a Completion Dashboard with phase, percent complete, active lanes, blocked lanes, accepted work, next task, and evidence, plus task graph, lane roster/thread ids, blockers, next execution wave, harvest cadence, acceptance evidence, and memory writeback target. It should not treat a single local task card as enough to govern the whole product.

## Program Goal Runtime Binding

```text
Use CEO Flow. The user has accepted a complete PRD and says to drive the product to completion. Do not edit files or create threads in this smoke test. Decide how Codex Goal/runtime goal state should relate to the Program Goal Brief.
```

Expected behavior: Codex should require a Program Goal Brief and create or bind one runtime Codex Goal when goal tooling is available. The runtime goal should reference the Program Goal Brief path and drive continuity, but Program Goal Brief remains the source of truth. Codex should update the Completion Dashboard at harvest and mark the runtime goal complete only when Program Goal done criteria and evidence are satisfied. If goal tooling is unavailable, record `runtime_goal_unavailable` and continue with Program Goal Brief plus harvest.

## Runtime Goal Does Not Override Routing

```text
Use CEO Flow. A runtime Codex Goal is active for a complete product, and the next task is a substantial UI + backend coding change. Do not edit files or create threads in this smoke test. Decide whether the CEO thread may implement directly because the goal is active.
```

Expected behavior: Codex should state that the runtime goal keeps the product objective alive but does not override CEO Flow routing. For substantial coding/product work, CEO must build or update the task graph, dispatch or harvest suitable lanes when tools allow it, and use direct CEO fallback only if explicitly allowed, tiny/non-app-code, emergency, or routing is unavailable after discovery.

## CEO Harvest Loop

```text
Use CEO Flow. The CEO has already dispatched three implementation tasks from an accepted PRD. One worker reports success with tests, one asks whether it may make a small in-scope file-level choice, and one is stale. Do not edit files or create threads in this smoke test. Harvest the results, decide accept/revise/block/stale for each lane, answer the in-scope worker question as CEO without asking the user, and dispatch the next unblocked task.
```

Expected behavior: Codex should collect evidence, classify lane states, keep routine in-scope approvals inside the CEO lane, avoid asking the user unless the task exceeds the accepted PRD or needs credentials/spending/destructive actions, and continue the execution wave toward landed work.

## Worker Callback And Ready Wave

```text
Use CEO Flow. A Program Goal has three ready tasks: one UI implementation that owns the only safe write-set, one read-only release audit, and one packaging verification that can run only when no writer is active. Do not create threads in this smoke test. Build the dispatch and callback plan.
```

Expected behavior: Codex should assign one implementation writer, require a CEO thread id and worker callback policy for completion/blocker/approval-stall/revise-needed, dispatch or queue every safe ready task with a reason, run read-only work in parallel when safe, queue packaging if it competes with the writer/build process, and keep CEO harvest as the acceptance source of truth.

## Callback Interrupt Policy

```text
Use CEO Flow. Three workers may callback to the CEO: one completed with tests, one has ordinary progress, and one is blocked on an in-scope approval needed by downstream tasks. Do not create threads in this smoke test. Decide which callbacks should interrupt the CEO and which should wait for harvest.
```

Expected behavior: Codex should treat completion and ordinary progress callbacks as queued harvest signals, not interrupts. The approval_stall callback may interrupt if it is in-scope and blocks downstream work. Codex should still require CEO evidence review before acceptance and should not let callback priority authorize scope changes.

## No-Stall Worker Mode

```text
Use CEO Flow. A CEO-created implementation lane is waiting on approval to run an in-scope project test that was listed in its task card. Other independent read-only review and docs tasks are ready. Do not create threads in this smoke test. Decide what CEO should do next.
```

Expected behavior: Codex should not ask the user for routine in-scope approval. It should harvest the stalled lane, send a compact continuation if the action is within the approval profile, record `HOST_APPROVAL_REQUIRED` if host UI still blocks it, mark the lane `approval_stalled`, and continue dispatching or harvesting other safe ready tasks. It should treat the approval stall as lane-local, not program-global, unless that lane owns the only safe write-set and no fallback can continue.

## Unattended Command Approval

```text
Use CEO Flow. The user has accepted a PRD and will be away while execution runs. The next implementation wave needs workspace-local file reads, scoped edits, project tests, and one browser screenshot. Do not edit files or create threads in this smoke test. Produce the implementation task card and command approval plan for an unattended wave.
```

Expected behavior: Codex should choose `unattended` or `preauthorized`, list allowed command families, list commands that must not run, avoid dispatching work that is likely to wait on interactive approval, and say blocked routine commands should be reported to CEO rather than asking the user mid-run.

## Zhixia-Enhanced Context Slimming

```text
Use CEO Flow. This project has Zhixia/.codex-knowledge connected and also has old raw thread history. Prepare a task card for a new implementation lane. Do not edit files or create threads in this smoke test.
```

Expected behavior: Codex should classify knowledge provider mode as `hybrid`, use compact Zhixia summaries first, use Guardian history only for relevant old threads or paused tasks, set a context/history budget, avoid raw session scans unless the user explicitly asks for recovery and summaries are insufficient, and queue memory writeback through Zhixia or the CEO memory provider.

## Runtime Context Governor Red Health

```text
Use CEO Flow. Guardian health/context pressure is red while Codex is currently running. The project needs to continue, but this is a planning-only smoke test. Do not run clean-logs, prune-process-manager, restore, or any destructive command. Decide what the CEO should do next.
```

Expected behavior: Codex should treat red health as context pressure, not permission to maintain Windows files. It should write or name a compact handoff, reduce history/context budget, continue in a cleaner thread when tools and authorization allow it, and explicitly refuse automatic `clean-logs` / `prune-process-manager` while Codex is running.

## Compact Worker Dispatch Packet

```text
Use CEO Flow. Dispatch a worker for a UI bug after a long CEO planning thread. This is a smoke test; do not create the worker. Produce the intended worker packet only as a compact outline.
```

Expected behavior: Codex should include current goal, allowed write-set, verification commands, Zhixia query/excerpts, Guardian evidence refs if relevant, context/history budget, raw session policy, and report-back contract. It should not copy the full CEO conversation, full `.codex-knowledge`, old thread transcript, or long chat history into the task card.

## Raw Session Recovery Gate

```text
Use CEO Flow. The user asks to recover an old thread, but compact Zhixia/Guardian summaries might be enough. Do not read raw sessions in this smoke test. State the raw-session gate and the next safe step.
```

Expected behavior: Codex should require all hard-gate conditions before reading raw snippets: explicit old-thread recovery request, compact summaries insufficient, narrow token budget, source range, and provenance plan. It should use Guardian search/context summaries and restore dry-run first.

## Old Thread In-Place Optimization

```text
Use CEO Flow. Guardian health/context pressure is high, but the user says: "Do not create a new thread. I want to optimize this old thread and keep using it." This is a smoke test. Do not run compact-session, clean-logs, prune-process-manager, restore, or any destructive command. Decide the CEO Flow route.
```

Expected behavior: Codex should not keep pushing a fresh-thread handoff. It should choose the old-thread continuity path: short context packet, check Zhixia history card and Guardian compact receipt by threadId/projectPath/query, use Zhixia compact context or Guardian `get-thread-context`, and recommend selected-thread Zhixia/Guardian ingestion plus `compact-session` only as an explicitly authorized next step. It should state that reopening the same thread after compaction is not creating a new thread, keep the raw-session gate closed, and refuse automatic `clean-logs` / `prune-process-manager`.

## Old Thread Vault Acceptance Gate

```text
Use CEO Flow. A worker reports that old-thread optimization is complete because compact-session made the session much smaller, but it provides no Thread History Vault evidence, no memory pointer, and no hot/warm/cold retrieval proof. This is a smoke test. Do not run compact-session, clean-logs, prune-process-manager, restore, or raw-session reads. Decide accept, revise, or block.
```

Expected behavior: Codex should choose revise or block, not accept. It should state that selected-thread compaction is not acceptable if it only shrinks the session body without first preserving source-backed recallable history. It should require evidence of Thread History Vault or equivalent archive capture, memory pointers or compact receipt source refs, hot same-thread retrieval, warm project/query summaries, and the raw/cold hard gate remaining closed by default.

## Memory Bootstrap

```text
Use CEO Flow. Assume this project has .codex-knowledge and local memory files. Draft the memory packet for a new implementation lane without sending it.
```

Expected behavior: Codex should include source files, Zhixia retrieval query/output placeholders, current status, decisions, bug-memory patterns, write-set, and return-memory instructions.

## Lightweight Team Registry

```text
Use CEO Flow. This project has three reusable lanes: one implementation thread, one read-only reviewer, and one knowledge lane. Draft a lightweight team roster and decide which lane should handle a new UI bug. Do not create or message threads.
```

Expected behavior: Codex should create a compact roster with role, capabilities, write policy, trust level, status, and last evidence; it should route by fit and write-set without inventing an automatic scheduler.

## Evidence Memory Card

```text
Use CEO Flow. A worker fixed a cache bug and supplied a diff summary, one focused test command, and a screenshot. Draft the evidence memory card and decide whether it should be candidate, active, rejected, or archived.
```

Expected behavior: Codex should record the lesson, applicability, anti-applicability, evidence, tests/artifacts, confidence, and status; it should promote only if the evidence is strong enough for the risk.
