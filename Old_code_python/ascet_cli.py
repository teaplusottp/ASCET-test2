#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ascet_cli.py — ASCET Copilot Command-Line Router
=================================================
Usage:
    python ascet_cli.py list_classes
    python ascet_cli.py get_calc_code --path "HAZ/VAF_Warning"
    python ascet_cli.py get_calc_code --path "HAZ/VAF_Warning" --version 6.1.5
    python ascet_cli.py check_diagram  --path "HAZ/VAF_Warning.amd"
    python ascet_cli.py render_diagram --path "HAZ/VAF_Warning"

Rules:
  - ALL output (success or error) is a single JSON line on stdout.
  - Debug / progress text goes to sys.stderr only, never stdout.
  - --version defaults to "auto" (tries common versions until one connects).
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
    if _base not in sys.path:
        _base = sys._MEIPASS          # type: ignore[attr-defined]

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

def cmd_render_diagram(path: str, version: str, output: str) -> None:
    """
    Parse a Block Diagram and render it to a PNG file.

    --path   logical ASCET path (e.g. HAZ/VAF_Warning) OR physical .amd path.
    --output optional absolute PNG output path; defaults to system temp dir.

    Output shape::

        {"success": true, "data": {"image_path": "C:/tmp/ascet_diagram_VAF_Warning.png",
                                   "class_name": "VAF_Warning"}}
    """
    import os as _os
    import tempfile as _tmp

    _stderr(f"[render_diagram] path={path!r}  version={version!r}")

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

    # ── Step 2: Import renderer ──────────────────────────────────────────────
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

    # ── Step 4: Determine output PNG path ───────────────────────────────────
    if not output:
        output = _os.path.join(_tmp.gettempdir(), f"ascet_diagram_{class_name}.png")

    # ── Step 5: Render to PNG ────────────────────────────────────────────────
    _stderr(f"[render_diagram] Rendering to PNG: {output}")
    try:
        render_to_png(diagram_data, output)
    except RuntimeError as exc:
        _err("Render failed", str(exc))
    except Exception:
        _err("Unexpected render error", traceback.format_exc())

    _stderr("[render_diagram] Done.")
    _ok({"image_path": output, "class_name": class_name})


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ascet_cli",
        description="ASCET Copilot CLI — outputs JSON on stdout",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Shared --version option (reused across sub-commands)
    def add_version(p):
        p.add_argument(
            "--version",
            default="auto",
            help=(
                'ASCET COM version string, e.g. 6.1.5. '
                'Use "auto" (default) to try common versions automatically.'
            ),
        )

    # --- list_classes (no --path required) --------------------------------
    p_list = sub.add_parser(
        "list_classes",
        help="Scan ASCET database and return ESDL class paths (with calc) as a JSON array",
    )
    add_version(p_list)

    # --- list_tree --------------------------------------------------------
    p_tree = sub.add_parser(
        "list_tree",
        help="Scan ASCET database and return ESDL classes as a hierarchical folder tree",
    )
    add_version(p_tree)

    # --- get_calc_code ----------------------------------------------------
    p_calc = sub.add_parser(
        "get_calc_code",
        help="Extract Main.calc source code from an ASCET class",
    )
    p_calc.add_argument(
        "--path",
        required=True,
        help="ASCET class path, e.g. HAZ/VAF_Warning",
    )
    add_version(p_calc)

    # --- check_diagram ----------------------------------------------------
    p_diag = sub.add_parser(
        "check_diagram",
        help="Parse an ASCET block-diagram (.amd) and return its netlist",
    )
    p_diag.add_argument(
        "--path",
        required=True,
        help="Absolute or relative path to the .amd diagram file",
    )
    add_version(p_diag)

    # --- get_diagram_logic ------------------------------------------------
    p_logic = sub.add_parser(
        "get_diagram_logic",
        help=(
            "Parse an ASCET block-diagram (.amd), run all 9 structural rules, "
            "and return defective wire indices grouped by category "
            "(calc / rule / ai)."
        ),
    )
    p_logic.add_argument(
        "--path",
        required=True,
        help="Absolute or relative path to the .amd (or .specification.amd) diagram file",
    )
    add_version(p_logic)

    # --- render_diagram ---------------------------------------------------
    p_render = sub.add_parser(
        "render_diagram",
        help="Parse a block-diagram and render it to a PNG file.",
    )
    p_render.add_argument(
        "--path",
        required=True,
        help="Logical ASCET class path or .amd file path",
    )
    p_render.add_argument(
        "--output",
        default="",
        help="Output PNG path (default: system temp folder)",
    )
    add_version(p_render)

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
            cmd_render_diagram(path=args.path, version=args.version, output=args.output)
        else:
            _err(f"Unknown command: {args.command!r}")
    except SystemExit:
        raise  # let _ok / _err control the exit code
    except Exception:
        _err("Unexpected error", traceback.format_exc())


if __name__ == "__main__":
    main()
