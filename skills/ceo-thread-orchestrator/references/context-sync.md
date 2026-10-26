# Safe-Boundary Context Sync

Use current Zhixia `sync_context` for ordinary compact continuity. It is not
`prepare_takeover`, `refresh_binding`, or write authorization.

## Trigger And Transport

At startup, before an actual new dispatch, and after formally accepted refresh and
reverification, invoke `scripts/sync_context_driver.py EVENT --state SYNC_LEDGER`.
This calls the installed `codex-control-mcp.cjs` exported `callTool` adapter with
`sync_context`, not a nonexistent low-level Runtime operation. It neither messages
a knowledge task nor calls Providers. Read-only sync verifies first and stays
headless with `showApp=false`.

Example caller-owned event, never taken from an untrusted worker callback:

```json
{
  "boundary": "before_dispatch",
  "eventId": "dispatch-17",
  "workspace": "/absolute/canonical/project",
  "projectId": "verified-project-id",
  "taskId": "current-ceo-task",
  "taskGoal": "implement the current bounded task",
  "tokenBudget": 1200
}
```

Allowed boundaries: `startup`, `before_dispatch`, `after_accepted_refresh`.
Get canonical workspace/project identity from registered configuration and app-owned
verify, not neutral cwd or caller aliases. Unknown identity needs verify first.
One root per event; cross-project tasks bootstrap lazily with separate task/project
ledgers. Reuse event ID on retry; changed content is rejected. Never generate fresh
IDs on every model response or unchanged poll. Default budget is 1200; necessary
anchors can justify an explicit increase up to 10000, never maximum by default.
Only bounded Hot/Warm items and scoped safe source paths are admitted (48 KB cap).
Unsupported source URI formats fail closed instead of importing cross-project text.

## Consumption

- `ready_new`: validate exact workspace/project, app-owned authority, current and
  recovery readiness, matched scan/checkpoint, generation/query, token budget,
  nonempty items/source refs and forbidden content. Persist before emitting.
- `unchanged`: no items, refs or token payload; pair must already be emitted by
  this task/project. Emit nothing. Repeated ready_new pairs also skip.
- `stale`, invalid or unavailable: emit no packet. Preserve lane-local current-memory
  gates, never unfreeze tasks or claim global blockage. Other safe lanes continue
  under their existing policy.

Key: canonical workspace + verified project ID + task ID. Track **generation/query
pairs**, not generation alone. A changed goal in the same generation can return a
new selection. Send the last emitted `knownContextGenerationId` and
`knownContextQueryKey` on the next call. This is separate from takeover's generation
idempotency; sync cannot clear a freeze or authorize execution.

Confirmed atomic state and locking serialize callers. Duplicate boundary events
never call the adapter again, including failed events. Durability errors suppress
packet output. This is **at-most-once emission**, not proof of Host injection: a
crash between durable reservation and delivery can lose a packet. Do not replay
automatically or fabricate consumption; reconcile against actual Host evidence or
use the existing clean takeover path. Ledgers cap at 256 events/pairs per task and
never silently evict deduplication entries.

## Boundaries

An acceptance note or staged slice does not authorize refresh. Complete the
existing exact-scan formal receipt -> refresh_binding -> verify chain before the
after-refresh boundary. Recovery still requires prepare_takeover, six authority
gates, exact frozen-task binding, Host telemetry/ACK and fresh takeover generation.

Skill text cannot intercept Host requests, push into running tasks or trim history.
The driver executes only when invoked. Host integration must call it at the three
boundaries, deliver compact output and record actual delivery evidence before
claiming automatic injection. It deliberately returns `hostTriggerVerified=false`;
fixture tests are not live Host E2E evidence. No real memory refresh is performed by
this read-only driver. Existing permissions and proven freezes always remain.
