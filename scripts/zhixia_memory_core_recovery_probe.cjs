const fs = require("node:fs");
const crypto = require("node:crypto");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const zhixiaRoot = path.resolve(process.argv[2] || "");
const sourceProject = path.resolve(process.argv[3] || "");

if (!fs.existsSync(zhixiaRoot) || !fs.existsSync(sourceProject)) {
  throw new Error("Usage: node run-zhixia-memory-core-recovery-probe.cjs <zhixia-app-root> <real-project-root>");
}

const electronExe = path.join(
  zhixiaRoot,
  "node_modules",
  "electron",
  "dist",
  process.platform === "win32" ? "electron.exe" : "electron",
);
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ceoflow-zhixia-real-recovery-"));
const userData = path.join(tempRoot, "user-data");
const codexHome = path.join(tempRoot, "codex-home");
const projectPath = path.join(tempRoot, "ceo-flow-project-snapshot");
const authoritativeProjectPath = path.join(tempRoot, "authoritative-14-slot-project");
const memoryRuntimeRoot = path.join(userData, "memory-runtime");

function extractFunctionSource(source, functionName) {
  const start = source.indexOf(`function ${functionName}`);
  if (start < 0) throw new Error(`${functionName} was not found in Zhixia main.cjs`);
  const signature = source.slice(start).match(/^function\s+\w+\s*\([\s\S]*?\)\s*\{/);
  if (!signature) throw new Error(`${functionName} has no extractable signature`);
  const bodyStart = start + signature[0].lastIndexOf("{");
  let depth = 0;
  for (let index = bodyStart; index < source.length; index += 1) {
    if (source[index] === "{") depth += 1;
    if (source[index] === "}") depth -= 1;
    if (depth === 0) return source.slice(start, index + 1);
  }
  throw new Error(`${functionName} body was not closed`);
}

function normalizeComparablePath(value) {
  const resolved = path.resolve(String(value || ""));
  const normalized = resolved.replace(/\\/g, "/").replace(/\/+$/, "");
  return process.platform === "win32" ? normalized.toLowerCase() : normalized;
}

function copyRequiredSnapshot() {
  const mappings = [
    ["README.md", "README.md"],
    ["CHANGELOG.md", path.join("docs", "RELEASE_NOTES.md")],
    [
      path.join("docs", "smoke", "CEO_FLOW_E2E_BEHAVIOR_SMOKE_REPORT_2026-07-08.md"),
      path.join("docs", "CEO_FLOW_HANDOFF.md"),
    ],
    [
      path.join("skills", "ceo-thread-orchestrator", "SKILL.md"),
      path.join("codex-skills", "e2e-review-skill", "SKILL.md"),
    ],
    [path.join("scripts", "smoke_eval.py"), path.join("scripts", "smoke_eval.py")],
  ];
  for (const [sourceRel, targetRel] of mappings) {
    const source = path.join(sourceProject, sourceRel);
    if (!fs.existsSync(source)) throw new Error(`Missing real-project source: ${source}`);
    const target = path.join(projectPath, targetRel);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(source, target);
  }
}

function seedRealProjectSnapshot() {
  const mainSource = fs.readFileSync(path.join(zhixiaRoot, "electron", "main.cjs"), "utf8");
  const helperSource = extractFunctionSource(mainSource, "buildMemoryCoreProjectSeedInput");
  const buildMemoryCoreProjectSeedInput = Function(
    "path",
    "crypto",
    `"use strict"; ${helperSource}; return buildMemoryCoreProjectSeedInput;`,
  )(path, crypto);
  const { createMemoryCoreRuntime } = require(path.join(zhixiaRoot, "electron", "memoryCoreRuntime.cjs"));
  const sourceFiles = [];
  const stack = [projectPath];
  while (stack.length) {
    const current = stack.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const target = path.join(current, entry.name);
      if (entry.isDirectory()) stack.push(target);
      else if (/\.(md|py)$/i.test(entry.name) || entry.name === "SKILL.md") sourceFiles.push(target);
    }
  }
  const projectDocs = sourceFiles.sort().map((filePath, index) => {
    const stat = fs.statSync(filePath);
    const content = fs.readFileSync(filePath);
    return {
      id: `real-project-doc-${index + 1}`,
      workspacePath: projectPath,
      filePath,
      fileModifiedAt: stat.mtime.toISOString(),
      updatedAt: stat.mtime.toISOString(),
      contentHash: crypto.createHash("sha256").update(content).digest("hex"),
      artifactType: /SKILL\.md$/i.test(filePath) ? "skill" : /README/i.test(filePath) ? "readme" : "report",
      sourceType: "codex_output",
      parseStatus: "ok",
    };
  });
  const seedInput = buildMemoryCoreProjectSeedInput({
    projectPath,
    projectDocs,
    layered: { project: "CEO Flow" },
    projectRecord: {
      name: "CEO Flow",
      aliases: ["CEO Flow", "ceo-thread-orchestrator"],
      governance: { status: "confirmed", reviewState: "current" },
    },
    projectRecordOverride: {
      confirmedAt: new Date().toISOString(),
      lastSummary: "CEO Flow orchestration skill real-project snapshot used for isolated Zhixia 0.9.0 recovery verification.",
      completion: "testing",
    },
  });
  if (!seedInput) throw new Error("Real-project snapshot did not produce a Memory Core seed input");
  const runtime = createMemoryCoreRuntime({ storeRoot: memoryRuntimeRoot });
  const result = runtime.seedProject(seedInput);
  return {
    projectId: result.projectId || seedInput.projectId || null,
    sourceDocCount: projectDocs.length,
    sourceRefCount: seedInput.sourceRefs.length,
    writeActions: (result.writes || []).map((write) => write.action),
  };
}

