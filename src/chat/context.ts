// src/chat/context.ts — fetch ESDL system prompt + calc code from CLI
//
// VS Code gọi getAscetContext() trước khi send LLM request để inject
// system prompt (luật lệ ASCET) và code hiện tại — thay thế vai trò
// của chat_panel._append_system_message() trong GUI cũ.

import * as vscode    from 'vscode';
import { runAscetCli } from '../cli/runner';
import { ContextResult } from '../cli/types';
import { log } from '../ui/logger';

export interface AscetContext {
    systemPrompt: string;
    calcCode: string | null;
    className: string;
}

/**
 * Call `ascet_cli get_context --path <classpath>` and return the enriched
 * system prompt + calc code.  Returns null if the CLI call fails.
 */
export async function getAscetContext(
    classpath: string,
    token?: vscode.CancellationToken
): Promise<AscetContext | null> {
    log(`[Context] Fetching context for ${classpath}...`);
    const result = await runAscetCli<ContextResult>(
        'get_context', ['--path', classpath], token
    );
    if (!result.success) {
        log(`[Context] Failed: ${result.error}`);
        return null;
    }
    const { system_prompt, calc_code, class_name } = result.data;
    log(`[Context] Got system prompt (${system_prompt.length} chars), calc_code=${!!calc_code}`);
    return { systemPrompt: system_prompt, calcCode: calc_code, className: class_name };
}

/**
 * Build the vscode.LanguageModelChatMessage array to prepend to any LLM
 * request involving an ASCET class.  Includes system prompt + code block.
 */
export function buildLmMessages(
    ctx: AscetContext,
    userQuery: string
): vscode.LanguageModelChatMessage[] {
    return [
        vscode.LanguageModelChatMessage.User(ctx.systemPrompt),
        vscode.LanguageModelChatMessage.User(userQuery),
    ];
}
