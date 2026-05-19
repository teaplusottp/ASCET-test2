"use strict";
// src/chat/context.ts — fetch ESDL system prompt + calc code from CLI  v0.6.0
//
// VS Code gọi getAscetContext() trước khi send LLM request để inject
// system prompt (luật lệ ASCET) và code hiện tại.
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
exports.getAscetContext = getAscetContext;
exports.buildLmMessages = buildLmMessages;
const vscode = __importStar(require("vscode"));
const runner_1 = require("../cli/runner");
const logger_1 = require("../ui/logger");
/**
 * Call `ascet_cli get_context --path <classpath>` and return the enriched
 * system prompt + calc code.  Returns null if the CLI call fails.
 */
async function getAscetContext(classpath, token) {
    (0, logger_1.log)(`[Context] Fetching context for ${classpath}...`);
    const result = await (0, runner_1.runAscetCli)("get_context", ["--path", classpath], token);
    if (!result.success || !result.data) {
        (0, logger_1.log)(`[Context] Failed: ${result.error}`);
        return null;
    }
    const ctx = result.data;
    (0, logger_1.log)(`[Context] Got system prompt (${ctx.system_prompt.length} chars), calc_code=${!!ctx.calc_code}`);
    return ctx;
}
/**
 * Build the vscode.LanguageModelChatMessage array to prepend to any LLM
 * request involving an ASCET class.  Includes system prompt + code block.
 */
function buildLmMessages(ctx, userQuery) {
    const parts = [ctx.system_prompt];
    if (ctx.calc_code) {
        parts.push(`\n\nCurrent ESDL calc code for \`${ctx.class_name}\`:\n\`\`\`esdl\n${ctx.calc_code}\n\`\`\``);
    }
    return [
        vscode.LanguageModelChatMessage.User(parts.join("")),
        vscode.LanguageModelChatMessage.User(userQuery),
    ];
}
//# sourceMappingURL=context.js.map