# Context And Memory Reference

Use this short router when a task involves runtime context size, memory/reference routing, `.codex-knowledge/`, memory providers, history providers, old-thread continuity, raw sessions, visual payload boundaries, or compact recovery. For detailed rules, load the focused reference below instead of keeping this file as a giant mixed policy.

## Runtime Context Governor

CEO Flow keeps active threads lean, source-backed, and recoverable. It is not a Windows Task Scheduler, automatic log cleaner, automatic process-manager pruner, or background cleanup service.

At bootstrap, dispatch, reuse, review, harvest, and writeback:

- use newest goal, bounded task card, allowed write-set, verification commands, relevant source refs, compact knowledge excerpts, and a short history budget;
- do not copy full CEO conversations into worker prompts;
- do not send full `.codex-knowledge/` or long generated knowledge files by default;
- do not read raw sessions or long chat transcripts by default;
- do not treat old threads as free context;
- prefer compact retrieval and source-backed packets over stacking instructions in long threads;
- for visual tasks, keep screenshots/reference/generated images in local artifacts and pass only paths, hashes, dimensions, short summaries, and decisions through chat and memory.

When a CEO/project-main thread is broken, context-exhausted, stale, unreadable, or bloated by image/base64 payloads, recover through a compact `ThreadRecoveryPacket`, not by forking or copying the old chat or visual payloads.

Recommended takeover read order:

1. ThreadRecoveryPacket;
2. Program Goal Brief and Completion Dashboard;
3. compact project memory / Memory Runtime `retrieve_context(queryType=project_resume)`;
4. active lane roster and latest callbacks;
5. canonical project docs/source files;
6. Memory Runtime / history-provider / vault sourceRefs;
7. cold/raw session evidence only through the raw-session gate.

## Reference Router

- Memory Runtime lifecycle, trigger gate, task-card retrieval fields, writeback/promotion, large `.codex-knowledge` file limits, precedent lookup, and Hot/Warm/Skill/Cold result contract: `memory-runtime.md`.
- History-provider old-thread continuity, Thread History Vault/source-backed archive evidence, selected-thread compaction safety, restore dry-run, raw-session gate, and freshness labels: `guardian-history.md`.
- Visual evidence and image payload budgets: `visual-evidence.md`.
- FlowSkill search/capture/score bridge: `flowskill-hook.md`.
- Program Goal, Completion Dashboard, ThreadRecoveryPacket, lane roster, harvest driver, and memory candidate schemas: `state-schema.md`.

## Knowledge Provider Modes

- `none`: no durable provider; use newest request, local source files, task cards, reports, and verification.
- `project-memory`: canonical local memory docs, decision logs, handoff logs, and bug memory.
- `memory-runtime`: compact project knowledge from a configured provider or `.codex-knowledge/` helper.
- `history-provider`: source-backed old Codex thread history, paused-task discovery, health, receipts, and restore dry-run evidence.
- `hybrid`: current project memory plus old-thread/history provenance; preferred when both are configured.

Use canonical project files, source code, tests, decision logs, and worker reports as stronger evidence than summaries when they disagree.

## Minimal Context Budget

- Bootstrap/resume: retrieve compact project memory first, then inspect only cited sourceRefs.
- Dispatch: include only the memory packet and sourceRefs the lane needs.
- Review/harvest: inspect current diffs/tests/artifacts plus compact precedent; do not reload long worker chat.
- Old-thread recovery: retrieve hot/warm memory before history-provider/vault pointers; cold/raw snippets require the hard gate.
- Visual tasks: preserve visual QA, but keep image bodies out of task cards, callbacks, memory, FlowSkill candidates, and third-party logs.

## Boundary

CEO Flow may generate compact evidence/writeback packets and decide when memory is needed. The configured provider owns ingestion, dedupe, layer classification, retrieval implementation, and durable promotion. History providers supply source-backed provenance and recovery evidence, not automatic memory ownership or cleanup authority.
