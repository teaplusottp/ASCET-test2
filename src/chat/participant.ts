// src/chat/participant.ts — register @ascet chat participant
//
// Slash commands:
//   /list              → list all classes
//   /analyze <path>    → extract calc + LLM analysis (default)
//   /diagram <path>    → netlist of block diagram
//   /dsd <path>        → export Excel DSD
//   /ai [mode] <path>  → run full AI review pipeline
//   /context <path>    → show system prompt + calc code (debug)

import * as vscode from 'vscode';
import { selectedAscetPath } from '../state';
import { handleList, handleAnalyze, handleDiagram, handleDsd, handleAi } from './handlers';
import { getAscetContext } from './context';
import { log } from '../ui/logger';

export function registerChatParticipant(context: vscode.ExtensionContext): void {
    const participant = vscode.chat.createChatParticipant(
        'ascet',
        async (
            request: vscode.ChatRequest,
            _ctx:    vscode.ChatContext,
            stream:  vscode.ChatResponseStream,
            token:   vscode.CancellationToken
        ) => {
            const cmd  = request.command ?? '';
            const text = request.prompt.trim();

            log(`[Chat] cmd=${cmd || '(default)'}  text=${text.slice(0, 80)}`);

            // /list — no classpath needed
            if (cmd === 'list') {
                await handleList(stream, token);
                return;
            }

            // Resolve classpath: prompt text OR last selected class
            const classpath = text || selectedAscetPath;
            if (!classpath) {
                stream.markdown(
                    '⚠️ No class selected.\n\n' +
                    '**Usage:**\n' +
                    '- `@ascet /analyze HAZ/VAF_Warning`\n' +
                    '- `@ascet /diagram HAZ/VAF_Warning`\n' +
                    '- `@ascet /dsd HAZ/VAF_Warning`\n' +
                    '- `@ascet /ai [direct|smart_direct] HAZ/VAF_Warning`\n' +
                    '- Or press the **🔍** button in the ASCET Copilot panel.'
                );
                return;
            }

            switch (cmd) {
                case 'diagram':
                    await handleDiagram(stream, classpath, token);
                    break;

                case 'dsd':
                    await handleDsd(stream, classpath, token);
                    break;

                case 'ai': {
                    // Optional mode prefix: "/ai smart_direct HAZ/VAF_Warning"
                    const MODES = ['direct', 'smart_direct', 'agent'];
                    const parts = classpath.split(/\s+/);
                    const mode  = MODES.includes(parts[0]) ? parts.shift()! : 'smart_direct';
                    const path  = parts.join(' ') || selectedAscetPath || '';
                    if (!path) {
                        stream.markdown('⚠️ Provide a class path: `@ascet /ai smart_direct HAZ/VAF_Warning`');
                        return;
                    }
                    await handleAi(stream, path, mode, token);
                    break;
                }

                case 'context': {
                    // Debug: show raw system prompt + calc code
                    stream.markdown(`Fetching context for \`${classpath}\`...\n\n`);
                    const ctx = await getAscetContext(classpath, token);
                    if (!ctx) {
                        stream.markdown('❌ Could not fetch context.');
                        return;
                    }
                    stream.markdown(`**Class:** \`${ctx.className}\`\n\n`);
                    stream.markdown('**System prompt (first 500 chars):**\n\n');
                    stream.markdown('```\n' + ctx.systemPrompt.slice(0, 500) + '\n```\n\n');
                    if (ctx.calcCode) {
                        stream.markdown(`**calc code (${ctx.calcCode.length} chars)** available.\n`);
                    } else {
                        stream.markdown('_calc code not available (ASCET not running?)_\n');
                    }
                    break;
                }

                default:
                    // /analyze or bare mention
                    await handleAnalyze(stream, classpath, token);
                    break;
            }
        }
    );

    participant.iconPath = new vscode.ThemeIcon('circuit-board');
    context.subscriptions.push(participant);
}
