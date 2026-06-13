# CEO Flow Old-Thread Continuity Report - 2026-06-11

## Decision

Decision: accept

This revision aligns Runtime Context Governor with the updated Zhixia/Guardian product decision: CEO Flow should reduce Codex runtime context without forcing a new thread when the user explicitly wants to keep using an old thread.

## Scope

Updated:

- `skills/ceo-thread-orchestrator/SKILL.md`
- `docs/CEO_FLOW_GUARDIAN_INTEGRATION.md`
- `examples/smoke-prompts.md`
- `README.md`
- `docs/INTRODUCTION.md`
- `docs/INTRODUCTION.zh-CN.md`
- `CHANGELOG.md`

Installed local skill was synced after repo edits.

## Policy Changes

### Old-Thread Continuity

When the user explicitly asks to keep using an old thread, CEO Flow must not default to recommending a new thread. It should first check:

1. Zhixia history card by thread id, project path, or query.
2. Guardian compact receipt for the selected thread.
3. Zhixia compact context or Guardian `get-thread-context`.
4. Whether the user explicitly allowed old-thread optimization for the selected thread.

### Context Governor Decision Order

1. Use short task packet and compact context first.
2. If the thread is too long and the user allows optimizing it, route to Zhixia ingestion plus selected-thread `compact-session`.
3. Continue the same old thread using Zhixia/Guardian retrieval after compaction.
4. Reopen the same thread when Codex needs to reread the slimmed session body.
5. Use fresh-thread handoff only when hot memory cannot release, the session is corrupted, compaction is unavailable, authorization is missing, or the user chooses that route.

### Compaction Safety Contract

Selected-thread compaction is not default read-only Guardian behavior. It is allowed only after explicit user trigger and a clear `ThreadId`.

Required receipt:

- before hash;
- backup hash;
- after hash;
- before byte count;
- backup byte count;
- after byte count;
- backup path;
- restore hint.

The operation must use full backup, backup SHA-256 verification, temp write, and replacement. If backup or hash verification fails, the operation must stop before replacement.

### What Remains Forbidden

CEO Flow must not treat Guardian as:

- Windows Task Scheduler;
- automatic log cleanup;
- automatic process-manager pruning;
- default raw-session reader;
- owner of durable project memory.

`clean-logs` and `prune-process-manager` remain manual maintenance commands and are not old-thread slimming paths.

## Smoke Coverage Added

Added smoke prompt: `Old Thread In-Place Optimization`.

Expected behavior:

- do not force fresh-thread handoff;
- check Zhixia history card and Guardian compact receipt;
- use compact context and `get-thread-context`;
- recommend selected-thread compaction only as an explicitly authorized next step;
- state that reopening the same thread is not creating a new thread;
- keep raw-session gate closed;
- refuse automatic `clean-logs` / `prune-process-manager`.

## Validation Results

Completed:

- Repo skill/plugin validator: pass.
- Installed skill validator: pass.
- Repo skill and installed skill SHA-256: match.
- Privacy/path scan for local user paths and private project paths: pass, no matches.
- Smoke prompt coverage: added `Old Thread In-Place Optimization`.
- Guardian health smoke: pass, `report -Json` returned `severity: green`.
- Guardian mutation commands: not run.
- `clean-logs`: not run.
- `prune-process-manager`: not run.
- Actual `compact-session`: not run.

## Smoke Result

Prompt under test:

```text
Use CEO Flow. Guardian health/context pressure is high, but the user says: "Do not create a new thread. I want to optimize this old thread and keep using it." This is a smoke test. Do not run compact-session, clean-logs, prune-process-manager, restore, or any destructive command. Decide the CEO Flow route.
```

Expected CEO route:

1. Stay in CEO-only planning or Core Team execution management, not direct maintenance mode.
2. Choose old-thread continuity rather than forced fresh-thread handoff.
3. Use short context packet plus Zhixia history card / compact context.
4. Check Guardian compact receipt or `get-thread-context` by selected thread id.
5. Recommend selected-thread `compact-session` only as the next explicitly authorized step.
6. State that reopening the same thread after compaction is not creating a new thread.
7. Keep raw-session gate closed unless compact summaries fail and the user explicitly asks for old detail recovery.
8. Refuse automatic `clean-logs` and `prune-process-manager`.

Smoke decision: pass by rule inspection. Live execution was intentionally not run because it would require a real selected thread and could mutate user sessions.

## Residual Risks

| Risk | Status | Mitigation |
|---|---|---|
| Agents may still over-recommend new threads from older installed skill context | Mitigated after installed skill sync and fresh thread test |
| `compact-session` availability may differ by Guardian deployment | Mitigated by "when supported" wording and receipt contract |
| In-place compaction is higher risk than read-only history lookup | Mitigated by explicit trigger, selected ThreadId, backup/hash/temp-write/receipt requirements |
| Same-thread reopen may still retain hot UI context until the host reloads | Mitigated by documenting reopen as same-thread refresh and keeping fresh-thread handoff as fallback |
