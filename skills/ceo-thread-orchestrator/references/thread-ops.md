# Thread Operations Reference

Use this reference when CEO Flow needs visible Codex thread coordination, sidebar cleanup, workspace anchoring, thread relay, or thread lifecycle decisions.

## Tool Discovery

Search for thread tools when thread work is needed. Available surfaces may expose `list_threads`, `read_thread`, `send_message_to_thread`, `create_thread`, `fork_thread`, `handoff_thread`, `set_thread_title`, `set_thread_pinned`, and `set_thread_archived`.

Use thread tools this way:

- Discover: list/search by project, role, domain, known names, and workspace before creating anything new.
- Inspect: read recent status and turn summaries before reusing, steering, accepting, archiving, or replacing a thread.
- Continue: send a follow-up prompt to an existing thread when it is the right lane.
- Reuse: prefer matching specialist lanes when role, workspace, freshness, and write-set reduce risk.
- Create: create only when user/project authorization and tool contract allow it.
- Fork: fork only when completed conversation history is needed. Active unfinished turns are not copied.
- Handoff: move between Local and Worktree only when supported and useful.
- Lifecycle: rename, pin, archive, or retire based on evidence.

## Sidebar Hygiene

Before creating or forking any visible lane:

1. Search for a reusable lane by project, role, area, and workspace.
2. Decide role, write-set, stop condition, expected report, and reuse policy.
3. Assign a stable lane id and planned title.
4. Put planned title and lifecycle policy in the task card.
5. Create only the lanes needed for the current task graph.

Use short sortable titles when title tools exist:

```text
<ProjectShort> CEO - <goal or project>
<ProjectShort> Impl - <area>
<ProjectShort> Review - <area>
<ProjectShort> UX - <flow>
<ProjectShort> Knowledge - <memory/archive>
<ProjectShort> Research - <question>
```

After creating or reusing a lane:

- Rename vague or untitled lanes immediately when the tool allows it.
- Pin only active CEO, implementation, review, and harvest-critical lanes.
- Archive or unpin after acceptance, supersession, or retirement, after recording why.
- Record `threadId`, title, role, workspace, write-set, status, and next harvest action in the roster or operating note.
- Avoid multiple sibling implementation lanes for the same project/area unless write-sets are non-overlapping and merge/review cost is justified.
- Do not use subagents as substitutes for visible lanes when the user asked for multi-thread execution, persistent experts, or later harvest.

Sidebar cleanup:

- At each harvest, classify lanes as `active`, `idle`, `busy`, `blocked`, `stale`, `superseded`, or `retired`.
- Archive/retire stale or superseded lanes only after a compact handoff, memory pointer, or reason is recorded.
- Prefer one stable implementation lane per project/domain, one review lane for high-risk work, and one knowledge lane only when durable memory work is active.

## Workspace Root Guard

Project work must stay anchored to the user's real project folder. Wrong Codex project folders, scratch directories, generated worktrees, or sibling folders cause long-term drift.

At the start of a project or execution wave, define:

```text
Project short name:
Canonical project root:
Allowed worktrees or sibling roots:
Forbidden / stale roots:
Workspace evidence:
```

Before reusing, creating, forking, or messaging a visible lane:

1. Compare the lane `cwd` or workspace with the canonical project root.
2. If it is a worktree, verify it belongs to the same project and record the parent root.
3. If it is a sibling project folder, old generated Codex folder, temporary workspace, or unknown directory, do not dispatch implementation work there.
4. If a wrong-workspace thread contains useful history, use it only for read-only context extraction, then relay a compact handoff to a correct-workspace lane.
5. If the tool cannot create a correct-workspace thread, state that limitation and ask for the correct project/thread target.

Task cards must include `Workspace`, `Canonical project root`, `Allowed worktrees / sibling roots`, and `Workspace verification`. Workers must report `workspace_mismatch` and stop before file edits if the root does not match.

When a user says a project lives in one folder, treat that as stronger than inferred thread history or old Codex saved-project locations.

## Unsaved Source Repo Host Lane

Some Codex hosts can create threads only inside saved projects. If the user's canonical source repo is not a saved project, do not silently switch implementation to a scratch or generated folder.

Use this fallback only when the user wants lane execution and no correct saved project target is available:

1. Create or reuse a host lane in the closest approved CEO/shell project.
2. State that the host workspace is not the canonical source repo.
3. Put the canonical source repo in `Canonical project root`.
4. Set `Allowed write-set` to absolute paths under that canonical source repo only.
5. Add `Do not touch` for the host project files unless they are explicitly part of the task.
6. Require the worker to run a workspace check before edits and stop with `workspace_mismatch` if the absolute canonical root is unavailable or differs from the task card.
7. Use absolute paths in every edit, command, and report.
8. Set a harvest mechanism before final reporting: heartbeat, concrete next harvest time, or immediate synchronous harvest.

This is a bridge for tool limitations, not permission to let project roots drift. If the host lane cannot safely access the canonical repo, keep it read-only and ask the user to open or save the correct project.

## Relay Packet

When routing between threads, use a compact relay packet instead of raw logs:

```text
From CEO thread:
Source thread / evidence:
Target thread:
Context snapshot:
Decision or request:
Allowed write-set:
Dependencies:
Required verification:
Report back with:
Stop condition:
```

Relay sequence:

1. Read the source thread's newest report, diff summary, or blocker.
2. Distill only relevant context, files, constraints, and evidence.
3. Read the target thread before sending, so the prompt fits its state.
4. Send a bounded relay packet or task card.
5. Record message, target thread id, expected report, and next harvest action.
6. Later read the target report and make an explicit CEO decision.

Do not use thread messaging as a hidden autonomous chat room. CEO remains accountable for context crossing thread boundaries.

## Capability Boundaries

- A new thread is a separate conversation, not a guaranteed autonomous employee.
- Existing thread steering requires explicit read/send operations.
- Subagents are short-lived scouts unless the user/tool contract says otherwise.
- Background work continues only with a live worker, heartbeat, lease, automation, or equivalent evidence.
- Dispatch is not complete until the CEO records how results will be harvested.
- Worker reports are evidence, not proof.
- Multiple agents sharing one directory can overwrite each other. Use one writer per write-set or approved worktrees.
- Memory is not automatic unless a maintained memory provider or writeback routine exists.
