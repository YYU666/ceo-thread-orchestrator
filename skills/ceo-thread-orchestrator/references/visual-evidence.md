# Visual Evidence Local-Artifact Policy

Use this reference for UI, game, design restoration, screenshot comparison, generated-image review, visual QA, and any task that might move image payloads through CEO Flow.

Core principle: visual quality still requires visual inspection. Do not disable screenshots, local image review, or visual comparison. What CEO Flow forbids is turning visual evidence into long-lived chat payloads, base64, `data:image`, full screenshot JSON, full OCR, full visual API request/response bodies, large per-image descriptions, memory blobs, FlowSkill candidates, worker callbacks, or third-party/CPA request logs.

## Standard Policy

```text
Visual evidence policy: local-artifacts-only
Reference input: local paths/folders only
Screenshot output: artifacts/visual-checks/<task-id>/
Manifest required: artifacts/visual-checks/<task-id>/visual-evidence-manifest.json
Thread return format: evidence card only
Image budget: no chat images; max direct image 0 unless user explicitly provides one
Artifact return policy: paths+hash+dimensions+bytes+summary+decision only
Forbidden payloads: image attachments, base64, data:image, full OCR, full screenshot JSON, full request/response bodies, large per-image descriptions
CPA/API request body cap: 8-10 MB unless explicitly approved
Memory writeback: path/hash/dimensions/summary/decision only
```

Store reference images, screenshots, comparison images, failed-state images, generated image candidates, contact sheets, and visual diffs in a project `artifacts/` location or equivalent local artifact folder. CEO/worker callbacks should report only path, dimensions, bytes, hash, timestamp, short visual summary, decision, and next edits.

Legacy shorthand `paths+hash+summary` remains valid, but the preferred evidence card should also include dimensions, bytes, manifest path, and decision when available.

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
- No image/base64/data:image payload included.
```

Do not attach images or paste long OCR/visual dumps into the card.

## Visual QA Is Still Required

For UI, game screens, design restoration, animation/motion, and generated-image review:

- workers may use Playwright or project tools to capture screenshots;
- workers may use local image viewers or visual inspection tools to inspect artifacts;
- workers may compare reference and actual screenshots;
- reviewers should inspect visual artifacts when visual quality is part of acceptance;
- CEO accepts from text evidence plus artifact paths/hashes, not from embedded image bodies.

If a task cannot be judged without seeing an image, inspect the local artifact file. Do not paste the image into the CEO thread as an attachment or base64 payload unless the user explicitly sends a single image for immediate understanding and the image budget allows it.

## Image Budget

Default image attachment budget is zero.

If the user must provide an image directly in chat:

```text
maxImages: 1 per turn
recommended maxBytesPerImage: 800 KB
hard maxBytesPerImage: 2 MB
maxTotalBytes: 2 MB unless explicitly approved
```

For multiple images, convert to local paths or folder paths first. For multi-page UI review, use short-lived visual workers, one page/module per worker where practical, and return path/hash/summary only.

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
- No image/base64/data:image payload included.
- Next edits: files/areas to adjust
```

Forbidden in callbacks:

- image attachments;
- base64 blobs;
- `data:image` URLs;
- complete screenshot JSON;
- full OCR;
- full visual API request/response bodies;
- large OCR transcripts;
- stacked multi-image descriptions that become a hidden visual dump;
- large per-image descriptions for every screenshot in a batch.

## Memory And FlowSkill Writeback

Hot memory, project memory, Zhixia memory, FlowSkill candidates, and worker callbacks may store only:

- artifact path or folder path;
- hash;
- dimensions;
- OCR/visual summary when useful;
- design conclusion;
- accepted/revise/block decision;
- remaining visual issues;
- source/provenance refs.

Raw image files stay in local artifacts. Raw Codex sessions stay in cold vault. Do not write full image bytes, base64, `data:image`, full screenshots, or complete request bodies into hot-readable memory.

Do not mutate raw Codex session files as part of this policy. If a visual-heavy thread needs slimming, generate a sidecar compact recovery packet and artifact index; leave original session handling to explicit Guardian/compaction safety contracts.

## Third-Party API / CPA / Model Calls

Before sending visual payloads to third-party services:

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
- hot session grows by many MB per visual turn;
- opening or harvesting the thread becomes slow due to image payloads.

Recovery route:

1. Stop using the visual-heavy thread as the project-main CEO thread.
2. Generate a compact `ThreadRecoveryPacket` plus visual artifact index.
3. Continue in a clean CEO/takeover thread when tools and authorization allow it.
4. New thread reads handoff, `.codex-knowledge`, artifact manifests, artifact index, compact visual summaries, and necessary source files first.
5. Open local images only when inspection is necessary.
6. Treat raw sessions and original image payloads as cold vault evidence, not default context.

Do not fork the bloated thread and do not copy image history into the takeover prompt.

## Task Card Fields

Use these fields for visual work:

```text
Visual evidence policy: local-artifacts-only
Reference input: local paths/folders only
Screenshot output: artifacts/visual-checks/<task-id>/
Manifest required: artifacts/visual-checks/<task-id>/visual-evidence-manifest.json
Thread return format: evidence card only
Image budget: no chat images; max direct image 0 unless user explicitly provides one
Artifact return policy: paths+hash+dimensions+bytes+summary+decision only
Forbidden payloads: image attachments, base64, data:image, full OCR, full screenshot JSON, full request bodies
CPA/API request body cap: 8-10 MB unless explicitly approved
Memory writeback: path/hash/dimensions/summary/decision only
Visual worker split: one page/module per worker when many screenshots are required
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
- confirmation that no image/base64/data:image payload entered callback, memory, FlowSkill candidate, or third-party logs.

## Multi-Image / UI Target Batch Rule

For many references, UI targets, screenshots, generated candidates, or page states:

- split by module/page/target where practical;
- generate a contact sheet per module when useful;
- return only contact sheet path plus manifest path;
- do not attach 10-20 images to a chat turn;
- do not write long per-image descriptions into the thread;
- use manifests and short issue lists to keep callback and memory small.
