# External Execution Providers

Use this reference when Codex remains the CEO/reviewer/publisher while OpenClaw, ACP, MCP, a CLI agent, a webhook worker, or another agent host executes bounded work with a different model/provider.

## Architecture

CEO Flow separates four planes:

1. **Control plane — Codex CEO.** Owns user intent, Program Goal, architecture, task graph, provider selection, permissions, evidence requirements, and final reporting.
2. **Execution plane — external providers.** Performs bounded implementation, tests, research, documentation, or deterministic operations from a typed task envelope.
3. **Assurance plane — Codex or an independent qualified reviewer.** Verifies diffs, tests, artifacts, provenance, policy compliance, and product alignment. External completion is never self-acceptance.
4. **Publish plane — Codex CEO with user authorization.** Owns merge, release, GitHub push, public posting, payment, production deployment, and other externally consequential actions.

The provider boundary is platform-neutral. Public policy should name capabilities and contracts, not assume one vendor, country, operating system, shell, model catalog, or token price.

## Event-Triggered Operation

External execution does not require a Codex Goal, heartbeat, or polling loop. If Goals are paused, keep them paused. Use one of:

- immediate synchronous execution and harvest;
- provider push/notification when supported;
- explicit user-requested harvest;
- a configured workflow/task ledger with terminal-state notification.

Do not poll a provider task repeatedly when it exposes push completion or a durable task ledger. A task ledger records what ran; it is not automatically the scheduler or acceptance authority.

## Provider Capability Gate

Before dispatch, discover and record:

```text
Execution provider ID:
Platform/host:
Adapter/transport: cli-json | acp | mcp | file-exchange | webhook | other
Dispatch capability:
Status/receipt capability:
Cancel capability:
Workspace mode:
Available models/reasoning:
Usage/cost reporting:
Provenance/receipt support:
Push notification support:
Secrets/auth boundary:
Unsupported controls:
```

Do not infer that a provider supports worktrees, cancellation, receipts, model overrides, usage reporting, or push callbacks merely because another provider does.

## Risk And Capability Routing

Route by measured capability, task risk, evidence quality, latency, cost, and data policy — not by provider nationality or model prestige.

| Risk tier | Typical work | Default execution | Assurance |
| --- | --- | --- | --- |
| `R0 mechanical` | formatting, search, indexing, deterministic tests, simple file generation | external `fast` | scripted checks or sampled CEO review |
| `R1 bounded` | ordinary implementation, docs, standard UI changes, unit tests | external `balanced` | Codex diff/test review before accept |
| `R2 complex` | cross-module integration, difficult debugging, migrations, important UX | strongest adequate external route or Codex worker | independent high-capability review and targeted reruns |
| `R3 critical` | architecture, security/privacy, destructive data work, release readiness, public/commercial claims | Codex CEO/frontier plus qualified implementation as needed | neutral frontier audit; user boundary where required |

Use the cheapest route that can satisfy the contract. A lower-cost executor does not weaken tests, provenance, write-set limits, or review. Escalate capability only after evidence of insufficiency or when the risk tier requires it.

To reduce Codex token use, do not make Codex replay the executor's reasoning or raw transcript. Codex receives only the task envelope, receipt, diff/files, tests, artifacts, sourceRefs, usage summary, and residual risks. For R0 batches, review by deterministic gate plus bounded sampling; for R1-R3, inspect decision-grade evidence at the required gate.

## Typed Exchange

Every external run uses:

- `ceoflow.external_execution_task.v1` — immutable dispatch envelope;
- `ceoflow.external_execution_receipt.v1` — executor result candidate;
- task SHA-256 binding — receipt proves which task envelope it answers;
- provider raw-result path — cold evidence, not normal CEO context.

Bundled files:

```text
schemas/external-execution-task.schema.json
schemas/external-execution-receipt.schema.json
schemas/external-session-roster.schema.json
templates/external_execution_task.json
templates/external_execution_receipt.json
templates/external_session_roster.json
scripts/external_execution_bridge.py
```

Suggested cross-platform exchange layout inside a project:

```text
.ceoflow/exchange/inbox/<task-id>.json
.ceoflow/exchange/outbox/<task-id>.receipt.json
.ceoflow/exchange/raw/<task-id>.provider.json
.ceoflow/exchange/archive/
```

