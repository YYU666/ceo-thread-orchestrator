# CEO Flow OpenClaw DeepSeek V4 Flash Probe

Date: 2026-07-22

Route: `deepseek/deepseek-v4-flash` through `ceoflow-executor`
Decision: connection/cost baseline `accept`; automatic writer routing `revise`.

## Configuration

- The API key was ingested through an Agent-scoped OpenClaw auth profile and was not written to the CEO Flow repository, task envelope, receipt, or memory.
- The temporary plaintext key file was deleted after auth verification.
- Legacy invalid DeepSeek custom routes were removed.
- Official models registered: `deepseek-v4-flash` and `deepseek-v4-pro`.
- Fallback remained empty; local models remained disabled.

Official model metadata was checked against [DeepSeek API pricing](https://api-docs.deepseek.com/quick_start/pricing): both V4 variants support thinking/non-thinking modes, tool calls, 1M context, and up to 384K output. The probe used Flash with thinking off.

## Probe contract

- One fresh physical Session, archived after receipt.
- One provider request, no retry, no fallback.
- Read-only deterministic TypeScript defect review.
- No tools, shell, repository reads, tests, network access, or file mutation by the model.
- Initial/per-request input limit: 12,000 tokens.
- Cumulative input limit: 20,000 tokens.
- Gross TPM limit: 50,000 tokens.

## Result

| Metric | Observed |
| --- | ---: |
| Gross input | 7,627 |
| Cached input | 0 |
| Output | 1,736 |
| Total | 9,363 |
| Provider calls | 1 |
| Duration | 17,727 ms |
| Estimated provider cost | USD 0.00155386 |
| Changed files | 0 |

The model correctly identified the core OR-versus-AND intent-classification defect and proposed separate creation-intent and entity-target gates. It also preserved the registered-tool check and supplied focused tests.

Residual quality issues:

- It proposed removing the scene-term guard without fully proving that mixed entity/scene requests remain safe.
- Chinese examples in the returned text were mojibake, so multilingual output transport is not yet accepted.
- This was read-only reasoning, not a tool-using writer probe.

Suitability:

- R0 read-only analysis: accepted.
- R1 bounded review/research: candidate with Codex verification.
- R1 writer or higher: not auto-enabled until a controlled tool/test probe passes.
- V4 Pro: configured but untested; it must not be claimed validated or automatically selected yet.

## Harness finding

The first preflight correctly blocked before provider execution because the global catalog used `main` auth while the credential was intentionally scoped to `ceoflow-executor`. The bridge was corrected and unit-tested so pinned model availability now uses the target Agent's allowed models and auth profile. No key was copied to `main`.
