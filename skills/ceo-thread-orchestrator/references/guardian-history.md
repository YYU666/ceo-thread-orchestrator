# Guardian History Reference

Use this reference when CEO Flow needs old Codex thread history, Thread History Vault/source-backed archive evidence, selected-thread compaction safety, restore dry-runs, raw-session snippets, freshness labels, or broken/stale old-thread recovery.

Guardian or equivalent history providers supply provenance and recoverability evidence. They are not the owner of current project memory, and they do not authorize automatic cleanup, restore, compaction, deletion, movement, or raw session mutation.

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

For broken, stalled, missing, overlong, archived, slimmed, or stale-lane recovery, first run or prepare `retrieve_context(queryType=thread_recovery)` and generate/update a `ThreadRecoveryPacket`. Guardian/vault sourceRefs may follow only as evidence pointers. Do not copy old chat into a new CEO/worker thread.
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
