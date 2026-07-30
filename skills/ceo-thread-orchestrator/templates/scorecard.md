# CEO Flow Scorecard

Use this scorecard before accepting pipeline work.

## Format

- [ ] Handoff is parseable or structured enough to inspect.
- [ ] Supported schema is declared: `typed_handoff_v1` or `review_handoff_v1`.
- [ ] `laneId` is present and matches the pipeline/task card.
- [ ] `status` or `decision` is present.

## Scope And Write-Set

- [ ] Changed files are listed.
- [ ] Changed files are inside the allowed write-set.
- [ ] Forbidden paths are not touched.
- [ ] Out-of-scope work is disclosed.
- [ ] If the Coding Discipline Gate triggered, profile identity/state is recorded, adjacent refactors are absent or disclosed, and scope deviations are handled by the task policy.

## Evidence

- [ ] Required verification command was run, or a not-run reason is explicit.
- [ ] Test/build/lint result is stated.
- [ ] Artifacts, screenshots, or output refs are listed when relevant.
- [ ] Failed tests and blockers are visible.
- [ ] Declared success criteria were checked with real evidence; worker/model self-acceptance is ignored.

## Review

- [ ] Dependencies were satisfied before review acceptance.
- [ ] Review decision is `accept`, `revise`, or `block`.
- [ ] Residual risk is stated.
- [ ] CEO final decision is evidence-based.

## Decision

```text
Decision: accept | revise | block | supersede
Evidence inspected:
Missing evidence:
Required fixes:
Residual risk:
Next owner:
```
