#!/usr/bin/env python3
"""Run one bounded external Harness command and gate its machine receipt."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_external_harness_route as router


ALLOWED_EXITS = {0, 1, 2, 124, 125, 130, 143}
EXIT_BY_STOP_REASON = {
    "completed": 0,
    "execution_failed": 1,
    "model_route_mismatch": 1,
    "max_turns_reached": 125,
    "wall_timeout": 124,
    "user_interrupt": 130,
    "sigterm": 143,
    "tool_policy_violation": 1,
    "blocked": 1,
    "no_result": 1,
}
MAX_CAPTURE_BYTES = 1_000_000


def _strict_positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value > 0
        and value <= 86_400
    )


def _strict_positive_integer(value: Any) -> bool:
    return router.is_int(value) and 0 < value <= 86_400


def _canonical_directory(value: Any, field: str, errors: list[str]) -> Path | None:
    if not router.is_nonempty_string(value):
        errors.append(f"request.{field} must be a non-empty absolute directory")
        return None
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        errors.append(f"request.{field} must be absolute")
        return None
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        errors.append(f"request.{field} cannot be resolved: {exc}")
        return None
    if not resolved.is_dir():
        errors.append(f"request.{field} must resolve to a directory")
        return None
    if candidate != resolved:
        errors.append(f"request.{field} must be the canonical real path")
        return None
    return resolved


def _option_values(argv: list[str], flag: str) -> list[str]:
    return [argv[index + 1] for index in range(len(argv) - 1) if argv[index] == flag]


def _require_exact_option(
    argv: list[str], flag: str, expected: str, label: str, errors: list[str]
) -> None:
    if _option_values(argv, flag) != [expected]:
        errors.append(f"argv must apply exactly one {label}")


def _git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )
    return completed.stdout


def _git_identity(root: Path) -> tuple[Path, Path]:
    top = Path(_git_output(root, "rev-parse", "--show-toplevel").strip()).resolve(strict=True)
    common_raw = _git_output(root, "rev-parse", "--git-common-dir").strip()
    common = Path(common_raw)
    if not common.is_absolute():
        common = root / common
    return top, common.resolve(strict=True)


def _git_changed_paths(root: Path) -> list[str]:
    raw = _git_output(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    records = raw.split("\0")
    changed: set[str] = set()
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise ValueError("git status returned malformed porcelain output")
        status = record[:2]
        changed.add(record[3:].replace("\\", "/"))
        if "R" in status or "C" in status:
            if index >= len(records) or not records[index]:
                raise ValueError("git status omitted the rename/copy source path")
            changed.add(records[index].replace("\\", "/"))
            index += 1
    return sorted(changed)


def _validate_isolated_worktree(workspace: Path, source: Path, errors: list[str]) -> None:
    try:
        workspace_top, workspace_common = _git_identity(workspace)
        source_top, source_common = _git_identity(source)
        if workspace_top != workspace:
            errors.append("request.workspace must be the exact Git worktree root")
        if source_top != source:
            errors.append("request.canonicalSourceRoot must be the exact Git worktree root")
        if workspace_common != source_common:
            errors.append("isolated workspace must be a linked worktree of the canonical repository")
        if _git_changed_paths(workspace):
            errors.append("isolated workspace must be clean before Harness launch")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        errors.append(f"isolated Git worktree verification failed: {exc}")


def _validate_launch(
    adapter: Any,
    dispatch: Any,
    request: Any,
) -> tuple[dict[str, Any] | None, Path | None, list[str], list[str]]:
    errors = router.validate_adapter(adapter)
    route = router.route_for(adapter if router.is_plain_dict(adapter) else {}, dispatch, errors)
    launch_errors: list[str] = []
    if not router.is_plain_dict(request):
        return route, None, errors, ["request must be an object"]
    router.require_fields(
        request,
        (
            "schema",
            "workspace",
            "canonicalSourceRoot",
            "isolatedWorkspace",
            "argv",
            "internalBudget",
            "outerTimeoutSeconds",
            "terminationGraceSeconds",
        ),
        "request",
        launch_errors,
    )
    if request.get("schema") != "external_harness_process_request_v1":
        launch_errors.append("request.schema must be external_harness_process_request_v1")
    workspace = _canonical_directory(request.get("workspace"), "workspace", launch_errors)
    source = _canonical_directory(request.get("canonicalSourceRoot"), "canonicalSourceRoot", launch_errors)
    if not isinstance(request.get("isolatedWorkspace"), bool):
        launch_errors.append("request.isolatedWorkspace must be boolean")
    guard = dispatch.get("guard", {}) if router.is_plain_dict(dispatch) else {}
    if guard.get("isolatedWorkspace") is True:
        if request.get("isolatedWorkspace") is not True:
            launch_errors.append("dispatch requires an isolated workspace")
        if workspace is not None and source is not None and workspace == source:
            launch_errors.append("isolated workspace must differ from the canonical source root")
        elif workspace is not None and source is not None:
            _validate_isolated_worktree(workspace, source, launch_errors)

    argv = request.get("argv")
    if not isinstance(argv, list) or not argv or not all(router.is_nonempty_string(item) for item in argv):
        launch_errors.append("request.argv must be a non-empty string list")
        argv = []
    for field in ("outerTimeoutSeconds", "terminationGraceSeconds"):
        if not _strict_positive_number(request.get(field)):
            launch_errors.append(f"request.{field} must be a positive number within 86400 seconds")

    budget = request.get("internalBudget")
    router.require_fields(
        budget,
        ("maxTurns", "wallTimeoutSeconds", "toolTimeoutSeconds"),
        "request.internalBudget",
        launch_errors,
    )
    if not router.is_plain_dict(budget):
        budget = {}
    for field in ("maxTurns", "wallTimeoutSeconds", "toolTimeoutSeconds"):
        if not _strict_positive_integer(budget.get(field)):
            launch_errors.append(f"request.internalBudget.{field} must be a positive integer within 86400")
    if (
        _strict_positive_integer(budget.get("toolTimeoutSeconds"))
        and _strict_positive_integer(budget.get("wallTimeoutSeconds"))
        and budget["toolTimeoutSeconds"] > budget["wallTimeoutSeconds"]
    ):
        launch_errors.append("request.internalBudget.toolTimeoutSeconds cannot exceed wallTimeoutSeconds")
    if (
        _strict_positive_number(request.get("outerTimeoutSeconds"))
        and _strict_positive_integer(budget.get("wallTimeoutSeconds"))
        and request["outerTimeoutSeconds"] <= budget["wallTimeoutSeconds"]
    ):
        launch_errors.append("request.outerTimeoutSeconds must exceed the internal wall timeout")

    if route is None:
        return route, workspace, errors, launch_errors
    surface = route.get("selectionSurface")
    selector = route.get("selector", {})
    if surface not in {"cli_profile", "cli_patch"}:
        launch_errors.append("process driver supports only cli_profile and cli_patch routes")
    elif surface == "cli_profile":
        profile = selector.get("profile")
        if not router.is_nonempty_string(profile):
            launch_errors.append("route does not define a valid CLI profile")
        else:
            _require_exact_option(argv, "--profile", profile, "routed CLI profile", launch_errors)
        patch = selector.get("patch")
        if router.is_nonempty_string(patch):
            _require_exact_option(argv, "--patch", patch, "routed CLI patch", launch_errors)
        elif _option_values(argv, "--patch"):
            launch_errors.append("argv contains an unregistered CLI patch")
    else:
        patch = selector.get("patch")
        config = selector.get("config")
        if router.is_nonempty_string(patch):
            _require_exact_option(argv, "--patch", patch, "routed CLI patch", launch_errors)
        elif _option_values(argv, "--patch"):
            launch_errors.append("argv contains an unregistered CLI patch")
        if router.is_nonempty_string(config):
            _require_exact_option(argv, "--config", config, "routed CLI config", launch_errors)
        elif _option_values(argv, "--config"):
            launch_errors.append("argv contains an unregistered CLI config")

    if route.get("directModelOverride") is False and _option_values(argv, "--model"):
        launch_errors.append("argv uses an unsupported direct model override")

    _require_exact_option(
        argv,
        "--reasoning-policy",
        route.get("reasoning"),
        "routed reasoning policy",
        launch_errors,
    )

    if argv.count("--json") != 1:
        launch_errors.append("argv must request exactly one machine-readable result with --json")
    if budget:
        for flag, field in (
            ("--max-turns", "maxTurns"),
            ("--timeout", "wallTimeoutSeconds"),
            ("--tool-timeout", "toolTimeoutSeconds"),
        ):
            expected = budget.get(field)
            if _strict_positive_integer(expected):
                _require_exact_option(argv, flag, str(expected), f"{field} budget", launch_errors)
    allowed_tools = guard.get("allowedTools") if isinstance(guard.get("allowedTools"), list) else []
    tool_values = _option_values(argv, "--allowed-tools")
    if tool_values != [",".join(allowed_tools)]:
        launch_errors.append("argv allowed-tools do not match the dispatch guard exactly")
    write_set = guard.get("exactWriteSet") if isinstance(guard.get("exactWriteSet"), list) else []
    write_values = _option_values(argv, "--write-set")
    if write_values != [",".join(write_set)]:
        launch_errors.append("argv write-set does not match the dispatch guard exactly")
    commands = guard.get("allowedCommands") if isinstance(guard.get("allowedCommands"), list) else []
    if _option_values(argv, "--allowed-command") != commands:
        launch_errors.append("argv command allowlist does not match the dispatch guard exactly")
    return route, workspace, errors, launch_errors


def _terminate(process: subprocess.Popen[str], hard: bool) -> None:
    if process.poll() is not None:
        return
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGKILL if hard else signal.SIGTERM)
    elif hard:
        process.kill()
    else:
        process.terminate()


def _run_process(
    argv: list[str],
    workspace: Path,
    timeout_seconds: float,
    grace_seconds: float,
) -> tuple[int, str, str, bool, bool]:
    process = subprocess.Popen(
        argv,
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name == "posix",
    )
    supervisor_timed_out = False
    forced_kill = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        supervisor_timed_out = True
        _terminate(process, hard=False)
        try:
            stdout, stderr = process.communicate(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            forced_kill = True
            _terminate(process, hard=True)
            stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr, supervisor_timed_out, forced_kill


def _parse_receipt(stdout: str, errors: list[str]) -> dict[str, Any] | None:
    if len(stdout.encode("utf-8")) > MAX_CAPTURE_BYTES:
        errors.append("Harness stdout exceeded the bounded machine-result limit")
        return None
    lines = [line for line in stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        errors.append("Harness stdout must contain exactly one non-empty JSON line")
        return None
    try:
        receipt = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        errors.append(f"Harness stdout is not valid JSON: {exc}")
        return None
    if not router.is_plain_dict(receipt):
        errors.append("Harness result must be an object")
        return None
    return receipt


def _validate_result(
    route: dict[str, Any],
    dispatch: dict[str, Any],
    process_exit: int,
    receipt: dict[str, Any],
    supervisor_timed_out: bool,
    forced_kill: bool,
    observed_changed_paths: list[str],
) -> dict[str, Any]:
    errors: list[str] = []
    required = (
        "schema", "taskCompleted", "stopReason", "cliExit", "requestedProvider", "actualProvider",
        "requestedModel", "actualModel",
        "requestedReasoning", "actualReasoning", "modelIdentityProof", "turns", "modelCalls",
        "timedOut", "usage", "elapsedMilliseconds", "changedPaths", "commandsExecuted",
        "toolPolicyCompliant",
    )
    router.require_fields(receipt, required, "result", errors)
    if receipt.get("schema") != "dsh_headless_result_v1":
        errors.append("result.schema must be dsh_headless_result_v1")
    cli_exit = receipt.get("cliExit")
    if not router.is_int(cli_exit) or cli_exit not in ALLOWED_EXITS:
        errors.append("result.cliExit is unsupported")
    if process_exit != cli_exit:
        errors.append("caller-observed process exit does not match result.cliExit")
    for field in ("taskCompleted", "timedOut", "toolPolicyCompliant"):
        if not isinstance(receipt.get(field), bool):
            errors.append(f"result.{field} must be boolean")
    for field in ("turns", "modelCalls", "elapsedMilliseconds"):
        value = receipt.get(field)
        if not router.is_int(value) or value < 0:
            errors.append(f"result.{field} must be a non-negative integer")
    if receipt.get("turns") != receipt.get("modelCalls"):
        errors.append("result.turns must equal result.modelCalls")
    stop_reason = receipt.get("stopReason")
    expected_exit = EXIT_BY_STOP_REASON.get(stop_reason)
    if expected_exit is None:
        errors.append("result.stopReason is unsupported")
    elif cli_exit != expected_exit:
        errors.append("result.cliExit does not match result.stopReason")
    if receipt.get("taskCompleted") is not (stop_reason == "completed"):
        errors.append("result.taskCompleted does not match result.stopReason")
    if receipt.get("timedOut") is not (stop_reason == "wall_timeout"):
        errors.append("result.timedOut does not match result.stopReason")
    usage = receipt.get("usage")
    if not router.is_plain_dict(usage) or usage.get("status") not in {"available", "unavailable"}:
        errors.append("result.usage must be an available or unavailable record")
    elif usage.get("status") == "unavailable":
        if set(usage) != {"status"}:
            errors.append("result.usage unavailable must not carry fabricated token fields")
    else:
        usage_fields = (
            "inputTokens", "outputTokens", "cacheReadTokens", "cacheWriteTokens",
            "reasoningTokens", "totalTokens",
        )
        for field in usage_fields:
            if not router.is_int(usage.get(field)) or usage[field] < 0:
                errors.append(f"result.usage.{field} must be a non-negative integer")
        if all(router.is_int(usage.get(field)) for field in usage_fields):
            expected_total = usage["inputTokens"] + usage["outputTokens"] + usage["reasoningTokens"]
            if usage["totalTokens"] != expected_total:
                errors.append("result.usage.totalTokens must equal input + output + reasoning tokens")
    for field in ("changedPaths", "commandsExecuted"):
        value = receipt.get(field)
        if not isinstance(value, list) or not all(router.is_nonempty_string(item) for item in value):
            errors.append(f"result.{field} must be a string list")
    guard = dispatch.get("guard", {})
    paths = receipt.get("changedPaths") if isinstance(receipt.get("changedPaths"), list) else []
    allowed_paths = guard.get("exactWriteSet") if isinstance(guard.get("exactWriteSet"), list) else []
    if any(not router.path_allowed(path, allowed_paths) for path in paths):
        errors.append("result.changedPaths escaped the exact write-set")
    if any(not router.path_allowed(path, allowed_paths) for path in observed_changed_paths):
        errors.append("observed worktree diff escaped the exact write-set")
    if sorted(set(paths)) != observed_changed_paths:
        errors.append("result.changedPaths does not match the observed worktree diff")
    commands = receipt.get("commandsExecuted") if isinstance(receipt.get("commandsExecuted"), list) else []
    allowed_commands = guard.get("allowedCommands") if isinstance(guard.get("allowedCommands"), list) else []
    if any(command not in allowed_commands for command in commands):
        errors.append("result.commandsExecuted escaped the command guard")
    if errors:
        return {
            "ok": False,
            "decision": "block",
            "reason": "external_harness_process_receipt_invalid",
            "allowIntegration": False,
            "allowFallback": False,
            "errors": errors,
        }

    route_errors: list[str] = []
    for field, expected in (
        ("requestedModel", route.get("model")),
        ("actualModel", route.get("model")),
    ):
        if receipt.get(field) != expected:
            route_errors.append(f"result.{field} does not match the resolved route")
    route_errors.extend(router.validate_reasoning_policy(receipt, route.get("reasoning"), "result"))
    proof = receipt.get("modelIdentityProof")
    if (
        not router.is_plain_dict(proof)
        or proof.get("status") != "verified"
        or proof.get("method") != "durable_assistant_message"
        or proof.get("provider") != receipt.get("actualProvider")
        or proof.get("model") != receipt.get("actualModel")
        or proof.get("model") != route.get("model")
        or receipt.get("requestedProvider") != receipt.get("actualProvider")
    ):
        route_errors.append("result.modelIdentityProof does not verify the routed model")
    if route_errors:
        return {
            "ok": True,
            "decision": "fallback_required",
            "reason": "model_route_unavailable",
            "allowIntegration": False,
            "allowFallback": False,
            "fallbackRoute": dispatch["fallback"]["routeId"],
            "errors": [],
            "routeErrors": route_errors,
            "observedWorkspaceChangedPaths": observed_changed_paths,
        }

    complete = (
        process_exit == 0
        and receipt.get("cliExit") == 0
        and receipt.get("taskCompleted") is True
        and receipt.get("stopReason") == "completed"
        and receipt.get("timedOut") is False
        and receipt.get("toolPolicyCompliant") is True
        and not supervisor_timed_out
        and not forced_kill
    )
    if not complete:
        return {
            "ok": True,
            "decision": "fallback_required",
            "reason": "external_harness_execution_incomplete",
            "allowIntegration": False,
            "allowFallback": False,
            "fallbackRoute": dispatch["fallback"]["routeId"],
            "errors": [],
            "execution": {
                "processExitCode": process_exit,
                "cliExit": receipt.get("cliExit"),
                "taskCompleted": receipt.get("taskCompleted"),
                "stopReason": receipt.get("stopReason"),
                "supervisorTimedOut": supervisor_timed_out,
                "forcedKill": forced_kill,
            },
            "observedWorkspaceChangedPaths": observed_changed_paths,
            "candidateFrozen": bool(observed_changed_paths),
        }
    return {
        "ok": True,
        "decision": "candidate_review_required",
        "reason": "external_harness_execution_verified_pending_codex_review",
        "allowIntegration": False,
        "allowFallback": False,
        "errors": [],
        "candidateEvidence": receipt,
        "observedWorkspaceChangedPaths": observed_changed_paths,
    }


def execute(adapter: Any, dispatch: Any, request: Any) -> dict[str, Any]:
    route, workspace, contract_errors, launch_errors = _validate_launch(adapter, dispatch, request)
    if contract_errors:
        return {
            "ok": False,
            "decision": "block",
            "reason": "external_harness_contract_invalid",
            "allowIntegration": False,
            "allowFallback": False,
            "errors": contract_errors,
        }
    if launch_errors or route is None or workspace is None:
        return {
            "ok": True,
            "decision": "fallback_required",
            "reason": "model_route_unavailable",
            "allowIntegration": False,
            "allowFallback": False,
            "fallbackRoute": dispatch["fallback"]["routeId"],
            "errors": launch_errors,
        }
    process_exit, stdout, stderr, timed_out, forced_kill = _run_process(
        request["argv"],
        workspace,
        float(request["outerTimeoutSeconds"]),
        float(request["terminationGraceSeconds"]),
    )
    try:
        observed_changed_paths = _git_changed_paths(workspace)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return {
            "ok": False,
            "decision": "block",
            "reason": "external_harness_worktree_evidence_unavailable",
            "allowIntegration": False,
            "allowFallback": False,
            "errors": [str(exc)],
        }
    parse_errors: list[str] = []
    receipt = _parse_receipt(stdout, parse_errors)
    if receipt is None:
        return {
            "ok": False,
            "decision": "block",
            "reason": "external_harness_process_receipt_invalid",
            "allowIntegration": False,
            "allowFallback": False,
            "processExitCode": process_exit,
            "supervisorTimedOut": timed_out,
            "forcedKill": forced_kill,
            "observedWorkspaceChangedPaths": observed_changed_paths,
            "candidateFrozen": bool(observed_changed_paths),
            "stderrSummary": stderr[-4000:],
            "errors": parse_errors,
        }
    result = _validate_result(
        route, dispatch, process_exit, receipt, timed_out, forced_kill, observed_changed_paths
    )
    result["stderrSummary"] = stderr[-4000:]
    return result


def _load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute and gate one external Harness process.")
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--dispatch", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = execute(_load(args.adapter), _load(args.dispatch), _load(args.request))
    except (OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        result = {
            "ok": False,
            "decision": "block",
            "reason": "external_harness_execution_error",
            "allowIntegration": False,
            "allowFallback": False,
            "errors": [str(exc)],
        }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
