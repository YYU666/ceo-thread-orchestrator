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

## Execution Surfaces

CEO Flow keeps Codex internal multi-thread execution as its native path. This
branch also supports an optional hybrid path in which the Codex CEO sends one
bounded task to Codex Multi-Model Desktop (CMMD), validates a Host-owned typed
receipt, and remains the only acceptance and publishing authority.

- `codex-internal`: reusable Codex implementation/review/QA lanes.
- `cmmd`: currently optional R0 read-only runs through the v2 task, Context
  View, budget, and receipt contracts. R1 bounded writing is documented as a
  future gate but remains unavailable in the bundled R0-only Context View
  snapshot.
- OpenClaw: historical branch material only; it is not a default, dependency,
  retry target, or fallback in the CMMD hybrid path.

An explicit request to use Codex internal threads always remains valid. CMMD is
fail-closed when it is unavailable, contract-incompatible, or lacks readiness
for the requested risk tier; the CEO may then make a new, explicit routing
decision rather than silently switching executors. See
[CMMD Hybrid Execution](skills/ceo-thread-orchestrator/references/cmmd-execution.md)
and [branch rationale](docs/CMMD_HYBRID_BRANCH.md).

## What It Does

- Keeps the current Codex thread as the high-reasoning CEO lane.
- Creates the smallest useful execution artifact: task card, goal brief, or PRD/design brief.
- Delivers substantial PRDs, task graphs, task-card packs, audit/review reports, acceptance reports, and handoff packets as project documents, with chat limited to summary, links, risks, and decisions needed.
- Treats the PRD/design/task-graph thread as the CEO thread by default, then switches to Core Team execution after the plan is accepted.
- Maintains a goal ledger with done criteria, task graph, active owner, evidence, next action, and closure state.
- Runs a CEO harvest loop after dispatch: collect worker results, classify evidence, request revisions, and send the next unblocked task until the project lands.
- Supports pipeline execution for broad PRDs: bundled pipeline, handoff, review, and scorecard templates plus lightweight validators help CEO decide safe parallel lanes and reject vague worker reports.
- Plans unattended-safe command approval profiles before dispatch so routine shell/browser/test prompts do not stall worker lanes mid-run.
- Uses provider-specific memory modes: project memory for canonical docs, compact Memory Runtime providers for current project context, and optional history providers for old Codex sessions or paused-task recovery.
- Supports an event-triggered Memory Core continuity gate: CEO takeover/recovery consumes exact-project mandatory ProjectBrain pagination, workers/reviewers receive role-bounded slots, lifecycle changes emit bounded events, and trigger receipts prove retrieve/precedent/writeback execution when the provider exposes them.
- Uses a Single Front Door contract: the user normally interacts with one accountable CEO identity while implementation, review, research, memory, and temporary contractor lanes remain CEO-mediated behind it; visible specialist threads do not become separate entrances the user must coordinate.
- Acts as a runtime context governor: dispatch compact task packets, prefer source-backed summaries and refs, avoid long chat transcripts/raw sessions by default, and use optional history-provider evidence only when relevant.
- Keeps independent review gates neutral and evidence-first, with high reasoning when the tool surface allows it.
- Discovers model controls per surface and routes lanes through `fast`, `balanced`, `frontier`, or deliberate `inherit` classes instead of accidentally giving every worker the CEO's most expensive profile.
- Routes implementation, review, QA, product, market, and knowledge work to specialist lanes when tools allow it.
- Reuses existing specialist threads before creating new ones.
- Dynamically adjusts thread count when task size or requirements change.
- Bootstraps new or reused threads with compact memory packets.
- Maintains a lightweight team roster with role, capability, write policy, trust level, status, and last evidence.
- Captures evidence memory cards before promoting reusable lessons into durable project knowledge.
- Adds code quality gates to prevent broad speculative rewrites, hidden behavior changes, and repeated low-signal patch attempts.
- Detects doom-loop symptoms and prefers rollback, fresh bounded task cards, or independent review over larger speculative diffs.
- Supports `.codex-knowledge/` or other local project-memory exports when available, without requiring any private provider.
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

