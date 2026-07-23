import fs from "node:fs";
import path from "node:path";

export const POLICY_VERSION = "ceoflow.openclaw_budget_governor.v1";
export const TELEMETRY_VERSION = "ceoflow.openclaw_budget_telemetry.v1";

const SHA256_RE = /^[a-f0-9]{64}$/;
const REQUIRED_LIMITS = [
  "maxModelRequests",
  "maxToolCalls",
  "maxToolResultChars",
  "maxCumulativeToolResultChars",
  "maxInputTokensPerRequest",
  "maxCumulativeUncachedInputTokens",
  "maxCumulativeCachedInputTokens",
  "maxCumulativeInputTokens",
  "maxCumulativeGrossTokens",
  "maxGrossTokensPerMinute",
];

function isRecord(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function positiveInteger(value) {
  return Number.isInteger(value) && value > 0;
}

export function validateArmContract(value) {
  const errors = [];
  if (!isRecord(value) || value.schemaVersion !== POLICY_VERSION) {
    return ["invalid_budget_governor_schema"];
  }
  for (const key of ["taskId", "taskSha256", "agentId", "sessionKey", "telemetryPath"]) {
    if (typeof value[key] !== "string" || !value[key].trim()) errors.push(`budget_${key}_required`);
  }
  if (typeof value.taskSha256 === "string" && !SHA256_RE.test(value.taskSha256)) {
    errors.push("budget_task_sha256_invalid");
  }
  if (!isRecord(value.limits)) errors.push("budget_limits_required");
  else for (const key of REQUIRED_LIMITS) {
    if (!positiveInteger(value.limits[key])) errors.push(`budget_limit_invalid:${key}`);
  }
  if (positiveInteger(value?.limits?.maxModelRequests) && value.limits.maxModelRequests > 8) {
    errors.push("budget_model_request_limit_too_high");
  }
  if (positiveInteger(value?.limits?.maxToolCalls) && value.limits.maxToolCalls > 32) {
    errors.push("budget_tool_call_limit_too_high");
  }
  if (
    positiveInteger(value?.limits?.maxToolResultChars) &&
    positiveInteger(value?.limits?.maxCumulativeToolResultChars) &&
    value.limits.maxToolResultChars > value.limits.maxCumulativeToolResultChars
  ) errors.push("budget_per_tool_result_exceeds_cumulative_limit");
  return [...new Set(errors)].sort();
}

function safeStringify(value) {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value ?? "");
  }
}

export function measuredChars(value) {
  return safeStringify(value).length;
}

export function estimateInputTokens(event) {
  const payload = {
    systemPrompt: typeof event?.systemPrompt === "string" ? event.systemPrompt : "",
    prompt: typeof event?.prompt === "string" ? event.prompt : "",
    historyMessages: Array.isArray(event?.historyMessages) ? event.historyMessages : [],
    tools: Array.isArray(event?.tools) ? event.tools : [],
  };
  const serialized = safeStringify(payload);
  const utf8Bytes = Buffer.byteLength(serialized, "utf8");
  // Use the larger of a common character estimate and a UTF-8 estimate so
  // Chinese/JSON-heavy prompts fail closed before the provider request grows.
  return Math.max(Math.ceil(serialized.length / 4), Math.ceil(utf8Bytes / 3));
}

function findNumber(value, keys, depth = 0) {
  if (depth > 5 || value == null) return null;
  if (isRecord(value)) {
    for (const key of keys) {
      const candidate = value[key];
      if (typeof candidate === "number" && Number.isFinite(candidate)) return Math.trunc(candidate);
    }
    for (const candidate of Object.values(value)) {
      const found = findNumber(candidate, keys, depth + 1);
      if (found !== null) return found;
    }
  } else if (Array.isArray(value)) {
    for (const candidate of value) {
      const found = findNumber(candidate, keys, depth + 1);
      if (found !== null) return found;
    }
  }
  return null;
}

export function extractCommandTrace(event) {
  const params = isRecord(event?.params) ? event.params : {};
  const toolName = String(event?.toolName || "");
  if (!new Set(["exec", "process"]).has(toolName)) return null;
  const command = [params.command, params.cmd, params.script]
    .find((item) => typeof item === "string" && item.trim());
  const exitCode = findNumber(event?.result, ["exitCode", "exit_code", "code"]);
  return {
    toolName,
    toolCallId: typeof event?.toolCallId === "string" ? event.toolCallId : null,
    command: command ? command.trim().slice(0, 1000) : null,
    exitCode,
    error: typeof event?.error === "string" ? event.error.slice(0, 500) : null,
    durationMs: Number.isFinite(event?.durationMs) ? Math.trunc(event.durationMs) : null,
  };
}

