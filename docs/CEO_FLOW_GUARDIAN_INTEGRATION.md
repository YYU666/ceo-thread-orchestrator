# CEO Flow Guardian Integration

> **Status note (2026-07-07):** This is a historical optional-integration document for one local Memory Runtime / History Provider stack. It is not required for public CEO Flow usage, and referenced provider source files or commands may not exist in this repository. The public contract is now summarized in `docs/optional-integrations/MEMORY_AND_HISTORY_PROVIDERS.md`; provider-specific commands must be treated as unavailable unless the local deployment explicitly supplies them.


This document defines the formal integration contract between CEO Flow, Zhixia local docs, and Codex History Guardian.

It is a design contract, not an implementation checklist for destructive maintenance. CEO Flow must stay the orchestration layer and runtime context governor. Zhixia remains the local knowledge and document system. Codex History Guardian remains the history evidence, context-pressure, restore-index, and restore dry-run bridge.

This integration is about Codex runtime context governance, not Windows scheduled cleanup. CEO Flow uses Zhixia and Guardian to reduce active context load, avoid long-thread drift, and keep historical claims source-backed. It must not turn Guardian into an automatic log cleaner, task scheduler, or process-manager pruning service.

## Goals

- Let CEO Flow use Zhixia and Guardian without reading broad raw history.
- Reduce repeated context copying across worker threads.
- Keep Codex runtime packets short: task card, compact Zhixia context, relevant source refs, and narrow Guardian evidence.
- Detect context pressure from health/history evidence and route work through compact retrieval, old-thread in-place optimization, or compact handoffs instead of extending overloaded chats.
- Support old-thread continuity when the user explicitly wants to keep using the same thread after optimization.
- Require recallable old-thread history before slimming: a selected-thread compaction must not discard continuity by compressing the session body without first preserving source-backed history in Zhixia or an equivalent memory provider.
- Support paused-task recovery through source-backed summaries and restore dry-runs.
- Keep long-term memory clean by writing candidates before promotion.
- Preserve raw Codex sessions and source provenance.

## Non-Goals

- CEO Flow must not own Guardian maintenance.
- CEO Flow must not automatically clean logs, prune process state, restore sessions, delete files, move files, or edit raw session JSONL. The only raw-session mutation exception is explicit selected-thread `compact-session` under the backup/hash/temp-write/replace/receipt safety contract.
- CEO Flow must not describe this mechanism as Windows Task Scheduler, automatic log cleanup, automatic process-manager pruning, or background file maintenance.
- Zhixia summaries must not replace canonical source files, tests, diffs, worker evidence, or raw-session provenance.
- Generic knowledge bases must not be treated as if they support Zhixia-specific context slimming.

## Component Responsibilities

### CEO Flow

CEO Flow decides when to query knowledge, how much context to pass, which lane receives it, whether evidence is accepted, and whether memory updates become candidates.

CEO Flow owns:

- knowledge provider mode classification;
- task cards and memory packets;
- context and history budget;
- Runtime Context Governor behavior: short packets, long-thread fuse decisions, compact handoffs, and review/writeback context slimming;
- dispatch, harvest, review, accept, revise, block, and supersede decisions;
- neutral high-reasoning review gates;
- memory writeback candidate creation.

### Zhixia Local Docs

Zhixia local docs own current project knowledge and generated documents.

Zhixia local docs provide:

- `.codex-knowledge/project-knowledge.md`;
- `.codex-knowledge/context.md`;
- `.codex-knowledge/knowledge-items.md`;
- `.codex-knowledge/experience-cards.md`;
- source manifests and citations;
- stable Markdown documents that can be scanned back into the knowledge base.

### Codex History Guardian

Guardian owns Codex history inventory and restore evidence.

Guardian provides:

- health reports;
- context-pressure signals for CEO Flow to reduce active history load;
- session inventory;
- restore index;
- exported Zhixia history notes;
- paused-task and old-thread evidence through inventory/exported notes;
- agent-friendly search and thread-context summaries;
- restore dry-runs;
- maintenance commands that remain manual unless explicitly authorized.

Guardian does not own runtime orchestration, durable project memory, Windows scheduling, automatic cleanup, or process-manager repair. `clean-logs` and `prune-process-manager` remain manual maintenance commands and are outside default CEO Flow execution.

## Runtime Context Governance

