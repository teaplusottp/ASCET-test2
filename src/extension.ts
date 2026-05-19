// src/extension.ts — ASCET Copilot VS Code Extension  v0.6.0
// ============================================================
// Entry point: khởi tạo state, đăng ký providers, commands, participant.

import * as vscode from "vscode";
import * as os from "os";
import * as path from "path";
import { initState } from "./state";
import { AscetClassTreeProvider } from "./tree/provider";
import { registerParticipant } from "./chat/participant";
import { getScanQueue } from "./queue/scanQueue";
import { logInfo } from "./ui/logger";
import { runAscetCli } from "./cli/runner";
import type {
  DiagramRenderResult,
  AiReviewResult,
  DsdExportResult,
} from "./cli/types";

// ── Lazy tree provider reference ──────────────────────────────────────────────
let _treeProvider: AscetClassTreeProvider | undefined;
function getTreeProvider(): AscetClassTreeProvider {
  if (!_treeProvider) { throw new Error("Tree provider not initialised."); }
  return _treeProvider;
}

// ── Diagram webview cache ─────────────────────────────────────────────────────
let _diagramPanel: vscode.WebviewPanel | undefined;

export function activate(context: vscode.ExtensionContext): void {
  // ── 1. Init shared state ──────────────────────────────────────────────────
  initState(context);
  logInfo("ASCET Copilot v0.6.0 activating…");

  // ── 2. Tree provider ──────────────────────────────────────────────────────
  _treeProvider = new AscetClassTreeProvider();

  const treeView = vscode.window.createTreeView("ascetClassTree", {
    treeDataProvider: _treeProvider,
    showCollapseAll: true,
    canSelectMany: true,
  });

  // ── 3. Commands ───────────────────────────────────────────────────────────
  const cmds: [string, (...args: any[]) => any][] = [
    ["ascet.refresh",         _cmdRefresh],
    ["ascet.selectAndChat",   _cmdSelectAndChat],
    ["ascet.analyzeSelected", _cmdAnalyzeSelected],
    ["ascet.askCopilot",      _cmdAskCopilot],
    ["ascet.openLog",         _cmdOpenLog],
    ["ascet.exportDsd",       _cmdExportDsd],
    ["ascet.runAiReview",     _cmdRunAiReview],
    ["ascet.addToQueue",      _cmdAddToQueue],
    ["ascet.showQueue",       _cmdShowQueue],
    ["ascet.clearQueue",      _cmdClearQueue],
    ["ascet.showDiagram",     _cmdShowDiagram],
  ];

  for (const [id, handler] of cmds) {
    context.subscriptions.push(
      vscode.commands.registerCommand(id, handler)
    );
  }

  // ── 4. Chat participant (@ascet) ──────────────────────────────────────────
  context.subscriptions.push(registerParticipant(context));

  // ── 5. Status bar — queue badge ───────────────────────────────────────────
  const queueBadge = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    99
  );
  queueBadge.command = "ascet.showQueue";
  queueBadge.tooltip = "ASCET Scan Queue";

  const queue = getScanQueue();
  const _updateBadge = () => {
    const pending = queue.pendingCount;
    const running = queue.isRunning;
    if (pending === 0 && !running) {
      queueBadge.hide();
    } else {
      queueBadge.text = running
        ? `$(sync~spin) ASCET Queue: ${pending} pending`
        : `$(clock) ASCET Queue: ${pending} pending`;
      queueBadge.show();
    }
  };
  queue.onDidChange(_updateBadge);
  context.subscriptions.push(queueBadge);

  // ── 6. Tree view — multi-select → add to queue ────────────────────────────
  context.subscriptions.push(
    treeView.onDidChangeSelection((e) => {
      if (e.selection.length > 1) {
        vscode.window
          .showInformationMessage(
            `Add ${e.selection.length} classes to scan queue?`,
            "Add to Queue",
            "Cancel"
          )
          .then((action) => {
            if (action === "Add to Queue") {
              const paths = e.selection
                .filter((n) => n.contextValue === "ascetClass")
                .map(
                  (n) => n.resourceUri?.path ?? (n as any).classpath ?? ""
                )
                .filter(Boolean);
              if (paths.length > 0) {
                queue.enqueueMany(paths);
                logInfo(`Queued ${paths.length} classes.`);
                vscode.window
                  .showInformationMessage(
                    `${paths.length} classes added to scan queue.`,
                    "Show Queue"
                  )
                  .then((a) => {
                    if (a === "Show Queue") { _cmdShowQueue(); }
                  });
              }
            }
          });
      }
    })
  );

  context.subscriptions.push(treeView);
  logInfo("ASCET Copilot activated ✅");
}

export function deactivate(): void {
  logInfo("ASCET Copilot deactivated.");
}

// ── Command implementations ───────────────────────────────────────────────────

async function _cmdRefresh(): Promise<void> {
  await getTreeProvider().refresh();
}

