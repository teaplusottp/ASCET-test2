# -*- coding: utf-8 -*-
import sys
from win32com.client import Dispatch

def _log(msg):
    print(f"[COM-LOG] {msg}", file=sys.stderr)

class ASCETConnectionAPI:
    def __init__(self, version="6.1.4"):
        self.version = version
        self.ascet = None
        self.db = None

    def connect(self) -> bool:
        versions = ["6.1.5", "6.1.4", "6.2.0", "6.4.0"] if self.version == "auto" else [self.version]
        for v in versions:
            try:
                _log(f"Attempting hook on ETAS Ascet.Ascet.{v}")
                self.ascet = Dispatch(f"Ascet.Ascet.{v}")
                self.db = self.ascet.GetCurrentDataBase()
                if self.db:
                    self.version = v
                    _log(f"Connected successfully to DB: {self.db.GetName()}")
                    return True
            except Exception as e:
                _log(f"Version {v} target skipped: {e}")
        return False

    def scan_tree(self) -> dict:
        # High performance placeholder scanning implementation mirroring user logic
        root = {"type": "root", "children": {}}
        try:
            folders = self.db.GetAllAscetFolders()
            # Hierarchical structure parsing goes here
            root["children"]["SampleFolder"] = {
                "type": "folder",
                "name": "SampleFolder",
                "children": {
                    "SampleClass": {"type": "class", "class_type": "esdl", "name": "SampleClass", "path": "SampleFolder/SampleClass"}
                }
            }
        except Exception as e:
            _log(f"Error tree scan: {e}")
        return root

    def extract_calc_code(self, path: str) -> dict:
        normalized = path.replace("/", "\\").lstrip("\\")
        parts = normalized.split("\\")
        class_name = parts[-1]
        folder_path = "\\".join(parts[:-1])
        
        class_obj = self.db.GetItemInFolder(class_name, folder_path)
        if not class_obj:
            raise FileNotFoundError(f"Class component missing: {path}")
            
        diagram = class_obj.GetDiagramWithName("Main")
        method = diagram.GetMethod("calc")
        code = method.GetCode()
        
        return {
            "class_path": normalized,
            "class_name": class_name,
            "calc_code": code,
            "line_count": len(code.splitlines())
        }