# CMMD Contract Snapshot

These schemas are a compatibility snapshot from Codex Multi-Model Desktop
`master@98546e3`. CMMD remains the contract authority. CEO Flow vendors the
snapshot so a task or receipt can be checked before the external runtime is
trusted or even installed.

| Schema | SHA-256 |
| --- | --- |
| `ceoflow.external_execution_task.v2.schema.json` | `db5734568af3859e507486e3fabb2ddba9d77b84c13d8ab85a6c6b963811feda` |
| `ceoflow.external_execution_receipt.v2.schema.json` | `688691fa93d89fce12191b1d9a00d81883e1dbca596ed9330738b95cc96c5ab2` |
| `ceoflow.authorization_lease.v1.schema.json` | `8472ea35fda0ba8166c7f2fe9471d7fd029c7450d835c24cba0264f5fc9b1b89` |
| `cmmd.context_view.v1.schema.json` | `3d3e93e568677c12f5ab5c55e7e4a8223690b72b62eb1a285bdc9e9ce046b1f3` |

At dispatch, prefer the live CMMD schemas when their provenance and version are
available. A hash mismatch is a compatibility-review event, not permission to
silently accept a changed contract. Frozen v1 task/receipt formats are legacy
only and must not be used for new live runs.

`ceoflow.cmmd_readiness_evidence.v1.schema.json` is a CEO Flow-owned companion
schema, not a CMMD snapshot. It binds a readiness claim to project identity,
Provider/model, the four snapshot hashes, an expiry window, admitted risk tiers,
and source-backed evidence.
