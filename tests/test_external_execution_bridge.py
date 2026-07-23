import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "skills" / "ceo-thread-orchestrator" / "scripts" / "external_execution_bridge.py"
TASK_TEMPLATE = ROOT / "skills" / "ceo-thread-orchestrator" / "templates" / "external_execution_task.json"
TASK_SCHEMA = ROOT / "skills" / "ceo-thread-orchestrator" / "schemas" / "external-execution-task.schema.json"
RECEIPT_SCHEMA = ROOT / "skills" / "ceo-thread-orchestrator" / "schemas" / "external-execution-receipt.schema.json"
OPENCLAW_EXECUTOR_SKILL = ROOT / "integrations" / "openclaw" / "skills" / "ceoflow-external-executor" / "SKILL.md"
OPENCLAW_EXECUTOR_CONFIG = ROOT / "integrations" / "openclaw" / "agents" / "ceoflow-executor" / "openclaw-agent-config.fragment.json"

SPEC = importlib.util.spec_from_file_location("external_execution_bridge", BRIDGE_PATH)
BRIDGE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BRIDGE)


class ExternalExecutionBridgeTests(unittest.TestCase):
    def task(self):
        return json.loads(TASK_TEMPLATE.read_text(encoding="utf-8"))

    def receipt(self, task, changed_files=None):
        changed_files = changed_files or []
        return {
            "schemaVersion": BRIDGE.RECEIPT_SCHEMA_VERSION,
            "taskId": task["taskId"],
            "taskSha256": BRIDGE.sha256_json(task),
            "provider": {
                "providerId": task["execution"]["providerId"],
                "adapter": task["execution"]["adapter"],
                "transport": task["execution"]["transport"],
                "runId": "run-test-1",
                "sessionId": "session-test-1",
                "sessionKey": task["execution"].get("sessionKey"),
                "projectId": task["project"]["projectId"],
                "projectIdentitySha256": task["project"]["projectIdentitySha256"],
                "sessionDisplayName": task["execution"]["sessionDisplayName"],
                "frontendVisible": True,
                "actualModel": "domestic-provider/test-model",
                "actualThinking": "medium",
            },
            "status": "succeeded",
            "startedAt": "2026-07-20T00:00:00Z",
            "endedAt": "2026-07-20T00:01:00Z",
            "summary": "Bounded task completed with verification.",
            "changedFiles": changed_files,
            "writeSetCompliance": "pass" if changed_files else "not-applicable",
            "commands": [{"command": "python -m unittest", "exitCode": 0, "status": "passed", "evidenceRef": "artifacts/tests.txt"}],
            "tests": [{"name": "focused", "status": "passed", "evidenceRef": "artifacts/tests.txt"}],
            "artifacts": ["artifacts/tests.txt"],
            "sourceRefs": ["README.md"],
            "blockers": [],
            "residualRisks": [],
            "nextAction": "CEO review",
            "usage": {
                "reported": True,
                "inputTokens": 100,
                "uncachedInputTokens": 100,
                "cachedInputTokens": 0,
                "grossInputTokens": 100,
                "lastRequestInputTokens": 100,
                "outputTokens": 50,
                "totalTokens": 150,
                "providerCallCount": 1,
                "cost": 0.01,
                "currency": "CNY",
            },
            "budgetGovernor": {
                "required": True,
                "pluginId": BRIDGE.OPENCLAW_BUDGET_GOVERNOR_PLUGIN_ID,
                "policyVersion": BRIDGE.OPENCLAW_BUDGET_POLICY_VERSION,
                "runtimeVerified": True,
                "telemetryPath": ".ceoflow/exchange/runtime/test.budget.json",
                "telemetryComplete": True,
                "fuseTriggered": False,
                "fuseReason": None,
                "modelRequestsStarted": 1,
                "modelRequestsCompleted": 1,
                "toolCalls": 1,
                "cumulativeToolResultChars": 100,
                "observedContextTokenBudget": 25000,
                "grossTokensLastMinute": 150,
            },
            "provenance": {"rawResultPath": ".ceoflow/exchange/raw/EXTERNAL-TASK-001.provider.json", "transportReceiptId": "transport-1"},
            "forbiddenPayloadsPresent": False,
        }

    def budget_telemetry(self, task, *, fuse=False):
        return {
            "schemaVersion": BRIDGE.OPENCLAW_BUDGET_TELEMETRY_VERSION,
            "policyVersion": BRIDGE.OPENCLAW_BUDGET_POLICY_VERSION,
            "taskId": task["taskId"],
            "taskSha256": BRIDGE.sha256_json(task),
            "agentId": task["execution"]["agentId"],
            "sessionKey": task["execution"]["sessionKey"],
            "sessionId": "frontend-session-1",
            "runId": "run-test-1",
            "armed": True,
            "telemetryComplete": True,
            "fuseTriggered": fuse,
            "fuseReason": "tool_call_budget_exceeded" if fuse else None,
            "modelRequestsStarted": 1,
            "modelRequestsCompleted": 1,
            "toolCalls": 1,
            "cumulativeToolResultChars": 100,
            "cumulativeUncachedInputTokens": 100,
            "cumulativeCachedInputTokens": 0,
            "cumulativeCacheWriteTokens": 0,
            "cumulativeInputTokens": 100,
            "cumulativeOutputTokens": 50,
            "cumulativeGrossTokens": 150,
            "lastRequestInputTokens": 100,
            "peakRequestInputTokens": 100,
            "observedContextTokenBudget": 25000,
            "grossTokensLastMinute": 150,
            "commandTrace": [{
                "toolName": "exec", "toolCallId": "tool-1",
                "command": "python -m unittest", "exitCode": 0,
                "error": None, "durationMs": 10,
            }],
        }

    def zhixia_packet(self):
        packet = {
            "schemaVersion": BRIDGE.ZHIXIA_INJECTION_SCHEMA_VERSION,
            "query": "legacy audit",
            "queryType": "openclaw_audit",
            "memoryAuthority": "zhixia",
            "items": [{
                "title": "Accepted historical decision",
                "excerpt": "Automatic publishing was stopped because it was unstable and wasted tokens.",
                "memoryLayer": "cold",
                "sourceRefs": ["openclaw-vault://batch/openclaw/workspace/MEMORY.md"],
            }],
            "sourceRefs": ["openclaw-vault://batch/openclaw/workspace/MEMORY.md"],
            "effects": {"openClawMemoryEnabled": False, "rawSessionRead": False},
        }
        packet["tokenEstimate"] = BRIDGE.estimate_serialized_tokens(packet)
        return packet

    def test_template_task_validates(self):
        errors, warnings = BRIDGE.validate_task(self.task())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_json_schemas_expose_single_task_session_contract(self):
        task_schema = json.loads(TASK_SCHEMA.read_text(encoding="utf-8"))
        receipt_schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
        project_properties = task_schema["properties"]["project"]["properties"]
        execution_properties = task_schema["properties"]["execution"]["properties"]
        provider_properties = receipt_schema["properties"]["provider"]["properties"]
        self.assertIn("projectId", project_properties)
        self.assertIn("sessionKey", execution_properties)
        self.assertIn("sessionReusePolicy", execution_properties)
        self.assertIn("agentContextProfile", execution_properties)
        self.assertIn("laneId", execution_properties)
        self.assertIn("newSessionReason", execution_properties)
        self.assertIn("sessionGeneration", execution_properties)
        self.assertIn("sessionContextPolicy", execution_properties)
        self.assertIn("archiveAfterReceipt", execution_properties)
        self.assertIn("maxInitialInputTokens", execution_properties)
        self.assertIn("maxInputTokensPerRequest", execution_properties)
        self.assertIn("maxCumulativeInputTokens", execution_properties)
        self.assertIn("maxProviderCalls", execution_properties)
        self.assertIn("maxModelRequests", execution_properties)
        self.assertIn("maxToolCalls", execution_properties)
        self.assertIn("maxToolResultChars", execution_properties)
        self.assertIn("maxCumulativeToolResultChars", execution_properties)
        self.assertIn("maxCumulativeUncachedInputTokens", execution_properties)
        self.assertIn("maxCumulativeCachedInputTokens", execution_properties)
        self.assertIn("maxCumulativeGrossTokens", execution_properties)
        self.assertIn("budgetGovernorPolicy", execution_properties)
        self.assertIn("sessionDisplayName", execution_properties)
        self.assertIn("frontendVisibility", execution_properties)
        self.assertIn("archivedSessionPolicy", execution_properties)
        self.assertIn("modelRequirement", execution_properties)
        self.assertIn("routingMode", execution_properties)
        self.assertIn("modelPolicy", execution_properties)
        self.assertIn("reasoningRequirement", execution_properties)
        self.assertIn("fallbackPolicy", execution_properties)
        self.assertIn("networkRetryPolicy", execution_properties)
        self.assertIn("networkRetryBackoffSeconds", execution_properties)
        self.assertIn("workspaceMutationRetryPolicy", execution_properties)
        self.assertIn("providerCircuitBreaker", execution_properties)
        self.assertIn("sessionRosterPath", execution_properties)
        self.assertIn("projectIdentitySha256", project_properties)
        self.assertIn("sessionKey", provider_properties)
        self.assertIn("frontendVisible", provider_properties)
        self.assertIn("attemptedModel", provider_properties)
        self.assertIn("attemptedThinking", provider_properties)
        usage_properties = receipt_schema["properties"]["usage"]["properties"]
        self.assertIn("grossInputTokens", usage_properties)
        self.assertIn("cachedInputTokens", usage_properties)
        self.assertIn("lastRequestInputTokens", usage_properties)
        self.assertIn("providerCallCount", usage_properties)
        self.assertIn("budgetGovernor", receipt_schema["properties"])

    def test_openclaw_executor_skill_blocks_self_routing_and_self_acceptance(self):
        skill = OPENCLAW_EXECUTOR_SKILL.read_text(encoding="utf-8")
        self.assertIn("Never call `sessions_spawn`", skill)
        self.assertIn("one bounded task only", skill)
        self.assertIn("Do not turn `succeeded` into self-acceptance", skill)
        self.assertIn("final visible response must be exactly one JSON object", skill)
        self.assertIn("Codex subagent-style work arrives here", skill)

    def test_openclaw_executor_config_is_minimal_and_budgeted(self):
        task = self.task()
        agent = json.loads(OPENCLAW_EXECUTOR_CONFIG.read_text(encoding="utf-8"))
        profile, errors, warnings = BRIDGE.validate_openclaw_executor_agent_config(
            task, [agent], prompt_tokens=2_000,
        )
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertTrue(profile["verified"])
        self.assertLessEqual(profile["conservativeInitialTokens"], task["execution"]["maxInitialInputTokens"])
        self.assertEqual(profile["contextTokens"], task["execution"]["maxInputTokensPerRequest"])
        self.assertEqual(agent["tools"]["allow"], ["read", "apply_patch", "exec", "process"])

        bloated = json.loads(json.dumps(agent))
        bloated.pop("skills")
        bloated["tools"] = {"profile": "full"}
        _, errors, _ = BRIDGE.validate_openclaw_executor_agent_config(task, [bloated], prompt_tokens=2_000)
        self.assertIn("openclaw_executor_skill_allowlist_not_minimal", errors)
        self.assertIn("openclaw_executor_tool_allowlist_not_bounded", errors)

        oversized_context = json.loads(json.dumps(agent))
        oversized_context["contextTokens"] = task["execution"]["maxInputTokensPerRequest"] + 1
        _, errors, _ = BRIDGE.validate_openclaw_executor_agent_config(
            task, [oversized_context], prompt_tokens=2_000
        )
        self.assertIn("openclaw_executor_task_context_cap_not_bounded", errors)

    def test_budget_governor_live_runtime_preflight_fails_closed(self):
        task = self.task()
        valid_runtime = {
            "pluginId": BRIDGE.OPENCLAW_BUDGET_GOVERNOR_PLUGIN_ID,
            "hooks": sorted(BRIDGE.OPENCLAW_BUDGET_GOVERNOR_REQUIRED_HOOKS),
            "gatewayMethods": sorted(BRIDGE.OPENCLAW_BUDGET_GOVERNOR_REQUIRED_METHODS),
        }
        with patch.object(BRIDGE, "run_openclaw_json_command", return_value=(valid_runtime, None)):
            profile, errors = BRIDGE.preflight_openclaw_budget_governor(task, ["openclaw"], {})
        self.assertEqual(errors, [])
        self.assertTrue(profile["verified"])

        incomplete_runtime = {
            "pluginId": BRIDGE.OPENCLAW_BUDGET_GOVERNOR_PLUGIN_ID,
            "hooks": ["before_agent_run"],
            "gatewayMethods": ["ceoflow.budget.status"],
        }
        with patch.object(BRIDGE, "run_openclaw_json_command", return_value=(incomplete_runtime, None)):
            profile, errors = BRIDGE.preflight_openclaw_budget_governor(task, ["openclaw"], {})
        self.assertFalse(profile["verified"])
        self.assertTrue(any(error.startswith("openclaw_budget_governor_hooks_missing") for error in errors))
        self.assertTrue(any(error.startswith("openclaw_budget_governor_methods_missing") for error in errors))

    def test_retry_budget_governor_uses_remaining_task_budget(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task = self.task()
            task["project"]["canonicalRoot"] = temp_dir
            task["project"]["projectIdentitySha256"] = BRIDGE.project_identity_sha256(
                task["project"]["projectId"], temp_dir
            )
            telemetry = self.budget_telemetry(task)
            _, telemetry_path = BRIDGE.budget_governor_telemetry_path(task, 1)
            BRIDGE.write_json_atomic(telemetry_path, telemetry)
            contract = BRIDGE.budget_governor_contract(task, 2)
            self.assertEqual(contract["limits"]["maxModelRequests"], 3)
            self.assertEqual(contract["limits"]["maxToolCalls"], 15)
            self.assertEqual(
                contract["limits"]["maxCumulativeInputTokens"],
                task["execution"]["maxCumulativeInputTokens"] - 100,
            )
            self.assertEqual(
                contract["limits"]["maxCumulativeToolResultChars"],
                task["execution"]["maxCumulativeToolResultChars"] - 100,
            )

            telemetry["modelRequestsStarted"] = task["execution"]["maxModelRequests"]
            BRIDGE.write_json_atomic(telemetry_path, telemetry)
            arm, errors = BRIDGE.arm_openclaw_budget_governor(task, 2, ["openclaw"], {})
            self.assertIsNone(arm)
            self.assertIn("budget_governor_task_budget_exhausted_before_retry", errors)

    def test_external_publish_permissions_fail_closed(self):
        task = self.task()
        task["permissions"]["publishAllowed"] = True
        errors, _ = BRIDGE.validate_task(task)
        self.assertIn("external_executor_publishAllowed_must_be_false", errors)

        task = self.task()
        task["permissions"]["delegationAllowed"] = True
        errors, _ = BRIDGE.validate_task(task)
        self.assertIn("external_executor_delegationAllowed_must_be_false", errors)

        task = self.task()
        task["returnContract"]["receiptPath"] = "../outside.json"
        errors, _ = BRIDGE.validate_task(task)
        self.assertIn("receiptPath_must_be_project_relative", errors)

    def test_receipt_binds_task_hash_and_write_set(self):
        task = self.task()
        valid = self.receipt(task, ["src/example/feature.py", "tests/example/test_feature.py"])
        errors, _ = BRIDGE.validate_receipt(task, valid)
        self.assertEqual(errors, [])

        invalid_hash = self.receipt(task)
        invalid_hash["taskSha256"] = "0" * 64
        errors, _ = BRIDGE.validate_receipt(task, invalid_hash)
        self.assertIn("task_hash_mismatch", errors)

        out_of_scope = self.receipt(task, ["src/unowned/file.py"])
        errors, _ = BRIDGE.validate_receipt(task, out_of_scope)
        self.assertIn("write_set_violation:src/unowned/file.py", errors)

    def test_openclaw_render_is_non_executing_and_explicit(self):
        task = self.task()
        command = BRIDGE.openclaw_command(task)
        self.assertEqual(command[:2], ["openclaw", "agent"])
        self.assertIn("--json", command)
        self.assertNotIn("--thinking", command)
        self.assertIn("--session-key", command)
        self.assertNotIn("--session-id", command)
        self.assertNotIn("--deliver", command)
        prompt = command[command.index("--message") + 1]
        self.assertIn(BRIDGE.sha256_json(task), prompt)
        self.assertIn("final visible response must be exactly one JSON", prompt)
        self.assertIn("native OpenClaw memory", prompt)
        self.assertIn("RECEIPT_ENTRY_SHAPES", prompt)
        self.assertIn("PROVIDER_TASK_VIEW", prompt)
        self.assertNotIn("TASK_ENVELOPE", prompt)
        self.assertIn('"command": string', prompt)
        self.assertIn('"evidenceRef": string|null', prompt)
        self.assertIn("Do not use alternate keys such as cmd, exit, note, passed, failed, or total.", prompt)

        shaped_task = self.task()
        shaped_task["execution"]["thinking"] = "off"
        shaped_command = BRIDGE.openclaw_command(shaped_task)
        self.assertIn("--thinking", shaped_command)
        self.assertEqual(shaped_command[shaped_command.index("--thinking") + 1], "off")

        routed_command = BRIDGE.openclaw_command(task, model_route={
            "selectedModel": "minimax/MiniMax-M3",
            "selectedThinking": "adaptive",
        })
        self.assertEqual(routed_command[routed_command.index("--model") + 1], "minimax/MiniMax-M3")
        self.assertEqual(routed_command[routed_command.index("--thinking") + 1], "adaptive")

        local_task = self.task()
        local_task["execution"]["localMode"] = True
        errors, _ = BRIDGE.validate_task(local_task)
        self.assertIn("local_model_execution_disabled", errors)
        local_command = BRIDGE.openclaw_command(local_task)
        self.assertNotIn("--local", local_command)

        local_model_task = self.task()
        local_model_task["execution"]["requestedModel"] = "ollama/qwen2.5vl:7b"
        errors, _ = BRIDGE.validate_task(local_model_task)
        self.assertIn("local_model_route_disabled", errors)

        completed = subprocess.run(
            [sys.executable, str(BRIDGE_PATH), "run-openclaw", "--task", str(TASK_TEMPLATE), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        result = json.loads(completed.stdout)
        self.assertIn("execution_requires_explicit_--execute", result["errors"])

    def test_openclaw_task_session_generation_is_deterministic(self):
        task = self.task()
        errors, _ = BRIDGE.validate_task(task)
        self.assertEqual(errors, [])
        self.assertEqual(
            task["execution"]["sessionKey"],
            BRIDGE.expected_task_session_key(task),
        )
        self.assertTrue(task["execution"]["sessionKey"].endswith("external-task-001-19102661"))

        missing_key = self.task()
        missing_key["execution"]["sessionKey"] = None
        errors, _ = BRIDGE.validate_task(missing_key)
        self.assertIn("openclaw_session_target_required", errors)
        self.assertIn("openclaw_single_task_session_key_mismatch", errors)

        next_task = self.task()
        next_task["taskId"] = "EXTERNAL-TASK-002"
        next_task["execution"]["sessionGeneration"] = 2
        next_task["execution"]["sessionKey"] = BRIDGE.expected_task_session_key(next_task)
        next_task["execution"]["sessionDisplayName"] = "Example Project · Implementation · EXTERNAL-TASK-002"
        self.assertEqual(BRIDGE.validate_task(next_task)[0], [])
        self.assertNotEqual(task["execution"]["sessionKey"], next_task["execution"]["sessionKey"])

    def test_openclaw_context_budget_fails_closed(self):
        task = self.task()
        task["execution"]["maxInitialInputTokens"] = 30_001
        errors, _ = BRIDGE.validate_task(task)
        self.assertIn("invalid_openclaw_context_budget:maxInitialInputTokens", errors)

        task = self.task()
        task["context"]["tokenBudget"] = 3_001
        errors, _ = BRIDGE.validate_task(task)
        self.assertIn("invalid_context_token_budget", errors)

        task = self.task()
        receipt = self.receipt(task)
        receipt["usage"]["inputTokens"] = task["execution"]["maxCumulativeInputTokens"] + 1
        receipt["usage"]["grossInputTokens"] = task["execution"]["maxCumulativeInputTokens"] + 1
        errors, _ = BRIDGE.validate_receipt(task, receipt)
        self.assertIn("external_provider_cumulative_context_budget_exceeded", errors)

        receipt = self.receipt(task)
        receipt["usage"].update({
            "grossInputTokens": task["execution"]["maxCumulativeInputTokens"] + 1,
            "lastRequestInputTokens": task["execution"]["maxInputTokensPerRequest"] + 1,
            "providerCallCount": task["execution"]["maxProviderCalls"] + 1,
        })
        errors, _ = BRIDGE.validate_receipt(task, receipt)
        self.assertIn("external_provider_cumulative_context_budget_exceeded", errors)
        self.assertIn("external_provider_per_request_context_budget_exceeded", errors)
        self.assertIn("external_provider_call_budget_exceeded", errors)

        receipt = self.receipt(task)
        receipt["usage"]["providerCallCount"] = None
        errors, _ = BRIDGE.validate_receipt(task, receipt)
        self.assertIn("external_provider_call_count_required", errors)

        task = self.task()
        task["execution"]["agentId"] = "main"
        task["execution"]["sessionKey"] = BRIDGE.expected_task_session_key(task)
        errors, _ = BRIDGE.validate_task(task)
        self.assertIn("openclaw_default_main_agent_context_forbidden", errors)

    def test_multi_project_sessions_are_isolated_by_project_identity(self):
        first = self.task()
        second = self.task()
        second["project"].update({
            "projectId": "another-project",
            "projectDisplayName": "Another Project",
            "canonicalRoot": "/absolute/path/to/another-project",
            "ceoOwnerId": "codex-ceo-another",
        })
        second["project"]["projectIdentitySha256"] = BRIDGE.project_identity_sha256(
            second["project"]["projectId"], second["project"]["canonicalRoot"]
        )
        second["execution"].update({
            "sessionDisplayName": "Another Project · Implementation · EXTERNAL-TASK-001",
            "sessionCategory": "Another Project",
            "dispatchLeaseId": "another-project:implementation-main:lease-001",
        })
        second["execution"]["sessionKey"] = BRIDGE.expected_task_session_key(second)
        self.assertEqual(BRIDGE.validate_task(first)[0], [])
        self.assertEqual(BRIDGE.validate_task(second)[0], [])
        self.assertNotEqual(first["execution"]["sessionKey"], second["execution"]["sessionKey"])
        second["execution"]["sessionKey"] = first["execution"]["sessionKey"]
        errors, _ = BRIDGE.validate_task(second)
        self.assertIn("openclaw_single_task_session_key_mismatch", errors)

    def test_project_identity_and_frontend_visibility_fail_closed(self):
        task = self.task()
        task["project"]["canonicalRoot"] = "/wrong/project"
        errors, _ = BRIDGE.validate_task(task)
        self.assertIn("project_identity_sha256_mismatch", errors)

        task = self.task()
        task["execution"]["sessionDisplayName"] = "Unscoped Worker"
        task["execution"]["nativeMemoryPolicy"] = "allow"
        errors, _ = BRIDGE.validate_task(task)
        self.assertIn("openclaw_session_display_name_must_be_project_scoped", errors)
        self.assertIn("openclaw_native_memory_must_be_forbidden", errors)

    def test_frontend_registration_uses_gateway_session_create_and_patch(self):
        task = self.task()
        commands = BRIDGE.openclaw_session_commands(task)
        self.assertIn("sessions.list", commands["list"])
        self.assertIn("sessions.list", commands["listArchived"])
        self.assertIn("sessions.create", commands["create"])
        self.assertIn("sessions.patch", commands["patch"])
        self.assertIn("sessions.patch", commands["archive"])
        self.assertNotIn("--deliver", commands["create"])
        self.assertNotIn("--local", commands["create"])

        visible = {
            "sessions": [{
                "key": task["execution"]["sessionKey"],
                "sessionId": "frontend-session-1",
                "label": task["execution"]["sessionDisplayName"],
                "category": task["execution"]["sessionCategory"],
                "status": "done",
            }]
        }
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[
            ({"sessions": []}, None),
            ({"sessions": []}, None),
            ({"ok": True}, None),
            ({"ok": True}, None),
            (visible, None),
        ]):
            registration, errors, warnings = BRIDGE.ensure_openclaw_frontend_session(task, ["openclaw"], {})
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertTrue(registration["frontendVisible"])
        self.assertEqual(registration["displayName"], "Example Project · Implementation · EXTERNAL-TASK-001")

        task["execution"]["thinking"] = "low"
        active_with_capabilities = {"sessions": [], "defaults": {"thinkingOptions": ["off", "adaptive"]}}
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[
            (active_with_capabilities, None),
            ({"sessions": []}, None),
        ]):
            _, errors, _ = BRIDGE.ensure_openclaw_frontend_session(task, ["openclaw"], {})
        self.assertIn("openclaw_requested_thinking_not_supported", errors)

    def test_archived_or_busy_openclaw_session_is_not_reused(self):
        task = self.task()
        archived = {"sessions": [{"key": task["execution"]["sessionKey"], "archived": True}]}
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[
            ({"sessions": []}, None), (archived, None)
        ]):
            _, errors, _ = BRIDGE.ensure_openclaw_frontend_session(task, ["openclaw"], {})
        self.assertIn("openclaw_archived_session_requires_explicit_restore", errors)

        busy = {"sessions": [{"key": task["execution"]["sessionKey"], "status": "running"}]}
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[
            (busy, None), ({"sessions": []}, None)
        ]):
            _, errors, _ = BRIDGE.ensure_openclaw_frontend_session(task, ["openclaw"], {})
        self.assertIn("openclaw_session_busy", errors)

    def test_terminal_openclaw_task_session_is_archived_and_verified(self):
        task = self.task()
        archived = {
            "sessions": [{
                "key": task["execution"]["sessionKey"],
                "sessionId": "archived-session-1",
                "archived": True,
                "archivedAt": 123,
            }]
        }
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[
            ({"ok": True}, None), (archived, None),
        ]):
            result, errors = BRIDGE.archive_openclaw_frontend_session(task, ["openclaw"], {})
        self.assertEqual(errors, [])
        self.assertTrue(result["archived"])
        self.assertEqual(result["sessionId"], "archived-session-1")

    def test_openclaw_model_fallback_requires_ceo_authorization(self):
        task = self.task()
        status = {
            "defaultModel": "moonshot/kimi-k3",
            "resolvedDefault": "moonshot/kimi-k3",
            "fallbacks": ["custom-provider/expensive-model"],
        }
        catalog = {"models": [{"key": "moonshot/kimi-k3", "available": True, "missing": False}]}
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[(status, None), (catalog, None)]):
            route, errors, _ = BRIDGE.preflight_openclaw_model_route(task, ["openclaw"], {})
        self.assertIn("openclaw_unapproved_model_fallbacks_configured", errors)
        self.assertEqual(route["selectedModel"], "moonshot/kimi-k3")

        task["execution"]["fallbackPolicy"] = "ceo-approved"
        task["execution"]["approvedFallbackModels"] = ["custom-provider/expensive-model"]
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[(status, None), (catalog, None)]):
            _, errors, _ = BRIDGE.preflight_openclaw_model_route(task, ["openclaw"], {})
        self.assertEqual(errors, [])

    def test_pinned_model_availability_uses_target_agent_auth(self):
        model_key = "deepseek/deepseek-v4-flash"
        catalog = {"models": [{"key": model_key, "available": False, "missing": False}]}
        status = {
            "allowed": [model_key],
            "auth": {
                "providers": [{
                    "provider": "deepseek",
                    "profiles": {"count": 1, "apiKey": 1, "labels": ["deepseek:ceoflow=***"]},
                }],
                "unusableProfiles": [],
            },
        }
        self.assertTrue(BRIDGE.target_agent_can_use_model(status, catalog, model_key))
        status["auth"]["unusableProfiles"] = [{"profileId": "deepseek:ceoflow"}]
        self.assertFalse(BRIDGE.target_agent_can_use_model(status, catalog, model_key))

    def test_minimax_auto_class_routes_importance_to_real_thinking_controls(self):
        status = {
            "defaultModel": "minimax/MiniMax-M3",
            "resolvedDefault": "minimax/MiniMax-M3",
            "fallbacks": [],
        }
        catalog = {"models": [{"key": "minimax/MiniMax-M3", "available": True, "missing": False}]}

        routine = self.task()
        routine["execution"]["modelPolicy"] = "minimax-validated-v1"
        routine["riskTier"] = "R0-mechanical"
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[(status, None), (catalog, None)]):
            route, errors, _ = BRIDGE.preflight_openclaw_model_route(routine, ["openclaw"], {})
        self.assertEqual(errors, [])
        self.assertEqual(route["capabilityClass"], "fast")
        self.assertEqual(route["selectedModel"], "minimax/MiniMax-M3")
        self.assertEqual(route["selectedThinking"], "off")
        self.assertEqual(route["routeSource"], "validated_model_policy")
        self.assertIn("minimax/MiniMax-M2.7-highspeed:not_validated", route["rejectedCandidates"])

        complex_task = self.task()
        complex_task["execution"]["modelPolicy"] = "minimax-validated-v1"
        complex_task["riskTier"] = "R2-complex"
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[(status, None), (catalog, None)]):
            route, errors, _ = BRIDGE.preflight_openclaw_model_route(complex_task, ["openclaw"], {})
        self.assertEqual(errors, [])
        self.assertEqual(route["capabilityClass"], "frontier")
        self.assertEqual(route["selectedThinking"], "adaptive")

        reviewer = self.task()
        reviewer["execution"]["modelPolicy"] = "minimax-validated-v1"
        reviewer["role"] = "review-sidecar"
        reviewer["project"]["allowedWriteSet"] = []
        reviewer["execution"]["writeConcurrency"] = "read-only"
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[(status, None), (catalog, None)]):
            route, errors, _ = BRIDGE.preflight_openclaw_model_route(reviewer, ["openclaw"], {})
        self.assertEqual(errors, [])
        self.assertEqual(route["selectedThinking"], "adaptive")

    def test_kimi_k3_tier1_policy_routes_one_model_with_dynamic_thinking(self):
        status = {
            "defaultModel": "moonshot/kimi-k3",
            "resolvedDefault": "moonshot/kimi-k3",
            "fallbacks": [],
        }
        catalog = {"models": [{"key": "moonshot/kimi-k3", "available": True, "missing": False}]}

        routine = self.task()
        routine["riskTier"] = "R0-mechanical"
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[(status, None), (catalog, None)]):
            route, errors, _ = BRIDGE.preflight_openclaw_model_route(routine, ["openclaw"], {})
        self.assertEqual(errors, [])
        self.assertEqual(route["modelPolicy"], "kimi-k3-tier1-v1")
        self.assertEqual(route["selectedModel"], "moonshot/kimi-k3")
        self.assertEqual(route["selectedThinking"], "off")

        complex_task = self.task()
        complex_task["riskTier"] = "R2-complex"
        with patch.object(BRIDGE, "run_openclaw_json_command", side_effect=[(status, None), (catalog, None)]):
            route, errors, _ = BRIDGE.preflight_openclaw_model_route(complex_task, ["openclaw"], {})
        self.assertEqual(errors, [])
        self.assertEqual(route["selectedModel"], "moonshot/kimi-k3")
        self.assertEqual(route["selectedThinking"], "adaptive")

        policy = BRIDGE.load_openclaw_model_policy(policy_id="kimi-k3-tier1-v1")
        envelope = policy["ceoFlowSafetyEnvelope"]
        self.assertEqual(envelope["recommendedMaxConcurrentTasks"], 3)
        self.assertLess(envelope["maxGrossTokensPerTaskMinute"] * 3, policy["providerLimits"]["tpm"])

        oversized = self.task()
        oversized["execution"]["maxGrossTokensPerMinute"] = 450000
        errors, _ = BRIDGE.validate_task(oversized)
        self.assertIn(
            "openclaw_model_policy_budget_exceeded:maxGrossTokensPerMinute", errors
        )

    def test_unvalidated_minimax_model_cannot_auto_activate(self):
        policy = BRIDGE.load_openclaw_model_policy()
        catalog = {"models": [
            {"key": "minimax/MiniMax-M2.7-highspeed", "available": True, "missing": False},
            {"key": "minimax/MiniMax-M3", "available": False, "missing": True},
        ]}
        selected, _, rejected = BRIDGE.resolve_policy_model(policy, "fast", catalog)
        self.assertIsNone(selected)
        self.assertIn("minimax/MiniMax-M2.7-highspeed:not_validated", rejected)

    def test_network_failure_gets_typed_failed_receipt_not_invalid_receipt(self):
        task = self.task()
        failure_code = BRIDGE.classify_openclaw_failure(
            1,
            '{"error":"LLM request failed: network connection error"}',
            "",
            {},
        )
        self.assertEqual(failure_code, "external_provider_network_error")
        receipt = BRIDGE.build_missing_receipt(
            task,
            Path(".ceoflow/exchange/raw/failure.provider.json"),
            {"sessionId": "session-1", "frontendVisible": True},
            {"selectedModel": "minimax/MiniMax-M3", "selectedThinking": "off"},
            failure_code,
        )
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["blockers"], ["external_provider_network_error"])
        self.assertEqual(receipt["provider"]["attemptedModel"], "minimax/MiniMax-M3")
        receipt, governor_errors = BRIDGE.attach_budget_governor_telemetry(
            receipt, self.budget_telemetry(task), task, 1
        )
        self.assertEqual(governor_errors, [])
        self.assertEqual(BRIDGE.validate_receipt(task, receipt)[0], [])

    def test_upstream_capacity_failures_are_transient_but_auth_and_quota_are_not(self):
        transient_samples = [
            "The AI service is temporarily overloaded. Please try again in a moment.",
            "service unavailable",
            "server busy",
            "capacity exceeded",
            "HTTP 502 Bad Gateway",
            "HTTP status 503",
            "gateway returned 504",
        ]
        for sample in transient_samples:
            with self.subTest(sample=sample):
                failure_code = BRIDGE.classify_openclaw_failure(1, "", sample, {})
                self.assertEqual(failure_code, "external_provider_capacity_error")

        permanent_samples = [
            "HTTP 401 invalid API key",
            "HTTP 403 forbidden",
            "HTTP 429 rate limit reached",
            "quota exhausted code 2056",
            "HTTP 500 internal error",
        ]
        for sample in permanent_samples:
            with self.subTest(sample=sample):
                failure_code = BRIDGE.classify_openclaw_failure(1, "", sample, {})
                self.assertEqual(failure_code, "external_provider_process_error")

        task = self.task()
        allowed, reason = BRIDGE.network_retry_decision(
            task, "external_provider_capacity_error", False, 1, 2
        )
        self.assertTrue(allowed)
        self.assertEqual(reason, "bounded_network_retry_eligible")

        allowed, reason = BRIDGE.network_retry_decision(
            task, "external_provider_capacity_error", True, 1, 2
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "workspace_changed_harvest_required")

    def test_transient_network_retry_is_bounded_and_requires_unchanged_workspace(self):
        task = self.task()
        policy = BRIDGE.retry_policy(task)
        self.assertEqual(policy["mode"], "bounded-backoff")
        self.assertEqual(policy["backoffSeconds"], [60])
        self.assertEqual(policy["attemptBudget"], 2)

        allowed, reason = BRIDGE.network_retry_decision(
            task, "external_provider_network_error", False, 1, 2
        )
        self.assertTrue(allowed)
        self.assertEqual(reason, "bounded_network_retry_eligible")

        allowed, reason = BRIDGE.network_retry_decision(
            task, "external_provider_network_error", True, 1, 2
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "workspace_changed_harvest_required")

        allowed, reason = BRIDGE.network_retry_decision(
            task, "external_provider_process_error", False, 1, 2
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "failure_not_retryable")

        allowed, reason = BRIDGE.network_retry_decision(
            task, "external_provider_network_error", False, 2, 2
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "network_retry_budget_exhausted")

    def test_workspace_fingerprint_catches_partial_writer_changes_ignored_by_receipt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src" / "example").mkdir(parents=True)
            source = root / "src" / "example" / "feature.py"
            source.write_text("value = 1\n", encoding="utf-8")
            task = self.task()
            task["project"]["canonicalRoot"] = temp_dir
            task["project"]["projectIdentitySha256"] = BRIDGE.project_identity_sha256(
                task["project"]["projectId"], temp_dir
            )
            before = BRIDGE.capture_workspace_fingerprint(task)
            source.write_text("value = 2\n", encoding="utf-8")
            after = BRIDGE.capture_workspace_fingerprint(task)
            self.assertNotEqual(before["fingerprint"], after["fingerprint"])
            self.assertEqual(
                BRIDGE.workspace_changed_paths(before, after),
                ["src/example/feature.py"],
            )
            receipt = BRIDGE.build_missing_receipt(
                task,
                Path(".ceoflow/exchange/raw/failure.provider.json"),
                {"sessionId": "session-1", "frontendVisible": True},
                {"selectedModel": "minimax/MiniMax-M3", "selectedThinking": "off"},
                "external_provider_network_error",
                changed_files=["src/example/feature.py"],
                retry_disposition="denied",
            )
            self.assertEqual(receipt["changedFiles"], ["src/example/feature.py"])
            self.assertIn("harvest", receipt["nextAction"])
            receipt, governor_errors = BRIDGE.attach_budget_governor_telemetry(
                receipt, self.budget_telemetry(task), task, 1
            )
            self.assertEqual(governor_errors, [])
            self.assertEqual(BRIDGE.validate_receipt(task, receipt)[0], [])

    def test_provider_circuit_opens_without_blocking_program_goal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task = self.task()
            task["project"]["canonicalRoot"] = temp_dir
            task["project"]["projectIdentitySha256"] = BRIDGE.project_identity_sha256(
                task["project"]["projectId"], temp_dir
            )
            route = {"selectedModel": "minimax/MiniMax-M3"}
            first = BRIDGE.record_provider_circuit_outcome(task, route, "network_failure")
            self.assertEqual(first["state"], "closed")
            second = BRIDGE.record_provider_circuit_outcome(task, route, "network_failure")
            self.assertEqual(second["state"], "open")
            self.assertGreaterEqual(second["retryAfterSeconds"], 300)
            inspected = BRIDGE.inspect_provider_circuit(task, route)
            self.assertEqual(inspected["state"], "open")
            closed = BRIDGE.record_provider_circuit_outcome(task, route, "success")
            self.assertEqual(closed["state"], "closed")

    def test_attempt_evidence_paths_are_unique_and_first_attempt_stays_compatible(self):
        base = Path(".ceoflow/exchange/raw/TASK.provider.json")
        self.assertEqual(BRIDGE.attempt_output_path(base, 1), base)
        self.assertEqual(
            BRIDGE.attempt_output_path(base, 2),
            Path(".ceoflow/exchange/raw/TASK.provider.attempt-2.json"),
        )

    def test_run_openclaw_waits_once_then_reuses_same_task_and_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task = self.task()
            task["project"]["canonicalRoot"] = temp_dir
            task["project"]["projectIdentitySha256"] = BRIDGE.project_identity_sha256(
                task["project"]["projectId"], temp_dir
            )
            task_path = root / "task.json"
            task_path.write_text(json.dumps(task), encoding="utf-8")
            success_receipt = self.receipt(task)
            success_payload = json.dumps({"payloads": [{"text": json.dumps(success_receipt)}]})
            network_result = subprocess.CompletedProcess(
                ["openclaw"], 1,
                stdout='{"error":"LLM request failed: network connection error"}',
                stderr="",
            )
            success_result = subprocess.CompletedProcess(
                ["openclaw"], 0, stdout=success_payload, stderr=""
            )
            registration = {
                "sessionId": "frontend-session-1",
                "frontendVisible": True,
                "displayName": task["execution"]["sessionDisplayName"],
                "category": task["execution"]["sessionCategory"],
            }
            route = {
                "selectedModel": "minimax/MiniMax-M3",
                "selectedThinking": "off",
            }
            fingerprint = {"fingerprint": "same", "gitState": "same", "files": {}}
            args = SimpleNamespace(
                execute=True,
                task=str(task_path),
                raw_output=None,
                receipt_output=None,
                json=True,
            )
            with (
                patch.object(BRIDGE, "resolve_openclaw_invocation", return_value=(["openclaw"], {})),
                patch.object(BRIDGE, "preflight_openclaw_executor_agent", return_value=({"verified": True}, [], [])),
                patch.object(BRIDGE, "preflight_openclaw_budget_governor", return_value=({"verified": True}, [])),
                patch.object(BRIDGE, "arm_openclaw_budget_governor", return_value=({"armed": True}, [])),
                patch.object(BRIDGE, "load_budget_governor_telemetry", return_value=(self.budget_telemetry(task), [])),
                patch.object(BRIDGE, "preflight_openclaw_model_route", return_value=(route, [], [])),
                patch.object(BRIDGE, "inspect_provider_circuit", return_value={"state": "closed", "failureCount": 0, "retryAfterSeconds": 0}),
                patch.object(BRIDGE, "prepare_external_session_roster", return_value=(None, [])),
                patch.object(BRIDGE, "ensure_openclaw_frontend_session", side_effect=[(registration, [], []), (registration, [], [])]),
                patch.object(BRIDGE, "archive_openclaw_frontend_session", return_value=({"archived": True}, [])),
                patch.object(BRIDGE, "update_external_session_roster"),
                patch.object(BRIDGE, "capture_workspace_fingerprint", return_value=fingerprint),
                patch.object(BRIDGE.subprocess, "run", side_effect=[network_result, success_result]) as run_mock,
                patch.object(BRIDGE.time, "sleep") as sleep_mock,
                patch.object(BRIDGE, "record_provider_circuit_outcome", side_effect=[
                    {"state": "closed", "failureCount": 1, "retryAfterSeconds": 0},
                    {"state": "closed", "failureCount": 0, "retryAfterSeconds": 0},
                ]),
                patch.object(BRIDGE, "emit_result") as emit_mock,
            ):
                exit_code = BRIDGE.command_run_openclaw(args)
            self.assertEqual(exit_code, 0)
            self.assertEqual(run_mock.call_count, 2)
            sleep_mock.assert_called_once_with(60)
            emitted = emit_mock.call_args.args[0]
            self.assertTrue(emitted["ok"])
            self.assertEqual(emitted["attemptsUsed"], 2)
            self.assertEqual(len(emitted["attemptEvidence"]), 2)
            self.assertTrue((root / ".ceoflow/exchange/raw/EXTERNAL-TASK-001.provider.json").exists())
            self.assertTrue((root / ".ceoflow/exchange/raw/EXTERNAL-TASK-001.provider.attempt-2.json").exists())
            self.assertTrue((root / ".ceoflow/exchange/outbox/EXTERNAL-TASK-001.receipt.json").exists())
            self.assertTrue((root / ".ceoflow/exchange/outbox/EXTERNAL-TASK-001.receipt.attempt-2.json").exists())

    def test_timeout_writes_evidence_and_archives_task_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task = self.task()
            task["project"]["canonicalRoot"] = temp_dir
            task["project"]["projectIdentitySha256"] = BRIDGE.project_identity_sha256(
                task["project"]["projectId"], temp_dir
            )
            task_path = root / "task.json"
            task_path.write_text(json.dumps(task), encoding="utf-8")
            registration = {
                "sessionId": "frontend-session-timeout",
                "frontendVisible": True,
                "displayName": task["execution"]["sessionDisplayName"],
                "category": task["execution"]["sessionCategory"],
            }
            route = {"selectedModel": "minimax/MiniMax-M3", "selectedThinking": "off"}
            fingerprint = {"fingerprint": "same", "gitState": "same", "files": {}}
            args = SimpleNamespace(execute=True, task=str(task_path), raw_output=None, receipt_output=None, json=True)
            with (
                patch.object(BRIDGE, "resolve_openclaw_invocation", return_value=(["openclaw"], {})),
                patch.object(BRIDGE, "preflight_openclaw_executor_agent", return_value=({"verified": True}, [], [])),
                patch.object(BRIDGE, "preflight_openclaw_budget_governor", return_value=({"verified": True}, [])),
                patch.object(BRIDGE, "arm_openclaw_budget_governor", return_value=({"armed": True}, [])),
                patch.object(BRIDGE, "load_budget_governor_telemetry", return_value=(self.budget_telemetry(task), [])),
                patch.object(BRIDGE, "preflight_openclaw_model_route", return_value=(route, [], [])),
                patch.object(BRIDGE, "inspect_provider_circuit", return_value={"state": "closed", "failureCount": 0, "retryAfterSeconds": 0}),
                patch.object(BRIDGE, "prepare_external_session_roster", return_value=(None, [])),
                patch.object(BRIDGE, "ensure_openclaw_frontend_session", return_value=(registration, [], [])),
                patch.object(BRIDGE, "archive_openclaw_frontend_session", return_value=({"archived": True}, [])) as archive_mock,
                patch.object(BRIDGE, "update_external_session_roster"),
                patch.object(BRIDGE, "capture_workspace_fingerprint", return_value=fingerprint),
                patch.object(BRIDGE.subprocess, "run", side_effect=subprocess.TimeoutExpired(["openclaw"], 930)),
                patch.object(BRIDGE, "emit_result") as emit_mock,
            ):
                exit_code = BRIDGE.command_run_openclaw(args)
            self.assertEqual(exit_code, 2)
            archive_mock.assert_called_once()
            emitted = emit_mock.call_args.args[0]
            self.assertEqual(emitted["executionFailureCode"], "external_execution_timed_out")
            self.assertTrue(emitted["sessionArchive"]["archived"])
            self.assertTrue((root / ".ceoflow/exchange/raw/EXTERNAL-TASK-001.provider.json").exists())
            self.assertTrue((root / ".ceoflow/exchange/outbox/EXTERNAL-TASK-001.receipt.json").exists())

    def test_project_session_roster_enforces_owner_and_single_writer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task = self.task()
            task["project"]["canonicalRoot"] = temp_dir
            task["project"]["projectIdentitySha256"] = BRIDGE.project_identity_sha256(
                task["project"]["projectId"], temp_dir
            )
            path, errors = BRIDGE.prepare_external_session_roster(task)
            self.assertEqual(errors, [])
            self.assertTrue(path.is_file())
            roster = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(roster["ceoOwnerId"], "codex-ceo-example")
            self.assertEqual(roster["sessions"][0]["status"], "dispatching")

            competing_owner = json.loads(json.dumps(task))
            competing_owner["project"]["ceoOwnerId"] = "another-ceo"
            _, errors = BRIDGE.prepare_external_session_roster(competing_owner)
            self.assertIn("openclaw_project_dispatch_owner_conflict", errors)

            competing_writer = json.loads(json.dumps(task))
            competing_writer["execution"].update({
                "laneId": "implementation-two",
                "sessionGeneration": 2,
                "sessionDisplayName": "Example Project · Implementation Two · EXTERNAL-TASK-001",
                "dispatchLeaseId": "example-project:implementation-two:lease-001",
            })
            competing_writer["execution"]["sessionKey"] = BRIDGE.expected_task_session_key(competing_writer)
            _, errors = BRIDGE.prepare_external_session_roster(competing_writer)
            self.assertIn("openclaw_project_writer_lease_conflict", errors)

            BRIDGE.update_external_session_roster(path, task, "completed")
            path, errors = BRIDGE.prepare_external_session_roster(competing_writer)
            self.assertEqual(errors, [])

        cross_project = self.task()
        cross_project["project"]["projectId"] = "another-project"
        errors, _ = BRIDGE.validate_task(cross_project)
        self.assertIn("openclaw_single_task_session_key_mismatch", errors)

        fresh = self.task()
        fresh["execution"]["sessionReusePolicy"] = "fresh-isolated"
        fresh["execution"]["newSessionReason"] = None
        errors, _ = BRIDGE.validate_task(fresh)
        self.assertIn("fresh_openclaw_session_reason_required", errors)

    def test_openclaw_execution_can_use_message_file(self):
        task = self.task()
        command = BRIDGE.openclaw_command(task, message_file=Path("task-prompt.txt"))
        self.assertIn("--message-file", command)
        self.assertNotIn("--message", command)
        self.assertEqual(command[command.index("--message-file") + 1], "task-prompt.txt")

    def test_extract_openclaw_payload_receipt(self):
        task = self.task()
        receipt = self.receipt(task)
        result = {"payloads": [{"text": json.dumps(receipt)}], "meta": {"durationMs": 10}}
        self.assertEqual(BRIDGE.extract_openclaw_receipt(result), receipt)
        redacted = BRIDGE.sanitize_raw_text("Bearer abcdefghijklmnop data:image/png;base64," + "A" * 100, 1000)
        self.assertIn("[REDACTED_SECRET]", redacted)
        self.assertIn("[REDACTED_BASE64_PAYLOAD]", redacted)

        receipt["provider"]["actualModel"] = "untrusted/self-reported-model"
        receipt["provider"]["actualThinking"] = "off"
        receipt["usage"] = {"reported": False, "inputTokens": None, "outputTokens": None, "cost": None, "currency": None}
        enriched = BRIDGE.enrich_openclaw_receipt(receipt, {
            "result": {"meta": {
                "agentMeta": {
                    "provider": "minimax",
                    "model": "MiniMax-M3",
                    "sessionId": "session-cloud",
                    "usage": {"input": 321, "output": 45, "cacheRead": 79, "total": 445},
                    "lastCallUsage": {"input": 321, "output": 45, "cacheRead": 79, "total": 445},
                    "promptTokens": 400,
                },
                "requestShaping": {"thinking": "adaptive"},
            }}
        })
        self.assertEqual(enriched["provider"]["actualModel"], "minimax/MiniMax-M3")
        self.assertEqual(enriched["provider"]["actualThinking"], "adaptive")
        self.assertEqual(enriched["usage"]["inputTokens"], 400)
        self.assertEqual(enriched["usage"]["uncachedInputTokens"], 321)
        self.assertEqual(enriched["usage"]["cachedInputTokens"], 79)
        self.assertEqual(enriched["usage"]["grossInputTokens"], 400)
        self.assertEqual(enriched["usage"]["lastRequestInputTokens"], 321)
        self.assertIsNone(enriched["usage"]["providerCallCount"])
        self.assertTrue(enriched["usage"]["reported"])
        self.assertEqual(enriched["provenance"]["transportReceiptId"], "transport-1")

    def test_receipt_object_arrays_are_bounded_and_deterministically_normalized(self):
        task = self.task()
        receipt = self.receipt(task)
        receipt["artifacts"] = [{"kind": "report", "path": "artifacts/e2b.json"}]
        receipt["sourceRefs"] = [{"path": "src/e2b.ts", "anchor": "preflight"}]
        receipt["blockers"] = [{"code": "none", "description": "No blocker"}]
        normalized, warnings, errors = BRIDGE.normalize_receipt_string_arrays(receipt)
        self.assertEqual(errors, [])
        self.assertEqual(
            warnings,
            [
                "receipt_string_array_normalized:artifacts",
                "receipt_string_array_normalized:blockers",
                "receipt_string_array_normalized:sourceRefs",
            ],
        )
        self.assertTrue(all(isinstance(item, str) for item in normalized["artifacts"]))
        self.assertTrue(all(isinstance(item, str) for item in normalized["sourceRefs"]))
        self.assertTrue(all(isinstance(item, str) for item in normalized["blockers"]))
        self.assertEqual(BRIDGE.validate_receipt(task, normalized)[0], [])

        unsafe = self.receipt(task)
        unsafe["artifacts"] = [{"path": "data:image/png;base64," + "A" * 100}]
        _, _, errors = BRIDGE.normalize_receipt_string_arrays(unsafe)
        self.assertIn("receipt_string_array_item_unsafe:artifacts:0", errors)

    def test_openclaw_executable_override_is_explicit_and_checked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            launcher = Path(temp_dir) / ("openclaw.cmd" if sys.platform == "win32" else "openclaw")
            launcher.write_text("@echo off\n" if sys.platform == "win32" else "#!/bin/sh\n", encoding="utf-8")
            previous = BRIDGE.os.environ.get("OPENCLAW_EXECUTABLE")
            try:
                BRIDGE.os.environ["OPENCLAW_EXECUTABLE"] = str(launcher)
                self.assertEqual(BRIDGE.resolve_openclaw_executable(), str(launcher.resolve()))
                self.assertEqual(BRIDGE.resolve_openclaw_invocation(), ([str(launcher.resolve())], {}))
                BRIDGE.os.environ["OPENCLAW_EXECUTABLE"] = str(Path(temp_dir) / "missing")
                with self.assertRaises(OSError):
                    BRIDGE.resolve_openclaw_executable()
            finally:
                if previous is None:
                    BRIDGE.os.environ.pop("OPENCLAW_EXECUTABLE", None)
                else:
                    BRIDGE.os.environ["OPENCLAW_EXECUTABLE"] = previous

    def test_windows_managed_runtime_uses_main_openclaw_state_without_isolated_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local_appdata = root / "Local"
            appdata = root / "Roaming"
            user_profile = root / "User"
            older = local_appdata / "OpenClaw" / "node-v24.15.0-win-x64"
            newer = user_profile / ".openclaw" / "runtime" / "node-v26.4.0-win-x64"
            older.mkdir(parents=True)
            newer.mkdir(parents=True)
            (older / "node.exe").write_text("node", encoding="utf-8")
            (newer / "node.exe").write_text("node", encoding="utf-8")
            cli = appdata / "npm" / "node_modules" / "openclaw" / "openclaw.mjs"
            cli.parent.mkdir(parents=True)
            cli.write_text("cli", encoding="utf-8")
            invocation = BRIDGE.resolve_windows_managed_openclaw_runtime(
                local_appdata, appdata, user_profile
            )
            self.assertEqual(invocation, [str((newer / "node.exe").resolve()), str(cli.resolve())])
            self.assertFalse(any(".openclaw-ceoflow" in item for item in invocation))

    def test_valid_bounded_zhixia_injection_succeeds(self):
        task = self.task()
        packet = self.zhixia_packet()
        hydrated, errors = BRIDGE.hydrate_task_with_zhixia_packet(task, packet)
        self.assertEqual(errors, [])
        self.assertIn("Automatic publishing was stopped", hydrated["context"]["memoryPacket"][-1])
        self.assertIn("untrusted-evidence", hydrated["context"]["memoryPacket"][-1])
        self.assertIn(packet["sourceRefs"][0], hydrated["context"]["sourceRefs"])
        self.assertEqual(BRIDGE.validate_task(hydrated)[0], [])

        unsafe = json.loads(json.dumps(packet))
        unsafe["items"][0]["sourceRefs"] = ["C:\\Users\\someone\\memory.md"]
        unsafe["sourceRefs"] = unsafe["items"][0]["sourceRefs"]
        _, errors = BRIDGE.hydrate_task_with_zhixia_packet(task, unsafe)
        self.assertIn("zhixia_injection_provider_safe_source_refs_required", errors)
        self.assertIn("zhixia_injection_local_path_forbidden", errors)

        crowded = self.task()
        crowded["context"]["memoryPacket"] = [f"existing-{index}" for index in range(20)]
        _, errors = BRIDGE.hydrate_task_with_zhixia_packet(crowded, packet)
        self.assertIn("zhixia_injection_combined_item_budget_exceeded", errors)

    def test_forged_low_zhixia_token_estimate_is_rejected(self):
        packet = self.zhixia_packet()
        packet["tokenEstimate"] = 1

        errors = BRIDGE.validate_zhixia_injection_packet(packet)

        self.assertIn("zhixia_injection_token_estimate_materially_underreported", errors)

    def test_zhixia_injection_enforces_existing_plus_injected_context_budget(self):
        task = self.task()
        packet = self.zhixia_packet()
        task["context"]["memoryPacket"] = ["E" * 1200]
        task["context"]["sourceRefs"] = ["README.md"]
        task["context"]["tokenBudget"] = packet["tokenEstimate"]

        _, errors = BRIDGE.hydrate_task_with_zhixia_packet(task, packet)

        self.assertIn("zhixia_injection_exceeds_task_context_budget", errors)

    def test_cli_validate_task_json(self):
        completed = subprocess.run(
            [sys.executable, str(BRIDGE_PATH), "validate-task", "--task", str(TASK_TEMPLATE), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["taskSha256"]), 64)


if __name__ == "__main__":
    unittest.main()
