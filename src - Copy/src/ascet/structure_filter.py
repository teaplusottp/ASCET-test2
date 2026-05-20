# -*- coding: utf-8 -*-
"""
ASCET Database Structure Scanner API 
- Default behavior: only keep ESDL classes that have a "calc" method inside the "Main" diagram.
"""

from win32com.client import Dispatch
import pythoncom  # COM initialization
import traceback
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class ScanResult:
    """Data class for scan results"""
    success: bool
    classes_found: int
    scan_time: float
    message: str
    data: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class ScanStatistics:
    """Data class for scan statistics"""
    total_classes: int
    total_folders: int
    scan_duration: float
    classes_per_second: float
    folder_distribution: Dict[str, int]
    deepest_path_level: int
    timestamp: str
    esdl_classes: int
    non_esdl_classes_filtered: int


class ASCETStructureScannerAPI:
    """
    ASCET Database Structure Scanner API
    Provides efficient scanning and analysis of ASCET database structures.
    """

    def __init__(self, version: str = "6.1.4", debug: bool = False):
        """
        Initialize the ASCET structure scanner.

        Args:
            version: ASCET version, default "6.1.4"
            debug: Enable verbose logging if True
        """
        self.version = version
        self.debug = debug
        self.ascet = None
        self.db = None
        self._com_initialized = False  # track COM init state

        # Scanning state
        self._all_classes: Dict[str, Any] = {}
        self._processed_paths: Set[str] = set()
        self._scan_start_time: Optional[datetime] = None

        # Stats
        self._stats: Optional[ScanStatistics] = None
        self._esdl_count = 0
        self._non_esdl_filtered = 0

    # -----------------------------
    # Connect / Disconnect
    # -----------------------------
    def _initialize_com(self) -> bool:
        """Initialize COM library"""
        try:
            if not self._com_initialized:
                pythoncom.CoInitialize()
                self._com_initialized = True
                if self.debug:
                    print("COM initialized")
            return True
        except Exception as e:
            if self.debug:
                print(f"COM initialization failed: {str(e)}")
            return False

    def _uninitialize_com(self):
        """Uninitialize COM library"""
        try:
            if self._com_initialized:
                pythoncom.CoUninitialize()
                self._com_initialized = False
                if self.debug:
                    print("COM uninitialized")
        except Exception as e:
            if self.debug:
                print(f"COM uninit warning: {str(e)}")

    def connect(self) -> ScanResult:
        """
        Connect to the ASCET database.

        Returns:
            ScanResult
        """
        try:
            if not self._initialize_com():
                return ScanResult(
                    success=False,
                    classes_found=0,
                    scan_time=0.0,
                    message="Connect failed",
                    error="COM initialization failed"
                )

            if self.debug:
                print(f"Connecting to ASCET {self.version}...")

            # Create ASCET application and get current DB
            self.ascet = Dispatch(f"Ascet.Ascet.{self.version}")
            self.db = self.ascet.GetCurrentDataBase()

            if self.db:
                db_name = self.db.GetName()
                message = f"Connected to ASCET {self.version}, database: {db_name}"
                if self.debug:
                    print(message)
                return ScanResult(
                    success=True,
                    classes_found=0,
                    scan_time=0.0,
                    message=message,
                    data={"database_name": db_name, "version": self.version}
                )
            else:
                return ScanResult(
                    success=False,
                    classes_found=0,
                    scan_time=0.0,
                    message="Connect failed",
                    error="Could not get current database"
                )

        except Exception as e:
            err = f"Failed to connect ASCET: {str(e)}"
            if self.debug:
                print(err)
                traceback.print_exc()
            return ScanResult(
                success=False,
                classes_found=0,
                scan_time=0.0,
                message="Connect failed",
                error=err
            )

    def disconnect(self) -> ScanResult:
        """Disconnect from ASCET"""
        try:
            if self.ascet:
                try:
                    if hasattr(self.ascet, 'DisconnectFromTool'):
                        self.ascet.DisconnectFromTool()
                except Exception:
                    pass
                self.ascet = None
                self.db = None

            self._uninitialize_com()

            msg = "Disconnected from ASCET"
            if self.debug:
                print(msg)
            return ScanResult(True, 0, 0.0, msg)

        except Exception as e:
            err = f"Error on disconnect: {str(e)}"
            if self.debug:
                print(err)
            return ScanResult(False, 0, 0.0, "Disconnect failed", error=err)

    def __del__(self):
        """Ensure COM is uninitialized"""
        try:
            self._uninitialize_com()
        except Exception:
            pass

    # -----------------------------
    # Scanning & structure
    # -----------------------------
    def scan_all_classes(
        self,
        require_calc: bool = True,
        diagram_name: str = "Main",
        method_name: str = "calc",
        esdl_only: bool = True
    ) -> ScanResult:
        """
        Scan all classes in the database.

        Args:
            require_calc: If True (default), keep only classes that have a given method in a given diagram.
            diagram_name: Diagram name to check, default "Main"
            method_name: Method name to check, default "calc"
            esdl_only: If True (default), keep only ESDL classes

        Returns:
            ScanResult
        """
        try:
            if not self.db:
                return ScanResult(False, 0, 0.0, "Not connected", error="Call connect() first")

            if self.debug:
                print("\nStarting full-database class scan...")
                if esdl_only:
                    print("Filter: ESDL classes only")
                if require_calc:
                    print(f"Filter: Classes with '{method_name}' method in '{diagram_name}' diagram")

            start_time = datetime.now()
            self._scan_start_time = start_time

            # Reset state
            self._all_classes.clear()
            self._processed_paths.clear()
            self._esdl_count = 0
            self._non_esdl_filtered = 0

            # Top-level folders
            top_folders = self._get_top_level_folders()
            if not top_folders:
                return ScanResult(False, 0, 0.0, "Scan failed", error="No top-level folders found")

            if self.debug:
                print(f"Found {len(top_folders)} top-level folders")

            # Walk
            for folder in top_folders:
                if folder:
                    try:
                        folder_name = folder.GetName()
                        if self.debug:
                            print(f"Scanning: {folder_name}")
                        self._scan_folder_recursive(
                            folder,
                            folder_name,
                            None,
                            require_calc=require_calc,
                            diagram_name=diagram_name,
                            method_name=method_name,
                            esdl_only=esdl_only
                        )
                    except Exception as folder_error:
                        if self.debug:
                            print(f"Error processing folder: {str(folder_error)}")
                        continue

            # Stats
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            classes_count = len(self._all_classes)
            speed = classes_count / duration if duration > 0 else 0

            self._generate_statistics(duration)

            msg = f"Scan completed: {classes_count} ESDL classes found in {duration:.2f}s"
            if self.debug:
                print(msg)
                print(f"Average speed: {speed:.1f} classes/s")
                print(f"ESDL classes found: {self._esdl_count}")
                print(f"Non-ESDL classes filtered out: {self._non_esdl_filtered}")

            return ScanResult(True, classes_count, duration, msg, data={"class_paths": list(self._all_classes.keys())})

        except Exception as e:
            err = f"Error scanning all classes: {str(e)}"
            if self.debug:
                print(err)
                traceback.print_exc()
            return ScanResult(False, 0, 0.0, "Scan failed", error=err)

    def scan_folder(
        self,
        folder_path: str,
        require_calc: bool = True,
        diagram_name: str = "Main",
        method_name: str = "calc",
        esdl_only: bool = True
    ) -> ScanResult:
        """
        Scan all classes under a specific folder path.

        Args:
            folder_path: Folder path like "PlatformLibrary\\Package"
            require_calc: If True (default), keep only classes that have a given method in a given diagram.
            diagram_name: Diagram name to check, default "Main"
            method_name: Method name to check, default "calc"
            esdl_only: If True (default), keep only ESDL classes

        Returns:
            ScanResult
        """
        try:
            if not self.db:
                return ScanResult(False, 0, 0.0, "Not connected", error="Call connect() first")

            if self.debug:
                print(f"\nScanning folder: {folder_path}")
                if esdl_only:
                    print("Filter: ESDL classes only")

            start_time = datetime.now()

            # Reset counters
            self._esdl_count = 0
            self._non_esdl_filtered = 0

            # Normalize path
            normalized_path = folder_path.replace('/', '\\')
            if normalized_path.startswith('\\'):
                normalized_path = normalized_path[1:]

            folder_obj = self._get_folder_by_path(normalized_path)
            if not folder_obj:
                return ScanResult(False, 0, 0.0, "Scan failed", error=f"Folder not found: {folder_path}")

            # Do scan
            folder_classes: Dict[str, Any] = {}
            self._scan_folder_recursive(
                folder_obj,
                normalized_path,
                folder_classes,
                require_calc=require_calc,
                diagram_name=diagram_name,
                method_name=method_name,
                esdl_only=esdl_only
            )

            # Stats
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            classes_count = len(folder_classes)

            msg = f"Folder scan completed: {classes_count} ESDL classes found in {duration:.2f}s"
            if self.debug:
                print(msg)
                print(f"ESDL classes found: {self._esdl_count}")
                print(f"Non-ESDL classes filtered out: {self._non_esdl_filtered}")
                if folder_classes:
                    print("\nESDL classes found:")
                    for i, class_path in enumerate(sorted(folder_classes.keys()), 1):
                        print(f"  {i:2d}. {class_path}")

            return ScanResult(True, classes_count, duration, msg,
                              data={"class_paths": list(folder_classes.keys()), "folder_path": folder_path})

        except Exception as e:
            err = f"Error scanning folder: {str(e)}"
            if self.debug:
                print(err)
                traceback.print_exc()
            return ScanResult(False, 0, 0.0, "Scan failed", error=err)

    def build_structure_tree(self, base_path: str = "", esdl_only: bool = True) -> ScanResult:
        """
        Build a full folder structure tree.

        Args:
            base_path: If empty, build the full tree from top-level
            esdl_only: If True (default), include only ESDL classes

        Returns:
            ScanResult with the structure tree
        """
        try:
            if not self.db:
                return ScanResult(False, 0, 0.0, "Not connected", error="Call connect() first")

            if self.debug:
                print("\nBuilding structure tree...")
                if esdl_only:
                    print("Filter: ESDL classes only")

            start_time = datetime.now()

            # Reset counters
            self._esdl_count = 0
            self._non_esdl_filtered = 0

            if base_path:
                folder_obj = self._get_folder_by_path(base_path)
                if folder_obj:
                    tree = self._build_tree_recursive(folder_obj, base_path, esdl_only=esdl_only)
                else:
                    return ScanResult(False, 0, 0.0, "Build failed", error=f"Path not found: {base_path}")
            else:
                tree: Dict[str, Any] = {"folders": {}, "classes": []}
                top_folders = self._get_top_level_folders()
                for folder in top_folders:
                    if folder:
                        folder_name = folder.GetName()
                        tree["folders"][folder_name] = self._build_tree_recursive(folder, folder_name, esdl_only=esdl_only)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            classes_count = self._count_classes_in_tree(tree)
            msg = f"Structure tree built: {classes_count} ESDL classes, in {duration:.2f}s"
            if self.debug:
                print(msg)
                print(f"ESDL classes found: {self._esdl_count}")
                print(f"Non-ESDL classes filtered out: {self._non_esdl_filtered}")

            return ScanResult(True, classes_count, duration, msg,
                              data={"structure_tree": tree, "base_path": base_path})

        except Exception as e:
            err = f"Error building structure tree: {str(e)}"
            if self.debug:
                print(err)
                traceback.print_exc()
            return ScanResult(False, 0, 0.0, "Build failed", error=err)

    def find_classes(self, pattern: str, case_sensitive: bool = False) -> ScanResult:
        """
        Find classes by substring match (searches in the paths collected by the last scan).

        Args:
            pattern: Substring to search in class paths
            case_sensitive: Case sensitivity flag

        Returns:
            ScanResult
        """
        try:
            if not self._all_classes:
                return ScanResult(False, 0, 0.0, "Search failed",
                                  error="No class data to search. Run a scan first.")

            start_time = datetime.now()

            search_pattern = pattern if case_sensitive else pattern.lower()
            matches: Dict[str, Any] = {}

            for path, class_obj in self._all_classes.items():
                search_path = path if case_sensitive else path.lower()
                if search_pattern in search_path:
                    matches[path] = class_obj

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            msg = f"Found {len(matches)} matching ESDL classes"
            if self.debug:
                print(f"Search pattern: '{pattern}' -> {msg}")
                for path in sorted(matches.keys()):
                    print(f"  - {path}")

            return ScanResult(True, len(matches), duration, msg,
                              data={"matches": list(matches.keys()), "pattern": pattern})

        except Exception as e:
            err = f"Error searching classes: {str(e)}"
            if self.debug:
                print(err)
            return ScanResult(False, 0, 0.0, "Search failed", error=err)

    def get_statistics(self) -> Optional[ScanStatistics]:
        """Return statistics from the last scan"""
        return self._stats

    def export_results(self, output_dir: str = ".", format: str = "json") -> ScanResult:
        """
        Export scan results.

        Args:
            output_dir: Output directory
            format: 'json', 'txt', or 'both'

        Returns:
            ScanResult
        """
        try:
            if not self._all_classes:
                return ScanResult(False, 0, 0.0, "Export failed",
                                  error="No data to export. Run a scan first.")

            Path(output_dir).mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            exported_files: List[str] = []

            export_data = {
                "scan_info": {
                    "timestamp": datetime.now().isoformat(),
                    "ascet_version": self.version,
                    "total_esdl_classes": len(self._all_classes),
                    "statistics": asdict(self._stats) if self._stats else None
                },
                "esdl_classes": sorted(self._all_classes.keys())
            }

            # JSON
            if format in ["json", "both"]:
                json_file = Path(output_dir) / f"ascet_esdl_structure_{timestamp}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                exported_files.append(str(json_file))

            # TXT
            if format in ["txt", "both"]:
                txt_file = Path(output_dir) / f"ascet_esdl_structure_{timestamp}.txt"
                with open(txt_file, 'w', encoding='utf-8') as f:
                    f.write("ASCET Database ESDL Structure Scan Results\n")
                    f.write("=" * 60 + "\n")
                    f.write(f"Scan time: {export_data['scan_info']['timestamp']}\n")
                    f.write(f"ASCET version: {export_data['scan_info']['ascet_version']}\n")
                    f.write(f"Total ESDL classes: {export_data['scan_info']['total_esdl_classes']}\n")

                    if self._stats:
                        f.write(f"Duration: {self._stats.scan_duration:.2f} s\n")
                        f.write(f"Throughput: {self._stats.classes_per_second:.1f} classes/s\n")
                        f.write(f"ESDL classes found: {self._stats.esdl_classes}\n")
                        f.write(f"Non-ESDL classes filtered: {self._stats.non_esdl_classes_filtered}\n")

                    f.write("\nAll ESDL classes:\n")
                    f.write("-" * 40 + "\n")
                    for i, path in enumerate(export_data['esdl_classes'], 1):
                        f.write(f"{i:4d}. {path}\n")

                    if self._stats and self._stats.folder_distribution:
                        f.write("\nBy top-level folder:\n")
                        f.write("-" * 40 + "\n")
                        for folder, count in sorted(self._stats.folder_distribution.items()):
                            f.write(f"  {folder}: {count} ESDL classes\n")

                exported_files.append(str(txt_file))

            msg = f"Exported {len(exported_files)} file(s)"
            if self.debug:
                print(msg)
                for file in exported_files:
                    print(f"  {file}")

            return ScanResult(True, len(self._all_classes), 0.0, msg, data={"exported_files": exported_files})

        except Exception as e:
            err = f"Error exporting results: {str(e)}"
            if self.debug:
                print(err)
                traceback.print_exc()
            return ScanResult(False, 0, 0.0, "Export failed", error=err)

    def get_class_paths(self) -> List[str]:
        """Return a sorted list of all ESDL class paths from the last scan"""
        return sorted(self._all_classes.keys())

    def get_class_object(self, class_path: str) -> Optional[Any]:
        """Return the COM class object by path (from the last scan), or None"""
        return self._all_classes.get(class_path)

    # -----------------------------
    # Private helpers
    # -----------------------------
    def _get_top_level_folders(self) -> List[Any]:
        """Get all top-level folders"""
        try:
            top_folders: List[Any] = []

            # Method 1: GetAllAscetFolders
            try:
                get_folders_attr = getattr(self.db, "GetAllAscetFolders", None)
                if get_folders_attr:
                    folders = get_folders_attr() if callable(get_folders_attr) else get_folders_attr
                    if isinstance(folders, (tuple, list)):
                        top_folders.extend([f for f in folders if f])
                    elif folders:
                        top_folders.append(folders)
            except Exception:
                pass

            # Method 2: GetAllFolders (fallback)
            if not top_folders:
                try:
                    folders = self.db.GetAllFolders()
                    if folders:
                        if isinstance(folders, (tuple, list)):
                            top_folders.extend([f for f in folders if f])
                        else:
                            top_folders.append(folders)
                except Exception:
                    pass

            return top_folders

        except Exception:
            return []

    def _get_folder_by_path(self, folder_path: str) -> Optional[Any]:
        """Resolve a folder object by path like 'A\\B\\C'"""
        try:
            parts = folder_path.split('\\')
            folder_name = parts[-1]
            parent_path = '\\'.join(parts[:-1]) if len(parts) > 1 else ""

            if not parent_path:
                for folder in self._get_top_level_folders():
                    if folder and folder.GetName() == folder_name:
                        return folder
                return None

            try:
                return self.db.GetItemInFolder(folder_name, parent_path)
            except Exception:
                return None

        except Exception:
            return None

    def _is_esdl_class(self, class_item: Any) -> bool:
        """
        Check whether a class is an ESDL class using IsClassESDL() method.
        Any exception or missing API is treated as "not ESDL".
        """
        try:
            is_esdl_method = getattr(class_item, "IsClassESDL", None)
            if not is_esdl_method or not callable(is_esdl_method):
                return False
            return bool(is_esdl_method())
        except Exception:
            return False

    def _class_has_method_in_diagram(
        self,
        class_item: Any,
        diagram_name: str = "Main",
        method_name: str = "calc"
    ) -> bool:
        """
        Check whether a class contains a given method in a given diagram.
        Any exception or missing API is treated as "does not satisfy".
        """
        try:
            get_diagram = getattr(class_item, "GetDiagramWithName", None)
            if not get_diagram or not callable(get_diagram):
                return False

            diagram = get_diagram(diagram_name)
            if not diagram:
                return False

            get_method = getattr(diagram, "GetMethod", None)
            if not get_method or not callable(get_method):
                return False

            method = get_method(method_name)
            return bool(method)
        except Exception:
            return False

    def _scan_folder_recursive(
        self,
        folder: Any,
        folder_path: str,
        results: Optional[Dict[str, Any]] = None,
        require_calc: bool = True,
        diagram_name: str = "Main",
        method_name: str = "calc",
        esdl_only: bool = True
    ):
        """Recursively scan classes (supports optional filtering by diagram/method and ESDL type)"""
        try:
            if not folder or folder_path in self._processed_paths:
                return

            self._processed_paths.add(folder_path)

            if results is None:
                results = self._all_classes

            # If current node is a class, decide whether to keep it
            if hasattr(folder, 'IsClass') and folder.IsClass():
                # Check ESDL filter first
                if esdl_only:
                    if not self._is_esdl_class(folder):
                        self._non_esdl_filtered += 1
                        if self.debug:
                            print(f"Filtered (non-ESDL): {folder_path}")
                        return  # Skip non-ESDL classes completely
                    else:
                        self._esdl_count += 1

                # Check calc method filter
                if (not require_calc) or self._class_has_method_in_diagram(folder, diagram_name, method_name):
                    results[folder_path] = folder
                    if self.debug:
                        print(f"ESDL Class: {folder_path}")
                # continue to traverse items just in case

            # Items
            items = self._get_all_items(folder)
            if items:
                for item in items:
                    if not item:
                        continue
                    try:
                        item_name = item.GetName()
                        item_path = f"{folder_path}\\{item_name}"

                        if hasattr(item, 'IsClass') and item.IsClass():
                            # Check ESDL filter first
                            if esdl_only:
                                if not self._is_esdl_class(item):
                                    self._non_esdl_filtered += 1
                                    if self.debug:
                                        print(f"Filtered (non-ESDL): {item_path}")
                                    continue  # Skip non-ESDL classes
                                else:
                                    self._esdl_count += 1

                            # Check calc method filter
                            if (not require_calc) or self._class_has_method_in_diagram(item, diagram_name, method_name):
                                results[item_path] = item
                                if self.debug:
                                    print(f"ESDL Class: {item_path}")
                        elif hasattr(item, 'IsFolder') and item.IsFolder():
                            self._scan_folder_recursive(
                                item, item_path, results,
                                require_calc=require_calc,
                                diagram_name=diagram_name,
                                method_name=method_name,
                                esdl_only=esdl_only
                            )
                    except Exception:
                        continue

            # Subfolders
            subfolders = self._get_subfolders(folder)
            if subfolders:
                for sub in subfolders:
                    if not sub:
                        continue
                    try:
                        sub_name = sub.GetName()
                        sub_path = f"{folder_path}\\{sub_name}"
                        self._scan_folder_recursive(
                            sub, sub_path, results,
                            require_calc=require_calc,
                            diagram_name=diagram_name,
                            method_name=method_name,
                            esdl_only=esdl_only
                        )
                    except Exception:
                        continue

        except Exception:
            pass

    def _build_tree_recursive(self, folder: Any, folder_path: str, esdl_only: bool = True) -> Optional[Dict[str, Any]]:
        """Recursively build a folder tree (with optional ESDL filtering)"""
        try:
            node: Dict[str, Any] = {
                "name": folder.GetName() if hasattr(folder, 'GetName') else "Unknown",
                "path": folder_path,
                "type": "folder",
                "children": {}
            }

            if hasattr(folder, 'IsClass') and folder.IsClass():
                # Check ESDL filter
                if esdl_only:
                    if not self._is_esdl_class(folder):
                        self._non_esdl_filtered += 1
                        return None  # Skip non-ESDL classes
                    else:
                        self._esdl_count += 1

                node["type"] = "class"
                node["class_type"] = "ESDL"
                return node

            items = self._get_all_items(folder)
            subfolders = self._get_subfolders(folder)

            children: List[Any] = []
            if items:
                children.extend(items)
            if subfolders:
                children.extend(subfolders)

            for child in children:
                if not child:
                    continue
                try:
                    name = child.GetName()
                    child_path = f"{folder_path}\\{name}"
                    child_node = self._build_tree_recursive(child, child_path, esdl_only=esdl_only)
                    if child_node:  # Only add if not filtered out
                        node["children"][name] = child_node
                except Exception:
                    continue

            return node

        except Exception:
            return None

    def _get_all_items(self, folder: Any) -> List[Any]:
        """Return all database items inside a folder"""
        try:
            if hasattr(folder, 'GetAllDataBaseItems'):
                getter = getattr(folder, 'GetAllDataBaseItems')
                items = getter() if callable(getter) else getter
                if isinstance(items, (tuple, list)):
                    return list(items)
                elif items:
                    return [items]
            return []
        except Exception:
            return []

    def _get_subfolders(self, folder: Any) -> List[Any]:
        """Return all subfolders inside a folder"""
        try:
            if hasattr(folder, 'GetSubFolders'):
                subs = folder.GetSubFolders()
                if isinstance(subs, (tuple, list)):
                    return list(subs)
                elif subs:
                    return [subs]
            return []
        except Exception:
            return []

    def _count_classes_in_tree(self, tree: Dict[str, Any]) -> int:
        """Count classes in a built tree"""
        count = 0
        if isinstance(tree, dict):
            if tree.get("type") == "class":
                count += 1
            elif "children" in tree:
                for child in tree["children"].values():
                    count += self._count_classes_in_tree(child)
            elif "folders" in tree:
                for folder in tree["folders"].values():
                    count += self._count_classes_in_tree(folder)
        return count

    def _generate_statistics(self, scan_duration: float):
        """Generate basic statistics"""
        try:
            classes_count = len(self._all_classes)

            folder_stats: Dict[str, int] = {}
            max_depth = 0

            for path in self._all_classes.keys():
                top_folder = path.split('\\')[0]
                folder_stats[top_folder] = folder_stats.get(top_folder, 0) + 1

                depth = len(path.split('\\'))
                max_depth = max(max_depth, depth)

            cps = classes_count / scan_duration if scan_duration > 0 else 0.0

            self._stats = ScanStatistics(
                total_classes=classes_count,
                total_folders=len(self._processed_paths),
                scan_duration=scan_duration,
                classes_per_second=cps,
                folder_distribution=folder_stats,
                deepest_path_level=max_depth,
                timestamp=datetime.now().isoformat(),
                esdl_classes=self._esdl_count,
                non_esdl_classes_filtered=self._non_esdl_filtered
            )

        except Exception as e:
            if self.debug:
                print(f"Error generating statistics: {str(e)}")


