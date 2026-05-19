// src/chat/handlers.ts — @ascet slash-command handlers  v0.6.0
//
// Slash commands:
//   /list              → list all classes
//   /analyze <path>    → extract calc + LLM analysis
//   /diagram <path>    → block diagram SVG + Mermaid
//   /dsd [path]        → export Excel DSD
//   /ai [mode] <path>  → full AI review pipeline
//   /context <path>    → system prompt + calc code (debug)

import * as vscode from "vscode";
import * as os from "os";
import * as path from "path";
import { runAscetCli } from "../cli/runner";
import { getAscetContext, buildLmMessages } from "./context";
import { logInfo, logError } from "../ui/logger";
import type {
  AiReviewResult,
  DiagramLogicResult,
  DiagramRenderResult,
  DsdExportResult,
  AscetContext,
} from "../cli/types";

type ChatStream = vscode.ChatResponseStream;
type CancelToken = vscode.CancellationToken;

// ── /list ─────────────────────────────────────────────────────────────────────
export async function handleList(
  stream: ChatStream,
  _token: CancelToken
): Promise<void> {
  stream.progress("Loading class list…");
  const result = await runAscetCli<string[]>("list_classes", []);

  if (!result.success || !result.data) {
    stream.markdown(`❌ **Error:** ${result.error}`);
    return;
  }

  stream.markdown(`### ASCET Classes (${result.data.length})\n\n`);
  stream.markdown(result.data.map((c) => `- \`${c}\``).join("\n"));
  stream.markdown(
    `\n\n> Tip: \`@ascet /analyze <class_path>\` to analyze any class.`
  );
}

// ── /analyze ──────────────────────────────────────────────────────────────────
export async function handleAnalyze(
  stream: ChatStream,
  class_path: string,
  token: CancelToken,
  request: vscode.ChatRequest
): Promise<void> {
  if (!class_path) {
    stream.markdown("❌ Usage: `/analyze <class_path>`");
    return;
  }

  stream.progress(`Fetching context for \`${class_path}\`…`);
  const ctx = await getAscetContext(class_path, token);
  if (!ctx) {
    stream.markdown(`❌ Cannot load context for \`${class_path}\``);
    return;
  }

  // Hiển thị calc code
  if (ctx.calc_code) {
    stream.markdown(`### 📋 Calc Code: \`${class_path}\`\n`);
    stream.markdown("```esdl\n" + ctx.calc_code + "\n```\n\n");
  } else {
    stream.markdown(
      `> ⚠️ No calc code loaded${ctx.warning ? `: ${ctx.warning}` : "."}\n\n`
    );
  }

  // Gửi lên LLM với system prompt đã inject
  stream.progress("Sending to LLM for analysis…");
  const [model] = await vscode.lm.selectChatModels({
    vendor: "copilot",
    family: "gpt-4o",
  });
  if (!model) {
    stream.markdown("❌ No LLM model available.");
    return;
  }

  const userQuery =
    "Analyze the following ASCET ESDL calc code and report any issues:\n\n```esdl\n" +
    (ctx.calc_code ?? "(no code)") +
    "\n```";
  const messages = buildLmMessages(ctx, userQuery);

  try {
    const response = await model.sendRequest(messages, {}, token);
    stream.markdown("### 🤖 LLM Analysis\n\n");
    for await (const chunk of response.text) {
      stream.markdown(chunk);
    }
  } catch (e: any) {
    stream.markdown(`❌ LLM error: ${e.message}`);
    logError(`LLM error in /analyze: ${e.message}`);
  }
}

