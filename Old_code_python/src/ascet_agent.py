

"""
=================================================================================
集成ASCET数据提取的代码审查系统
=================================================================================

主要特性：
    ✓ 自动化ASCET数据提取和分析
    ✓ 基于规则的代码质量检查
    ✓ AI驱动的深度代码分析
    ✓ RAG（检索增强生成）知识库集成
    ✓ 多种运行模式支持
    ✓ 统一的模型配置管理
    ✓ 详细的错误统计和报告生成
    ✓ Token使用统计和成本监控

运行模式：
    1. direct（直接模式）
       - 仅执行基础规则检查，无AI分析
    2. （AI_RULE）
       - 固定流程执行 + AI分析

工作流程：
    第一阶段：数据准备
    ├── ASCET数据库连接和扫描
    ├── 项目结构分析
    ├── 代码和信号数据提取
    └── 数据验证和内存加载
    
    第二阶段：质量分析
    ├── 审查器初始化和配置
    ├── 基础规则检查（命名规范、结构问题等）
    ├── AI深度分析（仅smart_direct模式）
    └── 错误统计和分类
    
    第三阶段：报告生成
    ├── 审查报告生成（Word格式）
    ├── JSON格式错误统计
    ├── 执行摘要和性能统计
    └── Token使用和成本分析


=================================================================================
"""

import os
import json
import re
import time
import random
import hashlib
import pickle
import numpy as np
import math
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from tqdm import tqdm
from win32com.client import Dispatch
from datetime import datetime
import xml.etree.ElementTree as ET
import sys
import traceback
import shutil


from src.ai_core.ai_error_arbitrator import (
    AIErrorArbitrator, 
    AIErrorExtractor, 
    create_arbitrator,
    extract_ai_errors
)

# ==================== 导入模型配置管理 ====================
try:
    from src.ai_core.model_config import ModelConfig, create_model_config
    print("Model Configuration module imported successfully")
except ImportError as e:
    print(f"Model Configuration import failed: {e}")
    print("Please ensure model_config.py is available")
    sys.exit(1)

# ==================== 导入统一Token统计系统 ====================
try:
    from src.ai_core.token_tracker import global_token_tracker, track_response, get_token_summary, reset_token_tracker
    print("Token Counter ok")
except ImportError as e:
    print(f"Token Counter error: {e}")
  

# ==================== TOOL模块 ====================
try:
    from src.agents.ascet_tool import (
        RateLimiter, EmbeddingGenerator, HistoricalCaseRetriever, 
        AscetCodeExtractor, RAGEnhancedAIReviewer, RAGEnhancedCodeReviewer
    )
    print("RAG modules imported successfully")
except ImportError as e:
    print(f"RAG modules import failed: {e}")

try:
    from src.tools.dsd_gen_tool import IntegratedAscetScanner
    print("ASCET data extraction module imported successfully")
except ImportError as e:
    print(f"ASCET data extraction module import failed: {e}")
    print("Please ensure the ASCET data extraction module is available")

try:
    from src.diagrams.diagram_ai_review import DiagramAIReviewFlow, is_diagram_item
    DIAGRAM_FLOW_AVAILABLE = True
except ImportError as e:
    DIAGRAM_FLOW_AVAILABLE = False
    print(f"Diagram AI flow import failed: {e}")

# ==================== 执行进度管理 ====================
class ProgressTracker:
    """执行进度跟踪器"""
    def __init__(self, mode: str):
        self.mode = mode
        self.start_time = time.time()
        self.current_step = 0
        
        if mode == "direct":
            self.total_steps = 6
        elif mode == "smart_direct":
            self.total_steps = 7
        self.step_details = []
        self.step_names = self._get_step_names()
        
    def _get_step_names(self):
        if self.mode == "direct":
            return [
                "ASCET数据提取",
                "审查器初始化", 
                "基础规则检查",
                "报告生成",
                "错误统计输出",
                "执行摘要"
            ]
        elif self.mode == "smart_direct":
            return [
                "ASCET数据提取",
                "审查器初始化",
                "规则检查", 
                "Wrong Variable Assignment Check",
                "报告生成",
                "错误统计输出",
                "执行摘要"
            ]
    
    def start_step(self, step_name: str):
        """开始执行步骤"""
        self.current_step += 1
        step_info = {
            "step_number": self.current_step,
            "step_name": step_name,
            "start_time": time.time(),
            "status": "RUNNING"
        }
        self.step_details.append(step_info)
        progress_percent = (self.current_step / self.total_steps) * 100
        print(f"[{self.current_step}/{self.total_steps}] ({progress_percent:.1f}%) 开始执行: {step_name}")
        
    def complete_step(self, status: str = "SUCCESS", details: str = ""):
        """完成当前步骤"""
        if self.step_details:
            current = self.step_details[-1]
            current["end_time"] = time.time()
            current["duration"] = current["end_time"] - current["start_time"]
            current["status"] = status
            current["details"] = details
            
            status_symbol = "完成" if status == "SUCCESS" else "失败" if status == "ERROR" else "警告"
            print(f"[{current['step_number']}/{self.total_steps}] {status_symbol}: {current['step_name']} (耗时: {current['duration']:.2f}秒)")
            if details:
                print(f"    详情: {details}")
    
    def get_progress_summary(self):
        """获取进度摘要"""
        total_time = time.time() - self.start_time
        completed_steps = len([s for s in self.step_details if s.get("status") != "RUNNING"])
        
        summary = {
            "mode": self.mode,
            "total_steps": self.total_steps,
            "completed_steps": completed_steps,
            "current_step": self.current_step,
            "progress_percent": (completed_steps / self.total_steps) * 100,
            "total_execution_time": total_time,
            "step_details": self.step_details
        }
        return summary