function nowIso(nowMs) {
  return new Date(nowMs).toISOString();
}

export function createRunState(contract, runId, sessionId, nowMs = Date.now()) {
  return {
    contract,
    telemetry: {
      schemaVersion: TELEMETRY_VERSION,
      policyVersion: POLICY_VERSION,
      taskId: contract.taskId,
      taskSha256: contract.taskSha256,
      agentId: contract.agentId,
      sessionKey: contract.sessionKey,
      sessionId: sessionId || null,
      runId: runId || null,
      armed: true,
      startedAt: nowIso(nowMs),
      endedAt: null,
      telemetryComplete: false,
      fuseTriggered: false,
      fuseReason: null,
      modelRequestsStarted: 0,
      modelRequestsCompleted: 0,
      toolCalls: 0,
      cumulativeToolResultChars: 0,
      cumulativeUncachedInputTokens: 0,
      cumulativeCachedInputTokens: 0,
      cumulativeCacheWriteTokens: 0,
      cumulativeInputTokens: 0,
      cumulativeOutputTokens: 0,
      cumulativeGrossTokens: 0,
      lastRequestInputTokens: null,
      peakRequestInputTokens: 0,
      lastEstimatedInputTokens: null,
      peakEstimatedInputTokens: 0,
      observedContextTokenBudget: null,
      observedContextWindowSource: null,
      contextWindowMatchesTaskCap: null,
      grossTokensLastMinute: 0,
      commandTrace: [],
      limits: { ...contract.limits },
    },
    minuteUsage: [],
  };
}

export function triggerFuse(state, reason, nowMs = Date.now()) {
  if (!state.telemetry.fuseTriggered) {
    state.telemetry.fuseTriggered = true;
    state.telemetry.fuseReason = reason;
    state.telemetry.fuseTriggeredAt = nowIso(nowMs);
  }
  return state.telemetry.fuseReason;
}

export function onModelCallStarted(state, event, nowMs = Date.now()) {
  const telemetry = state.telemetry;
  telemetry.modelRequestsStarted += 1;
  if (positiveInteger(event?.contextTokenBudget)) {
    telemetry.observedContextTokenBudget = event.contextTokenBudget;
    telemetry.observedContextWindowSource = typeof event?.contextWindowSource === "string"
      ? event.contextWindowSource
      : null;
    // OpenClaw reports the resolved model/session context window here, not the
    // token count of this request. Record propagation drift but enforce the
    // task limit against llm_input and exact llm_output usage instead.
    telemetry.contextWindowMatchesTaskCap = event.contextTokenBudget <= state.contract.limits.maxInputTokensPerRequest;
  }
  if (telemetry.modelRequestsStarted > state.contract.limits.maxModelRequests) {
    return triggerFuse(state, "model_request_budget_exceeded", nowMs);
  }
  return null;
}

export function onLlmInput(state, event, nowMs = Date.now()) {
  const estimated = estimateInputTokens(event);
  state.telemetry.lastEstimatedInputTokens = estimated;
  state.telemetry.peakEstimatedInputTokens = Math.max(
    state.telemetry.peakEstimatedInputTokens,
    estimated,
  );
  if (estimated > state.contract.limits.maxInputTokensPerRequest) {
    return triggerFuse(state, "estimated_request_input_budget_exceeded", nowMs);
  }
  return null;
}

export function beforeToolCall(state, nowMs = Date.now()) {
  const telemetry = state.telemetry;
  const limits = state.contract.limits;
  if (telemetry.fuseTriggered) return telemetry.fuseReason;
  if (telemetry.modelRequestsStarted >= limits.maxModelRequests) {
    return triggerFuse(state, "model_request_budget_exhausted_before_tool", nowMs);
  }
  if (telemetry.toolCalls >= limits.maxToolCalls) {
    return triggerFuse(state, "tool_call_budget_exceeded", nowMs);
  }
  if (telemetry.cumulativeToolResultChars + limits.maxToolResultChars > limits.maxCumulativeToolResultChars) {
    return triggerFuse(state, "cumulative_tool_result_budget_would_be_exceeded", nowMs);
  }
  telemetry.toolCalls += 1;
  return null;
}