CEO Flow should treat Zhixia and Guardian as a runtime context control layer.

Default context packet:

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

- full CEO chat history;
- full implementation thread transcript;
- full `.codex-knowledge/` contents;
- broad raw session scans;
- old chat transcripts as default task context;
- maintenance commands such as `clean-logs` or `prune-process-manager`.

Context-pressure fuse:

- If Guardian health/context pressure is `yellow` or `red`, CEO Flow should reduce history, use compact Zhixia/Guardian retrieval, write or update a compact handoff when useful, or follow an explicitly approved old-thread optimization path. It must not run maintenance commands automatically.
- If the active CEO or worker thread is too long, stalled, or context-fragmented, CEO Flow should reduce history and split a compact task packet first. If the user permits optimizing the old thread, CEO Flow should recommend Zhixia ingestion plus selected-thread `compact-session` before pushing a new thread.
- If an old thread is considered for reuse, CEO Flow must check relevance, freshness, role, workspace, write-set, and context risk before reusing it.
- If raw-session recovery is requested, CEO Flow must pass the raw-session hard gate before reading snippets.

This fuse reduces Codex runtime load. It does not trigger Windows cleanup.

### Three Runtime Paths

CEO Flow must distinguish these paths:

| Path | Use When | Default Context | Mutation Policy |
|---|---|---|---|
| Old-thread in-place compaction | User wants to keep using a selected old thread and allows optimization | Short task packet, Zhixia compact context, Guardian history card, compact receipt | Allowed only for explicit selected `ThreadId` with backup/hash/temp-write/receipt safety |
| Zhixia history retrieval | Continuing work after compaction, bootstrapping context, or recovering project history | Zhixia history card, compact excerpts, Guardian `get-thread-context`, source refs | Read-only |
| Fresh-thread handoff | Hot memory cannot release, session is corrupted, permissions are missing, or user chooses a clean start | Compact handoff document plus source refs | Creates or reuses a cleaner lane only when authorized |

"Reopen the same thread" means Codex rereads the slimmed session body for the same thread. It is not a new-thread handoff.

### Old-Thread Memory Layers

When Zhixia or another configured provider supports old-thread memory, CEO Flow treats it as the recall layer for slimmed threads.

Before selected-thread compaction:

- full old-thread history must be captured into a Thread History Vault or equivalent source-backed archive;
- captured history must keep provenance and source refs;
- the compact receipt or slimmed thread context must include memory pointers or lookup refs back to the captured history;
- CEO Flow must block or revise a result that only reports a smaller session body without usable recall evidence.

Default retrieval order when continuing a slimmed old thread:

1. newest user request;
2. thread memory pointer or compact receipt;
3. Zhixia hot layer for the same `threadId`;
4. warm summaries by project path or task keywords;
5. canonical project docs and current source files;
6. Guardian evidence refs or restore dry-run metadata when relevant;
7. cold/raw history only under the hard gate.

Cooling policy:

- `hot`: recent same-`threadId` continuity, active task state, open blockers, accepted PRD/task graph, and latest implementation/review status. It may be retrieved by default for the same slimmed thread.
- `warm`: older same-project or keyword-relevant summaries, decisions, handoffs, bug memories, and experience cards. Retrieve it only with a bounded project/query match.
- `cold`: archived full history, raw session provenance, and restore evidence. Do not read it by default.

Raw session snippets remain behind the hard gate: explicit old-detail recovery request, compact summaries insufficient, narrow token budget, source range, and provenance plan.

## Knowledge Provider Modes

CEO Flow should classify the mode before memory-sensitive orchestration.

```text
none
project-memory
zhixia-local-docs
guardian-history
hybrid
```

### `none`

No durable knowledge provider is available.

CEO Flow uses only:

- the newest user request;
- local source files required for the task;
- task cards;
- worker reports;
- verification evidence.

### `project-memory`

The project has canonical local memory documents, but no Zhixia or Guardian integration is available.

Examples:

```text
docs/PROJECT_MEMORY.md
docs/DECISION_LOG.md
docs/BUG_FIX_MEMORY.md
docs/HANDOFF.md
```

### `zhixia-local-docs`

The project has Zhixia or `.codex-knowledge/`.

CEO Flow may use:

- summary-first retrieval;
- compact context bundles;
- knowledge items;
- experience cards;
- Zhixia-scannable generated documents.

### `guardian-history`

