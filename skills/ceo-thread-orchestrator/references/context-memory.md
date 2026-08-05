# Context And Memory Router

Use this router when a task involves project continuity, context pressure, `.codex-knowledge`, a Memory Runtime, a history provider, takeover, or compact recovery. Load only the focused reference whose gate fired.

## Routing

- Context pressure, sticky freeze, strict takeover packets, generation idempotency, and refresh binding: `context-governance.md` plus `scripts/context_governor.py`.
- ProjectBrain roles/slots, exact identity, pagination, receipts, runtime events, and Warm Anchor: `project-continuity.md`.
- Provider hooks, query types/budgets, result envelopes, precedents, large-file handling, and evidence writeback: `memory-runtime.md`.
- Zhixia app-owned adapter details: `zhixia-app-owned-governance.md`.
- Old-task vault/history evidence, compaction safety, restore, and raw-session gate: `guardian-history.md`.
- Program state and gate record fields: `state-schema.md`.

## Trigger Summary

Use compact project memory when `.codex-knowledge` exists or the request depends on continuation, recovery, accepted decisions, blockers, prior failures, release state, or old-task evidence. Do not claim remembered project state if the configured provider was skipped or failed.

For large/program continuation, takeover, recovery, direction switch, active runtime Goal, or pre-dispatch checks:

1. Run app-owned `verify` and a read-only exact scan when required.
2. Run `scripts/context_governor.py` on compact metrics/state.
3. On takeover/recovery, run Project Continuity and request `prepare_takeover`.
4. Inject one verified bounded generation into a clean task with `replace_long_thread_context`.
5. Fail closed and stop the old driver when pressure, authority, identity, freshness, content, budget, or generation checks fail.

Heartbeat, tool-result, commentary, and unchanged status wakeups do not re-query memory or re-inject context.

## Context Budget

Prefer newest goal, bounded task card, source refs, compact Hot/Warm excerpts, verification commands, and a short history budget. Never copy full CEO conversations, raw sessions, complete logs, giant knowledge files, image/base64 bodies, or full worker chats into task cards or takeover packets.

Default read order:

1. compact recovery/program/task packet;
2. Hot/Warm memory and required continuity slots;
3. canonical docs/source refs;
4. lane roster and current evidence;
5. history-provider/vault pointers;
6. narrow Cold/raw evidence only after its hard gate.

Visual artifacts stay local; context and memory carry paths, hashes, dimensions, short summaries, and decisions only.

## Ownership Boundary

CEO Flow owns task lifecycle, context budget, freeze/stop decisions, harvest drivers, clean-task creation, evidence review, and accept/revise/block. The provider owns ingestion, dedupe, storage, classification, retrieval, verification, packet content, and promotion. A provider cannot shrink an already bloated Codex task; CEO Flow must stop or replace it.
