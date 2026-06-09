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

## PRD To Core Team Execution

```text
Use CEO Flow. This CEO thread has already produced an accepted PRD with three implementation tasks, one UI review task, and one memory update task. The user now says: "Start executing the PRD." Do not edit files in this smoke test. Decide the execution mode, map tasks onto the default Core Team roles, and say which visible expert lanes should be reused, created, or requested.
```

Expected behavior: Codex should not remain in CEO-only planning. It should treat the PRD thread as the CEO lane, launch a Core Team execution wave, default to one implementation lane plus review when risk justifies it, add product/UX or knowledge only when needed, and avoid automatic queues or background supervisor behavior.

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

## CEO Harvest Loop

```text
Use CEO Flow. The CEO has already dispatched three implementation tasks from an accepted PRD. One worker reports success with tests, one asks whether it may make a small in-scope file-level choice, and one is stale. Do not edit files or create threads in this smoke test. Harvest the results, decide accept/revise/block/stale for each lane, answer the in-scope worker question as CEO without asking the user, and dispatch the next unblocked task.
```

Expected behavior: Codex should collect evidence, classify lane states, keep routine in-scope approvals inside the CEO lane, avoid asking the user unless the task exceeds the accepted PRD or needs credentials/spending/destructive actions, and continue the execution wave toward landed work.

## Unattended Command Approval

```text
Use CEO Flow. The user has accepted a PRD and will be away while execution runs. The next implementation wave needs workspace-local file reads, scoped edits, project tests, and one browser screenshot. Do not edit files or create threads in this smoke test. Produce the implementation task card and command approval plan for an unattended wave.
```

Expected behavior: Codex should choose `unattended` or `preauthorized`, list allowed command families, list commands that must not run, avoid dispatching work that is likely to wait on interactive approval, and say blocked routine commands should be reported to CEO rather than asking the user mid-run.

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
