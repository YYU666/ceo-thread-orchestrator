# Memory Runtime Reference

Use this reference when CEO Flow must retrieve compact project memory, dispatch source-backed task cards, look up precedents, write back accepted evidence, or coordinate a configured local Memory Runtime without reading giant Markdown, raw chats, raw sessions, or visual payload bodies.

CEO Flow owns trigger timing, task-card fields, evidence packets, and accept/revise/block decisions. The Memory Runtime provider owns ingestion, dedupe, Hot/Warm/Skill/Cold classification, storage, retrieval behavior, and promotion policy. Provider-specific tools are optional examples; equivalent local providers may implement the same contract.

## Knowledge Provider Modes

- `none`: no durable provider; use newest request, local source files, task cards, reports, and verification.
- `project-memory`: canonical local memory docs, decision logs, handoff logs, and bug memory.
- `memory-runtime`: compact provider for local project knowledge, including `.codex-knowledge/` when available.
- `history-provider`: source-backed old thread/session history and restore evidence; see `guardian-history.md`.
- `hybrid`: Memory Runtime for current project knowledge plus a history provider/sourceRefs for old thread evidence; preferred when both are configured.

Use canonical project files, source code, tests, decision logs, and worker reports as stronger evidence than summaries when they disagree.

## Memory Trigger Gate

Memory Runtime is a default lifecycle action when local memory is present or the user is asking for continuity. It is not merely an optional tool.

Enable a configured compact Memory Runtime provider when any trigger is true:

- canonical project root contains `.codex-knowledge/`;
- user mentions continuing a project, resuming work, taking over an old thread, restoring memory, history, previous progress, a configured memory provider, a history provider, or old-thread recovery;
- task depends on accepted decisions, active blockers, current module progress, prior bugs, release state, archive/slimming history, or repeated failures.

CEO Flow must not rely on model memory alone to state project status under these triggers. If provider use fails or is skipped, record:

```text
Memory Runtime result:
  provider:
  hook:
  queryType:
  query:
  tokenBudget:
  memoryMode: none | project-memory | memory-runtime | history-provider | hybrid
  memoryLayers:
    hot:
    warm:
    skill:
    cold:
  recallPlan:
    defaultReadOrder:
    coldLayer.defaultRead: false unless hard gate is satisfied
  top memory items:
  retrieved sourceRefs:
  skipped/unavailable reason:
```

If this record is absent, CEO must not claim it already understands project state.

When a provider offers a JSON/helper interface, prefer bounded machine packets, for example:

```text
retrieve_context(task_goal, queryType=project_resume, tokenBudget=1500-3000)
retrieve_context(task_goal, queryType=task_dispatch, tokenBudget=800-1500)
retrieve_precedent(task_type, tokenBudget=800-1200)
retrieve_context(queryType=thread_recovery, threadId=<id>, tokenBudget=1500-3000)
```

Provider-specific commands belong in optional integration docs, not the core public contract.
## Memory Runtime Lifecycle

A compact project memory provider may expose explicit runtime hooks such as `retrieve_context(task_goal)`, `retrieve_precedent(task_type)`, `writeback_evidence(result)`, and `promote_memory(candidate)`. Any project may supply an equivalent local memory runtime.

CEO Flow uses the provider as a lifecycle service, not as a giant context file:

| CEO Flow stage | Memory Runtime hook | CEO use |
| --- | --- | --- |
| Bootstrap / resume | `retrieve_context(task_goal)` with `queryType=project_resume` | confirm project state, current source of truth, blockers, next action, active lanes |
| Dispatch / task card | `retrieve_context(task_goal)` with `queryType=task_dispatch` | build compact `Memory packet` with source-backed excerpts, constraints, and sourceRefs |
| Pre-task precedent | `retrieve_precedent(task_type)` | check prior bug repairs, UI decisions, packaging/release evidence, archive rules, or tool-skill boundaries |
| Review gate | `retrieve_context(...)` or `retrieve_precedent(...)` with `queryType=review_gate` | give reviewer task card, diff/tests/artifacts, relevant docs, and compact memory; do not start from long worker chat |
| Harvest | `writeback_evidence(result)` candidate | capture CEO decision, evidence, missing evidence, blocker, revise reason, or accepted outcome |
| Handoff | `writeback_evidence(result)` candidate plus compact Handoff | preserve next action and source refs instead of whole chat history |
| Old-thread recovery | `retrieve_context(...)` with `queryType=thread_recovery` | retrieve hot/warm history by threadId, parent CEO, project path, and query before cold/raw gated recovery |

