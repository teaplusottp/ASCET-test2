"use strict";
// src/cli/resolver.ts — locate the ascet_cli binary or python fallback
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
exports.getConfig = getConfig;
exports.resolveCliDir = resolveCliDir;
exports.resolveCliInvocation = resolveCliInvocation;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const state_1 = require("../state");
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
/**
 * Returns [executable, baseArgs] in order of preference:
 *   1. User-configured cliBinPath   → [path, []]
 *   2. Bundled bin/ascet_cli.exe    → [path, []]
 *   3. Python + ascet_cli.py        → [python, [cliPath]]
 */
function resolveCliInvocation() {
    // 1. Explicit user override
    const userBinPath = getConfig('cliBinPath', '');
    if (userBinPath && fs.existsSync(userBinPath)) {
        return [userBinPath, []];
    }
    // 2. Bundled exe
    const bundledExe = path.join((0, state_1.getExtensionUri)().fsPath, 'bin', 'ascet_cli.exe');
    if (fs.existsSync(bundledExe)) {
        return [bundledExe, []];
    }
    // 3. Python fallback
    const cliDir = resolveCliDir();
    const cliPath = path.join(cliDir, 'ascet_cli.py');
    // 3a. User-configured pythonPath
    const configuredPython = getConfig('pythonPath', '');
    if (configuredPython) {
        return [configuredPython, [cliPath]];
    }
    // 3b. VS Code Python extension API
    try {
        const pyExt = vscode.extensions.getExtension('ms-python.python');
        if (pyExt) {
            const api = pyExt.exports;
            const execCmd = api?.settings?.getExecutionDetails?.()?.execCommand;
            if (execCmd && execCmd.length > 0 && execCmd[0]) {
                return [execCmd[0], [cliPath]];
            }
        }
    }
    catch { /* ignore */ }
    // 3c. Hard fallback
    return ['python', [cliPath]];
}
//# sourceMappingURL=resolver.js.map