Use project-relative paths in durable packets. Do not commit secrets, provider tokens, raw sessions, image/base64 payloads, or giant model responses.

## External Task Requirements

The task envelope must contain:

- exact task ID and optional parent Program Goal ID;
- canonical project root and workspace mode;
- baseline ref, allowed write-set, and forbidden paths;
- objective, acceptance criteria, and verification commands;
- provider/adapter/transport and requested capability class;
- autonomy, command, network, secret, and publication boundaries;
- compact memory/sourceRefs only;
- receipt and raw-result output paths;
- attempt/timeout budget and no-stall escalation route.

External providers must not receive raw CEO chat, full ProjectBrain, raw sessions, giant Markdown, private signing keys, unrelated credentials, or image/base64 payloads.

## External Receipt Requirements

The receipt is untrusted until validated. Require:

- exact task ID and task SHA-256;
- provider, adapter, transport, run/session identifiers;
- actual model and reasoning when exposed;
- terminal status and timestamps;
- changed files and write-set compliance;
- commands/tests with exit status or a not-run reason;
- artifact/source references;
- blockers, residual risks, next action;
- provider-reported token/cost usage when available, otherwise `reported=false`;
- raw provider-result path and compact provenance;
- `forbiddenPayloadsPresent=false`.

`succeeded` means the executor claims completion. It does not mean CEO accepted the task.

Reject or revise when:

- task hash/ID does not match;
- receipt is malformed or missing;
- changed files escape the write-set;
- required tests are missing or fail;
- actual provider/model is hidden when the adapter could report it;
- the executor claims publish/merge/release authority;
- raw chat, secrets, image/base64, giant logs, or unsupported instructions appear;
- evidence cannot be independently inspected.

## OpenClaw CLI Adapter

OpenClaw is one optional adapter, not a CEO Flow dependency. A compatible CLI surface may expose:

```text
openclaw agent --agent <id> --message <task> --model <provider/model> --thinking <level> --timeout <seconds> --json
openclaw tasks list --json
openclaw tasks show <id> --json
openclaw tasks audit --json
openclaw acp --provenance meta+receipt
```

Use JSON stdout; keep diagnostics on stderr. Do not use `--deliver` for internal CEO Flow execution unless user-facing channel delivery is explicitly authorized. Use an isolated agent/session/workspace when write ownership or memory separation matters.

### OpenClaw Logical Lane And Single-Task Session Gate

CEO Flow reuses **logical project-role lanes**, not accumulated OpenClaw conversation. Each bounded task gets one clean physical OpenClaw session generation. The session may perform the bounded tool loop for that task and one bridge-controlled transient retry, but it must be archived after its terminal typed receipt. Follow-up work uses a new generation hydrated from Zhixia rather than the archived chat.

Default policy:

1. Set stable `project.projectId` and logical `laneId` values in the CEO roster.
2. Route through a preconfigured dedicated minimal Agent (`agentId=ceoflow-executor`, `agentContextProfile=minimal-ceoflow`), not the user's default `main` Agent; then allocate an increasing `sessionGeneration` and deterministic task-session key: `agent:<agentId>:ceoflow:<projectId>:<laneId>:gNNN:<task-slug>-<hash>`.
3. Set `sessionReusePolicy=single-task`, `sessionContextPolicy=single-task-zhixia`, and `archiveAfterReceipt=true`.
4. A new task ID, materially changed objective, model/provider change, trust-boundary change, or write-set change requires a new physical session generation. Never fork or copy the previous chat.
5. The external-session roster may contain several archived generations for one logical lane. Only one writable generation per project may be active.
6. The bridge archives every succeeded, failed, blocked, or exhausted-retry task session through official Gateway `sessions.patch`, verifies it in the archived list, and marks archive failure explicitly. An archived task session is never restored for follow-up work.

The OpenClaw executor must never create/spawn/route another session, Agent, subagent, or task. If the caller selected the wrong generation, it returns `blocked`. CEO Flow owns logical staffing; the bridge owns physical session registration and terminal archival.

This is deliberately not “one command per session.” One bounded task may use a small tool loop. It is also not “one project per permanent session.” The lease is exactly one acceptance-sized task slice.

### Provider Context Budget Gate

