#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ascet_cli.py — ASCET Copilot Command-Line Router
=================================================
Usage:
    python ascet_cli.py list_classes
    python ascet_cli.py list_tree
    python ascet_cli.py --version 6.1.5 get_calc_code --path "HAZ/VAF_Warning"
    python ascet_cli.py check_diagram  --path "HAZ/VAF_Warning.amd"
    python ascet_cli.py render_diagram --path "HAZ/VAF_Warning" [--format svg|png]
    python ascet_cli.py export_dsd [--class_path "HAZ/VAF_Warning"] [--output_dir "C:/tmp"]
    python ascet_cli.py analyze_code --path "HAZ/VAF_Warning" [--mode direct|ai_rule] [--rag_enabled]
    python ascet_cli.py get_system_prompt [--for copilot|review|chat]
    python ascet_cli.py get_context --path "HAZ/VAF_Warning"
    python ascet_cli.py rag_query --query "signal mapping" [--top_k 5] [--knowledge_dir "kb/"]
    python ascet_cli.py get_class_info --path "HAZ/VAF_Warning"

Rules:
  - ALL output (success or error) is a single JSON line on stdout.
  - Debug / progress text goes to sys.stderr only, never stdout.
  - --version is a GLOBAL flag (before the command) and defaults to "auto".
  - Minimize live ASCET COM calls — use cached/downloaded data when possible.