Guardian inventory and restore index are available.

CEO Flow may use Guardian for:

- old Codex thread lookup;
- paused task discovery;
- historical evidence;
- restore dry-runs;
- health summaries.

Guardian history is not automatically canonical project truth.

### `hybrid`

Both Zhixia local docs and Guardian history are available.

This is the preferred enhanced mode:

- current project knowledge comes from Zhixia local docs;
- old thread and paused task history comes from Guardian;
- durable updates go through memory candidates before promotion.

Recommended retrieval order:

1. newest user request;
2. canonical project memory files;
3. Zhixia compact context;
4. Guardian history search results;
5. raw source files only when compact sources are missing, stale, contradicted, or insufficient.
6. raw session snippets only when the user explicitly asks to recover old thread context, compact summaries are insufficient, and the CEO states a narrow token budget and source range before reading.

## CEO Flow Call Points

### New Thread Memory Bootstrap

Use:

- `zhixia-local-docs` for compact project context;
- Guardian `get-project-history -Json` only when old thread history is relevant or context pressure needs evidence.
- Fallback when the agent CLI is unavailable: read Guardian inventory or exported Zhixia history indexes, then select a small number of relevant items.

Default behavior:

- pass compact task packet, compact excerpts, source paths, freshness, and narrow history budget;
- do not pass raw sessions or full old chat transcripts;
- do not pass full CEO chat history;
- do not pass the full `.codex-knowledge/` directory or long generated knowledge files;
- include a context and history budget in the task card.

### Before Reusing An Old Thread

Use Guardian history search to check whether the thread is relevant, stale, blocked, or pointed at the wrong workspace.

Preferred path: `search-history -Json`. Fallback when the agent CLI is unavailable: read Guardian inventory/exported indexes.

CEO Flow should ask:

- Is the old lane relevant to the current project?
- Is its last evidence recent enough?
- Does it have a usable role and write-set?
- Would using it reduce or increase context risk?
- Is the thread too long or fragmented to reuse safely?

If the user explicitly says they want to keep using the old thread, CEO Flow must not default to arguing for a new thread. It should check, in order:

1. whether Zhixia already has a history card for the thread or project;
2. whether Zhixia or an equivalent provider has captured full old-thread history in a Thread History Vault or source-backed archive;
3. whether Guardian has a compact receipt for the selected `ThreadId`;
4. whether `get-thread-context` or Zhixia hot/warm compact context can recover enough history;
5. whether the user has allowed old-thread optimization for the selected `ThreadId`.

If reuse would increase context risk and old-thread optimization is allowed, route to the Zhixia/Guardian ingest plus `compact-session` path. If optimization is not available or not authorized, write a compact handoff and recommend reopening the same thread after compaction when possible, or a cleaner thread only as a fallback.

### Old-Thread In-Place Compaction

Default Guardian behavior remains read-only. A selected old thread may be modified only when the user explicitly triggers `compact-session` or a Zhixia UI action such as "slim session body" or "slim all visible history" for a clear `ThreadId`.

Required safety contract:

```text
explicit user trigger
selected ThreadId
source-backed old-thread history captured before slimming
memory pointers or lookup refs for hot/warm/cold retrieval
full backup before mutation
backup SHA-256 equals original SHA-256
temp write of compacted session
atomic or safest-available replacement
receipt with before hash, backup hash, after hash, before bytes, backup bytes, after bytes, backup path, restore hint, memory pointers or source refs
```

CEO Flow may request or inspect the receipt. It must not perform the compaction itself unless the current task explicitly authorizes that exact operation and target thread.

After compaction, CEO Flow should continue the same old thread with:

- newest task packet;
- thread memory pointer or compact receipt;
- Zhixia hot layer for the same `ThreadId`;
- warm summaries by project path or task keywords;
- canonical project docs/source when needed;
- Guardian `get-thread-context` for the selected `ThreadId`;
- compact receipt and source refs;
- raw-session gate still closed by default.

Do not treat compressed-away raw content as the working memory. If a missing detail matters, retrieve it through Zhixia/Guardian summaries and source refs first.

CEO Flow must block or revise a selected-thread compaction that cannot show recallable history capture plus hot/warm/cold retrieval evidence. A smaller session file alone is not an acceptable continuity result.

### Paused Task Recovery

Use:

