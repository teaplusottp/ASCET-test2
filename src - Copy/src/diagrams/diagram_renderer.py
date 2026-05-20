#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagram_renderer.py — Standalone ASCET Diagram Parser + PySide6 Renderer
=========================================================================
Ported / adapted from share_cn.ipynb.

Public API
----------
    data = parse_diagram_xml(amd_path)   -> dict | None
    render_to_png(data, output_path)     -> None   (raises on failure)
"""

import os
import sys
import math
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any


# ─────────────────────────────────────────────────────────────────────────────
# Parser  (share_cn.ipynb  →  parse_diagram_2xml)
# ─────────────────────────────────────────────────────────────────────────────

def parse_diagram_xml(xml_file: str) -> Optional[Dict[str, Any]]:
    """
    Parse an ASCET .specification.amd (or .amd) file and return a diagram_data
    dict suitable for ``render_to_png``.

    Returns ``None`` if the file contains no diagram specification.
    """
    if not os.path.exists(xml_file):
        raise FileNotFoundError(f"Diagram file not found: {xml_file}")

    tree  = ET.parse(xml_file)
    root  = tree.getroot()

    # Strip XML namespaces
    for el in root.iter():
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]

    main_spec = root.find('.//Specification[@name="Main"]')
    if main_spec is None:
        main_spec = root.find('.//Specification')
    if main_spec is None:
        return None

    parent_map = {c: p for p in root.iter() for c in p}

    data: Dict[str, Any] = {
        "diagram_name": os.path.basename(xml_file).replace('.amd', ''),
        "blocks":        [],
        "connections":   [],
        "sequence_calls": [],
    }

    TARGET_TAGS   = ['ComplexElement', 'SimpleElement', 'Literal', 'Operator',
                     'Junction', 'Connector', 'ConnectionPoint']
    DIAGRAM_PORTS = ['ReturnPort', 'ArgumentPort', 'MessagePort', 'Parameter',
                     'TriggerPort', 'SelectorPort']
    VALID_PORT_TAGS = ['ReturnPort', 'SelectorPort', 'ArgumentPort',
                       'TriggerPort', 'MessagePort']

    parsed_blocks: Dict[str, dict] = {}

    for elem in main_spec.iter():
        tag = elem.tag
        if tag not in TARGET_TAGS and tag not in DIAGRAM_PORTS:
            continue

        b_oid = elem.attrib.get('graphicOID', '')
        pos   = elem.find('./Position')
        if not b_oid or pos is None or b_oid == "-1":
            continue

        b_type = tag

        if b_type in DIAGRAM_PORTS:
            p = parent_map.get(elem)
            if p is not None and p.tag == 'DiagramElement':
                b_name = (elem.get('elementName') or elem.get('methodName')
                          or elem.get('name') or b_type)
                if b_type == 'ReturnPort':
                    b_name = f"return / {b_name}"
                b_type = 'SimpleElement'
            else:
                continue
        else:
            if b_type == 'Literal':
                b_name = elem.attrib.get('value', '???')
            elif b_type == 'Operator':
                b_name = elem.attrib.get(
                    'operator', elem.attrib.get('kind', elem.attrib.get('type', 'Op')))
            elif b_type in ('Junction', 'Connector', 'ConnectionPoint'):
                b_name = ''
            else:
                b_name = elem.attrib.get('elementName', elem.tag)

        bx = float(pos.attrib.get('x', 0))
        by = float(pos.attrib.get('y', 0))

        block_data: dict = {
            "id": b_oid, "name": b_name, "type": b_type,
            "x": bx, "y": by, "ports": [],
        }

        interfaces = elem.find('.//Interfaces')
        if interfaces is not None:
            for port in interfaces.iter():
                if port.tag not in VALID_PORT_TAGS:
                    continue
                p_oid = port.attrib.get('graphicOID')
                if not p_oid or p_oid == "-1":
                    continue

                is_visible = port.attrib.get('visibility', 'true').lower() == 'true'
                p_pos = port.find('./Position')
                px = float(p_pos.attrib.get('x', 0)) if p_pos is not None else bx
                py = float(p_pos.attrib.get('y', 0)) if p_pos is not None else by

                p_name = (port.get('name') or port.get('elementName')
                          or port.get('methodName') or port.get('instanceName'))
                if not p_name:
                    par = parent_map.get(port)
                    if par is not None:
                        if par.tag == 'MethodPort':
                            p_name = par.get('methodName') or par.get('name')
                        if not p_name:
                            gpar = parent_map.get(par)
                            if gpar is not None:
                                p_name = (gpar.get('elementName') or gpar.get('instanceName')
                                          or gpar.get('methodName') or gpar.get('ClassName'))
                if not p_name:
                    p_name = port.tag
                if port.attrib.get('nameVisibility', 'true').lower() == 'false':
                    p_name = ''

                block_data["ports"].append({
                    "id": p_oid, "name": p_name,
                    "x": px, "y": py, "is_visible": is_visible,
                })

        # Keep the richer version when we see the same OID twice
        old = parsed_blocks.get(b_oid)
        if old is None or len(block_data["ports"]) > len(old["ports"]):
            parsed_blocks[b_oid] = block_data

    data["blocks"] = list(parsed_blocks.values())

    # Sequence calls
    for seq in main_spec.findall('.//SequenceCall'):
        seq_num    = seq.get('sequenceNumber', '0')
        is_visible = seq.get('userVisibility', 'true').lower() == 'true'
        if not is_visible or seq_num == '0':
            continue
        pos_el = seq.find('./Position')
        if pos_el is None:
            continue
        method_name = seq.get('methodName', '')
        text = f"/{seq_num}/{method_name}" if method_name else f"/{seq_num}/"
        port_method = ''
        par = parent_map.get(seq)
        if par is not None and par.tag == 'MethodPort':
            port_method = par.get('methodName', '')
        data["sequence_calls"].append({
            "text": text, "port_method": port_method,
            "x": float(pos_el.get('x', 0)),
            "y": float(pos_el.get('y', 0)),
        })

    # Connections
    parsed_conns: set = set()
    for conn in main_spec.findall('.//Connection'):
        start = conn.find('.//Start')
        end   = conn.find('.//End')
        if start is None or end is None:
            continue
        src_oid = start.attrib.get('graphicOID')
        tgt_oid = end.attrib.get('graphicOID')
        if not src_oid or not tgt_oid:
            continue
        bends = tuple(
            (float(b.attrib.get('x', 0)), float(b.attrib.get('y', 0)))
            for b in conn.findall('.//BendPoint')
        )
        key = (src_oid, tgt_oid, bends)
        if key in parsed_conns:
            continue
        parsed_conns.add(key)
        data["connections"].append({
            "source_oid": src_oid,
            "target_oid": tgt_oid,
            "bend_points": [{"x": pt[0], "y": pt[1]} for pt in bends],
        })

    return data


# ─────────────────────────────────────────────────────────────────────────────
# Renderer  (share_cn.ipynb  →  render_diagram_pyside)
# ─────────────────────────────────────────────────────────────────────────────

def render_to_png(data: dict, output_path: str) -> None:
    """
    Render *data* (as returned by ``parse_diagram_xml``) to a PNG file at
    *output_path* using PySide6.

    Raises ``RuntimeError`` on failure.
    """
    try:
        import PySide6.QtGui    as _qtgui   # noqa: F401 (trigger lazy import)
        from PySide6.QtCore    import Qt, QRectF, QPointF
        from PySide6.QtWidgets import QApplication, QGraphicsScene
        from PySide6.QtGui     import (QPen, QBrush, QColor, QFont,
                                       QPainter, QImage, QPolygonF,
                                       QPainterPath)
    except ImportError as exc:
        raise RuntimeError(f"PySide6 is required for diagram rendering: {exc}")

    app   = QApplication.instance() or QApplication(sys.argv)
    scene = QGraphicsScene()

    pen_box      = QPen(Qt.black, 1.5)
    pen_line     = QPen(Qt.black, 1.5)
    pen_none     = QPen(Qt.NoPen)
    brush_complex = QBrush(QColor('#e8f4f8'))
    brush_simple  = QBrush(Qt.white)
    brush_literal = QBrush(QColor('#fffcdc'))
    brush_operator= QBrush(QColor('#e8f4f8'))
    brush_red     = QBrush(QColor('#cc3333'))
    brush_black   = QBrush(Qt.black)

    font_bold   = QFont("Consolas", 9, QFont.Bold)
    font_normal = QFont("Consolas", 7)
    font_op     = QFont("Consolas", 12, QFont.Bold)

    port_coords: dict = {}
    source_oids = {c['source_oid'] for c in data['connections']}
    target_oids = {c['target_oid'] for c in data['connections']}

    for block in data['blocks']:
        b_type = block['type']
        b_name = block['name']
        bx, by = block['x'], block['y']

        if b_type == 'Literal':
            t = scene.addText(str(b_name), font_normal)
            tw, th = t.boundingRect().width(), t.boundingRect().height()
            scene.addRect(bx - tw - 6, by - th/2, tw + 6, th, pen_line, brush_literal).setZValue(0)
            t.setPos(bx - tw - 3, by - th/2); t.setZValue(2)
            port_coords[block['id']] = (bx, by)

        elif b_type == 'Operator':
            r = 12
            scene.addEllipse(bx - r, by - r, r*2, r*2, pen_box, brush_operator).setZValue(0)
            t = scene.addText(b_name, font_op)
            t.setPos(bx - t.boundingRect().width()/2, by - t.boundingRect().height()/2 - 1)
            t.setZValue(2)
            port_coords[block['id']] = (bx, by)

        elif b_type in ('Junction', 'Connector', 'ConnectionPoint'):
            dot = scene.addEllipse(bx - 3, by - 3, 6, 6, pen_none, brush_black)
            dot.setZValue(3)
            port_coords[block['id']] = (bx, by)

        elif b_type == 'ComplexElement':
            v_px = [p['x'] for p in block['ports'] if p.get('is_visible', True)]
            v_py = [p['y'] for p in block['ports'] if p.get('is_visible', True)]
            if v_px and v_py:
                min_x, max_x = min(v_px), max(v_px)
                min_y, max_y = min(v_py), max(v_py)
                w = max_x - min_x
                h = max_y - min_y + 30
                rect_y = min_y - 15
            else:
                min_x, rect_y, w, h = bx, by, 100, 60

            scene.addRect(min_x, rect_y, w, h, pen_box, brush_complex).setZValue(-2)
            t = scene.addText(b_name, font_bold if b_name else font_normal)
            t.setPos(min_x + w/2 - t.boundingRect().width()/2, rect_y + h + 5)
            t.setZValue(2)

            for p in block['ports']:
                if not p.get('is_visible', True):
                    continue
                pid, px, py, pname = p['id'], p['x'], p['y'], p['name']
                port_coords[pid] = (px, py)
                scene.addRect(px - 3, py - 3, 6, 6, pen_box, brush_red).setZValue(1)
                if pname:
                    pt = scene.addText(pname, font_normal)
                    pt.setZValue(2)
                    if px <= min_x + w/2:
                        pt.setPos(px + 4, py - pt.boundingRect().height()/2)
                    else:
                        pt.setPos(px - pt.boundingRect().width() - 4,
                                  py - pt.boundingRect().height()/2)

        elif b_type == 'SimpleElement':
            t = scene.addText(b_name, font_normal)
            tw, th = t.boundingRect().width(), t.boundingRect().height()
            has_in  = any(p['id'] in target_oids for p in block.get('ports', []))
            has_out = any(p['id'] in source_oids for p in block.get('ports', []))
            is_tgt  = has_in and not has_out
            if is_tgt:
                scene.addRect(bx, by - th/2, tw + 6, th, pen_line, brush_simple).setZValue(0)
                t.setPos(bx + 3, by - th/2)
            else:
                scene.addRect(bx - tw - 6, by - th/2, tw + 6, th, pen_line, brush_simple).setZValue(0)
                t.setPos(bx - tw - 3, by - th/2)
            t.setZValue(2)
            if not block['ports']:
                port_coords[block['id']] = (bx, by)
            else:
                for p in block['ports']:
                    port_coords[p['id']] = (bx, by)

    # Draw connections
    for conn in data['connections']:
        src, tgt = conn['source_oid'], conn['target_oid']
        if src not in port_coords or tgt not in port_coords:
            continue
        pts = [(port_coords[src][0], port_coords[src][1])]
        for bend in conn.get('bend_points', []):
            pts.append((bend['x'], bend['y']))
        pts.append((port_coords[tgt][0], port_coords[tgt][1]))

        path = QPainterPath()
        path.moveTo(pts[0][0], pts[0][1])
        for pt in pts[1:]:
            path.lineTo(pt[0], pt[1])
        scene.addPath(path, pen_line).setZValue(-1)

        # Arrowhead at end
        for i in range(len(pts) - 1, 0, -1):
            px1, py1 = pts[i - 1]
            px2, py2 = pts[i]
            dist = math.hypot(px2 - px1, py2 - py1)
            if dist > 1e-3:
                dx, dy = (px2 - px1) / dist, (py2 - py1) / dist
                nx, ny = -dy, dx
                arrow = scene.addPolygon(
                    QPolygonF([
                        QPointF(px2, py2),
                        QPointF(px2 - 8*dx + 4*nx, py2 - 8*dy + 4*ny),
                        QPointF(px2 - 8*dx - 4*nx, py2 - 8*dy - 4*ny),
                    ]),
                    pen_none, brush_black
                )
                arrow.setZValue(2)
                break

    # Sequence-call markers
    for seq in data.get('sequence_calls', []):
        sx, sy = seq['x'], seq['y']
        scene.addRect(sx - 2, sy - 2, 4, 4, pen_line, brush_red).setZValue(3)
        if seq.get('port_method'):
            pm = scene.addText(f".{seq['port_method']}", font_normal)
            pm.setPos(sx + 3, sy - 16); pm.setZValue(4)
        si = scene.addText(seq['text'], font_normal)
        si.setPos(sx + 3, sy + (-6 if seq.get('port_method') else -10))
        si.setZValue(4)

    # Export to PNG
    final_rect = scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
    sz = final_rect.size().toSize()
    if sz.width() < 1 or sz.height() < 1:
        raise RuntimeError("Empty diagram — nothing to render.")

    image = QImage(sz, QImage.Format_ARGB32)
    image.fill(Qt.white)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    scene.render(painter, target=QRectF(image.rect()), source=final_rect)
    painter.end()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    if not image.save(output_path):
        raise RuntimeError(f"QImage.save() failed for path: {output_path}")
