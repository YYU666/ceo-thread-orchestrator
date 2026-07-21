# CEO Flow OpenClaw MiniMax Session-Reuse Smoke

Date: 2026-07-20
Decision: **accept for R0 typed execution and project-role session reuse; R1 code-writing pilot remains unverified**

## Surface

- OpenClaw: `2026.7.1-2`
- Provider/model: `minimax/MiniMax-M3`
- OpenClaw skill: `ceoflow-external-executor` (`eligible=true`, workspace-scoped to the `main` Agent)
- Goal/heartbeat: no Codex Goal, heartbeat, polling loop, channel delivery, project write, publish, merge, or release was used.

## Probe

Two immutable R0 tasks used different task IDs and hashes but the same project-role session key:

```text
agent:main:ceoflow:ceoflow-minimax-probe:test-main
```

| Task | Task SHA-256 | Receipt summary | Receipt validation |
| --- | --- | --- | --- |
| `CEOFLOW-MINIMAX-SESSION-REUSE-PROBE-01` | `1878216b7c7b45813dfc1e93b841368725de89f19b630374b50f0276e76b62bc` | `MINIMAX_SESSION_REUSE_ACK_01` | pass |
| `CEOFLOW-MINIMAX-SESSION-REUSE-PROBE-02` | `3cecdbe90aad1f214db44a1edf5e13cb28add6880e485a4a0d8a0a589fee3cc0` | `MINIMAX_SESSION_REUSE_ACK_02` | pass |

Both receipts reported the same OpenClaw session ID:

```text
22c40672-747e-4bda-9ce4-9ad34dc56f3e
```

This proves that a second task can reuse the same project-role OpenClaw session rather than creating a session per task.

## Receipt Evidence

- exact task ID and task hash matched;
- status was `succeeded` for both tasks;
- actual model was `minimax/MiniMax-M3`;
- session key and session ID matched across both receipts;
- changed files, commands, tests, artifacts, blockers, and residual risks were empty as required;
- `forbiddenPayloadsPresent=false`;
- the bridge validator returned `ok=true`, with no warnings, for both receipts.

Provider-reported usage:

- task 1: input `1457`, output `4655` tokens;
- task 2: input `1864`, output `779` tokens;
- cost was not reported by the provider.

## Defects Found And Fixed During The Probe

1. At probe time, non-local tasks could incorrectly select an existing isolated `.openclaw-ceoflow` launcher. The current policy now removes that execution branch entirely and hard-blocks `localMode=true` and `ollama/<model>` routes until the user explicitly reopens local-model support in a future capability review.
2. New OpenClaw project sessions require `--session-key`; the task schema and bridge now support deterministic project-role keys.
3. OpenClaw `2026.7.1-2` requires target/session arguments before the message for reliable target selection. Command generation now follows that order.
4. Multiline task envelopes were truncated when passed through a Windows `.cmd` launcher with `--message`. Real execution now uses `--message-file` and deletes the temporary prompt file after the turn.
5. Raw command evidence now replaces the prompt or temporary prompt path with a placeholder instead of persisting the full task payload.

## Remaining Boundary

The smoke proves transport, Skill activation, MiniMax generation, hash-bound typed receipts, and same-session reuse. It does not prove code editing quality, repository write-set enforcement under a real diff, test execution, R1 neutral review, provider price, or production reliability. Those require a disposable prepared-snapshot R1 pilot before broader delegation.
