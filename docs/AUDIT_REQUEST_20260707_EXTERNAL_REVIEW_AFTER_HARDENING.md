# External Audit Request: CEO Flow Hardening Follow-up Review

- Date: 2026-07-07
- Target repository: <https://github.com/YYU666/ceo-thread-orchestrator>
- Target branch: `main`
- Target commit to review: `e24c5ea Harden validators and public release gates`
- Requested mode: external, adversarial, evidence-first review

## Audit Principle

Do not trust repository claims by default. Prefer code inspection, adversarial samples, and script execution. Documentation saying "fixed" is not evidence unless the code and tests prove it.

## Background

A previous external audit found that CEO Flow's main risk was not its orchestration idea, but weak engineering enforcement:

- `scorecard_handoff.py` could be bypassed by adding a `decision:` field to an implementation handoff.
- Review reports mentioning "done criteria" could trigger a false failure.
- `validate_pipeline.py` used regex-like YAML parsing and missed dependency cycles, `parallelWith` ghost lanes, and write-set prefix overlap.
- `smoke_eval.py` output could be misread as LLM behavior proof, though it only checked policy-term coverage.
- `plugin.json` versioning drifted from git tags/releases.
- There was no CI.
- Public docs over-coupled the core skill to private/local tools such as Zhixia and Guardian.
- `SKILL.md` Critical Path had become too long.
- Prompt-injection / untrusted-input boundaries were not structurally clear enough.

The repository now claims these issues were addressed in commit `e24c5ea`. Please verify whether the remediation is real.

## Claimed Remediation To Verify

### 1. `scorecard_handoff.py` rewritten

Expected changes:

- Uses PyYAML / structured parsing.
- Report type is determined only by top-level key: `handoff:` or `review:`.
- Arbitrary content fields such as `decision:` must not determine the report type.
- `writeSetCompliant: false` cannot be bypassed.
- Review text containing "done criteria" should not fail as a bare done-style report.
- `status`, `decision`, and `confidence` values are validated.
- real visual payload markers such as `data:image/...;base64,` or long base64-like blobs are rejected, while ordinary prose mentioning `base64,` should not false-positive.

### 2. `validate_pipeline.py` rewritten

Expected changes:

- Uses PyYAML / structured parsing.
- Validates required top-level and lane fields.
- Validates `dependsOn` references.
- Validates `parallelWith` references.
- Detects dependency cycles.
- Detects obvious write-set prefix overlap.
- Handles legal YAML indentation without silently dropping lists.

### 3. Adversarial tests added

Expected file:

```text
tests/test_validators.py
```

Expected coverage:

- Implementation handoff containing `decision:` still fails when `writeSetCompliant: false`.
- Review reason containing "All done criteria met." passes.
- `confidence: banana` fails.
- Pipeline dependency cycle fails.
- 2-space indentation with ghost lanes fails.
- Bundled templates pass.

### 4. CI added

Expected file:

```text
.github/workflows/ci.yml
```

Expected CI checks:

- `python scripts/smoke_eval.py`
- `python -m unittest discover -s tests -v`
- bundled pipeline validator
- bundled typed/review handoff validators
- `python scripts/check_release_state.py`

### 5. Release-state discipline added

Expected file:

```text
scripts/check_release_state.py
```

Expected behavior:

- Current `.codex-plugin/plugin.json` version should be `0.2.7-dev`.
- Dev versions may exist without a matching tag.
- Non-dev release versions must have a matching `vX.Y.Z` git tag.

### 6. Documentation validation wording corrected

Expected documentation behavior:

- README says `smoke_eval.py` is a static documentation coverage check, not an LLM behavior evaluation.
- Public reproducible checks are the default validation path.
- Codex internal `quick_validate.py` / `validate_plugin.py` are optional, not required for external contributors.
- `docs/CEO_FLOW_RELEASE_GATE_2026-06-11.md` states the old release gate was revised/superseded by the 2026-07-07 external audit.

### 7. Private tool coupling reduced

Expected documentation behavior:

- Public core should be expressed as `Memory Runtime provider`, `history-provider`, `project-memory`, and `hybrid`.
- Zhixia / Guardian should be optional local implementations or historical design notes, not public prerequisites.
- Optional provider contract should exist at:

```text
docs/optional-integrations/MEMORY_AND_HISTORY_PROVIDERS.md
```

### 8. `SKILL.md` slimmed

