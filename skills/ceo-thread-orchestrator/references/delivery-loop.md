# Outcome-First Delivery

This is the execution-shape policy for ordinary development. Authority, permissions,
source validation, callback integrity, and lifecycle gates remain unchanged.

## Choose The Smallest Loop

- Quick path: a local, understood, reversible change in at most two files with no
  security, permission, payment, persistence, shared-contract, deployment, or
  unresolved-risk impact. The current owner edits, inspects the diff and runs a
  focused check. No mandatory new task, neutral reviewer, pipeline, or callback.
- Delivery loop: one owner implements a user-observable scenario through testing
  and packaging, coordinating bounded executors where useful. An existing CEO can own tightly coupled work. Do not split
  diagnosis, coding, test execution, packaging, or checklist checking into serial
  tasks merely because they are different activities.
- High risk: retain one owner, plus independent review of the complete candidate
  and affected checks. Explicit user/project review requirements override defaults.
  Size alone and the mere presence of UI do not require an extra reviewer.

Use `python scripts/delivery_policy.py REQUEST.json` for a small deterministic
planning check. Operations are `plan`, `staffing`, `wait`, `reuse`, `build`, `cleanup`, `ui`, and `outcome`;
the JSON fields are defined in its functions and executable examples in
`tests/test_delivery_policy.py`. These are caller-side decisions, not Host receipts,
an automation scheduler, authenticated evidence, or a sandbox. Never treat a
worker-supplied result as permission or proof. Existing callback validation remains
mandatory for delegated acceptance. Do not run the helper for every trivial edit.

## One Owner, Bounded Executors

A delivery owner is accountable for integration; it is not a project-wide ban on
multiple executors. Keep a single writer per overlapping write-set, not necessarily
one writer for every independent module. A small quick-path edit stays local.

For a larger delivery, assess staffing at slice start/completion, scope expansion,
and completion of a temporary CEO takeover. Look for an independently specifiable
module, focused test task, or read-only verification that advances the delivery
while the CEO handles critical integration. With authorization, tools, useful work
and free capacity, delegate one such unit instead of indefinitely retaining all work.
Do not hand off the immediate blocker when doing so just makes the CEO wait.

Default to at most two concurrent child lanes, including reviewers; an explicit
project limit takes precedence. Reuse/harvest existing lanes before adding capacity.
Use temporary subagents for bounded work when permitted, not mandatory visible
sidebar tasks. Never infer permission to create a visible task, spend externally,
change models, or fork full history from this policy.

When serial execution is preferable, record one concrete reason in the existing
lane record: overlapping files, unstable interface, no independent ready unit,
handoff cost larger than the bounded work, tool unavailability, or user instruction.
Reassess that reason at the next boundary, not on every tool call. CEO takeover of
a stalled worker ends with that recovered slice; it does not grant a permanent
whole-project solo lease. Confirm the previous writer has stopped before takeover.

`plan` accepts an optional `staffing` object. Without it, non-quick work returns
`assess_independent_work`, not an unconditional solo recommendation. The `staffing`
operation consumes CEO-assessed independent work, active child count, project limit,
authorization/tool availability and checkpoint; it recommends at most one extra
lane. `independentReadyCount` excludes overlapping writes, unstable dependencies,
and work already assigned to active lanes. A positive recommendation is advisory,
not execution authorization; the caller performs the actual tool call and records
the returned handle. No background scheduler or automatic task creation is implied.

## Reach A Runnable Result Early

Before starting, name the user's scenario and smallest runnable checkpoint. For an
editor/game loop this might be launch the actual target, create/edit, continue with
the agent, play, save, reopen. Use the project's real scenario, not a generic list
of module tests. Run the first thin path before expanding independent modules;
surface native/tool limitations then, not at final packaging. At final acceptance,
verify the affected end-to-end path once on the candidate. A fast copy edit needs
only its affected screen, not the entire product journey.

Tests and review completion are supporting evidence, not a substitute for that
scenario. Blocked native validation is explicitly unverified, not passed from
source inspection. Do not add an unrequested platform or product requirement.

## Bounded Work And Waiting

Dispatch with a wall-time budget and first-result checkpoint. Starting defaults
are 10 minutes for quick work, 30 for a delivery loop, 60 for high risk; tune to
project difficulty before dispatch. These are work-planning budgets, not token or
context measurements and not automatic process-kill deadlines.

At the checkpoint return a compact runnable result, actionable blocker, or partial
diff with test state and a still-running task/process handle. Prefer event-driven
bounded waits. Unchanged polls and commentary do not reset the deadline. At expiry
inspect once, request a partial handoff and stop new writes; retain handles and
ownership until actual termination or safe handoff is confirmed. Do not start a
replacement writer while the prior writer may still run. Shrink scope or reassign
only after that confirmation. Never kill a write operation merely to meet a budget.
Record the timeout action in the existing lane record (`timeoutActionIssued`);
subsequent waits consume that record and wait for an event, not send another nudge.

## Reuse Checks, Not Claims

The owner runs checks; CEO/reviewer inspects results and selectively reproduces
uncertain or risky evidence rather than automatically rerunning every command.
Reuse requires independently verified success binding exact command, relevant
source/test/config/lock/dependency hashes and environment/toolchain identity.
HEAD alone is insufficient for a dirty tree. Unknown dependency coverage, changed
inputs/environment, flakiness, a failed check, or a new concern means rerun affected
checks. Broaden only when blast radius warrants it. Do not rebind an old worker
receipt to a new task/slice to bypass the callback ledger.
The reuse helper requires an explicit `flaky` flag; a known flaky check never
reuses. Outcome helpers check declared readiness only (`evidenceVerified=false`);
the caller must inspect the referenced artifacts before accepting an observation.

For builds, packages, installs, large copies, or cleanup, use `artifact-lifecycle.md`:
state the trigger, reuse verified outputs by actual inputs/environment/output hash,
run missing checks, and prefer incremental phase validation. Content-only changes
do not automatically rebuild the engine. Only exact user-authorized temporary paths
with verified identity, no live references, and checked recovery may be cleanup
candidates. Disk pressure limits new unnecessary large copies, not safe source work.

## One Current Status

Maintain one row per observable outcome in the existing Completion Dashboard:
`outcomeId | current status | candidate digest | evidence refs | blocker | next action`.
Update that row in place on a meaningful transition. Move superseded statements to
separate historical evidence; never append a competing "passed" row beside an old
"pending" row. Derive completion from currently verified outcomes, not number of
messages, substeps, or tests. Keep status reports concise and only persist decisions,
changes, blockers and results, while honoring host-required progress updates.

After a task is accepted or superseded, save compact source-backed continuity via
the configured memory service and archive through the available task tool after
confirming no writes or needed handoff remain. Missing backup authority creates a
visible lane-local cleanup backlog, never a fabricated backup or repeated wakeup.
Do not spawn a task solely to update this table or archive another task.
