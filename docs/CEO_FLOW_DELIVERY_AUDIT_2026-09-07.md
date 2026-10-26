# Delivery Policy Audit - 2026-09-07

Scope: generic CEO Flow skill and installed copy. No product code, real Runtime,
Provider calls, task wakeups, model/permission changes, commit, or push.
Baseline: `a8fd4c8863b487fcc0a05a8dd091fbc90e29ef55`.

## Findings And Corrections

| Feedback | Source finding | Correction |
| --- | --- | --- |
| Small work becomes ceremony | Entry and playbook default to delegation/review for user-facing work | Explicit reversible two-file quick path; no synthetic task/card/callback |
| Serial microtask handoffs | Staffing and wave rules encourage dispatching every ready node | One end-to-end owner; diagnosis, tests, packaging and checklist work stay together |
| End-to-end validation late | Quality guidance emphasizes function/module slices | Define first runnable checkpoint and final observable scenario before expansion |
| Unbounded waits | No concrete deadline/partial-handoff policy | Configurable 10/30/60-minute planning defaults; preserve handles, one timeout action, no duplicate writer |
| Repeated testing | Available checks and reviewer counts become repeated commands | Reuse independently inspected exact input/environment/command evidence; invalidate on changes, unknown coverage, flakiness or concern |
| Visual evidence becomes text only | Current-task vision permission conflicts with durable-CEO prohibition | Bounded current-owner screenshots; same-target before/after motion evidence; AX/key dispatch alone is insufficient |
| UI navigation drift | No explicit app/window/document action boundary | Bind target and allowed actions; stop on mismatch, unknown action or observed deviation |
| Reporting substitutes for progress | Process count can reject otherwise verified code | Count is advisory; retain callback chain and evidence gates; measure verified outcomes |
| Conflicting completion records | Dashboard does not explicitly supersede prior status | One current row per outcome/candidate; historical evidence separate |

Independent review also found and prompted corrections to tiny-high-risk review
wording, ordinary-dispatch versus takeover routing, and duplicate JSON keys.
Native unknown-route documentation now agrees with the existing scoped callback
acceptance path. Package/config review is triggered by actual high-risk impact.

## Implementation Boundary

- `SKILL.md` routes execution shape to `references/delivery-loop.md`.
- Existing playbook, autopilot, parallel waves, quality, visual, state, thread,
  context-memory and repo-baseline references now share the same execution policy.
- `callback_gateway.py` emits an advisory warning for process-update excess;
  verification, model requirements, identity and callback-chain gates remain.
- `delivery_policy.py` provides bounded caller-side plan/wait/reuse/UI/outcome
  decisions, with strict primitive validation and duplicate-key rejection.
  It is not an executor, scheduler, authenticated receipt or sandbox. It cannot
  declare product completion. Actual artifact inspection and task control remain
  the caller's responsibility. Timeout-once state lives in the existing lane record.
- No memory authority, context-pressure, durable-state or Host lifecycle safeguards
  were relaxed. No changes were made to model defaults or external Harness routing.

## Verification

- Canonical: `python -m unittest discover -s tests`, from skill root: **242/242**.
- Installed: same command from installed skill root: **242/242**.
- Repository: `python -m unittest discover -s tests`: **16/16**.
- `scripts/smoke_eval.py`: **72/72** static documentation coverage, not LLM E2E.
- `skill-creator/scripts/quick_validate.py`: canonical and installed **PASS**.
- `python -m compileall -q .../scripts`: canonical and installed **PASS**.
- `git diff --check`: **PASS**.
- `scripts/check_release_state.py`: **PASS**, development version `0.2.7-dev`.
- Focused reference-link scan: no missing linked script/reference paths.
- Changed-file privacy pattern scan: no local home paths or matching credential
  patterns; not a claim of comprehensive security verification.
- Old-red/new-green: run
  `test_required_progress_updates_warn_without_rejecting_verified_work` against
  the baseline gateway loaded with `git show HEAD:.../callback_gateway.py`:
  **FAIL**, `processUpdateCount_budget_exceeded`. Current suite: **PASS**.
- New tests cover two-tooltip quick path, one-file permissions review, explicit
  budget/review policy, timeout and reentry, missing live handles, evidence reuse
  and invalidation, target/action drift, unobserved play/save-reopen, stale candidate,
  path escape, malformed/oversized/deep JSON and duplicate risk fields.

Validation used an isolated Python environment with the repository's PyYAML
dependency; no system package changes were needed.

## Installed Candidate

The installed preimage matched the baseline commit before sync. Mechanical sync
excluded Python caches and did not delete files. Source manifest comparison:

```text
fileCount: 59
canonical/installed equivalent: true
manifestSha256: 0e93433d47f1b9fed2812074f1aa2512f92e2bc03a29a75242a5a5e43b56555f
```

## Independent Review And Residual Risk

Initial independent scenario/source review: revise; corrections applied.
Focused correction recheck: **accept**, all 14 helper tests and 18 additional
focused assertions passed; no remaining blocking finding within the recheck.
This is a bounded review of the reported issues, not a fresh security certification.

Real product delivery latency/token improvement, native UI action enforcement,
and automatic backup/archive have not been end-to-end tested here. These require
an authorized live project run. Existing tasks must read the updated entry and
relevant reference on a new turn; installation does not replace their old context
or prove that a running task adopted the policy. Changes are local and uncommitted.