The minimum execution team is usually `CEO + Implementation`. Add `Review/QA` for high-risk or user-facing work, `Product/UX` for meaningful product or interface decisions, and `Knowledge/Memory` only when accepted learning should be written back. Review/QA lanes should stay neutral: they are not there to flatter the user, defend the worker, or keep momentum by blessing weak evidence. When model or thinking controls are available, CEO Flow discovers them per surface: routine implementation normally uses a balanced class, deterministic sidecars use a fast class, and neutral review/architecture uses a frontier class with high reasoning. Omitted settings are treated as inheritance, not automatic role optimization. Substantial review results should be saved as documents; chat should show only the decision, link, top risks, and next owner.

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
- Local project-memory exports such as `.codex-knowledge/`, or another local knowledge path chosen by the project.

Knowledge provider modes:

- `none`: pure orchestration with explicit task cards, handoffs, and source files.
- `project-memory`: canonical local memory docs such as project memory, decisions, handoffs, and bug memory.
- `memory-runtime`: summary-first current project context from a configured local provider or `.codex-knowledge/` helper.
- `history-provider`: old Codex sessions, paused-task discovery, history evidence, health summaries, and restore dry-runs from a configured provider.
- `hybrid`: current project memory plus history-provider source refs for old thread recovery.

## Compatibility Matrix

| Host capability | CEO Flow behavior |
|---|---|
| No thread tools | Works as a planning, task-card, document-first review, and acceptance discipline. It must not pretend to create worker lanes. |
| Manual copy/paste lanes only | Writes task cards, memory packets, and review reports as documents so a user can relay them manually. |
| Codex app thread tools available | Can create, read, reuse, steer, and harvest specialist lanes when the tool contract and user/project authorization allow it. |
| CMMD not installed or not enabled | Uses Codex internal lanes normally; CMMD is optional and no external execution is implied. |
| CMMD enabled with matching readiness | May dispatch one bounded v2 R0 run, then requires Codex CEO receipt/evidence review. R1 remains blocked until an R1-capable Context View and production evidence are accepted. |
| Different model lists across threads, subagents, and automations | Runs capability discovery per surface and resolves abstract `fast`, `balanced`, `frontier`, or `inherit` classes against the live tool contract. |
| No model selection controls | States the intended model/reasoning lane, then uses the closest available mechanism without pretending to set unavailable controls. |
| No automations or heartbeats | Leaves a concrete next harvest action in the report instead of creating a monitor. |
| No memory/history provider | Runs as a normal CEO Flow skill with explicit task cards, source files, worker reports, and project memory docs. |
| Memory Runtime available | Uses summary-first current project context and writes accepted learning into canonical docs or provider-scannable artifacts. |
| History provider available | Uses old-thread history and restore evidence read-only by default; selected-thread compaction is allowed only after explicit user trigger and safety receipt; restore remains dry-run unless the user explicitly approves actual restore. |

Memory/history providers are optional integrations, not prerequisites for the core skill. Provider-specific examples live in [Optional Memory And History Providers](docs/optional-integrations/MEMORY_AND_HISTORY_PROVIDERS.md). CEO Flow must not advertise a provider command as available until the local deployment supports it. Cleanup, prune, actual restore, and raw-session mutation remain explicit maintenance actions outside default CEO Flow runtime behavior.

## Repository Structure

```text
ceo-thread-orchestrator/
├── .codex-plugin/plugin.json
├── .github/workflows/ci.yml
├── requirements-dev.txt
├── scripts/
│   ├── smoke_eval.py
│   ├── check_release_state.py
│   └── validate.ps1
├── tests/
│   └── test_validators.py
├── skills/
│   └── ceo-thread-orchestrator/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       ├── references/
│       │   ├── ceo-autopilot.md
│       │   ├── cmmd-execution.md
│       │   ├── context-memory.md
│       │   ├── flowskill-hook.md
│       │   ├── guardian-history.md
│       │   ├── memory-runtime.md
│       │   ├── operating-playbook.md
│       │   ├── parallel-waves.md
│       │   ├── pipeline-contract.md
│       │   ├── quality-gate.md
│       │   ├── repo-baseline.md
│       │   ├── self-harness.md
│       │   ├── state-schema.md
│       │   ├── thread-ops.md
│       │   ├── visual-evidence.md
│       │   └── open-source-readiness.md
│       ├── templates/
│       │   ├── pipeline.yaml
│       │   ├── typed_handoff.yaml
│       │   ├── review_handoff.yaml
│       │   └── scorecard.md
│       └── scripts/
│           ├── validate_cmmd_exchange.py
│           ├── validate_pipeline.py
│           └── scorecard_handoff.py
├── examples/
└── docs/
```

## Documentation

