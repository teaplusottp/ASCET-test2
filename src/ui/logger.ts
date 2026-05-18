// src/ui/logger.ts — timestamped output channel logging

import { getOutputChannel } from '../state';

export function log(msg: string): void {
    const ts = new Date().toTimeString().slice(0, 8);
    getOutputChannel().appendLine(`[${ts}] ${msg}`);
}

export function showLog(): void {
    getOutputChannel().show(false);
}
