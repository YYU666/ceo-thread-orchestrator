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

### OpenClaw Project Session Gate

OpenClaw sessions are reusable execution lanes, not disposable threads to create per task. Before dispatch, resolve the project identity and inspect the external-session roster.

Default policy:

1. Set a stable `project.projectId` and lane id.
2. Reuse a deterministic key: `agent:<agentId>:ceoflow:<projectId>:<laneId>`.
3. Use `sessionReusePolicy: reuse-project-role` for normal follow-up tasks. A new task ID does not create a new session.
4. Default to one OpenClaw implementation session per CEO project. Add a second role session only when write ownership, test isolation, or a genuinely independent wave requires it. The staffing plan, not the executor, owns the approved session count.
5. Reuse only when project id, canonical root, lane role, workspace mode, trust boundary, and write ownership still match. Record the key, actual session id, current task, model, status, and last accepted receipt in the external-session roster.
6. Use `fresh-isolated` only for a recorded reason: broken/stale session, role contamination, context pressure, project/workspace/trust change, conflicting write ownership, or explicit isolation. Mark the old session superseded; do not fork/copy its raw conversation.

The OpenClaw executor must never create/spawn/route another session, Agent, subagent, or task. If the caller selected the wrong session, it returns `blocked`. CEO Flow updates the roster and chooses reuse or replacement.

Session reuse is not permission reuse. Every turn still receives a new immutable task envelope, task hash, write-set, verification contract, and current memory packet. Previous session instructions cannot expand the newest envelope.

### Multi-Project Session Namespace Gate

Different CEO projects may share one OpenClaw installation, but they must never share an execution session. Before dispatch, bind the task to an exact project identity:

