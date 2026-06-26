# Context And Memory Reference

Use this reference when a task involves Zhixia, Codex History Guardian, `.codex-knowledge/`, old-thread continuity, context slimming, restore, raw sessions, memory bootstrap, or memory writeback.

## Runtime Context Governor

CEO Flow keeps active threads lean, source-backed, and recoverable. It is not a Windows Task Scheduler, automatic log cleaner, automatic process-manager pruner, or background cleanup service.

At bootstrap, dispatch, reuse, review, harvest, and writeback:

- use newest goal, bounded task card, allowed write-set, verification commands, relevant source refs, compact knowledge excerpts, and short history budget;
- do not copy full CEO conversations into worker prompts;
- do not send full `.codex-knowledge/` or long generated knowledge files by default;
- do not read raw sessions or long chat transcripts by default;
- do not treat old threads as free context;
- prefer compact retrieval and source-backed packets over stacking instructions in long threads.

When a CEO/project-main thread is broken or context-exhausted, recover through a compact `ThreadRecoveryPacket`, not by forking or copying the old chat.

Recommended takeover read order:

1. ThreadRecoveryPacket;
2. Program Goal Brief and Completion Dashboard;
3. compact project memory / Memory Runtime `retrieve_context(queryType=project_resume)`;
4. active lane roster and latest callbacks;
5. canonical project docs/source files;
6. Zhixia/Guardian/vault sourceRefs;
7. cold/raw session evidence only through the raw-session gate.

## Knowledge Provider Modes

- `none`: no durable provider; use newest request, local source files, task cards, reports, and verification.
- `project-memory`: canonical local memory docs, decision logs, handoff logs, and bug memory.
- `zhixia-local-docs`: `.codex-knowledge/` and Zhixia compact project knowledge.
- `guardian-history`: Guardian inventory/exported notes for old Codex threads, paused tasks, evidence, health, and restore dry-runs.
- `hybrid`: Zhixia for current project knowledge and Guardian for old thread history; preferred when both are configured.

Use canonical project files, source code, tests, decision logs, and worker reports as stronger evidence than summaries when they disagree.

## Memory Runtime Lifecycle

A compact project memory provider may expose explicit runtime hooks such as `retrieve_context(task_goal)`, `retrieve_precedent(task_type)`, `writeback_evidence(result)`, and `promote_memory(candidate)`. Zhixia is one provider; another project may supply an equivalent local memory runtime.

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

Every provider result used in a task card or review should expose compact `items[]` with source/provenance fields when available:

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
Retrieved source refs:
Memory packet:
  compact excerpts:
  constraints:
  warnings:
Writeback target:
Promotion boundary:
```

Default token budgets should stay small:

- task dispatch: about 800-1500 tokens;
- project resume: about 1500-3000 tokens;
- review gate: enough for task card, evidence refs, and only relevant memory;
- thread recovery: explicit higher budget only when the hard gate is satisfied.

Do not increase retrieval limits merely to be complete. Stop when high-quality source-backed context is sufficient.

## Zhixia Workflow

When `.codex-knowledge/` exists, treat the workspace as Zhixia-enabled. Look for `project-knowledge.md`, `context.md`, `knowledge-items.md`, `experience-cards.md`, and `skill-candidates.md`.

Retrieval:

- Prefer compact query/excerpts over reading the whole knowledge base.
- Use query terms from task goal, files, feature names, bugs, decisions, and project path.
- Increase retrieval limits only when the lane truly needs broader memory.

Writeback:

- Workers report memory update candidates.
- CEO or active memory provider decides whether the result becomes a Decision, Handoff, Bug/Experience card, or KnowledgeItem.
- Do not edit `.codex-knowledge/` directly unless the user explicitly asks.
- Prefer durable updates in canonical markdown/docs that Zhixia can scan.
- When a Memory Runtime exists, call writeback only with compact accepted/revise/block evidence packets, not raw chats or raw session bodies.

Skill candidates from Zhixia are draft material only. Install or modify skills from them only with explicit user approval.

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

Precedents are context and risk signals. They do not expand the task scope, authorize tools, replace current source files, or override CEO accept/revise/block.

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
review decision:
sourceRefs:
freshness:
confidence:
residual risk:
memory candidates:
```

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

