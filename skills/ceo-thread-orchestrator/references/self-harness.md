# Failure-Triggered Reflection And Self-Harness

Use this reference only when CEO Flow behavior appears to fail, drift, repeat a process mistake, or needs a rule-candidate change. Do not run this routine for ordinary successful tasks.

## Contents

- Boundary and triggers
- Failure codes and reflection packet
- Promotion, regression, revert, and reporting

## Boundary

Self-reflection is a diagnostic step, not an automatic rule updater.

```text
Reflection proposes.
Harness verifies.
CEO decides accept | revise | block.
Only accepted evidence-backed rules enter the skill.
```

Do not use reflection as a generic apology, motivational summary, or always-on process tax.

## Trigger Conditions

Trigger failure reflection only when at least one is true:

- tests, validator, build, privacy scan, or required verification failed;
- CEO Flow explicit rules were violated;
- worker/review/lane output lacks required evidence for acceptance;
- user reports process drift, such as single-thread drift, missing parallelism, missing review, wrong workspace, or premature MVP stop;
- the same revise/block/supersede pattern appears twice;
- a worker/reviewer shows role contamination;
- a harvest driver targets a stale or superseded lane;
- a rule change to CEO Flow is being considered.

Do not trigger it for ordinary tiny edits, style preferences, harmless wording issues, or tasks that are accepted with sufficient evidence.

## Failure Codes

Use concrete codes instead of vague "I should be more careful" reflections:

```text
direct_ceo_fallback_leak
goal_single_thread_drift
missing_lane_roster
missing_parallel_wave
missing_review_gate
rubber_stamp_review
worker_role_contamination
stale_harvest_target
approval_stall_deadlock
workspace_mismatch
context_overload
premature_mvp_stop
insufficient_evidence
reasoning_direction_violation
tool_contract_limit
user_scope_change
```

Classify the cause:

```text
execution_failure  # rule existed but the agent did not follow it
rule_gap           # rule was missing or ambiguous
tool_limit         # host/tool surface cannot support the intended behavior
user_scope_change  # user changed goal or constraints
```

## Minimal Reflection Packet

Default to the short packet:

```text
Failure:
Expected:
Actual:
Failure code:
Cause class:
Minimal correction:
Regression check:
Promote to: no change | smoke prompt | reference | SKILL.md | project memory
```

Use a longer packet only when a public skill rule change is likely:

```text
Original user goal:
Interpreted goal:
Role expected:
Role actually used:
Evidence used:
Evidence missing:
Decision path:
Alternative paths not taken:
User impact:
Minimal rule candidate:
Transfer boundary:
Do not apply when:
Regression tests:
Rollback plan:
Decision:
```

## Promotion Gate

Do not promote a reflection into the skill unless:

1. The failure is reproducible or high-impact.
2. Evidence shows the issue is a rule gap, not only a one-off execution mistake.
3. The candidate rule is smaller than the failure it prevents.
4. A smoke prompt or validator can check the behavior.
5. The rule does not make ordinary small tasks heavier.
6. Public docs remain free of private paths, thread ids, secrets, and local workflow assumptions.

Promotion order:

```text
no change -> smoke prompt -> reference rule -> SKILL.md core rule
```

Prefer reference rules over expanding `SKILL.md`. Put only high-frequency or high-risk gates in `SKILL.md`.

## Regression And Revert

Every promoted rule needs a regression check:

```text
Positive case: behavior that should now happen.
Negative case: ordinary task that must not become heavier.
Evidence: smoke prompt, validator, or real-thread observation.
Revert condition: when the rule causes excessive ceremony, false positives, or slower execution without quality gain.
```

If a rule causes recurring false positives, move it from `SKILL.md` to a reference, narrow its trigger, or revert it.

## Chat Reporting

Keep user-facing reports short:

```text
Decision:
Failure code:
Cause:
Minimal correction:
Regression check:
Files changed or proposed:
```

Do not dump full reflection packets into chat unless the user asks.
