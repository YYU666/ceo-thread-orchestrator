# CEO Thread Orchestrator

CEO Thread Orchestrator is a community Codex plugin that packages a project-management skill for running Codex as a CEO/PM/architect instead of a single all-purpose worker.

The skill helps Codex coordinate specialist lanes, reuse thread context, bootstrap memory, route work to reviewers, and decide when new threads are actually worth the coordination cost. It also keeps an active goal loop so orchestration continues toward accepted, blocked, or superseded outcomes instead of stopping at a team plan.

## Introduction

- [English introduction](docs/INTRODUCTION.md)
- [中文介绍](docs/INTRODUCTION.zh-CN.md)

## What It Does

- Keeps the current Codex thread as the high-reasoning CEO lane.
- Routes implementation, review, QA, product, market, and knowledge work to specialist lanes when tools allow it.
- Reuses existing specialist threads before creating new ones.
- Dynamically adjusts thread count when task size or requirements change.
- Maintains goal briefs, task graphs, and next actions so work can keep moving until accepted, blocked, or superseded.
- Treats memory as explicit project infrastructure, with optional Zhixia/local-doc knowledge retrieval when available.
- Requires evidence before acceptance: diffs, tests, screenshots, reports, or other artifacts depending on task risk.
- Keeps thread creation, subagents, worktrees, automations, and spending-heavy model lanes behind tool-contract and user-authorization boundaries.

## Install

This repository is structured as a Codex plugin:

```text
ceo-thread-orchestrator/
├── .codex-plugin/plugin.json
└── skills/
    └── ceo-thread-orchestrator/
        ├── SKILL.md
        ├── agents/openai.yaml
        └── references/
```

Repository: <https://github.com/YYU666/ceo-thread-orchestrator>

If your Codex environment supports plugin installation from local or GitHub repositories, install this repository as a plugin. If you only use raw skills, copy `skills/ceo-thread-orchestrator/` into your Codex skills directory.

## Example Prompts

```text
Use CEO Thread Orchestrator to manage this project as CEO/PM.
```

```text
We have a feature request and two bug reports. Build a team plan, reuse existing threads if possible, and only create new lanes if the write-sets can run in parallel.
```

```text
Review the current team structure, memory plan, and decision ledger. Tell me whether this project needs fewer or more specialist threads.
```

More smoke prompts are in `examples/smoke-prompts.md`.

## Optional Integrations

This skill is designed to degrade gracefully. It can use these capabilities when available, but does not require all of them:

- Codex app thread tools such as list/read/send/create/fork/handoff.
- Codex worktrees for isolated parallel work.
- Subagents for explicitly authorized bounded delegation.
- Automations or heartbeats for follow-up monitoring.
- Project-defined task pools, external worker systems, or routing scripts when a project already defines them.
- Zhixia/local-doc knowledge exports through `.codex-knowledge/`.

## Safety Model

The skill treats new threads as capacity decisions, not a reflex. For ordinary coding, it prefers one reusable implementation lane. It adds another code lane only when work can run in parallel, has a distinct write-set, and can be verified independently.

Worker reports are evidence, not proof. The CEO lane still inspects meaningful artifacts before accepting work.

The CEO lane should not silently fall back into app-code implementation just because the user says "continue" or "go ahead". Those follow-ups mean "continue the current orchestration mode". Direct CEO implementation should be announced as a fallback and used only when the user explicitly asks for current-thread execution, the work is non-app-code, or no routing path is available.

After installing or updating the plugin, restart or refresh Codex if old threads appear to use stale behavior. Existing long-running threads may still carry older context, so start a fresh CEO thread for the most reliable test.

## Validation

For local development, validate the packaged skill with your Codex skill validator:

```powershell
python <path-to-skill-creator>/scripts/quick_validate.py .\skills\ceo-thread-orchestrator
```

If you have the Codex plugin validator available, also validate the plugin root:

```powershell
python <path-to-plugin-creator>/scripts/validate_plugin.py .
```

## License

MIT. See `LICENSE`.

## Status

This is an experimental community plugin. Codex thread tooling, model routing, worktrees, subagents, and automation support may differ by host and version. The skill always follows the active tool contract when it is stricter than the written workflow.
