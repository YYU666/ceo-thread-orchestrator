# Build, Artifact, And Cache Lifecycle

Use at an affected validation, large-copy/build/install boundary, milestone, or
cleanup checkpoint. Reuse `delivery-loop.md` and the current task/evidence records;
do not scan every disk or rebuild dependency caches each turn.

## Build Only For A Declared Need

Before a build, package, signature, or install, state its trigger in the current
task: changed affected inputs, missing/invalid artifact, unresolved evidence,
affected native behavior, or milestone delivery. Choose the smallest check that
covers that need. Incremental validation is the ordinary phase path. Full packaging,
signing, and installation serve affected native checks or milestone delivery when
the required evidence cannot be reused; they are not defaults for every micro-slice.
Run only the relevant stage, with existing permissions; a packaging need is not
signing, spending, upload, or installation authorization.

Content/map edits normally use the existing runtime and production tools. They do
not by themselves require rebuilding an engine. Rebuild the affected resource/bundle
or native component when actual dependency coverage shows the change affects it.
Missing coverage stays unverified; do not call an old executable a test of new content.

Artifact reuse binds the actual output digest plus the exact command/options, relevant
source/config/test/lock/dependency content identities, platform, toolchain, and build
environment. Use existing `reuse` checks; HEAD, filenames, sizes, and timestamps alone
are insufficient. Independently inspect output identity and evidence. Reuse of a build
does not reuse every test: run uncovered checks on the current candidate. Changes in
inputs/environment, absent output, digest mismatch, failed/flaky checks, incomplete
dependency coverage, or new concerns invalidate the affected reuse. A valid native
check or deliverable may be reused at a milestone if it already covers that exact need.

`delivery_policy.py`'s optional `build` operation consumes `triggerReason`,
`validationTarget=affected_check|affected_native_check|milestone_delivery`,
`changeKind=content|source|config|dependencies|toolchain|unknown`, and `requiredChecks`.
An optional `artifact` supplies the existing `reuse` request as `checkIdentity`,
`expectedSha256`, `observedSha256`, `exists`, `independentlyVerified`, and `coveredChecks`.
It recommends incremental validation, reuse plus missing checks, full packaging for
the declared target, or exact artifact reuse. It does not execute or authenticate a
build, stage, native check, or completion claim.

## Classify Before Retention Or Cleanup

| Class | Handling |
| --- | --- |
| Rebuildable cache / temporary scratch | Bounded project-defined count/space retention; confirm reproducible regeneration and absence of recovery data |
| Failed or superseded copy | Temporary only if no active dependency and no unique evidence, unreleased package, rollback, or user data remains |
| Formal release / rollback / unique evidence | Preserve under the project's explicit retention policy; no generic TTL or automatic deletion |
| User project / generated assets / unknown recovery data | Preserve; use existing specific authorization where deletion is necessary |

At build/copy/install starts and milestones, check free space on the affected volume
and the known task artifact roots. Under pressure, stop adding nonessential large
copies and reuse existing outputs. Safe ordinary source work can continue. Do not
mark the Program Goal blocked merely for a cache/copy limit or skipped optional build.
Record required large-output limits as local unmet evidence, not passed validation.

Before cleanup, enumerate exact canonical paths and content identity, confirm symlink
containment, current processes/writers and worktree/task references, and check needed
recovery plus successful regeneration/replacement where applicable. Keep the only
unpublished package or evidence until its required replacement/recovery is verified.
Never infer deletability from age or size, use wildcard/global-cache cleanup, broad
`rm`/`git clean`, or treat dirty/untracked work as disposable.

Automatic cleanup applies only to user-authorized exact temporary-path allowlists
with an authorization reference and the checks above. This policy is not permission
to delete any global cache or project data. Other categories retain their existing
authorization boundary; batch genuinely necessary questions under the normal policy,
without adding a new approval cycle to ordinary builds.

The optional `cleanup` operation classifies one exact absolute POSIX path from
caller-reviewed data. Inputs: `category`, `userAuthorizedTemporaryPaths`,
`authorizationSource`, `activeReferencesChecked`, `activeReferenceCount`,
`canonicalPathVerified`, `contentIdentityVerified`, `recoveryChecked`,
`rebuildVerified`, and `temporaryRetentionExceeded`. Categories are
`rebuildable_cache`, `scratch`, `superseded_copy`, `release`, `rollback`,
`unique_evidence`, `user_project`, `generated_asset`, and `unknown_recovery`.
It returns only a candidate and always `allowDeletion=false`. Actual cleanup uses
the existing authorized call site, rechecks the live facts immediately, and stops
if ownership/content/references changed. No deletion executor is added. On other
platforms record equivalent native-path checks locally; an unsupported planner path
does not block source work.

After a real authorized cleanup, record one compact row in the current artifact
record: exact path, reason, outcome, measured bytes released (or unknown). Do not
claim freed space from a plan, directory size, or proposed deletion. Keep formal
version retention in project policy and temporary retention finite; no new dashboard,
scheduled cleaner, Host requirement, or approval hierarchy is needed.
