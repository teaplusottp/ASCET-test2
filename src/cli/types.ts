// src/cli/types.ts -- ASCET Copilot shared types  v0.7.0

export interface CliResult<T> {
  success: boolean;
  data?: T;
  error?: string;
  detail?: string;
}

// -- Tree -----------------------------------------------------------------------
export interface AscetTreeNode {
  name: string;
  path: string;
  type: "class" | "folder";
  class_type?: "esdl" | "diagram" | "parameter";
  children?: Record<string, AscetTreeNode>;
}

export interface AscetTreeRoot {
  type: "root";
  children: Record<string, AscetTreeNode>;
}

// -- Calc Code ------------------------------------------------------------------
export interface CalcCodeResult {
  class_path: string;
  class_name: string;
  version: string;
  calc_code: string;
  line_count: number;
}

// -- Context (system prompt + code) --------------------------------------------
export interface AscetContext {
  class_name: string;
  class_path: string;
  system_prompt: string;
  calc_code: string | null;
  warning?: string;
}

// -- System Prompt -------------------------------------------------------------
export interface SystemPromptResult {
  system_prompt: string;
  for: string;
}

// -- Class Info ----------------------------------------------------------------
export interface ClassInfoResult {
  class_path: string;
  class_name: string;
  version: string;
  class_type: "esdl" | "diagram" | "parameter";
  has_calc: boolean;
  signals: Array<{ name: string; type: string }>;
  signal_count: number;
}

// -- Diagram -------------------------------------------------------------------
export interface DiagramLogicResult {
  diagram: { path: string; block_count: number; connection_count: number };
  errors: { calc: number[]; rule: number[]; ai: number[] };
  rule_details: Array<{
    rule_key: string;
    type: string;
    message: string;
    severity?: string;
  }>;
  stats: Record<string, number>;
  /** Mermaid flowchart markup */
  mermaid?: string;
  /** Flat netlist entries */
  netlist?: NetlistEntry[];
}

export interface NetlistEntry {
  from: string;
  to: string;
  signal?: string;
}

export interface DiagramRenderResult {
  class_name: string;
  format: "svg" | "png";
  /** SVG markup string (when format = "svg") */
  content?: string;
  /** Absolute file path to rendered PNG (when format = "png") */
  image_path?: string;
  block_count?: number;
  connection_count?: number;
}

// -- Rule / Diagram Check ------------------------------------------------------
export interface DiagramIssue {
  rule_id: string;
  severity: "error" | "warning" | "info";
  message: string;
  location?: string;
}

export interface CheckDiagramResult {
  diagram_path: string;
  connection_count: number;
  connections: unknown[];
  node_count: number;
}

// -- DSD Export ----------------------------------------------------------------
export interface DsdExportResult {
  output_file: string;
  class_path?: string;
  exported_classes?: number;
  output_dir?: string;
}

// -- AI Analysis ---------------------------------------------------------------
export interface AiError {
  id?: string;
  type?: string;
  severity: "high" | "medium" | "low" | "error" | "warning" | "info";
  message: string;
  line?: number;
  suggestion?: string;
  arbitration_result?: string;
}

export interface RagHit {
  /** Short descriptor of the matched pattern */
  pattern?: string;
  text?: string;
  similarity: number;
  description?: string;
  source?: string;
}

export interface AnalyzeCodeResult {
  class_path: string;
  class_name: string;
  version: string;
  mode: "direct" | "ai_rule";
  calc_code: string;
  line_count: number;
  errors: AiError[];
  rule_errors: AiError[];
  ai_errors: AiError[];
  rag_hits: RagHit[];
  summary: string;
  stats: {
    total: number;
    high: number;
    medium: number;
    low: number;
    rag_used: boolean;
    ai_used: boolean;
  };
}

// -- Queue ---------------------------------------------------------------------
export interface ScanQueueItem {
  id: string;
  class_path: string;
  status: "pending" | "running" | "done" | "error";
  addedAt: Date;
  finishedAt?: Date;
  result?: AnalyzeCodeResult;
  error?: string;
}

// -- Legacy AI Review (queue backward compat) ---------------------------------
export interface AiReviewResult {
  class_path: string;
  summary: string;
  errors?: AiError[];
  rule_errors?: AiError[];
  stats?: { total: number; high: number; medium: number; low: number };
}