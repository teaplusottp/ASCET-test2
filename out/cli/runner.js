"use strict";
// src/cli/runner.ts — spawn ascet_cli and parse JSON stdout  v0.6.0
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
exports.runCli = void 0;
exports.runAscetCli = runAscetCli;
const child_process = __importStar(require("child_process"));
const resolver_1 = require("./resolver");
const logger_1 = require("../ui/logger");
/**
 * Spawn ascet_cli with `command` + `extraArgs`, relay stderr to the
 * output channel, and resolve with the parsed JSON from stdout.
 *
 * All ascet_cli commands accept `--version <ver>` so the runner injects
 * it automatically from the workspace configuration.
 */
function runAscetCli(command, extraArgs, token) {
    return new Promise((resolve) => {
        let cliDir;
        let exe;
        let baseArgs;
        try {
            cliDir = (0, resolver_1.resolveCliDir)();
            [exe, baseArgs] = (0, resolver_1.resolveCliInvocation)();
        }
        catch (err) {
            resolve({ success: false, error: err.message });
            return;
        }
        const version = (0, resolver_1.getConfig)("ascetVersion", "6.1.4");
        const args = [
            ...baseArgs,
            "--version", version,
            command,
            ...extraArgs,
        ];
        (0, logger_1.log)(`> ${exe} ${args.join(" ")}`);
        const proc = child_process.spawn(exe, args, {
            cwd: cliDir,
            stdio: ["ignore", "pipe", "pipe"],
            windowsHide: true,
        });
        let stdout = "";
        proc.stdout.on("data", (c) => { stdout += c.toString(); });
        proc.stderr.on("data", (c) => { (0, logger_1.log)(c.toString().trimEnd()); });
        token?.onCancellationRequested(() => {
            proc.kill();
            resolve({ success: false, error: "Cancelled by user." });
        });
        proc.on("close", (code) => {
            const raw = stdout.trim();
            (0, logger_1.log)(`< exit ${code}  stdout=${raw.length} chars`);
            if (!raw) {
                resolve({
                    success: false,
                    error: "CLI produced no output.",
                    detail: "Check ASCET Copilot Log panel.",
                });
                return;
            }
            try {
                resolve(JSON.parse(raw));
            }
            catch {
                resolve({
                    success: false,
                    error: "CLI output is not valid JSON.",
                    detail: raw.slice(0, 400),
                });
            }
        });
        proc.on("error", (err) => {
            (0, logger_1.log)(`! spawn error: ${err.message}`);
            resolve({
                success: false,
                error: `Failed to start CLI: ${err.message}`,
                detail: exe,
            });
        });
    });
}
/** Alias so both import styles work throughout the codebase. */
exports.runCli = runAscetCli;
//# sourceMappingURL=runner.js.map