function createAuthoritative14SlotFixture() {
  const {
    createMemoryCoreRuntime,
    deriveProjectIdentity,
  } = require(path.join(zhixiaRoot, "electron", "memoryCoreRuntime.cjs"));
  const now = new Date().toISOString();
  const projectId = deriveProjectIdentity({ projectPath: authoritativeProjectPath }).projectId;
  const moduleId = "module-ceoflow-memory-core-compat";
  const docs = {
    prd: path.join(authoritativeProjectPath, "docs", "PRD.md"),
    architecture: path.join(authoritativeProjectPath, "docs", "ARCHITECTURE.md"),
    status: path.join(authoritativeProjectPath, "docs", "STATUS.md"),
    recovery: path.join(authoritativeProjectPath, "docs", "RECOVERY.md"),
  };
  for (const [name, filePath] of Object.entries(docs)) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, `# ${name}\n\nAuthoritative fixture evidence for ${projectId}.\n`, "utf8");
  }
  const sourceRef = (name, filePath = docs.status, refModuleId = moduleId) => ({
    kind: "project_doc",
    path: filePath,
    title: `Authoritative fixture ${name}`,
    hash: crypto.createHash("sha256").update(`${projectId}:${name}`).digest("hex"),
    projectId,
    moduleId: refModuleId,
    updatedAt: now,
  });
  const anchors = [
    {
      anchorId: "anchor-original-product-goal",
      category: "original_goal",
      statement: "Complete and verify the full CEO Flow Memory Core lifecycle integration.",
      authorityStatus: "accepted",
      sourceRefs: [sourceRef("original-goal", docs.prd)],
      updatedAt: now,
    },
    ...Array.from({ length: 12 }, (_, index) => ({
      anchorId: `anchor-architecture-${index + 1}`,
      category: "architecture",
      statement: `Authoritative architecture continuity rule ${index + 1}.`,
      authorityStatus: "accepted",
      sourceRefs: [sourceRef(`architecture-${index + 1}`, docs.architecture)],
      updatedAt: now,
    })),
    ...Array.from({ length: 12 }, (_, index) => ({
      anchorId: `anchor-standing-rule-${index + 1}`,
      category: index % 3 === 0 ? "safety" : index % 3 === 1 ? "acceptance" : "non_negotiable",
      statement: `Authoritative standing rule ${index + 1}.`,
      authorityStatus: "accepted",
      sourceRefs: [sourceRef(`standing-rule-${index + 1}`, docs.prd)],
      updatedAt: now,
    })),
  ];
  const modules = Array.from({ length: 3 }, (_, index) => ({
    moduleId: `module-authoritative-${index + 1}`,
    name: `Authoritative Module ${index + 1}`,
    purpose: `Fill the active module continuity slot ${index + 1}.`,
    currentStatus: "active",
    authorityStatus: "accepted",
    sourceRefs: [sourceRef(`module-${index + 1}`, docs.architecture, `module-authoritative-${index + 1}`)],
    updatedAt: now,
  }));
  const runtime = createMemoryCoreRuntime({ storeRoot: memoryRuntimeRoot });
  const seed = runtime.seedProject({
    projectPath: authoritativeProjectPath,
    projectName: "CEO Flow Authoritative Recovery Fixture",
    projectSummary: "A complete, source-backed 14-slot fixture that must paginate across multiple pages.",
    phase: "integration_verification",
    sourceRefs: [sourceRef("project-brain", docs.prd)],
    anchors,
    modules,
    now,
  });
  const checkpoint = runtime.formAppOwnedLifecycleEvent("observe_event", {
    eventType: "task_checkpoint",
    eventId: "ceoflow-zhixia-090-authoritative-checkpoint",
    projectPath: authoritativeProjectPath,
    projectId,
    moduleId,
    deterministic: true,
    riskLevel: "low",
    title: "Authoritative 14-slot recovery checkpoint",
    summary: "All required ProjectBrain continuity categories have source-backed fixture evidence.",
    acceptedProgress: ["Authoritative compatibility fixture seeded."],
    openTasks: ["Consume every mandatory continuation page."],
    blockers: ["A synthetic blocker record verifies the blocker slot."],
    nextActions: ["Verify final recoveryReady after complete pagination."],
    threadRefs: [{ threadId: "ceo-authoritative-fixture-thread" }],
    artifacts: [{
      id: "authoritative-recovery-doc",
      title: "Authoritative recovery contract",
      path: docs.recovery,
      sourceRef: sourceRef("recovery-contract", docs.recovery),
    }],
    sourceRefs: [sourceRef("checkpoint", docs.status)],
    observedAt: now,
  }, { now });
  if (checkpoint.accepted !== true || !checkpoint.receipt?.receiptId) {
    throw new Error(`Authoritative checkpoint formation failed: ${JSON.stringify(checkpoint)}`);
  }
  const record = (id, title, filePath, extra = {}) => ({
    id,
    title,
    projectId,
    authorityStatus: "accepted",
    mandatory: true,
    noDecay: true,
    sourceRefs: [sourceRef(id, filePath)],
    updatedAt: now,
    ...extra,
  });
  const workingState = {
    acceptedProgress: [record("progress-1", "Authoritative integration progress accepted.", docs.status)],
    openTasks: [record("task-1", "Finish the bounded compatibility verification.", docs.status, { status: "open" })],
    openBlockers: [record("blocker-1", "Synthetic blocker evidence is explicitly tracked.", docs.status, { status: "open" })],
    latestFailures: [record("failure-1", "A prior bounded failure is preserved as current evidence.", docs.status)],
    nextActions: [record("action-1", "Publish only after all pages and receipts verify.", docs.status, { status: "open" })],
    threadLineage: [record("thread-1", "CEO authoritative fixture thread lineage.", docs.recovery)],
    canonicalDocs: [record("canonical-doc-1", "Canonical PRD and recovery contract.", docs.prd)],
  };
  return {
    projectPath: authoritativeProjectPath,
    projectId,
    moduleId,
    now,
    workingState,
    seedWriteActions: seed.writes.map((write) => write.action),
    checkpointReceiptId: checkpoint.receipt.receiptId,
    anchorCount: anchors.length,
    moduleCount: modules.length,
  };
}

