"""
Diagram Viewer Dialog - Display diagram visualization and connection logic
Shows diagram with 2 tabs: Visual diagram + Text-based connection logic
"""

import os
import json as _json
import xml.etree.ElementTree as ET
import math
import html as _html
from typing import Dict, List, Optional, Set

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QGraphicsView, 
                               QGraphicsScene, QTextEdit, QPushButton, QLabel, QWidget)
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPainterPath, QPolygonF, QFont, QImage
from PySide6.QtCore import Qt, QPointF, QRectF


# =====================================================================
# DIAGRAM RENDERER (Vẽ sơ đồ)
# =====================================================================
class DiagramRenderer:
    def __init__(self, scene):
        self.scene = scene
        self.port_coords = {}
        
        self.pen_box = QPen(Qt.black, 1.5)
        self.pen_line = QPen(Qt.black, 1.5)
        self.pen_none = QPen(Qt.NoPen)
        self.pen_wire_ok = QPen(QColor('#1a8f1a'), 2.0)    # green – wire OK
        self.pen_wire_bad = QPen(QColor('#cc2222'), 2.0)   # red   – wire defective (AI)
        self.pen_wire_rule = QPen(QColor('#cc7700'), 2.0)  # orange – wire defective (rule-base)
        self.pen_wire_calc = QPen(QColor('#800080'), 2.0)  # purple - wire defective (calc flow)

        self.brush_complex = QBrush(QColor('#f8f9fa'))
        self.brush_simple = QBrush(Qt.white)
        self.brush_literal = QBrush(QColor('#fffcdc')) 
        self.brush_operator = QBrush(QColor('#e8f4f8')) 
        self.brush_red = QBrush(QColor('#cc3333'))
        self.brush_black = QBrush(Qt.black)
        self.brush_wire_ok = QBrush(QColor('#1a8f1a'))
        self.brush_wire_bad = QBrush(QColor('#cc2222'))
        self.brush_wire_rule = QBrush(QColor('#cc7700'))
        
        self.font_bold = QFont("Consolas", 9, QFont.Bold)
        self.font_normal = QFont("Consolas", 7) 
        self.font_op = QFont("Consolas", 12, QFont.Bold)

    def render(self, data, defective_wire_indices=None, rule_defective_wire_indices=None, calc_defective_wire_indices=None):
        """
        Render diagram blocks and connections.

        defective_wire_indices:
            None        – no AI review done; wires drawn in black
            set()       – all wires OK; wires drawn in green
            {1, 3, …}   – 1-based wire numbers that are defective (red);
                          all others drawn green
        rule_defective_wire_indices:
            None        – no rule-base review; ignored
            set()       – all wires OK per rule-base
            {2, 5, …}   – 1-based wire numbers flagged by rule-base (orange)
        calc_defective_wire_indices:
            None        - no calc flow check
            set()       - all calc flows OK
            {4, 7, ...} - 1-based wire numbers flagged by sequence execution logic (purple)
        """
        self.scene.clear()
        self.port_coords.clear()

        source_oids, target_oids = set(), set()
        for conn in data.get('connections', []):
            source_oids.add(conn['source_oid'])
            target_oids.add(conn['target_oid'])

        # STEP 1: Draw blocks and record port coordinates
        for block in data.get('blocks', []):
            b_type, b_name, bx, by = block['type'], block['name'], block['position']['x'], block['position']['y']
            
            if b_type == 'Literal':
                t_item = self.scene.addText(str(b_name), self.font_normal)
                tw, th = t_item.boundingRect().width(), t_item.boundingRect().height()
                box = self.scene.addRect(bx - tw - 6, by - th/2, tw + 6, th, self.pen_line, self.brush_literal)
                t_item.setPos(bx - tw - 3, by - th/2)
                box.setZValue(0); t_item.setZValue(2)
                self.port_coords[block['id']] = (bx, by)

            elif b_type == 'Operator':
                r = 12
                ellipse = self.scene.addEllipse(bx - r, by - r, r*2, r*2, self.pen_box, self.brush_operator)
                t_item = self.scene.addText(b_name, self.font_op)
                t_item.setPos(bx - t_item.boundingRect().width()/2, by - t_item.boundingRect().height()/2 - 1)
                ellipse.setZValue(0); t_item.setZValue(2)
                self.port_coords[block['id']] = (bx, by)
                
            elif b_type in ['Junction', 'Connector', 'ConnectionPoint']:
                dot = self.scene.addEllipse(bx - 3, by - 3, 6, 6, self.pen_none, self.brush_black)
                dot.setZValue(3) 
                self.port_coords[block['id']] = (bx, by)

            elif b_type == 'ComplexElement':
                v_px = [p['position']['x'] for p in block.get('ports', []) if p.get('is_visible', True)]
                v_py = [p['position']['y'] for p in block.get('ports', []) if p.get('is_visible', True)]
                
                if v_px and v_py:
                    min_x, max_x = min(v_px), max(v_px)
                    min_y, max_y = min(v_py), max(v_py)
                    
                    if min_x == max_x:
                        min_x -= 30; max_x += 30 
                    
                    w = max_x - min_x
                    h = max_y - min_y + 30
                    rect_y = min_y - 15
                else:
                    min_x, rect_y, w, h = bx, by, 100, 60

                rect = self.scene.addRect(min_x, rect_y, w, h, self.pen_box, self.brush_complex)
                rect.setZValue(-2) 
                
                # Label placed BELOW the box (matches share_cn notebook)
                t_item = self.scene.addText(b_name, self.font_bold)
                t_item.setPos(min_x + w/2 - t_item.boundingRect().width()/2, rect_y + h + 5)
                t_item.setZValue(2)

                for p in block.get('ports', []):
                    if not p.get('is_visible', True): continue 
                    pid, px, py, pname = p['id'], p['position']['x'], p['position']['y'], p['name']
                    self.port_coords[pid] = (px, py)
                    
                    p_box = self.scene.addRect(px - 3, py - 3, 6, 6, self.pen_box, self.brush_red)
                    p_item = self.scene.addText(pname, self.font_normal)
                    p_box.setZValue(1); p_item.setZValue(2)
                    
                    if px <= min_x + w/2: 
                        p_item.setPos(px + 4, py - p_item.boundingRect().height()/2)
                    else: 
                        p_item.setPos(px - p_item.boundingRect().width() - 4, py - p_item.boundingRect().height()/2)

            elif b_type == 'SimpleElement':
                t_item = self.scene.addText(b_name, self.font_normal)
                tw, th = t_item.boundingRect().width(), t_item.boundingRect().height()
                
                has_input_connection = any(p['id'] in target_oids for p in block.get('ports', []))
                has_output_connection = any(p['id'] in source_oids for p in block.get('ports', []))
                
                is_target = has_input_connection and not has_output_connection
                
                if is_target:
                    box = self.scene.addRect(bx, by - th/2, tw + 6, th, self.pen_line, self.brush_simple)
                    t_item.setPos(bx + 3, by - th/2)
                else:
                    box = self.scene.addRect(bx - tw - 6, by - th/2, tw + 6, th, self.pen_line, self.brush_simple)
                    t_item.setPos(bx - tw - 3, by - th/2)
                
                box.setZValue(0); t_item.setZValue(2)
                
                if not block.get('ports'): 
                    self.port_coords[block['id']] = (bx, by)
                else:
                    for p in block.get('ports'): 
                        self.port_coords[p['id']] = (bx, by)

        # STEP 2: Draw connections
        for wire_idx, conn in enumerate(data.get('connections', []), 1):
            src, tgt = conn['source_oid'], conn['target_oid']
            if src not in self.port_coords or tgt not in self.port_coords: 
                continue

            # Choose wire colour based on review results
            rule_set = rule_defective_wire_indices or set()
            calc_set = calc_defective_wire_indices or set()
            
            # Priority: Calc defective (purple) > AI defective (red) > Rule defective (orange) > OK (green) > no review (black)
            # if calc_set and wire_idx in calc_set:
            #     wire_pen = self.pen_wire_calc       # Calc Flow defective → purple
            #     arrow_brush = QBrush(QColor('#800080'))
            if defective_wire_indices is not None and wire_idx in defective_wire_indices:
                wire_pen = self.pen_wire_bad       # AI defective → red
                arrow_brush = self.brush_wire_bad
            # elif rule_set and wire_idx in rule_set:
            #     wire_pen = self.pen_wire_rule      # Rule defective → orange
            #     arrow_brush = self.brush_wire_rule
            elif defective_wire_indices is not None or rule_defective_wire_indices is not None or calc_defective_wire_indices is not None:
                wire_pen = self.pen_wire_ok        # reviewed & OK → green
                arrow_brush = self.brush_wire_ok
            else:
                wire_pen = self.pen_line           # no review → black
                arrow_brush = self.brush_black
            
            sx, sy = self.port_coords[src]
            ex, ey = self.port_coords[tgt]
            
            path_points = [(sx, sy)]
            for bend in conn.get('bend_points', []):
                path_points.append((bend['x'], bend['y']))
            path_points.append((ex, ey))

            path = QPainterPath()
            path.moveTo(path_points[0][0], path_points[0][1])
            for pt in path_points[1:]: 
                path.lineTo(pt[0], pt[1])
            
            path_item = self.scene.addPath(path, wire_pen)
            path_item.setZValue(-1) 
            
            # Draw arrow head
            if len(path_points) >= 2:
                for i in range(len(path_points)-1, 0, -1):
                    px1, py1 = path_points[i-1]
                    px2, py2 = path_points[i]
                    dist = math.hypot(px2 - px1, py2 - py1)
                    if dist > 1e-3: 
                        dx, dy = (px2 - px1) / dist, (py2 - py1) / dist
                        nx, ny = -dy, dx
                        p1 = QPointF(px2, py2)
                        p2 = QPointF(px2 - 8*dx + 4*nx, py2 - 8*dy + 4*ny)
                        p3 = QPointF(px2 - 8*dx - 4*nx, py2 - 8*dy - 4*ny)
                        arrow = self.scene.addPolygon(QPolygonF([p1, p2, p3]), self.pen_none, arrow_brush)
                        arrow.setZValue(2)
                        break
                        
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))

        # STEP 3: Draw sequence call markers (execution order, e.g. /1/calc)
        
        # --- 3.1 Tìm các block bị dính lỗi Calc Flow ---
        defective_calc_blocks = set()
        if calc_defective_wire_indices:
            # Map port_id -> block_id
            port_to_block = {}
            for block in data.get('blocks', []):
                bid = block['id']
                port_to_block[bid] = bid
                for p in block.get('ports', []):
                    port_to_block[p['id']] = bid
                    
            # Tìm block từ wire bị lỗi
            for wire_idx, conn in enumerate(data.get('connections', []), 1):
                if wire_idx in calc_defective_wire_indices:
                    src_block = port_to_block.get(conn['source_oid'])
                    tgt_block = port_to_block.get(conn['target_oid'])
                    if src_block: defective_calc_blocks.add(src_block)
                    if tgt_block: defective_calc_blocks.add(tgt_block)

        # --- 3.2 Vẽ sequence markers và đổi màu text ---
        for seq in data.get('sequence_calls', []):
            pos = seq.get('position', {})
            sx, sy = pos.get('x', 0), pos.get('y', 0)

            # Vẽ ô vuông đỏ mặc định
            sq = self.scene.addRect(sx - 2, sy - 2, 4, 4, self.pen_line, self.brush_red)
            sq.setZValue(3)

            # Highlight text ĐỎ + IN ĐẬM nếu dính lỗi
            is_defective_calc = seq.get('block_oid') in defective_calc_blocks
            text_color = Qt.red if is_defective_calc else Qt.black
            calc_font = QFont("Consolas", 9, QFont.Bold) if is_defective_calc else self.font_normal

            if seq.get('port_method'):
                pm_item = self.scene.addText(f".{seq['port_method']}", calc_font)
                pm_item.setDefaultTextColor(text_color)
                pm_item.setPos(sx + 3, sy - 16)
                pm_item.setZValue(4)

            seq_item = self.scene.addText(seq.get('text', ''), calc_font)
            seq_item.setDefaultTextColor(text_color)
            y_offset = -6 if seq.get('port_method') else -10
            seq_item.setPos(sx + 3, sy + y_offset)
            seq_item.setZValue(4)

