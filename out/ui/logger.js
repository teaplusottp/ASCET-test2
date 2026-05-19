"use strict";
// src/ui/logger.ts — timestamped output channel logging  v0.6.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.logInfo = void 0;
exports.log = log;
exports.logError = logError;
exports.showLog = showLog;
const state_1 = require("../state");
function log(msg) {
    const ts = new Date().toTimeString().slice(0, 8);
    (0, state_1.getOutputChannel)().appendLine(`[${ts}] ${msg}`);
}
/** Alias — used by handlers and participant */
exports.logInfo = log;
function logError(msg) {
    const ts = new Date().toTimeString().slice(0, 8);
    (0, state_1.getOutputChannel)().appendLine(`[${ts}] ERROR: ${msg}`);
}
function showLog() {
    (0, state_1.getOutputChannel)().show(false);
}
//# sourceMappingURL=logger.js.map