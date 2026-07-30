# CMMD Hybrid Execution Gate

Use this reference when CEO Flow may route a bounded task to Codex Multi-Model
Desktop (CMMD). CMMD is an optional execution Provider. It does not replace the
Codex CEO, Codex internal threads, the project memory authority, or the CEO's
acceptance and publishing responsibility.

## Contents

- Operating Position
- Readiness Is Two-Dimensional
- Execution Surface Gate
- Stable Role Thread, Isolated Run
- Context View Gate
- Risk Tiers
- Contract And Admission
- Model Route And Budget
- Receipt Review
- Fail-Closed Reasons

## Operating Position

The supported hybrid shape is:

```text
user -> Codex CEO
       -> Codex internal implementation/review lanes (native path)
       -> CMMD bounded run (optional external path)
       <- typed host-owned receipt
       -> Codex CEO evidence review and accept/revise/block/supersede
```

Defaults:

- `codex-internal` remains available and is the default when no project policy
  explicitly enables CMMD;
- an explicit user request for Codex internal multi-thread execution overrides
  CMMD routing for that request;
- CMMD may be selected only after capability, readiness, risk, context, budget,
  workspace, and contract gates pass;
- OpenClaw is historical migration evidence only. Do not route new work to it,
  probe it, configure it, or treat it as a fallback;
- do not use Ollama or add local-runtime setup as a hidden prerequisite;
- CMMD may use only a user-configured and currently admitted Provider. CEO Flow
  does not install models, start runtimes, read credentials, or invent routes.

## Readiness Is Two-Dimensional

Record both states; never collapse them into one `ready` flag.

```text
CMMD live smoke readiness: unknown | unavailable | live_smoke_ready
CMMD production acceptance readiness: false | production_acceptance_ready
Evidence refs:
```

Executable admission uses a typed `ceoflow.cmmd_readiness_evidence.v1` packet
bound to project/project-identity, Provider/model, admitted risk tiers, all four
contract snapshot hashes, observed/expiry times, authority, and sourceRefs. A
free-text readiness label is not execution evidence.

`live_smoke_ready` proves only the frozen capability and risk tier named by the
evidence. It does not authorize broader work. For example, accepted R0
read-only evidence does not authorize an R1 writer.

`production_acceptance_ready` requires the current CMMD production/recovery
gates and relevant risk tier to have independently accepted evidence. Until
then, use CMMD only for an explicitly authorized experiment whose scope matches
the accepted smoke evidence. Do not describe an experimental R0 path as the
default production executor.

CMMD currently vendors a Windows-path v2 task contract. On a non-Windows host,
fail closed unless the live CMMD contract explicitly supports that host and the
same gate has evidence. CEO Flow itself remains cross-platform; Provider
availability is surface-specific.

The compatibility snapshot bundled with this branch has an R0-only
`cmmd.context_view.v1`. Therefore the currently admissible CMMD path is R0 only.
R1 rules below define the future gate and must remain blocked until a reviewed
live Context View contract represents R1 and production acceptance is proven.

## Execution Surface Gate

Choose one surface per task:

```text
Execution surface: codex-internal | cmmd
Selection source: user | accepted-project-policy | CEO capability decision
Reason:
Fallback: deny
```

Use `codex-internal` when any is true:

- the user explicitly requests Codex internal threads or subagents;
- CMMD is not configured, not visible, contract-incompatible, or lacks the
  required readiness evidence;
- the task exceeds the admitted CMMD risk tier or capability class;
- CMMD cannot provide a Host-owned typed receipt and bounded Context View;
- the project needs a native Codex thread/tool behavior CMMD cannot prove.

Use `cmmd` only when all are true:

- the user or accepted project policy enables CMMD for the project;
- a specific Provider/model route is configured in CMMD and is supported by
  current capability evidence;
- the task is acceptance-sized, has a deterministic stop condition, and fits
  the currently admitted risk tier (`R0` in this snapshot);
- repo baseline, workspace identity, file ownership, privacy, and budget gates
  pass;