- [English introduction](docs/INTRODUCTION.md)
- [中文介绍](docs/INTRODUCTION.zh-CN.md)
- [Optional Memory And History Providers](docs/optional-integrations/MEMORY_AND_HISTORY_PROVIDERS.md)
- [Runtime Context Governor revision report](docs/CEO_FLOW_RUNTIME_CONTEXT_GOVERNOR_REPORT_2026-06-11.md)
- [Code-producing smoke report](docs/CEO_FLOW_CODE_SMOKE_REPORT_2026-06-11.md)
- [Release gate evidence](docs/CEO_FLOW_RELEASE_GATE_2026-06-11.md)
- [E2E behavior smoke protocol](docs/CEO_FLOW_E2E_BEHAVIOR_SMOKE_PROTOCOL_2026-07-07.md)
- [Zhixia 0.9.0 Memory Core compatibility report](docs/smoke/CEO_FLOW_ZHIXIA_090_MEMORY_CORE_COMPAT_REPORT_2026-07-16.md)
- [CMMD hybrid compatibility report](docs/smoke/CEO_FLOW_CMMD_HYBRID_COMPAT_REPORT_2026-07-27.md)
- [Smoke prompts](examples/smoke-prompts.md)
- [Pipeline contract reference](skills/ceo-thread-orchestrator/references/pipeline-contract.md)
- [Operating playbook](skills/ceo-thread-orchestrator/references/operating-playbook.md)
- [Open-source readiness checklist](skills/ceo-thread-orchestrator/references/open-source-readiness.md)

## Safety Model

The skill treats new threads as capacity decisions, not a reflex. For ordinary coding, it prefers one reusable implementation lane. It adds another code lane only when work can run in parallel, has a distinct write-set, and can be verified independently.

Worker reports are evidence, not proof. The CEO lane still inspects meaningful artifacts before accepting work.

After installing or updating the plugin, restart or refresh Codex if old threads appear to use stale behavior. Existing long-running threads may still carry older hot context; after an explicit old-thread compaction, reopening the same thread means rereading its slimmed session body, not creating a new thread.

## Validation

Public, reproducible checks:

```powershell
python -m pip install -r requirements-dev.txt
python scripts\smoke_eval.py
python -m unittest discover -s tests -v
python skills\ceo-thread-orchestrator\scripts\validate_pipeline.py skills\ceo-thread-orchestrator\templates\pipeline.yaml --json
python skills\ceo-thread-orchestrator\scripts\scorecard_handoff.py skills\ceo-thread-orchestrator\templates\typed_handoff.yaml --json
python skills\ceo-thread-orchestrator\scripts\scorecard_handoff.py skills\ceo-thread-orchestrator\templates\review_handoff.yaml --json
python scripts\check_release_state.py
```

Optional isolated Zhixia 0.9.0 provider smoke, when the local Zhixia app source and dependencies are available:

```powershell
node scripts\zhixia_memory_core_recovery_probe.cjs <zhixia-app-root> <ceo-flow-repo-root>
```

`smoke_eval.py` is a static documentation coverage check. It verifies that smoke cases are well formed and that policy terms exist in the skill/reference corpus; it is not an LLM behavior evaluation. The adversarial validator tests in `tests/` check executable guardrails for typed handoffs and pipeline contracts.

Optional Codex-internal checks, when you have the corresponding local validator skills installed:

```powershell
python <path-to-skill-creator>/scripts/quick_validate.py .\skills\ceo-thread-orchestrator
python <path-to-plugin-creator>/scripts/validate_plugin.py .
```

Before publishing a release, save evidence for:

- public CI/reproducible validator output;
- optional skill/plugin validator output if available;
- privacy/path scan output;
- provider JSON smoke only when the release claims a specific memory/history integration;
- one real code-producing CEO -> implementation -> review -> CEO accept/revise smoke on a disposable project, following the E2E behavior smoke protocol.

## Contributing

Issues and pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes.

Useful contributions include:

- real-world smoke test reports;
- clearer task-card or goal-loop behavior;
- safer thread/review routing patterns;
- memory-provider integration notes;
- examples for Codex projects with different tool surfaces.

## Status

This is an experimental community plugin. Manifest versions with a `-dev` suffix are moving main-branch builds, not frozen releases. A stable release requires a full-pass E2E behavior smoke report in addition to green validator/CI checks. Codex thread tooling, model routing, worktrees, subagents, and automation support may differ by host and version. The skill always follows the active tool contract when it is stricter than the written workflow.

## License

MIT. See [LICENSE](LICENSE).
