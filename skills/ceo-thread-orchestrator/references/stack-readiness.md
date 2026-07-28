# Stack Readiness And Project Identity

Use this reference before claiming that CEO Flow, a memory provider, or CMMD is
ready for a project. A successful static validator is policy coverage, not
runtime readiness.

## ProjectIdentityEnvelope

Every project/worktree operation carries one stable identity envelope:

```text
ProjectIdentityEnvelope:
  projectId:
  canonicalRepoId:
  canonicalRoot:
  worktreeRoot:
  baselineHead:
  projectIdentitySha256:
```

- `projectId + canonicalRoot` select durable project memory.
- `worktreeRoot` identifies this run's workspace; it must not create a new
  long-term-memory identity.
- `canonicalRepoId` is derived from stable canonical-repository identity, not a
  temporary worktree path.
- `baselineHead` binds the run to a reproducible source state.
- `projectIdentitySha256` binds the normalized envelope. A mismatch fails
  closed; never relax exact project matching into cross-project search.

## Stack Doctor

Run the bundled read-only doctor at bootstrap, takeover, provider change,
installation validation, or when memory/execution results appear stale:

```powershell
python scripts/stack_doctor.py --project-root <workspace> --canonical-root <canonical-repo> --json
```

The doctor reports:

- source and installed CEO Flow hashes/version;
- Zhixia Skill/helper hashes and sidecar status;
- reported versus effective memory mode;
- stale source refs and duplicate memory IDs;
- CMMD control availability and vendored schema hashes;
- project/worktree identity;
- readiness plus exact skipped reasons.

It is read-only. It does not launch Electron, create a sidecar, start CMMD,
write memory, or prove model behavior.

## Fail-Closed Interpretation

- Missing/unavailable Memory Core or Memory Fact sidecar changes the effective
  mode to `fallback_stale`, even if an older helper reports `layered`.
- `fallback_stale` blocks claims that the packet is current or that recovery is
  ready. The CEO may use it as advisory history only, then verify canonical
  docs, Git state, tests, and fresh receipts.
- Duplicate item IDs are provider diagnostics. Deduplicate for prompt delivery,
  preserve merged `sourceRefs`/reasons, and record the anomaly.
- A packet labelled `fresh` whose source mtime exceeds the freshness budget is
  challenged as stale until canonical evidence confirms it.
- Missing CMMD control or readiness evidence does not block Codex-internal
  execution. It blocks only that CMMD route.
- CMMD R1 remains blocked until a stable accepted R1 contract and real bounded
  writer evidence exist. Intermediate schemas are not vendored automatically.

## Compatibility Receipt

Save the compact JSON doctor result as evidence when it affects routing. Do not
paste a full environment dump into the CEO task. Record only the result path,
hash, readiness fields, diagnostics, and skipped reasons.
