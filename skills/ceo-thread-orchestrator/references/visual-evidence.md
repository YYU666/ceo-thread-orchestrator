# Visual Evidence And Image Payload Safety

Use this reference for UI, game, design restoration, screenshot comparison, generated-image review, visual QA, and any task that might move image payloads through CEO Flow.

Core principle: visual quality still requires visual inspection. Do not disable screenshots, local image review, or visual comparison. What CEO Flow forbids is turning visual evidence into long-lived chat payloads, base64, `data:image`, full screenshot JSON, memory blobs, FlowSkill candidates, worker callbacks, or third-party request/debug logs.

## Standard Policy

```text
Visual evidence policy: local-artifacts-only
Reference input: local paths/folders only
Screenshot output: artifacts path + hash + summary
Artifact return policy: paths+hash+summary only
Forbidden: image attachments/base64/data:image in callbacks, memory writeback, FlowSkill candidates, and third-party logs
```

Store reference images, screenshots, comparison images, failed-state images, generated image candidates, and visual diffs in a project `artifacts/` location or equivalent local artifact folder. CEO/worker callbacks should report only path, dimensions, hash, timestamp, short visual summary, decision, and next edits.

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

## Worker Callback Format

Allowed callback shape:

```text
Visual evidence:
- Reference: artifacts/ui-render-targets/project-home.png
- Actual: artifacts/visual-checks/project-home-1280x900.png
- Actual hash: sha256:...
- Size: 1280x900
- Captured at:
- Result: accept | revise | block
- Summary: short visual differences and quality judgment
- Next edits: files/areas to adjust
```

Forbidden in callbacks:

- image attachments;
- base64 blobs;
- `data:image` URLs;
- complete screenshot JSON;
- large OCR transcripts;
- stacked multi-image descriptions that become a hidden visual dump.

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
- record only request purpose, artifact paths, hashes, sizes, and short result summaries.

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
4. Read project memory, artifact paths/hashes, compact visual summaries, and necessary source files first.
5. Treat raw sessions and original image payloads as cold vault evidence, not default context.

Do not fork the bloated thread and do not copy image history into the takeover prompt.

## Task Card Fields

Use these fields for visual work:

```text
Visual evidence policy: local-artifacts-only
Reference input: local paths/folders only
Screenshot output: artifacts path + hash + summary
Image budget: maxImages, maxBytesPerImage, maxTotalBytes
Artifact return policy: paths+hash+summary only
Forbidden: image attachments/base64/data:image in callbacks, memory writeback, FlowSkill candidates
Third-party request body limit: 8-10 MB unless explicitly approved
Visual worker split: one page/module per worker when many screenshots are required
```

## Acceptance Gate

CEO may accept visual work only when visual evidence is sufficient for the task risk. Text claims such as "looks good" are insufficient for UI/game/design tasks unless paired with artifact paths, screenshot hashes, inspected dimensions, summary, and reviewer/CEO decision.
