# Changelog

## Unreleased

- Published the external-execution work as the opt-in `openclaw-cost-efficient-execution` branch so `main` retains the original Codex-internal workflow. Added a branch rationale, explicit installation choice, responsibility split, cost caveats, and local-data boundary.
- Added cross-platform External Execution Providers: Codex control/assurance/publish planes, provider-neutral OpenClaw/ACP/MCP/CLI/webhook routing, R0-R3 cost/risk tiers, hash-bound task/receipt schemas, safe file-exchange conventions, an opt-in OpenClaw JSON bridge, executable validation, and external receipt scorecard gates.
- Added a thin OpenClaw `ceoflow-external-executor` skill plus deterministic project-role session reuse. CEO Flow now reuses `agent:<agentId>:ceoflow:<projectId>:<laneId>`, blocks arbitrary executor-side session spawning, and requires a recorded reason before rotating a broken or isolated lane.
- Disabled local-model execution for the current CEO Flow release: `localMode=true`, `--local`, isolated `.openclaw-ceoflow` routing, and `ollama/<model>` tasks now fail closed. External execution uses an explicitly configured cloud/provider model and must preflight auth, tools, thinking controls, and retry budget before dispatch.
- Redirected normal Codex subagent/contractor execution to OpenClaw reusable project-role sessions. Codex `spawn_agent`/`multi_agent` routes now default to deny, OpenClaw nested spawn remains forbidden, and only a higher-priority host-required bounded exception may use a Codex subagent.
- Added multi-project OpenClaw isolation and frontend visibility gates: exact project identity hashes, CEO owner/dispatch leases, project-scoped labels/categories, official Gateway session registration, archived/busy-session rejection, `Main Session` exclusion, single-writer policy, frontend-visible receipt evidence, and OpenClaw native-memory denial.
- Added OpenClaw model-route preflight after the live frontend probe exposed host-level fallback behavior. Tasks now declare preferred/exact model requirements and deny/CEO-approved fallback lists; unapproved configured fallbacks block before model execution.
- Replaced the narrow `openclaw sessions` verification path with Gateway `sessions.list` after CEO Flow and RGS independently reproduced missing-category false blocks. Active and archived queries now validate category, busy state, and supported thinking options before dispatch.
- Added a validated MiniMax dynamic-routing policy. `auto-class` maps R0/R1/R2/R3 importance to `fast/balanced/frontier`, selects only enabled+validated+live OpenClaw MiniMax candidates, and assigns the real `off/adaptive` thinking controls. M3 is the only active validated model; M2.7-highspeed remains disabled pending a controlled tool/coding/receipt probe.
- Upgraded transient provider recovery: MiniMax network failures remain schema-valid `failed/external_provider_network_error` receipts, but an unchanged workspace may now receive one delayed same-session/same-model retry. Independent workspace fingerprints expose partial writer mutations, attempt evidence is immutable, two failures open a five-minute provider circuit, and provider cooldown no longer blocks the whole Program Goal. GPT/cross-provider/local fallback remains denied.
- Hardened MiniMax/OpenClaw receipt adaptation after the first successful adaptive run returned provider-native object arrays: the prompt now requires string-array fields, the bridge safely canonicalizes bounded object entries without another model call, nested Gateway telemetry overrides untrusted model/thinking self-reports, and `reprocess-openclaw` can recover a preserved successful raw result offline.

- Added the Single Front Door contract: one default user-facing CEO identity, CEO-mediated specialist escalation, durable-visible versus background-contractor classification, star-shaped callbacks instead of chained handoffs, and neutral review preserved behind the unified entrance.

- Added Zhixia 0.9.0 Memory Core compatibility: event-triggered Project Continuity Gate, exact project identity, full 14-slot mandatory pagination for CEO recovery, role-bounded worker/reviewer slots, runtime event observation, source-backed decision writeback, trigger-receipt verification, helper-only partial/recovery-not-ready boundaries, and an isolated real-project Electron recovery probe/report.
- Hardened the Zhixia recovery probe after external audit with a source-backed 14/14-slot fixture, forced eight-page `32/32` mandatory traversal, final `recoveryReady=true`, independent seed/status/page identity comparison, wrong/cross-project identity rejection, tampered-cursor rejection, and exact per-call trigger-receipt ID/scope matching that excludes initialization receipts.

