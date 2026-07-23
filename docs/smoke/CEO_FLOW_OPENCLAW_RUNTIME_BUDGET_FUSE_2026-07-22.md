# CEO Flow OpenClaw Runtime Budget Fuse Smoke — 2026-07-22

## Decision

`revise` after the first paid RGS smoke exposed an OpenClaw context-window propagation mismatch; the compatibility repair is locally validated and awaits one bounded paid re-probe.

## Scope

- Added provider-neutral `ceoflow-budget-governor` OpenClaw plugin.
- Kept model/provider selection outside the plugin.
- Did not add local-model execution or modify the Codex CEO model/reasoning.
- Did not test or integrate any separate coding-agent product.

## Runtime proof

OpenClaw `2026.7.1-2` live runtime inspection reported:

```text
plugin: ceoflow-budget-governor
status: loaded
typed hooks: 7
  after_tool_call
  agent_end
  before_agent_run
  before_tool_call
  llm_input
  llm_output
  model_call_started
gateway methods: 3
  ceoflow.budget.arm
  ceoflow.budget.status
  ceoflow.budget.clear
diagnostics: 0
```

The live `ceoflow-executor` profile reported:

```text
contextTokens: 25000
skills: ceoflow-external-executor
tools: read, apply_patch, exec, process
toolResultMaxChars: 4000
```

The first RGS paid smoke proved exact task/session arming and safe cancellation, but OpenClaw reported `observedContextTokenBudget=1048576` even though the executor config declared 25k. Inspection of OpenClaw 2026.7.1 showed that this field is a resolved model/session window and that current execution paths can prefer `agents.defaults` over the per-Agent cap.

The repair therefore does not pretend that a model-window field is request usage. It now:

- records the observed window, source, and whether it matches the task cap;
- estimates the fully assembled `llm_input` payload before each request and triggers `estimated_request_input_budget_exceeded` when necessary;
- keeps exact post-response cached/uncached/gross usage gates;
- finalizes `endedAt`, `telemetryComplete`, failure reason, and completed-status lookup at fuse time, without depending on a later `agent_end` callback.

## Automated checks

```text
Python unittest discovery: 46/46 pass
OpenClaw governor node:test: 9/9 pass
Static smoke eval: 86/86 pass
Task template validation: pass
Pipeline + handoff validators: pass
Skill quick validator: pass
Codex plugin validator: pass
Release-state check: pass (development version)
Payload/privacy scan: 56 files, 0 embedded base64/private-key/token findings
git diff --check: pass
Installed CEO Flow source/hash comparison: 38 files, 0 mismatches
```

The governor tests cover:

- malformed/missing hard limits;
- fifth model-request fuse;
- preventing a fourth response from starting another tool loop;
- tool-call and worst-case cumulative tool-output blocking;
- separate cached/uncached accounting;
- authoritative command exit-code extraction;
- native context-window metadata not being misclassified as request usage;
- assembled input estimation before a provider request;
- complete terminal telemetry when abort occurs without `agent_end`;
- retry attempts consuming the original task budget.

## Safety boundary

OpenClaw 2026.7.1 dispatches model-call/usage observations asynchronously. The plugin calls the host abort API on breach and prevents an unbounded loop, but one violating provider call can already be in flight before cancellation lands. This is a runtime cancellation fuse, not a zero-overshoot billing guarantee.

Paid writer dispatch remains fail-closed when the live plugin, task arm receipt, request-size evidence, call counters, or terminal telemetry is absent. A budget fuse never enters the transient network retry path. The OpenClaw-native window may remain larger than the CEO Flow task budget; the task budget is enforced independently from assembled input plus exact usage telemetry.
