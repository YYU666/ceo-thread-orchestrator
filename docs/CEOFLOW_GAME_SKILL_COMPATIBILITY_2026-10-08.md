# Game Production Skill Compatibility Receipt

Decision: accept for the existing CEO Flow interface, using synthetic fixtures.
No production Skill, loader, routing, permission, or lifecycle change is needed.
This receipt does not accept a game-production candidate or claim a product trial.

## Verified Basis

- Branch: `codex/audit-remediation-20260813`.
- HEAD: `a8fd4c8863b487fcc0a05a8dd091fbc90e29ef55`; pre-existing dirty work is preserved.
- Canonical and installed Skill: 73 non-cache files, byte-equivalent.
- Both manifest SHA-256: `9dbffe890f2dcb4b2d9d3f8e3004e7863d8eb5ea3fb11ca0ac7dd146bbe6ca8e`.
- Loader SHA-256: `15c9f50af57b72aa23c677b939485ec260c1f6137acf3d996b6416933df4473a`.
- Installed `SKILL.md` and `references/project-domain.md` were read in this run.

## Producer Integration Contract

1. Keep generic rules in one small, topic-addressable Markdown file with exact
   `##` headings. Keep the current game's decisions in a separate project file.
   Use `game_production` for existing engine/tools/recipes/assets and
   `engine_development` for a separately bounded source/tool/test task.
2. After the candidate revision is accepted, import reviewed ordinary files into a
   project-owned location such as `docs/domain/game-production-rules.md`. Record
   the source Skill name, version/revision, source content manifest, file mapping,
   and SHA-256 in a project-local import manifest. Verify source and imported bytes
   against that accepted manifest. Never use absolute external paths, `..`, or
   symlinks to the global Skill in the domain index. This run used temporary
   synthetic source/snapshot files only; it imported nothing into a live project.
3. Add the existing `ceo_project_domain_v1` index at `.ceo-flow/domain.json`; keep
   the project's `AGENTS.md` entry short. Map `kind=rules` to the imported rules,
   `kind=spec` to current project decisions. Select only relevant `workKinds` and
   `topics`; a route-and-play/save slice usually selects `layout qa`.
4. Run `load_project_domain.py` with the canonical project root and actual task id,
   using its own domain state file. Existing limits remain eight selected sections
   and 12 KiB serialized prepared context. Keep optional rule entries
   `required=false`; only task-critical spec entries may be required. No config
   or missing optional files leaves ordinary development available.
5. Put the returned `taskCard` refs in the existing task card. Append a small
   caller-owned `domainSnapshot` provenance attachment containing the accepted
   source version and import-manifest reference/hash. Do not add version, model,
   permission, or delivery fields to the strict domain-index schema. The existing
   loader returns file/section hashes; it does not resolve or approve versions.
6. Before using a snapshot, compare each rule `fileSha256` to its import manifest.
   A mismatch needs explicit snapshot review/update or omission of that optional
   rule; never label changed bytes as the previously accepted version. The helper
   does not perform this version-manifest check automatically.
7. Parent preparation is not child reading. A child may prepare relevant sections
   under its own task id or receive those sections once. Record actual reading or
   delivery separately. `references_only` carries updated pointers without text;
   it is not a Host ACK, candidate acceptance, or unchanged-file claim.

Minimal index entry (paths and section names follow the accepted candidate):

```json
{
  "id": "production-layout",
  "kind": "rules",
  "path": "docs/domain/game-production-rules.md",
  "section": "Layout",
  "workKinds": ["game_production"],
  "topics": ["layout"],
  "required": false
}
```

The entry lives in the existing index object with `schema`, `domain`, and `entries`.
Example task-card provenance attachment, outside that index:

```text
domainSnapshot:
  sourceSkill: accepted production Skill name
  sourceVersion: accepted version or revision
  sourceManifestSha256: accepted source content digest
  importManifestRef: project-relative manifest path plus SHA-256
ruleRefs/specRefs: loader's selected path, section, fileSha256, excerptSha256
```

The production Skill can also provide its own short, focused entry for independent
use. Standalone use needs neither this loader nor a second CEO, Goal, or Host. When
used under CEO Flow, existing staffing, review, authorization, and recovery govern;
domain prose cannot grant permissions, spending, model changes, or freeze recovery.

## Current Candidate And Model Boundary

The named candidate's compact task summary reports a route mismatch and read-only
stop. Its `work/` and `outputs/` directories were empty when inspected. No candidate
rules, acceptance record, installation, or actual game trial was available to test.

The delegated report attributes the mismatch to requested model/reasoning overrides
versus actual app execution. The domain loader neither creates tasks nor chooses
models, so no loader change can repair that mismatch. This run did not independently
verify model telemetry, reproduce app creation, read raw sessions, or bypass Host
controls. The exact application cause remains for the Host/routing owner to verify.

## Commands And Results

- `CEOFLOW_INSTALLED_SKILL=<installed-skill> python -B -m unittest discover -s tests -v`:
  22/22 PASS, including six snapshot compatibility cases on both CLI copies.
- `python -B -m unittest discover -s skills/ceo-thread-orchestrator/tests -q`:
  canonical 289/289 PASS.
- `python -B -m unittest discover -s <installed-skill>/tests -q`:
  installed 289/289 PASS.
- `quick_validate.py skills/ceo-thread-orchestrator`: PASS.
- `git diff --check`: PASS.
- Existing `source_manifest.build_result(..., compare=..., verify_self=True)`:
  73-file equivalence PASS; Skill manifests unchanged from the previous candidate.

The fixture tests cover local snapshot identity, relevant topics, separate specs,
version-provenance attachment, parent/child deduplication, missing optional inputs,
engine separation, external-path rejection, and changed-snapshot hash detection.
Default repository tests use canonical only; installed-copy testing is explicitly
enabled by the environment variable, so a fresh clone requires no user installation.

Write-set: this receipt, its compact JSON evidence, and
`tests/test_domain_snapshot_compatibility.py`. No production installation sync was
necessary. No commit/push, live project edits, Goal, Provider, or model operation was
performed. Remaining work is candidate creation/acceptance under the requested route,
then separately authorized project snapshot configuration and actual delivery proof.