```powershell
powershell -File <guardian-script> inventory
powershell -File <guardian-script> restore -ThreadId "<thread-id>" -DryRun
```

Default behavior:

- search and summarize first;
- run restore dry-run only when raw session recovery may be needed;
- never perform actual restore without explicit user approval.

### Dispatch Task Card

Task cards should include:

```text
Knowledge provider mode:
Context / history budget:
Guardian usage:
Zhixia retrieval:
Memory writeback target:
Restore policy:
```

Example:

```text
Knowledge provider mode: hybrid
Context / history budget:
- Use Zhixia compact summaries first.
- Use Guardian only for relevant paused or old threads.
- Do not read raw sessions unless the user explicitly asks to recover old thread context, summaries are insufficient, and CEO states a narrow token budget and source range.
Guardian usage:
- search-history read-only when the planned CLI exists; otherwise use inventory/exported indexes
- restore dry-run only
Zhixia retrieval:
- include query and top compact excerpts
Memory writeback target:
- memory candidate queue
Restore policy:
- no actual restore without explicit user approval
```

Task cards should not include long chat transcripts, full CEO history, full old thread history, or full knowledge-base dumps. If a worker needs more context, send a smaller follow-up evidence packet with source refs rather than pasting entire conversations.

### Review And Accept Gate

Review gates may consult:

- task card;
- diff and changed files;
- tests and artifacts;
- Zhixia context;
- Guardian source references.

Review gates must:

- start from diff, tests, task card, relevant docs, and compact evidence refs;
- stay neutral and evidence-first;
- use high reasoning when the tool surface allows it;
- inspect provenance before accepting historical claims;
- avoid accepting summaries as proof when source evidence is missing.
- avoid reading the implementation thread's long conversation unless a specific unresolved claim requires it and the CEO states the reason and token budget.

### Memory Writeback

Accepted worker output must not automatically become durable memory.

Default flow:

1. CEO harvests worker result.
2. CEO extracts stable learning.
3. Worker reports memory update candidates only; CEO queues accepted candidates through Zhixia or the active CEO memory provider.
4. Human or project policy confirms promotion.
5. Zhixia scans the accepted document or candidate target.

Durable writeback targets should be explicit: Decision, Handoff, Bug or experience card, or KnowledgeItem. Guardian may provide provenance or a receipt, but it is not the memory owner.

### Historical Evidence Or Restore Dry-Run

Use Guardian only for source-backed historical lookup.

Default restore policy:

```text
restore: dry-run only
actual restore: explicit user approval required
```

## Guardian CLI Contract

Guardian has a local PowerShell CLI plus stable JSON files. The current MVP supports read-only agent JSON commands for report, history search, thread context, project history, export, and restore dry-run. Memory candidate writeback remains planned and belongs to Zhixia or the CEO memory provider.

### Current Implemented Guardian CLI

Current deployments can call the Guardian PowerShell script directly:

```powershell
powershell -File <guardian-script> report
powershell -File <guardian-script> inventory
powershell -File <guardian-script> export-zhixia -SinceDays 90
powershell -File <guardian-script> restore -ThreadId "<thread-id>" -DryRun
powershell -File <guardian-script> clean-logs
powershell -File <guardian-script> prune-process-manager
```

`clean-logs` and `prune-process-manager` are manual maintenance commands. CEO Flow must not run them automatically.

Current stable read targets:

```text
<codex-home>/guardian/health-latest.json
<codex-home>/guardian/inventory.json
<codex-home>/guardian/restore-index.json
<zhixia-root>/Codex History/_indexes/codex-thread-inventory.json
<zhixia-root>/Codex History/_indexes/codex-restore-index.json
```

Use the real local script path only in local deployment notes or task cards. Public docs should use `<guardian-script>`.

### Current Guardian Agent CLI

Current agent-friendly commands:

In the examples below, `guardian` is shorthand for `powershell -File <guardian-script>` until a dedicated wrapper command exists.

```powershell
guardian report -Json
guardian search-history -Query "<query>" -Limit 5 -Json
guardian get-thread-context -ThreadId "<thread-id>" -TokenBudget 1200 -Json
guardian get-project-history -ProjectPath "<project-path>" -Limit 10 -Json
guardian restore -ThreadId "<thread-id>" -DryRun -Json
guardian export-zhixia -SinceDays 90 -Json
```

Safety-gated selected-thread command when the local deployment supports old-thread optimization:

