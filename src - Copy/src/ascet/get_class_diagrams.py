from win32com.client import Dispatch

class AscetDiagramsExplorer:
    def __init__(self, version="6.1.5"):
        self.ascet = None
        self.db = None
        self.version = version
    
    def connect(self):
        """连接到ASCET并获取当前数据库"""
        self.ascet = Dispatch(f"Ascet.Ascet.{self.version}")
        self.db = self.ascet.GetCurrentDataBase()
    
    def print_all_diagrams(self, class_path):
        """
        打印类中的所有Diagrams
        Parameters:
            class_path (str): 类的完整路径（使用反斜杠分隔）
        """
        print(f"正在探索类: {class_path}")
        print("=" * 60)
        
        # 自动去掉开头的反斜杠
        if class_path.startswith("\\"):
            class_path = class_path[1:]
        
        # 解析路径
        path_parts = class_path.split('\\')
        class_name = path_parts[-1]
        folder_path = '\\'.join(path_parts[:-1])
        
        # 获取类组件
        class_item = self.db.GetItemInFolder(class_name, folder_path)
        if not class_item:
            print(f"❌ 未找到类: {class_name}")
            return
        
        # 打印类的基本信息
        print(f"📁 类名: {class_name}")
        print(f"📍 路径: {folder_path}")
        print()
        
        # 探索类的diagrams
        print("📋 所有 Diagrams:")
        print("-" * 40)
        
        try:
            # 获取所有diagrams
            all_diagrams = class_item.GetAllDiagrams()
            if all_diagrams:
                for i, diagram in enumerate(all_diagrams, 1):
                    try:
                        diagram_name = diagram.GetName()
                        print(f"  {i}. 📊 Diagram: {diagram_name}")
                        
                        # 获取diagram中的所有方法
                        all_methods = diagram.GetAllMethods()
                        if all_methods:
                            print(f"     包含 {len(all_methods)} 个方法:")
                            for j, method in enumerate(all_methods, 1):
                                try:
                                    method_name = method.GetName()
                                    print(f"       {j}. 🔧 {method_name}")
                                except Exception as e:
                                    print(f"       ❌ 方法读取错误: {e}")
                        else:
                            print("     ℹ️  无方法")
                        print()
                        
                    except Exception as e:
                        print(f"  ❌ Diagram读取错误: {e}")
                        print()
            else:
                print("  ℹ️  未找到Diagrams")
        except Exception as e:
            print(f"  ❌ Diagram探索错误: {e}")
    
    def disconnect(self):
        """断开与ASCET的连接"""
        if self.ascet:
            self.ascet.DisconnectFromTool()

# 使用示例
if __name__ == "__main__":
    explorer = AscetDiagramsExplorer()
    explorer.connect()
    
    # 替换为您要探索的类路径
    class_path = r"\PlatformLibrary\Package\StandstillLibrary\public\SSM_VHC_Fx\vhcDeactRampTimeFx"
    
    # 打印所有diagrams
    explorer.print_all_diagrams(class_path)
    
    explorer.disconnect()