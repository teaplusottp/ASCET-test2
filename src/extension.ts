// src/extension.ts — ASCET Copilot VS Code Extension  v0.3.0
// =============================================================
// Entry point: chỉ khởi tạo state, đăng ký providers và commands.
// Mọi logic nghiệp vụ nằm trong các module con.
//
// Cấu trúc:
//   src/
//   ├── state.ts              — global shared state (OutputChannel, StatusBar, …)
//   ├── cli/
//   │   ├── types.ts          — CliResult<T>, AscetTreeNode, CalcCodeResult, …
//   │   ├── resolver.ts       — locate ascet_cli.exe / python fallback
//   │   └── runner.ts         — spawn CLI, relay stderr, parse JSON stdout
//   ├── tree/
//   │   ├── item.ts           — AscetClassItem (TreeItem)
//   │   └── provider.ts       — AscetClassTreeProvider (TreeDataProvider)
//   ├── chat/
//   │   ├── context.ts        — get_context CLI → system prompt + calc code
//   │   ├── handlers.ts       — /list /analyze /diagram /dsd /ai /context handlers
//   │   └── participant.ts    — @ascet chat participant dispatcher
//   ├── commands/
//   │   └── index.ts          — all VS Code command implementations
//   └── ui/
//       ├── logger.ts         — timestamped output channel logging
//       └── statusBar.ts      — status bar text/command helper

import * as vscode from 'vscode';
import { initState }             from './state';
import { updateStatusBar }       from './ui/statusBar';
import { log }                   from './ui/logger';
import { AscetClassTreeProvider } from './tree/provider';
import { registerChatParticipant } from './chat/participant';
import {
    injectTreeProvider,
    cmdRefresh,
    cmdSelectAndChat,
    cmdAnalyzeSelected,
    cmdAskCopilot,
    cmdOpenLog,
    cmdExportDsd,
    cmdRunAiReview,
} from './commands/index';

export function activate(context: vscode.ExtensionContext): void {
    // 1. Bootstrap shared state (OutputChannel, StatusBar, extensionUri)
    initState(context);
    log('ASCET Copilot v0.3.0 activated.');

    // 2. Initial status bar
    updateStatusBar();

    // 3. Tree View
    const treeProvider = new AscetClassTreeProvider();
    injectTreeProvider(treeProvider);

    const treeView = vscode.window.createTreeView('myAscetTreeView', {
        treeDataProvider: treeProvider,
        showCollapseAll:  false,
    });

    // 4. Chat participant  @ascet
    registerChatParticipant(context);

    // 5. Commands
    context.subscriptions.push(
        treeView,
        vscode.commands.registerCommand('ascet.refresh',         cmdRefresh),
        vscode.commands.registerCommand('ascet.selectAndChat',   cmdSelectAndChat),
        vscode.commands.registerCommand('ascet.analyzeSelected', cmdAnalyzeSelected),
        vscode.commands.registerCommand('ascet.askCopilot',      cmdAskCopilot),
        vscode.commands.registerCommand('ascet.openLog',         cmdOpenLog),
        vscode.commands.registerCommand('ascet.exportDsd',       cmdExportDsd),
        vscode.commands.registerCommand('ascet.runAiReview',     cmdRunAiReview),
    );

    log('Ready. Open the ASCET Copilot panel in the Activity Bar (left sidebar).');
}

export function deactivate(): void { /* nothing */ }
