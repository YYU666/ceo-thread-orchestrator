# Contributing

Thanks for helping improve CEO Thread Orchestrator.

This project is a Codex plugin/skill for orchestration behavior, so the most useful contributions are clear behavior improvements, safer routing rules, realistic smoke tests, and concise documentation.

## Good First Contributions

- Add or refine smoke prompts in `examples/smoke-prompts.md`.
- Report where the CEO lane still falls back into direct implementation too quickly.
- Improve the goal-loop, memory-packet, or review-gate instructions.
- Add examples for different Codex tool surfaces.
- Clarify installation or validation steps.

## Before You Open A Pull Request

1. Keep changes narrow and behavior-focused.
2. Avoid adding private local paths, private workflow names, account-specific model ids, or secrets.
3. Prefer concise instruction changes over long process documents.
4. Run the skill validator when possible:

```powershell
python <path-to-skill-creator>/scripts/quick_validate.py .\skills\ceo-thread-orchestrator
```

5. Run the plugin validator when available:

```powershell
python <path-to-plugin-creator>/scripts/validate_plugin.py .
```

## Pull Request Checklist

- The change has a clear user-facing behavior reason.
- The skill remains generic and not tied to a private local workflow.
- New orchestration rules include a smoke prompt when practical.
- Validation results are included in the PR description.
- The README is updated if the public behavior or install story changes.

## Reporting Problems

When reporting behavior bugs, include:

- the prompt that triggered the behavior;
- whether thread tools, worktrees, automations, or subagents were available;
- what the CEO did;
- what you expected instead;
- whether the issue appeared in a fresh thread after reinstall/restart.

Please do not include secrets, API keys, private repo names, or full chat transcripts unless they are sanitized.