# --------------------------------
# Demo / Comprehensive test
# --------------------------------
def run_comprehensive_test():
    print("=" * 80)
    print("ASCET Structure Scanner API - Comprehensive Test (ESDL Only)")
    print("=" * 80)

    scanner = ASCETStructureScannerAPI(version="6.1.4", debug=True)

    try:
        # 1) Connect
        print("\nTest 1: Connect")
        print("-" * 40)
        connect_result = scanner.connect()
        print(f"Connected: {connect_result.success}")
        print(f"Message: {connect_result.message}")
        if connect_result.error:
            print(f"Error: {connect_result.error}")
        if not connect_result.success:
            print("[ERROR] Connection failed, aborting further tests")
            return

        # 2) Full DB scan (DEFAULT: filtered by ESDL and Main/calc)
        print("\nTest 2: Full database scan (filtered: ESDL classes with Main/calc by default)")
        print("-" * 40)
        scan_filtered = scanner.scan_all_classes()  # defaults to esdl_only=True, require_calc=True
        print(f"Success: {scan_filtered.success}")
        print(f"ESDL classes found: {scan_filtered.classes_found}")
        print(f"Duration: {scan_filtered.scan_time:.2f} s")
        print(f"Message: {scan_filtered.message}")

        if scan_filtered.success and scan_filtered.classes_found > 0:
            sample_paths = scan_filtered.data.get("class_paths", [])
            print("\nSample ESDL class paths:")
            for i, path in enumerate(sample_paths[:5], 1):
                print(f"  {i}. {path}")

        # 3) Folder scan (ESDL filtered)
        print("\nTest 3: Folder scan (ESDL filtered)")
        print("-" * 40)
        test_folder = r"PlatformLibrary\Package"  # adjust to your DB if needed
        folder_result = scanner.scan_folder(test_folder)  # defaults to esdl_only=True, require_calc=True
        print(f"Success: {folder_result.success}")
        print(f"ESDL classes found: {folder_result.classes_found}")
        print(f"Duration: {folder_result.scan_time:.2f} s")
        print(f"Message: {folder_result.message}")

        # 4) Build structure tree (ESDL only)
        print("\nTest 4: Build structure tree (ESDL only)")
        print("-" * 40)
        tree_result = scanner.build_structure_tree()  # defaults to esdl_only=True
        print(f"Success: {tree_result.success}")
        print(f"ESDL classes in tree: {tree_result.classes_found}")
        print(f"Duration: {tree_result.scan_time:.2f} s")
        print(f"Message: {tree_result.message}")

        # 5) Search classes (uses last scan_all_classes results)
        print("\nTest 5: Search ESDL classes")
        print("-" * 40)
        search_patterns = ["AEB", "Test", "Control"]
        for pattern in search_patterns:
            res = scanner.find_classes(pattern)
            print(f"Search '{pattern}': {res.classes_found} ESDL result(s)")
            if res.success and res.classes_found > 0:
                for match in res.data.get("matches", [])[:3]:
                    print(f"  - {match}")

        # 6) Statistics
        print("\nTest 6: Statistics")
        print("-" * 40)
        stats = scanner.get_statistics()
        if stats:
            print(f"Total ESDL classes: {stats.total_classes}")
            print(f"ESDL classes found: {stats.esdl_classes}")
            print(f"Non-ESDL classes filtered: {stats.non_esdl_classes_filtered}")
            print(f"Total folders: {stats.total_folders}")
            print(f"Duration: {stats.scan_duration:.2f} s")
            print(f"Throughput: {stats.classes_per_second:.1f} classes/s")
            print(f"Deepest path level: {stats.deepest_path_level}")
            print("Top-level folder distribution (ESDL classes):")
            for folder, count in list(stats.folder_distribution.items())[:5]:
                print(f"  {folder}: {count} ESDL classes")
        else:
            print("No statistics available")

        # 7) Export
        print("\nTest 7: Export ESDL results")
        print("-" * 40)
        export_result = scanner.export_results(output_dir="./test_output", format="both")
        print(f"Success: {export_result.success}")
        print(f"Message: {export_result.message}")
        if export_result.success:
            print("Files:")
            for f in export_result.data.get("exported_files", []):
                print(f"  {f}")

        # 8) API helpers
        print("\nTest 8: Helper API")
        print("-" * 40)
        class_paths = scanner.get_class_paths()
        print(f"get_class_paths(): {len(class_paths)} ESDL class paths")
        if class_paths:
            first = class_paths[0]
            obj = scanner.get_class_object(first)
            print(f"get_class_object('{first}'): {'OK' if obj else 'None'}")

        print("\n[SUCCESS] All tests finished!")

    except Exception as e:
        print(f"\n[ERROR] Test runtime error: {str(e)}")
        traceback.print_exc()

    finally:
        # 9) Disconnect
        print("\nTest 9: Disconnect")
        print("-" * 40)
        res = scanner.disconnect()
        print(f"Success: {res.success}")
        print(f"Message: {res.message}")


def main():
    """Entry point"""
    try:
        run_comprehensive_test()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nRuntime error: {str(e)}")
        traceback.print_exc()
    finally:
        print("\nProgram end")


if __name__ == "__main__":
    main()