async function _cmdSelectAndChat(): Promise<void> {
  const classList = getTreeProvider().getClassList();
  if (classList.length === 0) {
    vscode.window.showWarningMessage(
      "No ASCET classes loaded. Run Refresh first."
    );
    return;
  }

  const picked = await vscode.window.showQuickPick(classList, {
    placeHolder: "Select ASCET class to analyze…",
    matchOnDescription: true,
  });
  if (!picked) { return; }

  // Open GitHub Copilot chat with the class path pre-filled
  await vscode.commands.executeCommand("workbench.action.chat.open", {
    query: `@ascet /analyze ${picked}`,
  });
}

async function _cmdAnalyzeSelected(classpath?: string): Promise<void> {
  const cp = classpath ?? (await _pickClass());
  if (!cp) { return; }

  await vscode.commands.executeCommand("workbench.action.chat.open", {
    query: `@ascet /analyze ${cp}`,
  });
}

async function _cmdAskCopilot(): Promise<void> {
  await vscode.commands.executeCommand("workbench.action.chat.open", {
    query: "@ascet ",
  });
}

function _cmdOpenLog(): void {
  vscode.commands.executeCommand("workbench.action.focusPanel");
  const { showLog } = require("./ui/logger");
  showLog();
}

async function _cmdExportDsd(arg?: { path?: string }): Promise<void> {
  const outputDir = path.join(os.tmpdir(), "ascet_dsd");
  const cliArgs: string[] = ["--output_dir", outputDir];
  let label = "all classes";

  if (arg?.path) {
    cliArgs.push("--class_path", arg.path);
    label = arg.path;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: `Exporting DSD for ${label}…`,
      cancellable: false,
    },
    async () => {
      const result = await runAscetCli<DsdExportResult>("export_dsd", cliArgs);
      if (!result.success || !result.data) {
        vscode.window.showErrorMessage(`DSD export failed: ${result.error}`);
        return;
      }
      const outFile = result.data.output_file;
      const open = await vscode.window.showInformationMessage(
        `DSD exported: ${outFile}`,
        "Open"
      );
      if (open) {
        await vscode.commands.executeCommand(
          "vscode.open",
          vscode.Uri.file(outFile)
        );
      }
    }
  );
}

async function _cmdRunAiReview(arg?: { path?: string }): Promise<void> {
  const cp = arg?.path ?? (await _pickClass());
  if (!cp) { return; }

  await vscode.commands.executeCommand("workbench.action.chat.open", {
    query: `@ascet /ai severity ${cp}`,
  });
}

async function _cmdAddToQueue(arg?: { path?: string }): Promise<void> {
  const cp = arg?.path ?? (await _pickClass());
  if (!cp) { return; }

  const queue = getScanQueue();
  queue.enqueue(cp);
  logInfo(`Added to queue: ${cp}`);

  const action = await vscode.window.showInformationMessage(
    `Added \`${cp}\` to scan queue.`,
    "Show Queue"
  );
  if (action === "Show Queue") { _cmdShowQueue(); }
}

function _cmdShowQueue(): void {
  const queue = getScanQueue();
  const items = queue.items;

  if (items.length === 0) {
    vscode.window.showInformationMessage("Scan queue is empty.");
    return;
  }

  // Show as QuickPick with status
  const qpItems = items.map((item) => {
    const icon =
      item.status === "done"
        ? "✅"
        : item.status === "error"
        ? "❌"
        : item.status === "running"
        ? "🔄"
        : "⏳";
    const name = item.class_path.split("\\").pop() ?? item.class_path;
    const detail =
      item.status === "done"
        ? item.result?.summary ?? "Done"
        : item.status === "error"
        ? item.error ?? "Error"
        : item.status === "running"
        ? "Scanning…"
        : `Added ${item.addedAt.toLocaleTimeString()}`;

    return {
      label: `${icon} ${name}`,
      description: item.class_path,
      detail,
      id: item.id,
      status: item.status,
    };
  });

  vscode.window.showQuickPick(qpItems, {
    placeHolder: `Scan Queue — ${queue.pendingCount} pending${queue.isRunning ? ", 1 running" : ""}`,
    title: "ASCET Scan Queue",
    canPickMany: false,
  }).then((picked) => {
    if (!picked) { return; }
    if (picked.status === "done") {
      // Open Copilot chat with result
      vscode.commands.executeCommand("workbench.action.chat.open", {
        query: `@ascet /ai ${picked.description}`,
      });
    }
  });
}

async function _cmdClearQueue(): Promise<void> {
  const queue = getScanQueue();
  const choice = await vscode.window.showQuickPick(
    ["Clear finished items", "Clear all (keep running)", "Cancel"],
    { placeHolder: "Clear queue…" }
  );
  if (!choice || choice === "Cancel") { return; }
  if (choice === "Clear finished items") {
    queue.clearFinished();
    logInfo("Cleared finished queue items.");
  } else {
    queue.clearAll();
    logInfo("Cleared all queue items.");
  }
}