- Added a capability-discovered Model Routing Gate with `inherit`, `auto-class`, `pinned`, and `host-auto` modes; separate fast/balanced/frontier model classes from reasoning effort; prevent accidental frontier/high inheritance across routine fan-out; and record fallback plus actual model/reasoning evidence.

- Added an end-to-end CEO Flow behavior smoke protocol for proving CEO -> implementation -> review -> CEO harvest/decision before stable release, and refined visual payload detection to avoid ordinary `base64,` prose false positives.

- Reworked executable guardrails after external audit: structured PyYAML handoff/pipeline validators, adversarial unit tests, GitHub Actions CI, release-state check, and clearer smoke-eval/validator documentation.

- Added hard Repo Baseline Gate rules: dirty budget thresholds, strong worktree blocking for critical untracked files, Slice Closure Gate after accepted implementation slices, file ownership preflight, and controlled baseline task template.

- Strengthened Visual Evidence Local-Artifact Policy with three-layer raw/manifest/evidence-card model, full OCR/screenshot JSON guards, contact-sheet batch returns, and CPA/API payload caps.

- Added large-project CEO Autopilot rules: project/task scale classifier, startup card, bootstrap exit, staffing/lane-count decision, proof-loop fuse, and long-term Warm Anchor memory gate.

- Split context/memory policy into focused `memory-runtime.md` and `guardian-history.md` references while keeping `context-memory.md` as a lightweight router.

- Added a Memory Runtime result envelope with `memoryMode`, hot/warm/skill/cold `memoryLayers`, `recallPlan`, top memory items, and retrieved sourceRefs.

- Added a Memory Trigger Gate so Zhixia or equivalent Memory Runtime retrieval becomes a default lifecycle action for project resume, dispatch, precedent lookup, recovery, and accept/revise/block writeback.

- Added a Worktree Readiness Gate so CEO Flow blocks worktree implementation lanes when critical source/config/test files are untracked, falling back to one canonical writer plus read-only parallel lanes until a repo baseline task fixes it.

- Added visual evidence and image payload safety rules: visual QA remains required, but screenshots/reference/generated images stay in local artifacts while callbacks, memory, FlowSkill candidates, and third-party logs use paths, hashes, summaries, and decisions only.

- Added a Contractor/Subagent outside-help role so temporary subagents can support exploration, audit, verification, or disjoint bounded patches without replacing durable visible lanes; contractor traces preserve history for memory providers.

- Added a static `scripts/smoke_eval.py` harness plus `examples/smoke-eval-cases.json` to guard policy coverage for recent CEO Flow regressions without calling an LLM.
- Added `references/state-schema.md` to formalize Program Goal, Completion Dashboard, lane roster, harvest driver, decision, ThreadRecoveryPacket, and memory candidate contracts.
- Slimmed the main `SKILL.md` into a lean operating entry point and moved detailed state/goal/harvest policy behind references for progressive disclosure.

