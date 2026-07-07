# CEO Flow Guardian Implementation Tasks

> **Status note (2026-07-07):** This is a historical optional-integration document for one local Memory Runtime / History Provider stack. It is not required for public CEO Flow usage, and referenced provider source files or commands may not exist in this repository. The public contract is now summarized in `docs/optional-integrations/MEMORY_AND_HISTORY_PROVIDERS.md`; provider-specific commands must be treated as unavailable unless the local deployment explicitly supplies them.


## Goal

Implement the accepted CEO Flow, Zhixia local docs, and Codex History Guardian integration contract with a narrow first wave.

## Scope

- Update CEO Flow rules so task cards and memory bootstrap use the five knowledge provider modes.
- Update the installed `zhixia-local-docs` skill so Guardian history is treated as source-backed history evidence, not canonical project truth.
- Add Guardian JSON output and read-only agent commands for history search and compact thread/project context.
- Keep `write-memory-candidate` out of the Guardian MVP implementation.
- Keep restore as dry-run by default.

## Task Graph

```text
T1: CEO Flow skill contract update
Owner: CEO/direct skill editor
Write-set: CEO Flow repo SKILL.md, README, smoke prompts, changelog
Acceptance: task card rules include Knowledge provider mode, Context / history budget, Guardian usage, Zhixia retrieval, Memory writeback target, Restore policy.

T2: zhixia-local-docs installed skill update
Owner: CEO/direct skill editor
Write-set: installed zhixia-local-docs SKILL.md
Acceptance: Guardian history is retrieval evidence only; memory candidates belong to Zhixia/CEO memory provider.

T3: Guardian CLI MVP
Owner: CEO/direct tool editor
Write-set: codex-history-guardian.ps1
Acceptance: -Json works for existing commands; search-history, get-thread-context, and get-project-history return guardian.agent.v1 JSON without broad raw-session reads.

T4: Verification
Owner: neutral review gate
Acceptance: skill validators pass, Guardian JSON command smoke passes, privacy scan passes, installed CEO Flow skill is synced.
```

## Non-Goals

- No automatic `clean-logs`.
- No automatic `prune-process-manager`.
- No actual restore without explicit user approval.
- No raw session snippet reads in the agent-facing commands.
- No Guardian-owned memory promotion.
