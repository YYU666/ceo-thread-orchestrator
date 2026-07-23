import assert from "node:assert/strict";
import test from "node:test";
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
} from "../governor.js";

function contract(overrides = {}) {
  return {
    schemaVersion: POLICY_VERSION,
    taskId: "TASK-1",
    taskSha256: "a".repeat(64),
    agentId: "ceoflow-executor",
    sessionKey: "agent:ceoflow-executor:ceoflow:project:writer:g001:task",
    telemetryPath: ".ceoflow/exchange/runtime/TASK-1.budget.json",
    limits: {
      maxModelRequests: 4,
      maxToolCalls: 16,
      maxToolResultChars: 4000,
      maxCumulativeToolResultChars: 12000,
      maxInputTokensPerRequest: 25000,
      maxCumulativeUncachedInputTokens: 50000,
      maxCumulativeCachedInputTokens: 90000,
      maxCumulativeInputTokens: 90000,
      maxCumulativeGrossTokens: 110000,
      maxGrossTokensPerMinute: 300000,
      ...overrides,
    },
  };
}

test("arm contract requires every hard limit", () => {
  assert.deepEqual(validateArmContract(contract()), []);
  const invalid = contract();
  delete invalid.limits.maxToolCalls;
  assert.ok(validateArmContract(invalid).includes("budget_limit_invalid:maxToolCalls"));
});

test("fifth model request triggers fuse", () => {
  const state = createRunState(contract(), "run-1", "session-1", 0);
  for (let index = 0; index < 4; index += 1) {
    assert.equal(onModelCallStarted(state, { contextTokenBudget: 25000 }, index), null);
  }
  assert.equal(onModelCallStarted(state, { contextTokenBudget: 25000 }, 5), "model_request_budget_exceeded");
  assert.equal(state.telemetry.modelRequestsStarted, 5);
  assert.equal(state.telemetry.fuseTriggered, true);
});

test("model context window is telemetry, not request-size fuse", () => {
  const state = createRunState(contract(), "run-1", "session-1", 0);
  assert.equal(onModelCallStarted(state, {
    contextTokenBudget: 1048576,
    contextWindowSource: "model",
  }, 1), null);
  assert.equal(state.telemetry.observedContextTokenBudget, 1048576);
  assert.equal(state.telemetry.contextWindowMatchesTaskCap, false);
  assert.equal(state.telemetry.fuseTriggered, false);
});

test("assembled llm input is blocked before an oversized request", () => {
  const state = createRunState(contract({ maxInputTokensPerRequest: 100 }), "run-1", "session-1", 0);
  const reason = onLlmInput(state, {
    systemPrompt: "system",
    prompt: "x".repeat(500),
    historyMessages: [],
    tools: [],
  }, 1);
  assert.equal(reason, "estimated_request_input_budget_exceeded");
  assert.ok(state.telemetry.lastEstimatedInputTokens > 100);
});

test("fuse abort can finalize telemetry without agent_end", () => {
  const state = createRunState(contract(), "run-1", "session-1", 0);
  state.telemetry.fuseTriggered = true;
  state.telemetry.fuseReason = "tool_call_budget_exceeded";
  finalizeRun(state, { success: false, error: "budget_fuse_triggered:tool_call_budget_exceeded" }, 10);
  assert.equal(state.telemetry.telemetryComplete, true);
  assert.equal(state.telemetry.endedAt, "1970-01-01T00:00:00.010Z");
  assert.equal(state.telemetry.agentSuccess, false);
});

test("a fourth model response cannot start another tool loop", () => {
  const state = createRunState(contract(), "run-1", "session-1", 0);
  for (let index = 0; index < 4; index += 1) {
    assert.equal(onModelCallStarted(state, { contextTokenBudget: 25000 }, index), null);
  }
  assert.equal(
    beforeToolCall(state, 5),
    "model_request_budget_exhausted_before_tool",
  );
  assert.equal(state.telemetry.toolCalls, 0);
});

test("tool gate blocks before count or worst-case cumulative budget can be exceeded", () => {
  const state = createRunState(contract({ maxToolCalls: 2 }), "run-1", "session-1", 0);
  assert.equal(beforeToolCall(state, 1), null);
  afterToolCall(state, { toolName: "read", result: "x".repeat(1000) }, 2);
  assert.equal(beforeToolCall(state, 3), null);
  assert.equal(beforeToolCall(state, 4), "tool_call_budget_exceeded");

  const cumulative = createRunState(contract(), "run-2", "session-2", 0);
  cumulative.telemetry.cumulativeToolResultChars = 9000;
  assert.equal(
    beforeToolCall(cumulative, 1),
    "cumulative_tool_result_budget_would_be_exceeded",
  );
});

test("cached and uncached usage remain separate and cached tokens hit the fuse", () => {
  const state = createRunState(contract({ maxCumulativeCachedInputTokens: 100 }), "run-1", "session-1", 0);
  const reason = onLlmOutput(state, {
    usage: { input: 90, cacheRead: 101, cacheWrite: 4, output: 5 },
  }, 1000);
  assert.equal(reason, "cumulative_cached_input_budget_exceeded");
  assert.equal(state.telemetry.lastRequestInputTokens, 90);
  assert.equal(state.telemetry.cumulativeUncachedInputTokens, 90);
  assert.equal(state.telemetry.cumulativeCachedInputTokens, 101);
  assert.equal(state.telemetry.cumulativeInputTokens, 191);
  assert.equal(state.telemetry.cumulativeGrossTokens, 200);
});

test("exec exit codes come from tool trace", () => {
  const state = createRunState(contract(), "run-1", "session-1", 0);
  assert.equal(beforeToolCall(state, 1), null);
  afterToolCall(state, {
    toolName: "exec",
    toolCallId: "tool-1",
    params: { command: "npm test" },
    result: { exitCode: 2, output: "failed" },
  }, 2);
  assert.deepEqual(state.telemetry.commandTrace[0], {
    toolName: "exec",
    toolCallId: "tool-1",
    command: "npm test",
    exitCode: 2,
    error: null,
    durationMs: null,
  });
});