Zhixia remains the sole durable-memory authority. A fresh task session runs under the dedicated minimal `ceoflow-executor` Agent and receives only a compiled `ProviderTaskView`: project identity, bounded objective, write-set, verification, permissions, compact Zhixia packet/sourceRefs, return contract, and context limits. The user's default `main` Agent, full CEO control envelope, old OpenClaw transcript, unrelated Skills, giant diffs, raw logs, and prior task output do not enter provider context.

`minimal-ceoflow` is a verified configuration, not a label supplied by the task. Before any provider call, the bridge inspects the live `agents.list[]` entry and requires the single `ceoflow-external-executor` skill, bounded bootstrap/skill budgets, a task-sized `contextTokens` cap, the narrow `read/apply_patch/exec/process` tool allowlist, and the declared per-result cap. `write`, `edit`, `session_status`, browser, memory, session, spawn, and delegation tools are not part of the paid writer profile. Missing or broad configuration blocks locally with `providerCalled=false`; a broad tool surface reports `openclaw_executor_tool_allowlist_not_bounded`, while a missing/oversized context cap reports `openclaw_executor_task_context_cap_not_bounded`. Use `integrations/openclaw/agents/ceoflow-executor/openclaw-agent-config.fragment.json` as the canonical fragment.

Model availability must be resolved against the exact target Agent named by the task. An Agent-scoped provider credential may intentionally be absent from `main`; do not copy the key into `main` merely to satisfy a global catalog check. Require the model to be configured, allowed for the target Agent, backed by a usable target-Agent auth profile, and selected exactly when `modelRequirement=exact`. Record `openclaw_model_available_via_target_agent_auth` when this scoped route is used.

Hard defaults:

| Risk/task class | Initial compiled input | Provider calls | Cumulative input |
| --- | ---: | ---: | ---: |
| R0 read-only/mechanical | <= 12k | <= 2 | <= 25k |
| R1 bounded writer | <= 20k | <= 6 | <= 120k |
| R2 complex | <= 30k | <= 6 | <= 180k |
| R3 critical external slice | <= 30k | <= 4 | <= 180k |

Every task also sets a per-request context cap, separate uncached/cached cumulative limits, a gross session budget, a model-request count, a tool-call count, a per-result character cap, a cumulative tool-result cap, and gross TPM headroom. Cached input is **not** added to one request's context occupancy, but it does count toward cumulative cost/rate protection. Initial context means the compiled task prompt plus a conservative verified-harness allowance; a small `ProviderTaskView` alone is not proof that the OpenClaw system prompt is small.

Required hard-budget fields are `budgetGovernorPolicy=required`, `maxInitialInputTokens`, `maxInputTokensPerRequest`, `maxCumulativeUncachedInputTokens`, `maxCumulativeCachedInputTokens`, `maxCumulativeInputTokens`, `maxCumulativeGrossTokens`, `maxModelRequests`, `maxToolCalls`, `maxToolResultChars`, `maxCumulativeToolResultChars`, and `maxGrossTokensPerMinute`. `maxProviderCalls` remains a compatibility field and must equal `maxModelRequests`; legacy `toolOutputMaxChars` is not runtime enforcement evidence.

### OpenClaw Runtime Budget Fuse

Prompt instructions and post-run receipt rejection are not a hard budget. Paid OpenClaw writer execution therefore requires the local `ceoflow-budget-governor` plugin under `integrations/openclaw/plugins/ceoflow-budget-governor/`.

Before every attempt, the bridge must:

1. inspect the **live** Gateway runtime and verify all seven hooks (`before_agent_run`, `llm_input`, `model_call_started`, `llm_output`, `before_tool_call`, `after_tool_call`, `agent_end`) plus the `ceoflow.budget.arm/status/clear` methods;
2. verify `ceoflow-executor.contextTokens <= maxInputTokensPerRequest` and the minimal tool allowlist;
3. arm one immutable task hash/session key through `ceoflow.budget.arm` before invoking `openclaw agent`;
4. reject a paid run when the plugin is missing, inactive, unarmed, or returns incomplete telemetry.

The plugin counts by run ID, blocks excess tool calls before execution, conservatively blocks a tool when its maximum result could breach the remaining cumulative character budget, tracks model-call starts, separates uncached/cache-read/cache-write usage, maintains a rolling gross-TPM window, and calls OpenClaw's host `abortAgentHarnessRun(sessionId)` on a breach. Because OpenClaw 2026.7.1 exposes model-call and usage observations asynchronously, one violating provider call may already be in flight when cancellation lands; the fuse prevents an unbounded loop but must not be described as a zero-overshoot billing guarantee.

