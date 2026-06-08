# Changelog

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
