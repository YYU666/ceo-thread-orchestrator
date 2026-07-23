import path from "node:path";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { abortAgentHarnessRun } from "openclaw/plugin-sdk/agent-harness";
import {
  POLICY_VERSION,
  afterToolCall,
  beforeToolCall,
  createRunState,
  finalizeRun,
  onLlmInput,
  onLlmOutput,
  onModelCallStarted,
  validateArmContract,
  writeTelemetry,
} from "./governor.js";

const armed = new Map();
const activeByRun = new Map();
const activeBySession = new Map();
const completed = new Map();
const MAX_COMPLETED = 100;
const POST_END_TELEMETRY_GRACE_MS = 5000;
const POST_ABORT_TELEMETRY_GRACE_MS = 30000;

function isCeoFlowSession(sessionKey) {
  return typeof sessionKey === "string" && sessionKey.includes(":ceoflow:");
}

function safeTelemetryPath(contract, workspaceDir) {
  const root = path.resolve(workspaceDir || process.cwd());
  const target = path.resolve(root, contract.telemetryPath);
  const relative = path.relative(root, target);
  if (relative.startsWith("..") || path.isAbsolute(relative)) throw new Error("telemetry_path_outside_workspace");
  const normalized = relative.replaceAll("\\", "/");
  if (!normalized.startsWith(".ceoflow/exchange/runtime/")) throw new Error("telemetry_path_not_in_runtime_exchange");
  return target;
}

function persist(state) {
  try {
    writeTelemetry(state.contract.telemetryPathAbsolute, state.telemetry);
  } catch {
    // The bridge also verifies telemetry presence and fails closed. Never hide a
    // provider run by manufacturing a successful status when persistence fails.
  }
}

function abortForFuse(state, sessionId, reason) {
  finalizeRun(state, { success: false, error: `budget_fuse_triggered:${reason}` });
  persist(state);
  rememberCompleted(state);
  if (sessionId) abortAgentHarnessRun(sessionId);
  setTimeout(() => {
    if (state.telemetry.runId) activeByRun.delete(state.telemetry.runId);
    activeBySession.delete(state.contract.sessionKey);
  }, POST_ABORT_TELEMETRY_GRACE_MS).unref?.();
  return reason;
}

function resolveState(event, ctx) {
  const runId = event?.runId || ctx?.runId;
  if (runId && activeByRun.has(runId)) return activeByRun.get(runId);
  const sessionKey = event?.sessionKey || ctx?.sessionKey;
  return sessionKey ? activeBySession.get(sessionKey) : undefined;
}

function rememberCompleted(state) {
  completed.set(state.contract.taskId, state.telemetry);
  while (completed.size > MAX_COMPLETED) completed.delete(completed.keys().next().value);
}