async function _cmdShowDiagram(
  arg?: { path?: string } | string
): Promise<void> {
  const class_path =
    typeof arg === "string" ? arg : arg?.path ?? (await _pickClass());
  if (!class_path) { return; }

  // Fetch SVG từ CLI
  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: `Loading diagram for ${class_path.split("\\").pop()}…`,
      cancellable: false,
    },
    async () => {
      const result = await runAscetCli<DiagramRenderResult>(
        "render_diagram",
        ["--path", class_path, "--format", "svg"]
      );

      if (!result.success || !result.data) {
        vscode.window.showErrorMessage(`Diagram failed: ${result.error}`);
        return;
      }

      const svgContent = result.data.content;
      const className = class_path.split("\\").pop() ?? class_path;

      // Tái sử dụng panel nếu đang mở
      if (_diagramPanel) {
        _diagramPanel.title = `Diagram: ${className}`;
        _diagramPanel.webview.html = _buildDiagramHtml(
          className,
          class_path,
          svgContent
        );
        _diagramPanel.reveal(vscode.ViewColumn.Beside);
        return;
      }

      _diagramPanel = vscode.window.createWebviewPanel(
        "ascetDiagram",
        `Diagram: ${className}`,
        vscode.ViewColumn.Beside,
        { enableScripts: true, retainContextWhenHidden: true }
      );
      _diagramPanel.webview.html = _buildDiagramHtml(
        className,
        class_path,
        svgContent
      );
      _diagramPanel.onDidDispose(() => { _diagramPanel = undefined; });
    }
  );
}

// ── Helper: QuickPick class selector ─────────────────────────────────────────
async function _pickClass(): Promise<string | undefined> {
  const classList = getTreeProvider().getClassList();
  if (classList.length === 0) {
    const refresh = await vscode.window.showWarningMessage(
      "No ASCET classes loaded.",
      "Refresh Tree"
    );
    if (refresh) { await getTreeProvider().refresh(); }
    return undefined;
  }
  return vscode.window.showQuickPick(classList, {
    placeHolder: "Select ASCET class…",
  });
}

// ── Helper: Diagram WebView HTML ──────────────────────────────────────────────
function _buildDiagramHtml(
  className: string,
  classPath: string,
  svgContent: string
): string {
  return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ASCET Diagram — ${className}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--vscode-editor-background);
      color: var(--vscode-editor-foreground);
      font-family: var(--vscode-font-family);
      display: flex; flex-direction: column; height: 100vh; overflow: hidden;
    }
    header {
      padding: 8px 12px;
      background: var(--vscode-sideBar-background);
      border-bottom: 1px solid var(--vscode-panel-border);
      display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
    }
    header h2 { font-size: 13px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    header small { font-size: 11px; opacity: 0.6; }
    .controls { display: flex; gap: 6px; }
    button {
      background: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
      border: none; border-radius: 3px; padding: 4px 10px; cursor: pointer; font-size: 12px;
    }
    button:hover { background: var(--vscode-button-hoverBackground); }
    #canvas {
      flex: 1; overflow: auto;
      display: flex; align-items: flex-start; justify-content: flex-start;
      padding: 16px;
    }
    #canvas svg {
      max-width: none;
      transform-origin: top left;
      transition: transform 0.15s ease;
    }
  </style>
</head>
<body>
  <header>
    <h2>⬡ ${className}</h2>
    <small title="${classPath}">${classPath}</small>
    <div class="controls">
      <button onclick="zoom(1.2)">＋ Zoom In</button>
      <button onclick="zoom(0.8)">－ Zoom Out</button>
      <button onclick="reset()">⟳ Reset</button>
      <button onclick="exportSvg()">⬇ Export SVG</button>
    </div>
  </header>
  <div id="canvas">
    ${svgContent}
  </div>
  <script>
    let scale = 1;
    const svg = document.querySelector('#canvas svg');
    function zoom(factor) {
      scale = Math.min(Math.max(scale * factor, 0.1), 10);
      if (svg) svg.style.transform = 'scale(' + scale + ')';
    }
    function reset() {
      scale = 1;
      if (svg) svg.style.transform = 'scale(1)';
    }
    function exportSvg() {
      if (!svg) return;
      const blob = new Blob([svg.outerHTML], { type: 'image/svg+xml' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = '${className}_diagram.svg';
      a.click();
    }
    // Pan with mouse drag
    let dragging = false, startX = 0, startY = 0, scrollLeft = 0, scrollTop = 0;
    const canvas = document.getElementById('canvas');
    canvas.addEventListener('mousedown', e => {
      dragging = true; startX = e.pageX - canvas.offsetLeft;
      startY = e.pageY - canvas.offsetTop;
      scrollLeft = canvas.scrollLeft; scrollTop = canvas.scrollTop;
    });
    canvas.addEventListener('mousemove', e => {
      if (!dragging) return;
      canvas.scrollLeft = scrollLeft - (e.pageX - canvas.offsetLeft - startX);
      canvas.scrollTop  = scrollTop  - (e.pageY - canvas.offsetTop  - startY);
    });
    canvas.addEventListener('mouseup', () => { dragging = false; });
    // Wheel zoom
    canvas.addEventListener('wheel', e => {
      e.preventDefault();
      zoom(e.deltaY < 0 ? 1.1 : 0.9);
    }, { passive: false });
  </script>
</body>
</html>`;
}