Default bounded writer values are:

```text
maxModelRequests: 4
maxToolCalls: 16
maxToolResultChars: 4000
maxCumulativeToolResultChars: 12000
maxInputTokensPerRequest / agent contextTokens: 25000
maxCumulativeUncachedInputTokens: 50000
maxCumulativeCachedInputTokens: 90000
maxCumulativeInputTokens: 90000
maxCumulativeGrossTokens: 110000
maxGrossTokensPerMinute: 300000
```

Every terminal receipt must carry a bridge-injected `budgetGovernor` card and a local `.ceoflow/exchange/runtime/*.budget.json` telemetry path. Unknown provider-call count (`external_provider_call_count_required`), missing telemetry (`openclaw_budget_governor_telemetry_missing`), missing required usage, incomplete telemetry, runtime mismatch, or `fuseTriggered=true` fails closed. `budget_fuse_triggered` is terminal for that task attempt: never perform the network retry, never silently switch model/provider, and never accept a useful-looking patch automatically.

Command/test exit status comes from `after_tool_call` execution trace. The bridge overwrites matching model-authored exit codes with host-observed values and rejects claimed commands that have no authoritative trace (`command_execution_trace_missing`). Full tool output remains out of the receipt and CEO context.

Tool results return paths, hashes, exit codes, test counts, and short tails/summaries. Full file bodies, broad diffs, build logs, OCR, screenshots, raw API bodies, and repeated task envelopes stay in local artifacts or the Codex assurance plane.

### Multi-Project Session Namespace Gate

Different CEO projects may share one OpenClaw installation, but they must never share an execution session. Before dispatch, bind the task to an exact project identity:

```text
projectId: globally unique, session-safe id
projectDisplayName: human-readable frontend group name
canonicalRoot: exact project root
projectIdentitySha256: SHA-256(projectId + normalized canonicalRoot)
ceoOwnerId: current project dispatch owner
sessionKey: agent:<agentId>:ceoflow:<projectId>:<laneId>:gNNN:<task-slug>-<hash>
sessionGeneration: positive integer
sessionContextPolicy: single-task-zhixia
archiveAfterReceipt: true
agentId / agentContextProfile: ceoflow-executor / minimal-ceoflow
```

The bridge rejects a changed root with a stale identity hash, a session key from another project, or a display/category name that is not project-scoped. Each project keeps its own roster at the declared project-relative `sessionRosterPath`; the roster records owner, lane, session key/id, frontend name, lifecycle, active task, write policy, model, usage, and last receipt. Do not use `agent:<id>:main`, a generic `Main Session`, or a session from another canonical root for CEO Flow execution.

One project has one dispatch owner at a time. A second CEO may audit read-only, but it must not issue a competing write task until ownership is transferred. Every task carries a bounded `dispatchLeaseId`. A session with an active run is busy, not another free worker. Different projects may run concurrently only when roots, write sets, ports, databases, build resources, provider quotas, and cost ceilings are independent.

Default session budget per active project:

- small project/task: one execution session;
- medium project: one implementation session plus one test/review session;
- large project: implementation plus test/review, with research added only when justified;
- paused project: archive its sessions; archived sessions consume no turns and cannot be reused silently.

### OpenClaw Frontend Visibility Gate

OpenClaw CLI execution must remain inspectable in the OpenClaw frontend. For OpenClaw tasks, default `frontendVisibility=required` and provide:

```text
sessionDisplayName: <Project Display Name> · <Role> · <TaskId>
sessionCategory: <Project Display Name>
archivedSessionPolicy: reject
nativeMemoryPolicy: forbid
```

Before model execution, the bridge uses official Gateway methods rather than editing `sessions.json`:

1. query active and archived rows through Gateway `sessions.list`; use its complete `label/category/archived/hasActiveRun/thinkingOptions` projection rather than the narrower `openclaw sessions` CLI list;
2. reject an archived, active/busy, wrong-project, or mismatched session;
3. create a missing session with `sessions.create` and its project-role label;
4. set label/category with `sessions.patch`;
5. query Gateway `sessions.list` again and verify the exact key, label, category, session id, supported thinking controls, and non-archived/non-running state;
6. only then send the task through `openclaw agent --session-key ...`.