# ====================  共享状态管理 ====================
class ReviewerState:
    """代码审查器的共享状态"""
    def __init__(self, mode: str = "smart_direct"):
        # 基础状态
        self.mode = mode
        self.progress_tracker = ProgressTracker(mode)
        self.reviewer = None
        self.extracted_code = None
        self.basic_issues = []
        self.ai_review = None
        self.final_report = None
        self.execution_log = []
        self.config = None
        self.model_config = None  # 添加模型配置
        
        # 报告文件管理状态
        self.generated_reports = []
        self.current_report_path = None
        self.output_dir = None
        self.report_output_dir = None
        
        # ASCET数据提取相关状态
        self.ascet_scanner = None
        self.json_data = None
        self.data_collection_status = None
        self.ascet_class_path = None
        self.ascet_extraction_info = {}
        self.data_extraction_time = 0.0
        
        # 错误统计状态
        self.error_statistics = None
        self.error_statistics_json = None
        
        # UI回调函数
        self.agent_callback = None
        self.status_callback = None


         # 仲裁相关属性
        self.arbitrator = None
        self.ai_arbitration_enabled = True
        self.primary_ai_errors = []
        self.fallback_ai_errors = []
        self.arbitrated_ai_errors = []
        self.arbitration_in_progress = False
        self.arbitration_completed = False
        
    def set_model_config(self, model_config: ModelConfig):
        """设置模型配置"""
        self.model_config = model_config
        self.log_step("ModelConfig", "SUCCESS", f"模型配置设置: {model_config.get_model_name()}")
    
    def log_step(self, step_name: str, status: str, details: str = ""):
        """记录执行步骤"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step_name,
            "status": status,
            "details": details
        }
        self.execution_log.append(log_entry)
        
        # 使用回调发送到UI
        if self.agent_callback:
            self.agent_callback(f"[{step_name}] {status}: {details}")
        else:
            print(f" [{step_name}] {status}: {details}")
    
    def send_status(self, message: str):
        """发送状态消息到UI"""
        if self.status_callback:
            self.status_callback(message)
        else:
            print(f"STATUS: {message}")
    
    def set_json_data(self, json_data: Dict[str, Any]):
        """设置内存中的JSON数据"""
        self.json_data = json_data
        self.log_step("DataMemorySet", "SUCCESS", f"JSON数据已设置到内存 ({len(str(json_data))} 字符)")
    
    def get_json_data(self) -> Dict[str, Any]:
        """获取内存中的JSON数据"""
        return self.json_data
    
    def add_generated_report(self, report_path: str):
        """记录生成的报告文件"""
        if report_path and report_path not in self.generated_reports:
            self.generated_reports.append(report_path)
            self.current_report_path = report_path
            self.log_step("ReportGenerated", "INFO", f"报告已生成: {os.path.basename(report_path)}")

# 全局状态对象
global_state = None


class DiagramQueueDummyError:
    """Return an empty-error review result for diagram items queued from UI."""

    @staticmethod
    def is_diagram_item(class_path: Optional[str]) -> bool:
        if DIAGRAM_FLOW_AVAILABLE:
            return is_diagram_item(class_path)
        if not class_path:
            return False
        normalized = str(class_path).strip().lower()
        return normalized.endswith(".amd") or ".specification.amd" in normalized

    @staticmethod
    def build_result(config: Dict[str, Any], mode: str) -> Dict[str, Any]:
        class_path = str(config.get("class_path", ""))
        diagram_name = Path(class_path).name if class_path else "UnknownDiagram"
        empty_error_statistics = {
            "rule_errors": 0,
            "ai_errors": 0,
            "total_errors": 0,
            "rule_error_details": [],
            "ai_error_details": [],
            "rule_severity_stats": {
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0,
                "has_high_severity": False
            }
        }

        return {
            "status": "success",
            "mode": mode,
            "execution_time": 0.0,
            "basic_issues": [],
            "ai_review": "Diagram item detected in queue. Dummy review applied (empty error set).",
            "final_report": None,
            "current_report_path": None,
            "ascet_extraction_info": {
                "class_path": class_path,
                "diagram_name": diagram_name,
                "dummy_review": True
            },
            "data_collection_status": "diagram_dummy",
            "data_extraction_time": 0.0,
            "json_data_size": 0,
            "error_statistics": empty_error_statistics,
            "error_statistics_json": {
                "error_statistics": empty_error_statistics,
                "mode": mode,
                "class_path": class_path,
                "note": "Diagram queue item - dummy empty error result"
            },
            "summary": f"Diagram queue item skipped from ASCET class review: {diagram_name}",
            "token_statistics": "Diagram dummy review: no API calls"
        }

# ==================== ASCET数据提取Tool函数 ====================

def extract_ascet_data_tool(input_params: str) -> str:
    """从ASCET提取数据并保存到内存"""
    try:
        if not global_state.config:
            raise Exception("全局配置未设置")
        
        # 从配置中提取参数
        class_path = global_state.config.get("class_path")
        ascet_version = global_state.config.get("ascet_version", "6.1.4")
        
        if not class_path:
            raise Exception("类路径未在配置中设置")
        
        global_state.log_step("ASCETExtract", "RUNNING", f"开始提取ASCET数据: {class_path}")
        global_state.send_status(f"正在提取ASCET数据: {class_path}")
        
        # 初始化ASCET扫描器
        scanner = IntegratedAscetScanner(ascet_version)
        global_state.ascet_scanner = scanner
        
        if not scanner.connect():
            raise Exception("无法连接到ASCET数据库")
        
        global_state.log_step("ASCETConnect", "SUCCESS", "已连接到ASCET数据库")
        
        # 扫描数据库结构
        if not scanner.scan_database_structure():
            raise Exception("数据库结构扫描失败")
        
        # 收集数据
        start_time = time.time()
        if not scanner.collect_all_data(class_path):
            raise Exception("数据收集失败")
        
        global_state.data_extraction_time = time.time() - start_time
        
        # 获取JSON数据并保存到内存
        json_data_str = scanner.get_json_data(class_path, indent=None)
        json_data = json.loads(json_data_str)
        
        # 保存到全局状态
        global_state.set_json_data(json_data)
        global_state.ascet_class_path = class_path
        global_state.data_collection_status = "success"
        
        # 提取关键信息
        signals_count = len(json_data.get("signals", []))
        import_sources = json_data.get("import_sources", [])
        
        global_state.ascet_extraction_info = {
            "signals_count": signals_count,
            "import_sources_count": len(import_sources),
            "extraction_time": global_state.data_extraction_time,
            "class_path": class_path
        }
        
        summary = f"ASCET数据提取成功"
        summary += f"\n- 类路径: {class_path}"
        summary += f"\n- 信号数量: {signals_count}"
        summary += f"\n- 导入源: {len(import_sources)} 个"
        summary += f"\n- 提取耗时: {global_state.data_extraction_time:.2f} 秒"
        summary += f"\n- 数据已保存到内存"
        
        global_state.log_step("ASCETExtract", "SUCCESS", summary)
        
        return f"SUCCESS: {summary}"
        
    except Exception as e:
        error_msg = f"ASCET数据提取失败: {str(e)}"
        global_state.log_step("ASCETExtract", "ERROR", error_msg)
        global_state.data_collection_status = "failed"
        return f"ERROR: {error_msg}"

# ==================== 错误统计功能 ====================

def collect_error_statistics() -> Dict[str, Any]:
    """收集和统计规则错误"""
    try:
        statistics = {
            "rule_errors": 0,
            "ai_errors": 0,
            "total_errors": 0,
            "rule_error_details": [],
            "ai_error_details": [],
            "rule_severity_stats": {
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0,
                "has_high_severity": False
            }
        }
        
        # 处理规则错误
        if global_state.basic_issues:
            statistics["rule_errors"] = len(global_state.basic_issues)
            
            print(f"调试：共有 {len(global_state.basic_issues)} 个规则问题")
            
            for issue in global_state.basic_issues:
                severity = (issue.get('severity') or 
                           issue.get('Severity') or 
                           issue.get('SEVERITY') or 
                           'Unknown')
                
                print(f"   问题: {issue.get('type', 'Unknown')}, 原始severity: '{severity}'")
                
                error_detail = {
                    "type": issue.get('type', 'Unknown'),
                    "message": issue.get('description', '') or issue.get('message', '') or "未提供详细信息",
                    "severity": severity
                }
                
                statistics["rule_error_details"].append(error_detail)
                
                # 严格按照severity字段分类
                severity_str = str(severity).strip().lower()
                
                if severity_str in ['high', 'h', '高', 'critical', 'error']:
                    statistics["rule_severity_stats"]["high_severity"] += 1
                    statistics["rule_severity_stats"]["has_high_severity"] = True
                elif severity_str in ['medium', 'med', 'm', '中', 'warning', 'warn']:
                    statistics["rule_severity_stats"]["medium_severity"] += 1
                elif severity_str in ['low', 'l', '低', 'info', 'minor']:
                    statistics["rule_severity_stats"]["low_severity"] += 1
            
            # 处理未分类错误
            accounted_errors = (statistics["rule_severity_stats"]["high_severity"] + 
                              statistics["rule_severity_stats"]["medium_severity"] + 
                              statistics["rule_severity_stats"]["low_severity"])
            
            unaccounted_errors = statistics["rule_errors"] - accounted_errors
            if unaccounted_errors > 0:
                statistics["rule_severity_stats"]["high_severity"] += unaccounted_errors
                statistics["rule_severity_stats"]["has_high_severity"] = True
        
        
        
        # 处理AI错误 - 集成仲裁逻辑
        if global_state.arbitration_completed and global_state.arbitrated_ai_errors is not None:
            # 使用仲裁后的结果
            statistics["ai_errors"] = len(global_state.arbitrated_ai_errors)
            statistics["ai_error_details"] = global_state.arbitrated_ai_errors
            
            global_state.log_step("ArbitrationStats", "SUCCESS", 
                f"使用仲裁结果: 最终确认{statistics['ai_errors']}个AI错误")
        else:
            # 使用支持仲裁的错误提取
            ai_errors, ai_error_details = extract_ai_errors_from_review_with_arbitration()
            statistics["ai_errors"] = ai_errors
            statistics["ai_error_details"] = ai_error_details
        
        statistics["total_errors"] = statistics["rule_errors"] + statistics["ai_errors"]
        
        global_state.error_statistics = statistics
        
        global_state.log_step("ErrorStatistics", "SUCCESS", 
                            f"错误统计完成: 规则错误{statistics['rule_errors']}个, AI错误{statistics['ai_errors']}个, 总计{statistics['total_errors']}个")
        
        return statistics
        
    except Exception as e:
        error_msg = f"错误统计失败: {str(e)}"
        global_state.log_step("ErrorStatistics", "ERROR", error_msg)
        
        fallback_statistics = {
            "rule_errors": 0,
            "ai_errors": 0, 
            "total_errors": 0,
            "rule_error_details": [],
            "ai_error_details": [],
            "rule_severity_stats": {
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0,
                "has_high_severity": False
            },
            "error": error_msg
        }
        
        global_state.error_statistics = fallback_statistics
        return fallback_statistics

def extract_ai_errors_from_review() -> Tuple[int, List[Dict[str, Any]]]:
    """从AI审查结果中提取错误信息 - 处理多个独立JSON对象"""
    try:
        if not global_state.ai_review:
            print("AI审查结果为空")
            return 0, []
        
        ai_review_text = global_state.ai_review
        ai_error_details = []
        
        print(f"开始解析AI审查结果，文本长度: {len(ai_review_text)}")
        
        import re
        import json
        
        # 方法1: 首先尝试查找完整的JSON代码块
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        json_matches = re.findall(json_pattern, ai_review_text, re.DOTALL | re.IGNORECASE)
        
        print(f"找到JSON代码块数量: {len(json_matches)}")
        
        if json_matches:
            for i, json_str in enumerate(json_matches):
                print(f"处理JSON代码块 {i+1}")
                ai_error_details.extend(parse_single_or_multiple_json(json_str))
        
        # 方法2: 如果没找到代码块，尝试查找裸露的JSON
        if not ai_error_details:
            print("未找到JSON代码块，尝试查找裸露JSON...")
            json_objects = extract_json_objects_from_text(ai_review_text)
            print(f"找到裸露JSON对象数量: {len(json_objects)}")
            
            for json_obj in json_objects:
                ai_error_details.extend(parse_single_or_multiple_json(json_obj))
        
        # 方法3: 备用的关键词匹配
        if not ai_error_details:
            print("JSON解析完全失败，尝试关键词匹配...")
            ai_error_details.extend(fallback_keyword_extraction(ai_review_text))
        
        ai_error_count = len(ai_error_details)
        print(f"最终AI错误统计: {ai_error_count} 个")
        
        for j, error in enumerate(ai_error_details):
            print(f"  AI错误 {j+1}: {error['type']} - {error['message'][:50]}...")
        
        return ai_error_count, ai_error_details
        
    except Exception as e:
        print(f"AI错误提取异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0, []
    

def extract_ai_errors_from_review_with_arbitration() -> Tuple[int, List[Dict[str, Any]]]:
    """从AI审查结果中提取错误信息，支持仲裁流程"""
    try:
        if not global_state.ai_review:
            return 0, []
        
        # 使用仲裁模块的错误提取器
        extracted_errors = extract_ai_errors(global_state.ai_review)
        
        # 检查是否需要触发仲裁
        if (extracted_errors and 
            global_state.ai_arbitration_enabled and 
            not global_state.arbitration_in_progress and 
            not global_state.arbitration_completed):
            
            # 第一次检测到AI错误，准备仲裁
            global_state.primary_ai_errors = extracted_errors
            global_state.arbitration_in_progress = True
            
            error_types = [error.get('type', 'Unknown') for error in extracted_errors]
            global_state.log_step("ArbitrationTrigger", "WARNING", 
                f"检测到{len(extracted_errors)}个AI错误，触发仲裁流程: {', '.join(error_types)}")
            
            # 返回空列表，等待仲裁完成
            return 0, []
        
        elif (global_state.arbitration_in_progress and 
              not global_state.arbitration_completed):
            
            # 第二次分析，用于仲裁
            global_state.fallback_ai_errors = extracted_errors
            
            error_types = [error.get('type', 'Unknown') for error in extracted_errors]
            global_state.log_step("ArbitrationFallback", "INFO", 
                f"备用模型检测到{len(extracted_errors)}个AI错误: {', '.join(error_types)}")
            
            # 执行仲裁
            perform_ai_error_arbitration()
            
            # 返回仲裁结果
            return len(global_state.arbitrated_ai_errors), global_state.arbitrated_ai_errors
        
        else:
            # 仲裁已完成或被禁用，直接返回提取的错误
            return len(extracted_errors), extracted_errors
        
    except Exception as e:
        print(f"AI错误提取异常: {str(e)}")
        return 0, []

def perform_ai_error_arbitration():
    """执行AI错误仲裁"""
    try:
        if not global_state.arbitrator:
            # 创建仲裁器
            strategy = global_state.config.get("arbitration_strategy", "conservative")
            global_state.arbitrator = create_arbitrator(strategy=strategy)
        
        # 执行仲裁
        global_state.arbitrated_ai_errors = global_state.arbitrator.arbitrate_errors(
            global_state.primary_ai_errors,
            global_state.fallback_ai_errors
        )
        
        global_state.arbitration_completed = True
        global_state.arbitration_in_progress = False
        
        global_state.log_step("ArbitrationCompleted", "SUCCESS", 
            f"仲裁完成: 最终确认{len(global_state.arbitrated_ai_errors)}个AI错误")
        
    except Exception as e:
        global_state.log_step("ArbitrationError", "ERROR", f"仲裁执行失败: {str(e)}")
        # 仲裁失败时使用保守策略：不报告任何AI错误
        global_state.arbitrated_ai_errors = []
        global_state.arbitration_completed = True
        global_state.arbitration_in_progress = False

def parse_single_or_multiple_json(json_text: str) -> List[Dict[str, Any]]:
    """解析单个或多个JSON对象"""
    import json
    
    errors = []
    
    # 首先尝试作为单个JSON解析
    try:
        data = json.loads(json_text)
        print(f"成功解析为单个JSON，顶级键: {list(data.keys())}")
        errors.extend(process_json_data(data))
        return errors
    except json.JSONDecodeError as e:
        print(f"单个JSON解析失败: {e}")
        
        # 尝试分割为多个JSON对象
        json_objects = split_multiple_json_objects(json_text)
        print(f"尝试分割为多个JSON对象: {len(json_objects)} 个")
        
        for i, obj_text in enumerate(json_objects):
            try:
                data = json.loads(obj_text.strip())
                print(f"成功解析JSON对象 {i+1}，键: {list(data.keys())}")
                errors.extend(process_json_data(data))
            except json.JSONDecodeError as sub_e:
                print(f"JSON对象 {i+1} 解析失败: {sub_e}")
                print(f"失败的JSON文本: {obj_text[:100]}...")
                continue
    
    return errors

def split_multiple_json_objects(text: str) -> List[str]:
    """分割包含多个JSON对象的文本"""
    json_objects = []
    brace_count = 0
    current_obj = ""
    in_string = False
    escape_next = False
    
    for char in text:
        if escape_next:
            escape_next = False
            current_obj += char
            continue
        
        if char == '\\':
            escape_next = True
            current_obj += char
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
        
        current_obj += char
        
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                
                # 当大括号平衡时，我们可能找到了一个完整的JSON对象
                if brace_count == 0 and current_obj.strip():
                    json_objects.append(current_obj.strip())
                    current_obj = ""
    
    # 如果还有未处理的内容
    if current_obj.strip():
        json_objects.append(current_obj.strip())
    
    return json_objects

def process_json_data(data: Dict) -> List[Dict[str, Any]]:
    """处理单个JSON数据对象"""
    errors = []
    
    # 检查是否是扁平结构（直接包含"错误类型"）
    if "错误类型" in data:
        print("处理扁平JSON结构")
        error = process_flat_json_structure(data)
        if error:
            errors.append(error)
    
    # 检查是否是嵌套结构
    else:
        print("处理嵌套JSON结构")
        for category, error_data in data.items():
            if isinstance(error_data, dict) and "错误类型" in error_data:
                error = process_flat_json_structure(error_data, category)
                if error:
                    errors.append(error)
    
    return errors

def process_flat_json_structure(error_data: Dict, category: str = None) -> Dict[str, Any]:
    """
    处理扁平的JSON结构 
    Args:
        error_data: 错误数据字典
        category: 错误分类（可选）
    
    Returns:
        Dict[str, Any]: 错误详情字典，如果无错误则返回None
    """
    # 获取状态信息，处理不同的数据格式
    status_value = error_data.get("状态", [])
    error_types = error_data.get("错误类型", [])
    reason = error_data.get("理由", "")
    
    # 标准化状态格式为列表
    if isinstance(status_value, str):
        status_list = [status_value.strip()]
    elif isinstance(status_value, list):
        status_list = [str(s).strip() for s in status_value]
    else:
        status_list = []
    
    # 调试输出
    print(f"  处理错误类型: {error_types}")
    print(f"  原始状态: {repr(status_value)}")
    print(f"  处理后状态列表: {status_list}")
    
    # 定义表示缺陷的状态值
    DEFECT_STATUSES = {
        "Defect", "defect", "DEFECT",
        "Error", "error", "ERROR", 
        "错误", "缺陷", "问题"
    }
    
    # 定义表示无缺陷的状态值
    NO_DEFECT_STATUSES = {
        "No Defect", "no defect", "NO DEFECT",
        "No Error", "no error", "NO ERROR",
        "无缺陷", "无错误", "正常", "通过"
    }
    
    # 检查是否存在缺陷状态
    has_defect = any(status in DEFECT_STATUSES for status in status_list)
    has_no_defect = any(status in NO_DEFECT_STATUSES for status in status_list)
    
    print(f"  缺陷状态检查: has_defect={has_defect}, has_no_defect={has_no_defect}")
    
    # 只有明确的缺陷状态才认为是错误
    if has_defect and not has_no_defect:
        print("  发现真实缺陷!")
        
        # 确定错误类型
        if category:
            error_type = category
        elif error_types:
            error_type = error_types[0] if isinstance(error_types, list) else str(error_types)
        else:
            error_type = "未知AI错误"
        
        # 提取额外信息
        code_info = ""
        methods_issue = ""
        
        for key, value in error_data.items():
            if "代码行号" in key or "行号" in key:
                code_info += f"{key}: {value}\n"
            elif "Methods问题" in key or "方法问题" in key:
                methods_issue = str(value)
        
        # 根据错误类型确定严重程度
        if any(keyword in error_type for keyword in ["位置变量映射错误", "返回值变量名称映射错误", "变量映射"]):
            severity = "medium"
        elif any(keyword in error_type for keyword in ["一致性", "命名", "格式"]):
            severity = "medium"
        else:
            severity = "medium"
        
        error_detail = {
            "type": error_type,
            "message": reason or f"AI检测到{error_type}",
            "severity": severity,
            "code_info": code_info.strip(),
            "methods_issue": methods_issue,
            "raw_data": error_data,
            "status_analysis": {
                "original_status": status_value,
                "processed_status": status_list,
                "has_defect": has_defect,
                "has_no_defect": has_no_defect
            }
        }
        
        print(f"  创建错误详情: {error_type} (严重程度: {severity})")
        return error_detail
        
    elif has_no_defect:
        print(f"  明确无缺陷状态 (状态: {status_list})")
        return None
        
    
    
def extract_json_objects_from_text(text: str) -> List[str]:
    """从文本中提取JSON对象"""
    import re
    
    # 查找看起来像JSON的内容
    # 匹配以 { 开始，包含"错误类型"或"状态"的结构
    patterns = [
        r'\{[^{}]*"错误类型"[^{}]*\}',
        r'\{[^{}]*"状态"[^{}]*\}',
    ]
    
    json_candidates = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        json_candidates.extend(matches)
    
    # 去重
    return list(set(json_candidates))

def fallback_keyword_extraction(text: str) -> List[Dict[str, Any]]:
    """备用的关键词提取方法"""
    errors = []
    
    # 检查是否包含明确的缺陷标识
    if '"状态": ["Defect"]' in text or '"状态": [ "Defect" ]' in text:
        print("通过关键词发现Defect状态")
        
        # 查找错误类型
        if "位置变量映射错误" in text:
            errors.append({
                "type": "位置变量映射错误",
                "message": "通过关键词匹配检测到位置变量映射错误",
                "severity": "medium",
                "extraction_method": "keyword_fallback"
            })
        
        if "返回值变量名称映射错误" in text:
            errors.append({
                "type": "返回值变量名称映射错误", 
                "message": "通过关键词匹配检测到返回值变量名称映射错误",
                "severity": "medium",
                "extraction_method": "keyword_fallback"
            })
    
    return errors

def find_json_in_text(text: str) -> List[str]:
    """在文本中查找JSON结构"""
    import re
    
    # 查找以 { 开始，包含"错误类型"的完整JSON结构
    pattern = r'\{[^{}]*?"错误类型"[^{}]*?\}'
    simple_matches = re.findall(pattern, text, re.DOTALL)
    
    if simple_matches:
        return simple_matches
    
    # 查找更复杂的嵌套JSON
    brace_count = 0
    start_pos = -1
    json_strings = []
    
    for i, char in enumerate(text):
        if char == '{':
            if brace_count == 0:
                start_pos = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_pos != -1:
                potential_json = text[start_pos:i+1]
                if "错误类型" in potential_json:
                    json_strings.append(potential_json)
                start_pos = -1
    
    return json_strings

def get_error_statistics_tool(input_params: str) -> str:
    """获取错误统计信息的工具函数"""
    try:
        # 统计错误
        if not hasattr(global_state, 'error_statistics') or not global_state.error_statistics:
            statistics = collect_error_statistics()
        else:
            statistics = global_state.error_statistics
        
        # 构建JSON输出
        json_output = {
            "error_statistics": {
                "rule_errors": statistics['rule_errors'],
                "ai_errors": statistics['ai_errors'], 
                "total_errors": statistics['total_errors'],
                "rule_error_details": statistics.get('rule_error_details', []),
                "ai_error_details": statistics.get('ai_error_details', []),
                "rule_severity_stats": statistics.get('rule_severity_stats', {
                    "high_severity": 0,
                    "medium_severity": 0,
                    "low_severity": 0,
                    "has_high_severity": False
                })
            },
            "mode": global_state.mode,
            "model_info": {
                "model_name": global_state.model_config.get_model_name() if global_state.model_config else "Unknown",
                "supports_reasoning": global_state.model_config.supports_reasoning() if global_state.model_config else False,
                "is_streaming": global_state.model_config.is_streaming() if global_state.model_config else False
            },
            "consistency_status": "REMOVED",
            "generated_after_consistency_check": False,
            "generation_timestamp": datetime.now().isoformat(),
            "class_path": global_state.config.get("class_path", ""),
            "report_file": global_state.current_report_path,
            "note": "一致性检查功能已移除，使用统一模型配置管理"
        }
        
        # 保存JSON输出到全局状态
        global_state.error_statistics_json = json_output
        
        # 保存统计文件
        try:
            statistics_file_path = _save_error_statistics_to_file(json_output)
            if statistics_file_path:
                global_state.log_step("ErrorStatisticsFileFinal", "SUCCESS", 
                                    f"错误统计文件已保存: {os.path.basename(statistics_file_path)}")
        except Exception as e:
            global_state.log_step("ErrorStatisticsFileFinal", "ERROR", 
                                f"保存错误统计文件失败: {str(e)}")
        
        # 格式化输出
        result = f"SUCCESS: 错误统计JSON报告 ({global_state.mode}模式):\n"
        result += f"- 规则错误: {statistics['rule_errors']} 个\n"
        result += f"- AI错误: {statistics['ai_errors']} 个\n"
        result += f"- 总错误: {statistics['total_errors']} 个\n"
        
        if global_state.model_config:
            result += f"- 使用模型: {global_state.model_config.get_model_name()}\n"
        
        result += f"\nJSON格式统计:\n"
        result += json.dumps(json_output, ensure_ascii=False, indent=2)
        
        if statistics_file_path:
            result += f"\n统计文件已保存: {os.path.basename(statistics_file_path)}"
        
        global_state.log_step("ErrorStatisticsJSON", "SUCCESS", 
                            f"JSON统计: 总错误{statistics['total_errors']}个")
        
        return result
        
    except Exception as e:
        return f"ERROR: 获取错误统计失败: {str(e)}"
    
def _save_error_statistics_to_file(json_output: dict) -> str:
    """将错误统计JSON保存到文件系统"""
    try:
        stats_path = None
        
        # 方法1: 基于当前报告文件路径
        if global_state.current_report_path and os.path.exists(global_state.current_report_path):
            report_path = os.path.normpath(global_state.current_report_path)
            stats_path = os.path.splitext(report_path)[0] + "_statistics.json"
        
        # 方法2: 基于final_report
        elif global_state.final_report and global_state.final_report.get('filename'):
            report_path = os.path.normpath(global_state.final_report['filename'])
            if os.path.exists(report_path):
                stats_path = os.path.splitext(report_path)[0] + "_statistics.json"
        
        # 方法3: 默认路径
        if not stats_path:
            output_dir = global_state.output_dir or global_state.report_output_dir or "direct_reports"
            output_dir = os.path.normpath(output_dir)
            
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            class_name = "Unknown_Class"
            
            if global_state.config and global_state.config.get("class_path"):
                class_path = global_state.config["class_path"]
                class_name = class_path.split('\\')[-1] if '\\' in class_path else class_path.split('/')[-1]
            
            model_name = global_state.model_config.get_model_name() if global_state.model_config else "Unknown"
            stats_filename = f"ErrorStatistics_{class_name}_{model_name}_{timestamp}.json"
            stats_path = os.path.join(output_dir, stats_filename)
        
        stats_path = os.path.normpath(stats_path)
        
        # 确保目录存在
        stats_dir = os.path.dirname(stats_path)
        if not os.path.exists(stats_dir):
            os.makedirs(stats_dir, exist_ok=True)
        
        # 添加保存信息到JSON
        json_output_with_info = json_output.copy()
        json_output_with_info["save_info"] = {
            "save_timestamp": datetime.now().isoformat(),
            "save_path": stats_path,
            "report_file": global_state.current_report_path
        }
        
        # 写入文件
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(json_output_with_info, f, ensure_ascii=False, indent=2)
        
        # 验证文件存在
        if os.path.exists(stats_path):
            file_size = os.path.getsize(stats_path)
            global_state.log_step("StatisticsFileSave", "SUCCESS", 
                                f"错误统计文件已保存: {os.path.basename(stats_path)} ({file_size} 字节)")
            return stats_path
        else:
            raise Exception("文件写入后不存在")
        
    except Exception as e:
        global_state.log_step("StatisticsFileSave", "ERROR", f"保存错误统计文件失败: {str(e)}")
        return None



# ==================== 审查器Tool函数 ====================

def initialize_reviewer_tool(config_input: str) -> str:
    """初始化代码审查器（使用统一模型配置）"""
    try:
        config = global_state.config
        if not config:
            raise Exception("全局配置未设置")
        
        # 检查是否已有ASCET数据
        if not global_state.json_data:
            return "ERROR: 初始化失败: 请先提取ASCET数据"
        
        global_state.send_status("正在初始化代码审查器...")
        
        # 从配置中提取参数
        class_path = config.get("class_path")
        api_key = config.get("api_key")  # 统一的API密钥字段
        embedding_api_key = config.get("embedding_api_key")
        knowledge_base_path = config.get("knowledge_base_path", "esdl_knowledge_base")
        ascet_version = config.get("ascet_version", "6.1.4")
        diagram_name = config.get("diagram_name", "Main")
        method_name = config.get("method_name", "calc")
        
        # 检查必要的API密钥（smart_direct模式下需要）
        if global_state.mode == "smart_direct" and (not api_key or not embedding_api_key):
            raise Exception("智能模式下API密钥未设置")
        
        # 初始化ASCET提取器（如果还没有）
        if not hasattr(global_state, 'ascet_extractor') or not global_state.ascet_extractor:
            extractor = AscetCodeExtractor(version=ascet_version)
            if not extractor.connect():
                raise Exception("Failed to connect to ASCET")
            global_state.ascet_extractor = extractor
        else:
            extractor = global_state.ascet_extractor
        
        # 提取代码
        code, error = extractor.extract_method_code(class_path, diagram_name, method_name)
        if error or not code:
            raise Exception(f"Error extracting code: {error or 'No code extracted'}")
        
        # 创建临时JSON文件（仅用于兼容性）
        temp_json_path = "temp_memory_data.json"
        with open(temp_json_path, 'w', encoding='utf-8') as f:
            json.dump(global_state.json_data, f, ensure_ascii=False, indent=2)
        
        # 初始化审查器（使用统一API密钥）
        reviewer = RAGEnhancedCodeReviewer(
            json_file_path=temp_json_path,  # 临时文件路径
            deepseek_api_key=api_key or "dummy",  # 使用统一API密钥
            embedding_api_key=embedding_api_key or "dummy",
            knowledge_base_path=knowledge_base_path,
            ascet_extractor=extractor,
            ascet_version=ascet_version,
            model_type=global_state.model_config.get_model_name()
        )
        # 设置输出目录
        reviewer.output_dir = global_state.output_dir
        reviewer.report_output_dir = global_state.report_output_dir
        
        # 加载数据
        if not reviewer.load_data():
            raise Exception("Failed to load JSON data")
        
        # 设置内存中的JSON数据（覆盖文件数据）
        reviewer.json_data = global_state.json_data
        reviewer.set_code(code)
        
        # 清理临时文件
        try:
            os.remove(temp_json_path)
        except:
            pass
        
        # 保存到全局状态
        global_state.reviewer = reviewer
        global_state.extracted_code = code
        
        model_info = f"使用模型: {global_state.model_config.get_model_name()}" if global_state.model_config else "模型未配置"
        
        global_state.log_step("Initialize", "SUCCESS", f"审查器初始化成功，代码长度: {len(code)} 字符，{model_info}")
        
        return f"SUCCESS: 审查器初始化成功，使用内存JSON数据，代码长度: {len(code)} 字符，{model_info}"
        
    except Exception as e:
        error_msg = f"初始化失败: {str(e)}"
        global_state.log_step("Initialize", "ERROR", error_msg)
        return f"ERROR: {error_msg}"

def run_basic_rule_checks() -> str:
    """执行基础规则检查"""
    try:
        if not global_state.reviewer:
            raise Exception("审查器未初始化，请先初始化审查器")
        
        global_state.log_step("BasicChecks", "RUNNING", "开始执行基础规则检查")
        global_state.send_status("正在执行基础规则检查...")
        
        # 执行基础规则检查
        issues = global_state.reviewer.perform_basic_rule_checks(include_reference_analysis=True)
        global_state.basic_issues = issues
        
        # 统计问题类型
        issue_types = {}
        for issue in issues:
            issue_type = issue.get('type', 'Unknown')
            severity = issue.get('severity', 'Unknown')
            key = f"{issue_type}({severity})"
            issue_types[key] = issue_types.get(key, 0) + 1
        
        summary = f"发现 {len(issues)} 个问题："
        for issue_type, count in issue_types.items():
            summary += f"\n  - {issue_type}: {count} 个"
        
        global_state.log_step("BasicChecks", "SUCCESS", summary)
        
        return f"SUCCESS: 基础规则检查完成\n{summary}"
        
    except Exception as e:
        error_msg = f"基础规则检查失败: {str(e)}"
        global_state.log_step("BasicChecks", "ERROR", error_msg)
        return f"ERROR: {error_msg}"

def run_smart_ai_analysis(config: Dict[str, Any], model_config: ModelConfig) -> str:
    """智能AI分析：支持AI错误仲裁"""
    try:
        if not global_state.reviewer:
            raise Exception("审查器未初始化，请先初始化审查器")
        
        model_name = model_config.get_model_name()
        global_state.log_step("SmartAIAnalysis", "RUNNING", f"开始AI分析（{model_name}）")
        global_state.send_status(f"正在进行AI深度分析（{model_name}）...")
        
        # 执行第一次AI分析
        ai_review = global_state.reviewer.generate_rag_enhanced_review()
        global_state.ai_review = ai_review
        
        # 检查错误统计（这会触发仲裁检查）
        statistics = collect_error_statistics()
        
        # 如果触发了仲裁，需要进行第二次分析
        if global_state.arbitration_in_progress:
            return perform_second_ai_analysis_for_arbitration(config, model_config)
        
        # 构建分析摘要
        ai_summary = f"AI分析完成（{model_name}）"
        if "位置变量映射错误" in ai_review:
            ai_summary += " - 检测到位置变量相关问题"
        if "返回值变量名称映射错误" in ai_review:
            ai_summary += " - 检测到返回值映射问题"
        if "参数映射名称一致性错误" in ai_review:
            ai_summary += " - 检测到参数映射一致性问题"
        if "No Defect" in ai_review:
            ai_summary += " - 未发现缺陷"
        
        # 添加仲裁信息
        if global_state.ai_arbitration_enabled:
            if statistics.get("ai_errors", 0) > 0:
                ai_summary += f" - 未触发仲裁（无AI错误）"
        
        global_state.log_step("SmartAIAnalysis", "SUCCESS", ai_summary)
        return f"SUCCESS: {ai_summary}\n分析长度: {len(ai_review)} 字符"
        
    except Exception as e:
        error_msg = f"AI分析失败: {str(e)}"
        global_state.log_step("SmartAIAnalysis", "ERROR", error_msg)
        return f"ERROR: {error_msg}"

def perform_second_ai_analysis_for_arbitration(config: Dict[str, Any], primary_model_config: ModelConfig) -> str:
    """执行第二次AI分析用于仲裁 - 正确切换模型"""
    try:
        # ✅ 从仲裁配对中获取备用模型
        from src.ai_core.ai_error_arbitrator import ModelConfigFactory
        
        primary_model_name = primary_model_config.get_model_name()
        fallback_model_name = ModelConfigFactory.ARBITRATION_PAIRS.get(primary_model_name, "gpt5-mini")
        
        global_state.log_step("ModelSwitch", "INFO", 
            f"仲裁模型切换: {primary_model_name} → {fallback_model_name}")
        
        # ✅ 创建备用模型配置
        try:
            fallback_model_config = create_model_config(fallback_model_name)
            
            # 临时切换审查器的模型配置
            original_model_config = global_state.model_config
            global_state.set_model_config(fallback_model_config)
            
            # 如果审查器支持动态模型切换，也更新审查器配置
            if hasattr(global_state.reviewer, 'model_type'):
                global_state.reviewer.model_type = fallback_model_name
            
            global_state.log_step("SecondAnalysis", "RUNNING", 
                f"开始第二次AI分析用于仲裁（{fallback_model_name}）")
            global_state.send_status(f"正在进行第二次AI分析用于仲裁（{fallback_model_name}）...")
            
        except ValueError as e:
            # 如果备用模型不可用，记录警告但继续使用原模型
            global_state.log_step("ModelSwitch", "WARNING", 
                f"校验模型{fallback_model_name}不可用，使用原模型: {str(e)}")
            fallback_model_config = primary_model_config
            fallback_model_name = primary_model_name
        
        # 执行第二次分析
        fallback_ai_review = global_state.reviewer.generate_rag_enhanced_review()
        global_state.ai_review = fallback_ai_review
        
     
        if 'original_model_config' in locals():
            global_state.set_model_config(original_model_config)
        
        # 收集第二次分析的统计信息并执行仲裁
        final_statistics = collect_error_statistics()
        
        # 构建仲裁结果摘要
        primary_count = len(global_state.primary_ai_errors)
        fallback_count = len(global_state.fallback_ai_errors)
        final_count = len(global_state.arbitrated_ai_errors)
        
        summary = f"AI错误仲裁完成："
        summary += f"\n  主模型({primary_model_name}): {primary_count} 个错误"
        summary += f"\n  校验模型({fallback_model_name}): {fallback_count} 个错误"
        summary += f"\n  最终确认: {final_count} 个真实错误"
        summary += f"\n  过滤误报: {primary_count + fallback_count - final_count} 个"
        
        global_state.log_step("ArbitrationAnalysis", "SUCCESS", summary)
        return f"SUCCESS: AI错误仲裁分析完成\n{summary}"
        
    except Exception as e:
        error_msg = f"仲裁分析失败: {str(e)}"
        global_state.log_step("ArbitrationAnalysis", "ERROR", error_msg)
        
        # 仲裁失败时使用保守策略
        global_state.arbitrated_ai_errors = []
        global_state.arbitration_completed = True
        global_state.arbitration_in_progress = False
        
        return f"ERROR: {error_msg}. 采用保守策略，不报告任何AI错误。"

# ================== 日志函数 ==================

def initialize_arbitration_system(config: Dict[str, Any], primary_model_config: ModelConfig):
    """初始化仲裁系统，预先创建模型配置"""
    try:
        from src.ai_core.ai_error_arbitrator import ModelConfigFactory, create_arbitrator
        
        primary_model_name = primary_model_config.get_model_name()
        fallback_model_name = ModelConfigFactory.ARBITRATION_PAIRS.get(primary_model_name)
        
        if fallback_model_name:
            global_state.log_step("ArbitrationInit", "INFO", 
                f"仲裁系统初始化: 主模型={primary_model_name}, 校验模型={fallback_model_name}")
            
            # 预先验证备用模型可用性
            try:
                fallback_config = create_model_config(fallback_model_name)
                global_state.log_step("ArbitrationInit", "SUCCESS", 
                    f"备用模型{fallback_model_name}验证通过")
                return True
            except Exception as e:
                global_state.log_step("ArbitrationInit", "WARNING", 
                    f"备用模型{fallback_model_name}验证失败: {str(e)}")
                return False
        else:
            global_state.log_step("ArbitrationInit", "WARNING", 
                f"无法找到模型{primary_model_name}的仲裁配对")
            return False
            
    except Exception as e:
        global_state.log_step("ArbitrationInit", "ERROR", 
            f"仲裁系统初始化失败: {str(e)}")
        return False

def generate_report() -> str:
    """生成最终审查报告并收集错误统计"""
    try:
        if not global_state.reviewer:
            raise Exception("审查器未初始化")
        
        # 根据模式确定AI分析内容
        if global_state.mode == "direct":
            ai_review_content = "直接模式：跳过AI分析"
        else:
            ai_review_content = global_state.ai_review if global_state.ai_review else ""
        
        model_name = global_state.model_config.get_model_name() if global_state.model_config else "未知模型"
        
        global_state.log_step("GenerateReport", "RUNNING", f"生成最终审查报告（{model_name}）")
        global_state.send_status("正在生成审查报告...")
        
        # 生成报告
        review_doc = global_state.reviewer.generate_review_document(ai_review_content)
        global_state.final_report = review_doc
        
        # 收集错误统计
        statistics = collect_error_statistics()
        
        # 记录生成的报告文件路径
        report_path = review_doc.get('filename')
        if report_path:
            global_state.add_generated_report(report_path)
        
        # 立即生成最终错误统计文件
        json_output = {
            "error_statistics": {
                "rule_errors": statistics['rule_errors'],
                "ai_errors": statistics['ai_errors'], 
                "total_errors": statistics['total_errors'],
                "rule_error_details": statistics.get('rule_error_details', []),
                "ai_error_details": statistics.get('ai_error_details', []),
                "rule_severity_stats": statistics.get('rule_severity_stats', {
                    "high_severity": 0,
                    "medium_severity": 0,
                    "low_severity": 0,
                    "has_high_severity": False
                })
            },
            "mode": global_state.mode,
            "model_info": {
                "model_name": model_name,
                "supports_reasoning": global_state.model_config.supports_reasoning() if global_state.model_config else False,
                "is_streaming": global_state.model_config.is_streaming() if global_state.model_config else False
            },
            "consistency_status": "REMOVED",
            "generated_after_consistency_check": False,
            "generation_timestamp": datetime.now().isoformat(),
            "class_path": global_state.config.get("class_path", ""),
            "report_file": report_path,
            "note": "一致性检查功能已移除，使用统一模型配置管理"
        }
        
        # 保存到全局状态
        global_state.error_statistics_json = json_output
        global_state.error_statistics = statistics
        
        # 立即保存统计文件
        try:
            statistics_file_path = _save_error_statistics_to_file(json_output)
            if statistics_file_path:
                global_state.log_step("ErrorStatisticsFileGenerated", "SUCCESS", 
                                    f"错误统计文件已生成: {os.path.basename(statistics_file_path)}")
        except Exception as e:
            global_state.log_step("ErrorStatisticsFileGenerated", "ERROR", 
                                f"保存错误统计文件失败: {str(e)}")
        
        # 提取报告信息
        filename = review_doc.get('filename', 'unknown')
        rag_enabled = review_doc.get('rag_enabled', False)
        knowledge_base_size = review_doc.get('knowledge_base_size', 0)
        
        summary = f"报告已生成: {os.path.basename(filename)}"
        summary += f"\nRAG系统: {'启用' if rag_enabled else '未启用'}"
        summary += f"\n知识库规模: {knowledge_base_size} 个案例"
        summary += f"\n错误统计: 规则{statistics['rule_errors']}个, 总计{statistics['total_errors']}个"
        summary += f"\n使用模型: {model_name}"
        summary += f"\n使用内存JSON数据: 是"
        summary += f"\nASCET提取耗时: {global_state.data_extraction_time:.2f} 秒"
        summary += f"\n错误统计文件: 已生成"
        
        global_state.log_step("GenerateReport", "SUCCESS", summary)
        
        return f"SUCCESS: 报告生成成功\n{summary}"
        
    except Exception as e:
        error_msg = f"报告生成失败: {str(e)}"
        global_state.log_step("GenerateReport", "ERROR", error_msg)
        return f"ERROR: {error_msg}"

def get_execution_summary() -> str:
    """获取执行摘要和最终结果"""
    try:
        summary_parts = []
        summary_parts.append(f"代码审查执行完成（{global_state.mode}模式，统一模型配置管理）")
        summary_parts.append("=" * 60)
        
        # 进度统计
        progress = global_state.progress_tracker.get_progress_summary()
        summary_parts.append(f"执行进度:")
        summary_parts.append(f"   模式: {progress['mode']}")
        summary_parts.append(f"   完成步骤: {progress['completed_steps']}/{progress['total_steps']}")
        summary_parts.append(f"   进度: {progress['progress_percent']:.1f}%")
        summary_parts.append(f"   总耗时: {progress['total_execution_time']:.2f} 秒")
        
        # 模型配置信息
        if global_state.model_config:
            summary_parts.append(f"模型配置:")
            summary_parts.append(f"   模型名称: {global_state.model_config.get_model_name()}")
            summary_parts.append(f"   支持推理: {'是' if global_state.model_config.supports_reasoning() else '否'}")
            summary_parts.append(f"   流式输出: {'是' if global_state.model_config.is_streaming() else '否'}")
            summary_parts.append(f"   API类型: {global_state.model_config.get_api_type()}")
        
        # 性能优化提示
        if global_state.mode == "smart_direct":
            summary_parts.append(f"性能优化: 仅1次LLM调用（智能直接模式）")
        
        # ASCET数据提取统计
        if global_state.ascet_extraction_info:
            info = global_state.ascet_extraction_info
            summary_parts.append(f"ASCET数据提取:")
            summary_parts.append(f"   类路径: {info.get('class_path', '未知')}")
            summary_parts.append(f"   信号数量: {info.get('signals_count', 0)}")
            summary_parts.append(f"   导入源: {info.get('import_sources_count', 0)} 个")
            summary_parts.append(f"   提取耗时: {info.get('extraction_time', 0):.2f} 秒")
            summary_parts.append(f"   数据传输: 内存传输")
        
        # 基础统计
        if global_state.reviewer:
            summary_parts.append(f"代码分析:")
            summary_parts.append(f"   代码长度: {len(global_state.extracted_code or '')} 字符")
        
        # 错误统计摘要
        if hasattr(global_state, 'error_statistics') and global_state.error_statistics:
            stats = global_state.error_statistics
            summary_parts.append(f"错误统计:")
            summary_parts.append(f"   规则错误: {stats['rule_errors']} 个")
            summary_parts.append(f"   总错误: {stats['total_errors']} 个")
        else:
            issue_count = len(global_state.basic_issues)
            summary_parts.append(f"基础问题: {issue_count} 个")
        
        # RAG统计（智能模式）
        if global_state.mode == "smart_direct":
            if global_state.final_report and global_state.final_report.get('rag_enabled'):
                kb_size = global_state.final_report.get('knowledge_base_size', 0)
                summary_parts.append(f"RAG系统: 启用 ({kb_size} 个历史案例)")
            else:
                summary_parts.append("RAG系统: 未启用")
        
        # 报告文件状态
        if global_state.current_report_path:
            report_name = os.path.basename(global_state.current_report_path)
            summary_parts.append(f"报告文件: {report_name}")
        elif global_state.final_report:
            filename = global_state.final_report.get('filename', '未知')
            summary_parts.append(f"报告文件: {os.path.basename(filename)}")
        
        # Token统计信息
        try:
            token_summary = get_token_summary()
            if "暂无API调用" not in token_summary:
                summary_parts.append(f"\nToken使用统计:")
                if hasattr(global_token_tracker, 'call_count') and global_token_tracker.call_count > 0:
                    summary_parts.append(f"   API调用次数: {global_token_tracker.call_count} 次")
                    summary_parts.append(f"   总Token消耗: {global_token_tracker.total_tokens:,} tokens")
                    total_cost = sum(cat["cost"] for cat in global_token_tracker.api_categories.values())
                    summary_parts.append(f"   总成本: ${total_cost:.4f} USD")
        except Exception as e:
            summary_parts.append(f"\nToken统计获取失败: {str(e)}")
        
        # 执行日志摘要
        summary_parts.append("\n执行日志:")
        for log_entry in global_state.execution_log[-6:]:  # 显示最后6条日志
            step = log_entry['step']
            status = log_entry['status']
            summary_parts.append(f"  {step}: {status}")
        
        # 添加系统优化说明
        summary_parts.append(f"\n系统优化: 统一模型配置管理，支持多种AI模型")
        
        return "\n".join(summary_parts)
        
    except Exception as e:
        return f"摘要生成失败: {str(e)}"

# ==================== 直接模式执行函数 ====================

def run_direct_mode_review(config: Dict[str, Any]) -> Dict[str, Any]:
    """运行直接模式的代码审查（无LLM依赖）"""
    start_time = time.time()
    
    try:
        # 初始化全局状态和Token统计
        global global_state
        global_state = ReviewerState(mode="direct")
        global_state.config = config
        
        # 设置回调函数
        global_state.agent_callback = config.get('agent_callback')
        global_state.status_callback = config.get('status_callback')
        
        # 设置模型配置（直接模式不使用模型，但保持一致性）
        model_type = config.get("model_type", "gpt5-mini")
        try:
            model_config = create_model_config(model_type)
            global_state.set_model_config(model_config)
        except:
            # 直接模式可以容忍模型配置失败
            print("Warning: 模型配置设置失败，直接模式继续运行")
        
        # 重置Token统计为新的会话
        reset_token_tracker(f"direct_mode_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # 设置输出目录
        model_suffix = f"_{model_type}" if model_type else ""
        global_state.output_dir = config.get("output_dir", f"direct_reports{model_suffix}")
        global_state.report_output_dir = config.get("report_output_dir", global_state.output_dir)
        
        # 确保输出目录存在
        if global_state.output_dir:
            os.makedirs(global_state.output_dir, exist_ok=True)
        
        print("启动直接模式代码审查...")
        print("=" * 70)
        
        # 步骤1: 提取ASCET数据
        global_state.progress_tracker.start_step("ASCET数据提取")
        result = extract_ascet_data_tool("")
        if result.startswith("ERROR"):
            global_state.progress_tracker.complete_step("ERROR", "ASCET数据提取失败")
            raise Exception(f"ASCET数据提取失败: {result}")
        global_state.progress_tracker.complete_step("SUCCESS", "ASCET数据提取完成")
        
        # 步骤2: 初始化审查器
        global_state.progress_tracker.start_step("审查器初始化")
        result = initialize_reviewer_tool("")
        if result.startswith("ERROR"):
            global_state.progress_tracker.complete_step("ERROR", "审查器初始化失败")
            # 如果是代码提取失败，直接结束
            if "No code extracted" in result:
                global_state.progress_tracker.start_step("执行摘要")
                summary = get_execution_summary()
                global_state.progress_tracker.complete_step("SUCCESS", "分析结束")
                
                return {
                    "status": "terminated",
                    "reason": "No code extracted",
                    "execution_time": time.time() - start_time,
                    "progress": global_state.progress_tracker.get_progress_summary(),
                    "execution_log": global_state.execution_log,
                    "summary": summary,
                    "model_config": global_state.model_config.get_config() if global_state.model_config else None,
                    "token_statistics": get_token_summary()
                }
            else:
                raise Exception(f"审查器初始化失败: {result}")
        global_state.progress_tracker.complete_step("SUCCESS", "审查器初始化完成")
        
        # 步骤3: 基础规则检查
        global_state.progress_tracker.start_step("基础规则检查")
        result = run_basic_rule_checks()
        if result.startswith("ERROR"):
            global_state.progress_tracker.complete_step("ERROR", "基础检查失败")
            raise Exception(f"基础规则检查失败: {result}")
        global_state.progress_tracker.complete_step("SUCCESS", "基础检查完成")
        
        # 步骤4: 生成报告
        global_state.progress_tracker.start_step("报告生成")
        result = generate_report()
        if result.startswith("ERROR"):
            global_state.progress_tracker.complete_step("ERROR", "报告生成失败")
            raise Exception(f"报告生成失败: {result}")
        global_state.progress_tracker.complete_step("SUCCESS", "报告生成完成")
        
        # 步骤5: 错误统计输出
        global_state.progress_tracker.start_step("错误统计输出")
        result = get_error_statistics_tool("")
        if result.startswith("ERROR"):
            global_state.progress_tracker.complete_step("WARNING", "错误统计输出失败")
            print(f"警告: {result}")
        else:
            global_state.progress_tracker.complete_step("SUCCESS", "错误统计输出完成")
        
        # 步骤6: 执行摘要
        global_state.progress_tracker.start_step("执行摘要")
        summary = get_execution_summary()
        global_state.progress_tracker.complete_step("SUCCESS", "摘要生成完成")
        
        end_time = time.time()
        
        # 构建最终结果
        final_result = {
            "status": "success",
            "mode": "direct",
            "execution_time": end_time - start_time,
            "progress": global_state.progress_tracker.get_progress_summary(),
            "execution_log": global_state.execution_log,
            "basic_issues": global_state.basic_issues,
            "final_report": global_state.final_report,
            "current_report_path": global_state.current_report_path,
            "ascet_extraction_info": global_state.ascet_extraction_info,
            "data_collection_status": global_state.data_collection_status,
            "data_extraction_time": global_state.data_extraction_time,
            "json_data_size": len(str(global_state.json_data)) if global_state.json_data else 0,
            "error_statistics": global_state.error_statistics,
            "error_statistics_json": global_state.error_statistics_json,
            "model_config": global_state.model_config.get_config() if global_state.model_config else None,
            "summary": summary,
            "token_statistics": get_token_summary()
        }
        
        print("=" * 70)
        print(f"直接模式代码审查完成，总耗时: {end_time - start_time:.2f}秒")
        
        # 显示统计信息
        if global_state.ascet_extraction_info:
            info = global_state.ascet_extraction_info
            print(f"ASCET提取统计: {info.get('signals_count', 0)} 信号, {info.get('extraction_time', 0):.2f}秒")
        
        if global_state.error_statistics:
            stats = global_state.error_statistics
            print(f"错误统计: 规则{stats['rule_errors']}个, 总计{stats['total_errors']}个")
        
        if global_state.model_config:
            print(f"模型配置: {global_state.model_config.get_model_name()} (直接模式未使用)")
        
        # 显示Token统计
        print(f"\n{get_token_summary()}")
        
        return final_result
        
    except Exception as e:
        error_result = {
            "status": "error",
            "mode": "direct",
            "error_message": str(e),
            "execution_time": time.time() - start_time,
            "progress": global_state.progress_tracker.get_progress_summary() if global_state else {},
            "execution_log": global_state.execution_log if global_state else [],
            "ascet_extraction_info": global_state.ascet_extraction_info if global_state else {},
            "data_collection_status": global_state.data_collection_status if global_state else "failed",
            "error_statistics": global_state.error_statistics if global_state else None,
            "model_config": global_state.model_config.get_config() if global_state and global_state.model_config else None,
            "token_statistics": get_token_summary()
        }
        
        print(f"直接模式代码审查失败: {str(e)}")
        traceback.print_exc()
        
        return error_result

# ==================== 智能直接模式执行函数 ====================

def run_smart_direct_mode_review(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    智能直接模式：固定流程 + AI分析
    - 保留AI分析能力
    - 只在需要AI分析时调用一次LLM
    """
    start_time = time.time()
    
    try:
        # 初始化全局状态和Token统计
        global global_state
        global_state = ReviewerState(mode="smart_direct")
        global_state.config = config
        
        # 设置回调函数
        global_state.agent_callback = config.get('agent_callback')
        global_state.status_callback = config.get('status_callback')
        
        # 设置模型配置
        model_type = config.get("model_type", "gpt5-mini")
        try:
            model_config = create_model_config(model_type)
            global_state.set_model_config(model_config)

            if config.get("enable_ai_arbitration", True):
                initialize_arbitration_system(config, model_config)

        except ValueError as e:
            raise Exception(f"不支持的模型类型: {model_type}. {str(e)}")
        
        # 初始化Token统计
        reset_token_tracker(f"smart_direct_mode_{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # 设置输出目录
        global_state.output_dir = config.get("output_dir", f"smart_direct_reports_{model_type}")
        global_state.report_output_dir = config.get("report_output_dir", global_state.output_dir)
        
        # 确保输出目录存在
        if global_state.output_dir:
            os.makedirs(global_state.output_dir, exist_ok=True)
        
        print("启动智能直接模式代码审查...")
        print(f"使用模型: {model_config.get_model_name()}")
        print("=" * 70)
        
        # 步骤1: 提取ASCET数据
        global_state.progress_tracker.start_step("ASCET数据提取")
        result = extract_ascet_data_tool("")
        if result.startswith("ERROR"):
            global_state.progress_tracker.complete_step("ERROR", "ASCET数据提取失败")
            raise Exception(f"ASCET数据提取失败: {result}")
        global_state.progress_tracker.complete_step("SUCCESS", "ASCET数据提取完成")
        
        # 步骤2: 初始化审查器
        global_state.progress_tracker.start_step("审查器初始化")
        result = initialize_reviewer_tool("")
        if result.startswith("ERROR"):
            global_state.progress_tracker.complete_step("ERROR", "审查器初始化失败")
            # 如果是代码提取失败，直接结束
            if "No code extracted" in result:
                global_state.progress_tracker.start_step("执行摘要")
                summary = get_execution_summary()
                global_state.progress_tracker.complete_step("SUCCESS", "分析结束")
                
                return {
                    "status": "terminated",
                    "reason": "No code extracted",
                    "execution_time": time.time() - start_time,
                    "progress": global_state.progress_tracker.get_progress_summary(),
                    "execution_log": global_state.execution_log,
                    "summary": summary,
                    "model_config": global_state.model_config.get_config(),
                    "token_statistics": get_token_summary()
                }
            else:
                raise Exception(f"审查器初始化失败: {result}")
        global_state.progress_tracker.complete_step("SUCCESS", "审查器初始化完成")
        
        # 步骤3: 基础规则检查（本地操作）
        global_state.progress_tracker.start_step("基础规则检查")
        result = run_basic_rule_checks()
        if result.startswith("ERROR"):
            global_state.progress_tracker.complete_step("ERROR", "基础检查失败")
            raise Exception(f"基础规则检查失败: {result}")
        global_state.progress_tracker.complete_step("SUCCESS", "基础检查完成")
        
        # 步骤4: AI深度分析
        global_state.progress_tracker.start_step("AI深度分析")
        ai_result = run_smart_ai_analysis(config, model_config)
        if ai_result.startswith("ERROR"):
            global_state.progress_tracker.complete_step("ERROR", "AI分析失败")
            raise Exception(f"AI分析失败: {ai_result}")
        global_state.progress_tracker.complete_step("SUCCESS", "AI分析完成")
        
        # 步骤5: 生成报告（本地操作）
        global_state.progress_tracker.start_step("报告生成")
        result = generate_report()
        if result.startswith("ERROR"):
            global_state.progress_tracker.complete_step("ERROR", "报告生成失败")
            raise Exception(f"报告生成失败: {result}")
        global_state.progress_tracker.complete_step("SUCCESS", "报告生成完成")
        
        # 步骤6: 错误统计输出（本地操作）
        global_state.progress_tracker.start_step("错误统计输出")
        result = get_error_statistics_tool("")
        if result.startswith("ERROR"):
            global_state.progress_tracker.complete_step("WARNING", "错误统计输出失败")
            print(f"警告: {result}")
        else:
            global_state.progress_tracker.complete_step("SUCCESS", "错误统计输出完成")
        
        # 步骤7: 执行摘要（本地操作）
        global_state.progress_tracker.start_step("执行摘要")
        summary = get_execution_summary()
        global_state.progress_tracker.complete_step("SUCCESS", "摘要生成完成")
        
        end_time = time.time()
        
        # 构建最终结果
        final_result = {
            "status": "success",
            "mode": "smart_direct",
            "execution_time": end_time - start_time,
            "progress": global_state.progress_tracker.get_progress_summary(),
            "execution_log": global_state.execution_log,
            "basic_issues": global_state.basic_issues,
            "ai_review": global_state.ai_review,
            "final_report": global_state.final_report,
            "current_report_path": global_state.current_report_path,
            "ascet_extraction_info": global_state.ascet_extraction_info,
            "data_collection_status": global_state.data_collection_status,
            "data_extraction_time": global_state.data_extraction_time,
            "json_data_size": len(str(global_state.json_data)) if global_state.json_data else 0,
            "error_statistics": global_state.error_statistics,
            "error_statistics_json": global_state.error_statistics_json,
            "model_config": global_state.model_config.get_config(),
            "model_info": {
                "model_type": model_type,
                "model_name": model_config.get_model_name(),
                "supports_reasoning": model_config.supports_reasoning(),
                "is_streaming": model_config.is_streaming(),
                "api_type": model_config.get_api_type(),
                "llm_calls": 1  # 只调用一次LLM
            },
            "summary": summary,
            "token_statistics": get_token_summary(),
            "optimization_note": "使用智能直接模式，避免多轮交互开销"
        }
        
        print("=" * 70)
        print(f"智能直接模式代码审查完成，总耗时: {end_time - start_time:.2f}秒")
        
        # 显示优化效果
        print(f"性能优化: 仅1次LLM调用（高效模式）")
        
        # 显示ASCET提取统计
        if global_state.ascet_extraction_info:
            info = global_state.ascet_extraction_info
            print(f"ASCET提取统计: {info.get('signals_count', 0)} 信号, {info.get('extraction_time', 0):.2f}秒")
        
        # 显示错误统计
        if global_state.error_statistics:
            stats = global_state.error_statistics
            print(f"错误统计: 规则{stats['rule_errors']}个, 总计{stats['total_errors']}个")
        
        # 显示模型配置信息
        print(f"使用模型: {model_config.get_model_name()}")
        print(f"系统优化: 智能直接模式，最小LLM开销")
        
        # 显示Token统计摘要
        print(f"\n{get_token_summary()}")
        
        return final_result
        
    except Exception as e:
        error_result = {
            "status": "error",
            "mode": "smart_direct",
            "error_message": str(e),
            "execution_time": time.time() - start_time,
            "progress": global_state.progress_tracker.get_progress_summary() if global_state else {},
            "execution_log": global_state.execution_log if global_state else [],
            "ascet_extraction_info": global_state.ascet_extraction_info if global_state else {},
            "data_collection_status": global_state.data_collection_status if global_state else "failed",
            "error_statistics": global_state.error_statistics if global_state else None,
            "model_config": global_state.model_config.get_config() if global_state and global_state.model_config else None,
            "token_statistics": get_token_summary()
        }
        
        print(f"智能直接模式代码审查失败: {str(e)}")
        traceback.print_exc()
        
        return error_result

# ==================== 统一入口函数 ====================

def run_integrated_code_review(config: Dict[str, Any], mode: str = "smart_direct") -> Dict[str, Any]:
    """
    运行集成代码审查系统的统一入口（优化版）
    
    Args:
        config: 配置字典，包含所有必要的参数
        mode: 运行模式
            - "direct": 直接模式（无AI分析）
            - "smart_direct": 智能直接模式（固定流程+AI分析，推荐）
    
    Returns:
        Dict[str, Any]: 执行结果字典
    """
    # Diagram queue items use a dedicated AI flow (separate from class review pipeline).
    if DiagramQueueDummyError.is_diagram_item(config.get("class_path")):
        if DIAGRAM_FLOW_AVAILABLE:
            print("检测到diagram队列项，进入diagram专用AI评审流")
            return DiagramAIReviewFlow(config=config, mode=mode).run()

        print("检测到diagram队列项，但diagram流不可用，返回dummy空错误结果")
        return DiagramQueueDummyError.build_result(config, mode)

    if mode not in ["direct", "smart_direct"]:
        raise ValueError("模式必须是 'direct' 或 'smart_direct'")
    
    # 验证模型配置
    model_type = config.get("model_type", "gpt5-mini")
    try:
        model_config = create_model_config(model_type)
        print(f"使用模型配置: {model_config.get_model_name()}")
    except ValueError as e:
        print(f"模型配置错误: {e}")
        print(f"支持的模型: {list(ModelConfig.get_supported_models())}")
        raise
    
    print(f"=" * 80)
    print(f"代码审查系统启动 - {mode.upper().replace('_', ' ')}模式")
    print(f"模型: {model_config.get_model_name()} | 推理: {'是' if model_config.supports_reasoning() else '否'} | 流式: {'是' if model_config.is_streaming() else '否'}")
    
    # 显示模式说明
    if mode == "direct":
        print("直接模式: 无需LLM，仅执行基础检查和报告生成")
    elif mode == "smart_direct":
        print("智能直接模式: 固定流程 + AI分析，仅1次LLM调用（推荐）")
    
    print(f"=" * 80)
    
    if mode == "direct":
        return run_direct_mode_review(config)
    else:  # smart_direct mode
        return run_smart_direct_mode_review(config)

# ==================== UI适配函数 ====================

def run_integrated_code_review_with_logging(config: Dict[str, Any], mode: str = "smart_direct") -> Dict[str, Any]:
    """
    带详细日志的代码审查入口函数，用于UI集成
   
    
    Args:
        config: 配置字典，包含所有必要的参数，包含回调函数
        mode: 运行模式
            - "direct": 直接模式（无AI分析）
            - "smart_direct": 智能直接模式（固定流程+AI分析，）
            - "agent": 为了兼容UI，映射到smart_direct模式
    
    Returns:
        Dict[str, Any]: 执行结果字典
    """
    # 兼容旧的"agent"模式名称
    if mode == "agent":
        mode = "smart_direct"
    
    return run_integrated_code_review(config, mode)

# ==================== 配置管理函数 ====================

def create_default_config(model_type: str = "gpt5-mini") -> Dict[str, Any]:
    """创建默认配置"""
    
    config = {
        "class_path": r"\Customer\CC_CN\Package\ECAS_ElectronicallyControlledAirSpring\private\ECAS_HC_EachCorner_Trigger",
        "model_type": model_type,
        "api_key": "sk-NhxJsm3yenfoO79F22E25a3364354cC8875f135dEc84E50b",
        "api_base_url": "http://10.161.112.104:3000/v1",
        "embedding_api_key": "sk-yAYNtyvvu1JUE8zV0f13A3DdDeC14f6aAf442a81E6C58333",
        "knowledge_base_path": r"C:\ZJR\AscetTool\RAG\code_analysis_knowledge",
        "ascet_version": "6.1.4",
        "diagram_name": "Main",
        "method_name": "calc",
        "output_dir": f"{model_type}_reports_internal",
        "report_output_dir": None,
        "enable_ai_arbitration": True,           # 启用AI错误仲裁
        "arbitration_strategy": "conservative",  # 仲裁策略
      
        "proxy_config": {
            "enabled": False
        }
    }
    
    return config

# ==================== 主函数 ====================

def main():
    """主函数 - 优化版代码审查系统"""
    
    print("=" * 80)
    print("集成ASCET数据提取的代码审查系统（性能优化版）")
    print("支持两种模式:")
    print("  - direct: 直接模式（无AI分析）")
    print("  - smart_direct: 智能直接模式（推荐，固定流程+AI，仅1次LLM调用）")
    print(f"支持的AI模型: {', '.join(ModelConfig.get_supported_models())}")
    print("=" * 80)
    
    # 检查命令行参数确定模式和模型
    mode = "smart_direct"  # 默认智能直接模式
    model_type = "gpt5-mini"  # 默认GPT-5 mini
    
    if "--direct-mode" in sys.argv:
        mode = "direct"
    elif "--smart-mode" in sys.argv or "--smart-direct-mode" in sys.argv:
        mode = "smart_direct"
    
    # 检查模型参数
    for i, arg in enumerate(sys.argv):
        if arg.startswith("--model="):
            model_type = arg.split("=", 1)[1]
            break
        elif arg == "--model" and i + 1 < len(sys.argv):
            model_type = sys.argv[i + 1]
            break
    
    try:
        # 创建配置
        config = create_default_config(model_type)
        
        print(f"当前运行模式: {mode.upper().replace('_', ' ')}")
        print(f"使用模型: {model_type}")
        print(f"输出目录: {config['output_dir']}")
        
     
        
        print("-" * 40)
        
        # 运行审查
        result = run_integrated_code_review(config, mode=mode)
        
        if result["status"] == "success":
            print("\n" + "="*80)
            print(f"代码审查系统执行成功! ({mode.replace('_', ' ')}模式)")
            print("="*80)
            
            print(f"执行统计:")
            print(f"   运行模式: {result['mode'].upper().replace('_', ' ')}")
            print(f"   总耗时: {result['execution_time']:.2f} 秒")
            
            # 显示性能优化信息
            if result.get('model_info') and 'llm_calls' in result['model_info']:
                llm_calls = result['model_info']['llm_calls']
                print(f"   LLM调用次数: {llm_calls} 次")
                if mode == "smart_direct":
                    print(f"   性能优化: 高效模式，单次LLM调用")
            
            # 显示模型信息
            if result.get('model_info'):
                model_info = result['model_info']
                print(f"模型配置:")
                print(f"   模型名称: {model_info['model_name']}")
                print(f"   支持推理: {'是' if model_info['supports_reasoning'] else '否'}")
                print(f"   流式输出: {'是' if model_info['is_streaming'] else '否'}")
                print(f"   API类型: {model_info['api_type']}")
            
            # 进度统计
            if result.get('progress'):
                progress = result['progress']
                print(f"执行进度:")
                print(f"   完成步骤: {progress['completed_steps']}/{progress['total_steps']}")
                print(f"   进度: {progress['progress_percent']:.1f}%")
            
            # 显示ASCET数据提取统计
            if result.get('ascet_extraction_info'):
                info = result['ascet_extraction_info']
                print(f"ASCET数据提取:")
                print(f"   信号数量: {info.get('signals_count', 0)} 个")
                print(f"   导入源: {info.get('import_sources_count', 0)} 个")
                print(f"   提取耗时: {info.get('extraction_time', 0):.2f} 秒")
                print(f"   数据传输: 内存传输")
                print(f"   JSON大小: {result.get('json_data_size', 0)} 字符")
            
            print(f"代码审查:")
            print(f"   基础问题: {len(result.get('basic_issues', []))} 个")
            
            # 显示错误统计信息
            if result.get('error_statistics'):
                stats = result['error_statistics']
                print(f"错误统计:")
                print(f"   规则错误: {stats['rule_errors']} 个")
                print(f"   总错误: {stats['total_errors']} 个")
                
                # 显示JSON格式统计
                if result.get('error_statistics_json'):
                    print(f"   JSON统计: 已生成")
                else:
                    print(f"   JSON统计: 未生成")
            
            # 显示当前报告状态
            current_report = result.get('current_report_path')
            if current_report:
                report_name = os.path.basename(current_report)
                print(f"最终报告: {report_name}")
            
            # 智能模式显示额外信息
            if mode == "smart_direct":
                print(f"\n智能直接模式优化:")
                print(f"   固定流程执行，高效AI分析")
                print(f"   保留AI分析能力，性能显著提升")
            
            # 显示Token统计信息
            if result.get('token_statistics'):
                print(f"\n{result['token_statistics']}")
            
        elif result["status"] == "terminated":
            print(f"\n代码审查提前终止: {result.get('reason', '未知原因')}")
            print(f"执行耗时: {result['execution_time']:.2f} 秒")
            if result.get('summary'):
                print(f"\n执行摘要:\n{result['summary']}")
            if result.get('token_statistics'):
                print(f"\n{result['token_statistics']}")
        else:
            print(f"\n执行失败: {result.get('error_message', '未知错误')}")
            
            # 即使失败也显示ASCET提取信息
            if result.get('ascet_extraction_info'):
                info = result['ascet_extraction_info']
                print(f"ASCET提取状态: {result.get('data_collection_status', '未知')}")
            
            # 显示模型配置信息
            if result.get('model_config'):
                try:
                    model_config = ModelConfig("temp")
                    model_config.config = result['model_config']
                    print(f"使用模型: {model_config.get_model_name()}")
                except:
                    pass
            
            # 即使失败也显示Token统计
            if result.get('token_statistics'):
                print(f"\n{result['token_statistics']}")
            
            return 1
    
    except ValueError as e:
        print(f"配置错误: {str(e)}")
        return 1
    except Exception as e:
        print(f"系统异常: {str(e)}")
        traceback.print_exc()
        
        # 系统异常时也显示Token统计
        try:
            print(f"\n{get_token_summary()}")
        except:
            pass
        
        return 1
    
    print(f"\n代码审查系统运行完成 ({mode.replace('_', ' ')}模式，{model_type}模型)")
    return 0

if __name__ == "__main__":
    # 显示使用说明
    if "--help" in sys.argv or "-h" in sys.argv:
        
        sys.exit(0)
    
    exit_code = main()
    sys.exit(exit_code)