"use strict";
// src/commands/index.ts — all VS Code command handlers  v0.5.0
//
// Commands đăng ký trong extension.ts:
//   ascet.refresh           — refresh class tree
//   ascet.selectAndChat     — chọn class → mở chat
//   ascet.analyzeSelected   — analyze class đang chọn
//   ascet.askCopilot        — mở chat panel
//   ascet.openLog           — mở output channel
//   ascet.exportDsd         — xuất Excel DSD
//   ascet.runAiReview       — full AI review pipeline
//   ascet.addToQueue        — thêm class vào scan queue   🆕
//   ascet.showQueue         — hiển thị scan queue         🆕
//   ascet.clearQueue        — xóa items đã xong           🆕
//   ascet.showDiagram       — hiển thị diagram trong panel 🆕
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.injectTreeProvider = injectTreeProvider;
exports.cmdRefresh = cmdRefresh;
exports.cmdSelectAndChat = cmdSelectAndChat;
exports.cmdAnalyzeSelected = cmdAnalyzeSelected;
exports.cmdAskCopilot = cmdAskCopilot;
exports.cmdOpenLog = cmdOpenLog;
exports.cmdExportDsd = cmdExportDsd;
exports.cmdRunAiReview = cmdRunAiReview;
exports.cmdAddToQueue = cmdAddToQueue;
exports.cmdShowQueue = cmdShowQueue;
exports.cmdClearQueue = cmdClearQueue;
exports.cmdShowDiagram = cmdShowDiagram;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const runner_1 = require("../cli/runner");
const state_1 = require("../state");
const statusBar_1 = require("../ui/statusBar");
const logger_1 = require("../ui/logger");
const scanQueue_1 = require("../queue/scanQueue");
// Injected from activate()
let _treeProvider;
function injectTreeProvider(p) {
    _treeProvider = p;
}
// ── Helper: pick class from tree or input box ─────────────────────────────────
async function pickClassPath(preselected) {
    if (preselected)
        return preselected;
    // Quick pick từ danh sách class
    const result = await (0, runner_1.runCli)("list_classes", []);
    if (!result.success || !result.data) {
        vscode.window.showErrorMessage("Cannot load class list: " + result.error);
        return undefined;
    }
    return vscode.window.showQuickPick(result.data, {
        placeHolder: "Select ASCET class…",
        matchOnDetail: true,
    });
}
// ── ascet.refresh ─────────────────────────────────────────────────────────────
async function cmdRefresh() {
    (0, logger_1.logInfo)("Refreshing class tree…");
    (0, statusBar_1.setStatus)("$(sync~spin) Refreshing…");
    try {
        await _treeProvider?.refresh();
        (0, logger_1.logInfo)("Tree refreshed.");
    }
    finally {
        (0, statusBar_1.clearStatus)();
    }
}
// ── ascet.selectAndChat ───────────────────────────────────────────────────────
async function cmdSelectAndChat(node) {
    const class_path = await pickClassPath(node?.path);
    if (!class_path)
        return;
    // Store selection và mở chat
    await vscode.commands.executeCommand("workbench.panel.chat.view.copilot.focus");
    // Pre-fill với @ascet /analyze <path>
    await vscode.commands.executeCommand("workbench.action.chat.open", {
        query: `@ascet /analyze ${class_path}`,
    });
}
// ── ascet.analyzeSelected ─────────────────────────────────────────────────────
async function cmdAnalyzeSelected(node) {
    const class_path = await pickClassPath(node?.path);
    if (!class_path)
        return;
    (0, statusBar_1.setStatus)(`$(beaker~spin) Analyzing ${class_path}…`);
    (0, logger_1.logInfo)(`Analyzing: ${class_path}`);
    try {
        const result = await (0, runner_1.runCli)("ai_review", [
            class_path,
            "--mode", "severity",
        ]);
        if (!result.success || !result.data) {
            vscode.window.showErrorMessage(`Analysis failed: ${result.error}`);
            (0, logger_1.logError)(`Analysis failed: ${result.error}\n${result.detail}`);
            return;
        }
        _showReviewPanel(class_path, result.data);
        (0, logger_1.logInfo)(`Analysis done: ${result.data.summary}`);
    }
    finally {
        (0, statusBar_1.clearStatus)();
    }
}
// ── ascet.askCopilot ──────────────────────────────────────────────────────────
async function cmdAskCopilot() {
    await vscode.commands.executeCommand("workbench.panel.chat.view.copilot.focus");
}
// ── ascet.openLog ─────────────────────────────────────────────────────────────
function cmdOpenLog() {
    (0, state_1.getLog)().show(true);
}
// ── ascet.exportDsd ───────────────────────────────────────────────────────────
async function cmdExportDsd(node) {
    // Chọn output folder
    const folderUri = await vscode.window.showOpenDialog({
        canSelectFolders: true,
        canSelectFiles: false,
        openLabel: "Select output folder",
    });
    if (!folderUri || folderUri.length === 0)
        return;
    const outputDir = folderUri[0].fsPath;
    const cliArgs = ["--output_dir", outputDir];
    // Nếu có node được chọn → export 1 class
    if (node?.path) {
        cliArgs.push("--class_path", node.path);
        (0, logger_1.logInfo)(`Exporting DSD for: ${node.path}`);
    }
    else {
        // Hỏi user có muốn export all không
        const choice = await vscode.window.showQuickPick(["Export selected class", "Export all classes"], { placeHolder: "DSD Export scope" });
        if (!choice)
            return;
        if (choice === "Export selected class") {
            const class_path = await pickClassPath();
            if (!class_path)
                return;
            cliArgs.push("--class_path", class_path);
            (0, logger_1.logInfo)(`Exporting DSD for: ${class_path}`);
        }
        else {
            (0, logger_1.logInfo)("Exporting DSD for all classes…");
        }
    }
    (0, statusBar_1.setStatus)("$(file-excel~spin) Exporting DSD…");
    try {
        const result = await (0, runner_1.runCli)("export_dsd", cliArgs);
        if (!result.success || !result.data) {
            vscode.window.showErrorMessage(`DSD export failed: ${result.error}`);
            (0, logger_1.logError)(`DSD export failed: ${result.error}`);
            return;
        }
        const outFile = result.data.output_file;
        (0, logger_1.logInfo)(`DSD exported: ${outFile}`);
        const action = await vscode.window.showInformationMessage(`DSD exported: ${path.basename(outFile)}`, "Open File", "Open Folder");
        if (action === "Open File") {
            vscode.env.openExternal(vscode.Uri.file(outFile));
        }
        else if (action === "Open Folder") {
            vscode.env.openExternal(vscode.Uri.file(path.dirname(outFile)));
        }
    }
    finally {
        (0, statusBar_1.clearStatus)();
    }
}
// ── ascet.runAiReview ─────────────────────────────────────────────────────────
async function cmdRunAiReview(node) {
    const class_path = await pickClassPath(node?.path);
    if (!class_path)
        return;
    // Chọn mode
    const mode = await vscode.window.showQuickPick([
        { label: "$(shield) Severity-based", value: "severity", description: "Recommended" },
        { label: "$(lock) Conservative", value: "conservative", description: "Both models must agree" },
        { label: "$(people) Majority", value: "majority", description: "Majority vote" },
    ], { placeHolder: "Select arbitration mode" });
    if (!mode)
        return;
    const useRag = await vscode.window.showQuickPick(["Yes — use RAG knowledge base", "No — skip RAG (faster)"], { placeHolder: "Enable RAG?" });
    if (!useRag)
        return;
    const cliArgs = [
        class_path,
        "--mode", mode.value,
        ...(useRag.startsWith("No") ? ["--no_rag"] : []),
    ];
    (0, statusBar_1.setStatus)(`$(beaker~spin) AI Review: ${class_path}…`);
    (0, logger_1.logInfo)(`AI Review started: ${class_path} [mode=${mode.value}]`);
    try {
        const result = await (0, runner_1.runCli)("ai_review", cliArgs);
        if (!result.success || !result.data) {
            vscode.window.showErrorMessage(`AI Review failed: ${result.error}`);
            (0, logger_1.logError)(`AI Review failed: ${result.error}\n${result.detail}`);
            return;
        }
        _showReviewPanel(class_path, result.data);
        (0, logger_1.logInfo)(`AI Review done: ${result.data.summary}`);
    }
    finally {
        (0, statusBar_1.clearStatus)();
    }
}
// ── ascet.addToQueue (🆕) ─────────────────────────────────────────────────────
async function cmdAddToQueue(node) {
    const class_path = await pickClassPath(node?.path);
    if (!class_path)
        return;
    const queue = (0, scanQueue_1.getScanQueue)();
    queue.enqueue(class_path);
    (0, logger_1.logInfo)(`Added to queue: ${class_path}`);
    vscode.window.showInformationMessage(`Added to scan queue: ${class_path}`, "Show Queue").then((action) => {
        if (action === "Show Queue")
            cmdShowQueue();
    });
}
// ── ascet.showQueue (🆕) ──────────────────────────────────────────────────────
async function cmdShowQueue() {
    const queue = (0, scanQueue_1.getScanQueue)();
    const items = queue.items;
    if (items.length === 0) {
        vscode.window.showInformationMessage("Scan queue is empty.");
        return;
    }
    // Hiển thị trong WebviewPanel
    const panel = vscode.window.createWebviewPanel("ascetQueue", "ASCET Scan Queue", vscode.ViewColumn.Two, { enableScripts: true });
    panel.webview.html = _buildQueueHtml(items);
    // Auto-refresh khi queue thay đổi
    const sub = queue.onDidChange((updated) => {
        if (!panel.visible)
            return;
        panel.webview.html = _buildQueueHtml(updated);
    });
    panel.onDidDispose(() => sub.dispose());
}
// ── ascet.clearQueue (🆕) ─────────────────────────────────────────────────────
function cmdClearQueue() {
    (0, scanQueue_1.getScanQueue)().clearFinished();
    (0, logger_1.logInfo)("Cleared finished queue items.");
}
// ── ascet.showDiagram (🆕) ────────────────────────────────────────────────────
async function cmdShowDiagram(node) {
    const class_path = await pickClassPath(node?.path);
    if (!class_path)
        return;
    (0, statusBar_1.setStatus)(`$(symbol-class~spin) Loading diagram…`);
    (0, logger_1.logInfo)(`Loading diagram: ${class_path}`);
    try {
        // Lấy SVG render + Mermaid logic song song
        const [renderResult, logicResult] = await Promise.all([
            (0, runner_1.runCli)("render_diagram", [class_path, "--format", "svg"]),
            (0, runner_1.runCli)("get_diagram_logic", [class_path]),
        ]);
        if (!renderResult.success || !renderResult.data) {
            vscode.window.showErrorMessage(`Diagram render failed: ${renderResult.error}`);
            return;
        }
        const panel = vscode.window.createWebviewPanel("ascetDiagram", `Diagram: ${class_path}`, vscode.ViewColumn.Two, { enableScripts: true });
        const mermaid = logicResult.success ? logicResult.data?.mermaid ?? "" : "";
        panel.webview.html = _buildDiagramHtml(class_path, renderResult.data.content, mermaid);
        (0, logger_1.logInfo)(`Diagram loaded: ${class_path}`);
    }
    finally {
        (0, statusBar_1.clearStatus)();
    }
}
// ═══════════════════════════════════════════════════════════════════════════════
// WebView HTML builders
// ═══════════════════════════════════════════════════════════════════════════════
function _showReviewPanel(class_path, data) {
    const panel = vscode.window.createWebviewPanel("ascetReview", `AI Review: ${class_path}`, vscode.ViewColumn.Two, { enableScripts: false });
    panel.webview.html = _buildReviewHtml(class_path, data);
}
function _buildReviewHtml(class_path, d) {
    const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const issueRows = (issues, label) => issues.length === 0
        ? `<p style="color:#888">No ${label}</p>`
        : `<table class="issue-table">
          <tr><th>Severity</th><th>Message</th><th>Location</th></tr>
          ${issues.map((i) => `<tr class="${i.severity}">
              <td>${esc(i.severity ?? "")}</td>
              <td>${esc(i.message ?? "")}</td>
              <td>${esc(i.location ?? i.line?.toString() ?? "")}</td>
            </tr>`).join("")}
        </table>`;
    return `<!DOCTYPE html><html><head><meta charset="UTF-8">
  <style>
    body { font-family: var(--vscode-font-family); padding: 16px; }
    h1 { font-size: 1.2em; }
    h2 { font-size: 1em; margin-top: 20px; border-bottom: 1px solid #444; }
    .summary { background: #1e1e1e; padding: 8px 12px; border-radius: 4px;
               font-family: monospace; margin-bottom: 16px; }
    .issue-table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
    .issue-table th { text-align: left; padding: 4px 8px; background: #2d2d2d; }
    .issue-table td { padding: 4px 8px; border-bottom: 1px solid #333; }
    .error td:first-child { color: #f44; }
    .warning td:first-child { color: #fa0; }
    .info td:first-child { color: #4af; }
    .stat { display: inline-block; margin-right: 16px; font-size: 0.85em;
            color: #888; }
  </style></head><body>
  <h1>🔍 AI Review: ${esc(class_path)}</h1>
  <div class="summary">${esc(d.summary)}</div>
  <span class="stat">Tokens: ${d.tokens_used}</span>
  <span class="stat">Cost: $${d.cost_usd.toFixed(4)}</span>
  <span class="stat">RAG hits: ${d.rag_hits.length}</span>

  <h2>Rule Issues (${d.rule_issues.length})</h2>
  ${issueRows(d.rule_issues, "rule issues")}

  <h2>AI Errors (${d.ai_errors.length})</h2>
  ${issueRows(d.ai_errors, "AI errors")}

  <h2>AI Warnings (${d.ai_warnings.length})</h2>
  ${issueRows(d.ai_warnings, "AI warnings")}

  <h2>RAG Knowledge Hits (${d.rag_hits.length})</h2>
  ${d.rag_hits.length === 0
        ? '<p style="color:#888">No RAG hits</p>'
        : `<ul>${d.rag_hits.map((h) => `<li><b>${esc(h.pattern)}</b> (sim: ${h.similarity.toFixed(2)}) — ${esc(h.description)}</li>`).join("")}</ul>`}
  </body></html>`;
}
function _buildQueueHtml(items) {
    const statusIcon = (s) => ({ pending: "⏳", running: "🔄", done: "✅", error: "❌" }[s] ?? "?");
    return `<!DOCTYPE html><html><head><meta charset="UTF-8">
  <style>
    body { font-family: var(--vscode-font-family); padding: 16px; }
    table { width: 100%; border-collapse: collapse; }
    th { text-align: left; padding: 6px 10px; background: #2d2d2d; }
    td { padding: 6px 10px; border-bottom: 1px solid #333; font-size: 0.9em; }
    .done td { color: #4c4; }
    .error td { color: #f44; }
    .running td { color: #fa0; }
  </style></head><body>
  <h2>ASCET Scan Queue (${items.length} items)</h2>
  <table>
    <tr><th>Status</th><th>Class</th><th>Summary</th><th>Added</th></tr>
    ${items.map((i) => `
      <tr class="${i.status}">
        <td>${statusIcon(i.status)} ${i.status}</td>
        <td>${i.class_path}</td>
        <td>${i.result?.summary ?? i.error ?? "—"}</td>
        <td>${new Date(i.addedAt).toLocaleTimeString()}</td>
      </tr>`).join("")}
  </table>
  </body></html>`;
}
function _buildDiagramHtml(class_path, svg, mermaid) {
    return `<!DOCTYPE html><html><head><meta charset="UTF-8">
  <style>
    body { font-family: var(--vscode-font-family); padding: 16px; }
    .tabs { display: flex; gap: 8px; margin-bottom: 12px; }
    .tab { cursor: pointer; padding: 4px 12px; border-radius: 4px;
           background: #2d2d2d; border: none; color: inherit; }
    .tab.active { background: #0078d4; }
    .panel { display: none; }
    .panel.active { display: block; }
    pre { background: #1e1e1e; padding: 12px; border-radius: 4px;
          overflow: auto; font-size: 0.85em; }
    svg { max-width: 100%; height: auto; }
  </style></head><body>
  <h2>Block Diagram: ${class_path}</h2>
  <div class="tabs">
    <button class="tab active" onclick="show('svg-panel',this)">SVG Diagram</button>
    <button class="tab" onclick="show('mermaid-panel',this)">Mermaid Logic</button>
  </div>
  <div id="svg-panel" class="panel active">${svg}</div>
  <div id="mermaid-panel" class="panel"><pre>${mermaid}</pre></div>
  <script>
    function show(id, btn) {
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
      document.getElementById(id).classList.add('active');
      btn.classList.add('active');
    }
  </script>
  </body></html>`;
}
//# sourceMappingURL=index.js.map