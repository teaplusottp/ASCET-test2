# -*- coding: utf-8 -*-
"""
ascet DSD Exporter - Simplified version for CLI
Extracts ASCET class implementation data and exports to Excel
"""

import sys
import os
import json
import traceback
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    from win32com.client import Dispatch
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False

try:
    import pandas as pd
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import PatternFill, Border, Side, Alignment, Font
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class AscetDatabaseScanner:
    """
    CLI-optimized ASCET database scanner.
    Connects to ASCET, extracts class data, and exports to Excel.
    """
    
    def __init__(self, version="6.1.4"):
        self.version = version
        self.ascet = None
        self.db = None
        self.all_implementations: Dict[str, List[Dict]] = {}
        self.available_classes: Dict[str, object] = {}
        
    def connect(self) -> bool:
        """Connect to ASCET database via COM interface"""
        if not WIN32COM_AVAILABLE:
            print("ERROR: win32com not available", file=sys.stderr)
            return False
            
        try:
            print(f"[DSD] Connecting to ASCET {self.version}...", file=sys.stderr)
            self.ascet = Dispatch(f"Ascet.Ascet.{self.version}")
            self.db = self.ascet.GetCurrentDataBase()
            
            if not self.db:
                print("ERROR: Could not access ASCET database", file=sys.stderr)
                return False
                
            db_name = self.db.GetName() if hasattr(self.db, 'GetName') else "Unknown"
            print(f"[DSD] Connected to database: {db_name}", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"ERROR: ASCET connection failed: {e}", file=sys.stderr)
            return False
    
    def scan_database(self) -> bool:
        """Scan ASCET database to discover all classes"""
        if not self.db:
            return False
            
        try:
            print("[DSD] Starting database scan...", file=sys.stderr)
            self._scan_folder(self.db, "")
            print(f"[DSD] Found {len(self.available_classes)} classes", file=sys.stderr)
            return len(self.available_classes) > 0
            
        except Exception as e:
            print(f"ERROR: Database scan failed: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return False
    
    def _scan_folder(self, folder, path_prefix: str):
        """Recursively scan ASCET folder structure"""
        try:
            # Check if this folder is a class
            if hasattr(folder, 'IsClass') and folder.IsClass():
                class_name = folder.GetName() if hasattr(folder, 'GetName') else "Unknown"
                class_path = f"{path_prefix}/{class_name}".lstrip("/")
                self.available_classes[class_path] = folder
                print(f"[DSD] Found class: {class_path}", file=sys.stderr)
            
            # Scan subfolders
            if hasattr(folder, 'GetSubFolders'):
                try:
                    subfolders = folder.GetSubFolders()
                    if subfolders:
                        for subfolder in subfolders:
                            if subfolder:
                                subfolder_name = subfolder.GetName() if hasattr(subfolder, 'GetName') else ""
                                new_path = f"{path_prefix}/{subfolder_name}".lstrip("/")
                                self._scan_folder(subfolder, new_path)
                except Exception as e:
                    print(f"[DSD] Error scanning subfolders: {e}", file=sys.stderr)
                    
        except Exception as e:
            print(f"[DSD] Error in folder scan: {e}", file=sys.stderr)
    
    def process_class(self, class_path: str) -> bool:
        """Extract implementation data for a specific class"""
        if class_path not in self.available_classes:
            print(f"ERROR: Class not found: {class_path}", file=sys.stderr)
            return False
            
        try:
            print(f"[DSD] Processing class: {class_path}", file=sys.stderr)
            class_obj = self.available_classes[class_path]
            
            elements_info = []
            if hasattr(class_obj, 'GetAllModelElements'):
                try:
                    model_elements = class_obj.GetAllModelElements()
                    if model_elements:
                        for element in model_elements:
                            if element:
                                elem_data = self._extract_element_data(element)
                                if elem_data:
                                    elements_info.append(elem_data)
                except Exception as e:
                    print(f"[DSD] Error getting model elements: {e}", file=sys.stderr)
            
            if elements_info:
                self.all_implementations[class_path] = elements_info
                print(f"[DSD] Extracted {len(elements_info)} elements from {class_path}", file=sys.stderr)
                return True
            else:
                print(f"[DSD] No elements found in {class_path}", file=sys.stderr)
                return False
                
        except Exception as e:
            print(f"ERROR: Failed to process class {class_path}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return False
    
    def _extract_element_data(self, element) -> Optional[Dict]:
        """Extract key data from a model element"""
        try:
            data = {}
            
            if hasattr(element, 'GetName'):
                data['Name'] = element.GetName()
            if hasattr(element, 'GetType'):
                elem_type = element.GetType()
                data['Type'] = elem_type if elem_type else "Unknown"
            
            # Determine scope
            if hasattr(element, 'GetScope'):
                scope = element.GetScope()
                scope_map = {'local': 'Local', 'imported': 'Imported', 'exported': 'Exported'}
                data['Scope'] = scope_map.get(scope, scope) if scope else 'Unknown'
            
            # Determine kind
            data['Kind'] = self._determine_kind(element)
            
            # Get unit and comment
            if hasattr(element, 'GetUnit'):
                data['Unit'] = element.GetUnit() or '---'
            if hasattr(element, 'GetComment'):
                data['Comment'] = element.GetComment() or '---'
            
            # Try to get implementation info
            if hasattr(element, 'GetImplementation'):
                impl = element.GetImplementation()
                if impl and hasattr(impl, 'GetImplInfoForValue'):
                    impl_info = impl.GetImplInfoForValue()
                    if impl_info:
                        self._extract_implementation_info(data, impl_info)
            
            return data if 'Name' in data else None
            
        except Exception as e:
            print(f"[DSD] Error extracting element data: {e}", file=sys.stderr)
            return None
    
    def _determine_kind(self, element) -> str:
        """Determine element kind (Parameter, Variable, Constant, etc.)"""
        try:
            checks = [
                ('IsConstant', 'Constant'),
                ('IsParameter', 'Parameter'),
                ('IsVariable', 'Variable'),
                ('IsMethodArgument', 'Method Argument'),
                ('IsMethodReturn', 'Return Value'),
            ]
            
            for method, kind_name in checks:
                if hasattr(element, method):
                    try:
                        if getattr(element, method)():
                            return kind_name
                    except:
                        pass
            
            return 'Unknown'
        except:
            return 'Unknown'
    
    def _extract_implementation_info(self, elem_data: Dict, impl_info):
        """Extract implementation-level information (type, ranges, etc.)"""
        try:
            # Impl Type
            if hasattr(impl_info, 'GetImplType'):
                impl_type = impl_info.GetImplType()
                if impl_type:
                    elem_data['Impl. Type'] = impl_type
            
            # Ranges
            range_methods = [
                ('GetIntegerImplRange', int),
                ('GetFloatImplRange', float),
                ('GetDoubleImplRange', float),
            ]
            
            for method_name, conv_type in range_methods:
                if hasattr(impl_info, method_name):
                    try:
                        r = getattr(impl_info, method_name)()
                        if r and len(r) == 2:
                            elem_data['Impl. Min'] = str(conv_type(r[0]))
                            elem_data['Impl. Max'] = str(conv_type(r[1]))
                            break
                    except:
                        pass
                        
        except Exception as e:
            print(f"[DSD] Error in implementation info extraction: {e}", file=sys.stderr)
    
    def export_to_excel(self, output_path: str = None) -> str:
        """Export all collected data to Excel"""
        if not PANDAS_AVAILABLE:
            raise RuntimeError("pandas and openpyxl are required for Excel export")
        
        if not self.all_implementations:
            raise ValueError("No data to export. Run scan_database() and process_class() first.")
        
        try:
            output_path = output_path or os.path.join(os.path.expanduser("~"), "ascet_dsd_export.xlsx")
            
            print(f"[DSD] Exporting to {output_path}...", file=sys.stderr)
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                for class_path, elements in self.all_implementations.items():
                    df = pd.DataFrame(elements)
                    
                    # Sanitize sheet name (max 31 chars, no special chars)
                    sheet_name = os.path.basename(class_path)[:27]
                    sheet_name = "".join(c if c.isalnum() or c in '_-' else '' for c in sheet_name)
                    
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f"[DSD] Exported {len(elements)} elements to sheet: {sheet_name}", file=sys.stderr)
            
            print(f"[DSD] Export complete: {output_path}", file=sys.stderr)
            return output_path
            
        except Exception as e:
            print(f"ERROR: Excel export failed: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise
    
    def disconnect(self):
        """Disconnect from ASCET"""
        if self.ascet:
            try:
                if hasattr(self.ascet, 'DisconnectFromTool'):
                    self.ascet.DisconnectFromTool()
                print("[DSD] Disconnected from ASCET", file=sys.stderr)
            except Exception as e:
                print(f"[DSD] Disconnect warning: {e}", file=sys.stderr)