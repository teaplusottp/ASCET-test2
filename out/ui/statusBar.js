"use strict";
// src/ui/statusBar.ts — status bar management
Object.defineProperty(exports, "__esModule", { value: true });
exports.updateStatusBar = updateStatusBar;
exports.setStatus = setStatus;
exports.clearStatus = clearStatus;
const state_1 = require("../state");
function updateStatusBar() {
    const bar = (0, state_1.getStatusBar)();
    if (state_1.selectedAscetPath) {
        const label = state_1.selectedAscetPath.split('/').pop() ?? state_1.selectedAscetPath;
        bar.text = `$(circuit-board) ${label}`;
        bar.tooltip = `ASCET selected: ${state_1.selectedAscetPath}\nClick to re-analyze`;
        bar.command = 'ascet.analyzeSelected';
    }
    else {
        bar.text = `$(circuit-board) ASCET Copilot`;
        bar.tooltip = 'Click to search and select an ASCET class';
        bar.command = 'ascet.selectAndChat';
    }
    bar.show();
}
function setStatus(text) {
    const bar = (0, state_1.getStatusBar)();
    bar.text = text;
    bar.show();
}
function clearStatus() {
    const bar = (0, state_1.getStatusBar)();
    bar.text = `$(circuit-board) ASCET Copilot`; // Trả về text mặc định
    bar.show();
}
//# sourceMappingURL=statusBar.js.map