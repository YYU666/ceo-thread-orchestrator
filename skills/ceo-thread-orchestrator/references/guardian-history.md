# History Provider Reference

Use this optional history-provider reference when CEO Flow needs old Codex thread history, Thread History Vault/source-backed archive evidence, selected-thread compaction safety, restore dry-runs, raw-session snippets, freshness labels, or broken/stale old-thread recovery.

History providers supply provenance and recoverability evidence. They are not owners of current project memory, and they do not authorize automatic cleanup, restore, compaction, deletion, movement, or raw session mutation. Provider-specific tools are optional local implementations and are unavailable unless the local deployment explicitly supplies them.

## Old-Thread Continuity

If the user wants to keep using an old thread, do not default to pushing them into a new thread. First check whether a memory runtime or history provider has a history card, compact receipt, memory pointer, or source refs for that `threadId`, project path, or query.

Slimmed-thread retrieval order:

1. newest request;
2. thread memory pointer or compact receipt;
3. hot memory for the same `threadId`;
4. warm summaries by project path or task keywords;
5. canonical docs/source files;
6. history-provider evidence refs;
7. cold/raw history only under the hard gate.

For broken, stalled, missing, overlong, archived, slimmed, or stale-lane recovery, first run or prepare `retrieve_context(queryType=thread_recovery)` and generate/update a `ThreadRecoveryPacket`. History-provider/vault sourceRefs may follow only as evidence pointers. Do not copy old chat into a new CEO/worker thread.

## History Provider Workflow

Use a history provider only as source-backed history and restore-evidence provider. It is not the owner of project memory.

Allowed default roles:

- health/context pressure;
- compact old-thread evidence;
- old-thread lookup;
- paused task discovery;
- explicit selected-thread compaction receipts;
- restore dry-runs;
- raw-session gate provenance.

Default history-provider use is read-only. Local deployments may expose JSON files or commands for report, search-history, thread-context, project-history, export, and restore dry-run. Use only the commands actually implemented by that provider.

Never run cleanup, prune, actual restore, deletion, movement, or raw JSONL mutation from CEO Flow unless the user explicitly approved that exact operation in the current task. Cleanup/prune operations are manual maintenance commands and must not run while Codex is active unless explicitly authorized and safe.

## Compact Session Safety

Selected-thread compaction is never automatic. It is allowed only for explicit selected-thread optimization with a clear `ThreadId`, and only under the backup/hash/temp-write/replace/receipt safety contract:

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
2. compact memory/history summaries are missing, stale, contradicted, or insufficient;
3. CEO states a narrow token budget;
4. CEO states source range;
5. CEO states provenance plan.

Use history-provider summary/index evidence and restore dry-run before raw snippets. Summaries are retrieval aids, not replacements for source/provenance.

## Freshness Labels

- `current`: under 7 days with consistent source refs.
- `review`: 7-30 days or summary-only.
- `stale`: over 30 days or predating important changes.
- `unknown`: missing timestamp, hash, or provenance.
- `conflict`: disagreement between index, summary, timestamp, hash, canonical source, or worker evidence.
