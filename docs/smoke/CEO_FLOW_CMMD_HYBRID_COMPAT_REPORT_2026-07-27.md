# CEO Flow CMMD Hybrid Compatibility Report

Date: 2026-07-27

Branch: `cmmd-hybrid-execution`

Decision: `accept` for the CEO Flow integration contract

CMMD runtime claim: R0 experimental admission only; production/R1 not claimed

## Objective

Replace OpenClaw as CEO Flow's forward external-execution design with an
optional Codex CEO + CMMD hybrid path while preserving Codex internal
multi-thread execution as the native and explicitly selectable path.

## Landed Changes

- Created an independent branch from `main`; neither `main` nor the historical
  `openclaw-cost-efficient-execution` branch was rewritten.
- Added `references/cmmd-execution.md` with execution-surface, readiness,
  Context View, stable-role/isolated-run, R0/R1, lease, budget, receipt,
  acceptance, and no-silent-fallback gates.
- Kept `codex-internal` as the default when CMMD is not enabled and as an
  explicit per-project/per-task choice.
- Marked OpenClaw as historical-only: no default, probe, retry, or fallback.
- Vendored CMMD v2 task/receipt, authorization lease, and Context View schemas
  from the recorded CMMD snapshot, with SHA-256 provenance.
- Added CEO Flow's typed `ceoflow.cmmd_readiness_evidence.v1` packet, bound to
  project identity, Provider/model, risk tier, contract hashes, expiry, and
  sourceRefs.
- Added `validate_cmmd_exchange.py` with full vendored JSON-Schema checks plus
  task/project/Context commitments, readiness, source ranges, route, mutation,
  lease, budget arithmetic, Host evidence, cleanup, and visual-payload checks.
- Explicitly blocked R1 because the bundled `cmmd.context_view.v1` is R0-only.
  R1 policy is future-gated until an R1-capable Context View and production
  evidence are accepted.
- Clarified that the current task contract binds Provider/model but not exact
  reasoning; exact reasoning requirements fail closed rather than being
  described as enforced.

## Verification

| Check | Result |
| --- | --- |
| Python unit/adversarial tests | `22/22 PASS` |
| Static CEO Flow smoke cases | `70/70 PASS` |
| CMMD schema snapshot hashes | `PASS` |
| Pipeline template validator | `PASS` |
| Implementation/review handoff validators | `PASS` |
| Release-state check | `PASS` (`0.2.7-dev`) |
| Skill validator | `PASS` |
| Plugin validator | `PASS` |
| `git diff --check` | `PASS` |
| Credential/private-key/embedded data-image scan | `PASS`, no matches |
| Repository Skill vs installed Skill hashes | `33/33 files identical` |

## Independent Review

The first independent read-only review returned `revise` for false-admission
risks: missing full schema validation, unbound/expired leases, incomplete
mutation checks, R1 overclaiming, and reasoning-contract ambiguity.

The second review returned `revise` for an untyped readiness label, missing
budget reconciliation, and incomplete Context View semantic/size checks.

After bounded corrections and adversarial tests, the final independent
re-review returned `ACCEPT` with no remaining P0/P1/P2 finding in its bounded
scope.

## Residual Boundary

This report accepts CEO Flow's early integration and fail-closed contract. It
does not claim CMMD production acceptance, R1 writer readiness, package/restart
recovery readiness, or general Provider quality. Before those claims, CEO Flow
must synchronize a reviewed live CMMD contract and new readiness evidence.
