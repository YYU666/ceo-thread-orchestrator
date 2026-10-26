# Artifact Lifecycle Change Receipt

Decision: accept for bounded rules and caller-side planning; no actual cleanup or
native packaging acceptance is claimed. Existing dirty work was preserved.

## Changes

Reuse the existing delivery loop, input/environment check identity, permissions,
and evidence records. Add optional `build` and `cleanup` planning operations to
`delivery_policy.py`; they perform no filesystem or process operations.

Build decisions require a trigger and declared target, verify caller-reviewed output
digest plus the existing command/input/environment identity, and distinguish artifact
reuse from missing validation checks. Ordinary phase work uses incremental affected
checks; content alone never implies engine rebuilding. Required native or milestone
outputs may need full packaging if exact applicable evidence cannot be reused.

Cleanup separates temporary/cache/superseded candidates from release, rollback,
unique evidence, user projects, generated assets, and unknown recovery data. A
temporary candidate needs an exact user-authorized path, source of authorization,
canonical/content identity, no active references, recovery/regeneration checks, and
an exceeded project temporary-retention limit. Size and age do not authorize cleanup.
The helper always returns `allowDeletion=false`; live checks and actual permissions
remain at the existing call site. No cleaner, scheduler, Host, or approval loop is added.

Focused reference rules require node-scoped disk checks and compact cleanup records.
Space pressure limits new nonessential large copies, not safe ordinary source work.
Formal version retention is project-owned; no global cache/data deletion is authorized.

## Exact Skill Write-Set And SHA-256

| File | SHA-256 |
| --- | --- |
| `SKILL.md` | `502ff9e9d284eabc0e3fdc993e7dfe04fe3719edfd0e55c2b761b4ad4a7335e4` |
| `references/artifact-lifecycle.md` | `8e4ad20e6a0dd14139c092a12de495f9e0cf5597b015f4cd39ce660bea908235` |
| `references/delivery-loop.md` | `4771b064cb67f642a961c4fa2d4e024385947e4743d4f324646fb9718bcdeaa2` |
| `references/quality-gate.md` | `a39dc1c5a30ddfb4b1e44bd58cefbbdc6a3390dc56ac7b10c483fc045ca1daf1` |
| `scripts/delivery_policy.py` | `b76ca9c7d76585e0edc778e2f755d9c479208b291dc21363f8c2fb18dc6dfa60` |
| `tests/test_artifact_lifecycle.py` | `243e37e5989737533a37d2bd272ff300dc532d5188d95fbbc663c25701e18577` |

The repository-only additional file is this change receipt. The quality reference
clarifies that a `build/full` verification profile concerns affected coverage,
not repeated full packaging, signing, and installation.

## Verification

- Pre-sync installed preimage rejected `build` and `cleanup` as `unknown_operation`.
  New focused behaviors pass 10/10 tests.
- `python3 -B -m unittest discover -s skills/ceo-thread-orchestrator/tests -q`:
  canonical 299/299 PASS.
- `python3 -B -m unittest discover -s <installed-skill>/tests -q`:
  installed 299/299 PASS.
- Repository suite: 22/22 PASS, also with installed snapshot compatibility enabled.
- `python3 -B scripts/smoke_eval.py`: static coverage 72/72 PASS.
- `quick_validate.py`, `py_compile`, `git diff --check`: PASS.
- Focused privacy/path scan of new helper/rules/tests: no matching private project
  names, local user paths, model/provider identifiers, or credential markers.
- Mechanical installation sync excluded Python caches. Existing manifest helper
  verified 75-file byte equivalence (excluding caches):
  `fcda6468a5263d21026da97930f4c7471d8c0da87b86ef6231e785cfa230834e`.

## Remaining Boundaries

No live build/package/sign/install, cache regeneration, process-reference lookup,
power-loss test, filesystem deletion, or measured space release was performed.
No product files, memory store, Provider, Goal, model settings, thread, commit, or
push were changed. Advisory flags are not authenticated receipts. The cleanup helper
accepts normalized absolute POSIX paths; native Windows path handling at a real
cleanup call site remains unrun and does not block unrelated source work.

Installing these rules proves file parity, not automatic loading by a running CEO.
At the next relevant build/copy/install/cleanup boundary, read the focused lifecycle
reference and apply it through the current delivery owner and existing permissions.
Actual cost/latency savings and disk reclamation require separate runtime evidence.
