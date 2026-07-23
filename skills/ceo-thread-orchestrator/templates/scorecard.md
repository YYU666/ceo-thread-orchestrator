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

## Evidence

- [ ] Required verification command was run, or a not-run reason is explicit.
- [ ] Test/build/lint result is stated.
- [ ] Artifacts, screenshots, or output refs are listed when relevant.
- [ ] Failed tests and blockers are visible.

## External Execution Receipt

- [ ] External task schema, task ID, and task SHA-256 match the dispatch envelope.
- [ ] Provider, adapter, transport, run/session identifiers, actual model/reasoning, and usage availability are recorded.
- [ ] Exact project ID/root identity, CEO owner/lease, project-scoped session key, frontend display/category, and `frontendVisible=true` match the task.
- [ ] The physical session is a clean single-task generation, not `Main Session`, archived, busy, cross-project, or backed by OpenClaw native/global memory; writable work has one active writer and terminal sessions are archived.
- [ ] The task uses the dedicated `ceoflow-executor` Agent with `agentContextProfile=minimal-ceoflow`, not the default personal Agent.
- [ ] ProviderTaskView, initial/per-request/cumulative token limits, call budget, TPM headroom, and bounded tool-output policy are present and within risk-tier limits.
- [ ] Receipt validates; no write-set violation, forbidden publish/merge/release, secret, raw session, image/base64, or giant payload is present.
- [ ] Raw provider output remains cold evidence at a local path; CEO context uses only the compact receipt and inspectable evidence.
- [ ] External `succeeded` is treated as a completion claim, not CEO acceptance.

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
