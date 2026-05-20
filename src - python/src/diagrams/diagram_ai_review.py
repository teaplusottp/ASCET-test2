#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagram AI Review Flow
======================

Dedicated review flow for diagram queue items (.amd).
- Parse diagram connections into netlist text
- Send netlist text to AI for review
- Return result in the same shape used by class review pipeline
"""

import os
import re
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Set

from src.ai_core.model_config import create_model_config
from src.ai_core.response_handler import create_response_handler
from src.ai_core.ai_error_arbitrator import extract_ai_errors


from urllib.parse import urlparse

def get_proxies_for_url(url: str):
    host = urlparse(url).hostname or ""
    
    # Internal network (10.x.x.x)
    if host.startswith("10."):
        return {"http": None, "https": None}
    
    # Otherwise, use system proxy (if any)
    return None

def is_diagram_item(class_path: Optional[str]) -> bool:
    """Check whether queue item is a diagram path."""
    if not class_path:
        return False
    normalized = str(class_path).strip().lower()
    return normalized.endswith(".amd") or ".specification.amd" in normalized


class DiagramNetlistExtractor:
    """Extract connection netlist text from ASCET .amd XML."""

    @staticmethod
    def _strip_namespaces(root: ET.Element) -> None:
        for el in root.iter():
            if '}' in el.tag:
                el.tag = el.tag.split('}', 1)[1]

    @staticmethod
    def extract_connections(xml_file_path: str) -> Tuple[List[Dict[str, str]], Dict[str, Dict[str, str]]]:
        if not os.path.exists(xml_file_path):
            raise FileNotFoundError(f"Diagram file not found: {xml_file_path}")

        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        DiagramNetlistExtractor._strip_namespaces(root)

        oid_map: Dict[str, Dict[str, str]] = {}

        # Step 1: scan Layout for global/external ports
        layout_elem = root.find('./Layout')
        if layout_elem is not None:
            for node in layout_elem.iter():
                oid = node.attrib.get('graphicOID')
                if oid and oid != "-1":
                    name = node.attrib.get('name', node.attrib.get('elementName', node.attrib.get('methodName', node.tag)))
                    oid_map[oid] = {
                        "block_name": "[External Port]" if node.tag == 'ExternalPort' else "[Global Port]",
                        "port_name": name
                    }

        # Step 2: scan specification and build OID -> block/port mapping
        main_spec = root.find('.//Specification[@name="Main"]')
        if main_spec is None:
            main_spec = root.find('.//Specification')
        if main_spec is None:
            return [], oid_map

        for diagram_element in main_spec.findall('.//DiagramElement'):
            for block in diagram_element:
                if block.tag in ['Connection', 'Comment', 'Note', 'SequenceCall']:
                    continue

                b_type = block.tag
                DIAGRAM_PORTS = ['ReturnPort', 'ArgumentPort', 'MessagePort', 'Parameter', 'TriggerPort', 'SelectorPort']

                if b_type in DIAGRAM_PORTS:
                    b_name = (block.attrib.get('elementName') or block.attrib.get('methodName') or
                              block.attrib.get('name') or b_type)
                    if b_type == 'ReturnPort':
                        b_name = f"return / {b_name}"
                elif b_type == 'Literal':
                    b_name = block.attrib.get('value', 'constant')
                elif b_type == 'Operator':
                    b_name = block.attrib.get('operator', block.attrib.get('kind', block.attrib.get('type', 'operator')))
                elif b_type in ['Junction', 'Connector', 'ConnectionPoint']:
                    b_name = f"Connection_Point_{block.attrib.get('graphicOID', 'N/A')}"
                else:
                    b_name = block.attrib.get('elementName', block.attrib.get('name', block.attrib.get('methodName', block.tag)))

                # Build a local parent map for this block subtree (for port name resolution)
                block_parent_map = {c: p for p in block.iter() for c in p}

                for node in block.iter():
                    oid = node.attrib.get('graphicOID')
                    if oid and oid != "-1":
                        if node == block:
                            oid_map[oid] = {"block_name": b_name, "port_name": "Self", "port_tag": ""}
                        else:
                            # Robust name: direct attrs → parent MethodPort → grandparent
                            p_name = (node.get('name') or node.get('elementName') or
                                      node.get('methodName') or node.get('instanceName'))
                            if not p_name:
                                node_parent = block_parent_map.get(node)
                                if node_parent is not None:
                                    if node_parent.tag == 'MethodPort':
                                        p_name = node_parent.get('methodName') or node_parent.get('name')
                                    if not p_name:
                                        grand_el = block_parent_map.get(node_parent)
                                        if grand_el is not None:
                                            p_name = (grand_el.get('elementName') or grand_el.get('instanceName') or
                                                      grand_el.get('methodName') or grand_el.get('ClassName'))
                            if not p_name:
                                p_name = node.tag
                            if node.attrib.get('nameVisibility', 'true').lower() == 'false':
                                p_name = node.tag
                            oid_map[oid] = {"block_name": b_name, "port_name": p_name, "port_tag": node.tag}

        # Step 3: parse connections (dedupe by source/target/bendpoints)
        parsed_conns = set()
        connections: List[Dict[str, str]] = []
        for conn in main_spec.findall('.//Connection'):
            start_elem = conn.find('.//Start')
            end_elem = conn.find('.//End')
            if start_elem is None or end_elem is None:
                continue

            src_oid = start_elem.attrib.get('graphicOID')
            tgt_oid = end_elem.attrib.get('graphicOID')
            if not src_oid or not tgt_oid:
                continue

            bends = tuple((float(b.attrib.get('x', 0)), float(b.attrib.get('y', 0))) for b in conn.findall('.//BendPoint'))
            c_key = (src_oid, tgt_oid, bends)
            if c_key in parsed_conns:
                continue

            parsed_conns.add(c_key)
            connections.append({"source_oid": src_oid, "target_oid": tgt_oid})

        return connections, oid_map

    @staticmethod
    def build_element_dict(spec_amd_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Read the sibling .main.amd and .implementation.dp.amd next to the given
        .specification.amd and build a name → {scope, implType, min, max} dict.
        Scope values from ASCET: 'imported', 'local', 'constant'.
        """
        result: Dict[str, Dict[str, Any]] = {}
        try:
            from pathlib import Path as _Path
            spec = _Path(spec_amd_path)
            stem = spec.name
            if stem.endswith(".specification.amd"):
                base = stem[: -len(".specification.amd")]
            else:
                base = stem.rsplit(".", 1)[0]
            d = spec.parent

            def get_or_create(name: str) -> Dict[str, Any]:
                if name not in result:
                    result[name] = {"scope": None, "implType": None, "min": None, "max": None, "implMin": None, "implMax": None}
                return result[name]

            # --- .main.amd → scope ---
            main_file = d / f"{base}.main.amd"
            if main_file.exists():
                try:
                    root = ET.parse(str(main_file)).getroot()
                    for el in root.iter():
                        if "}" in el.tag:
                            el.tag = el.tag.split("}", 1)[1]
                    for elem in root.iter("Element"):
                        name = elem.get("name") or elem.get("elementName")
                        if not name:
                            continue
                        cfg = get_or_create(name)
                        prim = elem.find(".//PrimitiveAttributes")
                        if prim is not None:
                            scope = prim.get("scope")
                            if scope:
                                cfg["scope"] = scope
                except Exception:
                    pass

            # --- .implementation.amd + .implementation.dp.amd → implType / min / max ---
            # Both files can carry PhysicalInterval / ImplementationInterval data:
            #   .implementation.amd   → local variables / return signals
            #   .implementation.dp.amd → calibration parameters (data-points)
            def _parse_impl_file(impl_file_path):
                if not impl_file_path.exists():
                    return
                try:
                    _root = ET.parse(str(impl_file_path)).getroot()
                    for _el in _root.iter():
                        if "}" in _el.tag:
                            _el.tag = _el.tag.split("}", 1)[1]
                    for impl_entry in _root.iter("ElementImplementation"):
                        ename = impl_entry.get("elementName")
                        if not ename:
                            continue
                        _cfg = get_or_create(ename)
                        num_impl = impl_entry.find(".//NumericImplementation")
                        if num_impl is not None:
                            if num_impl.get("implType") and not _cfg["implType"]:
                                _cfg["implType"] = num_impl.get("implType")
                            phys_int = num_impl.find(".//PhysicalInterval")
                            if phys_int is not None:
                                if _cfg["min"] is None: _cfg["min"] = phys_int.get("min")
                                if _cfg["max"] is None: _cfg["max"] = phys_int.get("max")
                            impl_int = num_impl.find(".//ImplementationInterval")
                            if impl_int is not None:
                                if _cfg["implMin"] is None: _cfg["implMin"] = impl_int.get("min")
                                if _cfg["implMax"] is None: _cfg["implMax"] = impl_int.get("max")
                except Exception:
                    pass

            _parse_impl_file(d / f"{base}.implementation.amd")
            _parse_impl_file(d / f"{base}.implementation.dp.amd")
        except Exception:
            pass
        return result

    @staticmethod
    def to_netlist_text(xml_file_path: str) -> str:
        """
        Generate a full 3-section netlist report with scope/type annotations.

        Section 1 – ELEMENTS: all blocks + port tags
        Section 2 – SEQUENCE CALLS  (if present)
        Section 3 – CONNECTIONS / WIRES  with [Scope:ImplType] annotations
        """
        connections, oid_map = DiagramNetlistExtractor.extract_connections(xml_file_path)
        elem_dict = DiagramNetlistExtractor.build_element_dict(xml_file_path)

        # Parse sequence calls
        seq_calls: List[str] = []
        try:
            _tree = ET.parse(xml_file_path)
            _root = _tree.getroot()
            DiagramNetlistExtractor._strip_namespaces(_root)
            _spec = (_root.find('.//Specification[@name="Main"]') or
                     _root.find('.//Specification'))
            if _spec is not None:
                _pmap = {c: p for p in _root.iter() for c in p}
                for seq in _spec.findall('.//SequenceCall'):
                    seq_num = seq.get('sequenceNumber', '0')
                    if seq.get('userVisibility', 'true').lower() != 'true' or seq_num == '0':
                        continue
                    method_name = seq.get('methodName', '')
                    port_suffix = ""
                    par_el = _pmap.get(seq)
                    if par_el is not None and par_el.tag == 'MethodPort':
                        pm = par_el.get('methodName', '')
                        if pm:
                            port_suffix = f"  .{pm}"
                    seq_calls.append(
                        f"/{seq_num}/{method_name}" + port_suffix
                        if method_name else f"/{seq_num}/{port_suffix}"
                    )
        except Exception:
            pass

        # Scope/type tag helper
        def scope_tag(name: str) -> str:
            cfg = elem_dict.get(name, {})
            parts: List[str] = []
            scope = cfg.get("scope")
            if scope == "imported":
                parts.append("Imported")
            elif scope == "local":
                parts.append("Local")
            elif scope == "constant":
                parts.append("Constant")
            impl = cfg.get("implType")
            if impl:
                parts.append(impl)
            return f"[{':'.join(parts)}]" if parts else ""

        diagram_name = (os.path.basename(xml_file_path)
                        .replace(".specification.amd", "").replace(".amd", ""))
        W = 80
        lines: List[str] = [
            "=" * W,
            f"  ASCET DIAGRAM NETLIST  —  {diagram_name}",
            "=" * W, "",
        ]

        # ── SECTION 1: ELEMENTS ───────────────────────────────────────────
        # Collect unique blocks and their visible ports from oid_map
        block_ports: Dict[str, List[tuple]] = {}  # bname → list[(pname, ptag)]
        for info in oid_map.values():
            bname = info.get("block_name", "")
            pname = info.get("port_name", "Self")
            ptag  = info.get("port_tag", "")
            if not bname:
                continue
            if pname == "Self":
                block_ports.setdefault(bname, [])
            else:
                block_ports.setdefault(bname, []).append((pname, ptag))

        lines.append("[SECTION 1 — ELEMENTS]")
        lines.append("-" * W)
        for bname in sorted(block_ports.keys()):
            stag = scope_tag(bname)
            lines.append(f"  • {bname} {stag}".rstrip())
            for pname, ptag in sorted(set(block_ports[bname])):
                if not pname:
                    continue
                pstag = scope_tag(pname)
                plbl  = f"({ptag})" if ptag else ""
                lines.append(f"        {plbl:<22} {pname} {pstag}".rstrip())
        lines.append("")

        # ── SECTION 2: SEQUENCE CALLS ─────────────────────────────────────
        if seq_calls:
            lines.append("[SECTION 2 — SEQUENCE CALLS]")
            lines.append("-" * W)
            for i, sc in enumerate(seq_calls, 1):
                lines.append(f"  {i:02d}. {sc}")
            lines.append("")

        # ── SECTION 3: CONNECTIONS ────────────────────────────────────────
        lines.append(f"[SECTION 3 — CONNECTIONS / WIRES]  ({len(connections)} wire(s))")
        lines.append("-" * W)
        for wire_idx, conn in enumerate(connections, 1):
            si = oid_map.get(conn["source_oid"],
                             {"block_name": f"?(OID:{conn['source_oid']})",
                              "port_name": "Self", "port_tag": ""})
            ti = oid_map.get(conn["target_oid"],
                             {"block_name": f"?(OID:{conn['target_oid']})",
                              "port_name": "Self", "port_tag": ""})

            sname = si["block_name"]
            sport = si["port_name"]
            src_str = f"{sname}.{sport}" if sport and sport != "Self" else sname
            src_str += f"  {scope_tag(sname)}" if scope_tag(sname) else ""

            tname = ti["block_name"]
            tport = ti["port_name"]
            ttag  = ti["port_tag"]
            tgt_str = f"{tname}.{tport}" if tport and tport != "Self" else tname
            tgt_str += f"  {scope_tag(tname)}" if scope_tag(tname) else ""
            if ttag:
                tgt_str += f"  ({ttag})"

            lines.append(f"  Wire {wire_idx:02d}: {src_str.strip():<55} --> {tgt_str.strip()}")

        lines += ["", "=" * W]
        return "\n".join(lines)


