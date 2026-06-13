# CEO Flow

CEO Flow is a Codex plugin for people who want Codex to manage a project like a small product team, not just answer one task at a time. The package is still named `ceo-thread-orchestrator` for compatibility, but CEO Flow is the short public name.

It turns the current Codex thread into a CEO/PM/architect lane. That lane keeps the broad context, makes decisions, designs the team shape, routes work to specialist lanes, and checks evidence before accepting results. When that CEO thread owns an accepted PRD or task graph, the next execution request should move into a lightweight Core Team execution wave instead of staying in CEO-only planning.

## Why This Exists

Modern Codex can work across threads, worktrees, automations, subagents, local files, and project memory. That is powerful, but it also creates a coordination problem:

- Which thread should do the work?
- When should Codex reuse an existing thread instead of creating a new one?
- How much context should move between threads?
- Who decides whether a worker report is good enough?
- Where should project memory live after the chat scrolls away?

CEO Flow gives Codex a practical operating model for those questions.

## Core Idea

Use one high-reasoning CEO lane and several bounded specialist lanes.

The CEO lane owns:

- project scope and tradeoffs
- architecture decisions
- task decomposition
- staffing and thread reuse
- memory bootstrap packets
- lightweight team rosters
- evidence memory cards
- cross-thread relay
- review and acceptance decisions
- short user-facing reports

Specialist lanes own bounded work:

- implementation
- review and QA
- UX and product critique
- market or research scans
- project knowledge and memory hygiene

The CEO lane remains accountable. A worker report is evidence, not proof.

## Default Core Team

CEO Flow has a default company-style role map:

- CEO / PM / Architect
- Implementation Expert
- Review / QA Expert
- Product / UX Expert
- Knowledge / Memory Expert
- Research / Docs Expert

This is not a permanent org chart and it is not an automatic workflow engine. Roles become visible specialist lanes only when the task graph needs them, current tools allow them, and the user or project authorizes execution.

The normal PRD path is: the PRD thread is the CEO thread; once the PRD or task graph is accepted and the user asks to execute, the CEO maps work onto the smallest useful Core Team. Most projects start with CEO plus one implementation lane. High-risk or user-facing work adds review/QA. Product/UX, knowledge, and research lanes appear only when their evidence is needed.

Review/QA lanes should be neutral and evidence-first. Their job is not to flatter the user, defend the worker, or keep momentum by accepting weak evidence. When model or thinking controls are available, independent review gates should use high reasoning.

After dispatch, the CEO keeps harvesting results. It reads worker reports, checks evidence, classifies lanes as accepted, revise, blocked, superseded, still running, or stale, then sends the next unblocked task. Worker lanes should report routine in-scope questions to the CEO, not the user. The user is needed only when the decision changes the accepted PRD, exceeds the write-set or budget, needs credentials, touches destructive operations, or changes product direction.

## Unattended Execution

CEO Flow is often used for work that should keep moving while the user is away. The CEO lane should plan command approvals before dispatching worker lanes, not discover them through scattered mid-run prompts.

Each unattended implementation task card should include a command approval profile, allowed command families, and commands that must not run. Allowed families are usually workspace-local reads, scoped edits, project test/build scripts, and required screenshots. Disallowed commands include destructive operations, broad machine inspection, credential access, external-service calls, and machine-specific absolute-path probes unless the CEO explicitly approved them for that wave.

This does not bypass the Codex host's security UI. If the needed command families are not already allowed, the CEO should ask once at wave start, choose safer no-approval commands, reuse a lane with the right permission profile, or hold the wave at the CEO lane until command preauthorization exists. Worker lanes report blocked commands to CEO instead of asking the user for routine in-scope approval.

## Dynamic Thread Scaling

The plugin treats new threads as a capacity decision, not a reflex.

For ordinary coding tasks, it prefers one reusable implementation lane. That code lane keeps doing code work and accumulates useful local context.

It adds another code lane only when:

- the new work can run in parallel
- the write-set does not overlap
- the work can be verified independently
- the added speed is worth the merge and review cost

When requirements change mid-task, the CEO lane rebuilds the whole task graph first. It then decides whether to continue the current lane, queue the new work, add a reviewer, create an independent specialist lane, or supersede existing work.

## Code Quality Guardrails

The plugin treats AI-written code as fast but unfinished work. Before dispatching implementation, the CEO lane defines architecture invariants, reference docs, a rollback baseline, a narrow write-set, and verification evidence.

Workers should avoid tech-stack drift, duplicate logic, tight coupling, magic numbers, weak names, missing boundary checks, and broad speculative rewrites. If repeated fixes make the code worse, the CEO should stop the loop, preserve useful findings, and choose rollback planning, a fresh bounded task card, or independent read-only review.

## Goal Completion Loop

The plugin is not meant to stop at "here is a team plan."

For work that spans more than one step, the CEO lane keeps a lightweight goal brief:

- user outcome
- done criteria
- non-goals
- task graph
- active lanes and thread ids
- current owner
- last evidence
- next action
- closure state: accepted, blocked, or superseded