// ── /diagram ──────────────────────────────────────────────────────────────────
export async function handleDiagram(
  stream: ChatStream,
  class_path: string,
  _token: CancelToken
): Promise<void> {
  if (!class_path) {
    stream.markdown("❌ Usage: `/diagram <class_path>`");
    return;
  }

  stream.progress(`Rendering diagram for \`${class_path}\`…`);

  const [renderRes, logicRes] = await Promise.all([
    runAscetCli<DiagramRenderResult>("render_diagram", [
      "--path", class_path,
      "--format", "svg",
    ]),
    runAscetCli<DiagramLogicResult>("get_diagram_logic", ["--path", class_path]),
  ]);

  if (!renderRes.success || !renderRes.data) {
    stream.markdown(`❌ Diagram render failed: ${renderRes.error}`);
    return;
  }

  // Mermaid logic
  if (logicRes.success && logicRes.data?.mermaid) {
    stream.markdown(`### 🔀 Block Diagram Logic: \`${class_path}\`\n`);
    stream.markdown("```mermaid\n" + logicRes.data.mermaid + "\n```\n\n");
  }

  stream.markdown(
    `> SVG diagram ready. Click below to open in a panel.\n`
  );
  stream.button({
    command: "ascet.showDiagram",
    arguments: [{ path: class_path }],
    title: "$(symbol-class) Open Diagram Panel",
  });

  // Netlist summary
  if (logicRes.success && logicRes.data?.netlist?.length) {
    const nl = logicRes.data.netlist;
    stream.markdown(`\n### 🔌 Netlist (${nl.length} connections)\n`);
    stream.markdown(
      nl
        .slice(0, 20)
        .map(
          (e) =>
            `- \`${e.from}\` → \`${e.to}\`${e.signal ? ` *(${e.signal})*` : ""}`
        )
        .join("\n")
    );
    if (nl.length > 20) {
      stream.markdown(`\n*…and ${nl.length - 20} more connections.*`);
    }
  }
}

// ── /dsd ─────────────────────────────────────────────────────────────────────
export async function handleDsd(
  stream: ChatStream,
  class_path: string,
  _token: CancelToken
): Promise<void> {
  const outputDir = path.join(os.tmpdir(), "ascet_dsd");
  const cliArgs: string[] = ["--output_dir", outputDir];

  if (class_path) {
    cliArgs.push("--class_path", class_path);
    stream.progress(`Exporting DSD for \`${class_path}\`…`);
  } else {
    stream.progress("Exporting DSD for all classes…");
  }

  const result = await runAscetCli<DsdExportResult>("export_dsd", cliArgs);

  if (!result.success || !result.data) {
    stream.markdown(`❌ DSD export failed: ${result.error}`);
    logError(`DSD export failed: ${result.error}\n${result.detail}`);
    return;
  }

  const outFile = result.data.output_file;
  logInfo(`DSD exported: ${outFile}`);

  stream.markdown(`### 📊 DSD Export Complete\n`);
  stream.markdown(`- **File:** \`${outFile}\`\n`);
  stream.button({
    command: "vscode.open",
    arguments: [vscode.Uri.file(outFile)],
    title: "$(file-excel) Open Excel File",
  });
}

