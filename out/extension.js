"use strict";
// src/extension.ts — ASCET Copilot VS Code Extension  v0.2.0
// =============================================================
// UI components:
//   • Activity Bar panel "ASCET Copilot" with icon $(circuit-board)
//   • Tree View  myAscetTreeView  — lists all ASCET classes
//       toolbar: [🔄 Refresh]  [🔍 Search]  [📋 Log]
//       right-click item: [▶ Analyze]  [🤖 Ask Copilot]
//   • Status Bar item — shows currently selected class
//   • Output Channel "ASCET Copilot Log" — CLI stderr relay
//   • Chat Participant  @ascet  (/analyze /list /diagram)
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
exports.selectedAscetPath = void 0;
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const child_process = __importStar(require("child_process"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
let outputChannel;
let statusBar;
let treeProvider;
let extensionUri; // set in activate(), used to locate bundled exe
// ─────────────────────────────────────────────────────────────────────────────
// Config helpers
// ─────────────────────────────────────────────────────────────────────────────
function getConfig(key, fallback) {
    return vscode.workspace.getConfiguration('ascetCopilot').get(key, fallback);
}
function resolveCliDir() {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
        throw new Error('No workspace folder open. Open the ASCET project folder in VS Code.');
    }
    return folders[0].uri.fsPath;
}
function resolveCliInvocation() {
    // 1. Explicit user override in settings
    const userBinPath = getConfig('cliBinPath', '');
    if (userBinPath && fs.existsSync(userBinPath)) {
        return [userBinPath, []];
    }
    // 2. Bundled ascet_cli.exe shipped inside bin/ folder of this extension
    const bundledExe = path.join(extensionUri.fsPath, 'bin', 'ascet_cli.exe');
    if (fs.existsSync(bundledExe)) {
        return [bundledExe, []];
    }
    // 3. Fall back to python + ascet_cli.py in the workspace (dev / source mode)
    const cliDir = resolveCliDir();
    const cliPath = path.join(cliDir, 'ascet_cli.py');
    // 3a. User-configured pythonPath
    const configuredPython = getConfig('pythonPath', '');
    if (configuredPython) {
        return [configuredPython, [cliPath]];
    }
    // 3b. Try to get Python from the VS Code Python extension
    try {
        const pyExt = vscode.extensions.getExtension('ms-python.python');
        if (pyExt) {
            const api = pyExt.exports;
            const execDetails = api?.settings?.getExecutionDetails?.();
            const execCmd = execDetails?.execCommand;
            if (execCmd && execCmd.length > 0 && execCmd[0]) {
                return [execCmd[0], [cliPath]];
            }
        }
    }
    catch {
        // ignore, fall through to default
    }
    // 3c. Fallback default
    return ['python', [cliPath]];
}
function runAscetCli(command, extraArgs, token) {
    return new Promise((resolve) => {
        let cliDir;
        let exe;
        let baseArgs;
        try {
            cliDir = resolveCliDir();
            [exe, baseArgs] = resolveCliInvocation();
        }
        catch (err) {
            resolve({ success: false, error: err.message });
            return;
        }
        const version = getConfig('ascetVersion', 'auto');
        const args = [...baseArgs, command, '--version', version, ...extraArgs];
        log(`> ${exe} ${args.join(' ')}`);
        const proc = child_process.spawn(exe, args, {
            cwd: cliDir,
            stdio: ['ignore', 'pipe', 'pipe'],
            windowsHide: true,
        });
        let stdout = '';
        proc.stdout.on('data', (c) => { stdout += c.toString(); });
        proc.stderr.on('data', (c) => { log(c.toString().trimEnd()); });
        token?.onCancellationRequested(() => {
            proc.kill();
            resolve({ success: false, error: 'Cancelled by user.' });
        });
        proc.on('close', (code) => {
            const raw = stdout.trim();
            log(`< exit ${code}  stdout=${raw.length} chars`);
            if (!raw) {
                resolve({ success: false, error: 'CLI produced no output.', detail: 'Check ASCET Copilot Log panel.' });
                return;
            }
            try {
                resolve(JSON.parse(raw));
            }
            catch {
                resolve({ success: false, error: 'CLI output is not valid JSON.', detail: raw.slice(0, 400) });
            }
        });
        proc.on('error', (err) => {
            log(`! spawn error: ${err.message}`);
            resolve({ success: false, error: `Failed to start CLI: ${err.message}`, detail: exe });
        });
    });
}
// ─────────────────────────────────────────────────────────────────────────────
// Logging
// ─────────────────────────────────────────────────────────────────────────────
function log(msg) {
    const ts = new Date().toTimeString().slice(0, 8);
    outputChannel.appendLine(`[${ts}] ${msg}`);
}
// ─────────────────────────────────────────────────────────────────────────────
// Tree View — AscetClassItem
// ─────────────────────────────────────────────────────────────────────────────
class AscetClassItem extends vscode.TreeItem {
    constructor(nodeOrMsg, isMessage) {
        if (isMessage || typeof nodeOrMsg === 'string') {
            super(nodeOrMsg, vscode.TreeItemCollapsibleState.None);
            return;
        }
        const node = nodeOrMsg;
        super(node.name, node.type === 'folder'
            ? vscode.TreeItemCollapsibleState.Collapsed
            : vscode.TreeItemCollapsibleState.None);
        if (node.type === 'folder') {
            this.nodeChildren = node.children;
            this.iconPath = new vscode.ThemeIcon('folder');
            this.contextValue = 'ascetFolder';
        }
        else {
            this.classpath = node.path;
            this.tooltip = node.path;
            this.description = node.path?.includes('/')
                ? node.path.substring(0, node.path.lastIndexOf('/'))
                : '';
            this.contextValue = 'ascetClass';
            this.iconPath = new vscode.ThemeIcon('symbol-class');
            this.command = {
                command: 'ascet.analyzeSelected',
                title: 'Analyze',
                arguments: [node.path],
            };
        }
    }
}
// ─────────────────────────────────────────────────────────────────────────────
// Tree View — AscetClassTreeProvider
// ─────────────────────────────────────────────────────────────────────────────
class AscetClassTreeProvider {
    constructor() {
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        this.treeRoot = null;
        this.loading = false;
    }
    getTreeItem(element) { return element; }
    getChildren(element) {
        if (this.loading) {
            return [new AscetClassItem('$(sync~spin)  Đang quét database...', true)];
        }
        if (this.errorMsg) {
            return [new AscetClassItem(`$(error)  ${this.errorMsg}`, true)];
        }
        if (!this.treeRoot) {
            return [new AscetClassItem('$(refresh)  Nhấn Refresh để tải danh sách class', true)];
        }
        // Determine which children dict to expand
        const childrenMap = element?.nodeChildren ?? this.treeRoot.children;
        return Object.values(childrenMap)
            .sort((a, b) => {
            // Folders first, then classes; both alphabetically
            if (a.type !== b.type) {
                return a.type === 'folder' ? -1 : 1;
            }
            return a.name.localeCompare(b.name);
        })
            .map(node => new AscetClassItem(node));
    }
    async refresh(token) {
        this.loading = true;
        this.errorMsg = undefined;
        this._onDidChangeTreeData.fire(undefined);
        log('[Tree] Refreshing class tree...');
        const result = await runAscetCli('list_tree', [], token);
        this.loading = false;
        if (result.success) {
            this.treeRoot = result.data;
            const count = this._countClasses(result.data.children);
            log(`[Tree] Loaded ${count} ESDL classes.`);
        }
        else {
            this.errorMsg = result.error;
            log(`[Tree] Error: ${result.error}`);
            if (result.detail) {
                log(`[Tree] Detail:\n${result.detail}`);
            }
        }
        this._onDidChangeTreeData.fire(undefined);
    }
    _countClasses(children) {
        let n = 0;
        for (const node of Object.values(children)) {
            if (node.type === 'class') {
                n++;
            }
            else if (node.children) {
                n += this._countClasses(node.children);
            }
        }
        return n;
    }
    /** Flat sorted list of all class paths — used by QuickPick search */
    getClassList() {
        if (!this.treeRoot) {
            return [];
        }
        const out = [];
        this._collectClasses(this.treeRoot.children, out);
        return out.sort();
    }
    _collectClasses(children, out) {
        for (const node of Object.values(children)) {
            if (node.type === 'class' && node.path) {
                out.push(node.path);
            }
            else if (node.children) {
                this._collectClasses(node.children, out);
            }
        }
    }
}
// ─────────────────────────────────────────────────────────────────────────────
// Status Bar
// ─────────────────────────────────────────────────────────────────────────────
function updateStatusBar() {
    if (exports.selectedAscetPath) {
        const label = exports.selectedAscetPath.split('/').pop() ?? exports.selectedAscetPath;
        statusBar.text = `$(circuit-board) ${label}`;
        statusBar.tooltip = `ASCET selected: ${exports.selectedAscetPath}\nClick to re-analyze`;
        statusBar.command = 'ascet.analyzeSelected';
    }
    else {
        statusBar.text = `$(circuit-board) ASCET Copilot`;
        statusBar.tooltip = 'Click to search and select an ASCET class';
        statusBar.command = 'ascet.selectAndChat';
    }
    statusBar.show();
}
// ─────────────────────────────────────────────────────────────────────────────
// Shared helpers
// ─────────────────────────────────────────────────────────────────────────────
async function openCopilotChat(classpath) {
    const prompt = `@ascet /analyze ${classpath}`;
    log(`[Chat] Opening: ${prompt}`);
    try {
        await vscode.commands.executeCommand('workbench.action.chat.open', { query: prompt });
    }
    catch {
        await vscode.env.clipboard.writeText(prompt);
        vscode.window.showInformationMessage('ASCET: Prompt copied to clipboard — paste into Copilot Chat.', { modal: false });
    }
}
// ─────────────────────────────────────────────────────────────────────────────
// Command handlers
// ─────────────────────────────────────────────────────────────────────────────
async function cmdRefresh() {
    outputChannel.show(true);
    await vscode.window.withProgress({ location: { viewId: 'myAscetTreeView' }, title: 'Scanning ASCET database...' }, async (_, token) => { await treeProvider.refresh(token); });
}
async function cmdSelectAndChat() {
    outputChannel.show(true);
    let classList = treeProvider.getClassList();
    if (classList.length === 0) {
        const result = await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: 'ASCET Copilot', cancellable: true }, async (progress, token) => {
            progress.report({ message: 'Scanning ASCET Database...' });
            return runAscetCli('list_classes', [], token);
        });
        if (!result.success) {
            vscode.window.showErrorMessage(`ASCET: ${result.error}`);
            return;
        }
        classList = result.data;
        treeProvider.refresh(); // populate tree too
    }
    if (classList.length === 0) {
        vscode.window.showWarningMessage('ASCET: No classes found in the database.');
        return;
    }
    const picked = await vscode.window.showQuickPick(classList, {
        placeHolder: 'Type class name to search... (e.g. VAF_Warning)',
        matchOnDescription: true,
        title: `ASCET Classes  (${classList.length} total)`,
    });
    if (!picked) {
        return;
    }
    exports.selectedAscetPath = picked;
    updateStatusBar();
    await openCopilotChat(picked);
}
async function cmdAnalyzeSelected(classpath) {
    const target = classpath ?? exports.selectedAscetPath;
    if (!target) {
        vscode.window.showWarningMessage('ASCET: No class selected. Use the 🔍 button in the ASCET panel or click a class in the tree.');
        return;
    }
    exports.selectedAscetPath = target;
    updateStatusBar();
    outputChannel.show(true);
    log(`[Analyze] ${target}`);
    await openCopilotChat(target);
}
async function cmdAskCopilot(item) {
    const classpath = item?.classpath ?? exports.selectedAscetPath;
    if (!classpath) {
        vscode.window.showWarningMessage('ASCET: No class selected.');
        return;
    }
    exports.selectedAscetPath = classpath;
    updateStatusBar();
    await openCopilotChat(classpath);
}
function cmdOpenLog() {
    outputChannel.show(false);
}
// ─────────────────────────────────────────────────────────────────────────────
// Chat Participant: @ascet
// ─────────────────────────────────────────────────────────────────────────────
function registerChatParticipant(context) {
    const participant = vscode.chat.createChatParticipant('ascet', async (request, _ctx, stream, token) => {
        const cmd = request.command;
        const text = request.prompt.trim();
        if (cmd === 'list') {
            stream.markdown('Scanning ASCET Database...\n\n');
            const result = await runAscetCli('list_classes', [], token);
            if (!result.success) {
                stream.markdown(`❌ **Error:** ${result.error}`);
                return;
            }
            stream.markdown(`Found **${result.data.length}** classes:\n\n`);
            for (const cls of result.data) {
                stream.markdown(`- \`${cls}\`\n`);
            }
            return;
        }
        const classpath = text || exports.selectedAscetPath;
        if (!classpath) {
            stream.markdown('⚠️ No class selected.\n\n' +
                '**Usage:**\n' +
                '- `@ascet /analyze HAZ/VAF_Warning`\n' +
                '- Or press the **🔍** button in the ASCET Copilot panel.');
            return;
        }
        if (cmd === 'diagram') {
            stream.markdown(`Reading block diagram: \`${classpath}\`...\n\n`);
            const result = await runAscetCli('check_diagram', ['--path', classpath], token);
            if (!result.success) {
                stream.markdown(`❌ **Error:** ${result.error}`);
                return;
            }
            stream.markdown('```json\n' + JSON.stringify(result.data, null, 2) + '\n```');
            return;
        }
        // /analyze (default)
        stream.markdown(`Extracting \`Main.calc\` for **${classpath}**...\n\n`);
        const result = await runAscetCli('get_calc_code', ['--path', classpath], token);
        if (!result.success) {
            stream.markdown(`❌ **Error:** ${result.error}` +
                (result.detail ? `\n\n\`\`\`\n${result.detail}\n\`\`\`` : ''));
            return;
        }
        const { calc_code, class_name, line_count } = result.data;
        exports.selectedAscetPath = classpath;
        updateStatusBar();
        stream.markdown(`### \`${class_name}\`  ·  ${line_count} lines\n\n`);
        stream.markdown('```c\n' + calc_code + '\n```\n\n');
        const models = await vscode.lm.selectChatModels({ family: 'gpt-4o' });
        if (models.length === 0) {
            stream.markdown('_No language model available. Code shown above._');
            return;
        }
        const messages = [
            vscode.LanguageModelChatMessage.User(`You are a senior embedded-software engineer. ` +
                `Analyze the following ASCET calc code for class "${class_name}". ` +
                `Explain step-by-step what it does, identify potential issues, and suggest improvements.\n\n` +
                '```c\n' + calc_code + '\n```'),
        ];
        stream.markdown('---\n### 🤖 AI Analysis\n\n');
        const response = await models[0].sendRequest(messages, {}, token);
        for await (const chunk of response.text) {
            stream.markdown(chunk);
        }
    });
    participant.iconPath = new vscode.ThemeIcon('circuit-board');
    context.subscriptions.push(participant);
}
// ─────────────────────────────────────────────────────────────────────────────
// Extension lifecycle
// ─────────────────────────────────────────────────────────────────────────────
function activate(context) {
    extensionUri = context.extensionUri; // ← used by resolveCliInvocation()
    outputChannel = vscode.window.createOutputChannel('ASCET Copilot Log');
    log('ASCET Copilot v0.2.0 activated.');
    statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    updateStatusBar();
    treeProvider = new AscetClassTreeProvider();
    const treeView = vscode.window.createTreeView('myAscetTreeView', {
        treeDataProvider: treeProvider,
        showCollapseAll: false,
    });
    context.subscriptions.push(treeView, statusBar, outputChannel, vscode.commands.registerCommand('ascet.refresh', cmdRefresh), vscode.commands.registerCommand('ascet.selectAndChat', cmdSelectAndChat), vscode.commands.registerCommand('ascet.analyzeSelected', cmdAnalyzeSelected), vscode.commands.registerCommand('ascet.askCopilot', cmdAskCopilot), vscode.commands.registerCommand('ascet.openLog', cmdOpenLog));
    registerChatParticipant(context);
    log('Ready. Open the ASCET Copilot panel in the Activity Bar (left sidebar).');
}
function deactivate() { }
//# sourceMappingURL=extension.js.map