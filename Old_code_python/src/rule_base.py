#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from difflib import SequenceMatcher
import math

def build_global_dict(root_folder: str) -> Dict[str, Dict[str, Any]]:
    global_dict: Dict[str, Dict[str, Any]] = {}

    def _get_or_create(name: str) -> Dict[str, Any]:
        if name not in global_dict:
            global_dict[name] = {"BasicType": None, "ImplType": None, "Min": None, "Max": None, "ImplMin": None, "ImplMax": None, "Value": None, "Scope": None, "SourceFile": set()}
        return global_dict[name]

    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if not (filename.endswith(".amd") or filename.endswith(".xml")): continue
            filepath = os.path.join(dirpath, filename)
            try:
                tree = ET.parse(filepath)
                for elem in tree.getroot().iter():
                    name = (elem.get("name") or elem.get("elementName") or elem.get("dataName"))
                    if not name or name in {"default", "Data", "Impl", "Main"}: continue
                    cfg = _get_or_create(name)
                    cfg["SourceFile"].add(filename)
                    tag = elem.tag.split("}")[-1]

                    if tag in ("Element", "Argument", "MethodPort", "Message", "ReturnPort"):
                        attrs = elem.find(".//ElementAttributes")
                        if attrs is not None and attrs.get("basicModelType"): cfg["BasicType"] = attrs.get("basicModelType")
                        elif elem.get("type"): cfg["BasicType"] = elem.get("type")
                        prim = elem.find(".//PrimitiveAttributes")
                        if prim is not None and prim.get("scope"): cfg["Scope"] = prim.get("scope")
                    elif tag == "ElementImplementation":
                        num_impl = elem.find(".//NumericImplementation")
                        if num_impl is not None:
                            if num_impl.get("implType"): cfg["ImplType"] = num_impl.get("implType")
                            phys_int = num_impl.find(".//PhysicalInterval")
                            if phys_int is not None:
                                if phys_int.get("min"): cfg["Min"] = phys_int.get("min")
                                if phys_int.get("max"): cfg["Max"] = phys_int.get("max")
                            impl_int = num_impl.find(".//ImplementationInterval")
                            if impl_int is not None:
                                if impl_int.get("min"): cfg["ImplMin"] = impl_int.get("min")
                                if impl_int.get("max"): cfg["ImplMax"] = impl_int.get("max")
                    if not cfg["ImplType"] and elem.get("implType"): cfg["ImplType"] = elem.get("implType")
            except Exception:
                # Fallback: ET parse failed (e.g. malformed XML / encoding issues in .amd).
                # Use regex like test.ipynb does — it is more tolerant of broken markup.
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as _f:
                        raw = _f.read()
                    _elem_name_re = re.compile(r'elementName="([^"]+)"')
                    _phys_re = re.compile(r'<PhysicalInterval\s+min="([^"]+)"\s+max="([^"]+)"')
                    _impl_re = re.compile(r'<ImplementationInterval\s+min="([^"]+)"\s+max="([^"]+)"')
                    _block_re = re.compile(r'<ElementImplementation(.*?)</ElementImplementation>', re.DOTALL)
                    for block in _block_re.findall(raw):
                        nm = _elem_name_re.search(block)
                        if not nm: continue
                        bname = nm.group(1)
                        if bname in {"default", "Data", "Impl", "Main"}: continue
                        cfg = _get_or_create(bname)
                        cfg["SourceFile"].add(filename)
                        pm = _phys_re.search(block)
                        if pm:
                            cfg["Min"] = pm.group(1)
                            cfg["Max"] = pm.group(2)
                        im = _impl_re.search(block)
                        if im:
                            cfg["ImplMin"] = im.group(1)
                            cfg["ImplMax"] = im.group(2)
                except Exception:
                    pass

    for cfg in global_dict.values():
        if cfg.get("BasicType") == "log" and not cfg.get("ImplType"): cfg["ImplType"] = "boolean"
        cfg["SourceFile"] = sorted(cfg["SourceFile"])
    return global_dict


# =====================================================================
# POSITIONAL SUFFIX PATTERNS - FIX TÀI LANH BỎ X, Y, Z
# =====================================================================
_POSITION_GROUPS = {
    "FL": "FrontLeft",  "FR": "FrontRight",
    "RL": "RearLeft",   "RR": "RearRight",
    "Front": "Front",   "Rear": "Rear",
    "Left": "Left",     "Right": "Right",
    "Lh": "Left",       "Rh": "Right",
    # Đã xóa X, Y, Z để không bắt nhầm các biến vector vật lý như a_Veh_x
}

