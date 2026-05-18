from win32com.client import Dispatch
import traceback

class ASCETDiagramSignalExtractor:
    """简洁高效的ASCET Block Diagram信号提取器"""
    
    def __init__(self, version="6.1.4"):
        self.ascet = None
        self.db = None
        self.version = version
    
    def connect(self):
        """连接到ASCET"""
        try:
            self.ascet = Dispatch(f"Ascet.Ascet.{self.version}")
            self.db = self.ascet.GetCurrentDataBase()
            print(f"✅ Successfully connected to ASCET {self.version}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            return False
    
    def get_diagram_signals(self, class_path):
        """
        获取Block Diagram中的所有信号名称
        Args:
            class_path: 类路径，如 r"\PlatformLibrary\Package\StandstillLibrary\public\SSM_VHC\Ssm_pVehStartRoll"
        Returns:
            dict: {'input_signals': [], 'output_signals': [], 'internal_signals': [], 'element_details': []}
        """
        try:
            # 规范化路径格式
            normalized_path = class_path.replace('/', '\\').lstrip('\\')
            path_parts = normalized_path.split('\\')
            class_name = path_parts[-1]
            folder_path = '\\'.join(path_parts[:-1])
            
            print(f"🔍 Looking for class: {class_name} in {folder_path}")
            
            # 获取类组件
            class_component = self.db.GetItemInFolder(class_name, folder_path)
            if not class_component:
                print(f"❌ Class not found: {class_path}")
                return None
            
            # 获取Block Diagram
            if not hasattr(class_component, 'GetDiagram'):
                print(f"❌ Class {class_name} has no diagram")
                return None
                
            diagram = class_component.GetDiagram()
            if not diagram:
                print(f"❌ No diagram found for class {class_name}")
                return None
            
            print(f"✅ Found diagram for class: {class_name}")
            
            # 初始化结果
            result = {
                'input_signals': [],
                'output_signals': [],
                'internal_signals': [],
                'element_details': []
            }
            
            # 获取所有Pin（输入输出信号）- 增强版本
            print("\n🔍 Looking for diagram-level pins...")
            
            # 方法1: 直接从diagram获取pins
            if hasattr(diagram, 'GetAllPins'):
                pins = diagram.GetAllPins()
                if pins:
                    print(f"Found {len(pins)} diagram pins")
                    for pin in pins:
                        try:
                            pin_name = self._safe_get_name(pin)
                            if pin_name:
                                if hasattr(pin, 'IsInput') and pin.IsInput():
                                    result['input_signals'].append(pin_name)
                                    print(f"📥 Input signal: {pin_name}")
                                elif hasattr(pin, 'IsOutput') and pin.IsOutput():
                                    result['output_signals'].append(pin_name)
                                    print(f"📤 Output signal: {pin_name}")
                        except Exception as e:
                            print(f"⚠️ Error processing pin: {str(e)}")
                else:
                    print("No diagram-level pins found")
            
            # 方法2: 通过diagram的hierarchy获取pins
            if not result['input_signals'] and not result['output_signals']:
                print("🔍 Trying to get pins through diagram hierarchy...")
                try:
                    if hasattr(diagram, 'GetHierarchy'):
                        hierarchy = diagram.GetHierarchy()
                        if hierarchy and hasattr(hierarchy, 'GetAllPins'):
                            hierarchy_pins = hierarchy.GetAllPins()
                            if hierarchy_pins:
                                print(f"Found {len(hierarchy_pins)} hierarchy pins")
                                for pin in hierarchy_pins:
                                    try:
                                        pin_name = self._safe_get_name(pin)
                                        if pin_name:
                                            if hasattr(pin, 'IsInput') and pin.IsInput():
                                                result['input_signals'].append(pin_name)
                                                print(f"📥 Hierarchy input: {pin_name}")
                                            elif hasattr(pin, 'IsOutput') and pin.IsOutput():
                                                result['output_signals'].append(pin_name)
                                                print(f"📤 Hierarchy output: {pin_name}")
                                    except Exception as e:
                                        print(f"⚠️ Error processing hierarchy pin: {str(e)}")
                except Exception as e:
                    print(f"⚠️ Error getting hierarchy pins: {str(e)}")
            
            # 方法3: 从class component本身获取model elements（作为备选）
            if not result['input_signals'] and not result['output_signals']:
                print("🔍 Trying to get signals from class model elements...")
                try:
                    if hasattr(class_component, 'GetAllModelElements'):
                        model_elements = class_component.GetAllModelElements()
                        if model_elements:
                            for element in model_elements:
                                try:
                                    if hasattr(element, 'GetScope'):
                                        scope = element.GetScope()
                                        element_name = self._safe_get_name(element)
                                        if element_name:
                                            if scope and scope.lower() == 'imported':
                                                result['input_signals'].append(element_name)
                                                print(f"📥 Imported signal: {element_name}")
                                            elif scope and scope.lower() == 'exported':
                                                result['output_signals'].append(element_name)
                                                print(f"📤 Exported signal: {element_name}")
                                except Exception as e:
                                    print(f"⚠️ Error processing model element: {str(e)}")
                except Exception as e:
                    print(f"⚠️ Error getting model elements: {str(e)}")
            
            # 获取所有内部Pin
            if hasattr(diagram, 'GetAllInternalPins'):
                internal_pins = diagram.GetAllInternalPins()
                if internal_pins:
                    for pin in internal_pins:
                        try:
                            pin_name = self._safe_get_name(pin)
                            if pin_name:
                                result['internal_signals'].append(pin_name)
                                print(f"🔗 Internal signal: {pin_name}")
                        except Exception as e:
                            print(f"⚠️ Error processing internal pin: {str(e)}")
            
            # 获取所有Diagram元素（方块等）- 增强版本
            if hasattr(diagram, 'GetAllDiagramElements'):
                elements = diagram.GetAllDiagramElements()
                if elements:
                    print(f"🔍 Processing {len(elements) if hasattr(elements, '__len__') else 'several'} diagram elements...")
                    
                    for i, element in enumerate(elements):
                        element_info = self._process_diagram_element(element, i)
                        if element_info:
                            result['element_details'].append(element_info)
            
            # 输出汇总
            print(f"\n📊 Summary for {class_name}:")
            print(f"   📥 Input signals: {len(result['input_signals'])}")
            print(f"   📤 Output signals: {len(result['output_signals'])}")
            print(f"   🔗 Internal signals: {len(result['internal_signals'])}")
            print(f"   🔲 Diagram elements: {len(result['element_details'])}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error getting diagram signals: {str(e)}")
            traceback.print_exc()
            return None
    
    def _safe_get_name(self, obj):
        """安全获取对象名称 - 增强版本"""
        name = None
        
        # 方法1: 直接GetName()
        try:
            if hasattr(obj, 'GetName'):
                name = obj.GetName()
                if name and name.strip():
                    return name.strip()
        except:
            pass
        
        # 方法2: 通过GetHierarchy()获取名称
        try:
            if hasattr(obj, 'GetHierarchy'):
                hierarchy = obj.GetHierarchy()
                if hierarchy and hasattr(hierarchy, 'GetName'):
                    name = hierarchy.GetName()
                    if name and name.strip():
                        return name.strip()
        except:
            pass
        
        # 方法3: 通过GetCodeComponent()获取名称
        try:
            if hasattr(obj, 'GetCodeComponent'):
                code_component = obj.GetCodeComponent()
                if code_component and hasattr(code_component, 'GetName'):
                    name = code_component.GetName()
                    if name and name.strip():
                        return name.strip()
        except:
            pass
        
        return None
    
    def _process_diagram_element(self, element, index):
        """处理单个diagram元素 - 增强版本"""
        try:
            element_info = {
                'index': index,
                'name': None,
                'hierarchy_name': None,
                'code_component_name': None,
                'type': 'Unknown',
                'pins': []
            }
            
            # 尝试多种方法获取名称
            element_info['name'] = self._safe_get_name(element)
            
            # 专门尝试GetHierarchy()
            try:
                if hasattr(element, 'GetHierarchy'):
                    hierarchy = element.GetHierarchy()
                    if hierarchy:
                        hierarchy_name = self._safe_get_name(hierarchy)
                        if hierarchy_name:
                            element_info['hierarchy_name'] = hierarchy_name
                            print(f"   📋 Hierarchy name: {hierarchy_name}")
            except Exception as e:
                print(f"   ⚠️ Error getting hierarchy: {str(e)}")
            
            # 专门尝试GetCodeComponent()
            try:
                if hasattr(element, 'GetCodeComponent'):
                    code_component = element.GetCodeComponent()
                    if code_component:
                        code_name = self._safe_get_name(code_component)
                        if code_name:
                            element_info['code_component_name'] = code_name
                            print(f"   💻 Code component name: {code_name}")
            except Exception as e:
                print(f"   ⚠️ Error getting code component: {str(e)}")
            
            # 确定最佳显示名称
            display_name = (element_info['hierarchy_name'] or 
                          element_info['code_component_name'] or 
                          element_info['name'] or 
                          'Unnamed')
            
            # 确定元素类型
            element_type = self._get_element_type(element)
            element_info['type'] = element_type
            
            print(f"🔲 Element {index}: {display_name} (Type: {element_type})")
            
            # 获取元素的引脚信息
            if hasattr(element, 'GetAllPins'):
                try:
                    pins = element.GetAllPins()
                    if pins:
                        for pin in pins:
                            pin_name = self._safe_get_name(pin)
                            if pin_name:
                                element_info['pins'].append(pin_name)
                                print(f"   🔌 Pin: {pin_name}")
                except Exception as e:
                    print(f"   ⚠️ Error getting pins: {str(e)}")
            
            # 更新element_info中的display_name
            element_info['display_name'] = display_name
            
            return element_info
            
        except Exception as e:
            print(f"⚠️ Error processing element {index}: {str(e)}")
            return None
    
    def _get_element_type(self, element):
        """确定元素类型"""
        type_checks = [
            ('IsBlockDiagramHierarchy', 'Hierarchy'),
            ('IsBlockDiagramOperator', 'Operator'),
            ('IsBlockDiagramLiteral', 'Literal'),
            ('IsBlockDiagramFunctionalElement', 'Functional'),
            ('IsBlockDiagramControlElement', 'Control'),
            ('IsBlockDiagramHierarchyPin', 'HierarchyPin'),
            ('IsBlockDiagramComment', 'Comment')
        ]
        
        for method_name, type_name in type_checks:
            try:
                if hasattr(element, method_name):
                    if getattr(element, method_name)():
                        return type_name
            except:
                continue
        
        return 'Unknown'
    
    def disconnect(self):
        """断开ASCET连接"""
        if self.ascet:
            try:
                self.ascet.DisconnectFromTool()
                print("✅ Disconnected from ASCET")
            except Exception as e:
                print(f"⚠️ Error disconnecting: {str(e)}")

def main():
    """主函数 """
    # 你的类路径
    class_path = r"\Customer\CC_CN\Package\ECAS_ElectronicallyControlledAirSpring\private\ECAS_HC_StateMachine"
    
    # 创建提取器
    extractor = ASCETDiagramSignalExtractor()
    
    try:
        # 连接并提取信号
        if extractor.connect():
            signals = extractor.get_diagram_signals(class_path)
            
            if signals:
                print(f"\n🎯 Final Results:")
                print(f"Input Signals: {signals['input_signals']}")
                print(f"Output Signals: {signals['output_signals']}")
                print(f"Internal Signals: {signals['internal_signals']}")
                print(f"\nElement Details:")
                for elem in signals['element_details']:
                    display_name = elem.get('display_name', elem.get('name', 'Unnamed'))
                    print(f"  - {display_name} ({elem['type']})")
                    
                    # 显示不同来源的名称信息
                    if elem.get('hierarchy_name'):
                        print(f"    📋 Hierarchy: {elem['hierarchy_name']}")
                    if elem.get('code_component_name'):
                        print(f"    💻 Code Component: {elem['code_component_name']}")
                    
                    if elem['pins']:
                        print(f"    🔌 Pins: {elem['pins']}")
            else:
                print(" Failed to extract signals")
    
    finally:
        extractor.disconnect()

if __name__ == '__main__':
    main()