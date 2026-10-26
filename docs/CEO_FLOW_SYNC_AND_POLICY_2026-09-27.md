# Context Sync And Execution Policy Revision

## Scope

Generic CEO Flow only. No product edits, live Runtime/store calls, memory refresh,
Provider calls, model changes, commit or push. Installed Zhixia's control adapter
and sync_context schema were inspected read-only; all sync tests use fixtures.

## Changes

- Added `sync_context_driver.py` and `context-sync.md`. Explicit startup,
  before-dispatch and after-accepted-refresh boundaries call the installed control
  adapter, with default 1200-token budget and exact task/project scoping.
- Validated ready_new packets reserve a generation/query pair in confirmed atomic
  state before output; unchanged/repeated pairs emit nothing. Query changes can
  select new memories in the same generation. Failures never confer authority.
- Concurrent duplicate boundaries emit once; failure events do not poll. Durability
  ambiguity suppresses output. Existing takeover and refresh protocols are intact.
- Host preflight wording applies to executor-managed requests, not every native
  coding/tool operation. Existing freeze and lifecycle ACK rules remain strict.
- Low-risk callbacks may include one independent review. Low/medium verification
  profile overrides require caller-side rationale; worker callback fields cannot
  authorize overrides. High-risk full-profile and independent-review gates remain.
- Native callback CLI and lifecycle event accept the caller policy. Evidence still
  must match registered task/slice and declared commands.
- Visual interaction uses bounded sequential observations (default 6 images/8 MB
  per checkpoint, under 2 MB each) and SHA deduplication, not one image per turn.
- Model override rules defer to the actual tool contract and explicit user choice.

## Validation

- Complete canonical and installed skill suites: 261/261 each.

- New sync fixture suite: 11 tests including stale/forbidden/scope/budget negatives,
  restart deduplication, changed goal, changed generation, project/task isolation,
  concurrent requests and post-commit failure. No real Runtime invocation.
- Callback suite: 18 tests, including extra low-risk review, caller-controlled
  medium profile, invalid rationale and rejection of high-risk downgrade.
- Repository tests: 16 passed. Static smoke: 72 passed. Skill validation, Python
  compilation and diff whitespace checks passed.
- Source and installed skill manifest: 62 files, equivalent,
  `fe7b753c43c42fba6ab0625d3063a7caf59f5e539b0dbf0ec6a39f9adc363f95`.

## Remaining Boundaries

This is an executable safe-boundary entry, not a registered Desktop event hook.
`hostTriggerVerified=false` is intentional. Host-trigger/injection E2E remains
unverified; prompts alone cannot guarantee invocation or history replacement.
At-most-once emission can lose delivery after durable reservation plus process
failure. Never automatically replay or claim Host consumption; reconcile explicitly
or use the existing clean takeover workflow. Unsupported source URI forms remain
fail-closed. Read-only sync does not authenticate a caller's acceptance event or
authorize refresh. Exact formal acceptance/refresh/reverify is still separate.

Visual budgets and model-override precedence are instructions, not OS interceptors.
No claim of GPT-6 performance improvement or current running-task adoption is made.
