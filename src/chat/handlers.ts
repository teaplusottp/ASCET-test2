// src/chat/handlers.ts — @ascet slash-command handlers
//
// Mỗi handler nhận (stream, classpath, token) và tự xử lý CLI call.
// participant.ts chỉ dispatch đến đây — không có logic nghiệp vụ ở đó.

import * as vscode from 'vscode';
import { runAscetCli }      from '../cli/runner';
import { getAscetContext }  from './context';
import { setSelectedPath }  from '../state';
import { updateStatusBar }  from '../ui/statusBar';
import { log }              from '../ui/logger';
import {
    CalcCodeResult,
    AnalyzeResult,
    DsdExportResult,
    AscetTreeRoot,
} from '../cli/types';

// ── /list ─────────────────────────────────────────────────────────────────
export async function handleList(
    stream: vscode.ChatResponseStream,
    token:  vscode.CancellationToken
): Promise<void> {
    stream.markdown('Scanning ASCET Database...\n\n');
    const result = await runAscetCli<string[]>('list_classes', [], token);
    if (!result.success) {
        stream.markdown(`❌ **Error:** ${result.error}`);
        return;
    }
    stream.markdown(`Found **${result.data.length}** classes:\n\n`);
    for (const cls of result.data) {
        stream.markdown(`- \`${cls}\`\n`);
    }
}

// ── /diagram ──────────────────────────────────────────────────────────────
export async function handleDiagram(
    stream:    vscode.ChatResponseStream,
    classpath: string,
    token:     vscode.CancellationToken
): Promise<void> {
    stream.markdown(`Reading block diagram: \`${classpath}\`...\n\n`);
    const result = await runAscetCli<object>('check_diagram', ['--path', classpath], token);
    if (!result.success) {
        stream.markdown(`❌ **Error:** ${result.error}`);
        return;
    }
    stream.markdown('```json\n' + JSON.stringify(result.data, null, 2) + '\n```');
}

// ── /dsd ─────────────────────────────────────────────────────────────────
export async function handleDsd(
    stream:    vscode.ChatResponseStream,
    classpath: string,
    token:     vscode.CancellationToken
): Promise<void> {
    stream.markdown(`Exporting DSD (Excel) for \`${classpath}\`...\n\n`);
    const result = await runAscetCli<DsdExportResult>(
        'export_dsd', ['--path', classpath], token
    );
    if (!result.success) {
        stream.markdown(`❌ **Error:** ${result.error}`);
        return;
    }
    const { class_name, excel_path } = result.data;
    stream.markdown(`✅ **${class_name}** exported.\n\n`);
    stream.markdown(`📄 File: \`${excel_path}\``);
}

// ── /ai ──────────────────────────────────────────────────────────────────
export async function handleAi(
    stream:    vscode.ChatResponseStream,
    classpath: string,
    mode:      string,
    token:     vscode.CancellationToken
): Promise<void> {
    stream.markdown(`🤖 Running AI review (**${mode}** mode) for \`${classpath}\`...\n\n`);
    stream.markdown('_This may take 30–120 seconds depending on model and RAG settings._\n\n');

    const result = await runAscetCli<AnalyzeResult>(
        'analyze_code',
        ['--path', classpath, '--mode', mode],
        token
    );
    if (!result.success) {
        stream.markdown(`❌ **Error:** ${result.error}`);
        if (result.detail) {
            stream.markdown('```\n' + result.detail + '\n```');
        }
        return;
    }

    const d = result.data;
    const ruleCount = (d.rule_errors as unknown[])?.length ?? 0;
    const aiCount   = (d.ai_errors   as unknown[])?.length ?? 0;

    stream.markdown(`### Review complete\n\n`);
    stream.markdown(`- Rule errors: **${ruleCount}**\n`);
    stream.markdown(`- AI errors:   **${aiCount}**\n`);
    if (d.report_path) {
        stream.markdown(`- Report: \`${d.report_path}\`\n`);
    }
    if (ruleCount > 0 || aiCount > 0) {
        stream.markdown('\n```json\n' + JSON.stringify(d, null, 2).slice(0, 3000) + '\n```');
    }
}

// ── /analyze (default) ───────────────────────────────────────────────────
export async function handleAnalyze(
    stream:    vscode.ChatResponseStream,
    classpath: string,
    token:     vscode.CancellationToken
): Promise<void> {
    // 1. Fetch context (system prompt + calc code)
    const ctx = await getAscetContext(classpath, token);

    // 2. Fetch raw calc code for display (may already be in ctx)
    stream.markdown(`Extracting \`Main.calc\` for **${classpath}**...\n\n`);
    const result = await runAscetCli<CalcCodeResult>(
        'get_calc_code', ['--path', classpath], token
    );

    if (!result.success) {
        stream.markdown(
            `❌ **Error:** ${result.error}` +
            (result.detail ? `\n\n\`\`\`\n${result.detail}\n\`\`\`` : '')
        );
        return;
    }

    const { calc_code, class_name, line_count } = result.data;
    setSelectedPath(classpath);
    updateStatusBar();

    stream.markdown(`### \`${class_name}\`  ·  ${line_count} lines\n\n`);
    stream.markdown('```c\n' + calc_code + '\n```\n\n');

    // 3. LLM analysis — inject ASCET system prompt if available
    const models = await vscode.lm.selectChatModels({ family: 'gpt-4o' });
    if (models.length === 0) {
        stream.markdown('_No language model available. Code shown above._');
        return;
    }

    const systemPrompt = ctx?.systemPrompt ??
        `You are a senior embedded-software engineer reviewing ASCET calc code.`;

    const userMsg =
        `Analyze the following ASCET calc code for class "${class_name}". ` +
        `Explain step-by-step what it does, identify potential issues, and suggest improvements.\n\n` +
        '```c\n' + calc_code + '\n```';

    const messages = [
        vscode.LanguageModelChatMessage.User(systemPrompt),
        vscode.LanguageModelChatMessage.User(userMsg),
    ];

    stream.markdown('---\n### 🤖 AI Analysis\n\n');
    const response = await models[0].sendRequest(messages, {}, token);
    for await (const chunk of response.text) { stream.markdown(chunk); }
    log(`[Analyze] Done: ${class_name}`);
}