If required frontend registration cannot be verified, return `openclaw_frontend_visibility_preflight_failed` before model execution. Never repair this by editing the OpenClaw session store directly, sending the task to `Main Session`, restoring an archived session silently, or using `--deliver` to an external channel. The receipt records exact project identity, frontend display name, session id/key, and `frontendVisible=true`; this proves routing metadata, not that a human watched the whole stream live.

OpenClaw sessions isolate conversation history, but sessions under one Agent still share Agent configuration, tools, and workspace bootstrap context. CEO Flow therefore requires the preconfigured minimal `ceoflow-executor` Agent and sets `nativeMemoryPolicy=forbid`; only the bounded Zhixia packet and explicit project sourceRefs may be used. OpenClaw cannot create or reconfigure that Agent from inside a task.

### Codex Subagent Redirection Gate

When CEO Flow would previously have used a Codex subagent/contractor for exploration, audit, verification, research, docs, tests, or bounded implementation, dispatch a typed OpenClaw external task instead. Reuse the approved logical project-role lane, allocate a clean task-session generation, and record both identities in the roster.

Do not call Codex `spawn_agent`, `multi_agent`, or equivalent project-execution subagent tools by default. If OpenClaw cannot satisfy the task, return `external_provider_unavailable`; do not silently substitute a Codex subagent. A higher-priority host contract may require a bounded `host-required-exception`, which must be recorded with its scope, model/permissions, evidence, and reason OpenClaw was not used.

This is direct star routing: `Codex CEO -> OpenClaw lane -> Codex CEO`. OpenClaw cannot spawn another OpenClaw Agent, Codex subagent, ACP child, or TaskFlow child unless a future user-approved workflow contract explicitly changes this boundary.

The optional OpenClaw execution skill is versioned at `integrations/openclaw/skills/ceoflow-external-executor/SKILL.md`. It enforces the execution/receipt boundary but does not provide transport, create sessions, select models, or grant publication authority.

### Local Model Gate — Disabled

CEO Flow does not currently route work to local models. `execution.localMode=true`, `--local`, isolated `.openclaw-ceoflow` launchers, and `ollama/<model>` routes are hard-blocked. Keep `localMode=false` and use an explicitly configured cloud/provider route such as the current OpenClaw Kimi K3 profile.

Do not choose a local model because it appears cheaper, more private, or available after a cloud failure. Do not start a local model service, download a model, copy cloud credentials into an isolated state, or switch from a configured cloud model to local execution without a future explicit user decision and a separate capability review.

Before dispatch, verify that the selected OpenClaw state exposes the requested model, provider authentication, required tool-call capability, compatible thinking controls, and required command tools. If preflight is unavailable or fails, block before model execution. Changing task IDs must not reset the same lane/objective/model retry budget.

OpenClaw may have a host-level fallback model list. Every task therefore declares `modelRequirement: preferred | exact`, `fallbackPolicy: deny | ceo-approved`, and `approvedFallbackModels`. The bridge reads `openclaw models status --json` before session/model execution. Configured fallbacks under `deny`, or a fallback outside the CEO-approved list, block with `openclaw_unapproved_model_fallbacks_configured` or `openclaw_configured_fallback_not_ceo_approved`. A task prompt saying “do not fallback” is not sufficient because host routing may occur before the model sees it. Do not set a thinking level until that exact model/surface advertises support; omit it rather than guessing `low/medium/high`.

The bundled bridge supports task/receipt validation, task hashing, prompt rendering, dry-run command generation, and explicitly authorized OpenClaw execution. Execution is never the default side effect.

### Kimi K3 Tier1 Route

For the current cloud profile, set `routingMode=auto-class`, `modelPolicy=kimi-k3-tier1-v1`, `requestedModel=null`, and `reasoningRequirement=preferred`. The bridge keeps the model on `moonshot/kimi-k3`, sends `off` for R0/ordinary R1 work, and sends `adaptive` for R1 research/review and R2/R3 bounded work.