Lifecycle requirements:

1. Bootstrap/resume/takeover must run `retrieve_context(task_goal, queryType=project_resume)` when the Memory Trigger Gate fires. Output must record provider, query, token budget, memoryMode, memoryLayers, recallPlan, top memory items, retrieved sourceRefs, and skipped/unavailable reason.
2. Dispatch to worker/reviewer must run `retrieve_context(task_goal, queryType=task_dispatch)` first. The task card must include `Memory packet`, `Retrieved source refs`, `Memory Runtime query / context budget`, and a no-long-history rule: no full `.codex-knowledge`, no raw session, no long chat transcript.
3. Review gate should use `queryType=review_gate` and start from task card, diff/tests/artifacts, relevant docs, and compact memory, not implementation-thread chat.
4. After CEO decides `accept | revise | block | supersede`, create a compact evidence packet. If Memory Runtime is available, call or prepare `writeback_evidence(result)`. If unavailable, record the skipped reason.
5. Broken-thread or old-thread recovery must retrieve `queryType=thread_recovery` before history-provider/vault fallback. Raw session snippets remain behind the raw-session gate.

Preferred query types:

```text
project_resume
task_dispatch
review_gate
bug_repair
architecture
release
thread_recovery
archive_candidate
runtime_diagnosis
tool_skill_lookup
workflow_reuse
handoff
memory_writeback
```

Every provider result used in a task card or review should expose a compact result envelope plus `items[]` with source/provenance fields when available:

```text
Memory Runtime result:
  memoryMode:
  memoryLayers:
    hot:
    warm:
    skill:
    cold:
  recallPlan:
    defaultReadOrder:
    coldLayer.defaultRead:
  top memory items:
  retrieved sourceRefs:
```

`memoryLayers` meaning:

- `hot`: current project status, accepted decisions, active blockers, current module progress, same-thread continuation.
- `warm`: relevant project summaries, prior decisions, bugs, handoffs, release/package notes, and experience cards.
- `skill`: reusable tool/skill/workflow candidates and reusable-skill provider records; advisory only until approved.
- `cold`: history-provider/vault/raw-history/archive evidence. Default read is false unless `thread_recovery`, archive/performance, or raw-session hard gate applies.

`recallPlan.defaultReadOrder` should prefer hot -> warm -> canonical docs/source refs -> skill when relevant -> history-provider/sourceRefs -> cold only under gate.

Item contract:

```text
item id:
kind:
summary/excerpt:
sourceRefs:
freshness:
status:
whyMatched:
tokenEstimate:
requiresHumanConfirmation:
```

If the provider cannot supply source refs, treat the result as advisory context only.

## Long-Term Memory Anchor Gate

Long-Term Memory Anchor Gate prevents long-running projects from drifting when Hot memory and recent worker callbacks dominate the context. It is event-triggered only. It is not heartbeat, not a background timer, and not every-turn recall.

Trigger when any is true:

- new CEO takeover, thread recovery, or broken CEO recovery;
- starting a new module, wave, or writer lane;
- major acceptance that changes product progress, completion percentage, architecture direction, UI direction, release/open-source/commercial readiness, or long-term claims;
- user questions direction drift, memory loss, over-proofing, over-UI, over-testing, or missing original product goal;
- three consecutive proof/test/support slices occurred without checking the product anchor;
- task touches original PRD, product positioning, ordinary-user experience, core architecture principles, immutable constraints, or long-term boundaries;
- Hot short-term memory conflicts with Warm anchors or seems over-optimistic.

Do not trigger for:

- ordinary status reports;
- waiting for worker/reviewer callbacks;
- short polling inside the same unchanged task;
- tiny local bug fixes;
- the same task when the gate already ran and no new evidence changes direction;
- any two-minute heartbeat, background inspection, or always-on patrol.

Read order and budget:

```text
Hot memory: current goal, recent accepted work, active blockers, current module, next action; 600-1200 tokens.
Warm Anchor: long-term goal, original PRD/product position, architecture principles, UX principles, immutable boundaries, rejected directions, completion/readiness vocabulary; 500-900 tokens.
Cold: sourceRefs only by default, 0-300 tokens.
```

Cold/raw body reads are allowed only for thread recovery, evidence conflict, insufficient summaries, or explicit narrow user recovery request. If cold/raw is read, record reason, source range, provenance, and token budget. Do not read giant Markdown, raw sessions, vault bodies, long transcripts, image/base64, or full logs merely to be complete.

