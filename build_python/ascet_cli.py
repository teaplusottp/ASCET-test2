#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ascet_cli.py — ASCET Copilot Full-Featured Command-Line Router
=============================================================
Rules:
  - ALL successful data or structured errors are emitted as a single JSON line on stdout.
  - All debug/progress logs are strictly routed to sys.stderr to prevent JSON corruption.
"""

import sys
import os
import json
import argparse
import traceback
import contextlib

if getattr(sys, 'frozen', False):
    _base = sys._MEIPASS
    if _base not in sys.path:
        sys.path.insert(0, _base)

# Reconfigure stdout/stderr to ensure robust UTF-8 encoding across all Windows targets
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

def _stderr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def _ok(data: object) -> None:
    print(json.dumps({"success": True, "data": data}, ensure_ascii=True))
    sys.exit(0)

def _err(message: str, detail: str = "") -> None:
    payload = {"success": False, "error": message}
    if detail:
        payload["detail"] = detail
    print(json.dumps(payload, ensure_ascii=True))
    sys.exit(1)

def _connect_scanner(version: str):
    try:
        from src.ascet.connection import ASCETConnectionAPI
        scanner = ASCETConnectionAPI(version=version)
        if scanner.connect():
            return scanner, scanner.version
        _err("Could not connect to ASCET Database", f"Version target: {version}")
    except Exception as exc:
        _err("Import or initialization error in ASCET connection module", str(exc))

def main() -> None:
    parser = argparse.ArgumentParser(description="ASCET Copilot Modular CLI Router")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_version(p):
        p.add_argument("--version", default="auto", help="ASCET version string (e.g. 6.1.4, 6.1.5)")

    # Lệnh list_tree
    p_tree = sub.add_parser("list_tree")
    add_version(p_tree)

    # Lệnh get_calc_code
    p_calc = sub.add_parser("get_calc_code")
    p_calc.add_argument("--path", required=True)
    add_version(p_calc)

    # Lệnh get_diagram_logic
    p_logic = sub.add_parser("get_diagram_logic")
    p_logic.add_argument("--path", required=True)
    p_logic.add_argument("--enable-ai", action="store_true")
    add_version(p_logic)

    # Lệnh render_diagram
    p_render = sub.add_parser("render_diagram")
    p_render.add_argument("--path", required=True)
    p_render.add_argument("--output", default="")
    add_version(p_render)

    # Lệnh export_dsd
    p_dsd = sub.add_parser("export_dsd")
    p_dsd.add_argument("--path", required=True, help="Class path to export (e.g. 'HAZ/VAF_Warning')")
    p_dsd.add_argument("--output", default="", help="Output Excel file path (optional)")
    add_version(p_dsd)

    # Lệnh analyze_ai
    p_ai = sub.add_parser("analyze_ai")
    p_ai.add_argument("--path", required=True)
    p_ai.add_argument("--mode", default="smart_direct")
    add_version(p_ai)

    # Lệnh get_system_prompt
    p_prompt = sub.add_parser("get_system_prompt")
    p_prompt.add_argument("--type", default="esdl", 
                         help="Prompt type: esdl, diagram_review, code_review, context_extraction")

    # Lệnh get_context
    p_context = sub.add_parser("get_context")
    p_context.add_argument("--path", required=True, help="Class path to get context for")
    add_version(p_context)

    args = parser.parse_args()

    try:
        if args.command == "list_tree":
            scanner, resolved_ver = _connect_scanner(args.version)
            tree_data = scanner.scan_tree()
            _ok(tree_data)

        elif args.command == "get_calc_code":
            scanner, resolved_ver = _connect_scanner(args.version)
            code_data = scanner.extract_calc_code(args.path)
            _ok(code_data)

        elif args.command == "get_diagram_logic":
            from src.diagrams.netlist import DiagramNetlistExtractor
            from src.diagrams.rules import run_diagram_rule_checks
            
            # Extract netlist
            connections, oid_map = DiagramNetlistExtractor.extract_connections(args.path)
            diagram_data = DiagramNetlistExtractor.to_diagram_data(connections, oid_map)
            
            # Run rule-based validation
            rule_result = run_diagram_rule_checks(diagram_data)
            
            # If AI is enabled, perform structural AI verification
            ai_findings = []
            if args.enable_ai:
                from src.ai.agent import ASCETReviewSystem
                reviewer = ASCETReviewSystem(mode="diagram_review", version=args.version)
                ai_findings = reviewer.analyze_diagram(diagram_data)

            _ok({
                "diagram": {"path": args.path, "connection_count": len(connections)},
                "errors": {
                    "calc": rule_result.get("calc_errors", []),
                    "rule": rule_result.get("rule_errors", []),
                    "ai": ai_findings
                },
                "rule_details": rule_result.get("details", [])
            })

        elif args.command == "render_diagram":
            from src.diagrams.renderer import parse_diagram_xml, render_to_png
            import tempfile
            
            diagram_data = parse_diagram_xml(args.path)
            out_path = args.output or os.path.join(tempfile.gettempdir(), "ascet_rendered.png")
            render_to_png(diagram_data, out_path)
            _ok({"image_path": out_path})

        elif args.command == "export_dsd":
            from src.tools.dsd_exporter import AscetDatabaseScanner
            import tempfile
            
            try:
                scanner = AscetDatabaseScanner(version=args.version)
                
                # Connect and scan
                if not scanner.connect():
                    _err("Failed to connect to ASCET for DSD export")
                
                if not scanner.scan_database():
                    _err("Failed to scan ASCET database")
                
                # Process the specified class
                if not scanner.process_class(args.path):
                    _err(f"Failed to process class: {args.path}")
                
                # Export to Excel
                output_path = args.output or os.path.join(tempfile.gettempdir(), f"{os.path.basename(args.path)}_dsd_export.xlsx")
                final_path = scanner.export_to_excel(output_path)
                
                scanner.disconnect()
                
                _ok({
                    "status": "success",
                    "message": f"DSD export complete for {args.path}",
                    "output_file": final_path,
                    "class_path": args.path
                })
                
            except Exception as e:
                _err("DSD export failed", traceback.format_exc())

        elif args.command == "analyze_ai":
            from src.ai.agent import ASCETReviewSystem
            
            try:
                reviewer = ASCETReviewSystem(mode=args.mode, version=args.version)
                result = reviewer.run_analysis(target_path=args.path)
                
                if result and "error" not in result:
                    _ok({
                        "status": "success",
                        "target": args.path,
                        "mode": args.mode,
                        "defects": result.get("defects", []),
                        "token_statistics": result.get("token_statistics", {}),
                        "execution_time_seconds": result.get("execution_time_seconds", 0)
                    })
                else:
                    _err(result.get("error", "AI Code Analysis failed"))
            except Exception as e:
                _err("AI Code Analysis failed", traceback.format_exc())

        elif args.command == "get_system_prompt":
            from src.config.prompts import get_system_prompt, list_available_prompts
            
            try:
                prompt_text = get_system_prompt(args.type)
                _ok({
                    "type": args.type,
                    "prompt": prompt_text,
                    "available_types": list_available_prompts()
                })
            except Exception as e:
                _err(f"Failed to get system prompt: {str(e)}")

        elif args.command == "get_context":
            from src.ascet.context_provider import get_context
            
            try:
                context = get_context(args.path, args.version)
                
                # Add token estimate
                from src.ascet.context_provider import ContextProvider
                provider = ContextProvider(version=args.version)
                token_estimate = provider.estimate_token_count(context)
                context["estimated_tokens"] = token_estimate
                
                _ok({
                    "status": "success",
                    "context": context,
                    "note": "Context gathered from available sources (code, diagram, metadata)"
                })
            except Exception as e:
                _err(f"Failed to get context: {str(e)}", traceback.format_exc())

    except Exception as e:
        _err("Unexpected error occurred in execution loop", traceback.format_exc())

if __name__ == "__main__":
    main()