class DiagramAIReviewFlow:
    """Dedicated AI review flow for diagram queue items."""

    def __init__(self, config: Dict[str, Any], mode: str):
        self.config = config
        self.mode = mode
        self.class_path = str(config.get("class_path", ""))
        self.model_type = config.get("model_type", "gpt5-mini")
        self.model_config = create_model_config(self.model_type)
        self.response_handler = create_response_handler(self.model_type)
        self.api_key = config.get("api_key", "")
        self.api_url = self._build_chat_url()

    def _build_chat_url(self) -> str:
        if self.config.get("deepseek_api_url"):
            return str(self.config.get("deepseek_api_url"))

        base_url = str(self.config.get("api_base_url", "http://10.161.112.104:3000/v1")).rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _build_prompt(self, netlist_text: str) -> List[Dict[str, str]]:
        system_prompt = (
            "You are an expert Automotive Software and ASCET Diagram Reviewer. "
            "Your task is to detect semantic signal-mapping errors in ASCET Block Diagram netlists. "
            "The netlist uses tags [Imported:type], [Local:type], [Constant] to annotate variable scope. "
            "You must distinguish between harmless naming conventions and actual logic/wiring defects."
        )
        user_prompt = f"""Review the following ASCET diagram netlist and detect semantic wiring errors.

{netlist_text}

### Tag Legend in the netlist:
- `[Imported:type]`  – Parameter imported from outside the module (e.g. a signal from another component)
- `[Local:type]`     – Variable declared locally within this diagram
- `[Constant]`       – Local constant parameter
- `(ReturnPort)`     – Output port that returns a value from this module
- `(ArgumentPort)`   – Input port of a function block

### Rules to check (report each violated rule separately):

**Rule 6 – Wrong wire mapping (spatial / functional swap):**
Compare the *semantic meaning* of the Source variable name vs the Target port name on every wire.
Flag as defect if: directional identifiers are swapped (FL↔FR, RL↔RR, Left↔Right, Front↔Rear),
or signal roles are crossed (e.g. Brake_Request wired to BrakeSwitch port).
DO NOT flag: standard module prefix differences (CM_HAZ_ABSActive → ABSActive is CORRECT),
case/underscore variations, or numeric suffix differences that are part of a valid schema.

**Rule 7 – Wrong imported→local mapping:**
For wires where source has `[Imported]` tag: compare the semantic meaning of the imported parameter
name to the local variable it connects to. Flag if an imported signal about one physical quantity
or vehicle area is clearly assigned to a local variable describing a different quantity or area.

**Rule 8 – Wrong return port assignment:**
For wires ending at `(ReturnPort)`: verify the local variable being returned semantically matches
the return port name. Flag when the local variable and the return port describe clearly different
signals (e.g. a velocity variable `v_FL` wired to a return port named `Return_v_FR`).

**Rule 9 (partial) – Wrong calc/init task:**
If Section 2 lists sequence calls: flag if a method named "init" appears to have many complex
data-flow wires feeding into it (suggesting computation logic), or a method named "calc" only
receives constant assignments. Only flag when the evidence is clear from the wires involving that block.

### Output Format — exactly ONE valid JSON block, NO comments inside:

Defects found:
```json
{{
  "错误类型": ["Wrong wire mapping", "Wrong return port"],
  "状态": "Defect",
  "defective_wire_numbers": [3, 7],
  "理由": "Wire 03: source [v_FL][Local] is wired to ReturnPort [Return_v_FR] — left/right speed mismatch. Wire 07: ..."
}}
```

No defects:
```json
{{
  "错误类型": [],
  "状态": "No Defect",
  "defective_wire_numbers": [],
  "理由": "All wires are semantically consistent."
}}
```

Constraints:
- `状态` MUST be exactly `"Defect"` or `"No Defect"`.
- `defective_wire_numbers` MUST be an integer array (1-based wire numbers). Use `[]` if none.
- List EVERY defective wire in BOTH `defective_wire_numbers` AND `理由`.
- Do NOT include any `//` comments or trailing commas in the JSON.""".strip()

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _call_ai(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise ValueError("Missing api_key for diagram AI review")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = self.model_config.get_request_params(messages)
        # Diagram flow needs a deterministic single response payload.
        payload["stream"] = False

       # response = requests.post(self.api_url, headers=headers, data=json.dumps(payload), timeout=180)
        proxies = get_proxies_for_url(self.api_url)

        response = requests.post(
            self.api_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=180,
            proxies=proxies
        )
        response.raise_for_status()
        response_data = response.json()

        processed = self.response_handler.process_complete_response(response_data)
        return processed.get("complete_content") or processed.get("main_content") or ""

    def run(self) -> Dict[str, Any]:
        start_time = datetime.now()
        diagram_name = Path(self.class_path).name if self.class_path else "UnknownDiagram"

        try:
            # ── Rule-based checks ──────────────────────────────────────────
            rule_error_details: List[Dict[str, Any]] = []
            rule_severity_stats = {
                "high_severity": 0, "medium_severity": 0,
                "low_severity": 0, "has_high_severity": False,
            }
            try:
                from src.diagrams.rule_base import DiagramRuleChecker, build_global_dict
                # elem_dict: precise scope+implType from sibling .main/.implementation files
                elem_dict = DiagramNetlistExtractor.build_element_dict(self.class_path)
                # global_dict: wide scan for signal range checks (Rule 5) + fallback
                export_folder = self._find_export_folder(self.class_path)
                global_dict = build_global_dict(export_folder) if export_folder else {}
                diagram_data = self._parse_diagram_for_rules(self.class_path, diagram_name)
                if diagram_data:
                    checker = DiagramRuleChecker(diagram_data, global_dict,
                                                 elem_dict=elem_dict)
                    rule_error_details = checker.run()
                    rule_severity_stats = checker.get_stats()
            except Exception as rule_err:
                print(f"[DiagramAIReviewFlow] Rule checks failed (non-fatal): {rule_err}")

            # ── AI review (只在 agent / smart_direct mode) ─────────────────
            ai_review = ""
            ai_error_details: List[Dict[str, Any]] = []
            if self.mode != "direct":
                netlist_text = DiagramNetlistExtractor.to_netlist_text(self.class_path)
                ai_review = self._call_ai(self._build_prompt(netlist_text))
                ai_error_details = extract_ai_errors(ai_review)
            else:
                netlist_text = DiagramNetlistExtractor.to_netlist_text(self.class_path)

            rule_errors = len(rule_error_details)
            ai_errors = len(ai_error_details)
            total_errors = rule_errors + ai_errors

            error_statistics = {
                "rule_errors": rule_errors,
                "ai_errors": ai_errors,
                "total_errors": total_errors,
                "rule_error_details": rule_error_details,
                "ai_error_details": ai_error_details,
                "rule_severity_stats": rule_severity_stats,
            }

            execution_time = (datetime.now() - start_time).total_seconds()
            return {
                "status": "success",
                "mode": self.mode,
                "execution_time": execution_time,
                "basic_issues": [],
                "ai_review": ai_review,
                "final_report": None,
                "current_report_path": None,
                "ascet_extraction_info": {
                    "class_path": self.class_path,
                    "diagram_name": diagram_name,
                    "diagram_review_flow": True,
                },
                "data_collection_status": "diagram_reviewed",
                "data_extraction_time": 0.0,
                "json_data_size": len(netlist_text),
                "error_statistics": error_statistics,
                "error_statistics_json": {
                    "error_statistics": error_statistics,
                    "mode": self.mode,
                    "class_path": self.class_path,
                    "note": "Diagram queue item - reviewed by dedicated diagram AI flow",
                },
                "summary": f"Diagram reviewed: {diagram_name} | Rules: {rule_errors} | AI: {ai_errors}",
                "token_statistics": "Diagram AI review completed",
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            print(f"[DiagramAIReviewFlow] Diagram review flow failed: {str(e)}")
            return {
                "status": "error",
                "mode": self.mode,
                "error_message": f"Diagram review flow failed: {str(e)}",
                "execution_time": execution_time,
                "error_statistics": {
                    "rule_errors": 0,
                    "ai_errors": 0,
                    "total_errors": 0,
                    "rule_error_details": [],
                    "ai_error_details": [],
                    "rule_severity_stats": {
                        "high_severity": 0,
                        "medium_severity": 0,
                        "low_severity": 0,
                        "has_high_severity": False,
                    },
                },
                "summary": f"Diagram review failed: {diagram_name}",
            }

    # ------------------------------------------------------------------
    # Helpers for rule integration
    # ------------------------------------------------------------------

    @staticmethod
    def _find_export_folder(amd_path: str) -> Optional[str]:
        """Walk up the directory tree to find the ASCET_Auto_Exports root."""
        p = Path(amd_path).parent
        for _ in range(10):
            if p.name == "ASCET_Auto_Exports" or (p / "ASCET_Auto_Exports").is_dir():
                return str(p / "ASCET_Auto_Exports") if (p / "ASCET_Auto_Exports").is_dir() else str(p)
            # Also check if .xml MasterDatabase folder sibling exists
            candidates = [x for x in p.iterdir() if x.is_dir() and "MasterDatabase" in x.name] if p.exists() else []
            if candidates:
                return str(p)
            parent = p.parent
            if parent == p:
                break
            p = parent
        # Fallback: use the directory containing the .amd file's top ancestor
        return str(Path(amd_path).parent)

    @staticmethod
    def _parse_diagram_for_rules(amd_path: str, diagram_name: str) -> Optional[Dict[str, Any]]:
        """Lightweight XML parse to produce diagram_data for rule checker."""
        try:
            tree = ET.parse(amd_path)
            root = tree.getroot()
            for el in root.iter():
                if '}' in el.tag:
                    el.tag = el.tag.split('}', 1)[1]

            parent_map = {c: p for p in root.iter() for c in p}

            main_spec = root.find('.//Specification[@name="Main"]')
            if main_spec is None:
                main_spec = root.find('.//Specification')
            if main_spec is None:
                return None

            TARGET_TAGS = ['ComplexElement', 'SimpleElement', 'Literal', 'Operator',
                           'Junction', 'Connector', 'ConnectionPoint']
            DIAGRAM_PORTS = ['ReturnPort', 'ArgumentPort', 'MessagePort',
                             'Parameter', 'TriggerPort', 'SelectorPort']
            VALID_PORT_TAGS = ['ReturnPort', 'SelectorPort', 'ArgumentPort',
                               'TriggerPort', 'MessagePort']

            parsed_blocks: Dict[str, Any] = {}

            for elem in main_spec.iter():
                if elem.tag not in TARGET_TAGS and elem.tag not in DIAGRAM_PORTS:
                    continue
                b_oid = elem.attrib.get('graphicOID', '')
                pos = elem.find('./Position')
                if not b_oid or pos is None or b_oid == "-1":
                    continue

                b_type = elem.tag
                if b_type in DIAGRAM_PORTS:
                    elem_parent = parent_map.get(elem)
                    if elem_parent is not None and elem_parent.tag == 'DiagramElement':
                        b_name = (elem.get('elementName') or elem.get('methodName') or
                                  elem.get('name') or b_type)
                        if b_type == 'ReturnPort':
                            b_name = f"return / {b_name}"
                        b_type = 'SimpleElement'
                    else:
                        continue
                else:
                    if b_type == 'Literal':
                        b_name = elem.attrib.get('value', '???')
                    elif b_type == 'Operator':
                        b_name = elem.attrib.get('operator', elem.attrib.get('kind', 'Op'))
                    elif b_type in ['Junction', 'Connector', 'ConnectionPoint']:
                        b_name = ''
                    else:
                        b_name = elem.attrib.get('elementName', elem.tag)

                bx = float(pos.attrib.get('x', 0))
                by = float(pos.attrib.get('y', 0))
                block_data: Dict[str, Any] = {
                    "id": b_oid, "name": b_name, "type": b_type,
                    "position": {"x": bx, "y": by}, "ports": []
                }

                interfaces = elem.find('.//Interfaces')
                if interfaces is not None:
                    for port in interfaces.iter():
                        if port.tag not in VALID_PORT_TAGS:
                            continue
                        p_oid = port.attrib.get('graphicOID')
                        if not p_oid or p_oid == "-1":
                            continue
                        p_pos = port.find('./Position')
                        px = float(p_pos.attrib.get('x', 0)) if p_pos is not None else bx
                        py = float(p_pos.attrib.get('y', 0)) if p_pos is not None else by
                        p_name = (port.get('name') or port.get('elementName') or
                                  port.get('methodName') or port.get('instanceName'))
                        if not p_name:
                            pp = parent_map.get(port)
                            if pp is not None:
                                if pp.tag == 'MethodPort':
                                    p_name = pp.get('methodName') or pp.get('name')
                                if not p_name:
                                    gp = parent_map.get(pp)
                                    if gp is not None:
                                        p_name = (gp.get('elementName') or gp.get('instanceName') or
                                                  gp.get('methodName') or gp.get('ClassName'))
                        if not p_name:
                            p_name = port.tag
                        block_data["ports"].append({
                            "id": p_oid, "name": p_name,
                            "tag": port.tag,
                            "position": {"x": px, "y": py},
                            "is_visible": port.attrib.get('visibility', 'true').lower() == 'true'
                        })

                if b_oid not in parsed_blocks or \
                   len(block_data["ports"]) > len(parsed_blocks[b_oid].get("ports", [])):
                    parsed_blocks[b_oid] = block_data

            connections = []
            seen: set = set()
            for conn in main_spec.findall('.//Connection'):
                s = conn.find('.//Start')
                e = conn.find('.//End')
                if s is None or e is None:
                    continue
                src = s.attrib.get('graphicOID')
                tgt = e.attrib.get('graphicOID')
                if not src or not tgt:
                    continue
                bends = tuple((float(b.attrib.get('x', 0)), float(b.attrib.get('y', 0)))
                              for b in conn.findall('.//BendPoint'))
                key = (src, tgt, bends)
                if key in seen:
                    continue
                seen.add(key)
                connections.append({
                    "source_oid": src, "target_oid": tgt,
                    "bend_points": [{"x": pt[0], "y": pt[1]} for pt in bends]
                })

            return {
                "diagram_name": diagram_name,
                "blocks": list(parsed_blocks.values()),
                "connections": connections,
                "sequence_calls": [],
            }
        except Exception as ex:
            print(f"[DiagramAIReviewFlow] _parse_diagram_for_rules failed: {ex}")
            return None


def parse_defective_wires(ai_review_text: str) -> Optional[Set[int]]:
    """
    Parse the AI chatbot diagram review response and return the set of
    1-based wire indices that the AI identified as defective.

    Returns:
        None      – could not parse the response or status is ambiguous
        set()     – reviewed, all wires OK ("No Defect")
        {1, 3, …} – reviewed, these 1-based wire numbers are defective
    """
    if not ai_review_text:
        return None

    # ── Step 1: extract the raw JSON text ──────────────────────────────
    json_text: Optional[str] = None

    # Try ```json ... ``` block first
    json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_review_text, re.DOTALL | re.IGNORECASE)
    if json_block_match:
        json_text = json_block_match.group(1)
    else:
        # Fallback: find outermost { … } in the full response
        try:
            start = ai_review_text.index('{')
            depth = 0
            for i, ch in enumerate(ai_review_text[start:], start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        json_text = ai_review_text[start:i + 1]
                        break
        except ValueError:
            pass

    if not json_text:
        return None

    # ── Step 2: strip JS-style // comments so json.loads doesn't fail ──
    # Remove   "key": value,  // some comment
    json_text_clean = re.sub(r'//[^\n]*', '', json_text)

    # ── Step 3: parse JSON ──────────────────────────────────────────────
    try:
        data = json.loads(json_text_clean)
    except json.JSONDecodeError:
        # Last resort: try original (model may not have added comments)
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            return None

    # ── Step 4: read status ────────────────────────────────────────────
    # Accept both "状态" (Chinese) and "status" (English) for robustness
    status = str(data.get("状态", data.get("status", ""))).strip()

    if "No Defect" in status:
        return set()          # all wires are correct

    if "Defect" not in status:
        return None           # unrecognised status

    # ── Step 5: extract defective wire numbers ─────────────────────────

    # PRIMARY: dedicated array field "defective_wire_numbers"
    wire_num_field = data.get("defective_wire_numbers")
    if isinstance(wire_num_field, list) and wire_num_field:
        result: Set[int] = set()
        for v in wire_num_field:
            try:
                result.add(int(v))
            except (ValueError, TypeError):
                pass
        if result:
            return result

    # FALLBACK: scan free-text 理由 / reason for "Wire NN" patterns
    reason = str(data.get("理由", data.get("reason", "")))
    wire_nums = re.findall(
        r'\bWire\s*[#№]?\s*(\d+)\b',
        reason,
        re.IGNORECASE,
    )
    if wire_nums:
        return {int(n) for n in wire_nums}

    # "Defect" declared but no wire numbers found anywhere
    return None