function runProbe(safetySeed, authoritativeFixture) {
  const projectJson = JSON.stringify(projectPath);
  const normalizedProjectJson = JSON.stringify(normalizeComparablePath(projectPath));
  const safetySeedJson = JSON.stringify(safetySeed);
  const authoritativeFixtureJson = JSON.stringify(authoritativeFixture);
  const probeScript = `(async () => {
    const projectPath = ${projectJson};
    const normalizedExpectedProjectPath = ${normalizedProjectJson};
    const safetySeed = ${safetySeedJson};
    const authoritativeFixture = ${authoritativeFixtureJson};
    const normalizeComparablePath = (value) => String(value || "")
      .replace(/\\\\/g, "/")
      .replace(/\\/+$/, "")
      .toLowerCase();
    const initialization = await window.docKnowledge.e2eProbe({ projectPath });
    const baselineReceiptResult = await window.docKnowledge.listMemoryRuntimeTriggerReceipts({ projectPath, limit: 100 });
    const baselineReceiptIds = new Set((baselineReceiptResult.receipts || []).map((receipt) => receipt.id));
    const status = await window.docKnowledge.getMemoryCoreContinuityStatus({
      projectPath,
      projectId: safetySeed.projectId,
      projectName: "CEO Flow",
      projectSummary: "CEO Flow orchestration skill real-project snapshot",
      tokenBudget: 2200,
      maxPacketItems: 8,
      maxPacketChars: 12000
    });
    const projectId = status.projectId;
    const pages = [];
    let cursor = null;
    let mandatoryReturned = 0;
    let mandatoryTotal = 0;
    let finalPage = null;
    for (let pageIndex = 0; pageIndex < 20; pageIndex += 1) {
      const page = await window.docKnowledge.getProjectContinuity({
        projectPath,
        projectId: safetySeed.projectId,
        projectName: "CEO Flow",
        projectSummary: "CEO Flow orchestration skill real-project snapshot",
        taskGoal: "Recover CEO Flow project continuity for Zhixia 0.9.0 compatibility",
        cursor,
        tokenBudget: 2200,
        maxPacketItems: 4,
        maxPacketChars: 9000
      });
      finalPage = page;
      const packet = page.continuityPacket || {};
      mandatoryReturned += Number(packet.mandatoryReturned || 0);
      mandatoryTotal = Math.max(mandatoryTotal, Number(packet.mandatoryTotal || 0));
      pages.push({
        index: pageIndex,
        projectId: page.projectId,
        projectPath: page.projectPath,
        returned: Number(packet.mandatoryReturned || 0),
        total: Number(packet.mandatoryTotal || 0),
        remaining: Number(packet.mandatoryRemaining || 0),
        mandatoryComplete: page.mandatoryComplete === true,
        recoveryReady: page.recoveryReady === true,
        nextCursor: page.nextCursor || null,
        missing: page.missing || [],
        stale: page.stale || [],
        conflict: page.conflict || []
      });
      if (!page.nextCursor) break;
      cursor = page.nextCursor;
    }

    const successStatus = await window.docKnowledge.getMemoryCoreContinuityStatus({
      projectPath: authoritativeFixture.projectPath,
      projectId: authoritativeFixture.projectId,
      projectName: "CEO Flow Authoritative Recovery Fixture",
      projectSummary: "Complete source-backed 14-slot recovery fixture",
      taskGoal: "Prove complete multi-page ProjectBrain recovery",
      workingState: authoritativeFixture.workingState,
      tokenBudget: 2200,
      maxPacketItems: 4,
      maxPacketChars: 9000
    });
    const successPages = [];
    let successCursor = null;
    let successMandatoryReturned = 0;
    let successMandatoryTotal = 0;
    let successFinalPage = null;
    for (let pageIndex = 0; pageIndex < 40; pageIndex += 1) {
      const page = await window.docKnowledge.getProjectContinuity({
        projectPath: authoritativeFixture.projectPath,
        projectId: authoritativeFixture.projectId,
        projectName: "CEO Flow Authoritative Recovery Fixture",
        projectSummary: "Complete source-backed 14-slot recovery fixture",
        taskGoal: "Prove complete multi-page ProjectBrain recovery",
        workingState: authoritativeFixture.workingState,
        cursor: successCursor,
        tokenBudget: 2200,
        maxPacketItems: 4,
        maxPacketChars: 9000
      });
      successFinalPage = page;
      const packet = page.continuityPacket || {};
      successMandatoryReturned += Number(packet.mandatoryReturned || 0);
      successMandatoryTotal = Math.max(successMandatoryTotal, Number(packet.mandatoryTotal || 0));
      successPages.push({
        index: pageIndex,
        projectId: page.projectId,
        projectPath: page.projectPath,
        returned: Number(packet.mandatoryReturned || 0),
        total: Number(packet.mandatoryTotal || 0),
        remaining: Number(packet.mandatoryRemaining || 0),
        pageStart: Number(packet.mandatoryManifest?.pageStart ?? -1),
        pageEndExclusive: Number(packet.mandatoryManifest?.pageEndExclusive ?? -1),
        manifestFingerprint: packet.manifestFingerprint || null,
        mandatoryComplete: page.mandatoryComplete === true,
        recoveryReady: page.recoveryReady === true,
        nextCursor: page.nextCursor || null,
        filled: packet.continuity?.filledSlots || [],
        missing: page.missing || [],
        stale: page.stale || [],
        conflict: page.conflict || []
      });
      if (!page.nextCursor) break;
      successCursor = page.nextCursor;
    }
    const firstSuccessCursor = successPages[0]?.nextCursor || null;
    const negativeChecks = {
      wrongProjectIdRejected: false,
      crossProjectIdentityRejected: false,
      tamperedCursorRejected: false
    };
    try {
      await window.docKnowledge.getProjectContinuity({
        projectPath: authoritativeFixture.projectPath,
        projectId: "project-intentionally-wrong",
        workingState: authoritativeFixture.workingState
      });
    } catch {
      negativeChecks.wrongProjectIdRejected = true;
    }
    try {
      await window.docKnowledge.getProjectContinuity({
        projectPath,
        projectId: authoritativeFixture.projectId
      });
    } catch {
      negativeChecks.crossProjectIdentityRejected = true;
    }
    if (firstSuccessCursor) {
      const last = firstSuccessCursor.slice(-1);
      const tamperedCursor = firstSuccessCursor.slice(0, -1) + (last === "A" ? "B" : "A");
      const tampered = await window.docKnowledge.getProjectContinuity({
        projectPath: authoritativeFixture.projectPath,
        projectId: authoritativeFixture.projectId,
        workingState: authoritativeFixture.workingState,
        cursor: tamperedCursor,
        tokenBudget: 2200,
        maxPacketItems: 4,
        maxPacketChars: 9000
      });
      negativeChecks.tamperedCursorRejected = tampered.recoveryReady !== true
        && tampered.mandatoryComplete !== true
        && tampered.continuityPacket?.mandatoryManifest?.cursorInvalid === true;
    }

    const operationStartedAt = new Date().toISOString();
    const checkpoint = await window.docKnowledge.observeMemoryRuntimeEvent({
      eventType: "task_checkpoint",
      severity: "info",
      projectPath,
      title: "CEO Flow Memory Core compatibility checkpoint",
      summary: "Project continuity pagination and role-bound memory contract were inspected.",
      decisions: ["Keep recovery claims evidence-backed."],
      nextAction: "Verify lifecycle trigger receipts.",
      sourceRefs: [{ kind: "project_doc", path: projectPath + "/docs/CEO_FLOW_HANDOFF.md" }]
    });
    const takeover = await window.docKnowledge.observeMemoryRuntimeEvent({
      eventType: "thread_takeover",
      severity: "info",
      projectPath,
      threadId: "old-ceo-thread-redacted",
      replacementThreadId: "new-ceo-thread-redacted",
      title: "CEO takeover recovery probe",
      summary: "A clean CEO lane takes ownership from an old lane.",
      nextAction: "Use exact ProjectBrain continuity and compact context.",
      sourceRefs: [{ kind: "project_doc", path: projectPath + "/docs/CEO_FLOW_HANDOFF.md" }]
    });
    const invalidation = await window.docKnowledge.observeMemoryRuntimeEvent({
      eventType: "broken_thread",
      severity: "warning",
      projectPath,
      threadId: "invalid-worker-thread-redacted",
      title: "Worker thread invalidation probe",
      summary: "A stale or broken worker reference must be recorded without stopping the Program Goal.",
      nextAction: "Use the thread locator or replace the bounded lane.",
      sourceRefs: [{ kind: "project_doc", path: projectPath + "/docs/CEO_FLOW_HANDOFF.md" }]
    });
    const ruleUpdate = await window.docKnowledge.observeMemoryRuntimeEvent({
      eventType: "user_rule_update",
      severity: "info",
      projectPath,
      title: "Durable user rule update probe",
      summary: "Project Continuity Gate remains event-triggered and must not alter CEO model or reasoning settings.",
      decisions: ["No heartbeat, polling, or every-turn recall."],
      nextAction: "Apply the rule at the next qualifying lifecycle event.",
      sourceRefs: [{ kind: "project_doc", path: projectPath + "/docs/RELEASE_NOTES.md" }]
    });
    const context = await window.docKnowledge.retrieveMemoryRuntimeContext({
      taskGoal: "Resume CEO Flow after takeover with exact project continuity",
      queryType: "project_resume",
      projectPath,
      parentCeoThreadId: "new-ceo-thread-redacted",
      tokenBudget: 1400,
      maxResults: 6
    });
    const precedent = await window.docKnowledge.retrieveMemoryRuntimePrecedent({
      taskType: "thread recovery and Memory Core compatibility",
      query: "Project Continuity Gate recoveryReady mandatory pagination trigger receipt",
      projectPath,
      parentCeoThreadId: "new-ceo-thread-redacted",
      tokenBudget: 900,
      maxResults: 5
    });
    const writeback = await window.docKnowledge.writebackMemoryRuntimeEvidence({
      decision: "accept",
      task: {
        id: "CEOFLOW-ZHIXIA-090-RECOVERY-PROBE",
        goal: "Verify CEO Flow compatibility with Zhixia 0.9.0 Memory Core",
        projectPath,
        parentCeoThreadId: "new-ceo-thread-redacted"
      },
      evidence: {
        summary: "Exact project continuity, bounded events, and lifecycle receipt checks completed in isolated userData.",
        sourceRefs: [
          { kind: "project_doc", path: projectPath + "/docs/CEO_FLOW_HANDOFF.md" },
          { kind: "project_doc", path: projectPath + "/docs/RELEASE_NOTES.md" }
        ]
      }
    });
    const operationEndedAt = new Date().toISOString();
    const receiptResult = await window.docKnowledge.listMemoryRuntimeTriggerReceipts({ projectPath, limit: 50 });
    const receipts = (receiptResult.receipts || []).filter((receipt) => !baselineReceiptIds.has(receipt.id));
    const hooks = receipts.map((receipt) => receipt.hook);
    const receiptEvidence = receipts.map((receipt) => ({
      hook: receipt.hook,
      projectId: receipt.projectId || null,
      projectPath: receipt.projectPath || null,
      partial: receipt.partial === true,
      sourceRefCount: Array.isArray(receipt.sourceRefs) ? receipt.sourceRefs.length : 0,
      status: receipt.status || null
    }));
    const sourceRefSignature = (ref) => [ref?.kind || "", normalizeComparablePath(ref?.path || ""), ref?.hash || ""].join("|");
    const verifyTriggerReceipt = (callResult, expected) => {
      const direct = callResult?.triggerReceipt || null;
      const persisted = direct?.id ? receipts.find((receipt) => receipt.id === direct.id) || null : null;
      const directRefs = (direct?.sourceRefs || []).map(sourceRefSignature).sort();
      const persistedRefs = (persisted?.sourceRefs || []).map(sourceRefSignature).sort();
      const checks = {
        directReceiptPresent: Boolean(direct?.id),
        persistedExactId: Boolean(direct?.id && persisted?.id === direct.id),
        hook: persisted?.hook === expected.hook,
        queryType: persisted?.queryType === expected.queryType,
        projectPath: normalizeComparablePath(persisted?.projectPath) === normalizeComparablePath(expected.projectPath),
        threadId: (persisted?.threadId || null) === (expected.threadId || null),
        operationWindow: Boolean(persisted?.createdAt && persisted.createdAt >= operationStartedAt && persisted.createdAt <= operationEndedAt),
        returnedCount: Number(persisted?.returnedCount) === Number(expected.returnedCount),
        tokenEstimate: Number(persisted?.tokenEstimate) === Number(expected.tokenEstimate),
        partial: Boolean(persisted?.partial) === Boolean(expected.partial),
        sourceRefs: JSON.stringify(persistedRefs) === JSON.stringify(directRefs) && persistedRefs.length === expected.sourceRefCount,
        excludedInitializationReceipt: Boolean(persisted?.id && !baselineReceiptIds.has(persisted.id))
      };
      return {
        id: direct?.id || null,
        verified: Object.values(checks).every(Boolean),
        checks,
        persisted: persisted ? {
          hook: persisted.hook,
          queryType: persisted.queryType,
          projectPath: persisted.projectPath,
          threadId: persisted.threadId,
          returnedCount: persisted.returnedCount,
          tokenEstimate: persisted.tokenEstimate,
          partial: persisted.partial,
          sourceRefCount: (persisted.sourceRefs || []).length,
          createdAt: persisted.createdAt
        } : null
      };
    };
    const receiptVerification = {
      retrieveContext: verifyTriggerReceipt(context, {
        hook: "retrieve_context",
        queryType: "project_resume",
        projectPath,
        threadId: "new-ceo-thread-redacted",
        returnedCount: (context.items || []).length,
        tokenEstimate: context.tokenEstimate || 0,
        partial: context.partial === true,
        sourceRefCount: (context.triggerReceipt?.sourceRefs || []).length
      }),
      retrievePrecedent: verifyTriggerReceipt(precedent, {
        hook: "retrieve_precedent",
        queryType: "retrieve_precedent",
        projectPath,
        threadId: "new-ceo-thread-redacted",
        returnedCount: (precedent.items || []).length,
        tokenEstimate: precedent.tokenEstimate || 0,
        partial: precedent.partial === true,
        sourceRefCount: (precedent.triggerReceipt?.sourceRefs || []).length
      }),
      writebackEvidence: verifyTriggerReceipt(writeback, {
        hook: "writeback_evidence",
        queryType: "memory_writeback",
        projectPath,
        threadId: "new-ceo-thread-redacted",
        returnedCount: writeback.memoryFactWriteback?.written || 0,
        tokenEstimate: 0,
        partial: writeback.status !== "queued",
        sourceRefCount: 2
      })
    };
    const strictReceiptsVerified = Object.values(receiptVerification).every((receipt) => receipt.verified);
    const writebackReceipt = writeback.triggerReceipt?.id
      ? receipts.find((receipt) => receipt.id === writeback.triggerReceipt.id) || null
      : null;
    return {
      schemaVersion: "ceoflow.zhixia_090_memory_core_compat_probe.v2",
      sourceProjectKind: "real_project_snapshot_plus_authoritative_14_slot_fixture",
      projectId,
      projectPathMatched: Boolean(projectId)
        && projectId === safetySeed.projectId
        && normalizeComparablePath(projectPath) === normalizedExpectedProjectPath
        && pages.every((page) => (
        page.projectId === safetySeed.projectId && normalizeComparablePath(page.projectPath) === normalizedExpectedProjectPath
      )),
      mandatorySlotCount: Array.isArray(status.mandatorySlots) ? status.mandatorySlots.length : 0,
      statusRecoveryReady: status.recoveryReady === true,
      statusUnsatisfiedSlots: status.unsatisfiedSlots || [],
      pages,
      pagesRead: pages.length,
      paginationComplete: Boolean(finalPage && finalPage.mandatoryComplete === true && !finalPage.nextCursor),
      mandatoryReturned,
      mandatoryTotal,
      finalRecoveryReady: Boolean(finalPage && finalPage.recoveryReady === true),
      finalMissing: finalPage?.missing || [],
      finalStale: finalPage?.stale || [],
      finalConflict: finalPage?.conflict || [],
      safetyScenario: {
        expectedProjectId: safetySeed.projectId,
        exactIdentityMatched: projectId === safetySeed.projectId && pages.every((page) => page.projectId === safetySeed.projectId),
        paginationComplete: Boolean(finalPage && finalPage.mandatoryComplete === true && !finalPage.nextCursor),
        failClosedVerified: Boolean(finalPage && finalPage.recoveryReady !== true && ((finalPage.missing || []).length > 0 || (finalPage.conflict || []).length > 0 || (finalPage.stale || []).length > 0))
      },
      authoritativeScenario: {
        expectedProjectId: authoritativeFixture.projectId,
        statusProjectId: successStatus.projectId || null,
        exactIdentityMatched: successStatus.projectId === authoritativeFixture.projectId
          && normalizeComparablePath(successStatus.projectPath) === normalizeComparablePath(authoritativeFixture.projectPath)
          && successPages.every((page) => page.projectId === authoritativeFixture.projectId
            && normalizeComparablePath(page.projectPath) === normalizeComparablePath(authoritativeFixture.projectPath)),
        mandatorySlotCount: Array.isArray(successStatus.mandatorySlots) ? successStatus.mandatorySlots.length : 0,
        filledSlotCount: Array.isArray(successStatus.filledSlots) ? successStatus.filledSlots.length : 0,
        filledSlots: successStatus.filledSlots || [],
        pages: successPages,
        pagesRead: successPages.length,
        firstPageRequiresContinuation: Boolean(successPages[0]?.nextCursor && successPages[0]?.recoveryReady !== true),
        paginationComplete: Boolean(successFinalPage && successFinalPage.mandatoryComplete === true && !successFinalPage.nextCursor),
        mandatoryReturned: successMandatoryReturned,
        mandatoryTotal: successMandatoryTotal,
        finalRecoveryReady: successFinalPage?.recoveryReady === true,
        statusRecoveryReady: successStatus.recoveryReady === true,
        finalMissing: successFinalPage?.missing || [],
        finalStale: successFinalPage?.stale || [],
        finalConflict: successFinalPage?.conflict || [],
        negativeChecks
      },
      context: {
        itemCount: (context.items || []).length,
        sourceRefCount: (context.sourceRefs || []).length,
        receiptHook: context.triggerReceipt?.hook || null,
        receiptPartial: context.triggerReceipt?.partial ?? null
      },
      precedent: {
        itemCount: (precedent.items || []).length,
        sourceRefCount: (precedent.sourceRefs || []).length,
        receiptHook: precedent.triggerReceipt?.hook || null,
        receiptPartial: precedent.triggerReceipt?.partial ?? null
      },
      writeback: {
        status: writeback.status || null,
        sourceRefCount: Array.isArray(writebackReceipt?.sourceRefs) ? writebackReceipt.sourceRefs.length : 0,
        receiptHook: writeback.triggerReceipt?.hook || null,
        receiptPartial: writeback.triggerReceipt?.partial ?? null
      },
      eventReceipts: {
        checkpointStatus: checkpoint.status || null,
        takeoverStatus: takeover.status || null,
        invalidationStatus: invalidation.status || null,
        userRuleUpdateStatus: ruleUpdate.status || null
      },
      triggerReceiptCount: receipts.length,
      triggerHooks: hooks,
      triggerReceipts: receiptEvidence,
      receiptVerification,
      requiredHooksVerified: strictReceiptsVerified,
      requiredEventsRecorded: [checkpoint, takeover, invalidation, ruleUpdate].every((receipt) => receipt.status === "recorded"),
      initialization: {
        importedCount: initialization.importedCount,
        triggerHooks: initialization.memoryRuntime?.triggerHooks || []
      }
    };
  })()`;

  return new Promise((resolve, reject) => {
    const child = spawn(electronExe, [
      zhixiaRoot,
      `--user-data-dir=${userData}`,
      "--disable-gpu",
      "--disable-dev-shm-usage",
      "--no-sandbox",
      "--ozone-platform=headless",
    ], {
      cwd: zhixiaRoot,
      env: {
        ...process.env,
        CODEX_HOME: codexHome,
        ELECTRON_DISABLE_GPU: "1",
        ELECTRON_ENABLE_LOGGING: "1",
        ZHIXIA_E2E_PROBE: "1",
        ZHIXIA_E2E_PROJECT_PATH: projectPath,
        ZHIXIA_E2E_RENDERER_SCRIPT: probeScript,
      },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });

    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error(`Recovery probe timed out.\nstdout:\n${stdout}\nstderr:\n${stderr}`));
    }, 60000);

    child.stdout.on("data", (chunk) => { stdout += chunk.toString(); });
    child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("exit", (code) => {
      clearTimeout(timer);
      const matches = [...stdout.matchAll(/ZHIXIA_E2E_RESULT (.+)/g)];
      if (!matches.length) {
        reject(new Error(`Recovery probe returned no JSON. Exit ${code}.\nstdout:\n${stdout}\nstderr:\n${stderr}`));
        return;
      }
      try {
        resolve(JSON.parse(matches.at(-1)[1]));
      } catch (error) {
        reject(new Error(`Recovery probe returned invalid JSON: ${error.message}`));
      }
    });
  });
}