- the live CMMD contract matches the accepted v2 contract or has been reviewed;
- Codex CEO remains available to validate the terminal receipt and evidence.

Do not silently move a failed CMMD task to a Codex lane, another Provider, a
different model, or a different reasoning mode. Close the failed run, report
the reason, and let CEO create a newly reviewed task with a new route and run
identity. A Provider failure pauses only that task, not the Program Goal.

## Stable Role Thread, Isolated Run

Reuse a stable visible identity for `projectId + laneRole`, not Provider chat
history. Every task receives a new isolated run:

```text
Project role thread ID:
Run ID:
Execution epoch:
Run reservation ID:
Context View ID / SHA-256:
Task ID / SHA-256:
```

Rules:

- the visible project-role thread remains active after a terminal receipt;
- closing a run must not archive the visible role thread;
- Provider native memory and conversation reuse are disabled per run;
- previous Provider/tool messages are not continuity authority;
- Zhixia or the configured Memory Runtime remains long-term history authority;
- each run receives a newly compiled bounded `cmmd.context_view.v1`;
- terminal cleanup removes ephemeral Provider bodies, call maps, tool maps, and
  governor state while preserving compact receipt/provenance/sourceRefs.

## Context View Gate

The Context View may contain only the bounded task, workspace projection,
source ranges, Hot memory, event-triggered Warm anchors, approved Skill items,
Cold sourceRefs, current-run messages, tool contract, and remaining budget.

It must not contain raw CEO chat, a whole visible-thread transcript, raw
sessions, complete ProjectBrain, giant Markdown, broad repository dumps,
unrelated Skills, Provider-native history, images/base64/data:image, secrets,
credentials, or self-routing instructions.

Verify:

```text
Context View schema: cmmd.context_view.v1
Context View SHA-256:
Compiled at:
Source refs:
Estimated bytes/tokens:
Warm Anchor trigger:
Provider native memory: disabled-required
Conversation reuse: per-run-none
Forbidden payloads present: false
```

Ordinary tool turns do not recall memory again. Long-term recall remains
event-triggered under the Memory Runtime and Warm Anchor gates.

## Risk Tiers

### R0 Read-Only

- no changed files;
- empty write-set and command allowlist;
- no authorization lease;
- bounded source refs/ranges and read budget;
- receipt must report `changedFiles=[]` and matching before/after workspace
  fingerprints for success.

R0 is suitable for narrow audits, deterministic comparisons, evidence checks,
and bounded research that does not need arbitrary network access.

### R1 Bounded Writer

R1 is a future/gated path in the bundled snapshot, not a currently admissible
execution option. It may become available only when CMMD has accepted R1
readiness for the exact execution path and ships a reviewed R1-capable Context
View contract. Then require:

- reproducible repo/worktree baseline;
- explicit relative write-set and forbidden paths;
- one Host-issued `ceoflow.authorization_lease.v1` bound to task hash, project,
  role thread, run, epoch, write-set, command allowlist, and expiry;
- Host-enforced mutation limit and command allowlist;
- at least one Host-observed focused verification trace;
- Host-observed changed files and write-set compliance;
- no publish, merge, push, external message, credential access, or memory write.

The model cannot create, extend, choose, or renew the lease. A partial writer
failure never authorizes automatic replay after workspace mutation.

## Contract And Admission

New live runs use only:

```text
ceoflow.external_execution_task.v2
cmmd.context_view.v1
ceoflow.authorization_lease.v1       # R1 only
ceoflow.external_execution_receipt.v2
```

The compatibility snapshot is under `schemas/cmmd/`. CMMD is authoritative; a
snapshot/live hash difference triggers compatibility review. Do not silently
reinterpret changed fields and do not run frozen v1 envelopes.

Before dispatch verify task schema, canonical project identity, role-thread/run
identity, task and Context View hashes, exact workspace baseline, risk tier,
route, source refs/read contract, budgets, write-set, lease requirement,
`fallback=deny`, `retry=0`, visible-thread policy, and
`forbiddenPayloadsPresent=false`.