# =====================================================================
# CONNECTION LOGIC EXTRACTOR (Trích xuất logic dây nối)
# =====================================================================
class ConnectionLogicExtractor:
    """
    Generates a comprehensive text/HTML report of every element in diagram_data:
      Section 1 – ELEMENTS: all blocks grouped by type, with ports
      Section 2 – SEQUENCE CALLS: method call order
      Section 3 – CONNECTIONS (NETLIST): wires with source→target, colour-coded on review
    """

    # Display labels for each block type
    _TYPE_LABELS = {
        "ComplexElement":   "Function Block (Complex)",
        "SimpleElement":    "Simple Element / Variable",
        "Literal":          "Literal Constant",
        "Operator":         "Operator",
        "Junction":         "Junction",
        "Connector":        "Connector",
        "ConnectionPoint":  "Connection Point",
    }

    # Port tag → display label
    _PORT_LABELS = {
        "ReturnPort":   "ReturnPort  (out)",
        "ArgumentPort": "ArgumentPort(in) ",
        "MessagePort":  "MessagePort     ",
        "TriggerPort":  "TriggerPort     ",
        "SelectorPort": "SelectorPort    ",
    }

    @staticmethod
    def _build_oid_map(diagram_data: Dict) -> Dict:
        oid_map: Dict = {}
        for b in diagram_data.get("blocks", []):
            oid_map[b["id"]] = {"block_name": b.get("name", ""), "port_name": "Self", "port_tag": ""}
            for p in b.get("ports", []):
                oid_map[p["id"]] = {
                    "block_name": b.get("name", ""),
                    "port_name": p.get("name", ""),
                    "port_tag": p.get("tag", ""),
                }
        return oid_map

    # ──────────────────────────────────────────────────────────────────
    # Scope-tag helpers
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _scope_tag_text(name: str, scope_dict: Dict) -> str:
        """Return plain-text [Scope:ImplType] tag for a variable name."""
        cfg = scope_dict.get(name, {})
        parts: List[str] = []
        scope = cfg.get("scope")
        if scope == "imported":   parts.append("Imported")
        elif scope == "local":    parts.append("Local")
        elif scope == "constant": parts.append("Constant")
        impl = cfg.get("implType")
        if impl: parts.append(impl)
        return f"[{':'.join(parts)}]" if parts else ""

    @staticmethod
    def _scope_tag_html(name: str, scope_dict: Dict) -> str:
        """Return coloured HTML span for the scope/type tag."""
        cfg = scope_dict.get(name, {})
        scope = cfg.get("scope")
        impl  = cfg.get("implType")
        if scope == "imported":
            colour, label = "#b35900", "Imported"
        elif scope == "local":
            colour, label = "#006060", "Local"
        elif scope == "constant":
            colour, label = "#5a0080", "Constant"
        else:
            return ""
        text = f"{label}:{impl}" if impl else label
        return f'<span style="color:{colour};font-weight:bold;">[{text}]</span>'

    @staticmethod
    def _range_tag_text(name: str, scope_dict: Dict) -> str:
        """Return plain-text range annotation for a signal, e.g. [Phys:0.0~100.0 | Impl:0~255]."""
        cfg = scope_dict.get(name, {})
        phys_min = cfg.get("min") or cfg.get("Min")
        phys_max = cfg.get("max") or cfg.get("Max")
        impl_min = cfg.get("implMin") or cfg.get("ImplMin")
        impl_max = cfg.get("implMax") or cfg.get("ImplMax")
        parts: List[str] = []
        if phys_min is not None and phys_max is not None:
            parts.append(f"Phys:{phys_min}~{phys_max}")
        if impl_min is not None and impl_max is not None:
            parts.append(f"Impl:{impl_min}~{impl_max}")
        return f"[{' | '.join(parts)}]" if parts else ""

    @staticmethod
    def _range_tag_html(name: str, scope_dict: Dict) -> str:
        """Return coloured HTML span for the physical/implementation range."""
        cfg = scope_dict.get(name, {})
        phys_min = cfg.get("min") or cfg.get("Min")
        phys_max = cfg.get("max") or cfg.get("Max")
        impl_min = cfg.get("implMin") or cfg.get("ImplMin")
        impl_max = cfg.get("implMax") or cfg.get("ImplMax")
        parts: List[str] = []
        if phys_min is not None and phys_max is not None:
            parts.append(f"Phys:{_html.escape(str(phys_min))}~{_html.escape(str(phys_max))}")
        if impl_min is not None and impl_max is not None:
            parts.append(f"Impl:{_html.escape(str(impl_min))}~{_html.escape(str(impl_max))}")
        if not parts:
            return ""
        return f'<span style="color:#880088;">[{" | ".join(parts)}]</span>'

    # ──────────────────────────────────────────────────────────────────
    # Plain-text version  (used when no HTML widget available)
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def extract(diagram_data: Dict, scope_dict: Optional[Dict] = None) -> str:
        sd = scope_dict or {}
        W = 80
        sep = "=" * W
        thin = "-" * W

        lines = [
            sep,
            f"  DIAGRAM NETLIST & ELEMENT REPORT",
            f"  Diagram: {diagram_data.get('diagram_name', 'Unknown')}",
            sep,
        ]

        # ── SECTION 1: ELEMENTS ────────────────────────────────────────
        lines += ["", "  [1] ELEMENTS", thin]
        blocks = diagram_data.get("blocks", [])
        grouped: Dict[str, List] = {}
        for b in blocks:
            grouped.setdefault(b.get("type", "Unknown"), []).append(b)

        for btype, group in grouped.items():
            label = ConnectionLogicExtractor._TYPE_LABELS.get(btype, btype)
            lines.append(f"\n  ▶ {label} ({len(group)} item(s))")
            for b in group:
                stag = ConnectionLogicExtractor._scope_tag_text(b.get("name", ""), sd)
                rtag = ConnectionLogicExtractor._range_tag_text(b.get("name", ""), sd)
                lines.append(f"    • {b.get('name', '(unnamed)')}  {stag}  {rtag}".rstrip())
                for p in b.get("ports", []):
                    if not p.get("is_visible", True):
                        continue
                    ptag  = p.get("tag", "Port")
                    plbl  = ConnectionLogicExtractor._PORT_LABELS.get(ptag, f"{ptag:<20}")
                    pname = p.get("name", "")
                    pstag = ConnectionLogicExtractor._scope_tag_text(pname, sd)
                    prtag = ConnectionLogicExtractor._range_tag_text(pname, sd)
                    lines.append(f"        {plbl} : {pname}  {pstag}  {prtag}".rstrip())

        # ── SECTION 2: SEQUENCE CALLS ──────────────────────────────────
        seq_calls = diagram_data.get("sequence_calls", [])
        if seq_calls:
            lines += ["", "", f"  [2] SEQUENCE CALLS ({len(seq_calls)} call(s))", thin]
            for i, seq in enumerate(seq_calls, 1):
                pm = f"  .{seq['port_method']}" if seq.get("port_method") else ""
                lines.append(f"    {i:02d}.  {seq.get('text', '')}{pm}")

        # ── SECTION 3: CONNECTIONS ─────────────────────────────────────
        oid_map = ConnectionLogicExtractor._build_oid_map(diagram_data)
        connections = diagram_data.get("connections", [])
        lines += ["", "", f"  [3] CONNECTIONS / WIRES ({len(connections)} wire(s))", thin]
        for wire_idx, conn in enumerate(connections, 1):
            si = oid_map.get(conn["source_oid"])
            ti = oid_map.get(conn["target_oid"])
            if not si or not ti:
                continue
            sname = si['block_name']
            tname = ti['block_name']
            src_str = (f"[{sname}]" if si["port_name"] == "Self"
                       else f"[{sname}].{si['port_name']}")
            src_str += f"  {ConnectionLogicExtractor._scope_tag_text(sname, sd)}"
            tgt_str = (f"[{tname}]" if ti["port_name"] == "Self"
                       else f"[{tname}].{ti['port_name']}"
                       + (f" ({ti['port_tag']})" if ti["port_tag"] else ""))
            tgt_str += f"  {ConnectionLogicExtractor._scope_tag_text(tname, sd)}"
            lines.append(f"    Wire {wire_idx:02d}: {src_str.strip():<55} --> {tgt_str.strip()}")

        # ── SECTION 4: SIGNAL RANGES ───────────────────────────────────
        range_entries = []
        seen = set()
        for b in blocks:
            bname = b.get("name", "")
            if bname and bname not in seen:
                rtag = ConnectionLogicExtractor._range_tag_text(bname, sd)
                if rtag:
                    seen.add(bname)
                    range_entries.append((bname, rtag))
            for p in b.get("ports", []):
                pname = p.get("name", "")
                if pname and pname not in seen:
                    rtag = ConnectionLogicExtractor._range_tag_text(pname, sd)
                    if rtag:
                        seen.add(pname)
                        range_entries.append((pname, rtag))
        if range_entries:
            lines += ["", "", f"  [4] SIGNAL RANGES ({len(range_entries)} signal(s) with defined range)", thin]
            for sig_name, rtag in range_entries:
                lines.append(f"    • {sig_name:<45} {rtag}")

        lines += ["", sep]
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────
    # HTML version  (used by the PySide6 QTextEdit widget)
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def extract_html(diagram_data: Dict, defective_wire_indices: Optional[Set[int]] = None,
                     scope_dict: Optional[Dict] = None,
                     rule_defective_wire_indices: Optional[Set[int]] = None,
                     rule_error_details: Optional[List[Dict]] = None) -> str:
        sd = scope_dict or {}

        def esc(s: str) -> str:
            return _html.escape(str(s))

        W = 80
        sep  = esc("=" * W)
        thin = esc("-" * W)

        rows = [
            sep,
            f'<b>{esc("  DIAGRAM NETLIST & ELEMENT REPORT")}</b>',
            esc(f"  Diagram: {diagram_data.get('diagram_name', 'Unknown')}"),
            sep,
        ]

        # ── SECTION 1: ELEMENTS ────────────────────────────────────────
        rows += ["", f'<b style="color:#003580;">  [1] ELEMENTS</b>', thin]
        blocks = diagram_data.get("blocks", [])
        grouped: Dict[str, List] = {}
        for b in blocks:
            grouped.setdefault(b.get("type", "Unknown"), []).append(b)

        for btype, group in grouped.items():
            label = ConnectionLogicExtractor._TYPE_LABELS.get(btype, btype)
            rows.append(f'<b>  &#9654; {esc(label)} ({len(group)} item(s))</b>')
            for b in group:
                bname    = esc(b.get("name", "(unnamed)"))
                stag_h   = ConnectionLogicExtractor._scope_tag_html(b.get("name", ""), sd)
                rtag_h   = ConnectionLogicExtractor._range_tag_html(b.get("name", ""), sd)
                rows.append(f'    <span style="color:#333;">&#8226; {bname}</span>{stag_h}{rtag_h}')
                for p in b.get("ports", []):
                    if not p.get("is_visible", True):
                        continue
                    ptag  = p.get("tag", "Port")
                    plbl  = esc(ConnectionLogicExtractor._PORT_LABELS.get(ptag, f"{ptag:<20}"))
                    pname = esc(p.get("name", ""))
                    pstag = ConnectionLogicExtractor._scope_tag_html(p.get("name", ""), sd)
                    prtag = ConnectionLogicExtractor._range_tag_html(p.get("name", ""), sd)
                    if "Return" in ptag:
                        colour = "#8b0000"
                    elif "Argument" in ptag:
                        colour = "#005000"
                    else:
                        colour = "#555"
                    rows.append(
                        f'        <span style="color:{colour};">{plbl}</span>'
                        f' : <span style="color:#004080;">{pname}</span>{pstag}{prtag}'
                    )

        # ── SECTION 2: SEQUENCE CALLS ──────────────────────────────────
        seq_calls = diagram_data.get("sequence_calls", [])
        if seq_calls:
            rows += [
                "", "",
                f'<b style="color:#003580;">  [2] SEQUENCE CALLS ({len(seq_calls)} call(s))</b>',
                thin,
            ]
            for i, seq in enumerate(seq_calls, 1):
                text = esc(seq.get("text", ""))
                pm   = f'  <span style="color:#555;">.{esc(seq["port_method"])}</span>' \
                       if seq.get("port_method") else ""
                rows.append(
                    f'    <span style="color:#8b4513;font-weight:bold;">'
                    f'{i:02d}.  {text}{pm}</span>'
                )

        # ── SECTION 3: CONNECTIONS ─────────────────────────────────────
        oid_map = ConnectionLogicExtractor._build_oid_map(diagram_data)
        connections = diagram_data.get("connections", [])
        rows += [
            "", "",
            f'<b style="color:#003580;">  [3] CONNECTIONS / WIRES ({len(connections)} wire(s))</b>',
            thin,
        ]
        for wire_idx, conn in enumerate(connections, 1):
            si = oid_map.get(conn["source_oid"])
            ti = oid_map.get(conn["target_oid"])
            if not si or not ti:
                continue

            sname = si["block_name"]
            tname = ti["block_name"]
            src_plain = (f"[{sname}]" if si["port_name"] == "Self"
                         else f"[{sname}].{si['port_name']}")
            tgt_plain = (f"[{tname}]" if ti["port_name"] == "Self"
                         else f"[{tname}].{ti['port_name']}"
                         + (f" ({ti['port_tag']})" if ti["port_tag"] else ""))

            src_tag_h = ConnectionLogicExtractor._scope_tag_html(sname, sd)
            tgt_tag_h = ConnectionLogicExtractor._scope_tag_html(tname, sd)

            pad = max(1, 54 - len(src_plain))
            line_text = (f"  Wire {wire_idx:02d}: {esc(src_plain)}{src_tag_h}"
                         f"{'&nbsp;' * pad}"
                         f"--&gt; {esc(tgt_plain)}{tgt_tag_h}")

            if defective_wire_indices is None:
                rows.append(line_text)
            elif wire_idx in defective_wire_indices:
                rows.append(
                    f'<span style="color:#cc2222;font-weight:bold;">&#128279;{line_text}</span>'
                )
            elif rule_defective_wire_indices and wire_idx in rule_defective_wire_indices:
                rows.append(
                    f'<span style="color:#cc7700;font-weight:bold;">&#128279;{line_text}</span>'
                )
            else:
                rows.append(
                    f'<span style="color:#1a8f1a;font-weight:bold;">&#128279;{line_text}</span>'
                )

        # ── SECTION 4: SIGNAL RANGES ───────────────────────────────────
        range_entries_html = []
        seen_html: set = set()
        for b in blocks:
            bname_raw = b.get("name", "")
            if bname_raw and bname_raw not in seen_html:
                rtag_h = ConnectionLogicExtractor._range_tag_html(bname_raw, sd)
                if rtag_h:
                    seen_html.add(bname_raw)
                    range_entries_html.append((bname_raw, rtag_h))
            for p in b.get("ports", []):
                pname_raw = p.get("name", "")
                if pname_raw and pname_raw not in seen_html:
                    rtag_h = ConnectionLogicExtractor._range_tag_html(pname_raw, sd)
                    if rtag_h:
                        seen_html.add(pname_raw)
                        range_entries_html.append((pname_raw, rtag_h))
        if range_entries_html:
            rows += [
                "", "",
                f'<b style="color:#880088;">  [4] SIGNAL RANGES ({len(range_entries_html)} signal(s) with defined range)</b>',
                thin,
            ]
            for sig_name_raw, rtag_h in range_entries_html:
                rows.append(
                    f'    <span style="color:#333;">&#8226; {esc(sig_name_raw)}</span>'
                    f'&nbsp;&nbsp;&nbsp;{rtag_h}'
                )

        # ── SECTION 5: RULE-BASE ERRORS ────────────────────────────────
        rule_details = rule_error_details or []
        if rule_details:
            rows += [
                "", "",
                f'<b style="color:#cc7700;">  [5] RULE-BASE ERRORS ({len(rule_details)} issue(s))</b>',
                thin,
            ]
            for i, err in enumerate(rule_details, 1):
                rule_key = esc(err.get("rule_key", ""))
                err_type = esc(err.get("type", "Unknown"))
                message  = esc(err.get("message", ""))
                severity = err.get("original_severity", err.get("severity", ""))
                if str(severity).lower() in ("error", "high"):
                  #  sev_colour = "#cc2222" future
                    sev_colour = "#cc7700"
                    sev_label = "ERROR"
                else:
                    sev_colour = "#cc7700"
                    sev_label = "Warning"
                rows.append(
                    f'    <span style="color:{sev_colour};font-weight:bold;">'
                    f'{i:02d}. [{sev_label}] {rule_key}</span>'
                )
                rows.append(
                    f'        <span style="color:#555;">{err_type}</span>'
                )
                rows.append(
                    f'        <span style="color:#333;">{message}</span>'
                )

        rows += ["", sep]
        inner = "<br>".join(rows)
        return f'<pre style="font-family:Consolas,monospace;font-size:9pt;line-height:1.4;">{inner}</pre>'

    # ──────────────────────────────────────────────────────────────────
    # Calc Flow Analysis – Tab [3]
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def compute_calc_violations(diagram_data: Dict) -> Set[int]:
        """Return 1-based wire indices where calc_in >= calc_out (FAIL or SAME)."""
        blocks      = diagram_data.get("blocks", [])
        connections = diagram_data.get("connections", [])
        seq_calls   = diagram_data.get("sequence_calls", [])

        block_calc: Dict[str, int] = {}
        for sc in seq_calls:
            oid = sc.get("block_oid")
            if oid:
                cn = sc.get("calc_num")
                if cn is not None:
                    if oid not in block_calc or cn < block_calc[oid]:
                        block_calc[oid] = cn

        port_to_block: Dict[str, str] = {}
        for b in blocks:
            bid = b["id"]
            port_to_block[bid] = bid
            for p in b.get("ports", []):
                port_to_block[p["id"]] = bid

        violations: Set[int] = set()
        for wire_idx, conn in enumerate(connections, 1):
            src_block_oid = port_to_block.get(conn["source_oid"])
            tgt_block_oid = port_to_block.get(conn["target_oid"])
            src_calc = block_calc.get(src_block_oid) if src_block_oid else None
            tgt_calc = block_calc.get(tgt_block_oid) if tgt_block_oid else None
            if src_calc is not None and tgt_calc is not None and tgt_calc <= src_calc:
                violations.add(wire_idx)
        return violations

    @staticmethod
    def build_calc_flow_html(diagram_data: Dict, scope_dict: Optional[Dict] = None) -> str:
        """
        Build HTML for the Calc-Flow tab.

        For every connection wire:
          • identifies the SOURCE block (output side) and its calc/sequence number
          • identifies the TARGET block  (input  side) and its calc/sequence number
          • validates the user-defined rule:  calc_in < calc_out
            (the consumer block runs at a lower sequence number than the producer,
             meaning it reads the value produced in the PREVIOUS cycle)

        Also outputs the same data as pretty-printed JSON at the bottom of the tab.
        """
        def esc(s: str) -> str:
            return _html.escape(str(s))

        blocks      = diagram_data.get("blocks", [])
        connections = diagram_data.get("connections", [])
        seq_calls   = diagram_data.get("sequence_calls", [])

        # ── Build block_oid → minimum calc_num ─────────────────────────
        block_calc: Dict[str, int] = {}
        for sc in seq_calls:
            oid = sc.get("block_oid")
            if oid:
                cn = sc.get("calc_num")
                if cn is not None:
                    if oid not in block_calc or cn < block_calc[oid]:
                        block_calc[oid] = cn

        # ── Build helper maps ──────────────────────────────────────────
        port_to_block: Dict[str, str] = {}   # port_oid / block_oid → owning block_oid
        block_name_map: Dict[str, str] = {}
        block_ports_map: Dict[str, Dict] = {}  # block_oid → {inputs, outputs}

        for b in blocks:
            bid   = b["id"]
            bname = b.get("name", "")
            port_to_block[bid]  = bid
            block_name_map[bid] = bname
            block_ports_map[bid] = {"inputs": [], "outputs": []}
            for p in b.get("ports", []):
                port_to_block[p["id"]] = bid
                ptag  = p.get("tag", "")
                pname = p.get("name", "") or ptag
                if ptag == "ReturnPort":
                    block_ports_map[bid]["outputs"].append(pname)
                elif ptag in ("ArgumentPort", "MessagePort", "TriggerPort", "SelectorPort"):
                    block_ports_map[bid]["inputs"].append(pname)

        oid_map = ConnectionLogicExtractor._build_oid_map(diagram_data)

        # ── Build per-wire records ─────────────────────────────────────
        wire_records: List[Dict] = []
        violations: List[int]   = []
        unknowns:  List[int]    = []

        for wire_idx, conn in enumerate(connections, 1):
            si = oid_map.get(conn["source_oid"])
            ti = oid_map.get(conn["target_oid"])
            if not si or not ti:
                continue

            src_block_oid = port_to_block.get(conn["source_oid"])
            tgt_block_oid = port_to_block.get(conn["target_oid"])
            src_calc = block_calc.get(src_block_oid) if src_block_oid else None
            tgt_calc = block_calc.get(tgt_block_oid) if tgt_block_oid else None

            src_name = si["block_name"] or conn["source_oid"]
            tgt_name = ti["block_name"] or conn["target_oid"]
            src_port = si.get("port_name", "")
            tgt_port = ti.get("port_name", "")

            if src_calc is None or tgt_calc is None:
                status = "UNKNOWN"
                unknowns.append(wire_idx)
            elif tgt_calc > src_calc:   # calc_in < calc_out → VALID
                status = "VALID"
            elif tgt_calc == src_calc:
                status = "SAME"
            else:                        # calc_in > calc_out → VIOLATION
                status = "FAIL"
                violations.append(wire_idx)

            wire_records.append({
                "wire": wire_idx,
                "source": {
                    "block": src_name,
                    "port":  src_port if src_port != "Self" else "",
                    "role":  "out",
                    "calc":  src_calc,
                },
                "target": {
                    "block": tgt_name,
                    "port":  tgt_port if tgt_port != "Self" else "",
                    "role":  "in",
                    "calc":  tgt_calc,
                },
                "status": status,
            })

        # ── JSON data ──────────────────────────────────────────────────
        json_blocks = []
        for b in blocks:
            bid   = b["id"]
            bname = b.get("name", "")
            ports = block_ports_map.get(bid, {})
            json_blocks.append({
                "name":    bname,
                "id":      bid,
                "calc":    block_calc.get(bid),
                "outputs": ports.get("outputs", []),
                "inputs":  ports.get("inputs",  []),
            })

        summary_data = {
            "total_wires":                     len(wire_records),
            "valid_calc_in_lt_calc_out":        sum(1 for r in wire_records if r["status"] == "VALID"),
            "violations_calc_in_gte_calc_out":  len(violations),
            "unknown_no_calc_number":           len(unknowns),
            "violation_wire_indices":           violations,
        }
        json_data = {
            "diagram":     diagram_data.get("diagram_name", ""),
            "blocks":      json_blocks,
            "connections": wire_records,
            "summary":     summary_data,
        }
        json_str = _json.dumps(json_data, ensure_ascii=False, indent=2)

        # ── HTML rendering ─────────────────────────────────────────────
        W    = 100
        sep  = esc("=" * W)
        thin = esc("-" * W)

        rows = [
            sep,
            "<b>  CALC FLOW ANALYSIS &#8212; INPUT / OUTPUT MAPPING &amp; SEQUENCE VALIDATION</b>",
            esc(f"  Diagram : {diagram_data.get('diagram_name', 'Unknown')}"),
            esc(f"  Rule    : calc_in < calc_out"),
            esc(f"            (consumer block runs at a LOWER sequence number than the"
                f" producer → reads value produced in the PREVIOUS cycle)"),
            thin,
            "",
        ]

        # Table header
        hdr = f"{'Wire':>5}  {'Source Block [OUT]':<34}  {'calc_in':>8}  {'Target Block [IN]':<34}  {'calc_out':>7}  {'Status':>8}"
        rows.append(f'<b style="color:#003580;">{esc(hdr)}</b>')
        rows.append(thin)

        for rec in wire_records:
            src = rec["source"]
            tgt = rec["target"]
            src_label = f"{src['block']}.{src['port']}" if src["port"] else src["block"]
            tgt_label = f"{tgt['block']}.{tgt['port']}" if tgt["port"] else tgt["block"]
            co = str(src["calc"]) if src["calc"] is not None else "?"
            ci = str(tgt["calc"]) if tgt["calc"] is not None else "?"

            st = rec["status"]
            if st == "VALID":
                colour, sym = "#1a8f1a", "&#10003; OK"
            elif st == "FAIL":
                colour, sym = "#cc2222", "&#10007; FAIL"
            elif st == "SAME":
                colour, sym = "#cc7700", "= SAME"
            else:
                colour, sym = "#888888", "?  N/A"

            line = (
                f"{rec['wire']:>5}  {src_label:<34.34}  {co:>8}  "
                f"{tgt_label:<34.34}  {ci:>7}  {sym}"
            )
            rows.append(f'<span style="color:{colour};">{esc(line)}</span>')

        rows.append(sep)
        rows.append("")

        # Summary
        s = summary_data
        rows += [
            f'<b style="color:#003580;">  SUMMARY</b>',
            thin,
            f'  Total wires    : {s["total_wires"]}',
            f'  <span style="color:#1a8f1a;font-weight:bold;">'
            f'Valid   (calc_in &lt; calc_out) : {s["valid_calc_in_lt_calc_out"]}</span>',
            f'  <span style="color:#cc2222;font-weight:bold;">'
            f'Fail    (calc_in &gt;= calc_out): {s["violations_calc_in_gte_calc_out"]}'
            f'{ ("  ← wires: " + str(violations)) if violations else ""}</span>',
            f'  <span style="color:#888;">'
            f'Unknown (no calc info)   : {s["unknown_no_calc_number"]}</span>',
            sep,
            "",
        ]

        # JSON dump
        rows += [
            f'<b style="color:#003580;">  JSON OUTPUT</b>',
            thin,
            f'<span style="color:#444;">{esc(json_str)}</span>',
            sep,
        ]

        inner = "<br>".join(rows)
        return f'<pre style="font-family:Consolas,monospace;font-size:9pt;line-height:1.4;">{inner}</pre>'