Substantial planning and review outputs should be delivered as project documents, not only as chat text. PRDs, goal briefs, task graphs, task-card packs, review plans, audit reports, acceptance reports, and handoff packets should be saved in the project's agreed docs or knowledge-writeback location. The chat response should summarize the result, link the document, and call out only decisions, top findings, or risks that need attention.

Each CEO turn should move the goal forward by dispatching work, harvesting worker results, checking evidence, requesting revision, accepting, blocking, superseding, or updating durable memory.

## Memory Model

The plugin treats memory as explicit infrastructure.

Its default stack is:

1. project instructions and canonical local memory files
2. recommended Zhixia or `.codex-knowledge/` retrieval when available
3. active thread reports and relay packets
4. decision logs, bug memory, handoff logs, and generated docs

New or revived threads receive a compact memory packet. They should not be expected to infer project history from hidden chat context.

Projects may also specify another local knowledge path. Zhixia is the recommended knowledge provider for CEO Flow, not a hard requirement for every host.

CEO Flow uses this memory layer as a runtime context governor. New threads and worker packets should receive compact task context, Zhixia excerpts, source refs, and narrow Guardian evidence only when relevant. They should not receive full CEO chats, full `.codex-knowledge` dumps, long implementation transcripts, or raw sessions by default. If the user wants to keep using an old thread, CEO Flow should check Zhixia/Guardian history cards and compact receipts before recommending a fresh-thread handoff.

CEO Flow uses five knowledge provider modes:

- `none`: pure orchestration with explicit task cards, handoffs, and source files.
- `project-memory`: canonical local memory docs such as project memory, decisions, handoffs, and bug memory.
- `zhixia-local-docs`: summary-first current project context from Zhixia or `.codex-knowledge/`.
- `guardian-history`: old Codex sessions, paused-task discovery, history evidence, health summaries, and restore dry-runs.
- `hybrid`: Zhixia for current project knowledge plus Guardian for old thread history and paused-task recovery.

## Compatibility Matrix

| Host capability | CEO Flow behavior |
|---|---|
| No thread tools | Works as a planning, task-card, document-first review, and acceptance discipline. It must not pretend to create worker lanes. |
| Manual copy/paste lanes only | Writes task cards, memory packets, and review reports as documents for manual relay. |
| Codex app thread tools available | Can create, read, reuse, steer, and harvest specialist lanes when authorized. |
| No model selection controls | States the intended model/reasoning lane without pretending to set unavailable controls. |
| No automations or heartbeats | Leaves a concrete next harvest action instead of creating a monitor. |
| No Zhixia or Guardian | Runs with explicit task cards, source files, worker reports, and project memory docs. |
| Zhixia available | Uses summary-first current project context and writes accepted learning into canonical docs or Zhixia-scannable artifacts. |
| Guardian available | Uses old-thread history and restore evidence read-only by default; selected-thread compaction requires explicit user trigger and receipt; restore remains dry-run unless explicitly approved. |

## Lightweight Team Records

CEO Flow can keep a small roster for reusable specialist lanes: role, capabilities, write policy, trust level, current status, and last evidence. It can also capture evidence memory cards with the lesson, applicability, proof, tests, confidence, and status.

These records are deliberately manual and small. They help the CEO make better routing decisions without creating an automatic queue, supervisor, autoscaler, or self-repair system.

## Safety Boundaries

CEO Flow is deliberately cautious.

- It does not assume every Codex host has thread tools.
- It does not silently create persistent threads when the active tool contract requires explicit authorization.
- It does not treat automations or queued tasks as running unless there is live evidence.
- It does not install or switch memory systems just because one exists.
- It does not let multiple workers edit the same write-set at the same time.
- It keeps expensive model lanes for high-risk reasoning, not routine work.
- It does not treat Guardian as Windows Task Scheduler, automatic log cleanup, process-manager pruning, or a default raw-session reader.
- It does not force a new thread when the user explicitly wants old-thread optimization; it distinguishes same-thread reopen, old-thread compaction, and fresh-thread handoff.

## Who It Is For

This plugin is useful for:

- solo builders managing large Codex projects
- product teams using multiple Codex threads
- people who want stronger project memory and handoff discipline
- teams experimenting with agent orchestration
- non-programmers who want Codex to act more like a project lead

## What It Is Not

It is not a replacement for judgment, tests, or project ownership.

It is also not a promise that every Codex environment can create or manage threads. The skill always follows the active tool contract. If a host does not expose thread tools, the CEO lane should still plan, document, and route work through the mechanisms that are available.

## Example Workflow

1. A user gives product feedback or a bug report.
2. The CEO lane normalizes it into a goal brief or task card.
3. The CEO lane defines done criteria and a task graph.
4. The CEO lane searches for reusable specialist threads.
5. One implementation lane receives bounded work.
6. A review lane checks high-risk changes when needed.
7. The CEO lane inspects evidence and decides accept, revise, block, or supersede.
8. Stable learning goes back into memory, decisions, bug notes, or docs.

## Status

This is an experimental community plugin. It is meant to evolve with Codex thread tooling and with real project practice.