Tier1's provider ceiling is not a dispatch target. CEO Flow's conservative envelope is at most three active K3 tasks across projects, one writer per project, 25k input per request, 90k cumulative input and four provider calls per task, and 300k gross task TPM. The default task template uses these smaller limits, denies local/GPT/cross-provider fallback, and preserves Codex acceptance/publish authority. When multiple tasks might overlap, estimate aggregate gross TPM before dispatch and delay a task rather than approaching the 2,000,000 TPM account ceiling.

### MiniMax Dynamic Route (Optional)

For the current MiniMax cloud profile, set `routingMode=auto-class`, `modelPolicy=minimax-validated-v1`, `requestedModel=null`, and `reasoningRequirement=preferred`. The bridge maps risk to `fast | balanced | frontier`, intersects the bundled policy with the live OpenClaw model catalog, and sends an explicit MiniMax thinking value:

- R0 and ordinary R1 execution: `off`;
- R1 research/review plus R2/R3: `adaptive`.

Only enabled, locally validated policy candidates may auto-activate. The current validated model is `minimax/MiniMax-M3`; `MiniMax-M2.7-highspeed` remains disabled until a controlled coding/tool/receipt probe passes. No local/Ollama route and no GPT/cross-provider fallback may be introduced by this policy.

Provider transport or explicit upstream-capacity failure is not a malformed worker receipt. Network boundary errors use `external_provider_network_error`; `temporarily overloaded`, `service unavailable`, `server busy`, `capacity exceeded`, and explicit HTTP 502/503/504 gateway failures use `external_provider_capacity_error`. Both produce schema-valid `status=failed` receipts with attempted model/thinking, raw-result path, independently observed changed files, and unknown usage. They may use the same bounded retry fuse. Authentication failures, permission failures, HTTP 429/rate-limit, quota exhaustion, ordinary process errors, and HTTP 500 are not reclassified as transient capacity failures. Do not label a classified provider failure `invalid_receipt`, switch provider/model, create another session, or block the whole Program Goal from one transient incident.

### Transient Provider Retry And Circuit Fuse

Use `networkRetryPolicy=bounded-backoff` only for classified transient network/connection or explicit upstream-capacity failures. The default cloud task contract permits exactly two total attempts: the original attempt plus one retry after 60 seconds. Keep the same task hash, immutable semantics, single-task session generation, provider, model, thinking route, fallback denial, permissions, and write-set. Attempt one keeps the declared evidence paths; attempt two uses immutable `.attempt-2` sibling raw/receipt files. Never overwrite consumed evidence or reset the budget by renaming an equivalent task. Archive only after the final attempt.

The model/tool/token budgets belong to the task, not each attempt. Before arming attempt two, subtract attempt-one runtime telemetry from the remaining model requests, tool calls, tool-result characters, uncached/cache input, cumulative input, and gross-session limits. Missing/incomplete attempt-one telemetry or an exhausted remainder blocks the retry locally.

Before and after every provider attempt, the bridge independently fingerprints git state and task-owned files. A retry is permitted only when:

- the failure is `external_provider_network_error`, not auth/quota/schema/permission/tool/write-set/verification failure;
- no OpenClaw run remains active in the reused session;
- the independent workspace fingerprint is unchanged;
- the task's two-attempt budget remains;
- the provider circuit is not open.

If a writer changed files before the network failure, do not rerun the consumed task. Ignore a contradictory provider claim such as `changedFiles=[]`; record the independently observed paths, mark the patch an untrusted partial candidate, harvest the actual diff, wait for provider recovery, and issue a new bounded correction/continuation task ID. Preserve every task/raw/receipt hash.

Two consecutive transient failures open the project-scoped provider circuit for five minutes by default. During cooldown, do not call the provider repeatedly and do not switch to GPT, another provider, a local model, or a new session. Continue safe portfolio steering, review, evidence inspection, docs, or another already-authorized independent product wave. After cooldown, one half-open probe may run; success closes the circuit, while failure reopens it. Provider cooldown is lane-local and is not sufficient reason to block the Program Goal.

The public receipt keeps `artifacts`, `sourceRefs`, `blockers`, and `residualRisks` as compact string arrays. The OpenClaw prompt shows valid/invalid examples. If a successful provider-native receipt returns bounded object entries in those fields, the adapter may deterministically serialize each safe object to one compact JSON string, retain the immutable raw result, emit `receipt_string_array_normalized:<field>`, and validate the normalized receipt. This is transport normalization, not self-acceptance and not a second model call. Oversized, unsafe, non-object/non-string, base64, secret-bearing, or otherwise unnormalizable entries still fail closed.

