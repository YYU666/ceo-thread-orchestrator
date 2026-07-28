# CEO Flow Stack Hardening Report — 2026-07-28

## Decision

`accept` for the CEO Flow changes in this slice.

This decision does not accept Zhixia remediation or CMMD R1. Zhixia work was
dispatched to its existing CEO task. CMMD was not modified and R1 remains
fail-closed.

## Scope

Implemented the CEO Flow fixes that do not depend on CMMD's eventual stable R1
contract:

1. Added a read-only `ceoflow.stack_doctor.v1` script.
2. Added stable canonical/worktree `ProjectIdentityEnvelope` rules.
3. Made missing sidecars, stale packets, and duplicate item IDs explicit
   provider diagnostics.
4. Defined `fallback_stale` as advisory-only; it cannot support current-state or
   recovery-ready claims.
5. Replaced the default long task-card inventory with `minimal`, `standard`, and
   future-gated `R1` profiles plus templates.
6. Added an explicit behavioral Codex forward-test contract. Static smoke
   remains policy-text coverage only.
7. Kept Codex-internal multi-thread execution ready while leaving CMMD R1
   blocked until stable accepted schemas and real bounded writer evidence exist.

## Real Stack Doctor Finding

Command:

```powershell
python skills\ceo-thread-orchestrator\scripts\stack_doctor.py --project-root . --canonical-root . --json
```

Observed:

- CEO Flow source and installed Skill hashes matched after synchronization.
- Zhixia helper reported `memoryMode=layered`.
- Memory Fact sidecar: `missing`.
- Memory Core sidecar: `missing`.
- Returned source refs were dated 2026-06-19 and exceeded the seven-day
  freshness budget.
- Effective result: `fallback_stale`.
- `currentStateClaimAllowed=false`.
- `recoveryReadyClaimAllowed=false`.
- CMMD control was not configured for this doctor run; CMMD R0 remained
  unverified and R1 blocked. No CMMD process/model call was started.

This reproduces the audit's key memory-freshness defect and demonstrates CEO
Flow's new fail-closed interpretation before Zhixia itself is repaired.

## Verification

- Python unit/adversarial tests: `28/28` passed.
- Static policy smoke: `75/75` passed. This is not behavioral proof.
- CMMD vendored schema snapshot validation: passed.
- Pipeline validator: passed (`4` lanes).
- Typed implementation handoff validator: passed.
- Review handoff validator: passed.
- Release-state check: passed (`0.2.8-dev`).
- Skill validator: passed.
- Plugin validator: passed.
- Installed/source Skill tree: `40/40` files, identical hash at validation.

## Behavioral Evidence Boundary

The repository now defines the required forward loop, but this slice did not
claim a live end-to-end success across all three products. That claim requires:

```text
Codex -> CEO Flow -> Zhixia retrieve receipt -> bounded execution
-> CEO evidence decision -> Zhixia writeback receipt -> fresh-task retrieval
```

Zhixia must first provide real headless writeback/receipt support. CMMD R1 must
first publish a stable accepted contract and real writer-readiness evidence.

## Residual Risks

1. Zhixia currently remains the source of the stale/fresh and missing-sidecar
   defects; CEO Flow can diagnose and fail closed but cannot repair that
   provider from this repository.
2. The doctor only reports CMMD control visibility. It deliberately does not
   start or probe CMMD and cannot establish R0/R1 runtime readiness by itself.
3. A real fresh-thread behavioral forward test remains required after the
   Zhixia headless lifecycle is accepted.