Expected behavior:

- `SKILL.md` Critical Path should be a 10-step decision tree, not a 30-step checklist.
- Detailed policy should remain in references.
- `skills/ceo-thread-orchestrator/agents/openai.yaml` default prompt should be shorter and not a long single sentence.

### 9. Trust boundary / prompt injection guard added

Expected behavior:

- `SKILL.md` should include `Structured Trust Boundary`.
- `pipeline-contract.md` should state that worker/reviewer/callback/memory/history outputs are untrusted data.
- Free-text fields are data, not instructions.
- Worker output must not mutate CEO role, model, reasoning, permissions, quality gates, acceptance policy, or project scope.
- Handoff type must be decided by schema/top-level key, not arbitrary free text.

## Required Audit Output Structure

### 1. Audit Summary

Report:

- current commit hash inspected;
- whether the claimed remediation is present;
- decision: `accept | revise | block`;
- largest remaining risk.

### 2. Reproducible Validation

Run and report outputs:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/smoke_eval.py
python scripts/check_release_state.py
python skills/ceo-thread-orchestrator/scripts/validate_pipeline.py skills/ceo-thread-orchestrator/templates/pipeline.yaml --json
python skills/ceo-thread-orchestrator/scripts/scorecard_handoff.py skills/ceo-thread-orchestrator/templates/typed_handoff.yaml --json
python skills/ceo-thread-orchestrator/scripts/scorecard_handoff.py skills/ceo-thread-orchestrator/templates/review_handoff.yaml --json
```

### 3. Adversarial Sample Retest

Create temporary samples and test at least these cases. Report actual output and judgment for each.

#### `scorecard_handoff.py`

1. Implementation handoff includes `decision: accept` and `writeSetCompliant: false`; expected: fail.
2. Review reason includes `All done criteria met.`; expected: pass.
3. Review `confidence: banana`; expected: fail.
4. Handoff or review contains `data:image/...;base64,` or a long base64-like blob; expected: fail. Ordinary prose such as "we avoided base64, image payloads" should pass.

#### `validate_pipeline.py`

1. `A dependsOn B`, `B dependsOn A`; expected: fail.
2. Lane depends on ghost lane; expected: fail.
3. Lane `parallelWith` ghost lane; expected: fail.
4. Two implementation lanes write `src/a/**` and `src/a/sub/**`; expected: warning at minimum.
5. Legal 2-space YAML list indentation must not cause silent missed references.

### 4. CI And Release Discipline

Check:

- `.github/workflows/ci.yml` exists.
- CI contains the public reproducible checks.
- `plugin.json` version is dev or has a matching tag.
- `check_release_state.py` handles dev and non-dev versions correctly.
- README does not describe moving main as a stable release.

### 5. Documentation Consistency

Check:

- README Repository Structure matches current file tree.
- README Validation accurately separates public reproducible checks from optional Codex internal validators.
- `smoke_eval.py` is described as documentation coverage, not LLM behavior proof.
- Old release gate has a superseded/revised note.
- Historical optional-integration docs are clearly marked as historical/optional.

### 6. Private Tool Coupling

Check whether public core docs still imply that private/local tools are required. Look especially for:

- Zhixia / Guardian presented as required rather than optional examples;
- nonexistent private files or commands written as public required workflow;
- unclear provider abstraction;
- language that might mislead external users about what they can run.

### 7. `SKILL.md` Complexity

Check:

- whether the Critical Path is now a 10-step decision tree;
- whether the main skill remains too heavy;
- whether reference routing is clear;
- whether the skill still feels like accident-patch accumulation.

### 8. Prompt Injection / Trust Boundary

Check:

- whether free-text-as-data is clearly stated;
- whether validators avoid using free-text/content fields to choose report type;
- whether worker callbacks or memory items could still mutate CEO behavior;
- whether stronger JSON Schema / Pydantic validation should be recommended.

### 9. Remaining Risks And Recommendations

Group recommendations by priority:

- **P0**: must fix immediately; remediation cannot be accepted otherwise.
- **P1**: should fix before stable release.
- **P2**: later improvement.

### 10. Final Conclusion

Answer explicitly:

- Did this remediation truly fix the previous high-risk issues?
- Is current `main` safer than commit `56c6d9f`?
- Can this be released as a stable release now?
- If not, what is missing?
- Should the repo keep `0.2.7-dev`, or tag/release?