# =====================================================================
# GRAPHICS VIEW (Zoom & Pan support)
# =====================================================================
class DiagramGraphicsView(QGraphicsView):
    def __init__(self, scene=None):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setStyleSheet("border: 1px solid #ccc; background-color: white;")
        
    def wheelEvent(self, event):
        """Zoom with mouse wheel"""
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)


# =====================================================================
# MAIN DIALOG: DIAGRAM VIEWER
# =====================================================================
class DiagramViewerDialog(QDialog):
    """Dialog to display diagram with 2 tabs: Visual + Logic"""
    
    def __init__(self, diagram_data: Dict, parent=None,
                 defective_wire_indices: Optional[Set[int]] = None,
                 scope_dict: Optional[Dict] = None,
                 rule_defective_wire_indices: Optional[Set[int]] = None,
                 rule_error_details: Optional[List[Dict]] = None,
                 calc_defective_wire_indices: Optional[Set[int]] = None):
        """
        Parameters
        ----------
        defective_wire_indices:
            None      – no AI review; all wires drawn black
            set()     – reviewed, all wires OK (green)
            {1,3,…}   – 1-based indices of defective wires (red); rest green
        scope_dict:
            name → {scope, implType, min, max}  from DiagramNetlistExtractor.build_element_dict()
            Used to annotate elements and wires with [Imported:type] / [Local:type] etc.
        rule_defective_wire_indices:
            None      – no rule-base review
            set()     – all wires OK per rule-base
            {2,5,…}   – 1-based indices of rule-base defective wires (orange)
        rule_error_details:
            List of rule error dicts from DiagramRuleChecker (rule_key, type, message, severity)
        calc_defective_wire_indices:
            None      – no calc review done
            set()     – all wires OK per calc flow check
            {4,7,…}   – 1-based indices of calc flow execution sequence issues (purple)
        """
        super().__init__(parent)
        self.setWindowTitle(f"📊 Diagram View: {diagram_data.get('diagram_name', 'Unknown')}")
        self.resize(1200, 800)
        
        self.diagram_data = diagram_data
        self.defective_wire_indices = defective_wire_indices
        self.scope_dict = scope_dict or {}
        self.rule_defective_wire_indices = rule_defective_wire_indices
        self.rule_error_details = rule_error_details or []
        self.calc_defective_wire_indices = calc_defective_wire_indices
        self.setup_ui()
        
    def setup_ui(self):
        """Setup UI with 2 tabs"""
        layout = QVBoxLayout(self)
        
        # Top label
        title_label = QLabel(f"📊 Diagram: {self.diagram_data.get('diagram_name', 'Unknown')}")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(title_label)
        
        # Create tabs
        self.tab_widget = QTabWidget()
        
        # TAB 1: Visual Diagram
        self.scene = QGraphicsScene()
        self.view = DiagramGraphicsView(self.scene)

        # Auto-compute calc violations if not provided
        calc_wire_indices = self.calc_defective_wire_indices
        if calc_wire_indices is None:
            computed = ConnectionLogicExtractor.compute_calc_violations(self.diagram_data)
            if computed:
                calc_wire_indices = computed

        renderer = DiagramRenderer(self.scene)
        renderer.render(self.diagram_data, self.defective_wire_indices,
                        self.rule_defective_wire_indices,
                        calc_wire_indices)
        
        self.tab_widget.addTab(self.view, "📊 Visual Diagram")
        
        # TAB 2: Connection Logic  (always HTML for consistent formatting)
        self.logic_text = QTextEdit()
        self.logic_text.setReadOnly(True)
        self.logic_text.setFont(QFont("Consolas", 9))
        self.logic_text.setStyleSheet("background-color: #f5f5f5;")

        logic_container = QWidget()
        lc_layout = QVBoxLayout(logic_container)
        lc_layout.setContentsMargins(0, 0, 0, 0)
        lc_layout.setSpacing(0)

        has_any_review = (self.defective_wire_indices is not None
                          or self.rule_defective_wire_indices is not None
                          or self.calc_defective_wire_indices is not None)
        
        if has_any_review:
            legend_parts = [
                "Legend: ",
                "<span style='color:#1a8f1a;font-weight:bold;'>&#9632; Correct</span>",
                "&nbsp;&nbsp;",
                "<span style='color:#cc2222;font-weight:bold;'>&#9632; AI Defective</span>",
                "&nbsp;&nbsp;",
                "<span style='color:#cc7700;font-weight:bold;'>&#9632; Rule-base Issue</span>",
                "&nbsp;&nbsp;",
                "<span style='color:#800080;font-weight:bold;'>&#9632; Calc Flow Issue</span>",
                "&nbsp;&nbsp;&nbsp;&nbsp;",
                "<span style='color:#b35900;font-weight:bold;'>[Imported]</span>",
                "&nbsp;",
                "<span style='color:#006060;font-weight:bold;'>[Local]</span>",
                "&nbsp;",
                "<span style='color:#5a0080;font-weight:bold;'>[Constant]</span>",
                "&nbsp;&nbsp;",
                "<span style='color:#880088;font-weight:bold;'>[Phys:~/Impl:~] Range</span>",
            ]
            legend_label = QLabel("".join(legend_parts))
            legend_label.setTextFormat(Qt.RichText)
            legend_label.setStyleSheet(
                "padding:4px 6px; background:#f0f4f0; border-bottom:1px solid #ccc;")
            lc_layout.addWidget(legend_label)
        elif self.scope_dict:
            scope_legend = QLabel(
                "<span style='color:#b35900;font-weight:bold;'>[Imported]</span>"
                "&nbsp;"
                "<span style='color:#006060;font-weight:bold;'>[Local]</span>"
                "&nbsp;"
                "<span style='color:#5a0080;font-weight:bold;'>[Constant]</span>"
                " — scope annotations from ASCET element definitions"
            )
            scope_legend.setTextFormat(Qt.RichText)
            scope_legend.setStyleSheet(
                "padding:4px 6px; background:#f5f5f5; border-bottom:1px solid #ddd;")
            lc_layout.addWidget(scope_legend)

        lc_layout.addWidget(self.logic_text)
        self.tab_widget.addTab(logic_container, "📝 Connection Logic")

        html_content = ConnectionLogicExtractor.extract_html(
            self.diagram_data,
            self.defective_wire_indices,
            self.scope_dict,
            self.rule_defective_wire_indices,
            self.rule_error_details,
        )
        self.logic_text.setHtml(html_content)

        # TAB 3: Calc Flow Analysis
        self.calc_flow_text = QTextEdit()
        self.calc_flow_text.setReadOnly(True)
        self.calc_flow_text.setFont(QFont("Consolas", 9))
        self.calc_flow_text.setStyleSheet("background-color: #f5f5f5;")
        calc_flow_html = ConnectionLogicExtractor.build_calc_flow_html(
            self.diagram_data, self.scope_dict
        )
        self.calc_flow_text.setHtml(calc_flow_html)
        self.tab_widget.addTab(self.calc_flow_text, "🔢 Calc Flow")

        layout.addWidget(self.tab_widget)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)