"""

import sys
import os
import json
import argparse
import traceback

# ---------------------------------------------------------------------------
# PyInstaller bundle: add _MEIPASS to sys.path so "import src.*" works when
# running as a frozen .exe.  Has no effect when running as plain .py script.
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    _base = sys._MEIPASS          # type: ignore[attr-defined]
    if _base not in sys.path:
        sys.path.insert(0, _base)

# ---------------------------------------------------------------------------
# Ensure stdout/stderr are UTF-8 in all environments (incl. PyInstaller
# --noconsole where sys.stdout may default to ASCII or be None)
# ---------------------------------------------------------------------------
import io

if sys.stdout is None or not hasattr(sys.stdout, 'buffer'):
    sys.stdout = open('nul', 'w')  # windows: discard if truly missing
elif hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

if sys.stderr is None or not hasattr(sys.stderr, 'buffer'):
    sys.stderr = open('nul', 'w')
elif hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stderr(*args, **kwargs):
    """Print to stderr so stdout stays clean JSON."""
    print(*args, file=sys.stderr, **kwargs)


def _ok(data: object) -> None:
    """Emit a success JSON envelope and exit(0)."""
    print(json.dumps({"success": True, "data": data}, ensure_ascii=True))
    sys.exit(0)


def _err(message: str, detail: str = "") -> None:
    """Emit an error JSON envelope and exit(1)."""
    payload = {"success": False, "error": message}
    if detail:
        payload["detail"] = detail
    print(json.dumps(payload, ensure_ascii=True))
    sys.exit(1)


# ---------------------------------------------------------------------------
# Auto-detect ASCET version
# ---------------------------------------------------------------------------

_VERSION_CANDIDATES = ["6.1.5", "6.1.4", "6.2.0", "6.4.0", "6.0.0"]


def _connect_scanner(version: str):
    """
    Connect using ASCETStructureScannerAPI.
    Returns (scanner, resolved_version_str) or calls _err.
    """
    try:
        from src.ascet.structure_filter import ASCETStructureScannerAPI
    except Exception as exc:
        _err("Import error: src.ascet.structure_filter", str(exc))

    candidates = _VERSION_CANDIDATES if version == "auto" else [version]

    for v in candidates:
        _stderr(f"[auto-detect] Trying ASCET {v} ...")
        s = ASCETStructureScannerAPI(version=v, debug=False)
        r = s.connect()
        if r.success:
            _stderr(f"[auto-detect] Success — connected to ASCET {v}")
            return s, v

    tried = ", ".join(candidates)
    _err("Could not connect to ASCET", f"Tried versions: {tried}")


def _build_tree_from_paths(items: list) -> dict:
    """
    Convert a list of ``{"path": str, "type": "esdl"|"diagram"}`` dicts into a
    nested JSON-serialisable tree.  Leaf nodes carry a ``class_type`` field so
    the VS Code extension can render different icons for ESDL vs Diagram.

    Tree shape::

        {
          "type": "root",
          "children": {
            "HAZ": {
              "type": "folder", "name": "HAZ",
              "children": {
                "VAF_Warning": {
                  "type": "class",
                  "class_type": "esdl",   # or "diagram"
                  "name": "VAF_Warning",
                  "path": "HAZ/VAF_Warning"
                }
              }
            }
          }
        }
    """
    root: dict = {"type": "root", "children": {}}
    for item in sorted(items, key=lambda x: x["path"]):
        raw      = item["path"]
        cls_type = item.get("type", "esdl")
        parts    = raw.replace("/", "\\").strip("\\").split("\\")
        node     = root
        for i, part in enumerate(parts):
            children = node["children"]
            if i == len(parts) - 1:
                fwd = raw.replace("\\", "/")
                children[part] = {
                    "type":       "class",
                    "class_type": cls_type,
                    "name":       part,
                    "path":       fwd,
                }
            else:
                if part not in children:
                    children[part] = {"type": "folder", "name": part, "children": {}}
                node = children[part]
    return root


# ---------------------------------------------------------------------------
# Diagram-type classifier (COM) — called for classes that have no calc code
# ---------------------------------------------------------------------------

def _classify_class_without_calc(class_obj) -> str:
    """
    Phân loại ESDL class không có Main.calc thành "diagram" hoặc "parameter".

    Logic chuẩn dựa theo block_diagram.py:
      - Block Diagram class: GetDiagram() trả về non-None (đây là API block diagram
        của ASCET COM, khác với GetDiagramWithName). Nếu có BD → "diagram".
      - ESDL class không có calc nhưng vẫn có Main diagram (empty/init only) → "esdl_no_calc".
        Tuy nhiên VS Code tree gộp chung vào "parameter" (không có gì để review).
      - Data/Parameter class: không có cả GetDiagram() lẫn Main diagram → "parameter".
    """
    if not class_obj:
        return "parameter"

    try:
        # ── Cách 1: GetDiagram() → API dành riêng cho Block Diagram class ────────
        # Đây là cách block_diagram.py dùng (xem ASCETDiagramSignalExtractor.get_diagram_signals)
        get_diagram = getattr(class_obj, "GetDiagram", None)
        if get_diagram and callable(get_diagram):
            try:
                diagram = get_diagram()
                if diagram is not None:
                    # Xác nhận thêm: BD có pins (input/output) hoặc có elements
                    has_pins = False
                    get_pins = getattr(diagram, "GetAllPins", None)
                    if get_pins and callable(get_pins):
                        try:
                            pins = get_pins()
                            has_pins = bool(pins and len(pins) > 0)
                        except Exception:
                            pass
                    # Dù có pins hay không, GetDiagram() non-None đã là dấu hiệu BD
                    return "diagram"
            except Exception:
                pass  # GetDiagram() raise exception → không phải BD

        # ── Cách 2: GetDiagramWithName("Main") nhưng không có calc ───────────────
        # Đây là ESDL class có Main diagram nhưng impl trống (init-only, parameter…)
        get_diag_named = getattr(class_obj, "GetDiagramWithName", None)
        if get_diag_named and callable(get_diag_named):
            try:
                main_diag = get_diag_named("Main")
                if main_diag is not None:
                    # Còn một lần kiểm tra nữa: nếu Main chứa connections/wires
                    # thì đây vẫn có thể là BD được cài vào ESDL shell
                    get_connections = getattr(main_diag, "GetAllConnections", None)
                    if get_connections and callable(get_connections):
                        try:
                            conns = get_connections()
                            if conns and len(conns) > 0:
                                return "diagram"
                        except Exception:
                            pass
                    # Main diagram tồn tại nhưng không có wires → parameter/data class
                    return "parameter"
            except Exception:
                pass

        # Không tìm thấy gì → parameter/data class
        return "parameter"

    except Exception as e:
        _stderr(f"[classify] Lỗi phân loại: {e}")
        return "parameter"

# ---------------------------------------------------------------------------
# AMD file resolver — maps a logical class path to a physical .amd file
# ---------------------------------------------------------------------------

def _find_amd_file(class_name: str) -> str:
    """
    Search the current working directory (and well-known export sub-folders)
    for a ``*.specification.amd`` or ``*.amd`` file whose base stem matches
    *class_name* (case-insensitive).

    Search priority:
      1. ``<cwd>/ASCET_Auto_Exports/**``
      2. ``<cwd>/exports/**``  /  ``<cwd>/Export/**``
      3. ``<cwd>/**``  (full recursive fallback)

    Returns the absolute path of the best match, or raises ``FileNotFoundError``.
    A ``.specification.amd`` match is preferred over a plain ``.amd`` match.
    """
    import os

    name_lower = class_name.lower()
    cwd        = os.getcwd()

    # Build ordered search roots (skip duplicates)
    search_roots: list = []
    for candidate in ("ASCET_Auto_Exports", "exports", "Export", "amd", ""):
        p = os.path.join(cwd, candidate) if candidate else cwd
        if os.path.isdir(p) and p not in search_roots:
            search_roots.append(p)

    spec_match = None
    amd_match  = None

    for root in search_roots:
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                fl = fname.lower()
                if not fl.endswith(".amd"):
                    continue
                # Strip known compound suffixes to get the base class name
                stem = fl
                for suffix in (".specification.amd", ".main.amd",
                                ".implementation.dp.amd", ".amd"):
                    if stem.endswith(suffix):
                        stem = stem[: -len(suffix)]
                        break
                if stem != name_lower:
                    continue
                full = os.path.join(dirpath, fname)
                if ".specification.amd" in fl and spec_match is None:
                    spec_match = full
                elif amd_match is None and ".specification.amd" not in fl \
                        and ".main.amd" not in fl \
                        and ".implementation.dp.amd" not in fl:
                    amd_match = full
            if spec_match:
                break   # found best possible match in this root
        if spec_match:
            break

    result = spec_match or amd_match
    if not result:
        raise FileNotFoundError(
            f"No .amd file found for class '{class_name}'. "
            f"Please export the diagram to disk first "
            f"(searched under: {cwd})."
        )
    return result


# ---------------------------------------------------------------------------
# Command: list_classes
# ---------------------------------------------------------------------------

def cmd_list_classes(version: str) -> None:
    """
    Scan the ASCET database and return all relevant classes with type info.

    Output shape::

        {
          "success": true,
          "data": [
            {"path": "HAZ/VAF_Warning",  "type": "esdl"},
            {"path": "CTRL/Engine_BD",   "type": "diagram"}
          ]
        }

    Classification logic:
      - ``esdl``    : IsClassESDL() == True  AND has Main.calc text method.
      - ``diagram`` : IsClassESDL() == True  but  NO Main.calc  (block diagram).
    """
    _stderr(f"[list_classes] version={version!r}")

    scanner, resolved_ver = _connect_scanner(version)

    # ── Pass 1: Scan ALL ESDL classes (no calc filter) — keep COM objects ───────
    # We do this first so scanner._all_classes holds every ESDL COM object.
    _stderr("[list_classes] Pass 1 — scanning all ESDL classes (no calc filter) ...")
    scan_all = scanner.scan_all_classes(require_calc=False, esdl_only=True)
    if not scan_all.success:
        _err("Database scan failed (pass 1)", scan_all.error or "")

    def _norm(p: str) -> str:
        return p.replace("\\", "/").strip("/")

    # Keep COM objects from this pass before the next scan overwrites them
    com_objects: dict = {_norm(k): v for k, v in scanner._all_classes.items()}
    all_paths: list = sorted({_norm(p) for p in scan_all.data.get("class_paths", [])})
    _stderr(f"[list_classes] Pass 1: {len(all_paths)} total ESDL classes.")

    # ── Pass 2: ESDL classes WITH Main.calc (text-code classes) ──────────────
    _stderr("[list_classes] Pass 2 — scanning ESDL classes with Main.calc ...")
    scan_calc = scanner.scan_all_classes(require_calc=True, esdl_only=True)
    if not scan_calc.success:
        _err("Database scan failed (pass 2)", scan_calc.error or "")

    esdl_paths: set = {_norm(p) for p in scan_calc.data.get("class_paths", [])}
    _stderr(f"[list_classes] Pass 2: {len(esdl_paths)} ESDL+calc classes.")

    # ── Pass 3: classify the no-calc classes via COM ──────────────────────────
    no_calc_paths = sorted(set(all_paths) - esdl_paths)
    _stderr(
        f"[list_classes] {len(no_calc_paths)} classes without calc need classification ..."
    )

    classified: dict = {}          # path → "diagram" | "parameter"
    diag_count = param_count = 0
    for norm in no_calc_paths:
        com = com_objects.get(norm)
        cls_type = _classify_class_without_calc(com) if com else "parameter"
        classified[norm] = cls_type
        if cls_type == "diagram":
            diag_count += 1
        else:
            param_count += 1

    _stderr(
        f"[list_classes] Classification done: "
        f"{diag_count} diagrams, {param_count} parameter/data classes."
    )

    result = [
        {"path": norm,
         "type": "esdl" if norm in esdl_paths else classified.get(norm, "parameter")}
        for norm in all_paths
    ]
    _stderr(f"[list_classes] Total: {len(result)} classes returned.")
    _ok(result)


# ---------------------------------------------------------------------------
# Command: list_tree
# ---------------------------------------------------------------------------

def cmd_list_tree(version: str) -> None:
    """
    Scan all ESDL classes and return a hierarchical folder tree.
    Leaf nodes carry ``class_type``: ``"esdl"`` or ``"diagram"``.

    Output shape: {"success": true, "data": {"type": "root", "children": {...}}}
    """
    _stderr(f"[list_tree] version={version!r}")

    scanner, resolved_ver = _connect_scanner(version)

    # Same two-pass classification as list_classes
    _stderr("[list_tree] Pass 1 — all ESDL classes (no calc filter) ...")
    scan_all = scanner.scan_all_classes(require_calc=False, esdl_only=True)
    if not scan_all.success:
        _err("Scan failed (pass 1)", scan_all.error or "")

    def _norm(p: str) -> str:
        return p.replace("\\", "/").strip("/")

    com_objects: dict = {_norm(k): v for k, v in scanner._all_classes.items()}
    all_paths: list = sorted({_norm(p) for p in scan_all.data.get("class_paths", [])})
    _stderr(f"[list_tree] Pass 1: {len(all_paths)} total ESDL classes.")

    _stderr("[list_tree] Pass 2 — ESDL classes with Main.calc ...")
    scan_calc = scanner.scan_all_classes(require_calc=True, esdl_only=True)
    if not scan_calc.success:
        _err("Scan failed (pass 2)", scan_calc.error or "")
    esdl_paths: set = {_norm(p) for p in scan_calc.data.get("class_paths", [])}
    _stderr(f"[list_tree] Pass 2: {len(esdl_paths)} ESDL+calc classes.")

    no_calc_paths = sorted(set(all_paths) - esdl_paths)
    _stderr(f"[list_tree] {len(no_calc_paths)} classes need classification ...")
    classified: dict = {
        norm: (_classify_class_without_calc(com_objects.get(norm))
               if com_objects.get(norm) else "parameter")
        for norm in no_calc_paths
    }

    items = [
        {"path": norm,
         "type": "esdl" if norm in esdl_paths else classified.get(norm, "parameter")}
        for norm in all_paths
    ]
    _stderr(f"[list_tree] Building tree for {len(items)} classes.")
    _ok(_build_tree_from_paths(items))


# ---------------------------------------------------------------------------
# Command: get_calc_code
# ---------------------------------------------------------------------------

def cmd_get_calc_code(path: str, version: str) -> None:
    """
    Extract Main.calc source code from an ASCET class via COM.
    """
    _stderr(f"[get_calc_code] path={path!r}  version={version!r}")

    scanner, resolved_ver = _connect_scanner(version)

    # Normalise path (accept '/' or '\\' as separator)
    normalised_path = path.replace("/", "\\").lstrip("\\")
    parts = normalised_path.split("\\")
    class_name = parts[-1]
    folder_path = "\\".join(parts[:-1])
    _stderr(f"[get_calc_code] Normalised: class={class_name!r}  folder={folder_path!r}")

    # Fetch class COM object
    try:
        class_obj = scanner.db.GetItemInFolder(class_name, folder_path)
    except Exception:
        _err("Failed to access class via COM", traceback.format_exc())

    if not class_obj:
        _err(
            "Class not found in database",
            f"class_path={normalised_path!r}  version={resolved_ver!r}",
        )

    _stderr("[get_calc_code] Extracting Main.calc ...")
    try:
        diagram = class_obj.GetDiagramWithName("Main")
        if not diagram:
            _err("No 'Main' diagram found", f"class_path={normalised_path!r}")

        method = diagram.GetMethod("calc")
        if not method:
            _err("No 'calc' method in Main diagram", f"class_path={normalised_path!r}")

        code = method.GetCode()
        if not code or not code.strip():
            _err("calc method is empty", f"class_path={normalised_path!r}")
    except SystemExit:
        raise
    except Exception:
        _err("Failed to extract calc code", traceback.format_exc())

    _ok(
        {
            "class_path": normalised_path,
            "class_name": class_name,
            "version": resolved_ver,
            "calc_code": code,
            "line_count": len(code.splitlines()),
        }
    )


# ---------------------------------------------------------------------------
# Diagram helper: convert DiagramNetlistExtractor output →
#                 DiagramRuleChecker diagram_data format
# ---------------------------------------------------------------------------

def _oid_map_to_diagram_data(connections: list, oid_map: dict) -> dict:
    """
    Build the ``diagram_data`` dict expected by ``DiagramRuleChecker`` from
    the raw ``(connections, oid_map)`` returned by
    ``DiagramNetlistExtractor.extract_connections()``.

    The oid_map uses ``port_name == "Self"`` to mark an OID that belongs to the
    block itself (not a sub-port); all other OIDs for the same block_name are
    individual input/output ports.
    """
    blocks_by_name: dict = {}

    for oid, info in oid_map.items():
        bn = info["block_name"]
        if bn not in blocks_by_name:
            blocks_by_name[bn] = {
                "id": None,
                "name": bn,
                "type": "",
                "position": {"x": 0, "y": 0},
                "ports": [],
            }
        if info["port_name"] == "Self":
            blocks_by_name[bn]["id"] = oid
        else:
            blocks_by_name[bn]["ports"].append({
                "id": oid,
                "name": info["port_name"],
                "tag": info.get("port_tag", ""),
                "is_visible": True,
            })

    # Assign a stable generated ID to any block that had no "Self" OID
    for bn, block in blocks_by_name.items():
        if block["id"] is None:
            block["id"] = f"_gen_{bn}"

    return {
        "blocks": list(blocks_by_name.values()),
        "connections": connections,
    }


# ---------------------------------------------------------------------------
# Command: check_diagram
# ---------------------------------------------------------------------------

def cmd_check_diagram(path: str, version: str) -> None:
    """
    Parse a Block Diagram (.amd) and return its connection netlist.
    This command does not require a live ASCET COM connection — it reads the XML file directly.

    Calls: src.diagrams.diagram_ai_review.DiagramNetlistExtractor
    """
    _stderr(f"[check_diagram] path={path!r}  version={version!r}")

    try:
        from src.diagrams.diagram_ai_review import DiagramNetlistExtractor, is_diagram_item
    except Exception as exc:
        _err("Import error: src.diagrams.diagram_ai_review", str(exc))

    if not is_diagram_item(path) and not path.endswith(".amd"):
        _stderr(
            "[check_diagram] Warning: path does not end in .amd — proceeding anyway."
        )

    _stderr("[check_diagram] Extracting connections …")
    try:
        connections, oid_map = DiagramNetlistExtractor.extract_connections(path)
    except FileNotFoundError as exc:
        _err("Diagram file not found", str(exc))
    except Exception:
        _err("Failed to extract diagram connections", traceback.format_exc())

    _ok(
        {
            "diagram_path": path,
            "version": version,
            "connection_count": len(connections),
            "connections": connections,
            "node_count": len(oid_map),
        }
    )


# ---------------------------------------------------------------------------
# Command: get_diagram_logic
# ---------------------------------------------------------------------------

def cmd_get_diagram_logic(path: str, version: str) -> None:
    """
    Full structural analysis of a Block Diagram (.amd):
      1. Parse the .amd XML → netlist (blocks + connections).
      2. Run all 9 DiagramRuleChecker rules.
      3. Map flagged issues to 1-based wire indices, split by category:
           calc  → Rule 9  (wrong calc/init execution order)   [purple]
           rule  → Rules 1,4,6,8 (name/type/positional mismatches) [orange]
           ai    → not triggered in CLI mode (always empty)    [red]

    Output shape::

        {
          "success": true,
          "data": {
            "diagram":      {"path": "...", "block_count": N, "connection_count": M},
            "errors":       {"calc": [1, 4], "rule": [5], "ai": []},
            "rule_details": [{"type": "...", "message": "...", ...}, ...],
            "stats":        {"high_severity": X, "medium_severity": Y, ...}
          }
        }
    """
    _stderr(f"[get_diagram_logic] path={path!r}  version={version!r}")

    # ── Step 1: Import modules ──────────────────────────────────────────────
    try:
        from src.diagrams.diagram_ai_review import DiagramNetlistExtractor
        from src.diagrams.rule_base import (
            run_diagram_rule_checks,
            map_rule_errors_to_wire_indices,
        )
    except Exception as exc:
        _err("Import error: src.diagrams", str(exc))

    # ── Step 2: Resolve physical .amd file path ─────────────────────────────
    # ``path`` may be a logical ASCET path (e.g. "HAZ/VAF_Warning") or already
    # a physical file path ending in .amd.  Resolve to physical before parsing.
    import os as _os
    physical_path = path
    if not _os.path.isfile(physical_path):
        _stderr(
            f"[get_diagram_logic] '{path}' is not a file on disk — "
            "searching for matching .amd file ..."
        )
        class_name = path.replace("\\", "/").rstrip("/").split("/")[-1]
        try:
            physical_path = _find_amd_file(class_name)
            _stderr(f"[get_diagram_logic] Resolved to: {physical_path}")
        except FileNotFoundError as exc:
            _err("Cannot resolve diagram file", str(exc))

    # ── Step 3: Extract connections + OID map ───────────────────────────────
    _stderr("[get_diagram_logic] Parsing diagram XML ...")
    try:
        connections, oid_map = DiagramNetlistExtractor.extract_connections(physical_path)
    except FileNotFoundError as exc:
        _err("Diagram file not found", str(exc))
    except Exception:
        _err("Failed to extract diagram connections", traceback.format_exc())

    _stderr(
        f"[get_diagram_logic] {len(connections)} connection(s), "
        f"{len(oid_map)} OID(s) found."
    )

    # ── Step 4: Convert to DiagramRuleChecker format ────────────────────────
    diagram_data = _oid_map_to_diagram_data(connections, oid_map)

    # ── Step 5: Build element dict (implType, scope, min/max) if available ──
    elem_dict: dict = {}
    if ".specification.amd" in physical_path:
        _stderr("[get_diagram_logic] Building element dict from specification ...")
        try:
            elem_dict = DiagramNetlistExtractor.build_element_dict(physical_path)
            _stderr(f"[get_diagram_logic] elem_dict: {len(elem_dict)} entries.")
        except Exception:
            _stderr(
                "[get_diagram_logic] Warning: could not build elem_dict — "
                "Rules 1/4/5 may produce no findings.\n"
                + traceback.format_exc()
            )

    # ── Step 6: Run rule checker (global_dict empty → XML rules silent) ─────
    _stderr("[get_diagram_logic] Running DiagramRuleChecker (9 rules) ...")
    rule_result = run_diagram_rule_checks(
        diagram_data, global_dict={}, elem_dict=elem_dict
    )
    rule_details = rule_result.get("rule_error_details", [])
    _stderr(
        f"[get_diagram_logic] Rule checker: {len(rule_details)} issue(s) found."
    )

    # ── Step 7: Partition errors by category and map to wire indices ─────────
    #   calc  → Rule 9 (sequence / execution-order errors)
    #   rule  → Rules 1, 4, 6, 8 (wires carrying mismatched signals)
    #   block → Rules 2, 3 (unused blocks — not wire-specific, kept in details only)
    CALC_RULE_KEYS = {"Rule_9_Wrong_Task_Assignment"}
    WIRE_RULE_KEYS = {
        "Rule_1_Mismatch_Return",
        "Rule_4_Mismatch_Imported",
        "Rule_6_Wrong_Wire_Mapping",
        "Rule_8_Wrong_Return_Local",
    }

    calc_details = [e for e in rule_details if e.get("rule_key") in CALC_RULE_KEYS]
    wire_details = [e for e in rule_details if e.get("rule_key") in WIRE_RULE_KEYS]

    calc_wire_indices = sorted(
        map_rule_errors_to_wire_indices(calc_details, diagram_data)
    )
    rule_wire_indices = sorted(
        map_rule_errors_to_wire_indices(wire_details, diagram_data)
    )

    _stderr(
        f"[get_diagram_logic] Defective wires — "
        f"calc={calc_wire_indices}  rule={rule_wire_indices}"
    )

    _ok({
        "diagram": {
            "path": physical_path,
            "block_count": len(diagram_data["blocks"]),
            "connection_count": len(connections),
        },
        "errors": {
            "calc": calc_wire_indices,
            "rule": rule_wire_indices,
            "ai":   [],   # AI review not triggered in CLI mode
        },
        "rule_details": rule_details,
        "stats": rule_result.get("rule_severity_stats", {}),
    })


# ---------------------------------------------------------------------------
# Command: render_diagram
# ---------------------------------------------------------------------------

def cmd_render_diagram(path: str, version: str, output: str, fmt: str = "png") -> None:
    """
    Parse a Block Diagram and render it to a PNG or SVG file.

    --path   logical ASCET path (e.g. HAZ/VAF_Warning) OR physical .amd path.
    --output optional absolute output path; defaults to system temp dir.
    --format png (default) or svg

    Output shape (PNG)::
        {"success": true, "data": {"image_path": "...", "class_name": "...",
                                   "format": "png"}}
    Output shape (SVG)::
        {"success": true, "data": {"content": "<svg>...</svg>", "class_name": "...",
                                   "format": "svg"}}
    """
    import os as _os
    import tempfile as _tmp

    _stderr(f"[render_diagram] path={path!r}  version={version!r}  format={fmt!r}")

    # ── Step 1: Resolve physical .amd path ──────────────────────────────────
    physical_path = path
    if not _os.path.isfile(physical_path):
        class_name = path.replace("\\", "/").rstrip("/").split("/")[-1]
        _stderr(f"[render_diagram] Searching .amd for '{class_name}' ...")
        try:
            physical_path = _find_amd_file(class_name)
            _stderr(f"[render_diagram] Resolved to: {physical_path}")
        except FileNotFoundError as exc:
            _err("Cannot resolve diagram file", str(exc))
    else:
        class_name = _os.path.basename(physical_path).split('.')[0]

    # ── Step 2: Import renderer / parser ────────────────────────────────────
    try:
        from src.diagrams.diagram_renderer import parse_diagram_xml, render_to_png
    except Exception as exc:
        _err("Import error: src.diagrams.diagram_renderer", str(exc))

    # ── Step 3: Parse diagram XML ────────────────────────────────────────────
    _stderr("[render_diagram] Parsing XML ...")
    try:
        diagram_data = parse_diagram_xml(physical_path)
    except FileNotFoundError as exc:
        _err("Diagram file not found", str(exc))
    except Exception:
        _err("Failed to parse diagram XML", traceback.format_exc())

    if not diagram_data:
        _err("No diagram specification found in file", f"path={physical_path!r}")

    _stderr(
        f"[render_diagram] Parsed {len(diagram_data['blocks'])} blocks, "
        f"{len(diagram_data['connections'])} connections."
    )

    # ── Step 4: Render ───────────────────────────────────────────────────────
    if fmt == "svg":
        _stderr("[render_diagram] Rendering SVG ...")
        try:
            svg_content = _render_diagram_to_svg(diagram_data, class_name)
        except Exception:
            _err("SVG render failed", traceback.format_exc())
        _stderr("[render_diagram] SVG done.")
        _ok({
            "content": svg_content,
            "class_name": class_name,
            "format": "svg",
            "block_count": len(diagram_data["blocks"]),
            "connection_count": len(diagram_data["connections"]),
        })
    else:
        # PNG via PySide6
        if not output:
            output = _os.path.join(_tmp.gettempdir(), f"ascet_diagram_{class_name}.png")
        _stderr(f"[render_diagram] Rendering PNG to: {output}")
        try:
            render_to_png(diagram_data, output)
        except RuntimeError as exc:
            _err("Render failed", str(exc))
        except Exception:
            _err("Unexpected render error", traceback.format_exc())
        _stderr("[render_diagram] PNG done.")
        _ok({
            "image_path": output,
            "class_name": class_name,
            "format": "png",
            "block_count": len(diagram_data["blocks"]),
            "connection_count": len(diagram_data["connections"]),
        })


# ---------------------------------------------------------------------------
# SVG renderer — lightweight, no PySide6 required
# ---------------------------------------------------------------------------

def _render_diagram_to_svg(diagram_data: dict, class_name: str) -> str:
    """
    Generate an SVG string from parsed diagram_data (same dict used by
    PySide6 PNG renderer).  Produces a clean, zoomable block diagram.

    Returns the SVG markup as a string.
    """
    blocks      = diagram_data.get("blocks", [])
    connections = diagram_data.get("connections", [])
    seq_calls   = diagram_data.get("sequence_calls", [])

    BLOCK_W     = 80
    BLOCK_H     = 30
    PORT_R      = 4
    PADDING     = 60
    FONT_SIZE   = 10
    SMALL_FONT  = 8

    # Build a quick OID→block lookup for connection drawing
    oid_to_block: dict = {}
    for b in blocks:
        oid_to_block[b["id"]] = b
        for p in b.get("ports", []):
            oid_to_block[p["id"]] = {"x": p["x"], "y": p["y"], "name": p["name"]}

    # Compute bounding box
    xs = [b["x"] for b in blocks] + [0]
    ys = [b["y"] for b in blocks] + [0]
    min_x, min_y = min(xs) - PADDING, min(ys) - PADDING
    max_x = max(b["x"] + BLOCK_W for b in blocks) + PADDING if blocks else PADDING * 2
    max_y = max(b["y"] + BLOCK_H for b in blocks) + PADDING if blocks else PADDING * 2

    width  = max_x - min_x
    height = max_y - min_y

    COLORS = {
        "ComplexElement":  ("#cce8f4", "#1a6e8c"),
        "SimpleElement":   ("#ffffff", "#333333"),
        "Literal":         ("#fffcdc", "#7a6a00"),
        "Operator":        ("#e8f0fe", "#1a3c8c"),
        "Junction":        ("#cccccc", "#333333"),
        "Connector":       ("#cccccc", "#333333"),
        "ConnectionPoint": ("#cccccc", "#333333"),
    }

    def tx(x): return x - min_x
    def ty(y): return y - min_y

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{int(width)}" height="{int(height)}" '
        f'viewBox="0 0 {int(width)} {int(height)}" '
        f'style="background:#1e1e2e;font-family:Consolas,monospace;">',
        f'<title>ASCET Diagram — {class_name}</title>',
    ]

    # ── Connections (draw first so they appear behind blocks) ──────────────
    for conn in connections:
        src_oid = conn.get("source_oid", "")
        tgt_oid = conn.get("target_oid", "")
        src = oid_to_block.get(src_oid)
        tgt = oid_to_block.get(tgt_oid)
        if not src or not tgt:
            continue
        sx, sy = tx(src["x"]), ty(src["y"])
        ex, ey = tx(tgt["x"]), ty(tgt["y"])
        bends = conn.get("bend_points", [])
        pts = [(sx, sy)] + [(tx(b["x"]), ty(b["y"])) for b in bends] + [(ex, ey)]
        path_d = "M " + " L ".join(f"{px:.1f},{py:.1f}" for (px, py) in pts)
        parts.append(
            f'<path d="{path_d}" stroke="#88aacc" stroke-width="1.5" '
            f'fill="none" marker-end="url(#arrow)"/>'
        )

    # Arrow marker definition
    parts.insert(1,
        '<defs>'
        '<marker id="arrow" markerWidth="6" markerHeight="6" '
        'refX="5" refY="3" orient="auto">'
        '<path d="M0,0 L6,3 L0,6 Z" fill="#88aacc"/>'
        '</marker>'
        '</defs>'
    )

    # ── Blocks ──────────────────────────────────────────────────────────────
    for block in blocks:
        bx, by     = tx(block["x"]), ty(block["y"])
        b_type     = block.get("type", "SimpleElement")
        b_name     = block.get("name", "")
        fill, text_col = COLORS.get(b_type, COLORS["SimpleElement"])

        is_tiny = b_type in ("Junction", "Connector", "ConnectionPoint")
        if is_tiny:
            parts.append(
                f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="4" '
                f'fill="{fill}" stroke="#666" stroke-width="1"/>'
            )
        else:
            safe_name = b_name.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            parts.append(
                f'<rect x="{bx:.1f}" y="{by - BLOCK_H/2:.1f}" '
                f'width="{BLOCK_W}" height="{BLOCK_H}" rx="4" '
                f'fill="{fill}" stroke="#555" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{bx + BLOCK_W/2:.1f}" y="{by + 4:.1f}" '
                f'text-anchor="middle" font-size="{FONT_SIZE}" fill="{text_col}">'
                f'{safe_name[:16]}'
                f"{'…' if len(safe_name) > 16 else ''}</text>"
            )
            # Ports
            for port in block.get("ports", []):
                if not port.get("is_visible", True):
                    continue
                px, py  = tx(port["x"]), ty(port["y"])
                p_name  = (port.get("name") or "").replace("&","&amp;")[:12]
                parts.append(
                    f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{PORT_R}" '
                    f'fill="#4488ff" stroke="#fff" stroke-width="0.5"/>'
                )
                if p_name:
                    parts.append(
                        f'<text x="{px:.1f}" y="{py - 6:.1f}" '
                        f'text-anchor="middle" font-size="{SMALL_FONT}" fill="#99ccff">'
                        f'{p_name}</text>'
                    )

    # ── Sequence call labels ─────────────────────────────────────────────────
    for seq in seq_calls:
        sx, sy = tx(seq["x"]), ty(seq["y"])
        safe_t = seq.get("text", "").replace("&","&amp;")
        parts.append(
            f'<text x="{sx:.1f}" y="{sy:.1f}" '
            f'font-size="{SMALL_FONT}" fill="#ffaa44" font-style="italic">'
            f'{safe_t}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Command: export_dsd
# ---------------------------------------------------------------------------

def cmd_export_dsd(class_path: str, output_dir: str, version: str) -> None:
    """
    Export ASCET implementation data (import parameters, localparameters, …)
    to an Excel workbook (.xlsx) using AscetDatabaseScanner from dsd_gen_tool.py.

    Strategy (minimize COM calls):
      1. Connect once via AscetDatabaseScanner.
      2. If class_path given → process that class only.
      3. Otherwise           → scan & export all classes.

    Output shape::
        {"success": true, "data": {"output_file": "path/to/result.xlsx",
                                   "exported_classes": N,
                                   "output_dir": "..."}}
    """
    import tempfile as _tmp
    import os as _os

    _stderr(f"[export_dsd] class_path={class_path!r}  version={version!r}")

    # Resolve output directory
    out_dir = output_dir.strip() or _os.path.join(_tmp.gettempdir(), "ascet_dsd")
    _os.makedirs(out_dir, exist_ok=True)

    # Import the scanner
    try:
        from src.tools.dsd_gen_tool import AscetDatabaseScanner
    except Exception as exc:
        _err("Import error: src.tools.dsd_gen_tool", str(exc))

    # Try to import the integrated scanner if available (richer export)
    IntegratedScanner = None
    try:
        from src.tools.dsd_gen_tool import IntegratedAscetScanner
        IntegratedScanner = IntegratedAscetScanner
    except ImportError:
        pass

    candidates = _VERSION_CANDIDATES if version == "auto" else [version]
    scanner    = None
    resolved_v = version

    for v in candidates:
        _stderr(f"[export_dsd] Trying ASCET {v} ...")
        s = AscetDatabaseScanner(version=v)
        if s.connect():
            scanner    = s
            resolved_v = v
            _stderr(f"[export_dsd] Connected to ASCET {v}")
            break

    if scanner is None:
        _err("Could not connect to ASCET", f"Tried: {', '.join(candidates)}")

    # ── Scan & filter ──────────────────────────────────────────────────────
    _stderr("[export_dsd] Scanning database structure ...")
    scanner.scan_database_structure_internal()

    target_classes: dict = {}
    if class_path:
        norm = class_path.replace("/", "\\").strip("\\")
        # find nearest key match
        for k in scanner.available_classes:
            if k.replace("/", "\\").strip("\\").endswith(norm) or \
               norm.endswith(k.replace("/", "\\").strip("\\")):
                target_classes[k] = scanner.available_classes[k]
                break
        if not target_classes:
            # Try exact lower-case match
            norm_low = norm.lower()
            for k, v in scanner.available_classes.items():
                if k.replace("/", "\\").strip("\\").lower() == norm_low:
                    target_classes[k] = v
                    break
        if not target_classes:
            _err("Class not found in ASCET database", f"class_path={class_path!r}")
    else:
        target_classes = scanner.available_classes

    _stderr(f"[export_dsd] Processing {len(target_classes)} class(es) ...")

    # ── Use IntegratedAscetScanner for richer export if available ──────────
    if IntegratedScanner and not class_path:
        _stderr("[export_dsd] Using IntegratedAscetScanner for full database export ...")
        integrated = IntegratedScanner(version=resolved_v)
        try:
            out_file = integrated.run_full_scan(output_dir=out_dir)
            if out_file:
                _ok({
                    "output_file": out_file,
                    "exported_classes": len(target_classes),
                    "output_dir": out_dir,
                })
        except Exception:
            _stderr("[export_dsd] IntegratedAscetScanner failed, falling back to AscetDatabaseScanner")

    # ── Fallback: process each class individually and write xlsx ───────────
    for k, cls_obj in target_classes.items():
        try:
            scanner.process_class_implementation(cls_obj, k)
        except Exception as exc:
            _stderr(f"[export_dsd] Warning: failed to process {k}: {exc}")

    if not scanner.all_implementations:
        _err("No implementation data found", "All classes may be parameter/data classes")

    # Write Excel
    try:
        import pandas as pd
        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = class_path.replace("/", "_").replace("\\", "_") if class_path else "all"
        xlsx_name = f"ASCET_DSD_{suffix}_{timestamp}.xlsx"
        out_file  = _os.path.join(out_dir, xlsx_name)

        rows = []
        for cls_k, impl_data in scanner.all_implementations.items():
            if isinstance(impl_data, dict):
                for elem_name, elem_info in impl_data.items():
                    if isinstance(elem_info, dict):
                        rows.append({
                            "class_path":    cls_k,
                            "element_name":  elem_name,
                            **{str(k): str(v) for k, v in elem_info.items()
                               if not isinstance(v, (dict, list))},
                        })
                    else:
                        rows.append({"class_path": cls_k, "element_name": elem_name,
                                     "value": str(elem_info)})
            else:
                rows.append({"class_path": cls_k, "data": str(impl_data)[:200]})

        df = pd.DataFrame(rows)
        df.to_excel(out_file, index=False)
        _stderr(f"[export_dsd] Written {len(rows)} rows → {out_file}")
        _ok({
            "output_file": out_file,
            "exported_classes": len(scanner.all_implementations),
            "output_dir": out_dir,
        })

    except ImportError:
        _err("pandas is required for Excel export", "pip install pandas openpyxl")
    except Exception:
        _err("Failed to write Excel file", traceback.format_exc())


# ---------------------------------------------------------------------------
# Command: analyze_code
# ---------------------------------------------------------------------------

# ESDL system prompt (shared between analyze_code and get_system_prompt)
_ESDL_SYSTEM_PROMPT = """\
You are an expert ASCET ESDL (Embedded Software Description Language) code assistant.
You help automotive software engineers write, review, modify, and debug ASCET calc methods.
ASCET uses a C-like procedural language (ESDL) inside its diagrams.

=== ESDL Language Rules ===
- Variables are declared by first assignment. No explicit type declarations.
- Standard C operators: +, -, *, /, %, ==, !=, <, >, <=, >=, &&, ||, !
- Control flow: if/else if/else, switch/case (with break), while, for
- Output variables are assigned by value: outVar = expression;
- No includes, headers, or extern declarations — only the method body.
- String literals are NOT supported in ESDL.
- Division: beware integer vs. float semantics. Use explicit casts if needed.

=== ASCET Architecture Conventions ===
- Signal naming: {direction}_{Location}_{Name}, e.g. sI_FL_WheelSpeed, sO_BrakeRequest
- Directions: sI_ (input), sO_ (output), sL_ (local), sP_ (parameter)
- Location codes: FL=front-left, FR=front-right, RL=rear-left, RR=rear-right
- Parameter types: ImportParam, LocalParam, ImportConst, LocalConst
- Block diagrams use ReturnPort, ArgumentPort, MessagePort for signal routing

=== Code Review Guidelines ===
- Check variable mapping consistency (position variables FL/FR/RL/RR)
- Verify return value variable names match port names
- Detect unused variables, redundant conditions, potential division-by-zero
- Flag uint32 overflow risks in multiplication/shift operations
- Identify incorrect task assignment (exec order vs. calc sequence)

When asked to review code, produce a structured JSON error list.
When asked to generate code, show the COMPLETE updated method body in ```esdl ... ``` blocks.
"""

_REVIEW_SYSTEM_PROMPT = """\
You are an ASCET code reviewer. Analyze the provided ESDL calc method for:
1. Variable mapping errors (position variables FL/FR/RL/RR incorrect assignment)
2. Return value variable name consistency (must match port/interface names)
3. Parameter mapping name consistency (local vs. imported parameter names)
4. Logic errors, unused variables, redundant conditions
5. Numeric overflow risks (uint32 multiplication, bit-shift operations)

Respond ONLY with a JSON object in this exact format:
{
  "errors": [
    {
      "type": "<error category>",
      "severity": "high|medium|low",
      "message": "<description>",
      "suggestion": "<how to fix>"
    }
  ],
  "summary": "<one-line summary>",
  "confidence": 0.0-1.0
}
"""


def cmd_analyze_code(
    path: str,
    version: str,
    mode: str,
    rag_enabled: bool,
    model: str,
    api_key: str,
    api_url: str,
    knowledge_dir: str,
) -> None:
    """
    Full code-review pipeline:
      1. Fetch calc code via COM (or from cache if already extracted).
      2. Run rule-based checks via RAGEnhancedCodeReviewer.
      3. (ai_rule mode) Send to LLM with optional RAG context.
      4. (rag_enabled) Retrieve historical cases via HistoricalCaseRetriever.
      5. Return structured JSON with errors + summary.

    Output shape::
        {"success": true, "data": {"class_path": "...", "errors": [...],
                                   "rag_hits": [...], "summary": "...",
                                   "mode": "...", "stats": {...}}}
    """
    _stderr(
        f"[analyze_code] path={path!r}  mode={mode!r}  "
        f"rag_enabled={rag_enabled}  version={version!r}"
    )

    # ── Step 1: Get calc code ──────────────────────────────────────────────
    _stderr("[analyze_code] Fetching calc code via COM ...")
    scanner, resolved_v = _connect_scanner(version)

    norm = path.replace("/", "\\").lstrip("\\")
    parts_list = norm.split("\\")
    c_name = parts_list[-1]
    f_path = "\\".join(parts_list[:-1])

    try:
        cls_obj = scanner.db.GetItemInFolder(c_name, f_path)
    except Exception:
        _err("Failed to access class via COM", traceback.format_exc())

    if not cls_obj:
        _err("Class not found in database", f"path={path!r}")

    calc_code = None
    try:
        diag = cls_obj.GetDiagramWithName("Main")
        if diag:
            meth = diag.GetMethod("calc")
            if meth:
                calc_code = meth.GetCode()
    except Exception:
        _stderr(f"[analyze_code] Warning: could not extract calc code: {traceback.format_exc()}")

    if not calc_code:
        _err("No calc code found for this class", f"path={path!r}")

    _stderr(f"[analyze_code] Got {len(calc_code.splitlines())} lines of calc code.")

    # ── Step 2: Rule-based checks ──────────────────────────────────────────
    rule_errors = []
    try:
        from src.agents.ascet_tool import RAGEnhancedCodeReviewer
        reviewer = RAGEnhancedCodeReviewer(
            api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
            api_url=api_url or "",
            model=model or "DeepSeek-r1-0528-fp16-671b",
        )
        _stderr("[analyze_code] Running rule-based checks ...")
        rule_errors = reviewer.run_basic_checks(calc_code)
        _stderr(f"[analyze_code] Rule checks: {len(rule_errors)} issue(s).")
    except Exception as exc:
        _stderr(f"[analyze_code] Warning: rule-based check failed: {exc}")

    # ── Step 3: RAG context retrieval ──────────────────────────────────────
    rag_hits = []
    if rag_enabled:
        try:
            from src.agents.ascet_tool import HistoricalCaseRetriever
            kb_dir = knowledge_dir or os.path.join(os.getcwd(), "knowledge_base")
            _stderr(f"[analyze_code] RAG query from {kb_dir!r} ...")
            retriever = HistoricalCaseRetriever(
                knowledge_base_dir=kb_dir,
                api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
                api_url=api_url or "",
            )
            rag_hits = retriever.retrieve_similar_cases(
                query=calc_code[:500],
                top_k=5,
            )
            _stderr(f"[analyze_code] RAG: {len(rag_hits)} hit(s).")
        except Exception as exc:
            _stderr(f"[analyze_code] Warning: RAG retrieval failed: {exc}")

    # ── Step 4: AI analysis (ai_rule mode only) ────────────────────────────
    ai_errors = []
    if mode == "ai_rule":
        if not (api_key or os.environ.get("OPENAI_API_KEY")):
            _stderr("[analyze_code] Warning: no API key — skipping AI analysis.")
        else:
            try:
                from src.agents.ascet_tool import RAGEnhancedAIReviewer
                ai_reviewer = RAGEnhancedAIReviewer(
                    api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
                    api_url=api_url or "",
                    model=model or "DeepSeek-r1-0528-fp16-671b",
                )
                _stderr("[analyze_code] Running AI analysis ...")
                ai_result = ai_reviewer.analyze_code(
                    calc_code=calc_code,
                    class_path=path,
                    rag_context=rag_hits,
                    system_prompt=_REVIEW_SYSTEM_PROMPT,
                )
                ai_errors = ai_result.get("errors", []) if isinstance(ai_result, dict) else []
                _stderr(f"[analyze_code] AI: {len(ai_errors)} error(s).")

                # ── Run arbitration to reduce false positives ────────────────────
                if ai_errors and rule_errors:
                    try:
                        from src.ai_core.ai_error_arbitrator import create_arbitrator
                        arbitrator = create_arbitrator(strategy="severity_based")
                        ai_errors  = arbitrator.arbitrate_errors(ai_errors, rule_errors)
                        _stderr(f"[analyze_code] Post-arbitration: {len(ai_errors)} confirmed error(s).")
                    except Exception as exc:
                        _stderr(f"[analyze_code] Warning: arbitration failed: {exc}")

            except Exception as exc:
                _stderr(f"[analyze_code] Warning: AI analysis failed: {exc}\n{traceback.format_exc()}")

    # ── Step 5: Combine & return ───────────────────────────────────────────
    all_errors = rule_errors + ai_errors
    high   = sum(1 for e in all_errors if str(e.get("severity","")).lower() in ("high","error","critical","3"))
    medium = sum(1 for e in all_errors if str(e.get("severity","")).lower() in ("medium","warning","2"))
    low    = sum(1 for e in all_errors if str(e.get("severity","")).lower() in ("low","info","1"))

    _ok({
        "class_path":  path,
        "class_name":  c_name,
        "version":     resolved_v,
        "mode":        mode,
        "calc_code":   calc_code,
        "line_count":  len(calc_code.splitlines()),
        "errors":      all_errors,
        "rule_errors": rule_errors,
        "ai_errors":   ai_errors,
        "rag_hits":    rag_hits,
        "summary":     f"{len(all_errors)} issue(s) found: {high} high, {medium} medium, {low} low",
        "stats": {
            "total":   len(all_errors),
            "high":    high,
            "medium":  medium,
            "low":     low,
            "rag_used": rag_enabled,
            "ai_used":  mode == "ai_rule",
        },
    })


# ---------------------------------------------------------------------------
# Command: get_system_prompt
# ---------------------------------------------------------------------------

def cmd_get_system_prompt(for_target: str) -> None:
    """
    Return the ESDL system prompt for the requested context.
    No ASCET COM connection required.

    Output shape::
        {"success": true, "data": {"system_prompt": "...", "for": "copilot"}}
    """
    _stderr(f"[get_system_prompt] for={for_target!r}")

    prompt_map = {
        "copilot": _ESDL_SYSTEM_PROMPT,
        "review":  _REVIEW_SYSTEM_PROMPT,
        "chat":    _ESDL_SYSTEM_PROMPT,
    }
    prompt = prompt_map.get(for_target, _ESDL_SYSTEM_PROMPT)
    _ok({"system_prompt": prompt, "for": for_target})


# ---------------------------------------------------------------------------
# Command: get_context
# ---------------------------------------------------------------------------

def cmd_get_context(path: str, version: str) -> None:
    """
    Return both the system prompt and the calc code for a class.
    This is the primary command VS Code calls before sending any LLM request.

    Output shape::
        {"success": true, "data": {"class_name": "...", "class_path": "...",
                                   "system_prompt": "...", "calc_code": "...",
                                   "warning": "..."}}
    """
    _stderr(f"[get_context] path={path!r}  version={version!r}")

    norm = path.replace("/", "\\").lstrip("\\")
    parts_list = norm.split("\\")
    c_name = parts_list[-1]
    f_path = "\\".join(parts_list[:-1])

    calc_code = None
    warning   = ""

    # Try to get calc code — non-fatal if it fails (diagram class, etc.)
    try:
        scanner, _v = _connect_scanner(version)
        cls_obj = scanner.db.GetItemInFolder(c_name, f_path)
        if cls_obj:
            diag = cls_obj.GetDiagramWithName("Main")
            if diag:
                meth = diag.GetMethod("calc")
                if meth:
                    calc_code = meth.GetCode()
            if not calc_code:
                warning = "This class has no Main.calc (may be a block-diagram or parameter class)."
        else:
            warning = f"Class '{path}' not found in ASCET database."
    except SystemExit:
        raise
    except Exception as exc:
        warning = f"ASCET COM error: {exc}"

    _ok({
        "class_name":    c_name,
        "class_path":    path,
        "system_prompt": _ESDL_SYSTEM_PROMPT,
        "calc_code":     calc_code,
        "warning":       warning,
    })


# ---------------------------------------------------------------------------
# Command: rag_query
# ---------------------------------------------------------------------------

def cmd_rag_query(
    query: str,
    top_k: int,
    knowledge_dir: str,
    api_key: str,
    api_url: str,
) -> None:
    """
    Query the RAG knowledge base for historical ASCET cases similar to *query*.

    Output shape::
        {"success": true, "data": {"results": [{"text": ..., "similarity": ...,
                                                 "source": ...}, ...],
                                   "query": "...", "top_k": N}}
    """
    _stderr(f"[rag_query] query={query[:60]!r}  top_k={top_k}")

    kb_dir = knowledge_dir.strip() or os.path.join(os.getcwd(), "knowledge_base")
    eff_api_key = api_key.strip() or os.environ.get("OPENAI_API_KEY", "")

    if not eff_api_key:
        _err(
            "API key required for RAG query",
            "Set --api_key or OPENAI_API_KEY environment variable",
        )

    try:
        from src.agents.ascet_tool import HistoricalCaseRetriever
    except Exception as exc:
        _err("Import error: src.agents.ascet_tool (HistoricalCaseRetriever)", str(exc))

    _stderr(f"[rag_query] Loading knowledge base from {kb_dir!r} ...")
    try:
        retriever = HistoricalCaseRetriever(
            knowledge_base_dir=kb_dir,
            api_key=eff_api_key,
            api_url=api_url or "",
        )
        results = retriever.retrieve_similar_cases(query=query, top_k=top_k)
    except Exception:
        _err("RAG query failed", traceback.format_exc())

    _stderr(f"[rag_query] {len(results)} result(s) retrieved.")
    _ok({"results": results, "query": query, "top_k": top_k})


# ---------------------------------------------------------------------------
# Command: get_class_info
# ---------------------------------------------------------------------------

def cmd_get_class_info(path: str, version: str) -> None:
    """
    Retrieve structural info about an ASCET class via COM without extracting
    full calc code.  Useful for quick type/signal inspection.

    Output shape::
        {"success": true, "data": {"class_path": "...", "class_name": "...",
                                   "class_type": "esdl|diagram|parameter",
                                   "signals": [...], "has_calc": bool}}
    """
    _stderr(f"[get_class_info] path={path!r}  version={version!r}")

    scanner, resolved_v = _connect_scanner(version)

    norm = path.replace("/", "\\").lstrip("\\")
    parts_list = norm.split("\\")
    c_name = parts_list[-1]
    f_path = "\\".join(parts_list[:-1])

    try:
        cls_obj = scanner.db.GetItemInFolder(c_name, f_path)
    except Exception:
        _err("COM access failed", traceback.format_exc())

    if not cls_obj:
        _err("Class not found", f"path={path!r}")

    has_calc  = False
    cls_type  = "parameter"
    signals   = []

    # Check for calc method
    try:
        diag = cls_obj.GetDiagramWithName("Main")
        if diag:
            meth = diag.GetMethod("calc")
            has_calc = bool(meth and meth.GetCode())
    except Exception:
        pass

    # Classify
    cls_type = _classify_class_without_calc(cls_obj) if not has_calc else "esdl"

    # Collect signals via GetAllModelElements
    try:
        get_elems = getattr(cls_obj, "GetAllModelElements", None)
        if callable(get_elems):
            elems = get_elems()
        else:
            elems = get_elems
        if elems:
            for elem in elems:
                try:
                    e_name = elem.GetName() if hasattr(elem, "GetName") else str(elem)
                    e_type = type(elem).__name__
                    signals.append({"name": e_name, "type": e_type})
                except Exception:
                    pass
    except Exception:
        pass

    _ok({
        "class_path": path,
        "class_name": c_name,
        "version":    resolved_v,
        "class_type": cls_type,
        "has_calc":   has_calc,
        "signals":    signals[:100],   # cap at 100 for JSON size
        "signal_count": len(signals),
    })

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ascet_cli",
        description="ASCET Copilot CLI — outputs JSON on stdout",
    )
    # Global --version flag: placed BEFORE the subcommand on the CLI.
    # e.g.:  ascet_cli.exe --version 6.1.5 list_classes
    parser.add_argument(
        "--version",
        default="auto",
        dest="version",
        help=(
            'ASCET COM version string, e.g. 6.1.5. '
            'Use "auto" (default) to try common versions automatically. '
            'This is a GLOBAL flag — place it before the subcommand.'
        ),
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # --- list_classes (no --path required) --------------------------------
    sub.add_parser(
        "list_classes",
        help="Scan ASCET database and return all ESDL/diagram class paths as a JSON array",
    )

    # --- list_tree --------------------------------------------------------
    sub.add_parser(
        "list_tree",
        help="Scan ASCET database and return ESDL classes as a hierarchical folder tree",
    )

    # --- get_calc_code ----------------------------------------------------
    p_calc = sub.add_parser(
        "get_calc_code",
        help="Extract Main.calc source code from an ASCET class",
    )
    p_calc.add_argument("--path", required=True, help="ASCET class path, e.g. HAZ/VAF_Warning")

    # --- check_diagram ----------------------------------------------------
    p_diag = sub.add_parser(
        "check_diagram",
        help="Parse an ASCET block-diagram (.amd) and return its netlist",
    )
    p_diag.add_argument("--path", required=True, help="Absolute or relative path to the .amd file")

    # --- get_diagram_logic ------------------------------------------------
    p_logic = sub.add_parser(
        "get_diagram_logic",
        help="Parse a block-diagram, run 9 structural rules, return defective wire indices",
    )
    p_logic.add_argument("--path", required=True, help="Path to .amd or .specification.amd file")

    # --- render_diagram ---------------------------------------------------
    p_render = sub.add_parser(
        "render_diagram",
        help="Parse a block-diagram and render it to PNG or SVG.",
    )
    p_render.add_argument("--path", required=True, help="Logical ASCET class path or .amd path")
    p_render.add_argument("--output", default="", help="Output file path (default: system temp)")
    p_render.add_argument(
        "--format", default="png", choices=["png", "svg"],
        help="Output format: png (default) or svg",
    )

    # --- export_dsd -------------------------------------------------------
    p_dsd = sub.add_parser(
        "export_dsd",
        help="Export ASCET implementation data to Excel (DSD format).",
    )
    p_dsd.add_argument(
        "--class_path", default="",
        help="Optional: limit export to a single class, e.g. HAZ/VAF_Warning",
    )
    p_dsd.add_argument(
        "--output_dir", default="",
        help="Directory for the output .xlsx file (default: system temp)",
    )

    # --- analyze_code -----------------------------------------------------
    p_ai = sub.add_parser(
        "analyze_code",
        help="Run the full AI review pipeline on an ASCET ESDL class.",
    )
    p_ai.add_argument("--path", required=True, help="ASCET class path, e.g. HAZ/VAF_Warning")
    p_ai.add_argument(
        "--mode", default="direct", choices=["direct", "ai_rule"],
        help="Review mode: direct = rule check only, ai_rule = rule + AI analysis",
    )
    p_ai.add_argument(
        "--rag_enabled", action="store_true",
        help="Enable RAG context retrieval for the AI analysis step",
    )
    p_ai.add_argument(
        "--model", default="",
        help="AI model name override (leave empty to use default from config)",
    )
    p_ai.add_argument(
        "--api_key", default="",
        help="API key (falls back to OPENAI_API_KEY env var)",
    )
    p_ai.add_argument(
        "--api_url", default="",
        help="API endpoint URL override",
    )
    p_ai.add_argument(
        "--knowledge_dir", default="",
        help="Directory containing the RAG knowledge-base files (embeddings / FAISS index)",
    )

    # --- get_system_prompt ------------------------------------------------
    p_sysprompt = sub.add_parser(
        "get_system_prompt",
        help="Return the ESDL system prompt used for LLM chat context.",
    )
    p_sysprompt.add_argument(
        "--for", default="copilot",
        choices=["copilot", "review", "chat"],
        dest="for_target",
        help="Prompt variant to return (default: copilot)",
    )

    # --- get_context ------------------------------------------------------
    p_ctx = sub.add_parser(
        "get_context",
        help=(
            "Return the combined system prompt + calc code for a class. "
            "Used by VS Code to build LLM message context."
        ),
    )
    p_ctx.add_argument("--path", required=True, help="ASCET class path")

    # --- rag_query --------------------------------------------------------
    p_rag = sub.add_parser(
        "rag_query",
        help="Query the RAG knowledge base for relevant historical cases.",
    )
    p_rag.add_argument("--query", required=True, help="Query string")
    p_rag.add_argument("--top_k", type=int, default=5, help="Number of results (default: 5)")
    p_rag.add_argument("--knowledge_dir", default="", help="Path to knowledge-base directory")
    p_rag.add_argument("--api_key", default="", help="Embedding API key")
    p_rag.add_argument("--api_url", default="", help="Embedding API endpoint URL")

    # --- get_class_info ---------------------------------------------------
    p_info = sub.add_parser(
        "get_class_info",
        help="Get structural info (signals, type, BD summary) for an ASCET class via COM.",
    )
    p_info.add_argument("--path", required=True, help="ASCET class path")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "list_classes":
            cmd_list_classes(version=args.version)
        elif args.command == "list_tree":
            cmd_list_tree(version=args.version)
        elif args.command == "get_calc_code":
            cmd_get_calc_code(path=args.path, version=args.version)
        elif args.command == "check_diagram":
            cmd_check_diagram(path=args.path, version=args.version)
        elif args.command == "get_diagram_logic":
            cmd_get_diagram_logic(path=args.path, version=args.version)
        elif args.command == "render_diagram":
            cmd_render_diagram(
                path=args.path,
                version=args.version,
                output=args.output,
                fmt=args.format,
            )
        elif args.command == "export_dsd":
            cmd_export_dsd(
                class_path=args.class_path,
                output_dir=args.output_dir,
                version=args.version,
            )
        elif args.command == "analyze_code":
            cmd_analyze_code(
                path=args.path,
                version=args.version,
                mode=args.mode,
                rag_enabled=args.rag_enabled,
                model=args.model,
                api_key=args.api_key,
                api_url=args.api_url,
                knowledge_dir=args.knowledge_dir,
            )
        elif args.command == "get_system_prompt":
            cmd_get_system_prompt(for_target=args.for_target)
        elif args.command == "get_context":
            cmd_get_context(path=args.path, version=args.version)
        elif args.command == "rag_query":
            cmd_rag_query(
                query=args.query,
                top_k=args.top_k,
                knowledge_dir=args.knowledge_dir,
                api_key=args.api_key,
                api_url=args.api_url,
            )
        elif args.command == "get_class_info":
            cmd_get_class_info(path=args.path, version=args.version)
        else:
            _err(f"Unknown command: {args.command!r}")
    except SystemExit:
        raise  # let _ok / _err control the exit code
    except Exception:
        _err("Unexpected error", traceback.format_exc())


if __name__ == "__main__":
    main()
