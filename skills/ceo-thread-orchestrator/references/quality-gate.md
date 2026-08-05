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

Reviewer starts from task card, diff, tests, local artifacts/screenshots by path, relevant docs, and compact evidence refs. A path is not permission to call `view_image`: zero-payload review uses local OCR/metadata/hash/diff summaries, while model-visible inspection requires a fresh bounded visual worker with no forked history. Do not send image attachments/base64/data:image/input_image, full screenshot JSON, or the implementation thread's long conversation unless a specific unresolved claim requires bounded model vision and CEO records reason and byte budget.

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

Allowed only for:

- explicit user request for direct execution;
- orchestration skill, project memory, PRD, strategy, or docs edits;
- emergency unblock when delegation is unavailable or failed repeatedly;
- tiny local fixes where creating a worker costs more than the fix.

Not appropriate for broad user-facing implementation such as page rewrites, UI skeleton rebuilds, database/schema changes, Electron IPC, provider/generation flows, payment/auth, installer/deploy changes, or tasks requiring screenshots, runtime smoke tests, or independent review.

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
