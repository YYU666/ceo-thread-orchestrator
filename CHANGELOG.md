# Changelog

## v0.2.5 - Unattended Command Approval Planning

- Added an unattended execution policy so CEO Flow plans command approval profiles before dispatching worker lanes.
- Added task-card fields for allowed command families and commands that must not run.
- Clarified that routine command approvals are not product approvals and should not be scattered across worker threads.
- Added guidance for fully unattended waves: preauthorize command families, choose safer no-approval commands, reuse lanes with the right permission profile, or hold the wave at the CEO lane before dispatch.
- Added a smoke prompt for unattended command approval behavior.

## v0.2.4 - PRD Core Team Execution

- Added a default Core Team role map for CEO, implementation, review/QA, product/UX, knowledge/memory, and research/docs work.
- Clarified that the thread owning an accepted PRD, design brief, or task graph is the CEO thread by default.
- Added a PRD-to-execution gate: after the user asks to execute an accepted plan, CEO Flow should leave CEO-only planning and route work through reusable or requested expert lanes.
- Added a CEO harvest loop so the CEO collects worker results, classifies lane status, sends revisions or next tasks, and keeps routine in-scope approvals inside the CEO lane.
- Kept the Core Team model lightweight: roles are not permanent threads, and they do not create automatic queues, supervisor loops, or background workers.
- Added smoke prompts for PRD-to-Core-Team execution and CEO harvest behavior.

## v0.2.3 - CEO Flow

- Added CEO Flow as the short public display name while keeping `ceo-thread-orchestrator` as the compatible package and skill id.
- Added a lightweight team registry template for reusable lanes with role, capabilities, write policy, trust level, status, and last evidence.
- Added evidence memory card guidance so reusable lessons are promoted only when backed by concrete proof.
- Clarified Zhixia / `.codex-knowledge/` as the recommended CEO Flow knowledge provider while allowing projects to specify another local knowledge path.
- Updated smoke prompts for roster, evidence-memory, and CEO Flow alias behavior.

## v0.2.2 - Doom Loop Guardrails

- Added task-card fields for architecture invariants, required reference docs, and rollback baseline.
- Strengthened the code quality gate against doom loops, tech-stack drift, copy-paste logic, weak naming, magic numbers, missing boundary checks, and one-shot code.
- Added worker self-review, static-check expectations, and independent read-only review guidance for high-risk changes.
- Added smoke prompts for doom-loop recovery and maintainability gates.

## v0.2.1 - Code Quality Gate

- Added code quality gates to reduce broad speculative rewrites and repeated low-signal patch attempts.
- Added change budget and quality-gate reporting fields to implementation task cards.
- Added a smoke prompt for failed bug-fix loops that need root-cause re-analysis.

## v0.2.0 - Goal Completion Loop

- Added a goal completion loop so CEO orchestration continues toward accepted, blocked, or superseded outcomes.
- Added goal brief guidance, active goal ledger fields, and closure-state reporting.
- Tightened direct CEO fallback behavior so broad app-code/UI work routes to implementation lanes unless explicitly authorized.
- Added transient model failure handling so temporary 5xx/502 service errors do not become permanent model bans.
- Clarified exact model variant routing for preview or special pricing lanes.
- Improved public README positioning for open-source discovery.
- Added community contribution, code of conduct, security, issue, and PR templates.

## v0.1.1

- Removed private workflow names and local environment references from public skill text.
- Replaced private implementation details with generic configured task-pool and external-worker wording.

## v0.1.0

- Initial public release of CEO Thread Orchestrator.
- Added CEO-as-brain orchestration model, specialist lanes, memory bootstrap, adaptive staffing, review gates, and open-source readiness checklist.
