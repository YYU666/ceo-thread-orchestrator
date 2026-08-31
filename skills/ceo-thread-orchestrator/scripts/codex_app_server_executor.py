#!/usr/bin/env python3
"""Production Codex App Server executor for CEO Flow lifecycle plans.

The executor uses the versioned JSON-RPC app-server surface. It never replays a
thread creation or context injection after an ambiguous crash window because
those Host methods do not expose an idempotency key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import select
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import atomic_state
import callback_gateway
import context_ingress_gateway
import context_governor
import task_lifecycle_driver


EXECUTOR_SCHEMA = "ceo_codex_app_server_executor_v1"
CLIENT_VERSION = "0.1.0"
AMBIGUOUS_PHASES = {"replacement_create_started", "recovery_packet_injection_started"}
TRANSPORT_EXISTING_HOST_PROXY = "existing_host_proxy"
TRANSPORT_STANDALONE_TEST = "standalone_test_server"
MAX_TURN_SUMMARY_PAGES = 20
TURN_SUMMARY_PAGE_SIZE = 100
MAX_VERIFICATION_RECEIPT_BYTES = 64 * 1024
VERIFICATION_COMMAND_RECEIPT_SCHEMA = "ceo_verification_command_receipt_v1"


class AppServerError(RuntimeError):
    pass


class RpcTransport(Protocol):
    notifications: list[dict[str, Any]]

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    def wait_notification(self, method: str, *, timeout: float) -> dict[str, Any] | None: ...

    def close(self) -> None: ...


class StdioAppServerTransport:
    def __init__(self, command: list[str], *, timeout: float = 10.0) -> None:
        if not command:
            raise AppServerError("app_server_command_required")
        self.timeout = timeout
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        if self.process.stdin is None or self.process.stdout is None:
            raise AppServerError("app_server_stdio_unavailable")
        self.notifications: list[dict[str, Any]] = []
        self.next_id = 1
        try:
            self._send(
                {
                    "method": "initialize",
                    "id": 0,
                    "params": {
                        "clientInfo": {
                            "name": "ceo_flow_host_executor",
                            "title": "CEO Flow Host Executor",
                            "version": CLIENT_VERSION,
                        },
                        "capabilities": {"experimentalApi": True},
                    },
                }
            )
            self._read_response(0)
            self._send({"method": "initialized", "params": {}})
        except (AppServerError, OSError):
            self.close()
            raise

    def _send(self, message: dict[str, Any]) -> None:
        if self.process.poll() is not None:
            raise AppServerError("app_server_exited")
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def _read_message(self, timeout: float | None = None) -> dict[str, Any]:
        assert self.process.stdout is not None
        ready, _, _ = select.select([self.process.stdout], [], [], self.timeout if timeout is None else timeout)
        if not ready:
            raise AppServerError("app_server_response_timeout")
        line = self.process.stdout.readline()
        if not line:
            raise AppServerError("app_server_closed")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AppServerError("app_server_invalid_json") from exc
        if not isinstance(value, dict):
            raise AppServerError("app_server_invalid_message")
        return value

    def _read_response(self, request_id: int) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AppServerError("app_server_response_timeout")
            message = self._read_message(remaining)
            if message.get("id") == request_id:
                if isinstance(message.get("error"), dict):
                    raise AppServerError(f"app_server_rpc_error:{message['error'].get('message')}")
                result = message.get("result")
                return result if isinstance(result, dict) else {}
            if "method" in message and "id" not in message:
                self.notifications.append(message)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        message: dict[str, Any] = {"method": method, "id": request_id}
        if params is not None:
            message["params"] = params
        self._send(message)
        return self._read_response(request_id)

    def wait_notification(self, method: str, *, timeout: float) -> dict[str, Any] | None:
        for index, message in enumerate(self.notifications):
            if message.get("method") == method:
                return self.notifications.pop(index)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                message = self._read_message(deadline - time.monotonic())
            except AppServerError as exc:
                if str(exc) == "app_server_response_timeout":
                    return None
                raise
            if message.get("method") == method and "id" not in message:
                return message
            if "method" in message and "id" not in message:
                self.notifications.append(message)
        return None

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()


def existing_host_proxy_command(codex: str, socket_path: Path | None = None) -> list[str]:
    command = [codex, "app-server", "proxy"]
    if socket_path is not None:
        command.extend(["--sock", str(socket_path)])
    return command


def standalone_test_server_command(codex: str) -> list[str]:
    return [codex, "app-server", "--stdio"]


def compact_token_estimate(value: Any) -> int:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return math.ceil(len(encoded) / 3)


def goal_payload(goal: dict[str, Any], thread_id: str, status: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "threadId": thread_id,
        "objective": goal.get("objective"),
        "status": status,
    }
    if goal.get("tokenBudget") is not None:
        payload["tokenBudget"] = goal["tokenBudget"]
    return payload


class CodexAppServerExecutor:
    def __init__(
        self,
        transport: RpcTransport,
        journal_dir: Path,
        *,
        reserved_output_tokens: int = 8_000,
        telemetry_timeout: float = 2.0,
    ) -> None:
        self.transport = transport
        self.journal_dir = journal_dir
        self.reserved_output_tokens = reserved_output_tokens
        self.telemetry_timeout = telemetry_timeout
        self.telemetry_failure_reason: str | None = None
        self.journal_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.journal_dir, 0o700)
        except OSError as exc:
            raise AppServerError("host_journal_permissions_unavailable") from exc

    def _journal_path(self, plan_sha256: str) -> Path:
        return self.journal_dir / f"{plan_sha256}.json"

    def _load_journal(self, plan_sha256: str) -> dict[str, Any]:
        path = self._journal_path(plan_sha256)
        if not path.exists():
            return {"schema": EXECUTOR_SCHEMA, "planSha256": plan_sha256, "phase": "new"}
        return context_governor.read_confirmed_state_json(path)

    def _save_journal(self, journal: dict[str, Any]) -> None:
        path = self._journal_path(str(journal["planSha256"]))
        previous = self._load_journal(str(journal["planSha256"])) if path.exists() else {}
        atomic_state.atomic_write_json(
            path,
            journal,
            expected_sha256=atomic_state.state_sha256(previous),
        )

    @staticmethod
    def _usage_snapshot(value: Any, task_id: str) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None
        if value.get("method") == "thread/tokenUsage/updated":
            params = value.get("params")
            if not isinstance(params, dict) or params.get("threadId") != task_id:
                return None
            usage = params.get("tokenUsage")
            return usage if isinstance(usage, dict) else None
        if value.get("threadId") not in {None, task_id}:
            return None
        direct = value.get("tokenUsage")
        if isinstance(direct, dict):
            return direct
        thread = value.get("thread")
        if isinstance(thread, dict) and thread.get("id") in {None, task_id}:
            usage = thread.get("tokenUsage")
            return usage if isinstance(usage, dict) else None
        return None

    def _build_telemetry_receipt(
        self,
        event: dict[str, Any],
        task_id: str,
        usage: dict[str, Any],
        context_compaction_count: int,
    ) -> dict[str, Any] | None:
        last = usage.get("last")
        total = usage.get("total")
        model_window = usage.get("modelContextWindow")
        if not isinstance(last, dict) or not isinstance(total, dict):
            return None
        last_input = context_governor.exact_nonnegative_int(last.get("inputTokens"))
        total_input = context_governor.exact_nonnegative_int(total.get("inputTokens"))
        window = context_governor.exact_nonnegative_int(model_window)
        if last_input is None or total_input is None or window is None:
            return None
        pending_tokens = compact_token_estimate(
            {
                key: value
                for key, value in event.items()
                if not key.startswith("_") and key != "hostTelemetryReceipt"
            }
        )
        receipt: dict[str, Any] = {
            "schema": context_governor.HOST_TELEMETRY_SCHEMA,
            "telemetrySource": context_governor.HOST_TELEMETRY_SOURCE,
            "metricScope": context_governor.HOST_TELEMETRY_SCOPE,
            "capturedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "taskId": task_id,
            "lastRequestInputTokens": last_input,
            "currentPostCompactionContextTokens": last_input,
            "projectedNextRequestInputTokens": last_input + pending_tokens,
            "estimatedContextBytes": (last_input + pending_tokens) * 4,
            "modelContextWindowTokens": window,
            "reservedOutputTokens": self.reserved_output_tokens,
            "cumulativeInputTokens": total_input,
            "contextCompactionCount": context_compaction_count,
            "compactionCountSource": context_governor.HOST_COMPACTION_SOURCE,
        }
        receipt["hostTelemetryReceiptId"] = context_governor.host_telemetry_receipt_sha256(receipt)
        return receipt

    def _context_compaction_count(self, task_id: str) -> int | None:
        """Count Host summary markers without loading raw message or tool bodies."""
        cursor: str | None = None
        seen_cursors: set[str] = set()
        seen_items: set[str] = set()
        count = 0
        for _ in range(MAX_TURN_SUMMARY_PAGES):
            params: dict[str, Any] = {
                "threadId": task_id,
                "limit": TURN_SUMMARY_PAGE_SIZE,
                "sortDirection": "desc",
                "itemsView": "summary",
            }
            if cursor is not None:
                params["cursor"] = cursor
            response = self.transport.request("thread/turns/list", params)
            rows = response.get("data")
            if not isinstance(rows, list):
                return None
            for turn in rows:
                if not isinstance(turn, dict):
                    return None
                items = turn.get("items")
                if not isinstance(items, list):
                    return None
                for item in items:
                    if not isinstance(item, dict):
                        return None
                    if item.get("type") != "contextCompaction":
                        continue
                    item_id = item.get("id")
                    if not isinstance(item_id, str) or not item_id:
                        return None
                    if item_id not in seen_items:
                        seen_items.add(item_id)
                        count += 1
            next_cursor = response.get("nextCursor")
            if next_cursor is None:
                return count
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
                return None
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        return None

    def capture_context_telemetry(self, event: dict[str, Any]) -> dict[str, Any] | None:
        self.telemetry_failure_reason = None
        task_id = event.get("taskId") or event.get("threadId")
        if not isinstance(task_id, str) or not task_id:
            self.telemetry_failure_reason = "host_telemetry_task_id_invalid"
            return None
        read_response = self.transport.request(
            "thread/read", {"threadId": task_id, "includeTurns": False}
        )
        usage = self._usage_snapshot(read_response, task_id)
        if usage is None:
            notification = self.transport.wait_notification(
                "thread/tokenUsage/updated", timeout=self.telemetry_timeout
            )
            usage = self._usage_snapshot(notification, task_id)
        if usage is None:
            self.telemetry_failure_reason = "host_telemetry_snapshot_unavailable"
            return None
        compaction_count = self._context_compaction_count(task_id)
        if compaction_count is None:
            self.telemetry_failure_reason = "host_compaction_summary_unavailable"
            return None
        receipt = self._build_telemetry_receipt(event, task_id, usage, compaction_count)
        if receipt is None:
            self.telemetry_failure_reason = "host_telemetry_snapshot_invalid"
        return receipt

    def capture_context_ingress(
        self, event: dict[str, Any], telemetry: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not (event.get("recoveryRequested") is True or event.get("replacementForTaskId")):
            return None
        receipt: dict[str, Any] = {
            "schema": context_ingress_gateway.SCHEMA,
            "taskId": event.get("taskId") or event.get("threadId"),
            "retainedContextTokens": telemetry.get("currentPostCompactionContextTokens"),
            "threadHistoryMode": "recovery_packet_only",
            "fullThreadHistoryLoaded": False,
            "newFocusedReferences": [],
            "toolOutputs": [],
        }
        receipt["receiptSha256"] = context_ingress_gateway.receipt_sha256(receipt)
        return receipt

    def capture_model_route_receipt(self, callback: dict[str, Any]) -> dict[str, Any] | None:
        if callback.get("routingProofSource") != "codex_host":
            return None
        task_id = callback.get("taskId")
        if not isinstance(task_id, str) or not task_id:
            return None
        response = self.transport.request("thread/read", {"threadId": task_id, "includeTurns": False})
        thread = response.get("thread")
        if not isinstance(thread, dict) or thread.get("id") != task_id:
            return None
        actual_model = thread.get("model")
        actual_thinking = thread.get("reasoningEffort")
        if (
            not isinstance(actual_model, str)
            or not actual_model
            or not isinstance(actual_thinking, str)
            or not actual_thinking
            or callback.get("actualModel") != actual_model
            or callback.get("actualThinking") != actual_thinking
        ):
            return None
        receipt = {
            "schema": callback_gateway.ROUTING_RECEIPT_SCHEMA,
            "source": "codex_host",
            "taskId": task_id,
            "requestedModel": callback.get("requestedModel"),
            "requestedThinking": callback.get("requestedThinking"),
            "actualModel": actual_model,
            "actualThinking": actual_thinking,
            "selectionSurface": "codex_thread_read",
        }
        receipt["receiptSha256"] = callback_gateway.routing_receipt_sha256(receipt)
        return receipt

    @staticmethod
    def _content_addressed_ref(value: Any) -> tuple[str, str] | None:
        if not isinstance(value, str):
            return None
        matched = re.fullmatch(r"([^#]+)#sha256=([0-9a-f]{64})", value)
        if matched is None:
            return None
        return matched.group(1), matched.group(2)

    def capture_verification_evidence_receipt(
        self, callback: dict[str, Any], event: dict[str, Any]
    ) -> dict[str, Any] | None:
        workspace = event.get("workspace")
        refs = callback.get("evidenceRefs")
        commands = callback.get("commands")
        if (
            not isinstance(workspace, str)
            or not workspace
            or not isinstance(refs, list)
            or not refs
            or not isinstance(commands, list)
            or not commands
        ):
            return None
        try:
            root = Path(workspace).resolve(strict=True)
        except OSError:
            return None
        verified_commands: set[str] = set()
        for value in refs:
            parsed = self._content_addressed_ref(value)
            if parsed is None:
                return None
            relative_path, expected_sha256 = parsed
            if not callback_gateway.relative_safe_path(relative_path):
                return None
            normalized = re.sub(r"[^a-z0-9]", "", relative_path.lower())
            if any(marker in normalized for marker in ("rawsession", "credential", "apikey", "sqlite")):
                return None
            try:
                artifact = (root / relative_path).resolve(strict=True)
                artifact.relative_to(root)
                if not artifact.is_file():
                    return None
                artifact_bytes = artifact.read_bytes()
                if len(artifact_bytes) > MAX_VERIFICATION_RECEIPT_BYTES:
                    return None
                digest = hashlib.sha256(artifact_bytes).hexdigest()
                if digest != expected_sha256:
                    return None
                command_receipt = json.loads(artifact_bytes.decode("utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
                return None
            if not isinstance(command_receipt, dict):
                return None
            allowed = {
                "schema",
                "taskId",
                "sliceId",
                "sliceBasisSha256",
                "verificationProfile",
                "command",
                "exitCode",
                "status",
                "summary",
            }
            command = command_receipt.get("command")
            if (
                set(command_receipt) - allowed
                or command_receipt.get("schema") != VERIFICATION_COMMAND_RECEIPT_SCHEMA
                or command_receipt.get("taskId") != callback.get("taskId")
                or command_receipt.get("sliceId") != callback.get("sliceId")
                or command_receipt.get("sliceBasisSha256") != callback.get("sliceBasisSha256")
                or command_receipt.get("verificationProfile") != callback.get("verificationProfile")
                or not isinstance(command, str)
                or command not in commands
                or command_receipt.get("exitCode") != 0
                or command_receipt.get("status") != "passed"
                or not isinstance(command_receipt.get("summary"), str)
            ):
                return None
            verified_commands.add(command)
        if verified_commands != set(commands):
            return None
        receipt = {
            "schema": callback_gateway.EVIDENCE_RECEIPT_SCHEMA,
            "taskId": callback.get("taskId"),
            "sliceId": callback.get("sliceId"),
            "sliceBasisSha256": callback.get("sliceBasisSha256"),
            "verificationProfile": callback.get("verificationProfile"),
            "changedPaths": callback.get("changedPaths"),
            "commands": commands,
            "evidenceRefs": refs,
        }
        receipt["receiptSha256"] = callback_gateway.evidence_receipt_sha256(receipt)
        return receipt

    def _no_op_ack(self, plan: dict[str, Any]) -> dict[str, Any]:
        actions = plan["controlReceipt"]["actions"]
        receipts = {"noOp": True}
        return {
            "schema": task_lifecycle_driver.HOST_ACK_SCHEMA,
            "planSha256": plan["planSha256"],
            "actionsApplied": True,
            "currentTaskId": (actions.get("currentTask") or {}).get("taskId"),
            "frozenTaskId": (actions.get("frozenTask") or {}).get("taskId"),
            "replacementTaskId": None,
            "harvestDriverAction": (actions.get("harvestDriver") or {}).get("action"),
            "actionReceipts": receipts,
            "actionReceiptsSha256": task_lifecycle_driver.host_action_receipts_sha256(receipts),
        }

    def _failure_ack(self, plan: dict[str, Any], reason: str) -> dict[str, Any]:
        return {
            "schema": task_lifecycle_driver.HOST_ACK_SCHEMA,
            "planSha256": plan.get("planSha256"),
            "actionsApplied": False,
            "reason": reason,
        }

    def _latest_turn(self, thread_id: str) -> dict[str, Any] | None:
        response = self.transport.request(
            "thread/turns/list",
            {"threadId": thread_id, "limit": 1, "sortDirection": "desc", "itemsView": "notLoaded"},
        )
        rows = response.get("data")
        return rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else None

    def _stop_active_turn(self, thread_id: str) -> None:
        turn = self._latest_turn(thread_id)
        if isinstance(turn, dict) and turn.get("status") == "inProgress":
            self.transport.request("turn/interrupt", {"threadId": thread_id, "turnId": turn.get("id")})

    def _activate_existing_replacement(
        self, plan: dict[str, Any], replacement: dict[str, Any]
    ) -> dict[str, Any]:
        plan_sha256 = str(plan["planSha256"])
        old_task_id = replacement.get("replacementForTaskId")
        replacement_task_id = replacement.get("replacementTaskId")
        ingress_receipt = replacement.get("contextIngressReceiptSha256")
        creation_plan_sha256 = replacement.get("creationPlanSha256")
        creation_receipts_sha256 = replacement.get("creationActionReceiptsSha256")
        retained_tokens = context_governor.exact_nonnegative_int(
            replacement.get("retainedContextTokens")
        )
        if (
            not isinstance(old_task_id, str)
            or not old_task_id
            or not isinstance(replacement_task_id, str)
            or not replacement_task_id
            or replacement_task_id == old_task_id
            or replacement.get("contextMode") != "replace"
            or not isinstance(ingress_receipt, str)
            or not re.fullmatch(r"[0-9a-f]{64}", ingress_receipt)
            or retained_tokens is None
            or retained_tokens > context_ingress_gateway.MAX_RETAINED_CONTEXT_TOKENS
            or not isinstance(creation_plan_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", creation_plan_sha256)
            or not isinstance(creation_receipts_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", creation_receipts_sha256)
        ):
            return self._failure_ack(plan, "host_existing_replacement_plan_incomplete")
        journal = self._load_journal(plan_sha256)
        if journal.get("phase") == "complete" and isinstance(journal.get("hostAck"), dict):
            return dict(journal["hostAck"])
        try:
            creation_journal = self._load_journal(creation_plan_sha256)
            creation_ack = creation_journal.get("hostAck")
            if (
                creation_journal.get("phase") != "complete"
                or not isinstance(creation_ack, dict)
                or creation_ack.get("planSha256") != creation_plan_sha256
                or creation_ack.get("frozenTaskId") != old_task_id
                or creation_ack.get("replacementTaskId") != replacement_task_id
                or creation_ack.get("actionReceiptsSha256") != creation_receipts_sha256
                or creation_ack.get("actionsApplied") is not True
            ):
                return self._failure_ack(plan, "host_replacement_creation_receipt_mismatch")
            self._stop_active_turn(old_task_id)
            old_thread = self.transport.request(
                "thread/read", {"threadId": old_task_id, "includeTurns": False}
            ).get("thread")
            current_thread = self.transport.request(
                "thread/read", {"threadId": replacement_task_id, "includeTurns": False}
            ).get("thread")
            old_goal = self.transport.request("thread/goal/get", {"threadId": old_task_id}).get(
                "goal"
            )
            current_goal = self.transport.request(
                "thread/goal/get", {"threadId": replacement_task_id}
            ).get("goal")
            if (
                not isinstance(old_thread, dict)
                or old_thread.get("id") != old_task_id
                or not isinstance(current_thread, dict)
                or current_thread.get("id") != replacement_task_id
                or old_goal is not None
                or not isinstance(current_goal, dict)
                or current_goal.get("status") != "active"
                or not isinstance(current_goal.get("objective"), str)
                or not current_goal["objective"].strip()
            ):
                return self._failure_ack(plan, "host_existing_replacement_postcondition_failed")
            self.transport.request("thread/archive", {"threadId": old_task_id})
            receipts = {
                "oldTaskExecutionStopped": True,
                "oldGoalCleared": True,
                "oldGoalWakeupsStopped": True,
                "replacementCreated": True,
                "compactRecoveryPacketInjected": True,
                "replacementGoalBound": True,
                "replacementGoalActive": True,
                "oldTaskArchived": True,
                "harvestDriverTransferred": True,
                "contextMode": "replace",
                "replacementTaskId": replacement_task_id,
                "activeGoalCount": 1,
                "retainedContextTokens": retained_tokens,
                "contextIngressReceiptSha256": ingress_receipt,
            }
            ack = {
                "schema": task_lifecycle_driver.HOST_ACK_SCHEMA,
                "planSha256": plan_sha256,
                "actionsApplied": True,
                "currentTaskId": replacement_task_id,
                "frozenTaskId": old_task_id,
                "replacementTaskId": replacement_task_id,
                "harvestDriverAction": "rebind",
                "actionReceipts": receipts,
                "actionReceiptsSha256": task_lifecycle_driver.host_action_receipts_sha256(
                    receipts
                ),
            }
            journal.update({"phase": "complete", "hostAck": ack})
            self._save_journal(journal)
            return ack
        except (
            AppServerError,
            atomic_state.StateConflictError,
            atomic_state.StateDurabilityError,
            OSError,
        ) as exc:
            return self._failure_ack(plan, f"host_execution_failed:{exc}")

    def apply(self, plan: dict[str, Any]) -> dict[str, Any]:
        plan_sha256 = plan.get("planSha256")
        if not isinstance(plan_sha256, str) or plan_sha256 != task_lifecycle_driver.canonical_sha256(
            {key: value for key, value in plan.items() if key != "planSha256"}
        ):
            return self._failure_ack(plan, "host_plan_digest_invalid")
        replacement = plan.get("replacement")
        if not isinstance(replacement, dict):
            return self._no_op_ack(plan)
        if replacement.get("action") == "activate_clean_replacement":
            return self._activate_existing_replacement(plan, replacement)
        if replacement.get("action") != "create_clean_replacement":
            return self._failure_ack(plan, "host_replacement_action_unsupported")
        journal = self._load_journal(plan_sha256)
        if journal.get("phase") == "complete" and isinstance(journal.get("hostAck"), dict):
            return dict(journal["hostAck"])
        if journal.get("phase") in AMBIGUOUS_PHASES:
            return self._failure_ack(plan, f"host_reconciliation_required:{journal['phase']}")
        old_task_id = replacement.get("replacementForTaskId")
        packet = plan.get("recoveryPacket")
        if not isinstance(old_task_id, str) or not old_task_id or not isinstance(packet, dict):
            return self._failure_ack(plan, "host_replacement_plan_incomplete")
        try:
            self._stop_active_turn(old_task_id)
            goal_response = self.transport.request("thread/goal/get", {"threadId": old_task_id})
            old_goal = goal_response.get("goal")
            if not isinstance(old_goal, dict) or old_goal.get("status") not in {"active", "paused"}:
                return self._failure_ack(plan, "host_source_goal_unavailable")
            self.transport.request("thread/goal/set", goal_payload(old_goal, old_task_id, "paused"))
            journal.update({"phase": "replacement_create_started", "oldTaskId": old_task_id})
            self._save_journal(journal)
            old_thread = self.transport.request(
                "thread/resume", {"threadId": old_task_id, "excludeTurns": True}
            )
            old_thread_record = old_thread.get("thread")
            if not isinstance(old_thread_record, dict):
                old_thread_record = old_thread
            start_params: dict[str, Any] = {
                "cwd": packet.get("canonicalProjectRoot") or old_thread_record.get("cwd"),
                "historyMode": "paginated",
                "threadSource": "ceo-flow-clean-replacement",
            }
            for source, target in (
                ("model", "model"),
                ("modelProvider", "modelProvider"),
                ("approvalPolicy", "approvalPolicy"),
                ("approvalsReviewer", "approvalsReviewer"),
                ("runtimeWorkspaceRoots", "runtimeWorkspaceRoots"),
                ("serviceTier", "serviceTier"),
            ):
                if old_thread_record.get(source) is not None:
                    start_params[target] = old_thread_record[source]
            active_profile = old_thread_record.get("activePermissionProfile")
            if isinstance(active_profile, dict) and isinstance(active_profile.get("id"), str):
                start_params["permissions"] = active_profile["id"]
            started = self.transport.request("thread/start", start_params)
            thread = started.get("thread")
            replacement_task_id = thread.get("id") if isinstance(thread, dict) else None
            if not isinstance(replacement_task_id, str) or not replacement_task_id:
                raise AppServerError("host_replacement_id_missing")
            journal.update({"phase": "replacement_created", "replacementTaskId": replacement_task_id})
            self._save_journal(journal)
            self.transport.request(
                "thread/goal/set", goal_payload(old_goal, replacement_task_id, "paused")
            )
            journal["phase"] = "recovery_packet_injection_started"
            self._save_journal(journal)
            self.transport.request(
                "thread/inject_items",
                {
                    "threadId": replacement_task_id,
                    "items": [
                        {
                            "type": "message",
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": json.dumps(packet, sort_keys=True, separators=(",", ":")),
                                }
                            ],
                        }
                    ],
                },
            )
            journal["phase"] = "recovery_packet_injected"
            self._save_journal(journal)
            self.transport.request("thread/goal/clear", {"threadId": old_task_id})
            self.transport.request(
                "thread/goal/set", goal_payload(old_goal, replacement_task_id, "active")
            )
            old_after = self.transport.request("thread/goal/get", {"threadId": old_task_id}).get("goal")
            new_after = self.transport.request("thread/goal/get", {"threadId": replacement_task_id}).get("goal")
            if old_after is not None or not isinstance(new_after, dict) or new_after.get("status") != "active":
                raise AppServerError("host_goal_transfer_verification_failed")
            self.transport.request("thread/archive", {"threadId": old_task_id})
            retained_tokens = compact_token_estimate(packet)
            receipts = {
                "oldTaskExecutionStopped": True,
                "oldGoalPausedBeforeReplacement": True,
                "oldGoalCleared": True,
                "oldGoalWakeupsStopped": True,
                "replacementCreated": True,
                "compactRecoveryPacketInjected": True,
                "replacementGoalBound": new_after.get("objective") == old_goal.get("objective"),
                "replacementGoalActive": new_after.get("status") == "active",
                "oldTaskArchived": True,
                "harvestDriverTransferred": True,
                "contextMode": "replace",
                "replacementTaskId": replacement_task_id,
                "activeGoalCount": 1,
                "retainedContextTokens": retained_tokens,
                "sourceGoalCreatedAt": old_goal.get("createdAt"),
            }
            ack = {
                "schema": task_lifecycle_driver.HOST_ACK_SCHEMA,
                "planSha256": plan_sha256,
                "actionsApplied": True,
                "currentTaskId": replacement_task_id,
                "frozenTaskId": old_task_id,
                "replacementTaskId": replacement_task_id,
                "harvestDriverAction": "rebind",
                "actionReceipts": receipts,
                "actionReceiptsSha256": task_lifecycle_driver.host_action_receipts_sha256(receipts),
            }
            journal.update({"phase": "complete", "hostAck": ack})
            self._save_journal(journal)
            return ack
        except (AppServerError, atomic_state.StateConflictError, atomic_state.StateDurabilityError, OSError) as exc:
            return self._failure_ack(plan, f"host_execution_failed:{exc}")

    def close(self) -> None:
        self.transport.close()


def lifecycle_limits(args: argparse.Namespace) -> dict[str, int]:
    return {
        "inputTokenLimit": args.input_token_limit,
        "contextTokenLimit": args.context_token_limit,
        "cumulativeInputLimit": args.cumulative_input_limit,
        "contextBytesLimit": args.context_bytes_limit,
        "takeoverTokenLimit": args.takeover_token_limit,
    }


def connect_transport(args: argparse.Namespace) -> tuple[StdioAppServerTransport, str]:
    if args.standalone_test_server:
        command = standalone_test_server_command(args.codex)
        mode = TRANSPORT_STANDALONE_TEST
    else:
        command = existing_host_proxy_command(args.codex, args.host_socket)
        mode = TRANSPORT_EXISTING_HOST_PROXY
    return StdioAppServerTransport(command, timeout=args.host_timeout), mode


def host_boundary_result(reason: str, *, transport_mode: str) -> dict[str, Any]:
    return {
        "schema": task_lifecycle_driver.SCHEMA,
        "ok": False,
        "decision": "block",
        "reason": reason,
        "lifecycleState": "lane_paused_recoverable",
        "programGoalBlocked": False,
        "allowModelRequest": False,
        "allowProjectToolCalls": False,
        "allowProviderCalls": False,
        "hostAcknowledged": False,
        "stateCommitted": False,
        "transportMode": transport_mode,
        "nextAction": "expose_existing_desktop_host_control_socket_then_retry",
    }


def compact_cli_result(result: dict[str, Any], *, transport_mode: str) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in result.items()
        if key not in {"state", "proposedState"}
    }
    compact["transportMode"] = transport_mode
    return compact


def execute_lifecycle_entry(
    event: dict[str, Any],
    state_path: Path,
    limits: dict[str, int],
    executor: CodexAppServerExecutor,
    *,
    callback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return task_lifecycle_driver.run_persisted(
        event,
        state_path,
        limits,
        executor,
        callback=callback,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run CEO Flow through an existing Codex Desktop Host. By default this connects "
            "through `codex app-server proxy` and never starts a second app-server writer."
        )
    )
    parser.add_argument(
        "plan",
        nargs="?",
        type=Path,
        help="Optional confirmed lifecycle plan for compatibility; prefer --event + --state",
    )
    parser.add_argument("--event", type=Path, help="Compact lifecycle event for the full production entry")
    parser.add_argument("--state", type=Path, help="Confirmed task-scoped lifecycle state")
    parser.add_argument("--callback", type=Path, help="Optional compact callback JSON")
    parser.add_argument("--journal-dir", type=Path, required=True)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--host-socket", type=Path, help="Existing Host control socket override")
    parser.add_argument("--host-timeout", type=float, default=10.0)
    parser.add_argument(
        "--standalone-test-server",
        action="store_true",
        help="Developer-test only: explicitly start a separate app-server; never use for Desktop takeover",
    )
    parser.add_argument("--input-token-limit", type=int, default=context_governor.DEFAULT_INPUT_TOKEN_LIMIT)
    parser.add_argument("--context-token-limit", type=int, default=context_governor.DEFAULT_CONTEXT_TOKEN_LIMIT)
    parser.add_argument(
        "--cumulative-input-limit", type=int, default=context_governor.DEFAULT_CUMULATIVE_INPUT_LIMIT
    )
    parser.add_argument("--context-bytes-limit", type=int, default=context_governor.DEFAULT_CONTEXT_BYTES_LIMIT)
    parser.add_argument("--takeover-token-limit", type=int, default=context_governor.DEFAULT_TAKEOVER_TOKEN_LIMIT)
    args = parser.parse_args()

    if bool(args.event) == bool(args.plan):
        parser.error("provide exactly one of --event or plan")
    if args.event and args.state is None:
        parser.error("--event requires --state")

    transport_mode = (
        TRANSPORT_STANDALONE_TEST if args.standalone_test_server else TRANSPORT_EXISTING_HOST_PROXY
    )
    transport: StdioAppServerTransport | None = None
    try:
        transport, transport_mode = connect_transport(args)
        executor = CodexAppServerExecutor(transport, args.journal_dir)
    except (AppServerError, OSError, subprocess.SubprocessError):
        if transport is not None:
            transport.close()
        result = host_boundary_result(
            "desktop_host_connection_unavailable",
            transport_mode=transport_mode,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    try:
        if args.event:
            event = context_governor.read_json(
                args.event, max_bytes=context_governor.MAX_EVENT_SERIALIZED_BYTES
            )
            callback = (
                context_governor.read_json(
                    args.callback, max_bytes=callback_gateway.MAX_CALLBACK_SERIALIZED_BYTES
                )
                if args.callback
                else None
            )
            result = execute_lifecycle_entry(
                event,
                args.state,
                lifecycle_limits(args),
                executor,
                callback=callback,
            )
            output = compact_cli_result(result, transport_mode=transport_mode)
            success = result.get("ok") is True
        else:
            plan = context_governor.read_confirmed_state_json(args.plan)
            result = executor.apply(plan)
            output = compact_cli_result(result, transport_mode=transport_mode)
            success = result.get("actionsApplied") is True
    except (
        AppServerError,
        atomic_state.StateConflictError,
        atomic_state.StateDurabilityError,
        context_governor.ControlPayloadError,
        OSError,
    ):
        output = host_boundary_result(
            "desktop_host_lifecycle_unavailable",
            transport_mode=transport_mode,
        )
        success = False
    finally:
        executor.close()

    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
