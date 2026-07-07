# Repo Baseline Gate Reference

Use this reference when CEO Flow is about to dispatch worktree implementation lanes, when a project has many dirty or untracked files, or when accepted slices are accumulating faster than the repository baseline is being made reproducible.

CEO Flow is not only a task orchestrator; it is also a repository state gatekeeper. If the canonical project root cannot be reproduced from git or an explicitly prepared snapshot, worktree implementation lanes are unsafe.

## Repo Baseline Gate

Run this gate before any worktree writer and after suspicious repo growth.

Trigger the gate when any condition is true:

- preparing to create, reuse, fork, or hand off a worktree implementation lane;
- any untracked critical file exists under `src/**`, `app/**`, `tests/**`, `test/**`, `scripts/**`, or equivalent source/test roots;
- any untracked project config/build file exists, including `package.json`, lockfiles, `tsconfig*`, `vite.config*`, `webpack*`, `electron*`, `tauri*`, test config, or app entrypoints;
- dirty files exceed 30;
- dirty files exceed 20 and the next task is another implementation slice;
- one worker finishes with more than 10 new untracked source, test, config, or docs files;
- three accepted implementation slices occurred since the last repo-state audit;
- a worker needed files that were present only in the canonical workspace and not in git/worktree.

Output:

```text
Repo Baseline Gate:
  dirty count:
  untracked critical source/config/test count:
  untracked docs/artifacts count:
  tracked baseline covers package/config/build:
  tracked baseline covers task source/test roots:
  worktree can reproduce project without canonical-only files:
  dirty budget state: green | yellow | red
  decision: ready | baseline_required | canonical_single_writer_only | read_only_only
  controlled baseline task needed: yes/no
  reason:
```

## Dirty Budget

Use numeric discipline so CEO does not keep accepting feature slices while the repo becomes unreproducible.

```text
dirty < 20: green; normal routing may continue if worktree readiness passes.
dirty 20-50: yellow; at most one canonical writer, plus read-only review/audit/QA. Record why more writing is safe.
dirty > 50: red; enter baseline mode before further product feature writing unless there is an explicit emergency unblock.
untracked critical source/config/test > 0 and preparing worktree writer: hard block.
```

Dirty means modified, added, deleted, renamed, copied, or untracked files visible in `git status --short`, not ignored cache files. Critical source/config/test means files needed to build, test, run, or understand the product, not local artifacts or generated output.

## Strong Worktree Block

If critical source, tests, or config are not tracked or intentionally included in an explicit snapshot, CEO must block worktree implementation lanes.

Forbidden bypasses:

- do not ask a worker worktree to read or copy missing files from the canonical workspace;
- do not let each worker invent its own snapshot;
- do not continue worktree writers while saying the worker can resolve missing files later;
- do not treat worktree failure as proof that all lanes are impossible.

Allowed while blocked:

- one canonical single-writer implementation lane, if write-set ownership is clear;
- read-only QA/Test, Product/UX, architecture, docs, or repo-baseline audit lanes;
- a controlled repo baseline task;
- CEO-only planning/review only when no safe lane work exists.

Hard sentence: if git cannot reproduce the canonical root, baseline first, then parallelize.

## Closure Gate After Accepted Slices

Before accepting each implementation slice, record repository state, not only test success.

```text
Slice Closure Gate:
  task id:
  changed files:
  untracked files:
  new untracked source/config/test/docs count:
  allowed write-set compliance:
  shared files touched:
  package/config changed: yes/no
  artifacts/docs are local evidence only: yes/no
  worktree readiness impact: improved | unchanged | worse | unknown
  baseline action needed: none | stage pathspec proposal | controlled baseline task | block next worktree writer
  evidence refs:
```

Do not mark a slice accepted solely because tests passed. If the slice worsens baseline readiness, accept only with a recorded baseline action or classify as revise/block when reproducibility risk is material.

## Continuous Baseline Audit

After every three accepted implementation slices, or sooner if dirty budget reaches yellow/red, CEO must run a repo-state audit before dispatching more feature work.

Audit checks:

- `git status --short` count and categories;
- critical untracked source/config/test/docs;
- whether package/config/build files are tracked;
- whether source/test roots needed by ready tasks are tracked;
- whether visual artifacts are local evidence only and excluded from hot memory/callbacks;
- whether worktree readiness improved, stayed the same, or degraded;
- whether next tasks must be downgraded to read-only or canonical single-writer.

If the audit finds continuous source/test creation without baseline, downgrade future feature dispatch to `canonical_single_writer_only` or `read_only_only` until a controlled baseline task runs.

## Worker File Ownership Preflight

Implementation task cards must declare file ownership before edits:

```text
File ownership:
  allowed write-set:
  forbidden files:
  shared file owner:
  package/config changes allowed: yes/no
  new docs allowed: yes/no
  new artifacts allowed: yes/no
  expected untracked outputs:
  baseline incorporation plan:
```

No implementation dispatch when the write-set is vague for a dirty repo. If package/config changes are allowed, neutral review is mandatory before acceptance.

## Controlled Repo Baseline Task Template

Use this when baseline mode is required. The task makes the current canonical project reproducible; it does not implement product features.

```text
Task: CONTROLLED_REPO_BASELINE_<id>
Goal: make current canonical project reproducible from git or an explicitly prepared snapshot.
Do not implement product features.
Do not delete, clean, reset, or run `git add .`.
Create an explicit pathspec.
Stage/propose only source, test, config, scripts, and necessary docs.
Exclude artifacts, dist/build output, node_modules, caches, raw sessions, private memory, generated heavy files, screenshots, base64 payloads, and secrets.
Run/report:
- git status --short categorized counts
- git diff --cached --name-status, if staging is authorized
- git diff --cached --check, if staging is authorized
- payload/base64/image scan on staged/proposed files
- typecheck/test/build commands appropriate to the project
Report worktree readiness: safe | still_blocked | canonical_single_writer_only
Report residual risks and exact next pathspec, not broad `git add .`.
```

If the user has not authorized staging, produce a baseline proposal and pathspec only. Do not commit or publish unless explicitly asked.

## Acceptance And Dispatch Consequences

- `ready`: worktree implementation lanes may be considered, subject to normal parallel/write-set/resource gates.
- `baseline_required`: dispatch a controlled repo baseline task before worktree writers.
- `canonical_single_writer_only`: allow at most one implementation writer in the canonical workspace plus read-only parallel lanes.
- `read_only_only`: do not dispatch writers until the repo state is understood or the user approves a baseline repair.

This gate should make CEO Flow more decisive, not heavier. Run it from counts and focused path checks; do not dump full diffs or giant artifacts into the CEO thread.