export function afterToolCall(state, event, nowMs = Date.now()) {
  const telemetry = state.telemetry;
  telemetry.cumulativeToolResultChars += measuredChars(event?.result) + measuredChars(event?.error || "");
  const trace = extractCommandTrace(event);
  if (trace && telemetry.commandTrace.length < 32) telemetry.commandTrace.push(trace);
  if (telemetry.cumulativeToolResultChars > state.contract.limits.maxCumulativeToolResultChars) {
    return triggerFuse(state, "cumulative_tool_result_budget_exceeded", nowMs);
  }
  return null;
}

export function onLlmOutput(state, event, nowMs = Date.now()) {
  const usage = isRecord(event?.usage) ? event.usage : {};
  const uncached = positiveInteger(usage.input) ? usage.input : 0;
  const cached = positiveInteger(usage.cacheRead) ? usage.cacheRead : 0;
  const cacheWrite = positiveInteger(usage.cacheWrite) ? usage.cacheWrite : 0;
  const output = positiveInteger(usage.output) ? usage.output : 0;
  const requestInput = uncached;
  const grossInput = uncached + cached;
  const gross = grossInput + cacheWrite + output;
  const telemetry = state.telemetry;
  telemetry.modelRequestsCompleted += 1;
  telemetry.cumulativeUncachedInputTokens += uncached;
  telemetry.cumulativeCachedInputTokens += cached;
  telemetry.cumulativeCacheWriteTokens += cacheWrite;
  telemetry.cumulativeInputTokens += grossInput;
  telemetry.cumulativeOutputTokens += output;
  telemetry.cumulativeGrossTokens += gross;
  telemetry.lastRequestInputTokens = requestInput;
  telemetry.peakRequestInputTokens = Math.max(telemetry.peakRequestInputTokens, requestInput);
  state.minuteUsage.push({ at: nowMs, gross });
  state.minuteUsage = state.minuteUsage.filter((item) => item.at >= nowMs - 60_000);
  telemetry.grossTokensLastMinute = state.minuteUsage.reduce((total, item) => total + item.gross, 0);
  const limits = state.contract.limits;
  const checks = [
    [requestInput > limits.maxInputTokensPerRequest, "per_request_input_budget_exceeded"],
    [telemetry.cumulativeUncachedInputTokens > limits.maxCumulativeUncachedInputTokens, "cumulative_uncached_input_budget_exceeded"],
    [telemetry.cumulativeCachedInputTokens > limits.maxCumulativeCachedInputTokens, "cumulative_cached_input_budget_exceeded"],
    [telemetry.cumulativeInputTokens > limits.maxCumulativeInputTokens, "cumulative_input_budget_exceeded"],
    [telemetry.cumulativeGrossTokens > limits.maxCumulativeGrossTokens, "cumulative_gross_token_budget_exceeded"],
    [telemetry.grossTokensLastMinute > limits.maxGrossTokensPerMinute, "gross_tpm_budget_exceeded"],
  ];
  const hit = checks.find(([condition]) => condition);
  return hit ? triggerFuse(state, hit[1], nowMs) : null;
}

export function finalizeRun(state, event = {}, nowMs = Date.now()) {
  state.telemetry.endedAt ??= nowIso(nowMs);
  state.telemetry.telemetryComplete = true;
  if (event?.success !== undefined) state.telemetry.agentSuccess = event.success === true;
  if (typeof event?.error === "string") state.telemetry.agentError = event.error.slice(0, 500);
  else if (state.telemetry.fuseTriggered && !state.telemetry.agentError) {
    state.telemetry.agentSuccess = false;
    state.telemetry.agentError = `budget_fuse_triggered:${state.telemetry.fuseReason}`;
  }
  return state.telemetry;
}

export function writeTelemetry(telemetryPath, telemetry) {
  const target = path.resolve(telemetryPath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const temporary = `${target}.tmp-${process.pid}-${Date.now()}`;
  fs.writeFileSync(temporary, `${JSON.stringify(telemetry, null, 2)}\n`, "utf8");
  fs.renameSync(temporary, target);
}
