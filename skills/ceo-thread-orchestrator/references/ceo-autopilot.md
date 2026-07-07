# CEO Autopilot Reference

Use this reference for large/program project takeover, complete-product execution, active runtime Goals, broken CEO recovery, or any request where CEO Flow must automatically decide goal mode, lane count, thread reuse, harvest driver, review gates, and long-term memory alignment before execution.

CEO Autopilot is not a workflow daemon. It is a bounded startup/control card for large projects. Skip it for casual chat, tiny direct edits, and one-off low-risk tasks.

## Project Scale Classifier

Classify both the whole project and the current request:

```text
Project scale: tiny | small | medium | large | program
Task scale: tiny | small | medium | large | program
Scale evidence:
Operating consequence:
  Goal required:
  Memory Runtime required:
  Warm Anchor required:
  Staffing Plan required:
  Lane count target:
  Harvest driver:
```

Heuristic score:

```text
+2 PRD / TECHNICAL_DESIGN / Program Goal Brief exists
+2 .codex-knowledge or equivalent Memory Runtime exists
+2 user says continue / takeover / resume / recover / finish product / long-running
+2 multiple modules, domains, packages, or subsystems
+2 UI/UX/user-facing workflow matters
+2 release/build/package/readiness/commercial/open-source scope
+1 tests, artifacts, screenshots, or evidence folders exist
+1 multiple worker/review/thread history exists
+1 visual QA or local artifacts are required
+1 architecture principles, completion percentage, or readiness claims are affected

0-2: tiny/small
3-5: medium
6-8: large
9+: program/product-scale
```

Corrections:

- A large project can still receive a tiny task. Do not force heavy Autopilot for typo fixes or one-line low-risk edits.
- Any takeover, complete-product request, active runtime Goal, readiness/progress claim, or major acceptance is at least large for operating purposes.
- RGS/Zhixia-style complete products with long memory, many lanes, and recovery needs are program/product-scale.

## CEO Autopilot Startup Card

Run this card before execution when project scale is large/program, a new CEO takes over, a broken CEO thread is recovered, a runtime Goal is active, or the user asks to continue/finish a long-running product.

```text
CEO Autopilot Startup Card:
  Project scale:
  Task scale:
  Canonical project root:
  Program Goal Brief:
  Runtime Goal:
  Memory Runtime:
  Long-Term Memory Anchor Gate:
  Current phase:
  Completion Dashboard:
  Ready task graph:
  Worktree readiness:
  Repo Baseline Gate / dirty budget:
  Lane reuse candidates:
  Lane count decision:
  Staffing Plan:
  Harvest driver:
  Review / audit plan:
  Memory writeback plan:
  Bootstrap exit decision:
```

Rules:

1. Build the card from compact memory, current docs/source refs, thread roster, and current user request. Do not load raw sessions, giant Markdown, or image payloads.
2. If a Program Goal Brief is missing for a large/program task, create or name the intended brief before dispatch.
3. If runtime Goal tooling is available, bind/reuse exactly one Goal for the whole Program Goal; otherwise record fallback harvest driver.
4. Record why each ready task is dispatched, queued, serialized, or skipped.
5. Autopilot output is a control decision, not a license to create unnecessary threads.

## Bootstrap Exit Gate

CEO-only bootstrap is for state recovery only. It expires after the first state recovery report.

Bootstrap may do:

- read compact handoff / Program Goal / Memory Runtime project_resume;
- classify accepted / pending / conflict / stale;
- verify canonical project root and current evidence;
- identify next safe execution options.

After bootstrap, output:

```text
Bootstrap Exit Decision:
  Next mode: Core Team execution | Core Team harvest | CEO-only bounded | configured workflow | direct CEO fallback
  Why not continue CEO-only:
  If CEO-only continues, reason:
  Staffing check required:
  Next routed lane/review:
  Stop condition:
```

Do not let "first step: no workers" become a continuing execution policy. Continuing CEO-only after bootstrap requires a bounded reason and stop condition.

## Staffing Plan And Lane Count Decision

Before Core Team execution on large/program tasks, produce a Staffing Plan:

```text
Staffing Plan:
  CEO role:
  Implementation lanes:
  Review lanes:
  UX/Product lanes:
  QA/Test lanes:
  Memory/Knowledge lane:
  Contractor/subagent use:
  Lane count decision:
  Why not more lanes:
  Why not fewer lanes:
  Thread reuse:
  New thread needed:
  Worktree/canonical mode:
  Repo baseline mode:
```

Lane count guide:

- `0 lanes`: strategy, state recovery, tiny edit, read-only audit, or user explicitly asks single-thread.
- `1 lane`: one coherent write-set or one safe implementation owner.
- `2 lanes`: one implementation lane plus one independent review lane.
- `3 lanes`: one canonical single writer plus read-only QA/Test and Product/UX review.
- `3-5 lanes`: multiple independent modules with non-overlapping write-sets and enough harvest/review capacity.
- `pipeline`: broad PRD, dependency graph, fan-out/fan-in, typed handoffs, or scorecard needed.

Hard rule: `worktree blocked != no lanes`. If worktree implementation is unsafe, consider one canonical single-writer lane plus parallel read-only review, QA, UX/Product, architecture/preflight, or repo-baseline lanes. If dirty budget is red or critical untracked source/config/test exists, enter baseline mode before new feature worktree writers.

## Proof Loop Fuse

CEO-only proof/audit/test/support slices are useful, but they must not become a substitute for product-facing progress.

Trigger the fuse when:

- CEO completes two consecutive CEO-only proof/audit/test/support slices under a large/program task;
- proof/support slices update progress, readiness, or acceptance docs repeatedly;
- the next action is another proof-only slice instead of a product-facing wave;
- user questions over-proofing, over-testing, direction drift, or why CEO is working alone.

Record:

```text
Proof Loop Fuse:
  consecutive CEO-only proof/support count:
  last product-facing wave:
  current proof value:
  risk of local optimization:
  staffing check:
  Warm Anchor required:
  next product-facing action:
  neutral review needed:
```

After the fuse, CEO must either restore Core Team routing, dispatch/read a neutral review, return to a product-facing wave, or record why only one more bounded CEO-only slice is safe.

CEO-only continuation requires:

```text
CEO-only continuation reason:
Why no worker/review lane:
Max one-slice stop condition:
Next staffing checkpoint:
```

## Large-Project Execution Loop

For large/program projects, each substantial cycle should follow:

1. Scale classify and refresh Autopilot Card when entering a new phase/wave/takeover.
2. Run Memory Runtime project_resume/task_dispatch as required.
3. Run Long-Term Memory Anchor Gate at direction-sensitive nodes.
4. Build or update task graph and lane count decision.
5. Dispatch compact task cards or record a bounded CEO-only reason.
6. Harvest evidence, classify lanes, and run review gates.
7. Update Program Goal/Completion Dashboard and memory candidates.
8. After terminal lane/module/proof results, run portfolio steering and proof-loop fuse if triggered.

Keep this loop light. If it feels heavy, reduce lanes; do not delete the control decisions.
