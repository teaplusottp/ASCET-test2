// src/state.ts — ASCET Copilot shared state
// ==========================================
// Single module mọi file đều import — không cần pass globals qua tham số.
// Chỉ extension.ts được phép gọi initState() trong activate().

import * as vscode from 'vscode';

let _outputChannel: vscode.OutputChannel;
let _statusBar: vscode.StatusBarItem;
let _extensionUri: vscode.Uri;
export let selectedAscetPath: string | undefined;

export function initState(ctx: vscode.ExtensionContext): void {
    _extensionUri    = ctx.extensionUri;
    _outputChannel   = vscode.window.createOutputChannel('ASCET Copilot Log');
    _statusBar       = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    ctx.subscriptions.push(_outputChannel, _statusBar);
}

export function getOutputChannel(): vscode.OutputChannel { return _outputChannel; }
export function getStatusBar(): vscode.StatusBarItem      { return _statusBar;     }
export function getExtensionUri(): vscode.Uri              { return _extensionUri;  }

export function setSelectedPath(p: string | undefined): void {
    selectedAscetPath = p;
}
