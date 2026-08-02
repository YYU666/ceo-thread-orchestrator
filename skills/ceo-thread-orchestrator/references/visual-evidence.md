# Visual Evidence Local-Artifact Policy

Use this reference for UI, game, design restoration, screenshot comparison, generated-image review, visual QA, and any task that might move image payloads through CEO Flow.

Core principle: visual quality still requires visual inspection. Do not disable screenshots, local image review, or visual comparison. What CEO Flow forbids is turning visual evidence into uncontrolled model-visible payloads, long-lived chat payloads, base64, `data:image`, `input_image`, full screenshot JSON, full OCR, full visual API request/response bodies, large per-image descriptions, memory blobs, FlowSkill candidates, worker callbacks, or third-party/CPA request logs.

`view_image` is not a zero-payload local viewer. It reads a local file, but its result is serialized as model-visible image content and may be persisted as `input_image`, `data:image`, or base64 inside a Codex request and raw session. The same applies to forwarding a screenshot or image result through `image(...)`. Never describe either operation as local-only.

## Standard Policy

```text
Visual evidence policy: local-artifacts-only
Visual transport mode: zero-payload-local-analysis | bounded-model-vision
Reference input: local paths/folders only
Screenshot output: artifacts/visual-checks/<task-id>/
Manifest required: artifacts/visual-checks/<task-id>/visual-evidence-manifest.json
Thread return format: evidence card only
Model-visible image budget: 0 by default
Forbidden in zero-payload mode: view_image, image(...), input_image, screenshot/image tool blocks returned to the model
Artifact return policy: paths+hash+dimensions+bytes+summary+decision only
Forbidden payloads: image attachments, base64, data:image, input_image, full OCR, full screenshot JSON, full request/response bodies, large per-image descriptions
CPA/API request body cap: 8-10 MB unless explicitly approved
Memory writeback: path/hash/dimensions/summary/decision only
```

Store reference images, screenshots, comparison images, failed-state images, generated image candidates, contact sheets, and visual diffs in a project `artifacts/` location or equivalent local artifact folder. CEO/worker callbacks should report only path, dimensions, bytes, hash, timestamp, short visual summary, decision, and next edits.

Legacy shorthand `paths+hash+summary` remains valid, but the preferred evidence card should also include dimensions, bytes, manifest path, and decision when available.

## Tool-Transport Reality Gate

Before any visual task, choose and record exactly one transport mode.

### Zero-Payload Local Analysis (default)

Use this mode when the user says not to send images, when many images are involved, when the CEO/project-main or a reusable worker would otherwise receive pixels, or when request/session size is a concern.

- Save screenshots and references to local artifacts without returning image blocks to the model.
- Use local commands or libraries for dimensions, file bytes, hashes, OCR, text extraction, pixel metrics, perceptual hashes, contact-sheet generation, and deterministic diffs.
- Store full OCR or machine-readable visual output only in a cold artifact sidecar; pass a bounded summary to the model.
- Do not call `view_image`.
- Do not call a screenshot/image tool in a way that returns pixels, base64, a data URL, or an image content block to the model.
- Do not use `image(result.image_url)`, loop over originals, or ask a child lane to reopen the same images.
- A path in the prompt is not proof of zero payload if the worker later calls `view_image` on it.
- If qualitative visual judgment cannot be supported by local metrics/OCR and bounded text evidence, return `insufficient_visual_evidence` or request the bounded mode below. Do not silently escalate.

### Bounded Model Vision (exception)

Use only when qualitative visual judgment genuinely requires model-visible pixels and the user or accepted project policy permits it.

- Create a fresh short-lived visual worker with no forked parent context and no inherited image-bearing history.
- Bind it to one page/module and normally one preprocessed image.
- Pre-compress/downscale locally before the call: recommended below 800 KB, hard default below 2 MB.
- Use at most one model-visible image per turn and do not use `detail="original"` unless the already-compressed file is below the budget.
- Never batch or loop multiple `view_image`/`image(...)` results into one tool output.
- Return only the evidence card; never relay the image block to CEO, another worker, memory, FlowSkill, or a later task.
- End the visual worker after the bounded inspection. Do not reuse it as a durable project or CEO lane.
- Record `modelVisibleImagesUsed`, `modelVisibleImageBytes`, worker/thread ID, source artifact hash, and why zero-payload analysis was insufficient.

User-supplied images remain user input to the current turn. Do not forward them to subagents or copy them into a new thread. If delegation is required, pass a local path plus bounded text summary under zero-payload mode, or use one explicitly admitted bounded visual worker.

## Three-Layer Evidence Model

### Layer 1 Raw Artifact Layer

Real visual files stay on the local filesystem, for example:

```text
artifacts/visual-checks/<task-id>/*.png
artifacts/visual-checks/<task-id>/*.jpg
artifacts/ui-render-targets-*/...
```

Allowed artifact roles include `reference`, `actual`, `diff`, `failure`, `generated candidate`, and `contact_sheet`. Record `sha256`, `width`, `height`, `bytes`, `viewport`, and `screen` whenever practical.

