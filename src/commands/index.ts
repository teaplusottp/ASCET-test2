// src/commands/index.ts — all VS Code command handlers
//
// Mỗi function export ở đây được đăng ký trong extension.ts.
// Không có global state được mutate trực tiếp — dùng state.ts setters.

import * as vscode from 'vscode';
import { AscetClassItem }       from '../tree/item';
import { AscetClassTreeProvider } from '../tree/provider';
import { runAscetCli }          from '../cli/runner';
import { setSelectedPath, selectedAscetPath, getOutputChannel } from '../state';
import { updateStatusBar }      from '../ui/statusBar';
import { log, showLog }         from '../ui/logger';
import { DsdExportResult, AnalyzeResult } from '../cli/types';

// The tree provider is injected once from activate()
let _treeProvider: AscetClassTreeProvider;
export function injectTreeProvider(p: AscetClassTreeProvider): void {
    _treeProvider = p;
}

// ── Shared helper ─────────────────────────────────────────────────────────
async function openCopilotChat(classpath: string): Promise<void> {
    const prompt = `@ascet /analyze ${classpath}`;
    log(`[Chat] Opening: ${prompt}`);
    try {
        await vscode.commands.executeCommand('workbench.action.chat.open', { query: prompt });
    } catch {
        await vscode.env.clipboard.writeText(prompt);
        vscode.window.showInformationMessage(
            'ASCET: Prompt copied to clipboard — paste into Copilot Chat.',
            { modal: false }
        );
    }
}

// ── ascet.refresh ─────────────────────────────────────────────────────────
export async function cmdRefresh(): Promise<void> {
    getOutputChannel().show(true);
    await vscode.window.withProgress(
        { location: { viewId: 'myAscetTreeView' }, title: 'Scanning ASCET database...' },
        async (_, token) => { await _treeProvider.refresh(token); }
    );
}

// ── ascet.selectAndChat ───────────────────────────────────────────────────
export async function cmdSelectAndChat(): Promise<void> {
    getOutputChannel().show(true);

    let classList = _treeProvider.getClassList();

    if (classList.length === 0) {
        const result = await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'ASCET Copilot',
                cancellable: true,
            },
            async (progress, token) => {
                progress.report({ message: 'Scanning ASCET Database...' });
                return runAscetCli<string[]>('list_classes', [], token);
            }
        );
        if (!result.success) {
            vscode.window.showErrorMessage(`ASCET: ${result.error}`);
            return;
        }
        classList = result.data;
        _treeProvider.refresh();
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
    if (!picked) { return; }

    setSelectedPath(picked);
    updateStatusBar();
    await openCopilotChat(picked);
}

// ── ascet.analyzeSelected ─────────────────────────────────────────────────
export async function cmdAnalyzeSelected(classpath?: string): Promise<void> {
    const target = classpath ?? selectedAscetPath;
    if (!target) {
        vscode.window.showWarningMessage(
            'ASCET: No class selected. Use the 🔍 button or click a class in the tree.'
        );
        return;
    }
    setSelectedPath(target);
    updateStatusBar();
    getOutputChannel().show(true);
    log(`[Analyze] ${target}`);
    await openCopilotChat(target);
}

// ── ascet.askCopilot ──────────────────────────────────────────────────────
export async function cmdAskCopilot(item: AscetClassItem | undefined): Promise<void> {
    const classpath = item?.classpath ?? selectedAscetPath;
    if (!classpath) {
        vscode.window.showWarningMessage('ASCET: No class selected.');
        return;
    }
    setSelectedPath(classpath);
    updateStatusBar();
    await openCopilotChat(classpath);
}

// ── ascet.openLog ─────────────────────────────────────────────────────────
export function cmdOpenLog(): void { showLog(); }

// ── ascet.exportDsd ───────────────────────────────────────────────────────
// Gọi từ right-click context menu hoặc command palette
export async function cmdExportDsd(item?: AscetClassItem): Promise<void> {
    const classpath = item?.classpath ?? selectedAscetPath;
    if (!classpath) {
        vscode.window.showWarningMessage('ASCET: No class selected for DSD export.');
        return;
    }

    // Optional: ask for output directory
    const outputUri = await vscode.window.showOpenDialog({
        canSelectFiles: false,
        canSelectFolders: true,
        openLabel: 'Select export folder (optional)',
    });
    const outputDir = outputUri?.[0]?.fsPath ?? '';

    const extraArgs = outputDir ? ['--path', classpath, '--output_dir', outputDir]
                                : ['--path', classpath];

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: `ASCET: Exporting DSD for ${classpath.split('/').pop()}...`,
            cancellable: true,
        },
        async (_, token) => {
            const result = await runAscetCli<DsdExportResult>('export_dsd', extraArgs, token);
            if (!result.success) {
                vscode.window.showErrorMessage(`ASCET DSD export failed: ${result.error}`);
                return;
            }
            const { class_name, excel_path } = result.data;
            const openAction = 'Open folder';
            const choice = await vscode.window.showInformationMessage(
                `ASCET: DSD exported for ${class_name}`,
                openAction
            );
            if (choice === openAction && excel_path) {
                const folder = vscode.Uri.file(
                    excel_path.includes('/') || excel_path.includes('\\')
                        ? excel_path.substring(0, Math.max(excel_path.lastIndexOf('/'), excel_path.lastIndexOf('\\')))
                        : excel_path
                );
                vscode.commands.executeCommand('revealFileInOS', folder);
            }
        }
    );
}

// ── ascet.runAiReview ─────────────────────────────────────────────────────
// Quick-pick mode then run analyze_code pipeline
export async function cmdRunAiReview(item?: AscetClassItem): Promise<void> {
    const classpath = item?.classpath ?? selectedAscetPath;
    if (!classpath) {
        vscode.window.showWarningMessage('ASCET: No class selected for AI review.');
        return;
    }

    const MODE_ITEMS: vscode.QuickPickItem[] = [
        { label: 'smart_direct', description: 'Rule checks + 1 LLM call (recommended)' },
        { label: 'direct',       description: 'Rule checks only — no LLM, fastest' },
    ];
    const picked = await vscode.window.showQuickPick(MODE_ITEMS, {
        title: `ASCET AI Review — ${classpath.split('/').pop()}`,
        placeHolder: 'Select review mode',
    });
    if (!picked) { return; }
    const mode = picked.label;

    getOutputChannel().show(true);
    log(`[AI Review] ${classpath}  mode=${mode}`);

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: `ASCET: AI reviewing ${classpath.split('/').pop()} (${mode})...`,
            cancellable: true,
        },
        async (_, token) => {
            const result = await runAscetCli<AnalyzeResult>(
                'analyze_code', ['--path', classpath, '--mode', mode], token
            );
            if (!result.success) {
                vscode.window.showErrorMessage(`ASCET AI review failed: ${result.error}`);
                if (result.detail) { log(`[AI Review] ${result.detail}`); }
                return;
            }
            const d = result.data;
            const ruleCount = (d.rule_errors as unknown[])?.length ?? 0;
            const aiCount   = (d.ai_errors   as unknown[])?.length ?? 0;
            const msg = `AI review done — ${ruleCount} rule errors, ${aiCount} AI errors`;
            log(`[AI Review] ${msg}`);
            vscode.window.showInformationMessage(`ASCET: ${msg}`);
        }
    );
}