Required output:

```text
Long-Term Memory Anchor Gate:
  Hot memory used:
  Warm anchor used:
  Direction check: aligned | drifting | conflict | insufficient evidence
  If drifting:
    correction:
    blocked or revised task:
  Source refs:
  Cold history read:
    yes/no
    reason if yes:
```

Task-card field:

```text
Warm Anchor Gate:
  triggered: yes/no
  reason:
  warm query:
  anchor summary:
  direction check:
  sourceRefs:
  cold read: no by default
```

Boundary:

- Warm Anchor does not replace current evidence.
- Warm Anchor does not expand scope or authorize tools.
- Warm Anchor does not authorize raw history reads.
- Warm Anchor does not force repeated planning.
- Its job is to remind CEO why the project exists, what must not be forgotten, which directions were rejected, and which completion/readiness claims cannot be overstated.

Priority when Hot and Warm conflict:

1. newest explicit user goal;
2. canonical docs and accepted evidence;
3. Warm Anchor as conflict/correction signal;
4. no guessing or smoothing conflicts into `accepted`.
## Task Card Memory Runtime Fields

For memory-enabled dispatch, include only the fields needed for the task:

```text
Knowledge provider mode:
Memory Runtime query:
  provider:
  hook: retrieve_context | retrieve_precedent
  queryType:
  query:
  projectPath/projectId:
  threadId:
  parentCeoThreadId:
  tokenBudget:
Memory Runtime result:
  memoryMode:
  memoryLayers:
    hot:
    warm:
    skill:
    cold:
  recallPlan:
    defaultReadOrder:
    coldLayer.defaultRead:
  top memory items:
  retrieved sourceRefs:
Memory packet:
  compact excerpts:
  constraints:
  warnings:
Warm Anchor Gate:
  triggered:
  reason:
  warm query:
  anchor summary:
  direction check:
  sourceRefs:
  cold read:
Writeback target:
Promotion boundary:
```

Default token budgets should stay small:

- project_resume: 1500-3000 tokens;
- task_dispatch: 800-1500 tokens;
- review_gate: 800-1500 tokens;
- precedent: 800-1200 tokens;
- thread_recovery: 1500-3000 tokens by default; explicit higher budget only when the hard gate is satisfied.

Do not increase retrieval limits merely to be complete. Stop when high-quality source-backed context is sufficient.
## Large Knowledge File Rule

Do not read large `.codex-knowledge` files as full context by default. If any single file such as `project-resume.md`, `retrieval-packet.md`, `knowledge-items.md`, `experience-cards.md`, `project-knowledge.md`, `skill-candidates.md`, or `tool-skill-inventory.md` exceeds 50 KB, CEO Flow must use the Memory Runtime helper/JSON small-packet path instead of reading the whole file into the CEO thread.

Allowed:

- file existence and size checks;
- helper JSON calls with `--json`, `--runtime-context`, `--precedent`, `--recover-thread`, `--token-budget`, and `--limit`;
- narrow source-file inspection after compact retrieval points to a relevant canonical file.

Forbidden by default:

- pasting full `.codex-knowledge` Markdown into task cards;
- treating a giant project-resume or retrieval-packet as the whole project state;
- reading raw sessions, screenshots/base64, complete logs, or full old chats to compensate for missing retrieval.

If helper/JSON retrieval is unavailable, record `memory_runtime_unavailable` or `large_memory_helper_unavailable` and continue only from canonical source files, docs, and a bounded manual summary. Do not claim full memory bootstrap.
## Optional `.codex-knowledge` Provider Workflow

When `.codex-knowledge/` exists, treat the workspace as memory-runtime enabled if a compact helper or bounded index is available. Look for files such as `project-knowledge.md`, `context.md`, `knowledge-items.md`, `experience-cards.md`, and `skill-candidates.md`, but do not read large files wholesale.

Retrieval:

- Prefer compact query/excerpts over reading the whole knowledge base.
- Use query terms from task goal, files, feature names, bugs, decisions, and project path.
- Increase retrieval limits only when the lane truly needs broader memory.

Writeback:

- Workers report memory update candidates.
- CEO or active memory provider decides whether the result becomes a Decision, Handoff, Bug/Experience card, or KnowledgeItem.
- Do not edit `.codex-knowledge/` directly unless the user explicitly asks.
- Prefer durable updates in canonical markdown/docs that a memory provider can scan.
- When a Memory Runtime exists, call writeback only with compact accepted/revise/block evidence packets, not raw chats or raw session bodies.