- Upgraded the CEO Flow pipeline layer beyond MVP with bundled `pipeline.yaml`, `typed_handoff.yaml`, `review_handoff.yaml`, and `scorecard.md` templates.
- Added lightweight `validate_pipeline.py` and `scorecard_handoff.py` scripts so pipeline contracts and worker/review handoffs can be checked before CEO acceptance.
- Added an operating playbook reference that gives a stable end-to-end decision flow for direct answers, CEO-only work, worker callbacks, runtime Goal harvest drivers, parallel waves, pipeline contracts, approval stalls, and accept/revise/block closure.
- Updated smoke prompts and pipeline docs to require template/validator-aware behavior while preserving the lightweight, non-workflow-engine boundary.
- Added a thin FlowSkill hook reference for optional local reusable-skill search, capture, and score operations without merging FlowSkill implementation into CEO Flow.
- Added worker role-contamination guardrails: prefer clean worker creation over CEO-thread forks, classify self-routing workers as `role_contamination`, and keep harvest drivers current when lanes are superseded.
- Clarified runtime Goal as orchestration state, not execution mode; direct CEO fallback under active Goal is a bounded lease and must restore worker/review routing.
- Added a role roster gate so Core Team execution assigns explicit lane roles, write-sets, callback policy, stop condition, and thread-operation permissions before dispatch.
- Added a mandatory neutral review gate for substantial app-code, PRD execution, runtime Goal implementation, direct-fallback output, user-facing/high-risk work, and repeated-fix loops.
- Added a top-down reasoning direction gate: CEO may assign lane reasoning profiles, but worker/review/audit callbacks cannot mutate CEO reasoning, model, role, or quality gates.
- Added a subagent gate that keeps subagents as temporary bounded scouts rather than substitutes for durable visible lanes, Program Goal harvest, or persistent expert roles.
- Added failure-triggered reflection / self-harness guidance so CEO Flow diagnoses repeated process failures with minimal evidence-backed packets instead of adding always-on reflection overhead.
- Added a generic Memory Runtime lifecycle contract for compact project memory providers: retrieve context/precedent, write back evidence, and promote memory under source-backed safety boundaries.
- Added portfolio steering guardrails so terminal lane/subline `pause`, `accept`, `block`, or `supersede` results trigger a Program Goal dashboard check; a module pause no longer implies project pause.
- Added a runtime Goal tool-state guard so stale/blocked host goals do not override the Program Goal Brief or stop product-progress waves when safe work remains.
- Added lightweight state-discipline guidance so CEO Flow borrows evidence-backed state transitions from legacy workflow thinking without loading old task pools, leases, supervisors, review queues, or completion ledgers by default.
- Added a lightweight Reference Scan Gate so substantial coding/product/architecture/UI/workflow/creative work starts from official docs, mature open-source patterns, excellent examples, and local conventions without becoming heavy research.
- Added stale lane reference recovery rules so missing, typoed, archived, or replaced worker/review thread ids trigger bounded locator fallback instead of retry loops or whole-program stalls.
- Added one-primary-harvest-driver rules so active runtime Goals and project-main heartbeats do not run as duplicate co-primary harvest loops.
- Added Broken CEO Thread / Heartbeat Fuse rules so stream-broken, repeatedly empty, context-exhausted, or unreadable CEO heartbeat targets move to compact ThreadRecoveryPacket takeover instead of being re-harvested or forked.

## v0.2.6 - Zhixia Context Slimming And Neutral Review

- Slimmed the main `SKILL.md` into a short operating entry point and moved detailed policies into focused `references/` files for progressive disclosure.
- Added PRD parallel execution wave guidance so independent non-overlapping tasks can run together while CEO tracks write-set ownership, integration order, harvest, and review.
- Added Runtime Context Governor rules: compact task packets, long-thread/context-pressure fuse, Guardian health as read-only pressure evidence, strict raw-session gate, and no automatic cleanup/prune behavior.
- Added old-thread continuity policy: when the user wants to keep using an old thread, CEO Flow should check Zhixia/Guardian history cards and compact receipts, prefer explicit selected-thread optimization plus retrieval, and treat fresh-thread handoff as a fallback.
- Added left-sidebar hygiene rules: visible lanes need planned titles, lane ids, lifecycle policy, roster tracking, pin/archive behavior, and subagents must not replace persistent worker/review threads.
- Added Workspace / Project Root Guard so CEO and worker lanes must stay anchored to the canonical project folder or an approved worktree before implementation work.
- Added release-readiness guidance from independent audit: compatibility matrix, Guardian implemented-vs-planned command status, code-producing smoke requirement, and tighter operating-mode labels.
- Added knowledge provider modes: `none`, `project-memory`, `zhixia-local-docs`, `guardian-history`, and `hybrid`.
- Clarified that Zhixia owns current project context while Guardian owns old Codex history, paused-task discovery, history evidence, health summaries, and restore dry-runs.
- Added `Knowledge provider mode`, `Context / history budget`, `Guardian usage`, `Zhixia retrieval`, `Memory writeback target`, and `Restore policy` fields to task cards.
- Strengthened independent review gates: reviewers must stay neutral, avoid flattering or reassuring weak work, and use high reasoning/thinking when available.
- Added document-first delivery for substantial CEO planning and review artifacts such as PRDs, task graphs, task-card packs, audit/review reports, acceptance reports, and handoff packets.
- Added the CEO Flow Guardian integration contract document for Zhixia local docs and Codex History Guardian.

