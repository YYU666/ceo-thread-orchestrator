# CEO Flow MiniMax Dynamic Routing Smoke — 2026-07-21

## Decision

`accept` for policy/bridge integration; `revise` remains for provider network reliability and additional-model activation.

## Scope

- Keep Codex as CEO/control/review/publish plane.
- Dynamically assign OpenClaw MiniMax execution model/thinking by risk.
- Do not change the Codex CEO model or reasoning.
- Do not enable local/Ollama execution.
- Do not restore GPT or cross-provider fallback.
- Classify MiniMax network failures as provider failures, not malformed receipts.

## Official capability evidence

- MiniMax-M3 supports explicit `thinking: disabled` and `thinking: adaptive`; the OpenClaw surface represents these as `off` and `adaptive`.
- MiniMax-M2.x thinking cannot be disabled.
- MiniMax documents M3, M2.7, and M2.7-highspeed; appearing in the catalog is not sufficient for CEO Flow activation.
- Token Plan Plus is described as approximately 3–4 Agents, with RPM/TPM and dynamic high-traffic throttling. This is not a guaranteed simultaneous-concurrency SLA.

Sources:

- https://platform.minimaxi.com/docs/guides/text-generation
- https://platform.minimaxi.com/docs/api-reference/text-anthropic-api
- https://platform.minimaxi.com/docs/token-plan/openclaw
- https://platform.minimaxi.com/docs/token-plan/faq

## Implemented route

| Task importance | Effective class | Active model | Thinking | Required assurance |
| --- | --- | --- | --- | --- |
| R0 mechanical | fast | MiniMax-M3 | off | deterministic checks / bounded sampling |
| R1 bounded implementation/docs/test | balanced | MiniMax-M3 | off | Codex diff/test review |
| R1 research/review | balanced | MiniMax-M3 | adaptive | source/evidence challenge |
| R2 complex | frontier | MiniMax-M3 | adaptive | independent Codex review |
| R3 critical | frontier external execution only when bounded | MiniMax-M3 | adaptive | Codex owns decision + neutral audit |

`MiniMax-M2.7-highspeed` is present as a disabled candidate for future fast lanes. It cannot auto-activate until OpenClaw availability, tool calling, typed receipt integrity, latency, coding quality, and reliability pass a controlled probe.

## Live read-only preflight

OpenClaw version: `2026.7.1-2`.

Observed configuration:

- default/resolved model: `minimax/MiniMax-M3`;
- configured fallbacks: empty;
- live catalog: M3 available;
- dynamic route: `auto-class -> balanced -> MiniMax-M3 -> off`;
- route source: `validated_model_policy`;
- errors/warnings: none.

No model generation was invoked by this smoke.

## Network failure correction

The observed RGS error `LLM request failed: network connection error` occurs after frontend/Gateway/model-route preflight. The bridge now emits:

- receipt status: `failed`;
- blocker: `external_provider_network_error`;
- attempted model/thinking;
- raw-result path;
- usage unknown when provider reports none;
- no automatic retry, provider switch, model switch, or new session.

`invalid_receipt` is retained only for an unclassified completed process that fails to return the typed receipt contract.

## Verification

- Python compile: pass.
- External bridge unit tests: 24/24 pass.
- Full public validator suite: 31/31 pass.
- Smoke eval: 74/74 pass.
- Task template/schema validation: pass.
- Skill validator: pass.
- Plugin validator: pass.
- Installed Skill validator: pass.
- Repo/installed key-file SHA-256 comparison: all matched.
- `git diff --check`: pass (line-ending notices only).

## Residual risks

1. MiniMax provider network reliability is not proven by this non-generating smoke.
2. M2.7-highspeed remains deliberately inactive.
3. Provider usage accounting can still be absent on failed runs; no usage is inferred.
4. This change does not promise Plus-plan concurrency beyond MiniMax's documented approximate guidance and dynamic throttling.

## Follow-up: first successful adaptive run

RGS task `RGS-E2B-BROWSER-EVIDENCE-PREFLIGHT-004` subsequently proved the provider path:

- provider exit `0` with no network error;
- session reused, one active run;
- MiniMax-M3 + adaptive request shaping;
- input `78,018`, output `4,226` provider-reported tokens;
- `changedFiles=[]`.

The initial receipt was revised because `artifacts`, `sourceRefs`, and `blockers` used object arrays and the model-authored receipt contradicted Gateway telemetry with `actualThinking=off`. The bridge now:

1. requires string-only array shapes in both prompt and OpenClaw executor Skill;
2. deterministically serializes bounded safe object entries without a second provider call;
3. reads nested `result.meta.agentMeta/requestShaping` telemetry and overrides self-reported model/thinking;
4. provides `reprocess-openclaw` for offline recovery from preserved raw output.

Offline regression against the immutable 004 raw result produced `actualThinking=adaptive`, string-only receipt fields, provider usage `78,018/4,226`, and zero validation errors.