```powershell
guardian compact-session -ThreadId "<thread-id>" -Json
```

This command is not part of default read-only CEO Flow behavior. It may be used only after an explicit user trigger for the selected thread and must return a receipt that proves backup, hash verification, temp write, replacement, and restore hint.

Planned commands:

```powershell
guardian list-paused -ProjectPath "<project-path>" -Limit 20 -Json
guardian write-memory-candidate -InputJson "<candidate.json>" -Json
```

These planned commands are not part of the Guardian MVP unless a local deployment explicitly implements them. CEO Flow task cards and public release notes must not imply `write-memory-candidate` is callable by default.

### Command Semantics

#### `report -Json`

Returns current Guardian health, hot-state size, and warnings.

CEO Flow may use it for read-only preflight. CEO Flow must not call maintenance commands automatically based only on the report.

#### `search-history -Query ... -Limit ... -Json`

Searches Guardian inventory and exported Zhixia history notes.

Must not read broad raw sessions by default.

#### `get-thread-context -ThreadId ... -TokenBudget ... -Json`

Returns one compact thread context with provenance and restore dry-run hint.

Must prefer exported summary and inventory fields over raw session reads.

#### `get-project-history -ProjectPath ... -Limit ... -Json`

Returns relevant project history items grouped by status, recency, and match reason.

Useful for bootstrapping a CEO or implementation lane.

#### Safety-gated: `compact-session -ThreadId ... -Json`

Compacts one selected old thread session in place after the user explicitly requests old-thread optimization.

Must not run from default CEO Flow preflight, task dispatch, review, memory writeback, health checks, or unattended cleanup. It is not a replacement for `clean-logs`, not a process-manager prune, and not a scheduled task.

Required output:

```json
{
  "schemaVersion": "guardian.agent.v1",
  "command": "compact-session",
  "mode": "explicit_mutation",
  "threadId": "019e...",
  "status": "completed",
  "requiresHumanConfirmation": false,
  "receipt": {
    "beforeSha256": "...",
    "backupSha256": "...",
    "afterSha256": "...",
    "beforeBytes": 123456,
    "backupBytes": 123456,
    "afterBytes": 34567,
    "backupPath": "<codex-home>/guardian/backups/...",
    "restoreHint": "Use guardian restore or backup copy according to local Guardian docs."
  },
  "sourceRefs": [],
  "provenance": {}
}
```

If any backup or hash check fails, the command must stop before replacing the original session and return `status: "blocked"` or `status: "failed"` with warnings.

#### Planned: `write-memory-candidate -InputJson ... -Json`

Queues a candidate memory update through the active memory provider. Canonical ownership belongs to Zhixia or the CEO memory provider, not Guardian. Guardian may provide a write adapter or receipt when the candidate came from history evidence, but it must not directly modify canonical memory or `.codex-knowledge/`.

#### `restore -ThreadId ... -DryRun -Json`

Returns a restore preview.

Actual restore is outside default CEO Flow permissions.

## JSON Contract

All agent-facing Guardian commands should use this top-level shape:

```json
{
  "schemaVersion": "guardian.agent.v1",
  "command": "search-history",
  "generatedAt": "2026-06-11T12:00:00+08:00",
  "query": "...",
  "mode": "read_only",
  "items": [],
  "warnings": [],
  "provenance": {
    "guardianInventoryPath": "<codex-home>/guardian/inventory.json",
    "guardianRestoreIndexPath": "<codex-home>/guardian/restore-index.json",
    "zhixiaIndexPath": "<zhixia-root>/Codex History/_indexes/codex-thread-inventory.json",
    "sourceGeneratedAt": "..."
  }
}
```

### `items[]`

```json
{
  "threadId": "019e...",
  "title": "Steam login binding fix",
  "summary": "Compact summary, not raw transcript.",
  "status": "paused",
  "freshness": "current",
  "whyMatched": "Matched project root and title.",
  "tokenEstimate": 220,
  "requiresHumanConfirmation": false,
  "restoreCommand": "guardian restore -ThreadId \"019e...\" -DryRun -Json",
  "sourceRefs": [
    {
      "kind": "guardian_inventory",
      "path": "<codex-home>/guardian/inventory.json",
      "sha256": "...",
      "field": "items[12]"
    },
    {
      "kind": "zhixia_summary",
      "path": "<zhixia-root>/Codex History/Projects/example/thread.md",
      "sha256": "...",
      "section": "Guardian Summary"
    },
    {
      "kind": "raw_session",
      "path": "<codex-home>/sessions/.../rollout.jsonl",
      "sha256": "...",
      "readByDefault": false
    }
  ],
  "provenance": {
    "sourceBucket": "hot_sessions",
    "restoreState": "present",
    "lastWriteTime": "...",
    "projectRoot": "..."
  }
}
```