## v0.2.5 - Unattended Command Approval Planning

- Added an unattended execution policy so CEO Flow plans command approval profiles before dispatching worker lanes.
- Added task-card fields for allowed command families and commands that must not run.
- Clarified that routine command approvals are not product approvals and should not be scattered across worker threads.
- Added guidance for fully unattended waves: preauthorize command families, choose safer no-approval commands, reuse lanes with the right permission profile, or hold the wave at the CEO lane before dispatch.
- Added a smoke prompt for unattended command approval behavior.

## v0.2.4 - PRD Core Team Execution

- Added a default Core Team role map for CEO, implementation, review/QA, product/UX, knowledge/memory, and research/docs work.
- Clarified that the thread owning an accepted PRD, design brief, or task graph is the CEO thread by default.
- Added a PRD-to-execution gate: after the user asks to execute an accepted plan, CEO Flow should leave CEO-only planning and route work through reusable or requested expert lanes.
- Added a CEO harvest loop so the CEO collects worker results, classifies lane status, sends revisions or next tasks, and keeps routine in-scope approvals inside the CEO lane.
- Kept the Core Team model lightweight: roles are not permanent threads, and they do not create automatic queues, supervisor loops, or background workers.
- Added smoke prompts for PRD-to-Core-Team execution and CEO harvest behavior.

## v0.2.3 - CEO Flow

- Added CEO Flow as the short public display name while keeping `ceo-thread-orchestrator` as the compatible package and skill id.
- Added a lightweight team registry template for reusable lanes with role, capabilities, write policy, trust level, status, and last evidence.
- Added evidence memory card guidance so reusable lessons are promoted only when backed by concrete proof.
- Clarified Zhixia / `.codex-knowledge/` as the recommended CEO Flow knowledge provider while allowing projects to specify another local knowledge path.
- Updated smoke prompts for roster, evidence-memory, and CEO Flow alias behavior.

## v0.2.2 - Doom Loop Guardrails

- Added task-card fields for architecture invariants, required reference docs, and rollback baseline.
- Strengthened the code quality gate against doom loops, tech-stack drift, copy-paste logic, weak naming, magic numbers, missing boundary checks, and one-shot code.
- Added worker self-review, static-check expectations, and independent read-only review guidance for high-risk changes.
- Added smoke prompts for doom-loop recovery and maintainability gates.

## v0.2.1 - Code Quality Gate

- Added code quality gates to reduce broad speculative rewrites and repeated low-signal patch attempts.
- Added change budget and quality-gate reporting fields to implementation task cards.
- Added a smoke prompt for failed bug-fix loops that need root-cause re-analysis.

## v0.2.0 - Goal Completion Loop

- Added a goal completion loop so CEO orchestration continues toward accepted, blocked, or superseded outcomes.
- Added goal brief guidance, active goal ledger fields, and closure-state reporting.
- Tightened direct CEO fallback behavior so broad app-code/UI work routes to implementation lanes unless explicitly authorized.
- Added transient model failure handling so temporary 5xx/502 service errors do not become permanent model bans.
- Clarified exact model variant routing for preview or special pricing lanes.
- Improved public README positioning for open-source discovery.
- Added community contribution, code of conduct, security, issue, and PR templates.

## v0.1.1

- Removed private workflow names and local environment references from public skill text.
- Replaced private implementation details with generic configured task-pool and external-worker wording.

## v0.1.0

- Initial public release of CEO Thread Orchestrator.
- Added CEO-as-brain orchestration model, specialist lanes, memory bootstrap, adaptive staffing, review gates, and open-source readiness checklist.
