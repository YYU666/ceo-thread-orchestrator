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

## Mid-Task Rebalancing

```text
Use CEO Thread Orchestrator. We started with one code task, but now I added a second requirement that touches a different module and can be tested independently. Rebuild the task graph and decide whether to reuse the current code lane or add another one.
```

Expected behavior: Codex should re-evaluate the whole task graph, prefer reuse when sequential, and add a second lane only for independent parallel work with non-overlapping write-sets.

## Memory Bootstrap

```text
Use CEO Thread Orchestrator. Assume this project has .codex-knowledge and local memory files. Draft the memory packet for a new implementation lane without sending it.
```

Expected behavior: Codex should include source files, Zhixia retrieval query/output placeholders, current status, decisions, bug-memory patterns, write-set, and return-memory instructions.
