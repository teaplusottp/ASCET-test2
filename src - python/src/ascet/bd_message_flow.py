from win32com.client import Dispatch
import traceback
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

class AscetSignalLibraryAnalyzer:
    """两步骤分析：1.建立A2A和XPass信号库 2.分析Block Diagram信号来源"""
    
    def __init__(self, version="6.1.4"):
        """初始化分析器
        
        Args:
            version: ASCET版本
        """
        self.ascet = None
        self.db = None
        self.version = version
        self.signal_library = {
            "a2a_signals": {},
            "xpass_signals": {},
            "scan_timestamp": ""
        }
        
    def connect(self) -> bool:
        """连接到ASCET数据库"""
        try:
            print(f"连接到ASCET {self.version}...")
            self.ascet = Dispatch(f"Ascet.Ascet.{self.version}")
            self.db = self.ascet.GetCurrentDataBase()
            
            if self.db:
                db_name = self.db.GetName()
                print(f"[SUCCESS] 成功连接到ASCET数据库: {db_name}")
                return True
            else:
                print("[ERROR] 无法获取数据库引用")
                return False
                
        except Exception as e:
            print(f"[ERROR] 连接失败: {str(e)}")
            traceback.print_exc()
            return False
    
    def get_component_by_path(self, component_path: str):
        """根据路径获取组件对象"""
        try:
            # 标准化路径格式
            normalized_path = component_path.replace('/', '\\')
            if normalized_path.startswith('\\'):
                normalized_path = normalized_path[1:]
            
            # 分解路径
            path_parts = normalized_path.split('\\')
            component_name = path_parts[-1]
            folder_path = '\\'.join(path_parts[:-1])
            
            print(f"查找组件: {component_name} 在路径: {folder_path}")
            
            # 获取组件
            component = self.db.GetItemInFolder(component_name, folder_path)
            
            if component:
                print(f"[SUCCESS] 找到组件: {component_path}")
                return component
            else:
                print(f"[ERROR] 未找到组件: {component_path}")
                return None
                
        except Exception as e:
            print(f"[ERROR] 获取组件时出错 {component_path}: {str(e)}")
            return None
    
    def scan_component_signals(self, component_path: str, component_type: str) -> Dict:
        """扫描组件中的所有信号
        
        Args:
            component_path: 组件路径
            component_type: 组件类型 ("A2A" 或 "XPass")
            
        Returns:
            包含信号信息的字典
        """
        try:
            print(f"\n{'='*100}")
            print(f"[SCAN] 扫描{component_type}组件信号: {component_path}")
            print(f"{'='*100}")
            
            # 获取组件
            component = self.get_component_by_path(component_path)
            if not component:
                return {"error": f"无法找到组件: {component_path}"}
            
            # 获取组件的represented class（实际的类定义）
            target_class = component
            if hasattr(component, 'GetRepresentedClass'):
                represented_class = component.GetRepresentedClass()
                if represented_class:
                    target_class = represented_class
                    print(f"[INFO] 使用represented class: {represented_class.GetName()}")
            
            # 获取所有模型元素
            model_elements = []
            if hasattr(target_class, 'GetAllModelElements'):
                elements = target_class.GetAllModelElements()
                if elements:
                    model_elements = elements
                    print(f"[INFO] 找到 {len(model_elements)} 个模型元素")
                else:
                    print("[ERROR] 未找到模型元素")
                    return {"error": "组件中没有模型元素"}
            else:
                print("[ERROR] 组件不支持GetAllModelElements方法")
                return {"error": "组件不支持获取模型元素"}
            
            # 信号分类结果
            signals = {
                "component_path": component_path,
                "component_type": component_type,
                "timestamp": datetime.now().isoformat(),
                "send_messages": [],      # 发送信号
                "receive_messages": [],   # 接收信号
                "parameters": [],         # 参数
                "variables": [],          # 变量
                "constants": [],          # 常量
                "other_elements": []      # 其他元素
            }
            
            # 分析每个元素
            for element in model_elements:
                try:
                    if not element:
                        continue
                    
                    element_name = element.GetName() if hasattr(element, 'GetName') else "Unknown"
                    
                    # 创建元素信息
                    element_info = {
                        "name": element_name,
                        "type": "",
                        "scope": "",
                        "kind": "",
                        "unit": "",
                        "comment": "",
                        "min": "",
                        "max": "",
                        "default_value": ""
                    }
                    
                    # 获取基本信息
                    if hasattr(element, 'GetModelType'):
                        element_info["type"] = element.GetModelType()
                    
                    if hasattr(element, 'GetScope'):
                        element_info["scope"] = element.GetScope()
                    
                    if hasattr(element, 'GetUnit'):
                        unit = element.GetUnit()
                        element_info["unit"] = unit if unit else ""
                    
                    if hasattr(element, 'GetComment'):
                        comment = element.GetComment()
                        element_info["comment"] = comment if comment else ""
                    
                    # 获取范围信息
                    try:
                        if hasattr(element, 'GetImplementation'):
                            impl = element.GetImplementation()
                            if impl and hasattr(impl, 'GetImplInfoForValue'):
                                impl_info = impl.GetImplInfoForValue()
                                if impl_info:
                                    # 尝试获取物理范围
                                    range_methods = [
                                        'GetDoublePhysicalRange',
                                        'GetFloatPhysicalRange', 
                                        'GetIntegerPhysicalRange'
                                    ]
                                    
                                    for method_name in range_methods:
                                        if hasattr(impl_info, method_name):
                                            try:
                                                range_value = getattr(impl_info, method_name)()
                                                if range_value and len(range_value) == 2:
                                                    element_info["min"] = str(range_value[0])
                                                    element_info["max"] = str(range_value[1])
                                                    break
                                            except:
                                                continue
                    except:
                        pass
                    
                    # 获取默认值
                    try:
                        if hasattr(element, 'GetValue'):
                            value_obj = element.GetValue()
                            if value_obj:
                                # 尝试不同的值获取方法
                                value_methods = ['GetDoubleValue', 'GetFloatValue', 'GetIntegerValue', 
                                               'GetStringValue', 'GetBooleanValue']
                                for method_name in value_methods:
                                    if hasattr(value_obj, method_name):
                                        try:
                                            value = getattr(value_obj, method_name)()
                                            if value is not None:
                                                element_info["default_value"] = str(value)
                                                break
                                        except:
                                            continue
                    except:
                        pass
                    
                    # 确定元素类型并分类
                    element_kind = self._get_element_kind(element)
                    element_info["kind"] = element_kind
                    
                    # 根据类型分类
                    if element_kind == 'Send Message':
                        signals["send_messages"].append(element_info)
                        print(f"  [SEND] 发送信号: {element_name}")
                    elif element_kind == 'Receive Message':
                        signals["receive_messages"].append(element_info)
                        print(f"  [RECV] 接收信号: {element_name}")
                    elif element_kind == 'Send Receive Message':
                        # 同时添加到发送和接收
                        signals["send_messages"].append(element_info.copy())
                        signals["receive_messages"].append(element_info.copy())
                        print(f"  [BOTH] 发送接收信号: {element_name}")
                    elif element_kind == 'Parameter':
                        signals["parameters"].append(element_info)
                        print(f"  [PARAM] 参数: {element_name}")
                    elif element_kind == 'Variable':
                        signals["variables"].append(element_info)
                        print(f"  [VAR] 变量: {element_name}")
                    elif element_kind == 'Constant':
                        signals["constants"].append(element_info)
                        print(f"  [CONST] 常量: {element_name}")
                    else:
                        signals["other_elements"].append(element_info)
                        print(f"  [OTHER] 其他: {element_name} ({element_kind})")
                
                except Exception as e:
                    print(f"[ERROR] 分析元素时出错 {element_name}: {str(e)}")
                    continue
            
            # 打印扫描汇总
            self._print_component_summary(signals, component_type)
            
            return signals
            
        except Exception as e:
            print(f"[ERROR] 扫描组件时出错: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def build_signal_library(self, a2a_path: str, xpass_path: str) -> bool:
        """构建A2A和XPass信号库
        
        Args:
            a2a_path: A2A组件路径
            xpass_path: XPass组件路径
            
        Returns:
            是否成功构建信号库
        """
        try:
            print(f"\n{'#'*100}")
            print(f"[LIBRARY] 构建信号库")
            print(f"{'#'*100}")
            
            self.signal_library["scan_timestamp"] = datetime.now().isoformat()
            
            # 扫描A2A组件
            print(f"\n[STEP1] 第1步：扫描A2A组件...")
            a2a_signals = self.scan_component_signals(a2a_path, "A2A")
            if "error" in a2a_signals:
                print(f"[ERROR] A2A组件扫描失败: {a2a_signals['error']}")
                return False
            
            self.signal_library["a2a_signals"] = a2a_signals
            
            # 扫描XPass组件
            print(f"\n[STEP2] 第2步：扫描XPass组件...")
            xpass_signals = self.scan_component_signals(xpass_path, "XPass")
            if "error" in xpass_signals:
                print(f"[ERROR] XPass组件扫描失败: {xpass_signals['error']}")
                return False
            
            self.signal_library["xpass_signals"] = xpass_signals
            
            # 保存信号库到文件
            self._save_signal_library()
            
            print(f"\n[SUCCESS] 信号库构建完成!")
            print(f"[INFO] A2A信号: {len(a2a_signals['send_messages']) + len(a2a_signals['receive_messages'])} 个message信号")
            print(f"[INFO] XPass信号: {len(xpass_signals['send_messages']) + len(xpass_signals['receive_messages'])} 个message信号")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 构建信号库时出错: {str(e)}")
            traceback.print_exc()
            return False
    
    def analyze_block_diagram_with_library(self, block_diagram_path: str) -> Dict:
        """使用信号库分析Block Diagram中的信号来源
        
        Args:
            block_diagram_path: Block Diagram的路径
            
        Returns:
            包含信号分析结果的字典
        """
        try:
            print(f"\n{'='*100}")
            print(f"[ANALYZE] 使用信号库分析Block Diagram: {block_diagram_path}")
            print(f"{'='*100}")
            
            # 检查信号库是否已构建
            if not self.signal_library["a2a_signals"] or not self.signal_library["xpass_signals"]:
                print("[ERROR] 信号库尚未构建，请先调用build_signal_library()")
                return {"error": "信号库未构建"}
            
            # 获取Block Diagram组件
            bd_component = self.get_component_by_path(block_diagram_path)
            if not bd_component:
                return {"error": f"无法找到Block Diagram: {block_diagram_path}"}
            
            # 获取所有模型元素
            model_elements = []
            if hasattr(bd_component, 'GetAllModelElements'):
                elements = bd_component.GetAllModelElements()
                if elements:
                    model_elements = elements
                    print(f"[INFO] Block Diagram中找到 {len(model_elements)} 个模型元素")
                else:
                    print("[ERROR] Block Diagram中未找到模型元素")
                    return {"error": "Block Diagram中没有模型元素"}
            else:
                print("[ERROR] Block Diagram不支持GetAllModelElements方法")
                return {"error": "Block Diagram不支持获取模型元素"}
            
            # 创建信号查找索引
            a2a_signal_names = set()
            xpass_signal_names = set()
            
            # 构建A2A信号名称集合
            for signal_list in [self.signal_library["a2a_signals"]["send_messages"], 
                               self.signal_library["a2a_signals"]["receive_messages"]]:
                for signal in signal_list:
                    a2a_signal_names.add(signal["name"])
            
            # 构建XPass信号名称集合
            for signal_list in [self.signal_library["xpass_signals"]["send_messages"], 
                               self.signal_library["xpass_signals"]["receive_messages"]]:
                for signal in signal_list:
                    xpass_signal_names.add(signal["name"])
            
            print(f"[INFO] A2A信号库包含 {len(a2a_signal_names)} 个信号名称")
            print(f"[INFO] XPass信号库包含 {len(xpass_signal_names)} 个信号名称")
            
            # 分析结果
            analysis_result = {
                "block_diagram_path": block_diagram_path,
                "analysis_timestamp": datetime.now().isoformat(),
                "signal_library_timestamp": self.signal_library["scan_timestamp"],
                "total_elements": len(model_elements),
                "a2a_sourced_signals": [],
                "xpass_sourced_signals": [],
                "unknown_source_signals": [],
                "non_message_elements": []
            }
            
            # 分析每个元素
            for element in model_elements:
                try:
                    if not element:
                        continue
                    
                    element_name = element.GetName() if hasattr(element, 'GetName') else "Unknown"
                    element_info = {
                        "name": element_name,
                        "type": "",
                        "scope": "",
                        "kind": "",
                        "matched_signal_details": None
                    }
                    
                    # 获取基本信息
                    if hasattr(element, 'GetModelType'):
                        element_info["type"] = element.GetModelType()
                    
                    if hasattr(element, 'GetScope'):
                        element_info["scope"] = element.GetScope()
                    
                    # 确定元素类型
                    element_kind = self._get_element_kind(element)
                    element_info["kind"] = element_kind
                    
                    # 只分析message类型的元素
                    if self._is_message_element(element):
                        print(f"\n[CHECK] 分析Message: {element_name}")
                        
                        # 在信号库中查找匹配
                        if element_name in a2a_signal_names:
                            # 找到详细信息
                            matched_detail = self._find_signal_details(element_name, "A2A")
                            element_info["matched_signal_details"] = matched_detail
                            analysis_result["a2a_sourced_signals"].append(element_info)
                            print(f"  [MATCH] 来自A2A: {element_name}")
                            
                        elif element_name in xpass_signal_names:
                            # 找到详细信息
                            matched_detail = self._find_signal_details(element_name, "XPass")
                            element_info["matched_signal_details"] = matched_detail
                            analysis_result["xpass_sourced_signals"].append(element_info)
                            print(f"  [MATCH] 来自XPass: {element_name}")
                            
                        else:
                            analysis_result["unknown_source_signals"].append(element_info)
                            print(f"  [UNKNOWN] 未知来源: {element_name}")
                    else:
                        # 非message元素
                        analysis_result["non_message_elements"].append(element_info)
                        if element_kind in ["Parameter", "Variable", "Constant"]:
                            print(f"  [NON-MSG] 非消息元素: {element_name} ({element_kind})")
                
                except Exception as e:
                    print(f"[ERROR] 分析元素时出错 {element_name}: {str(e)}")
                    continue
            
            # 打印分析结果汇总
            self._print_analysis_summary(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            print(f"[ERROR] 分析Block Diagram时出错: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}
    
    def _find_signal_details(self, signal_name: str, source_type: str) -> Dict:
        """在信号库中查找信号的详细信息"""
        try:
            signal_source = self.signal_library["a2a_signals"] if source_type == "A2A" else self.signal_library["xpass_signals"]
            
            # 在发送信号中查找
            for signal in signal_source["send_messages"]:
                if signal["name"] == signal_name:
                    return signal
            
            # 在接收信号中查找
            for signal in signal_source["receive_messages"]:
                if signal["name"] == signal_name:
                    return signal
            
            return None
            
        except Exception:
            return None
    
    def _get_element_kind(self, element) -> str:
        """获取元素类型"""
        try:
            if hasattr(element, 'IsReceiveMessage') and element.IsReceiveMessage():
                return 'Receive Message'
            if hasattr(element, 'IsSendMessage') and element.IsSendMessage():
                return 'Send Message'
            if hasattr(element, 'IsSendReceiveMessage') and element.IsSendReceiveMessage():
                return 'Send Receive Message'
            if hasattr(element, 'IsParameter') and element.IsParameter():
                return 'Parameter'
            if hasattr(element, 'IsVariable') and element.IsVariable():
                return 'Variable'
            if hasattr(element, 'IsConstant') and element.IsConstant():
                return 'Constant'
            if hasattr(element, 'IsMethodArgument') and element.IsMethodArgument():
                return 'Method Argument'
            if hasattr(element, 'IsMethodReturn') and element.IsMethodReturn():
                return 'Return Value'
            
            return 'Unknown'
        except Exception:
            return 'Unknown'
    
    def _is_message_element(self, element) -> bool:
        """检查元素是否是message类型"""
        try:
            if hasattr(element, 'IsReceiveMessage') and element.IsReceiveMessage():
                return True
            if hasattr(element, 'IsSendMessage') and element.IsSendMessage():
                return True
            if hasattr(element, 'IsSendReceiveMessage') and element.IsSendReceiveMessage():
                return True
            return False
        except Exception:
            return False
    
    def _print_component_summary(self, signals: Dict, component_type: str):
        """打印组件扫描汇总"""
        print(f"\n[SUMMARY] {component_type}组件扫描汇总:")
        print(f"  发送信号: {len(signals['send_messages'])}")
        print(f"  接收信号: {len(signals['receive_messages'])}")
        print(f"  参数: {len(signals['parameters'])}")
        print(f"  变量: {len(signals['variables'])}")
        print(f"  常量: {len(signals['constants'])}")
        print(f"  其他元素: {len(signals['other_elements'])}")
    
    def _print_analysis_summary(self, result: Dict):
        """打印Block Diagram分析结果汇总"""
        print(f"\n{'='*100}")
        print(f"[RESULT] Block Diagram信号来源分析结果")
        print(f"{'='*100}")
        
        print(f"总元素数量: {result['total_elements']}")
        print(f"A2A来源信号: {len(result['a2a_sourced_signals'])}")
        print(f"XPass来源信号: {len(result['xpass_sourced_signals'])}")
        print(f"未知来源信号: {len(result['unknown_source_signals'])}")
        print(f"非消息元素: {len(result['non_message_elements'])}")
        
        if result['a2a_sourced_signals']:
            print(f"\n[A2A] A2A来源信号列表:")
            for i, signal in enumerate(result['a2a_sourced_signals'], 1):
                print(f"  {i}. {signal['name']} ({signal['kind']})")
                if signal['matched_signal_details']:
                    details = signal['matched_signal_details']
                    if details.get('unit'):
                        print(f"     单位: {details['unit']}")
                    if details.get('comment'):
                        print(f"     说明: {details['comment']}")
        
        if result['xpass_sourced_signals']:
            print(f"\n[XPASS] XPass来源信号列表:")
            for i, signal in enumerate(result['xpass_sourced_signals'], 1):
                print(f"  {i}. {signal['name']} ({signal['kind']})")
                if signal['matched_signal_details']:
                    details = signal['matched_signal_details']
                    if details.get('unit'):
                        print(f"     单位: {details['unit']}")
                    if details.get('comment'):
                        print(f"     说明: {details['comment']}")
        
        if result['unknown_source_signals']:
            print(f"\n[UNKNOWN] 未知来源信号列表:")
            for i, signal in enumerate(result['unknown_source_signals'], 1):
                print(f"  {i}. {signal['name']} ({signal['kind']})")
    
    def _save_signal_library(self):
        """保存信号库到JSON文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"signal_library_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.signal_library, f, ensure_ascii=False, indent=2)
            
            print(f"[SAVE] 信号库已保存到: {filename}")
            
        except Exception as e:
            print(f"[ERROR] 保存信号库时出错: {str(e)}")
    
    def export_analysis_to_file(self, analysis_result: Dict, output_file: str = None):
        """将分析结果导出到文件"""
        try:
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"block_diagram_analysis_{timestamp}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("ASCET Block Diagram 信号来源分析报告\n")
                f.write("="*80 + "\n\n")
                f.write(f"分析时间: {analysis_result['analysis_timestamp']}\n")
                f.write(f"信号库构建时间: {analysis_result['signal_library_timestamp']}\n")
                f.write(f"Block Diagram: {analysis_result['block_diagram_path']}\n")
                f.write(f"总元素数量: {analysis_result['total_elements']}\n\n")
                
                # A2A来源信号
                f.write(f"A2A来源信号 ({len(analysis_result['a2a_sourced_signals'])}个):\n")
                f.write("-" * 60 + "\n")
                for i, signal in enumerate(analysis_result['a2a_sourced_signals'], 1):
                    f.write(f"{i}. {signal['name']} ({signal['kind']})\n")
                    if signal['matched_signal_details']:
                        details = signal['matched_signal_details']
                        f.write(f"   类型: {details.get('type', 'N/A')}\n")
                        f.write(f"   作用域: {details.get('scope', 'N/A')}\n")
                        f.write(f"   单位: {details.get('unit', 'N/A')}\n")
                        f.write(f"   说明: {details.get('comment', 'N/A')}\n")
                        if details.get('min') and details.get('max'):
                            f.write(f"   范围: {details['min']} ~ {details['max']}\n")
                    f.write("\n")
                
                # XPass来源信号
                f.write(f"XPass来源信号 ({len(analysis_result['xpass_sourced_signals'])}个):\n")
                f.write("-" * 60 + "\n")
                for i, signal in enumerate(analysis_result['xpass_sourced_signals'], 1):
                    f.write(f"{i}. {signal['name']} ({signal['kind']})\n")
                    if signal['matched_signal_details']:
                        details = signal['matched_signal_details']
                        f.write(f"   类型: {details.get('type', 'N/A')}\n")
                        f.write(f"   作用域: {details.get('scope', 'N/A')}\n")
                        f.write(f"   单位: {details.get('unit', 'N/A')}\n")
                        f.write(f"   说明: {details.get('comment', 'N/A')}\n")
                        if details.get('min') and details.get('max'):
                            f.write(f"   范围: {details['min']} ~ {details['max']}\n")
                    f.write("\n")
                
                # 未知来源信号
                f.write(f"未知来源信号 ({len(analysis_result['unknown_source_signals'])}个):\n")
                f.write("-" * 60 + "\n")
                for i, signal in enumerate(analysis_result['unknown_source_signals'], 1):
                    f.write(f"{i}. {signal['name']} ({signal['kind']})\n")
                    f.write(f"   类型: {signal.get('type', 'N/A')}\n")
                    f.write(f"   作用域: {signal.get('scope', 'N/A')}\n\n")
            
            print(f"[EXPORT] 分析结果已导出到: {output_file}")
            
        except Exception as e:
            print(f"[ERROR] 导出文件时出错: {str(e)}")
    
    def disconnect(self):
        """断开ASCET连接"""
        if self.ascet:
            try:
                self.ascet.DisconnectFromTool()
                print("[DISCONNECT] 已断开ASCET连接")
            except Exception as e:
                print(f"[ERROR] 断开连接时出错: {str(e)}")


def main():
    """主函数 """
    # ASCET版本
    ascet_version = "6.1.4"
    
    # 定义组件路径
    a2a_component_path = r"\CN_Libary\Package\iTAS_IntelligenceTurningAssistanceSystem\Component\Asw2Asw_iTAS"
    xpass_component_path = r"\CN_Libary\Package\iTAS_IntelligenceTurningAssistanceSystem\Component\XPass_BB00000_iTAS"
    block_diagram_path = r"\CN_Libary\Package\iTAS_IntelligenceTurningAssistanceSystem\Component\Config\CM_iTAS"
    
    # 初始化分析器
    analyzer = AscetSignalLibraryAnalyzer(ascet_version)
    
    try:
        # 连接到ASCET
        if not analyzer.connect():
            print("[ERROR] 无法连接到ASCET，程序退出")
            return
        
        # 第一步：构建信号库
        print(f"\n[PHASE1] 开始第一步：构建A2A和XPass信号库...")
        if not analyzer.build_signal_library(a2a_component_path, xpass_component_path):
            print("[ERROR] 信号库构建失败，程序退出")
            return
        
        # 第二步：分析Block Diagram
        print(f"\n[PHASE2] 开始第二步：分析Block Diagram信号来源...")
        analysis_result = analyzer.analyze_block_diagram_with_library(block_diagram_path)
        
        if "error" not in analysis_result:
            # 导出分析结果
            analyzer.export_analysis_to_file(analysis_result)
            
            print(f"\n[COMPLETE] 分析完成！")
            print(f"找到 {len(analysis_result['a2a_sourced_signals'])} 个A2A来源信号")
            print(f"找到 {len(analysis_result['xpass_sourced_signals'])} 个XPass来源信号")
            print(f"发现 {len(analysis_result['unknown_source_signals'])} 个未知来源信号")
        else:
            print(f"[ERROR] 分析失败: {analysis_result['error']}")
        
    except Exception as e:
        print(f"[ERROR] 程序执行时出错: {str(e)}")
        traceback.print_exc()
        
    finally:
        # 断开连接
        analyzer.disconnect()


if __name__ == "__main__":
    main()