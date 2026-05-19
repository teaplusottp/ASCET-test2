// src/chat/context.ts — fetch ESDL system prompt + calc code from CLI  v0.6.0
//
// VS Code gọi getAscetContext() trước khi send LLM request để inject
// system prompt (luật lệ ASCET) và code hiện tại.

import * as vscode from "vscode";
import { runAscetCli } from "../cli/runner";
import { AscetContext } from "../cli/types";
import { log } from "../ui/logger";

export type { AscetContext };

/**
 * Call `ascet_cli get_context --path <classpath>` and return the enriched
 * system prompt + calc code.  Returns null if the CLI call fails.
 */
export async function getAscetContext(
  classpath: string,
  token?: vscode.CancellationToken
): Promise<AscetContext | null> {
  log(`[Context] Fetching context for ${classpath}...`);
  const result = await runAscetCli<AscetContext>(
    "get_context",
    ["--path", classpath],
    token
  );
  if (!result.success || !result.data) {
    log(`[Context] Failed: ${result.error}`);
    return null;
  }
  const ctx = result.data;
  log(
    `[Context] Got system prompt (${ctx.system_prompt.length} chars), calc_code=${!!ctx.calc_code}`
  );
  return ctx;
}

/**
 * Build the vscode.LanguageModelChatMessage array to prepend to any LLM
 * request involving an ASCET class.  Includes system prompt + code block.
 */
export function buildLmMessages(
  ctx: AscetContext,
  userQuery: string
): vscode.LanguageModelChatMessage[] {
  const parts: string[] = [ctx.system_prompt];

  if (ctx.calc_code) {
    parts.push(
      `\n\nCurrent ESDL calc code for \`${ctx.class_name}\`:\n\`\`\`esdl\n${ctx.calc_code}\n\`\`\``
    );
  }

  return [
    vscode.LanguageModelChatMessage.User(parts.join("")),
    vscode.LanguageModelChatMessage.User(userQuery),
  ];
}