(async () => {
  try {
    copyRequiredSnapshot();
    const safetySeed = seedRealProjectSnapshot();
    const authoritativeFixture = createAuthoritative14SlotFixture();
    const result = await runProbe(safetySeed, authoritativeFixture);
    const compatibilityPassed = result.safetyScenario.exactIdentityMatched
      && result.safetyScenario.paginationComplete
      && result.safetyScenario.failClosedVerified
      && result.authoritativeScenario.exactIdentityMatched
      && result.authoritativeScenario.mandatorySlotCount === 14
      && result.authoritativeScenario.filledSlotCount === 14
      && result.authoritativeScenario.pagesRead >= 2
      && result.authoritativeScenario.firstPageRequiresContinuation
      && result.authoritativeScenario.paginationComplete
      && result.authoritativeScenario.mandatoryReturned === result.authoritativeScenario.mandatoryTotal
      && result.authoritativeScenario.mandatoryTotal > 4
      && result.authoritativeScenario.finalRecoveryReady
      && result.authoritativeScenario.statusRecoveryReady
      && result.authoritativeScenario.finalMissing.length === 0
      && result.authoritativeScenario.finalStale.length === 0
      && result.authoritativeScenario.finalConflict.length === 0
      && Object.values(result.authoritativeScenario.negativeChecks).every(Boolean)
      && result.requiredHooksVerified
      && result.requiredEventsRecorded
      && result.writeback.sourceRefCount === 2;
    process.stdout.write(`${JSON.stringify({
      ...result,
      safetySeed,
      authoritativeFixture: {
        projectPath: authoritativeFixture.projectPath,
        projectId: authoritativeFixture.projectId,
        moduleId: authoritativeFixture.moduleId,
        anchorCount: authoritativeFixture.anchorCount,
        moduleCount: authoritativeFixture.moduleCount,
        checkpointReceiptId: authoritativeFixture.checkpointReceiptId,
        seedWriteActions: authoritativeFixture.seedWriteActions
      },
      compatibilityPassed
    }, null, 2)}\n`);
    if (!compatibilityPassed) process.exitCode = 2;
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 });
  }
})().catch((error) => {
  console.error(error.stack || error.message || String(error));
  try { fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 }); } catch {}
  process.exit(1);
});
