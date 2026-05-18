// src/ui/statusBar.ts — status bar management

import { getStatusBar, selectedAscetPath } from '../state';

export function updateStatusBar(): void {
    const bar = getStatusBar();
    if (selectedAscetPath) {
        const label    = selectedAscetPath.split('/').pop() ?? selectedAscetPath;
        bar.text       = `$(circuit-board) ${label}`;
        bar.tooltip    = `ASCET selected: ${selectedAscetPath}\nClick to re-analyze`;
        bar.command    = 'ascet.analyzeSelected';
    } else {
        bar.text       = `$(circuit-board) ASCET Copilot`;
        bar.tooltip    = 'Click to search and select an ASCET class';
        bar.command    = 'ascet.selectAndChat';
    }
    bar.show();
}