Guardian or equivalent history providers may supply provenance and receipts, but they do not own project memory promotion.

## Old-Thread Continuity

If the user wants to keep using an old thread, do not default to persuading them into a new thread. First check whether Zhixia/Guardian has a history card, compact receipt, memory pointer, or source refs for that `threadId`, project path, or query.

Slimmed-thread retrieval order:

1. newest request;
2. thread memory pointer or compact receipt;
3. Zhixia hot layer for same `threadId`;
4. warm summaries by project path or task keywords;
5. canonical docs/source files;
6. Guardian evidence refs;
7. cold/raw history only under the hard gate.

Cooling policy:

- Hot: recent same-thread continuity and open work; may be retrieved by default for that slimmed thread.
- Warm: older same-project or keyword-relevant summaries, decisions, handoffs, bugs, and experience cards; query-bounded.
- Cold/raw: archival evidence or raw provenance; not read by default.

Do not accept old-thread optimization that only shrinks the session body. Before selected-thread compaction, the full old-thread history must be captured into Zhixia Thread History Vault or an equivalent source-backed archive with provenance and recall pointers.

## Guardian Workflow

Use Guardian only as source-backed history and restore-evidence provider. It is not the owner of project memory.

Allowed default roles:

- health/context pressure;
- compact old-thread evidence;
- old-thread lookup;
- paused task discovery;
- explicit selected-thread compaction receipts;
- restore dry-runs;
- raw-session gate provenance.

Default Guardian use is read-only. Current/fallback evidence may come from `health-latest.json`, `inventory.json`, `restore-index.json`, and exported Zhixia history indexes. Agent CLI may include `report -Json`, `search-history -Json`, `get-thread-context -Json`, `get-project-history -Json`, `export-zhixia -Json`, and `restore -DryRun -Json` only when the local deployment supports them.

Never run `clean-logs`, `prune-process-manager`, actual restore, deletion, movement, or raw JSONL mutation from CEO Flow unless the user explicitly approved that exact operation in the current task. `clean-logs` and `prune-process-manager` are manual maintenance commands and must not run while Codex is active.

## Compact Session Safety

`compact-session` is never automatic. It is allowed only for explicit selected-thread optimization with a clear `ThreadId`, and only under the backup/hash/temp-write/replace/receipt safety contract:

- full backup;
- backup SHA-256 equals original SHA-256;
- temp write;
- replacement;
- receipt with before/backup/after hashes;
- byte counts;
- backup path;
- restore hint;
- memory pointers or source refs back to captured history.

"Reopen the same thread" means Codex rereads the slimmed session body for that same thread. It is not the same as creating a new thread.

Recommend a fresh thread only when hot memory remains unavailable, the session is corrupted, compaction is unavailable, permissions are missing, or the user chooses a reset.

## Raw Session Gate

Raw session snippets are allowed only when all are true:

1. the user explicitly asks to recover old thread context or old details;
2. compact Zhixia/Guardian summaries are missing, stale, contradicted, or insufficient;
3. CEO states a narrow token budget;
4. CEO states source range;
5. CEO states provenance plan.

Use Guardian summary/index evidence and restore dry-run before raw snippets. Summaries are retrieval aids, not replacements for source/provenance.

## Freshness Labels

- `current`: under 7 days with consistent source refs.
- `review`: 7-30 days or summary-only.
- `stale`: over 30 days or predating important changes.
- `unknown`: missing timestamp, hash, or provenance.
- `conflict`: disagreement between index, summary, timestamp, hash, canonical source, or worker evidence.
