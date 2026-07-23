# CEO Flow Budget Governor

Trusted local OpenClaw policy plugin for CEO Flow external execution. It is provider-neutral and applies only to the dedicated `ceoflow-executor` Agent and `:ceoflow:` task sessions.

## What it enforces

- exact task/session arm through `ceoflow.budget.arm`;
- model-request and tool-call counters by run ID;
- per-result and cumulative tool-result character limits;
- separate uncached, cache-read, cache-write, output, cumulative, and rolling-TPM telemetry;
- host cancellation through `abortAgentHarnessRun(sessionId)` after a fuse;
- compact command/exit-code trace from `after_tool_call`;
- local JSON telemetry under `.ceoflow/exchange/runtime/`.

It does not choose models, read project memory, persist chat/prompt bodies, create sessions or agents, retry work, accept patches, publish, or contact external services.

## Install and verify

```powershell
openclaw plugins install --link <repo>\integrations\openclaw\plugins\ceoflow-budget-governor
openclaw config set 'plugins.entries.ceoflow-budget-governor.hooks.allowConversationAccess' true --strict-json
openclaw gateway restart
openclaw plugins inspect ceoflow-budget-governor --runtime --json
```

The live runtime must expose:

- hooks: `before_agent_run`, `llm_input`, `model_call_started`, `llm_output`, `before_tool_call`, `after_tool_call`, `agent_end`;
- OpenClaw's reported context window is recorded as propagation telemetry; request-size enforcement uses the assembled `llm_input` estimate before dispatch and exact `llm_output` usage afterward;
- a fuse abort writes terminal telemetry immediately, even if OpenClaw never emits `agent_end` after cancellation;
- methods: `ceoflow.budget.arm`, `ceoflow.budget.status`, `ceoflow.budget.clear`.

OpenClaw categorizes three required lifecycle events as conversation hooks, hence the explicit trusted-local permission. The handlers use run/session metadata and aggregate usage; they do not store raw messages.

## Test

```powershell
node --test test\governor.test.mjs
```

The pure tests make no model/provider request.
