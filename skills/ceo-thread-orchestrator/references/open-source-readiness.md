# Open Source Readiness

Use this reference only when preparing `ceo-thread-orchestrator` for public distribution.

## Release Modes

- Raw skill catalog: publish the skill folder with `SKILL.md`, `agents/openai.yaml`, optional `references/`, and a per-skill `LICENSE.txt` if the target catalog expects one.
- Codex plugin: package the skill inside a plugin with `.codex-plugin/plugin.json`, then validate the plugin manifest before sharing.
- Internal-only: keep private paths, workflow policy, and memory-provider assumptions in local project docs rather than the public skill.

## Public Release Checklist

- Remove private project names, local absolute paths, private model ids, personal workflow names, secrets, and private repository references.
- Keep Zhixia optional. Do not publish `.codex-knowledge/`, user memory files, thread ids, worktree ids, completion ledgers, or private worker reports.
- State capability boundaries plainly: thread tools, model overrides, automations, subagents, worktrees, OpenClaw/AutoFlow, and knowledge providers are optional and tool-contract dependent.
- Require explicit authorization for new persistent threads, automations, subagents, spending-heavy model lanes, and worktree creation when the active tool contract requires it.
- Include public examples that show CEO-only, one code lane, code plus review, and dynamic rebalancing after a mid-task requirement change.
- Provide a compatibility note for Codex app, Codex CLI, and other Agent Skills hosts. Mark any Codex-app-only behavior such as thread read/send/create/handoff.
- Validate the skill with `quick_validate.py` before each release.
- Forward-test with read-only prompts first. Do not let tests create live threads, automations, or external workflow tasks unless the test explicitly authorizes that behavior.
- Add repo-level release materials outside the skill folder: README, license selection, contribution rules, install instructions, examples, security/reporting contact, and changelog.
- Prefer a small eval suite or scripted smoke prompts that check triggering, authorization boundaries, memory bootstrap, dynamic lane scaling, and clear-status report parsing.

## Ready Criteria

The skill is release-ready when a fresh Codex instance can install it, understand when to trigger it from metadata, use it without private context, avoid unsafe thread creation, route memory through optional providers, and explain its remaining limitations without relying on the original author.
