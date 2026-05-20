import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
from win32com.client import Dispatch

def _log(*args, **kwargs):
    """Print to stderr so stdout stays clean for JSON output."""
    print(*args, file=sys.stderr, **kwargs)


class SimpleAscetCodeExtractor:
    """简洁的ASCET代码提取器 - 只提取Main.calc代码并输出Markdown"""
    
    def __init__(self, version="6.1.5"):
        self.ascet = None
        self.db = None
        self.version = version
        self.available_classes = {}  # {path: class_object}
        
    def connect(self) -> bool:
        """连接到ASCET数据库"""
        try:
            _log(f"Connecting to ASCET {self.version}...")
            self.ascet = Dispatch(f"Ascet.Ascet.{self.version}")
            self.db = self.ascet.GetCurrentDataBase()
            
            if self.db:
                _log(f"Connected to database: {self.db.GetName()}")
                return True
            return False
        except Exception as e:
            _log(f"Connection failed: {e}")
            return False
    
    def scan_database(self) -> bool:
        """扫描数据库查找所有类"""
        try:
            _log("Scanning database structure...")
            self.available_classes.clear()
            
            # 获取顶级文件夹
            top_folders = self._get_top_folders()
            if not top_folders:
                _log("No folders found")
                return False
            
            # 递归扫描
            for folder in top_folders:
                if folder:
                    folder_name = folder.GetName()
                    folder_path = folder.GetNameWithPath() if hasattr(folder, 'GetNameWithPath') else folder_name
                    self._scan_folder(folder, folder_path)
            
            _log(f"Found {len(self.available_classes)} classes")
            return len(self.available_classes) > 0
            
        except Exception as e:
            _log(f"Scan failed: {e}")
            return False
    
    def _get_top_folders(self) -> List:
        """获取顶级文件夹"""
        try:
            get_folders_attr = getattr(self.db, "GetAllAscetFolders", None)
            if get_folders_attr:
                folders = get_folders_attr() if callable(get_folders_attr) else get_folders_attr
                if isinstance(folders, (tuple, list)):
                    return [f for f in folders if f]
                elif folders:
                    return [folders]
        except:
            pass
        
        try:
            folders = self.db.GetAllFolders()
            if folders:
                return [folders] if not isinstance(folders, (tuple, list)) else [f for f in folders if f]
        except:
            pass
        
        return []
    
    def _scan_folder(self, folder, folder_path: str):
        """递归扫描文件夹"""
        try:
            # 检查是否是类
            if hasattr(folder, 'IsClass') and folder.IsClass():
                self.available_classes[folder_path] = folder
            
            # 扫描子项目
            if hasattr(folder, 'GetAllDataBaseItems'):
                get_items_attr = getattr(folder, 'GetAllDataBaseItems')
                items = get_items_attr() if callable(get_items_attr) else get_items_attr
                
                if items:
                    for item in items:
                        if not item:
                            continue
                        try:
                            item_name = item.GetName()
                            item_path = f"{folder_path}\\{item_name}"
                            
                            if hasattr(item, 'IsClass') and item.IsClass():
                                self.available_classes[item_path] = item
                            elif hasattr(item, 'IsFolder') and item.IsFolder():
                                self._scan_folder(item, item_path)
                        except:
                            continue
            
            # 扫描子文件夹
            if hasattr(folder, 'GetSubFolders'):
                subfolders = folder.GetSubFolders()
                if subfolders:
                    for subfolder in subfolders:
                        if subfolder:
                            try:
                                subfolder_name = subfolder.GetName()
                                subfolder_path = f"{folder_path}\\{subfolder_name}"
                                self._scan_folder(subfolder, subfolder_path)
                            except:
                                continue
        except:
            pass
    
    def extract_main_calc_code(self, class_path: str) -> Optional[str]:
        """提取类的Main.calc代码"""
        try:
            # 标准化路径
            if class_path.startswith("\\"):
                class_path = class_path[1:]
            
            path_parts = class_path.split('\\')
            class_name = path_parts[-1]
            folder_path = '\\'.join(path_parts[:-1])
            
            # 获取类
            class_item = self.db.GetItemInFolder(class_name, folder_path)
            if not class_item:
                return None
            
            # 获取Main图表
            diagram = class_item.GetDiagramWithName('Main')
            if not diagram:
                return None
            
            # 获取calc方法
            method = diagram.GetMethod('calc')
            if not method:
                return None
            
            # 获取代码
            code = method.GetCode()
            return code if code and code.strip() else None
            
        except:
            return None
    
    def add_line_numbers(self, code: str) -> str:
        """为代码添加行号"""
        if not code:
            return "// No code available"
        
        lines = code.split('\n')
        max_line_num = len(lines)
        line_num_width = len(str(max_line_num))
        
        numbered_lines = []
        for i, line in enumerate(lines, 1):
            line_number = f"{i:>{line_num_width}}"
            numbered_lines.append(f"{line_number}: {line}")
        
        return '\n'.join(numbered_lines)
    
    def extract_all_and_export_markdown(self, output_file: str = None) -> bool:
        """提取所有类的Main.calc代码并导出到Markdown"""
        try:
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"ascet_classes_code_{timestamp}.md"
            
            _log(f"Extracting code and generating Markdown: {output_file}")
            
            total_classes = len(self.available_classes)
            processed = 0
            extracted = 0
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # 写入标题
                f.write("# ASCET Classes Code Extract Report\n\n")
                f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**数据库**: {self.db.GetName()}\n\n")
                f.write(f"**总类数**: {total_classes}\n\n")
                f.write("---\n\n")
                
                # 处理每个类
                for class_path, class_obj in self.available_classes.items():
                    processed += 1
                    
                    if processed % 10 == 0:
                        _log(f"Progress: {processed}/{total_classes}")
                    
                    # 提取代码
                    code = self.extract_main_calc_code(class_path)
                    
                    # 写入类信息
                    class_name = os.path.basename(class_path)
                    f.write(f"## {class_name}\n\n")
                    f.write(f"**类路径**: `{class_path}`\n\n")
                    
                    if code:
                        # 添加行号并写入代码
                        numbered_code = self.add_line_numbers(code)
                        f.write("**Main.calc 代码**:\n\n")
                        f.write("```c\n")
                        f.write(numbered_code)
                        f.write("\n```\n\n")
                        extracted += 1
                    else:
                        f.write("**Main.calc 代码**: *未找到或为空*\n\n")
                    
                    f.write("---\n\n")
                
                # 写入统计信息
                f.write("## 提取统计\n\n")
                f.write(f"- **处理类数**: {processed}\n")
                f.write(f"- **成功提取**: {extracted}\n")
                f.write(f"- **提取失败**: {processed - extracted}\n")
                f.write(f"- **成功率**: {(extracted/max(processed, 1)*100):.1f}%\n")
            
            _log(f"Markdown generated: {output_file}")
            _log(f"Processed {processed} classes, extracted {extracted}")
            
            return True
            
        except Exception as e:
            _log(f"Markdown generation failed: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.ascet:
            try:
                self.ascet.DisconnectFromTool()
                _log("Disconnected from ASCET")
            except:
                pass


def main():
    """主函数"""
    print("=" * 60)
    print("ASCET代码提取器 - Markdown输出")
    print("=" * 60)
    
    # 配置
    ascet_version = "6.1.4"
    output_file = "ascet_classes_main_calc_code.md"
    
    extractor = SimpleAscetCodeExtractor(ascet_version)
    
    try:
        # 1. 连接ASCET
        if not extractor.connect():
            return
        
        # 2. 扫描数据库
        if not extractor.scan_database():
            return
        
        # 3. 提取代码并生成Markdown
        if extractor.extract_all_and_export_markdown(output_file):
            _log(f"Done! Output: {output_file}")
        
    except KeyboardInterrupt:
        _log("Interrupted by user")
    except Exception as e:
        _log(f"Error: {e}")
    finally:
        extractor.disconnect()


if __name__ == "__main__":
    main()