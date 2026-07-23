# CEO Flow OpenClaw Kimi K3 Single-Task Context Probe

Date: 2026-07-21

Branch: `openclaw-cost-efficient-execution`
Decision: `revise` for the observed run; executor hardening completed afterward.

## Purpose

Measure one small deterministic RGS code-reasoning task under the single-task OpenClaw session policy without editing product files, using tools, retrying, falling back, or restoring the RGS Goal.

## Route and limits

- Model: `moonshot/kimi-k3`
- Thinking: `off`
- Provider calls: 1
- Fallback: denied and unused
- Physical session: one fresh generation, archived after receipt
- Initial/per-request input limit: 12,000 tokens
- Cumulative input limit: 25,000 tokens
- Gross TPM limit: 100,000 tokens
- Screenshot account limits used for comparison: 500,000 TPM / 1,500,000 TPD

## Observed result

K3 correctly diagnosed an RGS intent-classification defect: creation verbs and entity targets were joined in one OR list, so destructive or inspection wording could route to `createEntity`. It proposed a positive conjunction (creation intent AND entity target), preserved the registered-tool check, and supplied focused bilingual/adversarial tests.

Quality review:

- Correctness: 9/10
- Code quality: 8/10; substring matching still has boundary risks
- Test quality: 9/10
- Instruction adherence: 10/10
- Workspace mutation: none
- Network/auth/rate-limit failure: none

Usage telemetry:

| Metric | Observed |
| --- | ---: |
| Uncached input | 19,443 |
| Cache read | 5,888 |
| Gross prompt input | 25,331 |
| Output | 1,153 |
| Total | 26,484 |
| Duration | 38,836 ms |
| Provider calls | 1 |

The run stayed far below the account TPM/TPD limits and used about 3% of the earlier 831,830-input-token failure. However, it exceeded the task's 12,000 per-request limit and the 25,000 cumulative limit by 331 gross input tokens. The model answer was good, but the contract was not met.

## Root cause

The physical session was fresh, but the Agent was only minimal by convention. OpenClaw still injected approximately 8.3k characters of unrelated Skill catalog entries and 52.8k characters of global tool schemas. ProviderTaskView size alone therefore underestimated actual prompt cost.

## Hardening applied after the run

1. Added a canonical per-agent config fragment that allows only `ceoflow-external-executor`, caps Skill/bootstrap/tool-result context, and exposes only the bounded coding tools.
2. Added a live preflight that reads `agents.list[]` and blocks locally with `providerCalled=false` when the Agent profile is broad or missing.
3. Added a conservative harness allowance to initial-context preflight.
4. Changed receipt usage accounting to count cached input in gross prompt input and expose last-request, cumulative, total, and provider-call telemetry.
5. Added post-run errors for per-request, cumulative, and provider-call overrun.

Offline replay of this probe under the corrected receipt logic produces:

- `external_provider_per_request_context_budget_exceeded`
- `external_provider_cumulative_context_budget_exceeded`

The live Agent configuration now passes the zero-model profile preflight at an estimated 9,846 initial tokens for the same 12,000-token envelope. No second paid provider probe was run, preserving the one-probe instruction.

## Suitability

- R0 read-only reasoning: suitable, behind the new profile and receipt gates.
- R1 bounded coding: candidate only; require a later controlled writer probe with actual tests and the hardened profile.
- R2/R3 acceptance or publishing: not delegated; Codex CEO/reviewer remains the decision and publish authority.
