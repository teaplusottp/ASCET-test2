// src/cli/types.ts — ASCET Copilot shared types  v0.6.0

export interface CliResult<T> {
    success: boolean;
    data?: T;
    error?: string;
    detail?: string;
  }
  
  // ── Tree ──────────────────────────────────────────────────────────────────────
  export interface AscetTreeNode {
    name: string;
    path: string;
    type: "class" | "folder";
    class_type?: "esdl" | "diagram" | "parameter";
    children?: Record<string, AscetTreeNode>;
  }
  
  export interface AscetTreeRoot {
    children: Record<string, AscetTreeNode>;
  }
  
  // ── Calc Code ─────────────────────────────────────────────────────────────────
  export interface CalcCodeResult {
    class_path: string;
    code: string;
  }
  
  // ── Context (system prompt + code) ────────────────────────────────────────────
  export interface AscetContext {
    class_name: string;
    class_path: string;
    system_prompt: string;
    calc_code: string | null;
    warning?: string;
  }
  
  // ── System Prompt ─────────────────────────────────────────────────────────────
  export interface SystemPromptResult {
    system_prompt: string;
  }
  
  // ── Diagram ───────────────────────────────────────────────────────────────────
  export interface DiagramLogicResult {
    class_path: string;
    netlist: NetlistEntry[];
    mermaid: string;
  }
  
  export interface NetlistEntry {
    from: string;
    to: string;
    signal?: string;
  }
  
  export interface DiagramRenderResult {
    class_path: string;
    format: "svg" | "png";
    content: string;          // SVG string or base64 PNG
  }
  
  // ── Rule / Diagram Check ──────────────────────────────────────────────────────
  export interface DiagramIssue {
    rule_id: string;
    severity: "error" | "warning" | "info";
    message: string;
    location?: string;
  }
  
  export interface CheckDiagramResult {
    class_path: string;
    issues: DiagramIssue[];
    summary: string;
  }
  
  // ── DSD Export ────────────────────────────────────────────────────────────────
  export interface DsdExportResult {
    output_file: string;
    class_path?: string;
    exported_classes?: number;
    output_dir?: string;
  }
  
  // ── AI Analysis ───────────────────────────────────────────────────────────────
  export interface AiError {
    id?: string;
    severity: "error" | "warning";
    message: string;
    line?: number;
    suggestion?: string;
  }
  
  export interface RagHit {
    pattern: string;
    similarity: number;
    description: string;
  }
  
  export interface AnalyzeCodeResult {
    class_path: string;
    errors: AiError[];
    warnings: AiError[];
    rag_hits: RagHit[];
    tokens_used: number;
    cost_usd: number;
  }
  
  // ── Full AI Review ────────────────────────────────────────────────────────────
  export interface AiReviewResult {
    class_path: string;
    rule_issues: DiagramIssue[];
    ai_errors: AiError[];
    ai_warnings: AiError[];
    diagram_issues: DiagramIssue[];
    rag_hits: RagHit[];
    summary: string;
    tokens_used: number;
    cost_usd: number;
  }
  
  // ── Scan Queue ────────────────────────────────────────────────────────────────
  export type ScanStatus = "pending" | "running" | "done" | "error";
  
  export interface ScanQueueItem {
    id: string;
    class_path: string;
    status: ScanStatus;
    result?: AiReviewResult;
    error?: string;
    addedAt: Date;
    finishedAt?: Date;
  }