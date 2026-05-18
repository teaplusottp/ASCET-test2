// src/cli/types.ts — shared types for CLI layer

export interface CliSuccess<T> { success: true;  data: T; }
export interface CliFailure    { success: false; error: string; detail?: string; }
export type CliResult<T> = CliSuccess<T> | CliFailure;

// ── Tree types (matches JSON returned by ascet_cli list_tree) ──────────────
export interface AscetTreeNode {
    type: 'folder' | 'class';
    name: string;
    path?: string;                            // class nodes only — forward-slash
    class_type?: 'esdl' | 'diagram' | 'parameter';
    children?: Record<string, AscetTreeNode>; // folder nodes only
}
export interface AscetTreeRoot {
    type: 'root';
    children: Record<string, AscetTreeNode>;
}

// ── Calc code result ───────────────────────────────────────────────────────
export interface CalcCodeResult {
    class_path: string;
    class_name: string;
    version: string;
    calc_code: string;
    line_count: number;
}

// ── get_context result ─────────────────────────────────────────────────────
export interface ContextResult {
    class_path: string;
    class_name: string;
    system_prompt: string;
    calc_code: string | null;
}

// ── analyze_code result (simplified — full shape is in ascet_agent.py) ────
export interface AnalyzeResult {
    status: string;
    error_count?: number;
    rule_errors?: object[];
    ai_errors?: object[];
    report_path?: string;
    [key: string]: unknown;
}

// ── DSD export result ──────────────────────────────────────────────────────
export interface DsdExportResult {
    class_name: string;
    excel_path: string;
}
