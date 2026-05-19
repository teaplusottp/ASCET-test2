// src/ui/logger.ts — timestamped output channel logging  v0.6.0

import { getOutputChannel } from "../state";

export function log(msg: string): void {
  const ts = new Date().toTimeString().slice(0, 8);
  getOutputChannel().appendLine(`[${ts}] ${msg}`);
}

/** Alias — used by handlers and participant */
export const logInfo = log;

export function logError(msg: string): void {
  const ts = new Date().toTimeString().slice(0, 8);
  getOutputChannel().appendLine(`[${ts}] ERROR: ${msg}`);
}

export function showLog(): void {
  getOutputChannel().show(false);
}