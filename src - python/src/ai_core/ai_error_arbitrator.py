#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Error Arbitrator Module
=========================

LLM错误仲裁模块，用于减少AI分析中的误报。
通过双模型交叉验证来提高错误检测的准确性。

版本: 1.0
"""

import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


class AIErrorArbitrator:
    """AI错误仲裁器 - 用于减少AI错误误报"""
    
    def __init__(self, primary_model_config=None, fallback_model_config=None, strategy="conservative"):
        self.primary_model_config = primary_model_config
        self.fallback_model_config = fallback_model_config
        self.arbitration_enabled = True
        self.arbitration_log = []
        self.current_strategy = strategy
        
        # 仲裁策略配置
        self.strategies = {
            "conservative": self._conservative_strategy,    # 两个模型都报错才算错误
            "majority": self._majority_strategy,           # 暂不实现，需要3个模型
            "severity_based": self._severity_based_strategy # 基于严重程度的仲裁
        }
        
        # 固定的错误类型（基于你的JSON模板）
        self.fixed_error_types = [
            "位置变量映射错误",
            "返回值变量名称映射错误", 
            "参数映射名称一致性错误"
        ]
        
        # 严重程度级别映射
        self.severity_levels = {
            "low": 1, "l": 1, "info": 1, "minor": 1, "低": 1,
            "medium": 2, "med": 2, "m": 2, "warning": 2, "warn": 2, "中": 2,
            "high": 3, "h": 3, "error": 3, "critical": 3, "高": 3
        }
    
    def log_arbitration_step(self, step: str, details: str = ""):
        """记录仲裁步骤"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "details": details
        }
        self.arbitration_log.append(log_entry)
        print(f"[Arbitration] {step}: {details}")
    
    def arbitrate_errors(self, primary_errors: List[Dict], fallback_errors: List[Dict]) -> List[Dict]:
        """执行错误仲裁的主入口方法"""
        self.log_arbitration_step("STARTED", 
            f"开始AI错误仲裁: 主模型{len(primary_errors)}个错误, 备用模型{len(fallback_errors)}个错误")
        
        if not self.arbitration_enabled:
            self.log_arbitration_step("DISABLED", "仲裁功能已禁用，返回主模型结果")
            return primary_errors
        
        # 使用当前策略进行仲裁
        strategy_func = self.strategies.get(self.current_strategy, self._conservative_strategy)
        confirmed_errors = strategy_func(primary_errors, fallback_errors)
        
        self.log_arbitration_step("COMPLETED", 
            f"仲裁完成: 最终确认{len(confirmed_errors)}个真实错误")
        
        return confirmed_errors
    
    def _conservative_strategy(self, primary_errors: List[Dict], fallback_errors: List[Dict]) -> List[Dict]:
        """保守策略：只有两个模型都报告的错误才认为是真实错误"""
        confirmed_errors = []
        
        self.log_arbitration_step("STRATEGY", "使用保守策略进行仲裁")
        
        for p_error in primary_errors:
            p_type = p_error.get('type', '').lower().strip()
            
            # 查找fallback中是否有相同类型的错误
            for f_error in fallback_errors:
                f_type = f_error.get('type', '').lower().strip()
                
                if self._error_types_match(p_type, f_type):
                    # 合并两个错误的信息
                    confirmed_error = {
                        "type": p_error.get('type'),
                        "message": f"Confirmed by dual analysis: {p_error.get('message', '')}",
                        "severity": self._merge_severity(p_error.get('severity'), f_error.get('severity')),
                        "primary_analysis": p_error,
                        "fallback_analysis": f_error,
                        "arbitration_result": "CONFIRMED",
                        "arbitration_method": "conservative"
                    }
                    confirmed_errors.append(confirmed_error)
                    self.log_arbitration_step("CONFIRMED", 
                        f"错误类型 '{p_error.get('type')}' 被两个模型确认")
                    break
            else:
                # 没有找到匹配的错误，记录为可能的误报
                self.log_arbitration_step("DISPUTED", 
                    f"错误类型 '{p_error.get('type')}' 仅被主模型检测到 - 视为潜在误报")
        
        return confirmed_errors
    
    def _severity_based_strategy(self, primary_errors: List[Dict], fallback_errors: List[Dict]) -> List[Dict]:
        """基于严重程度的仲裁：高严重程度的错误即使只有一个模型报告也保留"""
        confirmed_errors = []
        
        self.log_arbitration_step("STRATEGY", "使用基于严重程度的仲裁策略")
        
        # 首先执行保守策略
        conservative_errors = self._conservative_strategy(primary_errors, fallback_errors)
        confirmed_errors.extend(conservative_errors)
        
        # 然后检查只有一个模型报告但严重程度高的错误
        all_errors = primary_errors + fallback_errors
        for error in all_errors:
            severity = error.get('severity', '').lower()
            if severity in ['high', 'critical', 'error', '高'] and not self._already_confirmed(error, confirmed_errors):
                error_copy = error.copy()
                error_copy.update({
                    "arbitration_result": "HIGH_SEVERITY_OVERRIDE",
                    "arbitration_method": "severity_based",
                    "message": f"High severity override: {error.get('message', '')}"
                })
                confirmed_errors.append(error_copy)
                self.log_arbitration_step("HIGH_SEVERITY", 
                    f"高严重程度错误 '{error.get('type')}' 保留（单模型检测）")
        
        return confirmed_errors
    
    def _majority_strategy(self, primary_errors: List[Dict], fallback_errors: List[Dict]) -> List[Dict]:
        """多数投票策略：需要3个或更多模型，暂不实现"""
        self.log_arbitration_step("UNSUPPORTED", "多数投票策略需要3个或更多模型，降级为保守策略")
        return self._conservative_strategy(primary_errors, fallback_errors)
    
    def _error_types_match(self, type1: str, type2: str) -> bool:
        """判断两个错误类型是否匹配（基于固定的错误类型）"""
        if not type1 or not type2:
            return False
        
        type1 = type1.strip()
        type2 = type2.strip()
        
        # 完全匹配（固定的三种错误类型）
        return type1 == type2
    
    def _merge_severity(self, sev1: str, sev2: str) -> str:
        """合并两个严重程度，取较高的"""
        level1 = self.severity_levels.get(str(sev1).lower().strip(), 2)  # 默认medium
        level2 = self.severity_levels.get(str(sev2).lower().strip(), 2)
        
        max_level = max(level1, level2)
        
        # 返回标准化的严重程度名称
        if max_level == 3:
            return "high"
        elif max_level == 2:
            return "medium"
        else:
            return "low"
    
    def _already_confirmed(self, error: Dict, confirmed_list: List[Dict]) -> bool:
        """检查错误是否已经在确认列表中"""
        error_type = error.get('type', '').lower().strip()
        for confirmed in confirmed_list:
            if self._error_types_match(error_type, confirmed.get('type', '')):
                return True
        return False
    
    def get_arbitration_summary(self) -> Dict[str, Any]:
        """获取仲裁摘要信息"""
        return {
            "enabled": self.arbitration_enabled,
            "strategy": self.current_strategy,
            "primary_model": self.primary_model_config.get_model_name() if self.primary_model_config else "Unknown",
            "fallback_model": self.fallback_model_config.get_model_name() if self.fallback_model_config else "Unknown",
            "log_entries": len(self.arbitration_log),
            "arbitration_log": self.arbitration_log
        }
    
    def reset_log(self):
        """重置仲裁日志"""
        self.arbitration_log = []
    
    def set_strategy(self, strategy: str):
        """设置仲裁策略"""
        if strategy in self.strategies:
            self.current_strategy = strategy
            self.log_arbitration_step("STRATEGY_CHANGED", f"仲裁策略更改为: {strategy}")
        else:
            self.log_arbitration_step("STRATEGY_ERROR", f"未知仲裁策略: {strategy}")