### Freshness Values

```text
current
review
stale
unknown
conflict
```

Meaning:

- `current`: last updated within 7 days and source refs are internally consistent.
- `review`: 7 to 30 days old, or based only on a summary without a recent canonical-source check.
- `stale`: older than 30 days, or known to predate important project changes.
- `unknown`: insufficient timestamp, hash, or provenance evidence.
- `conflict`: inventory, summary, file timestamp, hash, canonical source, or worker evidence disagree.

## Memory Candidate Contract

Canonical owner: Zhixia or the CEO memory provider.

Guardian role: optional adapter for history-derived candidates, provenance capture, and receipts. Guardian must not be the only owner of long-term project memory.

Input:

```json
{
  "candidateType": "decision",
  "projectPath": "<project-path>",
  "title": "...",
  "summary": "...",
  "evidence": [
    {
      "kind": "worker_report",
      "source": "thread id or report path"
    }
  ],
  "sourceRefs": [],
  "confidence": "medium",
  "requiresHumanConfirmation": true,
  "recommendedTarget": "<zhixia-root>/inbox or canonical docs path"
}
```

Output:

```json
{
  "schemaVersion": "guardian.agent.v1",
  "command": "write-memory-candidate",
  "status": "queued",
  "candidateId": "memcand-...",
  "candidatePath": "...",
  "requiresHumanConfirmation": true,
  "message": "Candidate queued. Not promoted to durable memory."
}
```

Candidate types:

```text
decision
bug_memory
handoff
project_memory
experience_card
test_evidence
release_note
```

## Safety Boundaries

CEO Flow may read by default:

```text
<codex-home>/guardian/health-latest.json
<codex-home>/guardian/inventory.json
<codex-home>/guardian/restore-index.json
<zhixia-root>/Codex History/_indexes/*.json
Zhixia exported Markdown summaries
```

CEO Flow must not automatically:

- delete Codex sessions;
- move Codex sessions;
- modify raw session JSONL;
- perform actual restore;
- run `clean-logs`;
- run `prune-process-manager`;
- schedule Windows cleanup;
- treat Guardian health pressure as permission to clean files;
- write directly into `.codex-knowledge/`;
- promote memory candidates into durable memory.

Exception: when the user explicitly triggers old-thread optimization for a selected `ThreadId`, a supported Guardian/Zhixia `compact-session` path may modify that one session body only under the backup/hash/temp-write/replace/receipt contract above. This exception does not permit broad scans, automatic cleanup, `clean-logs`, `prune-process-manager`, or mutation of unrelated sessions.

Guardian commands that imply mutation must return `requiresHumanConfirmation: true` unless the user explicitly approved the operation in the current task.

## Source And Provenance Rules

- Every history item must include `sourceRefs`.
- Raw session paths may be returned as provenance but should not be read by default.
- Summaries are retrieval aids, not proof.
- Conflicts must be reported as `freshness: "conflict"` or equivalent warnings.
- Review gates should inspect provenance when historical evidence affects acceptance.

## Token And History Budget

CEO Flow task cards should include a context budget.

Recommended defaults:

```text
Knowledge provider mode: hybrid
Context / history budget:
- Max 4-8 compact retrieval items for worker dispatch.
- Prefer Zhixia summaries and Guardian indexes.
- Send task packet + compact context + source refs, not full history.
- Avoid raw sessions and old chat transcripts.
- Read raw session snippets only when the user explicitly asks to recover old thread context, compact summaries are insufficient, and CEO states a narrow token budget, source range, and provenance plan.
```

Review gates may request more context, but should state why.

## Files To Update

### Repo Source Files

First phase:

```text
skills/ceo-thread-orchestrator/SKILL.md
skills/zhixia-local-docs/SKILL.md
docs/CEO_FLOW_GUARDIAN_INTEGRATION.md
examples/smoke-prompts.md
```

Second phase:

```text
codex-history-guardian.ps1
```

