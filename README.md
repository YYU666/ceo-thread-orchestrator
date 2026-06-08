# CEO Thread Orchestrator

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/YYU666/ceo-thread-orchestrator)](https://github.com/YYU666/ceo-thread-orchestrator/releases)
[![GitHub stars](https://img.shields.io/github/stars/YYU666/ceo-thread-orchestrator?style=social)](https://github.com/YYU666/ceo-thread-orchestrator/stargazers)

Turn Codex from a single coding thread into a CEO-led project workspace.

CEO Thread Orchestrator is an experimental Codex plugin/skill that helps one high-reasoning CEO thread coordinate specialist implementation, review, QA, product, market, and knowledge lanes. It is built for the new Codex app world where threads, worktrees, automations, skills, and local knowledge bases can work together, but only if someone keeps the goal, memory, and evidence straight.

## Why This Exists

As Codex gains thread coordination and richer local tooling, complex projects can fail in new ways:

- one thread silently becomes an all-purpose worker;
- new threads are created too eagerly and lose context;
- old specialist threads are not reused;
- worker reports are accepted without evidence;
- follow-up requirements create scattered task cards instead of one updated goal;
- project memory stays trapped in chat history.

This skill gives Codex an operating model for those problems: one CEO brain, reusable expert lanes, explicit memory packets, evidence-based acceptance, and a goal loop that continues until work is accepted, blocked, or superseded.

## Quick Start

Install this repository as a Codex plugin if your Codex environment supports plugin installation from local or GitHub repositories. If you only use raw skills, copy `skills/ceo-thread-orchestrator/` into your Codex skills directory.

Then start a fresh Codex thread and try:

```text
Use CEO Thread Orchestrator to manage this project goal until it is accepted, blocked, or superseded. Draft the smallest useful goal brief, create the next executable task card, and report the active goal status and next action. Do not stop at a team plan.
```

For safer first tests, use the smoke prompts in [examples/smoke-prompts.md](examples/smoke-prompts.md).

## What It Does

- Keeps the current Codex thread as the high-reasoning CEO lane.
- Creates the smallest useful execution artifact: task card, goal brief, or PRD/design brief.
- Maintains a goal ledger with done criteria, task graph, active owner, evidence, next action, and closure state.
- Routes implementation, review, QA, product, market, and knowledge work to specialist lanes when tools allow it.
- Reuses existing specialist threads before creating new ones.
- Dynamically adjusts thread count when task size or requirements change.
- Bootstraps new or reused threads with compact memory packets.
- Uses Zhixia/local-doc knowledge exports through `.codex-knowledge/` when available.
- Requires evidence before acceptance: diffs, tests, screenshots, reports, or other artifacts depending on task risk.
- Keeps thread creation, subagents, worktrees, automations, and spending-heavy model lanes behind tool-contract and user-authorization boundaries.

## Before And After

Without this skill:

```text
User: Go ahead.
Codex: I will directly edit the UI in this thread.
```

With this skill:

```text
Operating mode: route to existing implementation lane.
Goal status: dispatched.
Done criteria: UI renders correctly, tests pass, screenshot checked.
Next action: worker implements within the write-set, CEO reviews evidence, then accepts or requests revision.
```

## Operating Model

The CEO lane owns:

- scope and product judgment;
- architecture tradeoffs;
- task graph and staffing;
- memory routing;
- cross-thread relay;
- model/cost policy;
- review and acceptance decisions;
- concise user reporting.

Specialist lanes own bounded work:

- implementation;
- independent review and QA;
- UI/UX critique;
- market or competitor research;
- knowledge, memory, and documentation cleanup.

The CEO should not become a permanent all-purpose implementer. Direct CEO coding is reserved for tiny tasks, docs/skill/memory edits, explicit direct-current-thread requests, or emergency unblocks.

## Goal Completion Loop

The skill does not stop at "here is a team plan." For open goals, the CEO maintains:

```text
Goal ID:
User outcome:
Status: intake | planned | dispatched | executing | review | revise | accepted | blocked | superseded
Done criteria:
Task graph:
Active lanes / thread ids:
Current owner:
Last evidence:
Next action:
Stop / heartbeat condition:
Memory updates needed:
```

Each CEO turn should advance the goal by clarifying done criteria, dispatching work, checking evidence, requesting revision, accepting, blocking, superseding, or updating durable memory.

## Optional Integrations

This skill degrades gracefully. It can use these capabilities when available, but does not require all of them:

- Codex app thread tools such as list/read/send/create/fork/handoff.
- Codex worktrees for isolated parallel work.
- Subagents for explicitly authorized bounded delegation.
- Automations or heartbeats for follow-up monitoring.
- Project-defined task pools, external worker systems, or routing scripts.
- Zhixia/local-doc knowledge exports through `.codex-knowledge/`.

## Repository Structure

```text
ceo-thread-orchestrator/
├── .codex-plugin/plugin.json
├── skills/
│   └── ceo-thread-orchestrator/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       └── references/
├── examples/
└── docs/
```

## Documentation

- [English introduction](docs/INTRODUCTION.md)
- [中文介绍](docs/INTRODUCTION.zh-CN.md)
- [Smoke prompts](examples/smoke-prompts.md)
- [Open-source readiness checklist](skills/ceo-thread-orchestrator/references/open-source-readiness.md)

## Safety Model

The skill treats new threads as capacity decisions, not a reflex. For ordinary coding, it prefers one reusable implementation lane. It adds another code lane only when work can run in parallel, has a distinct write-set, and can be verified independently.

Worker reports are evidence, not proof. The CEO lane still inspects meaningful artifacts before accepting work.

After installing or updating the plugin, restart or refresh Codex if old threads appear to use stale behavior. Existing long-running threads may still carry older context, so start a fresh CEO thread for the most reliable test.

## Validation

For local development, validate the packaged skill:

```powershell
python <path-to-skill-creator>/scripts/quick_validate.py .\skills\ceo-thread-orchestrator
```

If you have the Codex plugin validator available, also validate the plugin root:

```powershell
python <path-to-plugin-creator>/scripts/validate_plugin.py .
```

## Contributing

Issues and pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes.

Useful contributions include:

- real-world smoke test reports;
- clearer task-card or goal-loop behavior;
- safer thread/review routing patterns;
- memory-provider integration notes;
- examples for Codex projects with different tool surfaces.

## Status

This is an experimental community plugin. Codex thread tooling, model routing, worktrees, subagents, and automation support may differ by host and version. The skill always follows the active tool contract when it is stricter than the written workflow.

## License

MIT. See [LICENSE](LICENSE).