### Layer 2 Evidence Manifest Layer

Every visual task should generate or maintain:

```text
artifacts/visual-checks/<task-id>/visual-evidence-manifest.json
```

Suggested manifest fields:

```json
{
  "schemaVersion": 1,
  "taskId": "<task-id>",
  "generatedAt": "<iso timestamp>",
  "policy": "local-artifacts-only",
  "transportMode": "zero-payload-local-analysis",
  "modelVisibleImagesUsed": 0,
  "modelVisibleImageBytes": 0,
  "visualWorkerThreadId": null,
  "items": [
    {
      "role": "reference | actual | diff | failure | contact_sheet",
      "path": "artifacts/visual-checks/<task-id>/actual.png",
      "sha256": "sha256:...",
      "width": 1280,
      "height": 720,
      "bytes": 123456,
      "viewport": "1280x720",
      "screen": "project-home",
      "shortSummary": "one or two sentence local visual summary",
      "decision": "accept | revise | block"
    }
  ],
  "comparison": {
    "method": "manual | pixel | layout-metrics | OCR-summary | mixed",
    "result": "accept | revise | block",
    "topIssues": ["short issue 1", "short issue 2"]
  },
  "forbiddenPayloadsPresent": false
}
```

If a project cannot produce JSON, use an equivalent compact manifest text file with the same fields. The manifest is evidence metadata, not a place to store base64, complete OCR, full screenshot JSON, or full API responses.

### Layer 3 Thread / Memory Evidence Card

Threads, callbacks, acceptance reports, memory writeback, and FlowSkill candidates may only return a short card:

```text
Visual evidence:
- Task:
- Manifest:
- Reference:
- Actual:
- Actual sha256:
- Size:
- Bytes:
- Result: accept | revise | block
- Summary:
- Top issues:
- No image/base64/data:image/input_image payload included.
```

Do not attach images or paste long OCR/visual dumps into the card.

## Visual QA Is Still Required

For UI, game screens, design restoration, animation/motion, and generated-image review:

- workers may use Playwright or project tools to capture screenshots;
- zero-payload workers may use local OCR, image metadata, perceptual hashes, pixel/layout metrics, and deterministic comparison tools without returning pixels to the model;
- model-visible image inspection is allowed only through the bounded exception above, never in the CEO/project-main or a durable reusable lane;
- workers may compare reference and actual screenshots through local metrics or a separately admitted bounded visual worker;
- reviewers should inspect visual artifacts when visual quality is part of acceptance;
- CEO accepts from text evidence plus artifact paths/hashes, not from embedded image bodies.

If a task cannot be judged from zero-payload evidence, do not quietly call `view_image`. Return `insufficient_visual_evidence` or route one bounded visual worker. Do not paste or relay the image into the CEO thread as an attachment, `input_image`, base64, data URL, or tool image block.

## Image Budget

Default model-visible image budget is zero. This budget covers chat attachments, `view_image`, `image(...)`, browser/screenshot tool image blocks, `input_image`, base64, and data URLs; changing the tool name does not reset the budget.

If the user must provide an image directly in chat:

```text
maxImages: 1 per turn
recommended maxBytesPerImage: 800 KB
hard maxBytesPerImage: 2 MB
maxTotalBytes: 2 MB unless explicitly approved
```

The direct-image allowance applies only to a user-supplied image in the current turn or an explicitly admitted bounded visual worker. It does not authorize relaying that image to a subagent.

For multiple images, keep local paths or folder paths and run zero-payload analysis first. If model vision remains necessary, split into independent short-lived visual workers, one page/module and normally one compressed image per worker, and return path/hash/summary only. Never run a loop that returns many original images to one model turn.

OCR and visible-text budgets:

- OCR summary: 100-200 words maximum in thread/callback/memory.
- Visible text list: at most 30 labels unless the task is explicitly text-audit focused.
- Full OCR belongs in an artifacts cold sidecar, not Hot memory, callback, CEO acceptance, or FlowSkill candidate.

## Worker Callback Format

Allowed callback shape:

```text
Visual evidence:
- Task: <task-id>
- Manifest: artifacts/visual-checks/<task-id>/visual-evidence-manifest.json
- Reference: artifacts/ui-render-targets/project-home.png
- Actual: artifacts/visual-checks/project-home-1280x900.png
- Actual hash: sha256:...
- Size: 1280x900
- Bytes: 123456
- Captured at:
- Result: accept | revise | block
- Summary: short visual differences and quality judgment
- Top issues: 1-3 bullets, not a per-image dump
- No image/base64/data:image/input_image payload included.
- Visual transport mode:
- Model-visible images/bytes used: 0/0 in zero-payload mode
- Next edits: files/areas to adjust
```

Forbidden in callbacks:

- image attachments;
- base64 blobs;
- `data:image` URLs;
- `input_image` or tool image blocks;
- complete screenshot JSON;
- full OCR;
- full visual API request/response bodies;
- large OCR transcripts;
- stacked multi-image descriptions that become a hidden visual dump;
- large per-image descriptions for every screenshot in a batch.

