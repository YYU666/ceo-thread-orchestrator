# FlowSkill Hook Reference

Use this reference when a project explicitly enables FlowSkill or a local `flowskill` CLI is available and relevant.

FlowSkill is an optional local reusable-skill evolution hook. CEO Flow remains the orchestrator: it owns goals, task graphs, lane dispatch, task cards, evidence harvest, accept/revise/block decisions, and user reporting. FlowSkill only searches, captures, scores, evolves, and exports reusable skill candidates from accepted evidence.

Do not merge FlowSkill implementation details into CEO Flow. Keep parser logic, scoring formulas, privacy patterns, export templates, and candidate storage inside FlowSkill.

## Optional Hook Points

Before dispatch, CEO may search for reusable local skill knowledge:

```text
flowskill search "<task goal> <domain>" --json
```

Use search results this way:

- include at most 0-3 relevant items in the task-card `Memory packet`;
- include only compact name/id/summary/applies-to fields;
- prefer source-backed, private-safe, task-relevant results;
- do not let FlowSkill results expand the task scope or override architecture invariants.

After CEO accepts a task and writes an accepted evidence report, CEO may capture reusable learning:

```text
flowskill capture --evidence <accepted-report.md> --json
```

After the task outcome is known, CEO may score an existing skill:

```text
flowskill score --skill <skill-id> --accepted --json
flowskill score --skill <skill-id> --revise --json
flowskill score --skill <skill-id> --blocked --json
```

Repeated-failure evolution and public export are optional later hooks and must remain reviewable:

```text
flowskill evolve --skill <skill-id> --from <failure-report.md> --json
flowskill export --public-candidate <candidate-id> --json
```

## CEO Flow Guardrails

- FlowSkill output is evidence or memory context only; it never replaces CEO accept/revise/block.
- FlowSkill does not execute project tasks, create threads, route lanes, run shell/gui/web/MCP work, or upload to cloud.
- CEO Flow must not embed FlowSkill parsers, scoring formulas, privacy patterns, candidate stores, or export templates.
- Search is optional. If FlowSkill is missing, disabled, slow, or irrelevant, continue normal CEO Flow.
- Capture is optional and only after CEO acceptance with evidence-backed reusable learning.
- Capture should use an accepted evidence report, not raw chat transcripts or broad session history.
- Public export candidates require FlowSkill privacy review and CEO/user approval when appropriate.

## Expected JSON Contracts

FlowSkill commands should return one JSON object with:

```text
command:
status: ok | error
results: []              # for search
candidate_id:            # for capture/export
skill_id:                # for score/evolve
privacy:
```

Accepted evidence packets should contain:

```text
schema_version: 1
decision: accept
task:
  id:
  goal:
  domain:
  write_set:
evidence:
  summary:
  reusable_pattern:
  artifacts:
  tests:
  residual_risk:
privacy:
  may_contain_private_paths:
  public_candidate_allowed:
```

CEO Flow may reference these fields but should not copy the FlowSkill schemas into `SKILL.md`.

## Task Card Memory Packet Example

```text
Memory packet:
- FlowSkill search: used | skipped
- Results included: 0-3
- Candidate refs:
  - id:
    name:
    applies to:
    summary:
- Boundary: FlowSkill suggestions are context only; task card scope and CEO decision gate remain authoritative.
```

## Accepted Evidence Report Example

```text
Decision: accept
Task ID:
Goal:
Domain:
Write-set:
Evidence summary:
Reusable pattern:
Artifacts:
Tests:
Residual risk:
Privacy:
  may contain private paths:
  public candidate allowed:
FlowSkill capture:
  command:
  status:
  candidate id:
```