class AIErrorExtractor:
    """AI错误提取器 - 从AI审查结果中提取错误信息"""
    
    @staticmethod
    def extract_errors_from_text(ai_review_text: str) -> List[Dict[str, Any]]:
        """从AI审查文本中提取错误信息"""
        ai_error_details = []
        
        if not ai_review_text:
            return ai_error_details
        
        try:
            # 方法1: 查找JSON代码块
            json_pattern = r'```json\s*(\{.*?\})\s*```'
            json_matches = re.findall(json_pattern, ai_review_text, re.DOTALL | re.IGNORECASE)
            
            if json_matches:
                for json_str in json_matches:
                    ai_error_details.extend(AIErrorExtractor._parse_json_errors(json_str))
            
            # 方法2: 查找裸露的JSON对象
            if not ai_error_details:
                json_objects = AIErrorExtractor._extract_json_objects(ai_review_text)
                for json_obj in json_objects:
                    ai_error_details.extend(AIErrorExtractor._parse_json_errors(json_obj))
            
           
        except Exception as e:
            print(f"AI错误提取异常: {str(e)}")
        
        return ai_error_details
    
    @staticmethod
    def _parse_json_errors(json_text: str) -> List[Dict[str, Any]]:
        """解析JSON字符串中的错误信息"""
        errors = []
        
        try:
            # 尝试解析单个JSON对象
            data = json.loads(json_text)
            errors.extend(AIErrorExtractor._process_json_data(data))
        except json.JSONDecodeError:
            # 尝试分割多个JSON对象
            json_objects = AIErrorExtractor._split_json_objects(json_text)
            for obj_text in json_objects:
                try:
                    data = json.loads(obj_text.strip())
                    errors.extend(AIErrorExtractor._process_json_data(data))
                except json.JSONDecodeError:
                    continue
        
        return errors
    
   
    
    @staticmethod
    def _process_json_data(data: Dict) -> List[Dict[str, Any]]:
        """处理JSON数据对象，提取错误信息"""
        errors = []
        
        # 检查是否是扁平结构（直接包含"错误类型"）
        if "错误类型" in data:
            error = AIErrorExtractor._process_flat_json_structure(data)
            if error:
                errors.append(error)
        
        # 检查是否是嵌套结构
        else:
            for category, error_data in data.items():
                if isinstance(error_data, dict) and "错误类型" in error_data:
                    error = AIErrorExtractor._process_flat_json_structure(error_data, category)
                    if error:
                        errors.append(error)
        
        return errors
    
    @staticmethod
    def _process_flat_json_structure(error_data: Dict, category: str = None) -> Optional[Dict[str, Any]]:
        """处理扁平的JSON结构，提取错误信息（适配固定JSON格式）"""
        # 获取状态信息
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
        
        # 检查是否有缺陷状态（基于你的固定格式）
        has_defect = "Defect" in status_list
        has_no_defect = "No Defect" in status_list
        
        # 只有明确的Defect状态才认为是错误
        if has_defect and not has_no_defect:
            # 确定错误类型
            if error_types and isinstance(error_types, list):
                error_type = error_types[0]
            else:
                error_type = category or "未知AI错误"
            
            # 根据错误类型提取特定字段
            additional_info = {}
            
            if error_type == "位置变量映射错误":
                # 查找代码行号相关字段
                for key, value in error_data.items():
                    if key.startswith("代码行号") and value:
                        additional_info["code_line_info"] = f"{key}: {value}"
            
            elif error_type == "返回值变量名称映射错误":
                methods_issue = error_data.get("Methods问题", "")
                if methods_issue:
                    additional_info["methods_issue"] = methods_issue
            
            elif error_type == "参数映射名称一致性错误":
                mapping_issue = error_data.get("映射问题", "")
                involved_mapping = error_data.get("涉及映射", "")
                if mapping_issue:
                    additional_info["mapping_issue"] = mapping_issue
                if involved_mapping:
                    additional_info["involved_mapping"] = involved_mapping
            
            # 根据错误类型确定严重程度
            if error_type in ["位置变量映射错误", "返回值变量名称映射错误"]:
                severity = "medium"
            elif error_type == "参数映射名称一致性错误":
                severity = "medium"
            else:
                severity = "medium"
            
            error_detail = {
                "type": error_type,
                "message": reason or f"检测到{error_type}",
                "severity": severity,
                "raw_data": error_data,
                **additional_info  # 添加特定字段信息
            }
            
            return error_detail
        
        # 如果状态是"No Defect"或者状态不明确，则不认为是错误
        return None
    
    @staticmethod
    def _extract_json_objects(text: str) -> List[str]:
        """从文本中提取JSON对象"""
        # 查找看起来像JSON的内容
        patterns = [
            r'\{[^{}]*"错误类型"[^{}]*\}',
            r'\{[^{}]*"状态"[^{}]*\}',
        ]
        
        json_candidates = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            json_candidates.extend(matches)
        
        return list(set(json_candidates))
    
    @staticmethod
    def _split_json_objects(text: str) -> List[str]:
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
                    
                    if brace_count == 0 and current_obj.strip():
                        json_objects.append(current_obj.strip())
                        current_obj = ""
        
        if current_obj.strip():
            json_objects.append(current_obj.strip())
        
        return json_objects
    


