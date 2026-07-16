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

function runProbe() {
  const projectJson = JSON.stringify(projectPath);
  const normalizedProjectJson = JSON.stringify(normalizeComparablePath(projectPath));
  const probeScript = `(async () => {
    const projectPath = ${projectJson};
    const normalizedExpectedProjectPath = ${normalizedProjectJson};
    const normalizeComparablePath = (value) => String(value || "")
      .replace(/\\\\/g, "/")
      .replace(/\\/+$/, "")
      .toLowerCase();
    const startedAt = new Date().toISOString();
    const initialization = await window.docKnowledge.e2eProbe({ projectPath });
    const status = await window.docKnowledge.getMemoryCoreContinuityStatus({
      projectPath,
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
        projectId,
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
    const receiptResult = await window.docKnowledge.listMemoryRuntimeTriggerReceipts({ projectPath, limit: 50 });
    const receipts = (receiptResult.receipts || []).filter((receipt) => receipt.createdAt >= startedAt);
    const hooks = receipts.map((receipt) => receipt.hook);
    const receiptEvidence = receipts.map((receipt) => ({
      hook: receipt.hook,
      projectId: receipt.projectId || null,
      projectPath: receipt.projectPath || null,
      partial: receipt.partial === true,
      sourceRefCount: Array.isArray(receipt.sourceRefs) ? receipt.sourceRefs.length : 0,
      status: receipt.status || null
    }));
    const writebackReceipt = receipts.find((receipt) => receipt.hook === "writeback_evidence") || null;
    return {
      schemaVersion: "ceoflow.zhixia_090_real_recovery_probe.v1",
      sourceProjectKind: "real_project_snapshot",
      projectId,
      projectPathMatched: Boolean(projectId) && pages.every((page) => (
        page.projectId === projectId && normalizeComparablePath(page.projectPath) === normalizedExpectedProjectPath
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
      requiredHooksVerified: ["retrieve_context", "retrieve_precedent", "writeback_evidence"].every((hook) => hooks.includes(hook)),
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
    const seed = seedRealProjectSnapshot();
    const result = await runProbe();
    const compatibilityPassed = result.projectPathMatched
      && result.mandatorySlotCount === 14
      && result.paginationComplete
      && result.mandatoryReturned === result.mandatoryTotal
      && result.requiredHooksVerified
      && result.requiredEventsRecorded
      && result.writeback.sourceRefCount > 0
      && (result.finalRecoveryReady || result.finalMissing.length > 0 || result.finalConflict.length > 0 || result.finalStale.length > 0);
    process.stdout.write(`${JSON.stringify({ ...result, seed, compatibilityPassed }, null, 2)}\n`);
    if (!compatibilityPassed) process.exitCode = 2;
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 });
  }
})().catch((error) => {
  console.error(error.stack || error.message || String(error));
  try { fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 }); } catch {}
  process.exit(1);
});
