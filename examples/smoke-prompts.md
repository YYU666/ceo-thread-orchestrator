# Smoke Prompts

Use these prompts to test behavior after installing the plugin. Start with read-only or planning tasks before allowing live thread creation, automations, subagents, or worktrees.

## CEO Only

```text
Use CEO Thread Orchestrator to audit this project structure. Do not edit files or create threads. Report the smallest useful operating model.
```

Expected behavior: Codex should act as CEO/PM, inspect local instructions when available, and avoid delegation because the task is read-only.

## Single Code Lane

```text
Use CEO Thread Orchestrator for a small bug fix. Create a task card for one implementation lane, but do not create a new thread unless the current tool contract and user authorization allow it.
```

Expected behavior: Codex should prefer one implementation lane and define write-set, acceptance criteria, tests, and report requirements.

## Build Plus Review

```text
Use CEO Thread Orchestrator for a risky UI change. Plan implementation plus independent review. Reuse existing specialist threads first.
```

Expected behavior: Codex should propose an implementer plus reviewer pattern and keep CEO as final acceptance gate.

## Follow-Up Does Not Mean Direct CEO Coding

```text
Use CEO Thread Orchestrator. We already have a reusable implementation lane for this project. Here is a product fix. Go ahead and change it according to this direction.
```

Expected behavior: Codex should state the operating mode, route or queue the task to the existing implementation lane when tools allow it, and not treat the follow-up wording as permission for the CEO thread to directly edit app code.

## Mid-Task Rebalancing

```text
Use CEO Thread Orchestrator. We started with one code task, but now I added a second requirement that touches a different module and can be tested independently. Rebuild the task graph and decide whether to reuse the current code lane or add another one.
```

Expected behavior: Codex should re-evaluate the whole task graph, prefer reuse when sequential, and add a second lane only for independent parallel work with non-overlapping write-sets.

## Goal Closure Loop

```text
Use CEO Thread Orchestrator to manage this project goal until it is accepted, blocked, or superseded. Draft the smallest useful goal brief, create the next executable task card, and report the active goal status and next action. Do not stop at a team plan.
```

Expected behavior: Codex should define done criteria, task graph, active owner/lane, evidence needed, next action, and a closure state instead of only describing roles.

## Memory Bootstrap

```text
Use CEO Thread Orchestrator. Assume this project has .codex-knowledge and local memory files. Draft the memory packet for a new implementation lane without sending it.
```

Expected behavior: Codex should include source files, Zhixia retrieval query/output placeholders, current status, decisions, bug-memory patterns, write-set, and return-memory instructions.
