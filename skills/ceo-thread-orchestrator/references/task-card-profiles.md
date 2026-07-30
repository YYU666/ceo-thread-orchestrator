# Task Card Profiles

Choose the smallest profile that safely carries the task. The old full field
inventory is a reference checklist, not a default prompt payload.

## Minimal

Use for tiny bounded work, read-only review, or a trusted existing lane.

Required fields:

```text
Profile: minimal
Task ID / role:
ProjectIdentityEnvelope ref:
Goal:
Allowed read/write-set:
Do not touch:
Acceptance:
Verification:
Stop condition:
Return: changed files + evidence + risks + next action
```

Add a memory source-ref line only when Memory Trigger Gate fires. A minimal card
does not repeat staffing, model-routing, visual, repo, or continuity fields that
are not relevant.

## Standard

Use for ordinary implementation/review lanes in a substantial project.

```text
Profile: standard
Task ID / parent goal / lane role:
ProjectIdentityEnvelope ref:
Execution surface / lane reuse decision:
Repo/worktree readiness and file ownership:
Goal / non-goals:
Allowed write-set / forbidden files:
Relevant sourceRefs / compact memory result or skipped reason:
Dependencies / parallel safety:
Acceptance criteria:
Required verification:
Coding Discipline Gate, when triggered:
Visual evidence policy, when relevant:
Approval/command boundary:
Callback and stop condition:
Return: files, commands/tests, artifacts, risks, memory candidate
```

## R1

Use only for an admitted CMMD bounded writer after stable R1 readiness has been
accepted. Do not hand-author the full task in prose; reference the exact
versioned task envelope, Context View, lease, schema hashes, and readiness
evidence.

```text
Profile: R1
Task envelope path + SHA-256:
ProjectIdentityEnvelope + SHA-256:
Context View path + SHA-256:
Authorization lease path + SHA-256:
Stable schema snapshot hashes:
Accepted R1 readiness evidence:
Coding Discipline Profile ID/state/SHA-256, when triggered:
Write-set / command allowlist / budgets:
Requested provider/model/reasoning; fallback=deny:
Receipt path and CEO review gate:
```

R1 is not enabled merely because these fields are present. In the bundled
snapshot it remains fail-closed and future-gated.

## Selection Rule

- Start at `minimal`.
- Upgrade to `standard` when writes, repo safety, continuity, multiple lanes,
  visual evidence, or significant verification require it.
- Use `R1` only for the admitted external writer contract.
- Add the compact Coding Discipline Gate only for non-trivial coding writer or
  reviewer work. The recorded CMMD candidate is default-off and fields alone
  never enable it or R1.
- Never include empty optional fields to make a task card look complete.
- Raw chats, raw sessions, giant memory files, image bodies/base64, full logs,
  and provider self-routing instructions are forbidden in every profile.