```text
projectId: globally unique, session-safe id
projectDisplayName: human-readable frontend group name
canonicalRoot: exact project root
projectIdentitySha256: SHA-256(projectId + normalized canonicalRoot)
ceoOwnerId: current project dispatch owner
sessionKey: agent:<agentId>:ceoflow:<projectId>:<laneId>
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
sessionDisplayName: <Project Display Name> · <Role>
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

OpenClaw sessions isolate conversation history, but sessions under one Agent may still share Agent configuration, tools, or native workspace memory. CEO Flow therefore sets `nativeMemoryPolicy=forbid`; only the bounded Zhixia packet and explicit project sourceRefs may be used. Sensitive projects may use a preconfigured dedicated OpenClaw Agent, but OpenClaw cannot create that Agent from inside a task.

### Codex Subagent Redirection Gate

When CEO Flow would previously have used a Codex subagent/contractor for exploration, audit, verification, research, docs, tests, or bounded implementation, dispatch a typed OpenClaw external task instead. Reuse the approved project-role session and record it in the lane roster.

Do not call Codex `spawn_agent`, `multi_agent`, or equivalent project-execution subagent tools by default. If OpenClaw cannot satisfy the task, return `external_provider_unavailable`; do not silently substitute a Codex subagent. A higher-priority host contract may require a bounded `host-required-exception`, which must be recorded with its scope, model/permissions, evidence, and reason OpenClaw was not used.

This is direct star routing: `Codex CEO -> OpenClaw lane -> Codex CEO`. OpenClaw cannot spawn another OpenClaw Agent, Codex subagent, ACP child, or TaskFlow child unless a future user-approved workflow contract explicitly changes this boundary.

The optional OpenClaw execution skill is versioned at `integrations/openclaw/skills/ceoflow-external-executor/SKILL.md`. It enforces the execution/receipt boundary but does not provide transport, create sessions, select models, or grant publication authority.

### Local Model Gate — Disabled

CEO Flow does not currently route work to local models. `execution.localMode=true`, `--local`, isolated `.openclaw-ceoflow` launchers, and `ollama/<model>` routes are hard-blocked. Keep `localMode=false` and use an explicitly configured cloud/provider route such as the current OpenClaw MiniMax profile.

Do not choose a local model because it appears cheaper, more private, or available after a cloud failure. Do not start a local model service, download a model, copy cloud credentials into an isolated state, or switch from a configured cloud model to local execution without a future explicit user decision and a separate capability review.

Before dispatch, verify that the selected OpenClaw state exposes the requested model, provider authentication, required tool-call capability, compatible thinking controls, and required command tools. If preflight is unavailable or fails, block before model execution. Changing task IDs must not reset the same lane/objective/model retry budget.

OpenClaw may have a host-level fallback model list. Every task therefore declares `modelRequirement: preferred | exact`, `fallbackPolicy: deny | ceo-approved`, and `approvedFallbackModels`. The bridge reads `openclaw models status --json` before session/model execution. Configured fallbacks under `deny`, or a fallback outside the CEO-approved list, block with `openclaw_unapproved_model_fallbacks_configured` or `openclaw_configured_fallback_not_ceo_approved`. A task prompt saying “do not fallback” is not sufficient because host routing may occur before the model sees it. Do not set a thinking level until that exact model/surface advertises support; omit it rather than guessing `low/medium/high`.

The bundled bridge supports task/receipt validation, task hashing, prompt rendering, dry-run command generation, and explicitly authorized OpenClaw execution. Execution is never the default side effect.

### MiniMax Dynamic Route

For the current MiniMax cloud profile, set `routingMode=auto-class`, `modelPolicy=minimax-validated-v1`, `requestedModel=null`, and `reasoningRequirement=preferred`. The bridge maps risk to `fast | balanced | frontier`, intersects the bundled policy with the live OpenClaw model catalog, and sends an explicit MiniMax thinking value:

- R0 and ordinary R1 execution: `off`;
- R1 research/review plus R2/R3: `adaptive`.

Only enabled, locally validated policy candidates may auto-activate. The current validated model is `minimax/MiniMax-M3`; `MiniMax-M2.7-highspeed` remains disabled until a controlled coding/tool/receipt probe passes. No local/Ollama route and no GPT/cross-provider fallback may be introduced by this policy.

Provider transport failure is not a malformed worker receipt. If OpenClaw reports `LLM request failed: network connection error` or an equivalent network boundary failure before a payload exists, write a schema-valid `status=failed` receipt with `blocker=external_provider_network_error`, attempted model/thinking, raw-result path, independently observed changed files, and unknown usage. Do not label it `invalid_receipt`, switch provider/model, create another session, or block the whole Program Goal from one transient incident. `invalid_receipt` is reserved for a process that completed without a valid typed contract and without a classified provider failure.

### Transient Provider Retry And Circuit Fuse

Use `networkRetryPolicy=bounded-backoff` only for classified transient network/connection failures. The default MiniMax task contract permits exactly two total attempts: the original attempt plus one retry after 60 seconds. Keep the same task hash, immutable semantics, project-role session, provider, model, thinking route, fallback denial, permissions, and write-set. Attempt one keeps the declared evidence paths; attempt two uses immutable `.attempt-2` sibling raw/receipt files. Never overwrite consumed evidence or reset the budget by renaming an equivalent task.

Before and after every provider attempt, the bridge independently fingerprints git state and task-owned files. A retry is permitted only when:

- the failure is `external_provider_network_error`, not auth/quota/schema/permission/tool/write-set/verification failure;
- no OpenClaw run remains active in the reused session;
- the independent workspace fingerprint is unchanged;
- the task's two-attempt budget remains;
- the provider circuit is not open.

If a writer changed files before the network failure, do not rerun the consumed task. Ignore a contradictory provider claim such as `changedFiles=[]`; record the independently observed paths, mark the patch an untrusted partial candidate, harvest the actual diff, wait for provider recovery, and issue a new bounded correction/continuation task ID. Preserve every task/raw/receipt hash.

Two consecutive transient failures open the project-scoped provider circuit for five minutes by default. During cooldown, do not call MiniMax repeatedly and do not switch to GPT, another provider, a local model, or a new session. Continue safe portfolio steering, review, evidence inspection, docs, or another already-authorized independent product wave. After cooldown, one half-open probe may run; success closes the circuit, while failure reopens it. Provider cooldown is lane-local and is not sufficient reason to block the Program Goal.

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
