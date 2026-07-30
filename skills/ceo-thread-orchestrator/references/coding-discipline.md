# Evidence-Driven Coding Discipline Gate
Use this gate for non-trivial coding writers and their reviewers. It is a
lightweight dispatch/review contract, not an always-loaded coding prompt and
not a substitute for project architecture, tests, or Host enforcement.

## Provenance And Claim Boundary

The profile is inspired by Andrej Karpathy's public observations about coding
agents and the experiment-loop design in `karpathy/autoresearch`. CEO Flow's
integration is independent and is not an official Karpathy skill.

Current CMMD candidate identity:

```text
Display: Evidence-Driven Coding Discipline / 证据驱动编程纪律
Profile: evidence-driven-coding-discipline-v1
Classification: evidence_driven_discipline_candidate
Default enabled: false
Capsule SHA-256: acca06bed7575442e3fd2779fdba9ecc237ee36440dde5d0e4a32e5e663a95b0
```

CMMD remains authoritative for the live profile and its exact capsule hash.
The recorded candidate does not authorize an R1 writer, change a model or
reasoning setting, or prove quality, cost, or token savings.

## Trigger

Trigger for non-trivial feature, bug-fix, refactor, test implementation,
architecture change, or multi-file coding writer/reviewer work. Do not trigger
for casual chat, status/wait turns, R0 narrow read-only work, ordinary memory
retrieval, visual-only review, or tiny edits unless the user explicitly asks.

The CEO uses only the compact gate fields. A writer may receive the exact
versioned discipline capsule only when the selected execution surface supports
it. A reviewer receives a scope/simplicity/evidence checklist, not the worker's
reasoning or an expected verdict.

## Priority And Unattended Behavior

Use this priority order:

```text
latest explicit user goal
> canonical architecture and security invariants
> accepted project conventions and tests
> discipline heuristics
> fewer lines
```

Simplicity does not mean minimum LOC. Do not remove necessary safety,
recovery, protocol, accessibility, or compatibility behavior to make a diff
smaller. In unattended work, record and use a reversible default for a
non-critical ambiguity; ask the user only for direction-changing,
security-sensitive, costly, or irreversible ambiguity.

## Compact Task-Card Gate

Include only when triggered:

```text
Coding Discipline Gate:
  profile: evidence-driven-coding-discipline-v1 | project-approved alternative
  state: candidate-default-off | project-enabled | skipped
  reason:
  task-critical assumptions:
  simplest viable approach:
  allowed write-set / forbidden adjacent refactor:
  success criteria:
  required verification:
  scope-deviation policy: fail-closed | report-and-stop
```

Do not paste the full skill, community prompt, raw reasoning, or empty fields.
For CMMD, reference the exact live task/profile contract and hash rather than
reconstructing the capsule in CEO prose.

## Host And Review Evidence

Prompt instructions are soft guidance. Acceptance still requires Host- or
Codex-observed evidence for the task risk:

- task/project/baseline identity;
- allowed write-set and forbidden-file compliance;
- actual changed files;
- required command exit codes and test evidence;
- before/after workspace evidence when required;
- disclosed scope deviations;
- independent `accept | revise | block | supersede` authority.

The worker or external model cannot self-accept. Unknown profile identity,
profile-hash mismatch, out-of-scope edits, fabricated command results, or
discipline fields that attempt to change CEO role/model/reasoning/routing fail
closed for that execution route.

Reviewer questions:

- Were task-critical assumptions surfaced without inventing requirements?
- Is this the smallest implementation that preserves accepted invariants?
- Does every changed file trace to the task and declared write-set?
- Did the change introduce speculative abstraction or adjacent refactoring?
- Were the success criteria verified with real evidence?
- Should the result be kept, revised, discarded, or superseded?

## Evidence Before Default Enablement

The candidate remains default-off until a paired, reproducible benchmark uses
the same model, context, budget, baseline, tasks, and blind reviewer for
baseline versus profile. Keep Codex quota, Provider tokens, Codex review
tokens, money, latency, retries, defects, and human intervention separate.
Source/fake harness success is not empirical coding-quality evidence.

References:

- <https://x.com/karpathy/status/2015883857489522876>
- <https://github.com/karpathy/autoresearch>
- <https://github.com/karpathy/autoresearch/blob/master/program.md>
