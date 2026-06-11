# CEO Flow

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/YYU666/ceo-thread-orchestrator)](https://github.com/YYU666/ceo-thread-orchestrator/releases)
[![GitHub stars](https://img.shields.io/github/stars/YYU666/ceo-thread-orchestrator?style=social)](https://github.com/YYU666/ceo-thread-orchestrator/stargazers)

Turn Codex from a single coding thread into a CEO-led project workspace.

CEO Flow is the short public name for the `ceo-thread-orchestrator` Codex plugin/skill. It helps one high-reasoning CEO thread coordinate specialist implementation, review, QA, product, market, and knowledge lanes. When the CEO thread owns a PRD or task graph and the user asks to execute, CEO Flow uses a lightweight Core Team role map to route the work instead of staying in CEO-only planning. It is built for the new Codex app world where threads, worktrees, automations, skills, and local knowledge bases can work together, but only if someone keeps the goal, memory, and evidence straight.

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
Use CEO Flow to manage this project goal until it is accepted, blocked, or superseded. Draft the smallest useful goal brief, create the next executable task card, and report the active goal status and next action. Do not stop at a team plan.
```

For safer first tests, use the smoke prompts in [examples/smoke-prompts.md](examples/smoke-prompts.md).

## What It Does

- Keeps the current Codex thread as the high-reasoning CEO lane.
- Creates the smallest useful execution artifact: task card, goal brief, or PRD/design brief.
- Treats the PRD/design/task-graph thread as the CEO thread by default, then switches to Core Team execution after the plan is accepted.
- Maintains a goal ledger with done criteria, task graph, active owner, evidence, next action, and closure state.
- Runs a CEO harvest loop after dispatch: collect worker results, classify evidence, request revisions, and send the next unblocked task until the project lands.
- Plans unattended-safe command approval profiles before dispatch so routine shell/browser/test prompts do not stall worker lanes mid-run.
- Uses Zhixia-enhanced summary-first context slimming when Zhixia or `.codex-knowledge/` is connected; generic knowledge bases remain retrieval-only.
- Keeps independent review gates neutral and evidence-first, with high reasoning when the tool surface allows it.
- Routes implementation, review, QA, product, market, and knowledge work to specialist lanes when tools allow it.
- Reuses existing specialist threads before creating new ones.
- Dynamically adjusts thread count when task size or requirements change.
- Bootstraps new or reused threads with compact memory packets.
- Maintains a lightweight team roster with role, capability, write policy, trust level, status, and last evidence.
- Captures evidence memory cards before promoting reusable lessons into durable project knowledge.
- Adds code quality gates to prevent broad speculative rewrites, hidden behavior changes, and repeated low-signal patch attempts.
- Detects doom-loop symptoms and prefers rollback, fresh bounded task cards, or independent review over larger speculative diffs.
- Recommends Zhixia/local-doc knowledge exports through `.codex-knowledge/` when available, while allowing projects to specify another local knowledge path.
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

## Default Core Team

CEO Flow has a default company-style role map:

```text
CEO / PM / Architect
Implementation Expert
Review / QA Expert
Product / UX Expert
Knowledge / Memory Expert
Research / Docs Expert
```

Roles are not permanent threads. They become visible specialist lanes only when the task graph needs them, the active Codex tools allow them, and the user or project has authorized execution.

The default PRD path is:

1. The PRD/design/task-graph thread becomes the CEO thread.
2. After the plan is accepted or the user says to execute, CEO leaves CEO-only planning.
3. CEO maps the next execution wave onto the Core Team roles.
4. CEO reuses existing visible expert lanes first.
5. If a needed lane does not exist, CEO creates or requests the smallest useful visible lane with a task card, write-set, verification, and stop condition.
6. CEO harvests worker results on a cadence, reviews evidence, and decides `accept | revise | block | supersede`.
7. CEO sends the next unblocked task or revision until the goal lands or has a real external blocker.

The minimum execution team is usually `CEO + Implementation`. Add `Review/QA` for high-risk or user-facing work, `Product/UX` for meaningful product or interface decisions, and `Knowledge/Memory` only when accepted learning should be written back. Review/QA lanes should stay neutral: they are not there to flatter the user, defend the worker, or keep momentum by blessing weak evidence. When model or thinking controls are available, independent review gates should use high reasoning.

Worker lanes should not ask the user for routine approvals inside an accepted PRD or task graph. They report questions and blockers to the CEO lane. The CEO can approve normal in-scope sequencing, file choices inside the allowed write-set, test selection, and bounded revisions. The user is needed only for out-of-scope changes, credentials, spending beyond the agreed budget, destructive actions, or product/business decisions that change the accepted goal.

## Unattended Execution

Many CEO Flow projects are meant to keep moving while the user is away. Before dispatching an unattended execution wave, the CEO should choose one command approval profile:

- `interactive`: the user is present and can answer routine tool prompts.
- `unattended`: the user is away, so workers must avoid commands likely to trigger interactive approvals.
- `preauthorized`: the needed command families, workspace roots, and verification commands are already approved for this wave.

Implementation task cards should name the allowed command families, such as project-local file reads, scoped edits, package-manager test commands, builds, or browser screenshots. They should also name commands that must not run, such as destructive operations, broad machine inspection, credential access, external-service calls, or absolute-path probes outside the approved workspace.

This does not bypass the Codex host's security UI. If command families are not already allowed, the CEO should resolve that before dispatch by asking once at wave start, choosing safer no-approval commands, reusing a lane with the right permission profile, or holding the wave at the CEO lane until command preauthorization exists. Worker lanes should report blocked commands to the CEO instead of asking the user for routine in-scope approval mid-run.

## Code Quality Gate

For implementation work, the CEO defines a change budget before dispatch:

- intended files or modules;
- architecture, framework, API, and persistence invariants;
- official/current reference docs for unfamiliar APIs;
- behavior that must remain unchanged;
- verification evidence required for acceptance;
- rollback baseline or stop condition when a fix starts spreading.

Workers are expected to inspect local conventions, make focused changes, avoid duplicate logic, tight coupling, magic numbers, weak names, and speculative rewrites, preserve contracts and failure paths, run available static checks, and report root cause plus verification. Repeated failed fixes should trigger re-analysis, rollback planning, or review/debug routing instead of larger patches.

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

After dispatch, the CEO should keep collecting results. A completed worker report is not the end of management; it is the next harvest point. The CEO reads the evidence, updates the task graph, and either accepts, requests revision, routes review, or sends the next task.

## Team Roster And Evidence Cards

CEO Flow borrows the useful parts of larger agent-team systems without requiring an automatic workflow. A project may keep a small roster of reusable lanes:

```text
Lane ID:
Role:
Capabilities:
Write policy:
Trust level:
Current status:
Last evidence:
```

It may also keep evidence memory cards for reusable lessons:

```text
Lesson:
Applies to:
Do not apply to:
Evidence:
Tests or artifacts:
Confidence:
Status:
```

These records are advisory. They help the CEO reuse the right lane and remember proven patterns, but they do not create background workers, automatic queues, autoscaling, or supervisor loops by themselves.

## Optional Integrations

This skill degrades gracefully. It can use these capabilities when available, but does not require all of them:

- Codex app thread tools such as list/read/send/create/fork/handoff.
- Codex worktrees for isolated parallel work.
- Subagents for explicitly authorized bounded delegation.
- Automations or heartbeats for follow-up monitoring.
- Project-defined task pools, external worker systems, or routing scripts.
- Zhixia/local-doc knowledge exports through `.codex-knowledge/`, or another local knowledge path chosen by the project.

Knowledge provider modes:

- `none`: pure orchestration with explicit task cards, handoffs, and source files.
- `generic`: retrieval only; CEO Flow does not assume screenshot slimming, thread history indexes, or harvest writeback.
- `zhixia-enhanced`: summary-first retrieval, compact memory packets, and accepted-result writeback to Zhixia-scannable notes so future lanes depend on summaries instead of long chat history.

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