### Installed Local Skill Files

After repo changes are accepted, sync installed local skills when testing locally:

```text
<codex-home>/skills/ceo-thread-orchestrator/SKILL.md
<codex-home>/skills/zhixia-local-docs/SKILL.md
```

Do not assume repo edits are active in Codex until the installed skill copy is synced or the plugin is reinstalled.

### Public Path Hygiene

Public documentation should use placeholder paths such as:

```text
<codex-home>/guardian/inventory.json
<zhixia-root>/Codex History/_indexes/codex-thread-inventory.json
```

Do not publish machine-specific local paths.

## Task Graph

```text
T1: Add integration design document
Owner: CEO/docs
Output: docs/CEO_FLOW_GUARDIAN_INTEGRATION.md
Acceptance: modes, call points, CLI, JSON contract, safety rules, and MVP criteria are documented.

T2: Update CEO Flow skill rules
Owner: skill editor
Output: SKILL.md, README, smoke prompts
Acceptance: task cards include Knowledge provider mode, Context / history budget, Guardian usage, and restore policy.

T3: Update zhixia-local-docs skill rules
Owner: skill editor
Output: zhixia-local-docs/SKILL.md
Acceptance: Guardian history is treated as source-backed history evidence, not canonical truth.

T4: Implement Guardian agent CLI
Owner: Guardian implementer
Output: codex-history-guardian.ps1
Acceptance: -Json support, search-history, get-thread-context, get-project-history, restore dry-run JSON. Keep write-memory-candidate planned unless explicitly scoped into a later wave.

T5: Smoke tests
Owner: neutral high-reasoning review lane
Acceptance:
- bootstrap uses Zhixia first;
- paused task search returns compact JSON;
- restore remains dry-run;
- memory candidate queues but does not promote;
- generic knowledge base does not enable Guardian-specific slimming.

T6: Release gate
Owner: CEO
Acceptance:
- skill validator passes;
- plugin validator passes;
- privacy scan passes;
- Guardian CLI smoke passes;
- a real code-producing CEO -> implementation -> review -> CEO accept/revise smoke passes;
- public docs contain no private paths.
```

## MVP Acceptance Criteria

- CEO Flow can classify `none`, `project-memory`, `zhixia-local-docs`, `guardian-history`, and `hybrid`.
- In `hybrid` mode, task cards include `Knowledge provider mode` and `Context / history budget`.
- New thread bootstrap uses Zhixia compact context first.
- Guardian history is used only for relevant old threads, paused tasks, restore dry-runs, or historical evidence.
- Guardian `search-history -Json` returns `items[]` with source refs, freshness, match reason, and token estimate.
- Guardian `restore -DryRun -Json` is usable by CEO Flow without actual restore.
- If the user says they do not want a new thread and want the old thread optimized, CEO Flow chooses Zhixia/Guardian history-card plus selected-thread compaction/retrieval path before recommending a fresh thread.
- CEO Flow clearly distinguishes old-thread in-place compaction, Zhixia history retrieval, and fresh-thread handoff.
- Memory writeback creates candidates only.
- Review gates check provenance before accepting historical claims.
- Raw sessions are not read by default.
- Public docs do not leak local private paths.

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| CEO Flow triggers destructive maintenance | Default to read-only and dry-run only |
| Summaries pollute durable memory | Require memory candidate queue and confirmation |
| Zhixia summary is stale | Use freshness, source refs, and canonical files as stronger evidence |
| History search costs too much token or IO | Enforce `Limit`, `TokenBudget`, and summary-first retrieval |
| Private local paths leak into public docs | Use placeholders in public documentation |
| Raw session becomes hidden source of truth | Keep raw sessions as provenance, not default context |
| Review gate over-trusts summaries | Require source refs and neutral high-reasoning review |
| CEO Flow over-corrects into forced new threads | Prefer old-thread compaction and retrieval when the user explicitly asks for old-thread continuity |
| In-place compaction corrupts a session | Require selected ThreadId, full backup, backup hash verification, temp write, replacement receipt, and restore hint |

## CEO Decision

Decision: accept

Reason: the integration keeps responsibility boundaries clear. CEO Flow decides when and how to use context. Zhixia handles current project knowledge and documents. Guardian handles old Codex history and restore evidence. The default path is read-only, summary-first, source-backed, and safe for multi-thread orchestration.
