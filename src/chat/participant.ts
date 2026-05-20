// src/chat/participant.ts — register @ascet chat participant  v0.7.0
//
// Slash commands:
//   /list              → list all classes
//   /analyze <path>    → extract calc + LLM analysis
//   /diagram <path>    → netlist + SVG diagram
//   /dsd [path]        → export Excel DSD
//   /ai [mode] <path>  → full AI review pipeline
//   /rag <query>       → query RAG knowledge base
//   /context <path>    → show system prompt + calc code (debug)

import * as vscode from "vscode";
import {
  handleList,
  handleAnalyze,
  handleDiagram,
  handleDsd,
  handleAiReview,
  handleRagQuery,
  handleContext,
} from "./handlers";
import { logInfo, logError } from "../ui/logger";

const PARTICIPANT_ID = "ascet.copilot";

export function registerParticipant(
  context: vscode.ExtensionContext
): vscode.Disposable {
  const participant = vscode.chat.createChatParticipant(
    PARTICIPANT_ID,
    async (
      request: vscode.ChatRequest,
      _ctx: vscode.ChatContext,
      stream: vscode.ChatResponseStream,
      token: vscode.CancellationToken
    ) => {
      logInfo(
        `@ascet /${request.command ?? "(no command)"} — "${request.prompt}"`
      );

      try {
        switch (request.command) {
          case "list":
            await handleList(stream, token);
            break;

          case "analyze": {
            const class_path = request.prompt.trim();
            await handleAnalyze(stream, class_path, token, request);
            break;
          }

          case "diagram": {
            const class_path = request.prompt.trim();
            await handleDiagram(stream, class_path, token);
            break;
          }

          case "dsd": {
            const class_path = request.prompt.trim();
            await handleDsd(stream, class_path, token);
            break;
          }

          case "ai": {
            await handleAiReview(stream, request.prompt, token);
            break;
          }

          case "rag": {
            await handleRagQuery(stream, request.prompt, token);
            break;
          }

          case "context": {
            const class_path = request.prompt.trim();
            await handleContext(stream, class_path, token);
            break;
          }

          default: {
            await _handleFreeChat(stream, request, token);
            break;
          }
        }
      } catch (e: any) {
        stream.markdown(`❌ **Unexpected error:** ${e.message}`);
        logError(`@ascet participant error: ${e.message}\n${e.stack}`);
      }
    }
  );

  // Metadata
  participant.iconPath = new vscode.ThemeIcon("circuit-board");
  participant.followupProvider = {
    provideFollowups(
      _result: vscode.ChatResult,
      _ctx: vscode.ChatContext,
      _token: vscode.CancellationToken
    ): vscode.ChatFollowup[] {
      return [
        { prompt: "", command: "list",    label: "$(list-tree) List classes" },
        { prompt: "", command: "diagram", label: "$(symbol-class) Show diagram" },
        { prompt: "", command: "dsd",     label: "$(file-excel) Export DSD" },
        { prompt: "", command: "ai",      label: "$(beaker) Full AI review" },
      ];
    },
  };

  return participant;
}

// ── Free-form chat ────────────────────────────────────────────────────────────
async function _handleFreeChat(
  stream: vscode.ChatResponseStream,
  request: vscode.ChatRequest,
  token: vscode.CancellationToken
): Promise<void> {
  stream.progress("Thinking…");

  const { runAscetCli } = await import("../cli/runner");
  const sysRes = await runAscetCli<{ system_prompt: string }>(
    "get_system_prompt",
    []
  );
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
  } catch (e: any) {
    stream.markdown(`❌ LLM error: ${e.message}`);
  }
}