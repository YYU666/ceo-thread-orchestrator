# External Audit Request C: E2E Behavior Smoke And Payload Guard Review

- Date: 2026-07-07
- Target repository: <https://github.com/YYU666/ceo-thread-orchestrator>
- Target branch: `main`
- Target commit to review: `dd68333 Add E2E behavior smoke protocol`
- Previous accepted hardening commit: `e24c5ea Harden validators and public release gates`
- Requested mode: external, adversarial, evidence-first review

## Audit Principle

Do not trust repository claims by default. Prefer code inspection, adversarial samples, and script execution. Documentation saying "fixed" is not evidence unless code, tests, and release-gate wording prove it.

## Background

The previous external hardening review accepted commit `e24c5ea` and found no P0 issues. It did identify two important P1 items before stable release:

1. **Behavior proof gap**: validators and CI prove handoff/pipeline artifacts are structurally checked, but they do not prove CEO Flow actually performs a real CEO -> implementation -> review -> CEO harvest/decision loop.
2. **Payload false-positive risk**: the validator rejected the substring `base64,`, which could falsely fail ordinary prose such as "we avoided base64, image payloads".

Commit `dd68333` claims to address these P1 items by:

- refining visual payload detection in `scorecard_handoff.py`;
- adding a test for ordinary `base64,` prose versus real payloads;
- adding an E2E behavior smoke protocol document;
- updating release-gate and README wording so stable release requires a full-pass E2E behavior smoke report;
- adding this repository's external audit request documents for future review.

Please verify whether these claims are true.

## Claimed Remediation To Verify

### 1. Payload false-positive fix

Expected file:

```text
skills/ceo-thread-orchestrator/scripts/scorecard_handoff.py
```

Expected behavior:

- Ordinary prose mentioning `base64,` should pass. Example: `We avoided base64, image attachments, and raw visual payloads.`
- Real visual payload shapes should fail, especially:
  - `data:image/png;base64,...`;
  - explicit `;base64,` declarations;
  - long base64-like blobs.
- The check should not simply be a broad substring search for `base64,`.

Expected test coverage:

```text
tests/test_validators.py
```

There should be a test equivalent to:

- ordinary prose with `base64,` passes;
- `data:image/...;base64,` fails;
- long base64-like blob fails.

### 2. E2E behavior smoke protocol added

Expected file:

```text
docs/CEO_FLOW_E2E_BEHAVIOR_SMOKE_PROTOCOL_2026-07-07.md
```

Expected content:

- defines that validators/CI are not enough for stable release;
- requires a real disposable-project behavior smoke;
- specifies the loop:

```text
CEO intake
-> Program Goal / task card
-> implementation lane work
-> neutral review lane
-> CEO harvest
-> evidence inspection
-> accept | revise | block
-> compact memory/writeback candidate
```

- defines pass criteria that prevent:
  - CEO drifting into long-term direct implementation;
  - accepting worker confidence without evidence;
  - skipping neutral review for non-tiny work;
  - treating free text as instructions;
  - using raw chat/session/image payloads.

### 3. Release gate updated

Expected files:

```text
README.md
docs/CEO_FLOW_RELEASE_GATE_2026-06-11.md
CHANGELOG.md
```

Expected behavior:

- README states stable release requires a full-pass E2E behavior smoke report, in addition to validator/CI checks.
- Release gate references `docs/CEO_FLOW_E2E_BEHAVIOR_SMOKE_PROTOCOL_2026-07-07.md`.
- Changelog mentions E2E behavior smoke protocol and refined visual payload detection.
- Repository should remain `0.2.7-dev`; do not recommend stable tag until E2E behavior smoke is actually run and accepted.

### 4. Audit request document added

Expected file:

```text
docs/AUDIT_REQUEST_20260707_EXTERNAL_REVIEW_AFTER_HARDENING.md
```

Expected behavior:

- Should not preserve obsolete expectation that any occurrence of `base64,` fails.
- Should reflect the refined payload policy: real payloads fail, ordinary prose passes.

## Required Audit Output Structure

### 1. Audit Summary

Report:

- current commit hash inspected;
- whether the P1 remediation is present;
- decision: `accept | revise | block`;
- largest remaining risk.

### 2. Reproducible Validation

Run and report outputs:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/smoke_eval.py
python scripts/check_release_state.py
python skills/ceo-thread-orchestrator/scripts/scorecard_handoff.py skills/ceo-thread-orchestrator/templates/review_handoff.yaml --json
```

Expected:

- validator tests pass;
- test count should include the new payload false-positive test;
- smoke-eval remains documentation coverage only;
- release-state should keep `0.2.7-dev` valid without tag.

### 3. Payload Adversarial Retest

Create temporary review handoff samples and run `scorecard_handoff.py` against them. Report actual output and judgment.

#### Case A: ordinary prose should pass

Review reason includes:

```text
We avoided base64, image attachments, and raw visual payloads in the callback.
```

Expected: pass.

#### Case B: `data:image/...;base64,` should fail

Review reason includes:

```text
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB
```

Expected: fail.

#### Case C: long base64-like blob should fail

Review reason includes a long base64-like string of at least ~160 chars.

Expected: fail.

#### Case D: short harmless token should pass

Review reason includes a short ordinary token such as:

```text
base64url encoding was not used.
```

Expected: pass.

### 4. E2E Protocol Quality Review

Evaluate `docs/CEO_FLOW_E2E_BEHAVIOR_SMOKE_PROTOCOL_2026-07-07.md`:

- Is the protocol specific enough to run?
- Does it define a disposable project setup?
- Does it define expected CEO behavior?
- Does it define implementation-lane evidence?
- Does it define review-lane evidence?
- Does it define CEO acceptance/revise/block criteria?
- Does it prevent confusing validator green with real behavior proof?
- Does it clearly say stable release still requires an actual full-pass behavior smoke report?

### 5. Release Readiness Check

Check:

- `plugin.json` is still `0.2.7-dev`;
- `check_release_state.py` still passes for dev version;
- README and release gate do not imply stable release is ready now;
- release criteria require actual E2E behavior smoke before tag/release.

### 6. Remaining Risks And Recommendations

Group recommendations by priority:

- **P0**: must fix immediately; remediation cannot be accepted otherwise.
- **P1**: should fix before stable release.
- **P2**: later improvement.

Please especially answer:

- Is `base64,` false-positive risk acceptably fixed?
- Is the E2E behavior smoke protocol adequate as a stable-release gate?
- Is it acceptable to keep `0.2.7-dev` until behavior smoke is actually run?
- What is the next concrete action before stable release?

### 7. Final Conclusion

Answer explicitly:

- Did commit `dd68333` correctly address the previous review's P1 items?
- Can the repo remain in dev state with confidence?
- Can it be tagged as stable now?
- If not, what exact evidence is still missing?
