// src/cli/resolver.ts — locate the ascet_cli binary or python fallback

import * as vscode from 'vscode';
import * as path   from 'path';
import * as fs     from 'fs';
import { getExtensionUri } from '../state';

export function getConfig<T>(key: string, fallback: T): T {
    return vscode.workspace.getConfiguration('ascetCopilot').get<T>(key, fallback);
}

export function resolveCliDir(): string {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
        throw new Error('No workspace folder open. Open the ASCET project folder in VS Code.');
    }
    return folders[0].uri.fsPath;
}

/**
 * Returns [executable, baseArgs] in order of preference:
 *   1. User-configured cliBinPath   → [path, []]
 *   2. Bundled bin/ascet_cli.exe    → [path, []]
 *   3. Python + ascet_cli.py        → [python, [cliPath]]
 */
export function resolveCliInvocation(): [string, string[]] {
    // 1. Explicit user override
    const userBinPath = getConfig<string>('cliBinPath', '');
    if (userBinPath && fs.existsSync(userBinPath)) {
        return [userBinPath, []];
    }

    // 2. Bundled exe
    const bundledExe = path.join(getExtensionUri().fsPath, 'bin', 'ascet_cli.exe');
    if (fs.existsSync(bundledExe)) {
        return [bundledExe, []];
    }

    // 3. Python fallback
    const cliDir  = resolveCliDir();
    const cliPath = path.join(cliDir, 'ascet_cli.py');

    // 3a. User-configured pythonPath
    const configuredPython = getConfig<string>('pythonPath', '');
    if (configuredPython) {
        return [configuredPython, [cliPath]];
    }

    // 3b. VS Code Python extension API
    try {
        const pyExt = vscode.extensions.getExtension('ms-python.python');
        if (pyExt) {
            const api = pyExt.exports as {
                settings?: {
                    getExecutionDetails?: (uri?: vscode.Uri) => { execCommand?: string[] }
                }
            };
            const execCmd = api?.settings?.getExecutionDetails?.()?.execCommand;
            if (execCmd && execCmd.length > 0 && execCmd[0]) {
                return [execCmd[0], [cliPath]];
            }
        }
    } catch { /* ignore */ }

    // 3c. Hard fallback
    return ['python', [cliPath]];
}
