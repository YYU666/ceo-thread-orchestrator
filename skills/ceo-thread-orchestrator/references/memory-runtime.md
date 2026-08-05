# Memory Runtime Lifecycle

Use this reference for provider triggers, compact retrieval, query budgets, precedents, large-file handling, and evidence writeback. Use `context-governance.md` for freeze/takeover authority and `project-continuity.md` for ProjectBrain continuity.

## Contents

- Knowledge provider modes and trigger
- Lifecycle hooks and result contract
- Query types and budgets
- Large knowledge files and local providers
- Precedent retrieval
- Evidence writeback and promotion
- Classification and cooling

## Knowledge Provider Modes

- `none`: newest request, canonical files, docs, task cards, reports, and verification only.
- `project-memory`: canonical memory docs, decisions, handoffs, and bug memory.
- `memory-runtime`: compact provider, including a bounded `.codex-knowledge` helper.
- `history-provider`: source-backed old-task/session provenance and restore evidence.
- `hybrid`: current project memory plus history-provider/vault pointers.

Canonical project files, source, tests, decision logs, and accepted evidence outrank summaries when they disagree.

## Memory Trigger Gate

Enable a configured compact provider when any condition holds:

- the canonical root contains `.codex-knowledge`;
- the user asks to continue, resume, recover, take over, restore memory/history, or inspect prior progress;
- the task depends on accepted decisions, active blockers, module progress, prior bugs/failures, release state, archive history, or workflow precedent.

If use fails or is skipped, record provider, hook/query type, token budget, mode/layers, source refs, and the unavailable reason. Do not claim current project memory without that record.

## Lifecycle Hooks

| Stage | Hook/query | Required use |
| --- | --- | --- |
| Bootstrap/resume | `retrieve_context(project_resume)` | current state, blockers, next action, active lanes |
| Dispatch | `retrieve_context(task_dispatch)` | compact task-specific memory and source refs |
| Pre-task | `retrieve_precedent(task_type)` | prior failures, decisions, and reusable workflow evidence |
| Review | `retrieve_context(review_gate)` or precedent | task card, diff/tests/artifacts, relevant docs, compact memory |
| State change | `observe_event(event)` | checkpoint, broken/stale task, takeover, user rule, heartbeat fuse |
| Harvest/decision | `writeback_evidence(result)` | compact accepted/revise/block/supersede evidence |
| Old-task recovery | `retrieve_context(thread_recovery)` | Hot/Warm continuity before vault/Cold escalation |

For `accept | revise | block | supersede`, Preserve sourceRefs and verify the `writeback_evidence receipt`; never use raw chat as provenance.

Lifecycle requirements:

1. Bootstrap/resume runs `project_resume` when the trigger fires.
2. Worker/reviewer dispatch runs `task_dispatch` and sends only task-relevant excerpts/source refs.
3. Review starts from current artifacts and compact memory, never long worker chat.
4. After a CEO decision, write back a compact evidence packet and verify its receipt when the provider supports receipts.
5. Observe only the state-change events defined in `project-continuity.md`; never create polling from observation.
6. Old-task recovery runs Project Continuity plus `thread_recovery` before raw/vault escalation.

## Result Contract

```text
Memory Runtime result:
  provider / hook / queryType / query / tokenBudget:
  memoryMode:
  memoryLayers: hot / warm / skill / cold
  recallPlan.defaultReadOrder:
  recallPlan.coldLayer.defaultRead:
  top memory items:
  retrieved sourceRefs:
  skipped/unavailable reason:
```

Each item should expose id, kind, summary/excerpt, source refs, freshness, status, why matched, token estimate, and whether human confirmation is required. Results without source refs are advisory.

Layer meaning:

- `hot`: current status, accepted decisions, blockers, module progress, and same-task continuity.
- `warm`: relevant summaries, prior decisions, bugs, handoffs, release notes, and experience cards.
- `skill`: reusable tool/workflow candidates; advisory until approved.
- `cold`: vault/raw/archive provenance; default read is false unless a hard gate authorizes it.

Default read order is Hot -> Warm -> canonical docs/source refs -> Skill when relevant -> history pointers -> Cold only under gate.

## Query Types And Budgets

Preferred query types:

```text
project_resume  task_dispatch  review_gate  bug_repair  architecture
release  thread_recovery  archive_candidate  runtime_diagnosis
tool_skill_lookup  workflow_reuse  handoff  memory_writeback
```

Default budgets:

- `project_resume`: 1500-3000 tokens;
- `task_dispatch` and `review_gate`: 800-1500;
- precedent: 800-1200;
- `thread_recovery`: 1500-3000, higher only after an explicit hard gate.

Stop when source-backed context is sufficient; do not increase limits merely for completeness. Put only the triggered Memory Runtime, continuity, Warm Anchor, and writeback fields into the task card; use `state-schema.md` for their exact record shape.

## Large Knowledge File Rule

Do not read a `.codex-knowledge` file over 50 KB wholesale. Use a bounded helper/index and inspect only cited canonical source ranges.

Allowed: existence/size checks, compact JSON/helper queries, and narrow source inspection after retrieval.

Forbidden by default: full project-resume/retrieval packets, raw sessions, full chats/logs, screenshots/base64, and giant OCR/knowledge dumps.

If compact retrieval is unavailable, record `memory_runtime_unavailable` or `large_memory_helper_unavailable` and continue only from canonical files plus a bounded manual summary. Do not claim full memory bootstrap.

For `.codex-knowledge`, retrieve by task terms and source refs. Do not edit it directly unless the user asks. Prefer canonical docs that the provider can scan. Skill candidates remain drafts; installing or modifying skills still requires explicit approval.

## Precedent Retrieval

Run `retrieve_precedent` before bug repair, UI direction correction, packaging/release, thread recovery, archive/compaction, performance/runtime diagnosis, workflow/skill reuse, and repeated failures.

| Task | Query |
| --- | --- |
| Bug or repeated failure | `bug_repair` |
| UI/architecture correction | `architecture` or `review_gate` |
| Packaging/release | `release` |
| Old-task recovery | `thread_recovery` |
| Archive/slimming | `archive_candidate` |
| Tool/workflow reuse | `tool_skill_lookup` or `workflow_reuse` |
| Performance/context issue | `runtime_diagnosis` or `bug_repair` |

Precedent does not expand scope, authorize tools, replace current source, or override CEO acceptance.

## Evidence Writeback And Promotion

Write back only compact CEO-reviewed packets containing decision, task/goal, write-set, changed files, tests, artifact/source refs, short visual summaries, review decision, risks, next action, confidence, and memory candidates.

Never write raw chat/session text, image/base64 bodies, complete logs/request bodies, credentials, SQLite/database bodies, or giant OCR dumps.

The provider owns durable promotion:

- accepted low-risk source-backed decisions, fixes, handoffs, and current-state summaries may become active/curated under provider policy;
- heuristics, history-derived lessons, preferences, model/workflow policy, cross-project rules, tool/skill records, stale/conflicting claims, and security/archive/install/destructive recommendations remain candidate/review until authorized.

History providers supply provenance and receipts but do not own project-memory promotion.

## Classification And Cooling

For ordinary continuation prioritize product status, accepted decisions, blockers, module progress, and canonical sources. Archive/slimming audits, history-provider records, worker prompts, and raw restore metadata should not dominate unless the query is recovery, archive, performance, or history-specific.

Hot is recent/current; Warm is older same-project or query-relevant evidence; Cold/raw is archival provenance. Before selected-task compaction, preserve full old-task history in a source-backed vault/archive with provenance and recall pointers.
