# Game Production Rules

These are production standards. Gameplay, style, content, and completion criteria
belong in the project specification. Existing CEO Flow coordination and permissions
remain in charge.

## Core loop

Validate the smallest playable core loop before expanding content. Name what the
player does, what feedback demonstrates it works, and the next runnable slice.
Use existing engine tools and recipes; represent a discovered tool gap as a bounded
engine-development task with a reproducible need and focused acceptance evidence.

## Region layout

Deliver a complete area, route, and player experience rather than an asset count.
Start with layout, scale, connectivity, collisions, accessibility, and traversable
routes. Play the route before decoration and polish. Preserve locked areas and
accepted regions; check neighboring connections when changing a boundary.

## Assets and audio

Reuse suitable existing assets first. Generate new assets only for a named gap in
the specification, after checking style, dimensions, integration, and existing
authorization. Track source/license and the in-game role. Match art and audio to
the playable scenario rather than delivering disconnected files. Preserve manual
edits; make replacement/adoption reversible where the engine supports it.

## Integration and delivery

Use explicit inputs, outputs, dependencies, and acceptance criteria between design,
level work, gameplay code, art/audio, and QA. Each production slice delivers a real
runnable result or an actionable partial result tied to the next runnable step.
Design documents, asset totals, and unit-test counts alone do not prove game progress.
Keep the actual editor/runtime synchronized with structured tool operations so the
user can inspect, give feedback, play, and take over. Never simulate progress with
fake mouse/cursor animations. Reuse existing approvals for authorized low-risk work;
direction changes, spending, deletion, and excess scope follow CEO Flow authorization.

## Verification and preservation

Inspect the actual player/editor outcome with risk-proportionate visual evidence.
For changed persistence or manual editing, verify modification, save, and reopen;
for changed gameplay/route, play the affected path; for changed packaging/export,
verify the produced export. Reuse evidence only on matching inputs and environment.
Do not overwrite user edits, locked regions, or accepted results to make a test pass.
