# Behavioral Forward Testing

Static smoke evaluation confirms that policy terms exist in the Skill corpus.
It does not call Codex or prove that a CEO will follow those policies. Never use
`smoke-eval 70/70` (or any later count) as behavioral acceptance evidence.

## Required Forward Loop

Before claiming a new lifecycle rule is operational, run a bounded forward test
in a disposable fixture or explicitly approved real project:

```text
fresh Codex task
-> operating-mode decision
-> ProjectIdentityEnvelope + stack doctor
-> Zhixia retrieve receipt (or exact skipped reason)
-> compact task-card profile selection
-> Codex-internal lane or admitted CMMD run
-> independent evidence review
-> CEO accept/revise/block
-> Zhixia writeback receipt (or exact skipped reason)
-> second fresh task retrieves the accepted evidence
```

## Evidence Checklist

- New task/thread ID and timestamp.
- Exact project identity and baseline.
- Doctor result path/hash.
- Retrieval hook receipt bound to project/task/time window.
- Selected `minimal | standard | R1` profile and resulting prompt bytes/tokens.
- Lane/run IDs and execution-surface decision.
- Changed files, commands, tests, artifacts, and receipt hashes.
- CEO decision and independent-review evidence.
- Actual writeback receipt.
- A later retrieval that returns the accepted item by sourceRef.
- Token/cost/latency when an external provider is used.

Missing provider capability may produce `block` or a scoped skipped reason. It
must not be converted into a passing behavioral claim. CMMD R1 forward testing
remains blocked until its stable accepted schema and real writer readiness are
available.

## Visual Transport Forward Test

Static wording is not proof that a future worker will avoid image tools. Before
claiming the zero-payload visual gate is behaviorally reliable, run an explicit
fresh-task test with local fixture images and no sensitive content:

```text
fresh non-forked visual task
-> transportMode=zero-payload-local-analysis
-> task card forbids view_image/image(...)/input_image/image tool blocks
-> local hash/dimensions/OCR/diff only
-> compact textual evidence card
-> session/request telemetry shows modelVisibleImagesUsed=0 and
   modelVisibleImageBytes=0
-> CEO inspect/accept|revise
```

Then run the separately authorized bounded exception with one compressed
fixture below the declared byte limit. It must show one fresh short-lived
worker, one model-visible image, no forked image history, no image relay to CEO,
and immediate worker closure. Any `view_image` call in zero-payload mode,
unknown image-byte count, multi-image tool output, image relay, or session
growth outside the declared budget is `revise` and prevents a behavioral claim.