class ModelConfigFactory:
    """模型配置工厂 - 创建仲裁模型配置"""
    
    
    ARBITRATION_PAIRS = {
        "gpt-5-mini": "gpt5-mini",
        "DeepSeek-r1-0528-fp16-671b": "gpt5-mini", 
        "gpt-oss-120b": "gpt5-mini"
    }
    
    @classmethod
    def create_arbitration_configs(cls, primary_model: str, create_model_config_func):
        """创建用于仲裁的主模型和备用模型配置"""
        fallback_model = cls.ARBITRATION_PAIRS.get(primary_model, "gpt5-mini")
        
        try:
            primary_config = create_model_config_func(primary_model)
            fallback_config = create_model_config_func(fallback_model)
            
            return primary_config, fallback_config
        except Exception as e:
            print(f"Warning: 创建备用模型配置失败: {e}")
            # 如果无法创建备用配置，使用同一个模型
            primary_config = create_model_config_func(primary_model)
            return primary_config, primary_config


# ==================== 便捷函数接口 ====================

def create_arbitrator(primary_model_config=None, fallback_model_config=None, strategy="conservative") -> AIErrorArbitrator:
    """创建AI错误仲裁器的便捷函数"""
    return AIErrorArbitrator(primary_model_config, fallback_model_config, strategy)


def arbitrate_ai_errors(primary_errors: List[Dict], fallback_errors: List[Dict], 
                       strategy: str = "conservative") -> List[Dict]:
    """执行AI错误仲裁的便捷函数"""
    arbitrator = AIErrorArbitrator(strategy=strategy)
    return arbitrator.arbitrate_errors(primary_errors, fallback_errors)


def extract_ai_errors(ai_review_text: str) -> List[Dict[str, Any]]:
    """从AI审查文本中提取错误信息的便捷函数"""
    return AIErrorExtractor.extract_errors_from_text(ai_review_text)