// ── /ai ───────────────────────────────────────────────────────────────────────
// Usage:
//   /ai <class_path>
//   /ai conservative <class_path>
//   /ai severity <class_path>
//   /ai majority <class_path>
//   /ai --no_rag <class_path>
export async function handleAiReview(
  stream: ChatStream,
  rawArgs: string,
  token: CancelToken
): Promise<void> {
  const MODES = ["conservative", "severity", "majority"] as const;
  type Mode = (typeof MODES)[number];

  let mode: Mode = "severity";
  let noRag = false;
  let class_path = rawArgs.trim();

  if (class_path.includes("--no_rag")) {
    noRag = true;
    class_path = class_path.replace("--no_rag", "").trim();
  }

  for (const m of MODES) {
    if (class_path.startsWith(m + " ")) {
      mode = m;
      class_path = class_path.slice(m.length).trim();
      break;
    }
  }

  if (!class_path) {
    stream.markdown(
      "❌ Usage: `/ai [conservative|severity|majority] [--no_rag] <class_path>`"
    );
    return;
  }

  stream.progress(
    `Running full AI review: \`${class_path}\` [mode=${mode}${noRag ? ", no_rag" : ""}]…`
  );
  logInfo(`/ai review: ${class_path} mode=${mode} no_rag=${noRag}`);

  const cliArgs = [
    class_path,
    "--mode", mode,
    ...(noRag ? ["--no_rag"] : []),
  ];

  const result = await runAscetCli<AiReviewResult>("ai_review", cliArgs, token);

  if (!result.success || !result.data) {
    stream.markdown(`❌ AI Review failed: ${result.error}`);
    logError(`/ai failed: ${result.error}\n${result.detail}`);
    return;
  }

  const d = result.data;

  // ── Summary header ──
  stream.markdown(`### 🔍 AI Review: \`${class_path}\`\n`);
  stream.markdown(`> ${d.summary}\n\n`);
  stream.markdown(
    `| Metric | Value |\n|--------|-------|\n` +
      `| Rule issues | ${d.rule_issues.length} |\n` +
      `| AI errors | ${d.ai_errors.length} |\n` +
      `| AI warnings | ${d.ai_warnings.length} |\n` +
      `| Diagram issues | ${d.diagram_issues?.length ?? 0} |\n` +
      `| RAG hits | ${d.rag_hits.length} |\n` +
      `| Tokens used | ${d.tokens_used} |\n` +
      `| Cost | $${d.cost_usd.toFixed(4)} |\n\n`
  );

  // ── Rule issues ──
  if (d.rule_issues.length > 0) {
    stream.markdown(`#### ⚙️ Rule Issues (${d.rule_issues.length})\n`);
    for (const issue of d.rule_issues) {
      const icon =
        issue.severity === "error"
          ? "🔴"
          : issue.severity === "warning"
          ? "🟡"
          : "🔵";
      stream.markdown(
        `${icon} **[${issue.rule_id ?? issue.severity}]** ${issue.message}` +
          (issue.location ? ` *(${issue.location})*` : "") +
          "\n"
      );
    }
    stream.markdown("\n");
  }

  // ── AI errors ──
  if (d.ai_errors.length > 0) {
    stream.markdown(`#### 🔴 AI Errors (${d.ai_errors.length})\n`);
    for (const err of d.ai_errors) {
      stream.markdown(
        `- **${err.message}**` +
          (err.line ? ` *(line ${err.line})*` : "") +
          (err.suggestion ? `\n  > 💡 ${err.suggestion}` : "") +
          "\n"
      );
    }
    stream.markdown("\n");
  }

  // ── AI warnings ──
  if (d.ai_warnings.length > 0) {
    stream.markdown(`#### 🟡 AI Warnings (${d.ai_warnings.length})\n`);
    for (const w of d.ai_warnings) {
      stream.markdown(
        `- ${w.message}` +
          (w.suggestion ? `\n  > 💡 ${w.suggestion}` : "") +
          "\n"
      );
    }
    stream.markdown("\n");
  }

  // ── Diagram issues ──
  if ((d.diagram_issues?.length ?? 0) > 0) {
    stream.markdown(`#### 🔀 Diagram Issues (${d.diagram_issues.length})\n`);
    for (const di of d.diagram_issues) {
      stream.markdown(`- **[${di.rule_id}]** ${di.message}\n`);
    }
    stream.markdown("\n");
  }

  // ── RAG hits ──
  if (d.rag_hits.length > 0) {
    stream.markdown(`#### 📚 RAG Knowledge Hits (${d.rag_hits.length})\n`);
    for (const hit of d.rag_hits) {
      stream.markdown(
        `- **${hit.pattern}** *(similarity: ${hit.similarity.toFixed(2)})*\n` +
          `  ${hit.description}\n`
      );
    }
    stream.markdown("\n");
  }

  // ── Action buttons ──
  stream.button({
    command: "ascet.showDiagram",
    arguments: [{ path: class_path }],
    title: "$(symbol-class) View Diagram",
  });
  stream.button({
    command: "ascet.exportDsd",
    arguments: [{ path: class_path }],
    title: "$(file-excel) Export DSD",
  });
}

// ── /context ──────────────────────────────────────────────────────────────────
export async function handleContext(
  stream: ChatStream,
  class_path: string,
  _token: CancelToken
): Promise<void> {
  if (!class_path) {
    stream.markdown("❌ Usage: `/context <class_path>`");
    return;
  }

  stream.progress(`Loading context for \`${class_path}\`…`);

  const ctx = await getAscetContext(class_path);
  if (!ctx) {
    stream.markdown(`❌ Cannot load context for \`${class_path}\``);
    return;
  }

  stream.markdown(`### 🧠 LLM Context: \`${class_path}\`\n\n`);

  stream.markdown("#### System Prompt (ASCET Rules)\n");
  stream.markdown(
    "```\n" +
      ctx.system_prompt.slice(0, 800) +
      (ctx.system_prompt.length > 800 ? "\n…(truncated)" : "") +
      "\n```\n\n"
  );

  stream.markdown("#### Calc Code\n");
  if (ctx.calc_code) {
    stream.markdown("```esdl\n" + ctx.calc_code + "\n```\n");
  } else {
    stream.markdown(`> ⚠️ No calc code${ctx.warning ? `: ${ctx.warning}` : "."}\n`);
  }
}