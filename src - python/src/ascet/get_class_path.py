from win32com.client import Dispatch
from typing import List, Dict, Optional

class ASCETClassFinder:
    """ASCET类路径查找器 - 根据类名获取完整路径"""
    
    def __init__(self, version: str = "6.1.4"):
        self.ascet = None
        self.db = None
        self.version = version
        self.class_name_to_path = {}
        
    def connect(self) -> bool:
        """连接到ASCET数据库"""
        try:
            self.ascet = Dispatch(f"Ascet.Ascet.{self.version}")
            self.db = self.ascet.GetCurrentDataBase()
            return True
        except Exception as e:
            print(f"连接失败: {str(e)}")
            return False
    
    def scan_all_classes(self) -> bool:
        """扫描所有类并建立索引"""
        try:
            top_folders = self.db.GetAllAscetFolders()
            if not top_folders:
                return False
            
            for folder in top_folders:
                if folder:
                    self._scan_folder_recursive(folder)
            
            return True
            
        except Exception as e:
            print(f"扫描失败: {str(e)}")
            return False
    
    def _scan_folder_recursive(self, folder):
        """递归扫描文件夹"""
        try:
            if not folder:
                return
                
            # 检查当前文件夹是否是类
            if hasattr(folder, 'IsClass') and folder.IsClass():
                full_path = self._get_full_path(folder)
                if full_path:
                    class_name = folder.GetName()
                    self.class_name_to_path[class_name] = full_path
            
            # 处理子文件夹
            if hasattr(folder, 'GetSubFolders'):
                subfolders = folder.GetSubFolders()
                if subfolders:
                    for subfolder in subfolders:
                        if subfolder:
                            self._scan_folder_recursive(subfolder)
            
            # 处理数据库项目
            if hasattr(folder, 'GetAllDataBaseItems'):
                get_items_attr = getattr(folder, 'GetAllDataBaseItems')
                items = get_items_attr() if callable(get_items_attr) else get_items_attr
                    
                if items:
                    for item in items:
                        if not item:
                            continue
                        
                        if hasattr(item, 'IsClass') and item.IsClass():
                            full_path = self._get_full_path(item)
                            if full_path:
                                class_name = item.GetName()
                                self.class_name_to_path[class_name] = full_path
                        elif hasattr(item, 'IsFolder') and item.IsFolder():
                            self._scan_folder_recursive(item)
                            
        except Exception:
            pass
    
    def _get_full_path(self, db_item) -> Optional[str]:
        """获取完整路径"""
        try:
            if hasattr(db_item, 'GetNameWithPath'):
                path = db_item.GetNameWithPath()
                if path:
                    return path if path.startswith('\\') else f'\\{path}'
            return None
        except Exception:
            return None
    
    def find_path(self, class_name: str) -> Optional[str]:
        """根据类名查找路径"""
        return self.class_name_to_path.get(class_name)
    
    def find_multiple_paths(self, class_names: List[str]) -> Dict[str, Optional[str]]:
        """批量查找多个类名的路径"""
        results = {}
        for class_name in class_names:
            results[class_name] = self.find_path(class_name)
        return results
    
    def disconnect(self):
        """断开ASCET连接"""
        if self.ascet:
            try:
                self.ascet.DisconnectFromTool()
            except Exception:
                pass


def main():
    """查找指定类名的路径"""
    
    # 要查找的类名列表
    target_classes = [
        "StandTime_Calculation_CA",
        "CTRL_ThrotteleProcessing", 
        "Nio_EBR_Arb_NT3",
        "TCS_CUS_BTC_AirSuspPreCtrl_WhlArticulationDet",
        "COOR_SignalMappingForSecondary",
        "PBC_SCUlockReq",
        "HMI_ApbTextMessage_NIO",
        "CEVT_EPB_Auto_Apply_Trigger_PMA",
        "APCBlock"
    ]
    
    finder = ASCETClassFinder("6.1.4")
    
    try:
        if not finder.connect():
            return
        
        if not finder.scan_all_classes():
            return
        
        results = finder.find_multiple_paths(target_classes)
        
        # 输出结果
        for class_name, path in results.items():
            if path:
                print(f"{class_name}: {path}")
            else:
                print(f"{class_name}: NOT FOUND")
        
    except Exception as e:
        print(f"错误: {str(e)}")
    
    finally:
        finder.disconnect()


def find_single_class(class_name: str):
    """查找单个类名"""
    finder = ASCETClassFinder("6.1.4")
    
    if finder.connect() and finder.scan_all_classes():
        path = finder.find_path(class_name)
        if path:
            print(f"{class_name}: {path}")
        else:
            print(f"{class_name}: NOT FOUND")
    
    finder.disconnect()


if __name__ == '__main__':
    main()
    
    # 或者查找单个类名
    # find_single_class("StandTime_Calculation_CA")