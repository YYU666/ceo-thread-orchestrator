# CEO Flow Runtime Context Governor Report - 2026-06-11

## Decision

Decision: accept release-candidate revision

This revision narrows CEO Flow's Zhixia/Guardian integration from history maintenance toward Codex runtime context governance.

The key behavior is now:

- use compact task packets;
- prefer Zhixia compact context and source refs;
- use Guardian only for source-backed history evidence, health/context pressure, old-thread lookup, restore dry-run, and raw-session gate;
- write compact handoffs or move to cleaner lanes under context pressure;
- do not run automatic cleanup or process pruning.

## Files Updated

- `skills/ceo-thread-orchestrator/SKILL.md`
- `skills/ceo-thread-orchestrator/agents/openai.yaml`
- `docs/CEO_FLOW_GUARDIAN_INTEGRATION.md`
- `examples/smoke-prompts.md`
- `README.md`
- `docs/INTRODUCTION.md`
- `docs/INTRODUCTION.zh-CN.md`
- `CHANGELOG.md`

Installed local skill was synced after validation:

- `<codex-home>/skills/ceo-thread-orchestrator/SKILL.md`
- `<codex-home>/skills/ceo-thread-orchestrator/agents/openai.yaml`

## Rule Changes

### Runtime Context Governor

CEO Flow now explicitly controls context/history budget at:

- new-thread bootstrap;
- task dispatch;
- old-thread reuse;
- review;
- harvest;
- memory writeback.

Default packet:

```text
current goal
bounded task card
allowed write-set
verification commands
Zhixia compact excerpts and source refs
Guardian evidence refs only when relevant
context/history budget
raw session policy
report-back contract
```

Default exclusions:

- full CEO conversation;
- full `.codex-knowledge/`;
- full implementation thread transcript;
- broad raw-session scans;
- old chat transcripts as task context.

### Context Pressure Fuse

When Guardian health/context pressure is yellow/red, or a CEO/worker thread is too long, stalled, or fragmented, CEO Flow should:

- reduce history retrieval;
- write or update compact handoff;
- create or reuse a cleaner lane when tools and authorization allow it;
- avoid pasting more long history into the same thread.

This is a Codex runtime-load response. It is not Windows maintenance.

### Guardian Boundary

Guardian is limited to:

- source-backed history evidence;
- health/context pressure;
- old-thread lookup;
- restore dry-run;
- raw-session gate;
- provenance or receipt for history-derived candidates.

Guardian is not:

- Windows Task Scheduler;
- automatic log cleanup;
- automatic process-manager pruning;
- durable memory owner;
- default raw-session reader.

`clean-logs` and `prune-process-manager` remain manual/explicitly authorized maintenance commands and must not run automatically while Codex is active.

### Review And Writeback Slimming

Review lanes should start from:

- task card;
- diff;
- tests;
- artifacts;
- relevant docs;
- compact evidence refs.

They should not start by reading the implementation thread's long conversation.

Workers report memory update candidates only. Durable writeback targets are Decision, Handoff, Bug/Experience card, or KnowledgeItem, owned by Zhixia or the CEO memory provider.

## Smoke Coverage Added

`examples/smoke-prompts.md` now includes:

1. Guardian health red should trigger compact handoff / cleaner-thread planning, not automatic `clean-logs`.
2. Worker dispatch after a long CEO thread should use a compact packet, not long chat history.
3. Old-thread recovery should enforce the raw-session hard gate before reading snippets.

## Validation Summary

Validation was run after the revision wave:

```text
repo skill validator: pass
repo plugin validator: pass
installed CEO Flow skill validator: pass
git diff --check: pass, line-ending warnings only
privacy/path scan: pass, no machine-specific local path matches
Guardian read-only smoke: pass
installed skill sync: pass
```

No `clean-logs`, `prune-process-manager`, destructive command, or actual restore was run.

## Residual Risk

- The rule set is stronger, but behavior still depends on fresh threads loading the updated installed skill.
- The new Runtime Context Governor behavior should be forward-tested on a real long-thread project before calling it stable.
- Public docs now state the correct boundary, but users may still confuse Guardian health with cleanup permission; release notes should repeat that cleanup is manual.

## CEO Decision

Decision: accept

Next owner: release gate / controlled user testing.
