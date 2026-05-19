"use strict";
// src/chat/participant.ts — register @ascet chat participant  v0.6.0
//
// Slash commands:
//   /list              → list all classes
//   /analyze <path>    → extract calc + LLM analysis
//   /diagram <path>    → netlist + SVG diagram
//   /dsd [path]        → export Excel DSD
//   /ai [mode] <path>  → full AI review pipeline
//   /context <path>    → show system prompt + calc code (debug)
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
exports.registerParticipant = registerParticipant;
const vscode = __importStar(require("vscode"));
const handlers_1 = require("./handlers");
const logger_1 = require("../ui/logger");
const PARTICIPANT_ID = "ascet.copilot";
function registerParticipant(context) {
    const participant = vscode.chat.createChatParticipant(PARTICIPANT_ID, async (request, _ctx, stream, token) => {
        (0, logger_1.logInfo)(`@ascet /${request.command ?? "(no command)"} — "${request.prompt}"`);
        try {
            switch (request.command) {
                case "list":
                    await (0, handlers_1.handleList)(stream, token);
                    break;
                case "analyze": {
                    const class_path = request.prompt.trim();
                    await (0, handlers_1.handleAnalyze)(stream, class_path, token, request);
                    break;
                }
                case "diagram": {
                    const class_path = request.prompt.trim();
                    await (0, handlers_1.handleDiagram)(stream, class_path, token);
                    break;
                }
                case "dsd": {
                    const class_path = request.prompt.trim();
                    await (0, handlers_1.handleDsd)(stream, class_path, token);
                    break;
                }
                case "ai": {
                    await (0, handlers_1.handleAiReview)(stream, request.prompt, token);
                    break;
                }
                case "context": {
                    const class_path = request.prompt.trim();
                    await (0, handlers_1.handleContext)(stream, class_path, token);
                    break;
                }
                default: {
                    await _handleFreeChat(stream, request, token);
                    break;
                }
            }
        }
        catch (e) {
            stream.markdown(`❌ **Unexpected error:** ${e.message}`);
            (0, logger_1.logError)(`@ascet participant error: ${e.message}\n${e.stack}`);
        }
    });
    // Metadata
    participant.iconPath = new vscode.ThemeIcon("circuit-board");
    participant.followupProvider = {
        provideFollowups(_result, _ctx, _token) {
            return [
                { prompt: "", command: "list", label: "$(list-tree) List classes" },
                { prompt: "", command: "diagram", label: "$(symbol-class) Show diagram" },
                { prompt: "", command: "dsd", label: "$(file-excel) Export DSD" },
                { prompt: "", command: "ai", label: "$(beaker) Full AI review" },
            ];
        },
    };
    return participant;
}
// ── Free-form chat ────────────────────────────────────────────────────────────
async function _handleFreeChat(stream, request, token) {
    stream.progress("Thinking…");
    const { runAscetCli } = await Promise.resolve().then(() => __importStar(require("../cli/runner")));
    const sysRes = await runAscetCli("get_system_prompt", []);
    const systemPrompt = sysRes.success
        ? (sysRes.data?.system_prompt ?? "")
        : "";
    const [model] = await vscode.lm.selectChatModels({
        vendor: "copilot",
        family: "gpt-4o",
    });
    if (!model) {
        stream.markdown("❌ No LLM model available.");
        return;
    }
    const messages = [
        ...(systemPrompt
            ? [vscode.LanguageModelChatMessage.User(systemPrompt)]
            : []),
        vscode.LanguageModelChatMessage.User(request.prompt),
    ];
    try {
        const response = await model.sendRequest(messages, {}, token);
        for await (const chunk of response.text) {
            stream.markdown(chunk);
        }
    }
    catch (e) {
        stream.markdown(`❌ LLM error: ${e.message}`);
    }
}
//# sourceMappingURL=participant.js.map