# CEO Flow Evidence-Driven Coding Discipline Compatibility Report

Date: 2026-07-29
Branch: `cmmd-hybrid-execution`
Decision: `accept` the lightweight CEO Flow integration; keep the CMMD profile
candidate-only and default-off.

## What Changed

- Added `references/coding-discipline.md` as a progressive-disclosure gate for
  non-trivial coding writers and reviewers.
- Added one optional field to Standard task cards and one exact-profile field
  to future-gated R1 cards.
- Added independent reviewer checks for adjacent refactors, scope deviations,
  real success evidence, and worker/model self-acceptance.
- Added static smoke cases proving that R0/tiny/status work does not inherit the
  full profile and that source/fake success cannot authorize R1 or savings
  claims.
- Made `scripts/validate.ps1` fail closed when an invoked validator exits
  non-zero; this report's first run correctly exposed one missing static-smoke
  phrase before the case was corrected.

## CMMD Evidence Consumed

CMMD accepted the source/fake candidate with:

- profile `evidence-driven-coding-discipline-v1`;
- classification `evidence_driven_discipline_candidate`;
- `defaultEnabled=false`;
- capsule `454` UTF-8 bytes / conservative `152` tokens;
- capsule SHA-256
  `acca06bed7575442e3fd2779fdba9ecc237ee36440dde5d0e4a32e5e663a95b0`;
- independent QA `P0/P1/P2=0/0/0`;
- focused `26/26`, full source `1134/1134`, build `132/200`, release config
  `200`.

These are compatibility/source-fake facts, not empirical Writer quality or
token-savings evidence. CEO Flow does not vendor a live discipline schema or
enable CMMD R1 from these facts.

## Provenance

The profile is an independent implementation inspired by:

- <https://x.com/karpathy/status/2015883857489522876>
- <https://github.com/karpathy/autoresearch>
- <https://github.com/karpathy/autoresearch/blob/master/program.md>

It is not an official Karpathy skill. No community prompt text is copied into
CEO Flow.

## Acceptance Boundary

- No CEO model, reasoning, route, Goal, heartbeat, memory authority, or
  acceptance permission changed.
- Codex-internal execution remains available.
- CMMD remains optional; R1 remains blocked by its own readiness contract.
- The profile remains default-off until paired live Writer A/B evidence holds
  model, context, task, budget, baseline, and blind reviewer constant.
- Codex quota, Provider tokens, Codex review tokens, money, latency, retries,
  defects, and human intervention must remain separate metrics.

Static smoke is regression coverage only. It is not behavioral proof that a
future model will obey the profile or that the profile improves code.
