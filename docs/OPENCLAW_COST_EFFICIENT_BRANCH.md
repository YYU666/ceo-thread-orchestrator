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

- Sessions are namespaced by exact project and role: `agent:<agentId>:ceoflow:<projectId>:<laneId>`.
- Related tasks reuse the same frontend-visible project-role session instead of creating a new session per task.
- One project defaults to one active writer plus optional read-only test/review lanes.
- Routine work uses the smallest validated adequate route; higher-risk work receives stronger reasoning and Codex assurance.
- Provider usage is recorded when available. Unknown token/cost remains unknown rather than being invented.
- Raw reasoning transcripts are not replayed into Codex; harvest uses typed receipts, diffs, tests, artifact paths, and source refs.

## Current MiniMax Policy

The bundled validated policy currently uses `minimax/MiniMax-M3` through OpenClaw:

- R0 and ordinary R1 execution: thinking `off`;
- R1 research/review and R2/R3 bounded execution: thinking `adaptive`;
- GPT, cross-provider, and local/Ollama fallback: denied by default;
- unvalidated models remain disabled until a controlled capability probe passes.

Users may configure another provider later, but a provider/model change requires a reviewed policy update rather than silent fallback.

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
