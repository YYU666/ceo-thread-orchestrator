# OpenClaw Cost-Efficient Execution Branch

## Why This Branch Exists

CEO Flow originally coordinated execution inside Codex through visible implementation/review lanes and host-provided worker capabilities. That remains the canonical workflow on the `main` branch.

After long-running projects showed high premium-token consumption for routine coding, tests, bounded research, and repeated provider recovery, this branch was created as an optional cost-oriented variant. It keeps Codex responsible for the work where stronger judgment matters most, while allowing OpenClaw to execute bounded tasks through a separately configured lower-cost model provider.

This is not a claim that every external model is cheaper or equally capable. Actual cost, latency, privacy, reliability, tool support, and quality depend on the user's OpenClaw provider and plan. CEO Flow therefore routes by task risk and validates evidence rather than trusting model branding.

## Branch Relationship

| Branch | Default execution model |
| --- | --- |
| `main` | Original Codex-internal CEO Flow and host lane workflow |
| `openclaw-cost-efficient-execution` | Codex CEO/assurance/publish plane plus OpenClaw external execution lanes |

The OpenClaw branch does not overwrite or redefine `main`. Users who want the original all-Codex workflow should install from `main`. Users who want the external-execution variant should explicitly install from this branch.

## Responsibility Split

### Codex remains responsible for

- user-facing CEO identity and Program Goal continuity;
- PRD, architecture, decomposition, staffing, and model-route policy;
- compact Zhixia/Memory Runtime retrieval and source references;
- write-set, repo baseline, privacy, visual-payload, and publication gates;
- independent diff/test/artifact review;
- `accept | revise | block | supersede` decisions;
- commit, push, release, and external publication when authorized.

### OpenClaw may perform

- bounded implementation inside an explicit write-set;
- focused tests and build verification;
- bounded research, docs, and read-only review;
- routine or mechanical tasks routed to an adequate lower-cost model;
- complex external execution only when Codex retains the acceptance decision.

OpenClaw cannot accept its own work, publish, merge, release, change the CEO model/reasoning, spawn child agents, use native global memory as project memory, or silently switch providers/models.

## Session And Cost Discipline

- Logical lanes are namespaced by exact project and role. Each bounded task receives a clean physical generation: `agent:<agentId>:ceoflow:<projectId>:<laneId>:gNNN:<task-slug>-<hash>`.
- Related tasks reuse the logical lane and Zhixia continuity, not the previous OpenClaw chat. Each terminal task session is archived through the Gateway and follow-up work starts in a new generation.
- Provider context is compiled into a compact `ProviderTaskView` with hard initial/per-request/cumulative token, call-count, TPM, and tool-output budgets.
- External execution uses the isolated `ceoflow-executor` Agent with `agentContextProfile=minimal-ceoflow`; the default personal `main` Agent is not a CEO Flow execution surface.
- `minimal-ceoflow` must match the checked-in per-agent config fragment. A dedicated workspace without explicit Skill/tool allowlists is still context-bloated and is rejected before a provider call.
- Single-task receipts count cache reads in gross input; a correct answer that exceeds per-request/cumulative/call budgets remains `revise`, not `accept`.
- One project defaults to one active writer plus optional read-only test/review lanes.
- Routine work uses the smallest validated adequate route; higher-risk work receives stronger reasoning and Codex assurance.
- Provider usage is recorded when available. Unknown token/cost remains unknown rather than being invented.
- Raw reasoning transcripts are not replayed into Codex; harvest uses typed receipts, diffs, tests, artifact paths, and source refs.

## Current Kimi K3 Tier1 Policy

The current default uses `moonshot/kimi-k3` through the dedicated minimal OpenClaw executor:

- R0 and ordinary R1 execution: thinking `off`;
- R1 research/review and R2/R3 bounded execution: thinking `adaptive`;
- no more than three active K3 tasks across projects and one writer per project;
- per task: 25k input/request, 90k cumulative input, four provider calls, 300k gross TPM;
- GPT, cross-provider, and local/Ollama fallback: denied by default;
- Codex remains the acceptance, release, and publishing authority.

This stays intentionally below the provider Tier1 ceiling of 50 concurrency, 200 RPM, and 2,000,000 TPM. MiniMax remains an optional reviewed policy, while DeepSeek V4 remains a manual probe candidate and is not an automatic fallback.

## Transient Network Recovery

A single classified provider connection failure no longer stops the project:

1. preserve a typed failure receipt and immutable raw evidence;
2. independently verify that the task-owned workspace did not change;
3. wait 60 seconds;
4. retry once using the same task semantics, OpenClaw session, model, thinking, and fallback policy;
5. after two transient failures, open a five-minute project/provider circuit and continue safe portfolio/review work;
6. allow one half-open probe after cooldown.

If a writer changed files before disconnecting, the old task is not rerun. Codex harvests the partial diff as untrusted evidence and issues a new bounded correction task. Provider cooldown is lane-local and does not by itself block the Program Goal.

## Local Data And Publication Boundary

The following remain local and must not be committed:

- `.ceoflow/` task exchange, raw provider results, receipts, session rosters, and circuit state;
- `.codex-knowledge/` project memory exports;
- raw Codex/OpenClaw sessions, credentials, images/base64, and private project artifacts.

Public examples and docs contain schemas and generic paths only. OpenClaw execution remains opt-in and requires explicit `--execute`; validation and rendering are side-effect free.

## Installation Choice

Original Codex-internal workflow:

```text
https://github.com/YYU666/ceo-thread-orchestrator/tree/main
```

OpenClaw cost-efficient execution variant:

```text
https://github.com/YYU666/ceo-thread-orchestrator/tree/openclaw-cost-efficient-execution
```

The OpenClaw-side execution contract is bundled at `integrations/openclaw/skills/ceoflow-external-executor/SKILL.md`. OpenClaw provider credentials and model configuration are user-managed and are never committed by this repository.

## Validation Evidence

Before publication this branch is checked with:

- Python unit and adversarial validator tests;
- static smoke-policy coverage;
- bundled task, receipt, pipeline, and handoff validation;
- Codex skill validator and plugin validator;
- privacy/path scan;
- installed-skill hash synchronization checks.

These checks validate contracts and deterministic guardrails. They do not claim that every third-party provider is always online or that static smoke coverage is a live LLM behavior benchmark.