The bundled CEO-side validator requires the exact task, Context View, and a
compact readiness-evidence packet; add receipt and R1 lease artifacts when
present. It performs full vendored JSON-Schema checks plus commitment and
cross-artifact checks. Missing `jsonschema`, Context View, readiness sourceRefs,
or required lease fails closed. Passing still means only candidate evidence.

## Optional Coding Discipline Candidate

CMMD has accepted `evidence-driven-coding-discipline-v1` only as a source/fake,
default-off candidate. CEO Flow may add the compact trigger fields from
`coding-discipline.md` to non-trivial coding writer/reviewer cards, but it must
not reconstruct or silently inject the CMMD capsule. A CMMD run may use it only
when the live task contract admits the exact profile ID/version/content hash
and current CMMD evidence supports that route.

The candidate does not authorize R1, alter provider/model/reasoning, or prove
coding quality, Codex-quota reduction, total-token reduction, latency, or cost
savings. Those claims require paired live Writer A/B evidence after R1 is
independently ready.

## Model Route And Budget

CMMD route selection remains a CEO-owned staffing decision. Use current CMMD
capability evidence, not model marketing or a stale global ranking.

Record:

```text
Requested provider/model/reasoning:
Requirement: preferred | exact
Capability evidence refs:
Budget: model requests, tool calls, input/request, cumulative input,
        cumulative tool bytes, wall time, estimated cost ceiling
Fallback: deny
Actual provider/model/reasoning:
Usage/cost source:
```

The current v2 CMMD route is fail-closed and has no in-run fallback or retry.
Treat the selected Provider/model as exact for admission unless a future
reviewed schema explicitly represents a bounded preferred-route policy. A
different actual Provider/model is `revise` or `block`, never automatic
acceptance. The current task v2 schema does not bind requested reasoning; its
receipt value is observational only. If exact reasoning is material, return
`cmmd_reasoning_contract_insufficient` rather than pretending it was enforced.

Budget evidence must be Host-owned. Missing model-call count, token totals,
tool count, cost status, or terminal governor state is incomplete evidence.
Budget exhaustion is a terminal task result, not permission to create another
run automatically.

## Receipt Review

CMMD output is an untrusted candidate even when its schema validates. Before
acceptance, verify:

1. exact task/project/role-thread/run/epoch/reservation/Context View identity;
2. task hash and Context View hash;
3. actual Provider/model/reasoning and no fallback/retry;
4. terminal status, failure classification, timestamps, and one attempt;
5. Host-owned usage, budget, workspace fingerprints, changed files, write-set,
   command/test traces, artifacts, and sourceRefs;
6. R0 has no mutations; R1 has a consumed matching lease and successful
   Host-observed verification;
7. ephemeral run cleanup is complete while the visible role thread stays active;
8. no forbidden visual, raw-session, secret, or large payload entered the
   receipt or memory writeback.

`terminalStatus=succeeded` means executor success, not CEO acceptance. CMMD,
its model, or its receipt cannot mutate the CEO model, reasoning, Goal, scope,
permissions, quality gates, or publish state; cannot self-accept; and cannot
merge, push, release, or publish by default.

After `accept | revise | block | supersede`, write only compact evidence and
sourceRefs through the normal Memory Runtime gate.

## Fail-Closed Reasons

Use a specific reason and keep other safe Program Goal work moving:

```text
cmmd_not_configured
cmmd_contract_mismatch
cmmd_readiness_insufficient
cmmd_risk_tier_not_admitted
cmmd_capability_evidence_missing
cmmd_context_view_invalid
cmmd_task_invalid
cmmd_receipt_invalid
cmmd_identity_mismatch
cmmd_route_mismatch
cmmd_reasoning_contract_insufficient
cmmd_budget_evidence_incomplete
cmmd_authorization_lease_invalid
cmmd_host_evidence_incomplete
cmmd_provider_unavailable
```

If CMMD is unavailable, CEO may explicitly create a new `codex-internal` task
card. That is a new routing decision, not fallback inside the failed run.
