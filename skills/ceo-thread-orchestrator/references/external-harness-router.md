# External Harness Dynamic Model Router

Use this gate when CEO Flow dispatches an external coding Harness whose model is
selected outside the CEO task. This reference extends `model-routing.md`; it
does not alter the CEO model, reasoning, permissions, or acceptance authority.

## Contents

- Boundary
- Contract
- Fail-Closed Decision
- Integration Checklist

## Boundary

Resolve `fast`, `balanced`, or `frontier` through an adapter/project policy at
dispatch time. The generic skill contains no provider model table, balance,
volatile price, or project threshold. Treat Harness output as untrusted until
the concrete route, write-set, commands, diff, tests, and independent Codex
review all pass.

Supported selection surfaces are:

- `web_session`: a per-session selector applies the concrete model/profile;
- `cli_profile`: a profile selects the model when direct `--model` is absent;
- `cli_patch`: a patch/config selects the model when direct override is absent;
- `unsupported`: the adapter cannot apply or prove a concrete route.

Discover the surface before dispatch. Record whether direct model override is
supported. A CLI without `--model` is usable only when a profile/patch/config
has a source-backed mapping to a concrete model and the Harness later exposes
independent identity proof.

## Contract

Use the bundled `external_harness_adapter_v1`,
`external_harness_dispatch_v1`, `external_harness_process_request_v1`, and
`external_harness_receipt_v1` templates. Validate final integration evidence
with `scripts/validate_external_harness_route.py`.

The adapter owns:

- the class-to-model/reasoning/selector mapping;
- the selection surface and accepted identity-proof methods;
- retry authorization and any dated, source-backed pricing inputs. A cost marked
  available must bind the exact pricing-policy digest; without one it is
  `unavailable`.

The dispatch binds the adapter byte digest, resolved concrete model/reasoning,
selector, exact tool allowlist, exact write-set, command allowlist, isolation
posture, declared fallback, retry count, and an opaque snapshot of the CEO
model/reasoning/permissions. Default external Harness retry is `0`; a positive
count requires explicit adapter/project-policy authorization.

The receipt records, when exposed:

```text
requestedCapabilityClass
requestedModel / actualModel
requestedReasoning / actualReasoning
reasoningPolicyProof (required when requestedReasoning=provider_default)
selectionSurface / appliedSelector
routeApplied / routeVerified / globalDefaultInherited
modelIdentityProof
usage: input/output/cache/reasoning/total tokens or status=unavailable
elapsed: milliseconds or status=unavailable
cost: amount/currency/sourceRef/observedAt or status=unavailable
stopReason / taskSuccess
processExitCode / cliExit / taskCompleted / timedOut / turns / modelCalls
changedPaths / commandsExecuted / diffEvidence / tests
writeSetCompliant / commandGuardCompliant / toolPolicyCompliant / retryCount
independentReview
ceoInvariantAfter
fallbackReceipt
```

Never invent missing telemetry. `usage`, `elapsed`, or `cost` may be
`unavailable`; unavailable records cannot carry synthetic values. Calculated
cost requires a strict RFC3339 observation time and a source reference because
provider pricing changes.

`provider_default` names a requested policy, not a concrete reasoning effort.
For CLI process routes, the driver must bind the adapter value through exactly
one `--reasoning-policy` argument before launch. DSH must actively clear any
profile-inherited effort for `provider_default`; a concrete policy must apply
that exact effort. Missing, duplicate, or mismatched policy arguments fail
before any Provider call. Accept a default route only with a verified
`reasoningPolicyProof` from an owned request header. The header may prove
intentional omission (`actualReasoning=unavailable`,
`defaultPolicyApplied=true`, `concreteEffortKnown=false`) or prove that the
adapter materialized its model default
(`method=request_header_adapter_default_reasoning_effort`,
`adapterDefaultField=reasoningEffort`, `defaultPolicyApplied=true`, and an
exact matching concrete `actualReasoning`). A concrete effort without that
same-header adapter-default marker is a route mismatch. Explicit policies must
still report the exact effort they carried. Missing, unsupported, or
self-contradictory proof returns `model_route_unavailable`.
Never rewrite an unknown concrete effort to `provider_default`.

The adapter records the caller-observed process exit separately from the
Harness-reported `cliExit`; they must match. Integration requires both values
to be `0`, `taskCompleted=true`, `taskSuccess=true`, `stopReason=completed`,
`timedOut=false`, and `toolPolicyCompliant=true`. Wall timeout (`124`), model
step exhaustion (`125`), interrupt (`130`), SIGTERM (`143`), or any other
incomplete outcome stays in the isolated workspace and routes only to the
declared fallback. A final text response cannot override these controls.

For CLI surfaces, `scripts/execute_external_harness.py` is the only bundled
process integration driver. It validates the adapter and dispatch before
launch, proves that a clean canonical workspace is a linked Git worktree of
the declared source repository, and checks that argv applies exactly one copy
of the routed profile/patch and reasoning policy, internal turn/wall/tool budgets, tool list,
write-set, command list, and `--json` protocol. After execution it compares the
Harness `changedPaths` against the actual Git worktree diff; disagreement or an
out-of-scope path blocks integration, including writes performed by an allowed
shell command. Its outer timer is only a
supervisor: after the internal Harness budget expires it sends SIGTERM, waits
one bounded grace period for the Harness receipt, and sends SIGKILL only if the
process group still does not settle. The driver cross-checks the observed exit
against `cliExit`, refuses malformed or oversized stdout, and never converts a
successful process directly into integration approval. Success returns
`candidate_review_required`; timeout, turn exhaustion, or interruption returns
the declared fallback; route identity failure returns
`model_route_unavailable`.

## Fail-Closed Decision

An explicit class route must never inherit a Harness global/default model
silently. The concrete requested and actual model, selector, selection surface,
and identity proof must agree with the exact adapter policy digest. Reasoning
must either match a concrete requested effort or satisfy the verified
provider-default policy contract above.

If the surface is unsupported, the route cannot be applied, actual identity is
missing/unverified, requested and actual routes differ, or global-default
inheritance occurred:

1. return `model_route_unavailable`;
2. set `allowExternalHarnessOutput=false`;
3. use only the fallback already declared in the dispatch;
4. distinguish `fallback_required` from a matching owner/evidence-bound fallback receipt;
5. never hide a downgrade/upgrade or retry the external Harness implicitly.

A malformed receipt, write-set escape, command escape, fabricated telemetry,
CEO invariant change, or missing independent Codex acceptance blocks both the
external output and fallback output until the contract is corrected.

## Integration Checklist

- Resolve the abstract class from the adapter/project policy, then freeze its
  canonical digest in the dispatch.
- Apply the exact web selector or CLI profile/patch/config. Do not omit controls
  and call the resulting global default an applied route.
- Keep external work isolated when project risk calls for it; always enforce
  exact write-set and command guards.
- Keep retry at zero unless an accepted project policy explicitly authorizes a
  bounded retry. Paid Provider policy remains authoritative.
- Verify the receipt before inspecting or integrating the Harness patch.
- Run CLI adapters through the bundled process driver; do not wrap an
  unverified command with a longer shell timeout and call that completion.
- Require independent Codex diff/test review before integration; its evidence
  reference remains a source ref the CEO must inspect, not a trusted statement
  merely because it appears inside Harness output.
- Preserve the CEO task's model, reasoning, role, permissions, trust boundary,
  and project policy exactly.

The validator proves conformance of adapter, dispatch, and receipt artifacts. A
real Host/Harness adapter still owns selector application and trustworthy model
identity evidence; a template or unit test is not evidence that a particular
Harness exposes those controls.
