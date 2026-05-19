// src/cli/runner.ts — spawn ascet_cli and parse JSON stdout  v0.6.0

import * as child_process from "child_process";
import * as vscode from "vscode";
import { getConfig, resolveCliDir, resolveCliInvocation } from "./resolver";
import { CliResult } from "./types";
import { log } from "../ui/logger";

/**
 * Spawn ascet_cli with `command` + `extraArgs`, relay stderr to the
 * output channel, and resolve with the parsed JSON from stdout.
 *
 * All ascet_cli commands accept `--version <ver>` so the runner injects
 * it automatically from the workspace configuration.
 */
export function runAscetCli<T>(
  command: string,
  extraArgs: string[],
  token?: vscode.CancellationToken
): Promise<CliResult<T>> {
  return new Promise((resolve) => {
    let cliDir: string;
    let exe: string;
    let baseArgs: string[];
    try {
      cliDir = resolveCliDir();
      [exe, baseArgs] = resolveCliInvocation();
    } catch (err) {
      resolve({ success: false, error: (err as Error).message });
      return;
    }

    const version = getConfig<string>("ascetVersion", "6.1.4");
    const args = [
      ...baseArgs,
      "--version", version,
      command,
      ...extraArgs,
    ];

    log(`> ${exe} ${args.join(" ")}`);

    const proc = child_process.spawn(exe, args, {
      cwd: cliDir,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });

    let stdout = "";
    proc.stdout.on("data", (c: Buffer) => { stdout += c.toString(); });
    proc.stderr.on("data", (c: Buffer) => { log(c.toString().trimEnd()); });

    token?.onCancellationRequested(() => {
      proc.kill();
      resolve({ success: false, error: "Cancelled by user." });
    });

    proc.on("close", (code) => {
      const raw = stdout.trim();
      log(`< exit ${code}  stdout=${raw.length} chars`);
      if (!raw) {
        resolve({
          success: false,
          error: "CLI produced no output.",
          detail: "Check ASCET Copilot Log panel.",
        });
        return;
      }
      try {
        resolve(JSON.parse(raw) as CliResult<T>);
      } catch {
        resolve({
          success: false,
          error: "CLI output is not valid JSON.",
          detail: raw.slice(0, 400),
        });
      }
    });

    proc.on("error", (err) => {
      log(`! spawn error: ${err.message}`);
      resolve({
        success: false,
        error: `Failed to start CLI: ${err.message}`,
        detail: exe,
      });
    });
  });
}

/** Alias so both import styles work throughout the codebase. */
export const runCli = runAscetCli;