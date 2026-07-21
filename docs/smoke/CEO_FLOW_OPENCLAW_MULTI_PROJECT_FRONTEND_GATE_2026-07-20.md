# CEO Flow OpenClaw Multi-Project And Frontend Gate Smoke

Date: 2026-07-20

Decision: `accept` for local gate implementation; `revise` for the live provider E2E until a cloud model turn returns a valid receipt.

## Upgrade

- Bound each external task to project ID, display name, normalized canonical root, project identity SHA-256, and CEO owner.
- Kept deterministic project-role session keys and prohibited `Main Session` or cross-project reuse.
- Added project-local external session roster, dispatch lease, one-writer conflict detection, archived/broken/superseded lifecycle blocking, and compact receipt state.
- Added OpenClaw frontend registration through official Gateway `sessions.create` and `sessions.patch` methods.
- Required project-scoped `<Project> · <Role>` display names and project categories.
- Added archived/busy session rejection and post-registration key/label/category/session verification before model execution.
- Kept local models, OpenClaw nested delegation, native OpenClaw memory, publication, merge, release, and external messaging disabled.

## Verification

- Python unit tests: `27/27 PASS`.
- Static CEO Flow smoke evaluation: `72/72 PASS`.
- Repository Skill validator: pass.
- Plugin validator: pass.
- Task template validation and non-executing OpenClaw command rendering: pass.
- JSON syntax checks for task, receipt, and session-roster schemas/templates: pass.
- `git diff --check`: pass.

## Covered Failure Cases

- different projects attempt to share one session key;
- canonical root changes without updating project identity;
- generic or cross-project frontend display names;
- OpenClaw native-memory permission is enabled;
- archived or busy session reuse;
- second CEO owner conflicts with the project roster;
- a second writer lease attempts to run in the same project;
- frontend registration uses direct session-store editing instead of Gateway APIs.

## Residual Boundary

The tests prove routing, schema, roster, and official Gateway command behavior. A controlled read-only live probe then created and reused one `CEO Flow · Frontend Probe` session through the Gateway. Session listing confirmed the expected label, session ID, `thinking=off`, and terminal timeout state; trajectory evidence confirmed context compilation and prompt submission.

The first dispatch was blocked before model generation because the narrower `openclaw sessions` CLI list omitted category even though Gateway patching persisted it. An independent RGS preflight reproduced the same failure. The bridge now uses Gateway `sessions.list` for active and archived lookups and verifies its complete key/session/label/category/archived/hasActiveRun/thinkingOptions projection.

The next dispatch exposed an unsupported guessed thinking level (`low`) for MiniMax-M3; the revised task used an advertised supported value (`off`). The real model request then timed out, and OpenClaw automatically attempted its configured higher-cost fallback. No valid receipt or reported token usage was produced. CEO Flow now reads model status before execution and blocks configured fallback routes unless the task explicitly names CEO-approved fallback models.

The remaining E2E requirement is one successful cloud-model response plus user confirmation that the named frontend session rendered the input, Activity, and final output. No further automatic retries are allowed under the probe's one-attempt budget.