## Memory And FlowSkill Writeback

Hot memory, project memory, project memory, FlowSkill candidates, and worker callbacks may store only:

- artifact path or folder path;
- hash;
- dimensions;
- OCR/visual summary when useful;
- design conclusion;
- accepted/revise/block decision;
- remaining visual issues;
- source/provenance refs.

Raw image files stay in local artifacts. Raw Codex sessions stay in cold vault. Do not write full image bytes, base64, `data:image`, full screenshots, or complete request bodies into hot-readable memory.

Do not mutate raw Codex session files as part of this policy. If a visual-heavy thread needs slimming, generate a sidecar compact recovery packet and artifact index; leave original session handling to explicit history-provider/compaction safety contracts.

## Third-Party API / CPA / Model Calls

Before sending visual payloads to third-party services:

- treat Codex `view_image`, `image(...)`, browser screenshot returns, and equivalent tool outputs as model/API visual payloads subject to this gate;
- default to zero bytes unless bounded model vision was explicitly admitted;
- reject any multi-image loop or batch whose total model-visible bytes were not precomputed before the call;
- reject, degrade, compress, summarize, or split requests above about 8-10 MB unless explicitly approved;
- prefer local files, compressed images, or summaries when the service supports them;
- if file references are unsupported, compress and batch instead of sending many large images at once;
- truncate base64 and `data:image` in logs;
- never duplicate full request bodies into debug logs, caches, memory, or callback text;
- never record full visual API request bodies or response bodies;
- record only request purpose, artifact paths, hashes, bytes, model/service name, and short result summaries.

If a request body exceeds the cap, CEO/worker must compress, split batches, degrade to local-summary mode, or ask the user for explicit approval. Do not silently send a giant visual payload.

## Broken / Stalled Visual Thread Recovery

Treat these as context-pressure or broken-thread signals:

- session size over about 50 MB;
- repeated `data:image`, base64, `input_image`, screenshot, or generated-image payloads;
- a single multi-image tool output or repeated `view_image` calls that add several MB even when the session is below 50 MB;
- hot session grows by many MB per visual turn;
- opening or harvesting the thread becomes slow due to image payloads.

Recovery route:

1. Stop using the visual-heavy thread as the project-main CEO thread.
2. Generate a compact `ThreadRecoveryPacket` plus visual artifact index.
3. Continue in a clean CEO/takeover thread when tools and authorization allow it.
4. New thread reads handoff, `.codex-knowledge`, artifact manifests, artifact index, compact visual summaries, and necessary source files first.
5. Run zero-payload local analysis first. If model vision is still necessary, use a new bounded short-lived visual worker; do not call `view_image` from the takeover/CEO thread.
6. Treat raw sessions and original image payloads as cold vault evidence, not default context.

Do not fork the bloated thread and do not copy image history into the takeover prompt.

## Task Card Fields

Use these fields for visual work:

```text
Visual evidence policy: local-artifacts-only
Visual transport mode: zero-payload-local-analysis by default
Reference input: local paths/folders only
Screenshot output: artifacts/visual-checks/<task-id>/
Manifest required: artifacts/visual-checks/<task-id>/visual-evidence-manifest.json
Thread return format: evidence card only
Model-visible image budget: 0 unless bounded-model-vision is explicitly admitted
Forbidden visual tools/returns in zero-payload mode: view_image, image(...), input_image, screenshot/image tool blocks
Artifact return policy: paths+hash+dimensions+bytes+summary+decision only
Forbidden payloads: image attachments, base64, data:image, input_image, full OCR, full screenshot JSON, full request bodies
CPA/API request body cap: 8-10 MB unless explicitly approved
Memory writeback: path/hash/dimensions/summary/decision only
Visual worker split: one page/module per worker when many screenshots are required
Visual transport receipt: mode + modelVisibleImagesUsed + modelVisibleImageBytes + worker/thread ID or skipped reason
```

## Acceptance Gate

CEO may accept visual work only when visual evidence is sufficient for the task risk. Text claims such as "looks good" are insufficient for UI/game/design tasks unless paired with artifact paths, screenshot hashes, inspected dimensions, summary, and reviewer/CEO decision.

Minimum acceptance evidence:

- manifest path;
- actual image path;
- reference image path when applicable;
- hash;
- dimensions;
- short visual summary;
- decision;
- top residual issues;
- confirmation that no image/base64/data:image/input_image payload entered callback, memory, FlowSkill candidate, or third-party logs.
- visual transport receipt confirming zero model-visible images/bytes, or the exact bounded worker/image budget and reason.

## Multi-Image / UI Target Batch Rule

For many references, UI targets, screenshots, generated candidates, or page states:

- split by module/page/target where practical;
- generate a contact sheet per module when useful;
- return only contact sheet path plus manifest path;
- do not attach 10-20 images to a chat turn;
- do not loop over `view_image` or `image(...)`; local paths and contact sheets do not become safe merely because the originals started on disk;
- do not write long per-image descriptions into the thread;
- use manifests and short issue lists to keep callback and memory small.
