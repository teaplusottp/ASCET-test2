"use strict";
// src/chat/handlers.ts -- @ascet slash-command handlers  v0.7.0
//
// Slash commands:
//   /list              -> list all classes
//   /analyze <path>    -> extract calc + LLM analysis (via Copilot GPT-4o)
//   /diagram <path>    -> block diagram SVG + rule check
//   /dsd [path]        -> export Excel DSD
//   /ai [mode] <path>  -> full AI review pipeline (analyze_code)
//   /rag <query>       -> query RAG knowledge base
//   /context <path>    -> system prompt + calc code (debug)
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
exports.handleList = handleList;
exports.handleAnalyze = handleAnalyze;
exports.handleDiagram = handleDiagram;
exports.handleDsd = handleDsd;
exports.handleAiReview = handleAiReview;
exports.handleRagQuery = handleRagQuery;
exports.handleContext = handleContext;
const vscode = __importStar(require("vscode"));
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const runner_1 = require("../cli/runner");
const context_1 = require("./context");
const logger_1 = require("../ui/logger");
// -- /list -------------------------------------------------------------------
async function handleList(stream, _token) {
    stream.progress("Loading class list...");
    const result = await (0, runner_1.runAscetCli)("list_classes", []);
    if (!result.success || !result.data) {
        stream.markdown(`Error: ${result.error}`);
        return;
    }
    const classes = result.data;
    const esdlCount = classes.filter((c) => c.type === "esdl").length;
    const diagCount = classes.filter((c) => c.type === "diagram").length;
    stream.markdown(`### ASCET Classes (${classes.length})\n` +
        `*${esdlCount} ESDL -- ${diagCount} Block Diagrams*\n\n`);
    stream.markdown(classes
        .slice(0, 200)
        .map((c) => {
        const icon = c.type === "diagram" ? "[BD]" : c.type === "parameter" ? "[P]" : "[E]";
        return `- \`${icon}\` \`${c.path}\``;
    })
        .join("\n"));
    if (classes.length > 200) {
        stream.markdown(`\n\n*...and ${classes.length - 200} more.*`);
    }
    stream.markdown(`\n\n> Tip: \`@ascet /analyze <class_path>\` to analyze any class.`);
}
// -- /analyze ----------------------------------------------------------------
async function handleAnalyze(stream, class_path, token, request) {
    if (!class_path) {
        stream.markdown("Usage: `/analyze <class_path>`");
        return;
    }
    stream.progress(`Fetching context for \`${class_path}\`...`);
    const ctx = await (0, context_1.getAscetContext)(class_path, token);
    if (!ctx) {
        stream.markdown(`Cannot load context for \`${class_path}\``);
        return;
    }
    if (ctx.calc_code) {
        stream.markdown(`### Calc Code: \`${class_path}\`\n`);
        stream.markdown("```esdl\n" + ctx.calc_code + "\n```\n\n");
    }
    else {
        stream.markdown(`> No calc code${ctx.warning ? `: ${ctx.warning}` : "."}\n\n`);
    }
    stream.progress("Sending to LLM for analysis...");
    const [model] = await vscode.lm.selectChatModels({ vendor: "copilot", family: "gpt-4o" });
    if (!model) {
        stream.markdown("No LLM model available.");
        return;
    }
    const userQuery = "Analyze the following ASCET ESDL calc code and report any issues:\n\n```esdl\n" +
        (ctx.calc_code ?? "(no code)") + "\n```";
    const messages = (0, context_1.buildLmMessages)(ctx, userQuery);
    try {
        const response = await model.sendRequest(messages, {}, token);
        stream.markdown("### LLM Analysis\n\n");
        for await (const chunk of response.text) {
            stream.markdown(chunk);
        }
    }
    catch (e) {
        stream.markdown(`LLM error: ${e.message}`);
        (0, logger_1.logError)(`LLM error in /analyze: ${e.message}`);
    }
}
// -- /diagram ----------------------------------------------------------------
async function handleDiagram(stream, class_path, _token) {
    if (!class_path) {
        stream.markdown("Usage: `/diagram <class_path>`");
        return;
    }
    stream.progress(`Rendering diagram for \`${class_path}\`...`);
    const [renderRes, logicRes] = await Promise.all([
        (0, runner_1.runAscetCli)("render_diagram", ["--path", class_path, "--format", "svg"]),
        (0, runner_1.runAscetCli)("get_diagram_logic", ["--path", class_path]),
    ]);
    if (!renderRes.success || !renderRes.data) {
        stream.markdown(`Diagram render failed: ${renderRes.error}`);
        return;
    }
    const d = renderRes.data;
    stream.markdown(`### Block Diagram: \`${class_path}\`\n` +
        `*${d.block_count ?? "?"} blocks -- ${d.connection_count ?? "?"} connections*\n\n`);
    if (logicRes.success && logicRes.data) {
        const ld = logicRes.data;
        const totalIssues = (ld.errors.calc?.length ?? 0) + (ld.errors.rule?.length ?? 0) + (ld.errors.ai?.length ?? 0);
        if (totalIssues > 0) {
            stream.markdown(`> **${totalIssues} issue(s) found** (calc=${ld.errors.calc.length}, rule=${ld.errors.rule.length}, ai=${ld.errors.ai.length})\n\n`);
            for (const detail of (ld.rule_details ?? []).slice(0, 10)) {
                const sev = detail.severity ?? "warning";
                const icon = sev === "error" || sev === "high" ? "[E]" : sev === "warning" ? "[W]" : "[I]";
                stream.markdown(`${icon} **[${detail.rule_key ?? "Rule"}]** ${detail.message}\n`);
            }
        }
        else {
            stream.markdown("> No structural issues found.\n\n");
        }
    }
    stream.button({ command: "ascet.showDiagram", arguments: [{ path: class_path }], title: "$(symbol-class) Open Diagram Panel" });
}
// -- /dsd --------------------------------------------------------------------
async function handleDsd(stream, class_path, _token) {
    const outputDir = path.join(os.tmpdir(), "ascet_dsd");
    const cliArgs = ["--output_dir", outputDir];
    if (class_path) {
        cliArgs.push("--class_path", class_path);
        stream.progress(`Exporting DSD for \`${class_path}\`...`);
    }
    else {
        stream.progress("Exporting DSD for all classes...");
    }
    const result = await (0, runner_1.runAscetCli)("export_dsd", cliArgs);
    if (!result.success || !result.data) {
        stream.markdown(`DSD export failed: ${result.error}`);
        (0, logger_1.logError)(`DSD export failed: ${result.error}\n${result.detail}`);
        return;
    }
    const outFile = result.data.output_file;
    (0, logger_1.logInfo)(`DSD exported: ${outFile}`);
    stream.markdown(`### DSD Export Complete\n- **File:** \`${outFile}\`\n- **Classes exported:** ${result.data.exported_classes ?? "?"}\n`);
    stream.button({ command: "vscode.open", arguments: [vscode.Uri.file(outFile)], title: "$(file-excel) Open Excel File" });
}
// -- /ai ---------------------------------------------------------------------
// Usage:
//   /ai <class_path>
//   /ai direct <class_path>   -- rule-based check only
//   /ai ai_rule <class_path>  -- rule + AI analysis
//   /ai --rag <class_path>    -- augment with RAG
async function handleAiReview(stream, rawArgs, token) {
    let mode = "direct";
    let ragEnabled = false;
    let class_path = rawArgs.trim();
    if (class_path.includes("--rag")) {
        ragEnabled = true;
        class_path = class_path.replace("--rag", "").trim();
    }
    if (class_path.startsWith("ai_rule ")) {
        mode = "ai_rule";
        class_path = class_path.slice("ai_rule ".length).trim();
    }
    else if (class_path.startsWith("direct ")) {
        mode = "direct";
        class_path = class_path.slice("direct ".length).trim();
    }
    if (!class_path) {
        stream.markdown("Usage: `/ai [direct|ai_rule] [--rag] <class_path>`\n- `direct` -- fast rule-based check\n- `ai_rule` -- rule + AI analysis\n- `--rag` -- add RAG context");
        return;
    }
    stream.progress(`Running ${mode === "ai_rule" ? "AI" : "rule"} review: \`${class_path}\`${ragEnabled ? " + RAG" : ""}...`);
    (0, logger_1.logInfo)(`/ai review: ${class_path} mode=${mode} rag=${ragEnabled}`);
    const cliArgs = ["--path", class_path, "--mode", mode, ...(ragEnabled ? ["--rag_enabled"] : [])];
    const result = await (0, runner_1.runAscetCli)("analyze_code", cliArgs, token);
    if (!result.success || !result.data) {
        stream.markdown(`AI Review failed: ${result.error}`);
        if (result.detail) {
            stream.markdown("```\n" + result.detail.slice(0, 500) + "\n```");
        }
        (0, logger_1.logError)(`/ai failed: ${result.error}\n${result.detail}`);
        return;
    }
    const d = result.data;
    const s = d.stats;
    stream.markdown(`### AI Review: \`${class_path}\`\n> ${d.summary}\n\n` +
        `| High | Medium | Low | Mode | RAG |\n|------|--------|-----|------|-----|\n` +
        `| ${s.high} | ${s.medium} | ${s.low} | \`${mode}\` | ${ragEnabled ? "yes" : "no"} |\n\n`);
    if (d.calc_code) {
        stream.markdown(`<details>\n<summary>Calc Code (${d.line_count} lines)</summary>\n\n`);
        stream.markdown("```esdl\n" + d.calc_code + "\n```\n\n</details>\n\n");
    }
    if (d.rule_errors && d.rule_errors.length > 0) {
        stream.markdown(`#### Rule Checks (${d.rule_errors.length})\n`);
        for (const err of d.rule_errors.slice(0, 15)) {
            const sev = String(err.severity ?? "").toLowerCase();
            const icon = sev.includes("high") || sev.includes("error") ? "[H]" : sev.includes("medium") ? "[M]" : "[L]";
            stream.markdown(`${icon} **${err.type ?? err.message}**${err.type && err.message !== err.type ? `: ${err.message}` : ""}${err.suggestion ? `\n   > ${err.suggestion}` : ""}\n`);
        }
        stream.markdown("\n");
    }
    if (d.ai_errors && d.ai_errors.length > 0) {
        stream.markdown(`#### AI Findings (${d.ai_errors.length})\n`);
        for (const err of d.ai_errors.slice(0, 10)) {
            const sev = String(err.severity ?? "").toLowerCase();
            const icon = sev.includes("high") ? "[H]" : sev.includes("medium") ? "[M]" : "[L]";
            stream.markdown(`${icon} **${err.type ?? "Issue"}**: ${err.message}${err.suggestion ? `\n   > ${err.suggestion}` : ""}\n`);
        }
        stream.markdown("\n");
    }
    if (d.rag_hits && d.rag_hits.length > 0) {
        stream.markdown(`#### Similar Historical Cases (${d.rag_hits.length})\n`);
        for (const hit of d.rag_hits.slice(0, 5)) {
            stream.markdown(`- **${hit.pattern ?? hit.text?.slice(0, 60) ?? "Case"}** *(${(hit.similarity * 100).toFixed(0)}% similar)*${hit.description ? `\n  ${hit.description}` : ""}\n`);
        }
        stream.markdown("\n");
    }
    stream.button({ command: "ascet.showDiagram", arguments: [{ path: class_path }], title: "$(symbol-class) View Diagram" });
    stream.button({ command: "ascet.exportDsd", arguments: [{ path: class_path }], title: "$(file-excel) Export DSD" });
}
// -- /rag --------------------------------------------------------------------
async function handleRagQuery(stream, rawArgs, token) {
    const query = rawArgs.trim();
    if (!query) {
        stream.markdown("Usage: `/rag <query>`\n\nExample: `/rag variable mapping FL FR`");
        return;
    }
    stream.progress(`Querying RAG: "${query}"...`);
    (0, logger_1.logInfo)(`/rag query: ${query}`);
    const result = await (0, runner_1.runAscetCli)("rag_query", ["--query", query, "--top_k", "5"], token);
    if (!result.success || !result.data) {
        stream.markdown(`RAG query failed: ${result.error}\n> Set \`ascetCopilot.apiKey\` in settings to enable RAG.`);
        return;
    }
    const { results } = result.data;
    if (results.length === 0) {
        stream.markdown(`No matching cases found for: *"${query}"*`);
        return;
    }
    stream.markdown(`### RAG Results for: *"${query}"*\n\n`);
    for (let i = 0; i < results.length; i++) {
        const hit = results[i];
        stream.markdown(`**${i + 1}. ${hit.pattern ?? hit.text?.slice(0, 80) ?? "Case"}** *(${(hit.similarity * 100).toFixed(0)}% similar)*\n` +
            (hit.description ? `> ${hit.description}\n` : "") +
            (hit.source ? `> *Source: ${hit.source}*\n` : "") + "\n");
    }
}
// -- /context ----------------------------------------------------------------
async function handleContext(stream, class_path, _token) {
    if (!class_path) {
        stream.markdown("Usage: `/context <class_path>`");
        return;
    }
    stream.progress(`Loading context for \`${class_path}\`...`);
    const ctx = await (0, context_1.getAscetContext)(class_path);
    if (!ctx) {
        stream.markdown(`Cannot load context for \`${class_path}\``);
        return;
    }
    stream.markdown(`### LLM Context: \`${class_path}\`\n\n`);
    stream.markdown("#### System Prompt (ASCET Rules)\n");
    stream.markdown("```\n" +
        ctx.system_prompt.slice(0, 800) +
        (ctx.system_prompt.length > 800 ? "\n...(truncated)" : "") +
        "\n```\n\n");
    stream.markdown("#### Calc Code\n");
    if (ctx.calc_code) {
        stream.markdown("```esdl\n" + ctx.calc_code + "\n```\n");
    }
    else {
        stream.markdown(`> No calc code${ctx.warning ? `: ${ctx.warning}` : "."}\n`);
    }
}
//# sourceMappingURL=handlers.js.map