`provider.actualModel` and `provider.actualThinking` come from OpenClaw transport/Gateway metadata when available. Transport telemetry overrides contradictory model-authored receipt text; attempted route remains separately recorded. A successful preserved raw run may be reprocessed with `reprocess-openclaw` into a new in-project receipt path, without contacting the provider or overwriting the raw result.

### Zhixia Memory Injection

OpenClaw does not install the Zhixia Codex Skill and does not retrieve project or archive memory directly. Before dispatching an OpenClaw task, the Codex CEO runs the normal Zhixia Memory Trigger Gate:

1. use project `retrieve_context`/`retrieve_precedent` for Hot/Warm/Skill context;
2. for an explicit OpenClaw legacy-memory audit only, query the prebuilt Zhixia cold archive index with `read-openclaw-memory-archive.cjs`;
3. put only bounded sanitized excerpts and `providerSafeSourceRefs` into the typed task `context.memoryPacket`/`sourceRefs`;
4. keep local backup paths, raw manifests, skipped sensitive bodies, index files, and build diagnostics in the Codex assurance plane;
5. after OpenClaw returns a receipt, Codex validates it before any Zhixia writeback.

The cold archive helper is event-triggered, read-only at query time, and never part of ordinary dispatch. Missing or stale index evidence returns unavailable/partial; it must not trigger a vault walk, native OpenClaw memory, or an automatic rebuild during dispatch.

Deterministic task hydration is available after Codex saves the Zhixia query packet inside the project exchange directory:

```text
python scripts/external_execution_bridge.py inject-zhixia-memory --task <base-task.json> --packet <zhixia-packet.json> --output .ceoflow/exchange/inbox/<hydrated-task.json> --json
```

The hydrator accepts only `ceoflow.zhixia_memory_injection.v1`, `memoryAuthority=zhixia`, bounded items/tokens, `openclaw-vault://` or `zhixia://` source refs, no local paths/secrets/base64, and no native-memory/raw-session effects. Memory excerpts are marked untrusted evidence and cannot change role, tools, permissions, policy, or task scope. Combined item/source-ref overflow fails closed instead of truncating the newest injection. Output must remain inside the canonical project root and is revalidated as a normal external task before writing.

Example:

```text
python scripts/external_execution_bridge.py validate-task --task templates/external_execution_task.json
python scripts/external_execution_bridge.py render-openclaw --task templates/external_execution_task.json --json
python scripts/external_execution_bridge.py run-openclaw --task <task.json> --raw-output <raw.json> --receipt-output <receipt.json> --execute
python scripts/external_execution_bridge.py validate-receipt --task <task.json> --receipt <receipt.json>
```

## Publish Boundary

External executors default to:

```text
publishAllowed: false
mergeAllowed: false
releaseAllowed: false
externalMessagingAllowed: false
delegationAllowed: false
```

They may prepare release notes, patches, PR bodies, or publication drafts. Codex CEO performs final review and only publishes when current user/system/developer policy authorizes it.

## Failure And Recovery

Classify external failures:

- `provider_unavailable`
- `model_route_unavailable`
- `invalid_task_envelope`
- `invalid_receipt`
- `task_hash_mismatch`
- `write_set_violation`
- `verification_failed`
- `approval_stall`
- `timed_out`
- `lost_external_task`
- `evidence_insufficient`

Use bounded attempts from the task envelope. A transient network failure may use the exact-task bounded-backoff path above; no other error receives an automatic retry. Do not create an automatic cross-provider retry chain that can multiply spend. A provider/model change requires CEO review of capability, privacy, cost, and workspace state. Preserve every failed receipt/raw-result pointer and supersede the old task ID when semantics change.

## Acceptance Gate

Codex CEO accepts only after:

1. task and receipt validate;
2. task hash, provider identity, run identity, and sourceRefs match;
3. write-set and repo baseline remain safe;
4. required tests/artifacts are independently inspectable;
5. neutral review is complete for R1-R3 as required;
6. usage/cost is within policy or explicitly unknown and accepted;
7. no external executor performed a forbidden publish/merge/release action;
8. CEO records `accept | revise | block | supersede` and compact writeback evidence.