_POS_PATTERN = re.compile(
    r'[_]?(' + '|'.join(sorted(_POSITION_GROUPS.keys(), key=len, reverse=True)) + r')(?=[_\b]|$)',
    re.IGNORECASE,
)

def _extract_position_tag(name: str) -> Optional[str]:
    """Extract a positional suffix from a signal name (FL, FR, RL, RR, Left, Right, ...)."""
    m = _POS_PATTERN.search(name)
    if not m:
        return None
    return _POSITION_GROUPS.get(m.group(1), m.group(1))

def _strip_position(name: str) -> str:
    """Remove the positional suffix and return the base name."""
    return _POS_PATTERN.sub('', name).rstrip('_').strip()


class DiagramRuleChecker:
    # =================================================================
    # DEFINITION TABLE FOR 9 RULES (based on define2.csv)
    # =================================================================
    RULE_IDS = {
        # --- Rule-based (1–5) ---
        "Rule_1_Mismatch_Return":       "Implementation mismatch between Local variable and return method",
        "Rule_2_Unused_Local":          "Unused Local Constant Parameter",
        "Rule_3_Unused_Imported":       "Unreferenced imported parameters",
        "Rule_4_Mismatch_Imported":     "Implementation mismatch between local and imported parameter",
        "Rule_5_Signal_Range":          "Signal Range Issue",
        # --- AI / Heuristic (6–9) ---
        "Rule_6_Wrong_Wire_Mapping":    "Wrong mapping between connections",
        "Rule_7_Wrong_Imported_Local":  "Wrong mapping between imported parameters and local parameters",
        "Rule_8_Wrong_Return_Local":    "Wrong mapping between return method and local variable",
        "Rule_9_Wrong_Task_Assignment": "Wrong calc/init task assignment",
    }

    SEVERITY_MAP = {
        "Rule_1_Mismatch_Return":       "ERROR",
        "Rule_2_Unused_Local":          "Warning",
        "Rule_3_Unused_Imported":       "Warning",
        "Rule_4_Mismatch_Imported":     "Warning",
        "Rule_5_Signal_Range":          "ERROR",
        "Rule_6_Wrong_Wire_Mapping":    "Warning",
        "Rule_7_Wrong_Imported_Local":  "Warning",
        "Rule_8_Wrong_Return_Local":    "Warning",
        "Rule_9_Wrong_Task_Assignment": "Warning",
    }

    # Check method: Rule based / AI / Heuristic / Not Implemented
    METHOD_MAP = {
        "Rule_1_Mismatch_Return":       "Rule based",       # Needs XML implType
        "Rule_2_Unused_Local":          "Rule based",       # Works with topology
        "Rule_3_Unused_Imported":       "Rule based",       # Works with topology
        "Rule_4_Mismatch_Imported":     "Rule based",       # Needs XML implType
        "Rule_5_Signal_Range":          "Rule based",       # Needs XML min/max
        "Rule_6_Wrong_Wire_Mapping":    "Heuristic",        # Positional suffix matching
        "Rule_7_Wrong_Imported_Local":  "Not Implemented",  # Stub (needs AI)
        "Rule_8_Wrong_Return_Local":    "Heuristic",        # Name similarity
        "Rule_9_Wrong_Task_Assignment": "Heuristic",        # Spatial proximity (degraded)
    }

    # Data requirements per rule — documents what each rule needs to produce findings
    DATA_REQUIREMENTS = {
        "Rule_1_Mismatch_Return":       "XML implType from global_dict (ElementImplementation)",
        "Rule_2_Unused_Local":          "Topology only (blocks + connections)",
        "Rule_3_Unused_Imported":       "Topology only (blocks + connections)",
        "Rule_4_Mismatch_Imported":     "XML implType from global_dict (ElementImplementation)",
        "Rule_5_Signal_Range":          "XML PhysicalInterval min/max from global_dict",
        "Rule_6_Wrong_Wire_Mapping":    "Topology only (connection names)",
        "Rule_7_Wrong_Imported_Local":  "AI model for semantic analysis",
        "Rule_8_Wrong_Return_Local":    "Topology only (connection names)",
        "Rule_9_Wrong_Task_Assignment": "XML spatial positions (x,y) OR explicit block-name in sequence calls",
    }

    # Feasibility with All.txt only (no XML)
    FEASIBILITY = {
        "Rule_1_Mismatch_Return":       "LIMITED",          # Silent skip without XML
        "Rule_2_Unused_Local":          "FULL",
        "Rule_3_Unused_Imported":       "FULL",
        "Rule_4_Mismatch_Imported":     "LIMITED",          # Silent skip without XML
        "Rule_5_Signal_Range":          "NOT_FEASIBLE",     # No min/max in topology
        "Rule_6_Wrong_Wire_Mapping":    "FULL",
        "Rule_7_Wrong_Imported_Local":  "NOT_IMPLEMENTED",  # Stub
        "Rule_8_Wrong_Return_Local":    "FULL",
        "Rule_9_Wrong_Task_Assignment": "DEGRADED",         # Spatial heuristic unreliable
    }

    def __init__(self, diagram_data: Dict[str, Any], global_dict: Dict[str, Any], elem_dict: Optional[Dict[str, Any]] = None):
        self.diagram_data = diagram_data
        self.global_dict = self._normalize(global_dict)
        self.elem_dict: Dict[str, Any] = elem_dict or {}
        self._errors: List[Dict[str, Any]] = []

    def run(self) -> List[Dict[str, Any]]:
        self._errors = []
        self._skipped_rules: List[str] = []
        connections, ports_map, blocks_map, connected_oids = self._resolve_connections()

        # --- FULL feasibility: work with topology data alone ---
        self._rule2_unused_local(connected_oids)
        self._rule3_unused_imported(connected_oids)
        self._rule6_wrong_wire_mapping(connections)
        self._rule8_wrong_return_local(connections)

        # --- LIMITED feasibility: require XML metadata (implType, scope, min/max) ---
        # These silently produce 0 findings when global_dict lacks the needed fields.
        self._rule1_mismatch_return(connections)
        self._rule4_mismatch_imported(connections)
        self._rule5_signal_range(connections)

        # --- DEGRADED / NOT IMPLEMENTED ---
        self._rule7_wrong_imported_local(connections)    # Stub — needs AI
        self._rule9_wrong_task_assignment(connections)   # Spatial proximity heuristic

        return self._errors

    def get_stats(self) -> Dict[str, Any]:
        high = sum(1 for e in self._errors if e.get("severity") in ("ERROR", "high"))
        medium = sum(1 for e in self._errors if e.get("severity") in ("Warning", "medium"))
        return {
            "high_severity": high,
            "medium_severity": medium,
            "low_severity": 0,
            "has_high_severity": high > 0,
            "skipped_rules": self._skipped_rules,
        }

    # =================================================================
    # CLEANUP AND LOOKUP HELPERS
    # =================================================================
    def _clean_name(self, name: str) -> str:
        if not name: return ""
        name = name.replace("[Local]", "").replace("[Imported]", "").replace("[Constant]", "").strip()
        if name.startswith("return / "): name = name[len("return / "):]
        return name

    def _lookup_range(self, raw_name: str) -> Optional[tuple]:
        """Return (f_phys_min, f_phys_max, f_impl_min, f_impl_max) or None if no data."""
        name = self._clean_name(raw_name)
        cfg_e = self.elem_dict.get(name, {})
        cfg_g = self.global_dict.get(name, {})
        phys_min = cfg_e.get("min") if cfg_e.get("min") is not None else cfg_g.get("Min")
        phys_max = cfg_e.get("max") if cfg_e.get("max") is not None else cfg_g.get("Max")
        impl_min = cfg_e.get("implMin") if cfg_e.get("implMin") is not None else cfg_g.get("ImplMin")
        impl_max = cfg_e.get("implMax") if cfg_e.get("implMax") is not None else cfg_g.get("ImplMax")
        if all(v is None for v in (phys_min, phys_max, impl_min, impl_max)):
            return None
        try:
            return (
                float(phys_min) if phys_min is not None else None,
                float(phys_max) if phys_max is not None else None,
                float(impl_min) if impl_min is not None else None,
                float(impl_max) if impl_max is not None else None,
            )
        except (ValueError, TypeError):
            return None

    def _lookup_impl(self, raw_name: str) -> Optional[str]:
        name = self._clean_name(raw_name)
        cfg = self.elem_dict.get(name, {})
        if cfg.get("implType"): return cfg["implType"]
        cfg = self.global_dict.get(name, {})
        if cfg.get("ImplType"): return cfg["ImplType"]
        if cfg.get("BasicType") == "log": return "boolean"
        return None

    def _lookup_scope(self, raw_name: str) -> Optional[str]:
        name = self._clean_name(raw_name)
        cfg = self.elem_dict.get(name, {})
        if cfg.get("scope"): return cfg["scope"]
        cfg = self.global_dict.get(name, {})
        return cfg.get("Scope")

    @staticmethod
    def _normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
        norm = {}
        for k, v in raw.items():
            nv = dict(v)
            if nv.get("BasicType") == "log" and not nv.get("ImplType"): nv["ImplType"] = "boolean"
            norm[k] = nv
        return norm

    def _resolve_connections(self):
        blocks_map = {}
        ports_map = {}
        return_port_block_oids = set()

        for block in self.diagram_data.get("blocks", []):
            b_id = block["id"]
            b_name = block.get("name", "")
            blocks_map[b_id] = b_name
            if b_name.startswith("return / "): return_port_block_oids.add(b_id)
            for port in block.get("ports", []):
                ports_map[port["id"]] = {"name": port.get("name", ""), "tag": port.get("tag", "")}

        connected_oids = set()
        connections = []
        for conn in self.diagram_data.get("connections", []):
            src_id, tgt_id = conn["source_oid"], conn["target_oid"]
            src_info, tgt_info = ports_map.get(src_id) or {}, ports_map.get(tgt_id) or {}
            
            src_name = src_info.get("name") or blocks_map.get(src_id)
            tgt_name = tgt_info.get("name") or blocks_map.get(tgt_id)
            
            # =========================================================
            # GUARD RAIL: filter out ghost or invalid wires.
            # =========================================================
            if not src_name or not tgt_name:
                continue
                
            connected_oids.add(src_id)
            connected_oids.add(tgt_id)

            tgt_tag = tgt_info.get("tag", "")
            if not tgt_tag and tgt_id in return_port_block_oids: 
                tgt_tag = "ReturnPort"
                
            connections.append({
                "source_name": src_name,
                "target_name": tgt_name,
                "target_tag": tgt_tag,
            })
            
        return connections, ports_map, blocks_map, connected_oids

    def _record(self, rule_key: str, message: str):
        sev = self.SEVERITY_MAP[rule_key]
        self._errors.append({
            "type": self.RULE_IDS[rule_key],
            "message": message,
            "severity": "high" if sev == "ERROR" else "medium",
            "rule_key": rule_key,
            "original_severity": sev,
        })

    def _rule1_mismatch_return(self, connections: List[Dict]) -> None:
        for conn in connections:
            if conn["target_tag"] != "ReturnPort" and "return" not in self._clean_name(conn["target_name"]).lower(): continue
            src_name, tgt_name = conn["source_name"], conn["target_name"]
            src_impl, tgt_impl = self._lookup_impl(src_name), self._lookup_impl(tgt_name)
            
            if src_impl and tgt_impl and src_impl.lower() != tgt_impl.lower():
                self._record("Rule_1_Mismatch_Return", f"Source [{self._clean_name(src_name)}] ({src_impl}) -> ReturnPort [{self._clean_name(tgt_name)}] ({tgt_impl}) - Data configuration mismatch")

    def _rule2_unused_local(self, connected_oids: Set) -> None:
        for block in self.diagram_data.get("blocks", []):
            b_type = block.get("type", "")
            raw_name = block.get("name", "")
            clean_name = self._clean_name(raw_name)

            if "Complex" in b_type or "Function" in b_type or "Method" in b_type: continue
            if not clean_name or "return" in clean_name.lower(): continue

            block_oids = {block.get("id")}
            for p in block.get("ports", []):
                block_oids.add(p.get("id"))

            if not block_oids.intersection(connected_oids):
                scope = self._lookup_scope(clean_name)
                if scope == "imported" or "[Imported]" in raw_name:
                    continue 
                else:
                    self._record("Rule_2_Unused_Local", f"Local/Constant variable [{clean_name}] is present on the diagram but unused (not wired).")

    def _rule3_unused_imported(self, connected_oids: Set) -> None:
        for block in self.diagram_data.get("blocks", []):
            b_type = block.get("type", "")
            raw_name = block.get("name", "")
            clean_name = self._clean_name(raw_name)

            if "Complex" in b_type or "Function" in b_type or "Method" in b_type: continue
            if not clean_name or "return" in clean_name.lower(): continue

            block_oids = {block.get("id")}
            for p in block.get("ports", []):
                block_oids.add(p.get("id"))

            if not block_oids.intersection(connected_oids):
                scope = self._lookup_scope(clean_name)
                if scope == "imported" or "[Imported]" in raw_name:
                    self._record("Rule_3_Unused_Imported", f"Imported variable [{clean_name}] is present on the diagram but unused (not wired).")

    def _rule4_mismatch_imported(self, connections: List[Dict]) -> None:
        for conn in connections:
            if conn["target_tag"] == "ReturnPort": continue
            src_name, tgt_name = conn["source_name"], conn["target_name"]
            scope = self._lookup_scope(src_name)
            
            if scope != "imported" and "[Imported]" not in src_name: continue
            src_impl, tgt_impl = self._lookup_impl(src_name), self._lookup_impl(tgt_name)
            if src_impl and tgt_impl and src_impl.lower() != tgt_impl.lower():
                self._record("Rule_4_Mismatch_Imported", f"Imported [{self._clean_name(src_name)}] ({src_impl}) -> Local [{self._clean_name(tgt_name)}] ({tgt_impl}) - Mapping configuration mismatch")

    def _rule5_signal_range(self, connections: List[Dict] = None) -> None:
        # Guard: this rule needs PhysicalInterval / ImplementationInterval min/max from XML.
        # With All.txt-only data (topology), global_dict has no Min/Max fields → 0 findings.
        has_range_data = any(
            cfg.get("Min") is not None or cfg.get("Max") is not None
            or cfg.get("ImplMin") is not None or cfg.get("ImplMax") is not None
            for cfg in self.global_dict.values()
        ) or any(
            cfg.get("min") is not None or cfg.get("max") is not None
            or cfg.get("implMin") is not None or cfg.get("implMax") is not None
            for cfg in self.elem_dict.values()
        )
        if not has_range_data:
            self._skipped_rules.append("Rule_5_Signal_Range: No min/max data available (need XML PhysicalInterval / ImplementationInterval)")
            return

        for name, cfg in self.global_dict.items():
            phys_min, phys_max = cfg.get("Min"), cfg.get("Max")
            impl_min, impl_max = cfg.get("ImplMin"), cfg.get("ImplMax")

            # --- Check 1: Physical range invalid (max <= min) ---
            f_phys_min = f_phys_max = None
            if phys_min is not None and phys_max is not None:
                try:
                    f_phys_min, f_phys_max = float(phys_min), float(phys_max)
                    if f_phys_max <= f_phys_min:
                        self._record(
                            "Rule_5_Signal_Range",
                            f"Signal '{name}' has invalid Physical range: Max ({f_phys_max}) <= Min ({f_phys_min})"
                        )
                except (ValueError, TypeError):
                    f_phys_min = f_phys_max = None

            # # --- Check 2: Implementation range invalid (max <= min) ---
            f_impl_min = f_impl_max = None
            # if impl_min is not None and impl_max is not None:
            #     try:
            #         f_impl_min, f_impl_max = float(impl_min), float(impl_max)
            #         if f_impl_max <= f_impl_min:
            #             self._record(
            #                 "Rule_5_Signal_Range",
            #                 f"Signal '{name}' has invalid Implementation range: Max ({f_impl_max}) <= Min ({f_impl_min})"
            #             )
            #     except (ValueError, TypeError):
            #         f_impl_min = f_impl_max = None

            # --- Check 3 (case khó): span mismatch or sign inconsistency ---
            if f_phys_min is not None and f_phys_max is not None and f_impl_min is not None and f_impl_max is not None:
                phys_span = f_phys_max - f_phys_min
                impl_span = f_impl_max - f_impl_min
                if phys_span > 0 and impl_span <= 0:
                    self._record(
                        "Rule_5_Signal_Range",
                        f"Signal '{name}' Physical range [{f_phys_min}, {f_phys_max}] is valid but "
                        f"Implementation range [{f_impl_min}, {f_impl_max}] has zero/invalid span"
                    )
                elif impl_span > 0 and phys_span <= 0:
                    self._record(
                        "Rule_5_Signal_Range",
                        f"Signal '{name}' Implementation range [{f_impl_min}, {f_impl_max}] is valid but "
                        f"Physical range [{f_phys_min}, {f_phys_max}] has zero/invalid span"
                    )
                # Sign-consistency check: Physical covers negative but Implementation does not (or vice versa)
                elif phys_span > 0 and impl_span > 0:
                    phys_negative = f_phys_min < 0
                    impl_negative = f_impl_min < 0
                    if phys_negative and not impl_negative:
                        self._record(
                            "Rule_5_Signal_Range",
                            f"Signal '{name}' Physical range [{f_phys_min}, {f_phys_max}] covers negative values "
                            f"but Implementation range [{f_impl_min}, {f_impl_max}] is entirely non-negative — "
                            f"Implementation cannot represent Physical negative values"
                        )

        # --- Check 4: Wire-level range mismatch (connected signals must have matching ranges) ---
        if not connections:
            return
        checked_pairs: Set[Tuple[str, str]] = set()
        for conn in connections:
            if conn.get("target_tag") == "ReturnPort":
                continue
            src_name = self._clean_name(conn["source_name"])
            tgt_name = self._clean_name(conn["target_name"])
            if not src_name or not tgt_name or src_name == tgt_name:
                continue
            pair_key = (min(src_name, tgt_name), max(src_name, tgt_name))
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            src_rng = self._lookup_range(src_name)
            tgt_rng = self._lookup_range(tgt_name)
            if src_rng is None or tgt_rng is None:
                continue

            s_fp_min, s_fp_max, s_fi_min, s_fi_max = src_rng
            t_fp_min, t_fp_max, t_fi_min, t_fi_max = tgt_rng

            # Physical range mismatch across wire
            if (s_fp_min is not None and s_fp_max is not None
                    and t_fp_min is not None and t_fp_max is not None):
                if s_fp_min != t_fp_min or s_fp_max != t_fp_max:
                    self._record(
                        "Rule_5_Signal_Range",
                        f"Wire range mismatch: [{src_name}] (Phys:[{s_fp_min}, {s_fp_max}]) "
                        f"→ [{tgt_name}] (Phys:[{t_fp_min}, {t_fp_max}]) — Physical ranges do not match"
                    )

            # Implementation range mismatch across wire
            # if (s_fi_min is not None and s_fi_max is not None
            #         and t_fi_min is not None and t_fi_max is not None):
            #     if s_fi_min != t_fi_min or s_fi_max != t_fi_max:
            #         self._record(
            #             "Rule_5_Signal_Range",
            #             f"Wire range mismatch: [{src_name}] (Impl:[{s_fi_min}, {s_fi_max}]) "
            #            k f"→ [{tgt_name}] (Impl:[{t_fi_min}, {t_fi_max}]) — Implementation ranges do not match"
            #         )

    def _rule6_wrong_wire_mapping(self, connections: List[Dict]) -> None:
        for conn in connections:
            src_raw = conn["source_name"]
            tgt_raw = conn["target_name"]
            src_name = self._clean_name(src_raw)
            tgt_name = self._clean_name(tgt_raw)

            src_pos = _extract_position_tag(src_name)
            tgt_pos = _extract_position_tag(tgt_name)

            if src_pos and tgt_pos and src_pos != tgt_pos:
                src_base = _strip_position(src_name)
                tgt_base = _strip_position(tgt_name)
                if self._name_similarity(src_base, tgt_base) > 0.5:
                    self._record(
                        "Rule_6_Wrong_Wire_Mapping",
                        f"Suspected positional wiring mismatch: [{src_name}] ({src_pos}) -> [{tgt_name}] ({tgt_pos}) - Positional suffixes do not match"
                    )
    @staticmethod
    # def _name_similarity(a: str, b: str) -> float:
    #     if not a or not b:
    #         return 0.0
            
    #     a_lower = a.lower()
    #     b_lower = b.lower()
        
    #     # 1. Trùng khớp hoàn toàn
    #     if a_lower == b_lower:
    #         return 1.0
            
    #     # 2. Kiểm tra chuỗi con (Xử lý trường hợp có thêm Prefix/Suffix)
    #     # Ví dụ: b="b_veh_x" nằm hoàn toàn trong a="m_a_b_veh_x"
    #     longer, shorter = (a_lower, b_lower) if len(a_lower) > len(b_lower) else (b_lower, a_lower)
    #     if shorter in longer:
    #         # Đảm bảo nó là một block logic (đứng sau dấu _ hoặc ở đầu/cuối chuỗi)
    #         if longer.endswith(f"_{shorter}") or longer.startswith(f"{shorter}_") or f"_{shorter}_" in longer:
    #             return 0.95  # Gần như chắc chắn là cùng một biến
    #         return 0.85      # Chứa chuỗi nhưng không cách bởi dấu _ (Vẫn cho điểm cao)

    #     # 3. Phân tích theo tập hợp từ (Token Matching)
    #     # Xử lý trường hợp bị đổi thứ tự: "veh_speed_x" vs "speed_veh_x"
    #     tokens_a = set(t for t in a_lower.split('_') if t)
    #     tokens_b = set(t for t in b_lower.split('_') if t)
        
    #     jaccard_ratio = 0.0
    #     if tokens_a and tokens_b:
    #         intersection = tokens_a.intersection(tokens_b)
    #         min_len = min(len(tokens_a), len(tokens_b))
            
    #         # Nếu toàn bộ token của chuỗi ngắn đều nằm trong chuỗi dài
    #         if len(intersection) == min_len and min_len > 0:
    #             # Trừ một chút điểm cho số lượng token thừa
    #             penalty = (max(len(tokens_a), len(tokens_b)) - min_len) * 0.05
    #             subset_score = max(0.80, 0.95 - penalty)
    #             return subset_score
                
    #         # Jaccard Similarity (Tỷ lệ giao thoa / Tổng số từ duy nhất)
    #         jaccard_ratio = len(intersection) / len(tokens_a.union(tokens_b))
            
    #     # 4. Fallback về SequenceMatcher (Để bắt các lỗi typo nhỏ, vd: "speed" vs "sped")
    #     from difflib import SequenceMatcher
    #     seq_ratio = SequenceMatcher(None, a_lower, b_lower).ratio()
        
    #     # Lấy điểm cao nhất trong các chiến lược
    #     return max(jaccard_ratio, seq_ratio)
    def _name_similarity(a: str, b: str) -> float:
        return 1.0
    def _rule7_wrong_imported_local(self, connections: List[Dict]) -> None:
        # NOT IMPLEMENTED — requires AI semantic similarity analysis.
        # Connection names alone are insufficient; need AI to detect subtle mapping errors
        # (e.g., similar-but-wrong imported-to-local parameter assignments).
        self._skipped_rules.append("Rule_7_Wrong_Imported_Local: Not implemented (requires AI semantic analysis)")

    def _rule8_wrong_return_local(self, connections: List[Dict]) -> None:
        for conn in connections:
            tgt_name = conn["target_name"]
            if conn["target_tag"] != "ReturnPort" and "return" not in tgt_name.lower():
                continue

            src_name = self._clean_name(conn["source_name"])
            ret_name = self._clean_name(tgt_name)

            if not src_name or not ret_name:
                continue

            similarity = self._name_similarity(src_name, ret_name)

            if similarity < 0.25 and len(ret_name) > 3 and len(src_name) > 3:
                self._record(
                    "Rule_8_Wrong_Return_Local",
                    f"Return [{ret_name}] receives data from [{src_name}] - Names are not similar (similarity={similarity:.0%}), possible wrong return variable"
                )

    # =================================================================
    # RULE 9 - Wrong calc/init task assignment
    # Fix bằng thuật toán Heuristic Không Gian (Spatial Proximity)
    # Map Sequence Call vào Block gần nhất dựa trên tọa độ (x, y)
    # =================================================================
    def _rule9_wrong_task_assignment(self, connections: List[Dict]) -> None:
        seq_calls = self.diagram_data.get("sequence_calls", [])
        blocks = self.diagram_data.get("blocks", [])
        if not seq_calls or not blocks:
            self._skipped_rules.append("Rule_9_Wrong_Task_Assignment: No sequence_calls or blocks data available")
            return

        # DEGRADED: Uses spatial proximity heuristic (Euclidean distance) to guess
        # which block a SequenceCall belongs to. This is unreliable because:
        # - All.txt sequence calls lack block-name mapping (e.g., "01. /12/ .calc")
        # - Spatial proximity can mismap when blocks are close together
        # Ideal fix: export sequence calls with block names like [HAZ_ABS_Warning].calc

        # 1. Xây dựng Mapping: Tên Block -> Thứ tự chạy (dựa vào khoảng cách gần nhất)
        block_order: Dict[str, int] = {}
        
        for idx, seq in enumerate(seq_calls):
            pos = seq.get("position", {})
            sx, sy = pos.get("x", 0), pos.get("y", 0)
            
            nearest_block_name = ""
            min_dist = float('inf')
            
            for block in blocks:
                b_type = block.get("type", "")
                # Bỏ qua các block thuần hiển thị dây/literal
                if b_type in ["Literal", "Junction", "Connector", "ConnectionPoint"]:
                    continue
                    
                b_pos = block.get("position", {})
                bx, by = b_pos.get("x", 0), b_pos.get("y", 0)
                
                # Tính khoảng cách Euclidean
                dist = math.hypot(sx - bx, sy - by)
                
                if dist < min_dist:
                    min_dist = dist
                    nearest_block_name = block.get("name", "")
            
            if nearest_block_name:
                # Cập nhật thứ tự chạy cho block (lấy thứ tự cao nhất nếu có nhiều call như init -> calc)
                block_order[nearest_block_name] = idx

        # 2. Xây dựng Dependency: Producer -> Consumer từ Connections
        port_to_block: Dict[str, str] = {}
        for block in blocks:
            b_name = block.get("name", "")
            for port in block.get("ports", []):
                port_to_block[port.get("id", "")] = b_name

        producer_consumer: List[Tuple[str, str]] = []
        for conn in self.diagram_data.get("connections", []):
            src_block = port_to_block.get(conn.get("source_oid", ""), "")
            tgt_block = port_to_block.get(conn.get("target_oid", ""), "")
            
            if src_block and tgt_block and src_block != tgt_block:
                # Chỉ check logic cho các function/complex blocks
                src_is_complex = any(b.get("name") == src_block and ("Complex" in b.get("type", "") or "Function" in b.get("type", "")) for b in blocks)
                tgt_is_complex = any(b.get("name") == tgt_block and ("Complex" in b.get("type", "") or "Function" in b.get("type", "")) for b in blocks)
                
                if src_is_complex and tgt_is_complex:
                    producer_consumer.append((src_block, tgt_block))

        # 3. Validate logic: Thằng sản xuất data (producer) PHẢI chạy TRƯỚC thằng tiêu thụ (consumer)
        for producer, consumer in set(producer_consumer): # Dùng set() để loại bỏ các dây trùng lặp
            prod_order = block_order.get(producer)
            cons_order = block_order.get(consumer)

            if prod_order is not None and cons_order is not None:
                if prod_order > cons_order:
                    self._record(
                        "Rule_9_Wrong_Task_Assignment",
                        f"Block [{producer}] (sequence #{prod_order+1}) provides data to [{consumer}] "
                        f"(sequence #{cons_order+1}) but is called later - Incorrect execution order"
                    )