Skill candidates from any memory provider are draft material only. Install or modify skills from them only with explicit user approval.
## Precedent Retrieval

Use `retrieve_precedent(task_type)` before tasks where prior experience can prevent repeat mistakes:

| Task type | Query type | Use |
| --- | --- | --- |
| Bug repair | `bug_repair` | prior fixes, failed attempts, root causes, do-not-repeat cards |
| UI redesign | `architecture` or `review_gate` | product rules, UX decisions, current design docs, rejected approaches |
| Packaging / installer | `release` | release runbooks, packaging commands, known installer/test issues |
| Release readiness | `release` | evidence gates, external validation status, residual risks |
| Thread archive / slimming | `archive_candidate` | vault, receipt, memory pointer, cooling state, blockers |
| Old-thread recovery | `thread_recovery` | hot/warm summaries before cold/raw |
| Tool or skill reuse | `tool_skill_lookup` or `workflow_reuse` | purpose, trigger, risk boundary, safe/forbidden command labels |
| Performance problem | `runtime_diagnosis` or `bug_repair` | bloat, context pressure, slow save/load, memory, database, rendering, or repeated stalls |
| Repeated failure | `bug_repair` or `workflow_reuse` | failed attempts, do-not-repeat lessons, better routing/review strategy |

Precedents are context and risk signals. They do not expand the task scope, authorize tools, replace current source files, or override CEO accept/revise/block.

Precedent is required before: bug repair, UI direction correction, packaging/release, thread recovery, one-click slimming/archive/compaction, performance problems, workflow/skill reuse, and any issue known to have failed repeatedly.
## Evidence Writeback And Promotion Boundary

Workers report candidates; CEO inspects evidence; the memory provider owns durable writeback and promotion policy.

`writeback_evidence(result)` may receive compact packets such as:

```text
decision: accept | revise | block | supersede
task id:
goal:
write-set:
changed files:
commands/tests:
artifacts:
visual evidence: paths + hashes + dimensions + short summaries only; no image bytes/base64/data:image
review decision:
sourceRefs:
freshness:
confidence:
residual risk:
memory candidates:
skipped/unavailable reason:
```

Writeback packets may contain only decisions, evidence paths/sourceRefs, files/tests, visual artifact paths/hashes/summaries, risks, next steps, and experience candidates. They must not contain raw chat, raw session text, image/base64/data:image, full logs, credentials, complete request bodies, or giant OCR dumps.

Accepted low-risk, source-backed evidence may become `active`, `ready`, or `curated` only through the provider's policy. Examples include accepted decisions, verified bug-fix lessons, current project status, accepted handoffs, and current source-of-truth summaries.

Keep these as `candidate` or `review` unless confirmed by the user, a configured memory owner, or an explicit project policy:

- heuristic or summary-only findings;
- history-derived lessons from old threads;
- user preferences;
- model/reasoning/workflow policy;
- cross-project or global rules;
- tool/skill/script records;
- stale, conflict, or low-confidence results;
- executable, install, archive, compact, restore, security, privacy, credential, spending, or destructive-action recommendations.

History providers may supply provenance and receipts, but they do not own project memory promotion.
## Memory Classification Priority

For default project continuation, bootstrap, and dispatch, prioritize current product/project memory:

1. product/project status;
2. accepted decisions;
3. active blockers;
4. current module progress;
5. canonical docs/source refs.

Do not let these categories dominate default project context unless the queryType is archive, performance, runtime diagnosis, thread recovery, old-thread continuity, or history audit:

- thread archive records;
- one-click slimming/debt-reduction records;
- history-provider audit records;
- worker task prompts;
- old thread maintenance logs;
- raw session or restore metadata.

These lower-priority records can be returned as warnings or provenance, but they should not outweigh current product state for ordinary development.

Cooling policy:

- Hot: recent same-thread continuity and open work; may be retrieved by default for that slimmed thread.
- Warm: older same-project or keyword-relevant summaries, decisions, handoffs, bugs, and experience cards; query-bounded.
- Cold/raw: archival evidence or raw provenance; not read by default.

Do not accept old-thread optimization that only shrinks the session body. Before selected-thread compaction, the full old-thread history must be captured into a Thread History Vault or equivalent source-backed archive with provenance and recall pointers.
