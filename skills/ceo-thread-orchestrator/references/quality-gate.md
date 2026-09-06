# Quality Gate Reference

Use this reference for coding tasks, high-risk reviews, repeated failed fixes, UI quality checks, or acceptance gates.

## Contents

- Change budget and implementation requirements
- CEO and independent review
- Doom-loop recovery
- Direct coding boundary and decision template

## Change Budget

Before dispatching or doing implementation work, define:

- intended files or modules;
- maximum acceptable edit scope;
- architecture, framework, API, persistence, naming, and UX invariants;
- reference scan notes for substantial product, code, UI, architecture, workflow, or creative implementation: official docs, mature OSS/local patterns, what to borrow, what not to copy, and license boundary;
- official/current docs or local references for unfamiliar APIs;
- behavior that must remain unchanged;
- required tests, local artifact screenshots, smoke checks, type checks, lint, format, or build checks;
- rollback baseline;
- stop condition if the fix starts spreading.

## Implementation Requirements

Implementation workers must:

- inspect existing architecture and local conventions before editing;
- follow accepted reference patterns where relevant, but do not cargo-cult unrelated architecture or copy licensed/private code;
- make the smallest behavior-preserving change that satisfies the task;
- keep one coherent editing unit at a time;
- for large work, land one function/component/route/module slice, verify it, then continue;
- avoid broad rewrites, dependency churn, generated boilerplate dumps, speculative abstractions, and style-only refactors;
- avoid copy-paste logic, tight coupling, unclear names, unexplained magic numbers, and hidden single-use shortcuts;
- avoid masking errors with catch-all fallbacks, disabled tests, relaxed types, removed assertions, or swallowed exceptions;
- preserve or improve error handling, validation, boundary checks, and failure paths touched by the change;
- keep public APIs, data contracts, persistence semantics, and user-visible copy stable unless explicitly changed;
- stop when root cause contradicts the task card;
- run a self-review before reporting;
- update or add focused tests when risk justifies it.

Worker reports must include changed files, exact commands, tests, failures, residual risks, quality-gate status, and memory update candidates.

## CEO Review

Scale verification to the accepted slice risk:

| Risk | Default evidence | Review budget |
| --- | --- | --- |
| `low` | at most two changed files, diff plus focused test | one CEO verification, no neutral review |
| `medium` | focused evidence plus typecheck/build | one CEO verification; neutral review only when a separate trigger applies |
| `high` | full affected suite/build and risk-specific evidence | one CEO verification plus exactly one neutral review |

Default to one CEO verification, one risk-triggered neutral review, one consolidated revision, and three process updates for milestones. New content-addressed verification evidence permits one additional check/revision per chained callback; unchanged evidence does not reset the budget. Acceptance requires at least one CEO verification and high risk requires at least one neutral review. Complete required checks, then broaden or repeat only for changed code, failures, or unresolved concerns. If equivalent failures persist, shrink the slice or change approach. Store long outputs in artifacts and return compact findings.

For ordinary native Codex review, use `callback_gateway.py CALLBACK --native-review-workspace WORKSPACE --task-id TASK --slice-id SLICE --slice-basis SHA`. The caller supplies the registered task/slice identity and independently inspects diff and command results. This local path verifies the same bounded content-addressed command receipts without a Desktop socket. Missing actual model telemetry remains unknown and does not prevent evidence-based acceptance. Add `--exact-model-required` for explicit model requirements; external Harnesses and model evaluations always use the strict route. The CLI reviews one callback; continuing workflows must persist the returned slice ledger through their confirmed state writer. A worker must never self-approve by selecting this caller policy or fabricating evidence.

Register the worker `callbackTaskId`, `sliceId`, and `sliceBasisSha256` in the trusted task event before the first callback. Persist callback sequence, prior callback digest, and cumulative review/update counters in the atomically committed task state. Each later callback must preserve all three registered identities, increment sequence by one, bind the prior digest, and use non-decreasing counters. A task-id/slice alias, unregistered slice, broken chain, or counter reset may be inspected as untrusted evidence but cannot advance the ledger or authorize acceptance.

Each acceptance evidence ref is `safe/relative/path#sha256=<64-hex>` and points to a bounded `ceo_verification_command_receipt_v1`, not a free-form log. The production Host hashes the file below the canonical workspace, rejects symlink/path escape and forbidden stores, parses a strict receipt binding worker task, slice, basis, verification profile, exact command, `exitCode=0`, and `status=passed`, and requires coverage of every declared command. It then supplies a compact `ceo_verification_evidence_receipt_v1` through a process-local capability. A placeholder path, caller digest, or non-existent artifact cannot authorize acceptance.

The CEO checks more than "does it run":

- diff size and touched files match the change budget;
- root cause is named, not just symptom;
- new code follows nearby patterns;
- existing helpers were reused when appropriate;
- edge cases and failure paths are preserved;
- tests or smoke checks cover changed behavior;
- UI/workflow/game/design changes are verified through user-visible behavior and local screenshot/artifact inspection where possible; callbacks and memory keep only paths, hashes, dimensions, summaries, and decisions;
- static checks/lint/type/build were run when available;
- no unrelated cleanup, formatting churn, dependency changes, or hidden product decisions are bundled;
- residual risk is explicit.

## Independent Review Gate

Use a separate reviewer for high-risk code, subtle tests, UI quality, generation/provider behavior, install/deploy, security, benchmark fairness, payment/auth, migrations, or expensive rollback risk.

Reviewer posture:

- neutral and evidence-first;
- not an advocate for worker, CEO, or user's preferred answer;
- high reasoning/thinking when the tool exposes it;
- report missed acceptance criteria, regressions, unclear evidence, and test gaps;
- do not flatter or reassure weak work.

Reviewer starts from task card, diff, tests, relevant artifacts and compact evidence. Authorized UI review may inspect bounded screenshots in the current task under `visual-evidence.md`; respect explicit no-image constraints. Do not forward image bodies, complete logs, or long implementation conversations into callbacks or memory.

## Doom Loop Recovery

After two failed attempts on the same bug, require root-cause re-analysis before another patch.

Doom-loop signs:

- repeated contradictory fixes;
- increasing diff size without new evidence;
- framework or data-contract drift;
- test weakening;
- catch-all fallbacks;
- fixes that only move the symptom;
- repeated uncertainty about the same root cause.

When doom-loop signs appear:

1. stop expanding the diff;
2. identify last stable baseline or evidence needed to find it;
3. preserve useful findings in memory;
4. route to review/debug lane or create a fresh bounded task card;
5. propose rollback only with user/project authorization;
6. do not run destructive rollback commands without explicit authorization.

## Direct CEO Coding Boundaries

Direct execution is appropriate for:

- explicit user request for direct execution;
- orchestration skill, project memory, PRD, strategy, or docs edits;
- emergency unblock when delegation is unavailable or failed repeatedly;
- tiny local fixes where creating a worker costs more than the fix.
- tightly coupled critical-path work where the CEO already has the necessary context and delegation would add serial handoff overhead.

For broad work, delegate independent modules when useful. Implementation ownership does not remove risk-specific review or testing requirements; a screenshot or build requirement alone is not a reason to force a new worker.

## Decision Template

```text
Decision: accept | revise | block | supersede
Evidence inspected:
Tests or artifacts checked:
Files or write-set reviewed:
Residual risk:
Next owner:
Memory update needed:
```

Accept only when the newest request is satisfied and evidence is good enough for risk. Revise when implementation, tests, UX, or report quality is insufficient. Block only for real external dependencies, missing credentials, broken tooling, or unresolved user decisions. Supersede when a newer decision or another lane made the task obsolete.