def run_diagram_rule_checks(diagram_data: Dict[str, Any], global_dict: Dict[str, Any], elem_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    checker = DiagramRuleChecker(diagram_data, global_dict, elem_dict=elem_dict)
    details = checker.run()
    stats = checker.get_stats()
    return {"rule_errors": len(details), "rule_error_details": details, "rule_severity_stats": stats}

def map_rule_errors_to_wire_indices(
    rule_error_details: List[Dict[str, Any]],
    diagram_data: Dict[str, Any],
) -> Set[int]:
    WIRE_RULES = {
        "Rule_1_Mismatch_Return",
        "Rule_4_Mismatch_Imported",
        "Rule_6_Wrong_Wire_Mapping",
        "Rule_8_Wrong_Return_Local",
    }

    bracket_pattern = re.compile(r'\[([^\]]+)\]')
    error_signal_pairs: List[Tuple[str, str]] = []

    for err in rule_error_details:
        rule_key = err.get("rule_key", "")
        if rule_key not in WIRE_RULES:
            continue
        msg = err.get("message", "")
        names = bracket_pattern.findall(msg)
        if len(names) >= 2:
            error_signal_pairs.append((names[0].strip(), names[1].strip()))
        elif len(names) == 1:
            error_signal_pairs.append((names[0].strip(), ""))

    if not error_signal_pairs:
        return set()

    blocks_map: Dict[str, str] = {}
    ports_map: Dict[str, Dict[str, str]] = {}
    for block in diagram_data.get("blocks", []):
        b_name = block.get("name", "")
        blocks_map[block["id"]] = b_name
        for port in block.get("ports", []):
            ports_map[port["id"]] = {
                "name": port.get("name", ""),
                "block_name": b_name,
            }

    result: Set[int] = set()
    connections = diagram_data.get("connections", [])

    for wire_idx, conn in enumerate(connections, 1):
        src_oid = conn.get("source_oid", "")
        tgt_oid = conn.get("target_oid", "")

        src_info = ports_map.get(src_oid, {})
        tgt_info = ports_map.get(tgt_oid, {})
        src_name = src_info.get("name") or src_info.get("block_name") or blocks_map.get(src_oid, "")
        tgt_name = tgt_info.get("name") or tgt_info.get("block_name") or blocks_map.get(tgt_oid, "")
        src_block = src_info.get("block_name", blocks_map.get(src_oid, ""))
        tgt_block = tgt_info.get("block_name", blocks_map.get(tgt_oid, ""))

        def _clean(n):
            n = n.replace("[Local]", "").replace("[Imported]", "").replace("[Constant]", "").strip()
            if n.startswith("return / "):
                n = n[len("return / "):]
            return n

        wire_names = {_clean(src_name), _clean(tgt_name), _clean(src_block), _clean(tgt_block)}
        wire_names.discard("")

        for err_src, err_tgt in error_signal_pairs:
            if err_src in wire_names and (not err_tgt or err_tgt in wire_names):
                result.add(wire_idx)
                break

    return result