export default definePluginEntry({
  id: "ceoflow-budget-governor",
  name: "CEO Flow Budget Governor",
  description: "Task-scoped OpenClaw runtime budget fuse for CEO Flow external execution.",
  register(api) {
    const executorAgentId = String(api.pluginConfig?.executorAgentId || "ceoflow-executor");

    api.registerGatewayMethod("ceoflow.budget.arm", ({ params, respond }) => {
      const errors = validateArmContract(params);
      if (errors.length) return respond(false, { code: "INVALID_REQUEST", message: errors.join(",") });
      try {
        const contract = { ...params, telemetryPathAbsolute: safeTelemetryPath(params, params.workspaceDir) };
        if (contract.agentId !== executorAgentId || !isCeoFlowSession(contract.sessionKey)) {
          return respond(false, { code: "INVALID_REQUEST", message: "budget_scope_mismatch" });
        }
        armed.set(contract.sessionKey, { contract, expiresAt: Date.now() + 15 * 60_000 });
        respond(true, {
          armed: true,
          pluginId: api.id,
          policyVersion: POLICY_VERSION,
          taskId: contract.taskId,
          taskSha256: contract.taskSha256,
          sessionKey: contract.sessionKey,
        });
      } catch (error) {
        respond(false, { code: "INVALID_REQUEST", message: String(error?.message || error) });
      }
    }, { scope: "operator.write" });

    api.registerGatewayMethod("ceoflow.budget.status", ({ params, respond }) => {
      const taskId = typeof params.taskId === "string" ? params.taskId : null;
      const sessionKey = typeof params.sessionKey === "string" ? params.sessionKey : null;
      const state = sessionKey ? activeBySession.get(sessionKey) : undefined;
      const telemetry = state?.telemetry || (taskId ? completed.get(taskId) : undefined) || null;
      respond(true, { pluginId: api.id, policyVersion: POLICY_VERSION, telemetry });
    }, { scope: "operator.read" });

    api.registerGatewayMethod("ceoflow.budget.clear", ({ params, respond }) => {
      const sessionKey = typeof params.sessionKey === "string" ? params.sessionKey : null;
      if (sessionKey) armed.delete(sessionKey);
      respond(true, { cleared: Boolean(sessionKey), sessionKey });
    }, { scope: "operator.write" });

    api.on("before_agent_run", (_event, ctx) => {
      if (ctx.agentId !== executorAgentId && !isCeoFlowSession(ctx.sessionKey)) return;
      const entry = ctx.sessionKey ? armed.get(ctx.sessionKey) : undefined;
      if (!entry || entry.expiresAt < Date.now()) {
        if (ctx.sessionKey) armed.delete(ctx.sessionKey);
        return { outcome: "block", reason: "ceoflow_budget_governor_not_armed" };
      }
      if (entry.contract.agentId !== ctx.agentId || entry.contract.sessionKey !== ctx.sessionKey) {
        return { outcome: "block", reason: "ceoflow_budget_governor_scope_mismatch" };
      }
      const state = createRunState(entry.contract, ctx.runId, ctx.sessionId);
      if (ctx.runId) activeByRun.set(ctx.runId, state);
      activeBySession.set(ctx.sessionKey, state);
      armed.delete(ctx.sessionKey);
      persist(state);
    }, { priority: 1000, timeoutMs: 2000 });

    api.on("model_call_started", (event, ctx) => {
      const state = resolveState(event, ctx);
      if (!state) return;
      const reason = onModelCallStarted(state, event);
      persist(state);
      if (reason) abortForFuse(state, event.sessionId || ctx.sessionId, reason);
    }, { priority: 1000, timeoutMs: 1000 });

    api.on("llm_input", (event, ctx) => {
      const state = resolveState(event, ctx);
      if (!state) return;
      const reason = onLlmInput(state, event);
      persist(state);
      if (reason) abortForFuse(state, event.sessionId || ctx.sessionId, reason);
    }, { priority: 1000, timeoutMs: 1000 });

    api.on("before_tool_call", (event, ctx) => {
      const state = resolveState(event, ctx);
      if (!state) return;
      const reason = beforeToolCall(state);
      persist(state);
      if (!reason) return;
      abortForFuse(state, ctx.sessionId, reason);
      return { block: true, blockReason: `budget_fuse_triggered:${reason}` };
    }, { priority: 1000, timeoutMs: 1000 });

    api.on("after_tool_call", (event, ctx) => {
      const state = resolveState(event, ctx);
      if (!state) return;
      const reason = afterToolCall(state, event);
      persist(state);
      if (reason) abortForFuse(state, ctx.sessionId, reason);
    }, { priority: 1000, timeoutMs: 1000 });

    api.on("llm_output", (event, ctx) => {
      const state = resolveState(event, ctx);
      if (!state) return;
      const reason = onLlmOutput(state, event);
      persist(state);
      if (reason) abortForFuse(state, event.sessionId || ctx.sessionId, reason);
    }, { priority: 1000, timeoutMs: 1000 });

    api.on("agent_end", (event, ctx) => {
      const state = resolveState(event, ctx);
      if (!state) return;
      finalizeRun(state, event);
      persist(state);
      rememberCompleted(state);
      // llm_output/model-call hooks are fire-and-forget in OpenClaw 2026.7.1.
      // Retain the run briefly so already-queued usage events can land after
      // agent_end; the final write remains compact and immutable by task id.
      setTimeout(() => {
        if (state.telemetry.runId) activeByRun.delete(state.telemetry.runId);
        activeBySession.delete(state.contract.sessionKey);
      }, POST_END_TELEMETRY_GRACE_MS).unref?.();
    }, { priority: 1000, timeoutMs: 2000 });
  },
});
