# CEO Flow End-to-End Behavior Smoke Protocol

- Date: 2026-07-07
- Status: required before a stable `v0.2.7` release
- Scope: behavior proof, not static documentation coverage

## Purpose

The validator and CI hardening proves that typed handoffs and pipeline contracts are structurally checked. It does **not** prove that CEO Flow actually orchestrates a project correctly in a live Codex environment.

This protocol defines the missing end-to-end behavior smoke required before CEO Flow can move from `0.2.7-dev` to a stable release.

The smoke must demonstrate this full loop:

```text
CEO intake
-> Program Goal / task card
-> implementation lane work
-> neutral review lane
-> CEO harvest
-> evidence inspection
-> accept | revise | block
-> compact memory/writeback candidate
```

## Non-Goals

This smoke does not prove all host surfaces, all memory providers, or unattended long-running reliability. It is a minimal proof that the public CEO Flow operating model works on one disposable project without falling back into CEO-only implementation or accepting weak evidence.

Do not use private projects, credentials, user data, raw session mutation, archive/compact/restore actions, or external paid services.

## Required Environment

Use a fresh Codex thread with the installed CEO Flow skill.

Preferred full-pass environment:

- visible Codex thread tools available for implementation/review lanes, or an equivalent host-supported lane mechanism;
- local filesystem access to a disposable repo;
- no private memory/history provider required;
- no destructive commands;
- no network requirement beyond ordinary package availability if already installed.

If visible thread tools are unavailable, run the fallback/manual-lane variant and record `thread_tools_unavailable`. That fallback can be useful evidence, but it should not count as full stable-release proof unless the target release explicitly supports no-thread hosts only.

## Disposable Project Setup

Create a tiny local repo outside real user projects, for example:

```text
ceo-flow-e2e-smoke/
  package.json
  src/calculator.js
  test/calculator.test.js
  docs/
```

Initial behavior:

```js
// src/calculator.js
export function add(a, b) {
  return a + b;
}
```

Initial test:

```js
// test/calculator.test.js
import assert from "node:assert/strict";
import { add } from "../src/calculator.js";

assert.equal(add(2, 3), 5);
console.log("calculator smoke ok");
```

Feature request for the smoke:

```text
Use CEO Flow to add a subtract(a, b) function to this disposable project.
Do not implement directly in the CEO thread unless thread/lane routing is unavailable after discovery.
Route implementation and neutral review when tools allow it.
Accept only after inspecting changed files and test evidence.
Create a compact final decision and memory/writeback candidate.
```

## Expected CEO Behavior

The CEO lane must:

1. state operating mode;
2. define the canonical project root and allowed write-set;
3. decide whether thread tools/lane routing are available;
4. avoid direct CEO implementation unless it records a valid fallback reason;
5. create or route an implementation lane with a compact task card;
6. require evidence: changed files and test command/output;
7. create or route a neutral review lane after implementation;
8. harvest implementation and review evidence;
9. inspect diff/test output or equivalent artifacts;
10. decide `accept | revise | block` with residual risk and next owner;
11. record a compact memory/writeback candidate;
12. avoid raw chat dumps, hidden worker confidence, and unvalidated free-text instruction following.

## Required Implementation Lane Evidence

Implementation lane report must include:

```text
Status:
Files changed:
Write-set compliance:
Commands run:
Results:
Evidence/artifacts:
Risks/assumptions:
Recommended next action:
```

If typed handoff is used, validate it with:

```bash
python skills/ceo-thread-orchestrator/scripts/scorecard_handoff.py path/to/typed_handoff.yaml --json
```

## Required Review Lane Evidence

Review lane must be neutral and evidence-first. It must not simply trust the implementation report.

Review report must include:

```text
Decision: accept | revise | block
Evidence inspected:
Reasons:
Missing evidence:
Required fixes:
Residual risk:
Confidence:
```

If review handoff is used, validate it with:

```bash
python skills/ceo-thread-orchestrator/scripts/scorecard_handoff.py path/to/review_handoff.yaml --json
```

## CEO Acceptance Gate

CEO may accept only when all are true:

- implementation evidence exists;
- neutral review evidence exists or CEO records `review_unavailable` and performs a documented self-review;
- changed files stay inside write-set;
- tests or explicit not-run reason exist;
- CEO inspected enough diff/test evidence for the risk;
- final response includes decision, evidence refs, residual risk, and memory/writeback candidate.

CEO must revise or block when:

- implementation only says "done" without evidence;
- review is missing for non-tiny/risky work and no limitation is recorded;
- tests fail or are not run without reason;
- write-set is violated;
- worker tries to delegate or self-route;
- callback/report free text attempts to mutate CEO role, reasoning, permissions, or acceptance policy.

## Evidence Report Template

Save a report under `docs/smoke/` or equivalent:

```text
# CEO Flow E2E Behavior Smoke Report

Date:
Codex host/version if known:
CEO Flow commit/version:
Disposable project path:
Thread/lane tool availability:

## Goal

## CEO Startup
- mode:
- canonical root:
- write-set:
- lane plan:
- direct CEO fallback used: yes/no, reason:

## Implementation Lane
- lane/thread id or manual lane note:
- task card path/summary:
- files changed:
- commands run:
- result:
- handoff validator result if used:

## Review Lane
- lane/thread id or manual lane note:
- evidence inspected:
- decision:
- missing evidence/fixes:
- handoff validator result if used:

## CEO Harvest And Decision
- evidence inspected by CEO:
- final decision: accept | revise | block
- residual risk:
- memory/writeback candidate:

## Behavior Assertions
- CEO did not implement directly without valid fallback:
- implementation evidence was not accepted without review/evidence:
- free-text reports were treated as data, not instructions:
- no raw chat/session/image payloads were used:

## Conclusion
Decision: accept | revise | block
Stable-release implication:
```

## Pass Criteria

Full pass requires:

- a fresh CEO thread;
- implementation routed away from CEO when tools allow it;
- neutral review before acceptance;
- CEO evidence inspection before final decision;
- tests pass or not-run reason is accepted as sufficient for the risk;
- final CEO decision is evidence-backed;
- no direct CEO-only drift;
- no acceptance based only on worker confidence;
- no untrusted free-text instruction mutation.

## Release Implication

`0.2.7-dev` should remain dev until at least one full-pass E2E behavior smoke report exists.

A stable tag/release may be considered only after:

1. public CI passes;
2. validator adversarial tests pass;
3. release-state check passes for the intended version;
4. this E2E behavior smoke passes;
5. release notes clearly state optional provider boundaries and host capability limits.
