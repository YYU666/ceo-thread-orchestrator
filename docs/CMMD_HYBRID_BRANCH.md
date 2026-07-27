# CMMD Hybrid Execution Branch

## Why This Branch Exists

The earlier external-execution experiment used OpenClaw to run lower-cost model
tasks. Real project trials showed that its accumulated session context and
internal multi-turn tool loop could consume far more tokens than the bounded CEO
task implied. Correcting that behavior required maintaining an external runtime
whose budget controls were outside CEO Flow's direct contract.

This branch takes a different approach:

- keep the proven Codex internal multi-thread workflow;
- keep Codex as the single user-facing CEO, reviewer, and publisher;
- make Codex Multi-Model Desktop (CMMD) an optional typed execution Provider;
- require a fresh bounded Context View and isolated run for every task;
- require Host-owned usage, diff, command, test, lease, and cleanup evidence;
- preserve stable project-role threads without reusing Provider conversation
  history;
- fail closed instead of silently falling back between executors or models.

## Branch Preservation

The intended public branch layout is:

| Branch | Purpose |
| --- | --- |
| `main` | Original/current Codex internal Core Team workflow. |
| `openclaw-cost-efficient-execution` | Historical OpenClaw cost experiment and evidence. |
| `cmmd-hybrid-execution` | Codex internal Core Team plus optional CMMD external execution. |

The CMMD branch does not delete, rewrite, or replace the internal Codex path.
Users can explicitly choose internal Codex multi-thread execution at project or
task level.

## Current CMMD Readiness Boundary

CEO Flow must distinguish:

```text
live_smoke_ready
production_acceptance_ready
R0 read-only
R1 bounded writer
```

At the compatibility snapshot used for this branch, CMMD had accepted evidence
for a frozen Kimi K3 R0 diagnostic smoke but had not yet earned a general
production-acceptance claim. R1 production/restart/package evidence remained a
separate gate. CEO Flow therefore ships the integration contract early without
claiming that every CMMD run is production-ready.

The bundled `cmmd.context_view.v1` is R0-only. Consequently this branch admits
only matching R0 experiments today. R1 policy is retained as a future contract
gate, but R1 dispatch remains blocked until both an R1-capable Context View and
production acceptance evidence are reviewed and synchronized.

CMMD is the authority for its live schemas and readiness evidence. The vendored
schema snapshot lets CEO Flow detect incompatibility before dispatch; it does
not freeze CMMD development or allow CEO Flow to reinterpret a changed schema.

## Safety And Cost Boundary

- No OpenClaw default, probe, retry, or fallback.
- No Ollama requirement or local-runtime installation behavior.
- No external worker may modify the CEO model, reasoning, Goal, scope, quality
  gate, permission policy, or publication state.
- No CMMD run can accept itself.
- No R0 run can write.
- No R1 run can write without a matching Host-issued authorization lease,
  explicit write-set, command allowlist, and Host-observed verification.
- No visible project-role thread is archived merely because one run ended.
- No raw CEO chat, complete thread history, raw session, full ProjectBrain,
  image/base64 payload, secret, or giant memory file enters the Provider view.

## Compatibility Snapshot

The branch vendors these live-target contracts under
`skills/ceo-thread-orchestrator/schemas/cmmd/`:

- `ceoflow.external_execution_task.v2`
- `ceoflow.external_execution_receipt.v2`
- `ceoflow.authorization_lease.v1`
- `cmmd.context_view.v1`

Their source revision and SHA-256 values are recorded in
`schemas/cmmd/SCHEMA_SNAPSHOT.md`. The fail-closed
`scripts/validate_cmmd_exchange.py` uses the development `jsonschema`
dependency plus CEO-side identity, Context View, readiness, route, risk, lease,
budget, evidence, and cleanup checks. Passing it means only
`candidate_for_ceo_review`; it never means `accept`.
