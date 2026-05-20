# ==================== 统一Token统计系统 ====================
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class UnifiedTokenTracker:
    """统一Token跟踪器 - 支持多种API和详细统计"""
    
    def __init__(self, session_name: str = None):
        # 会话信息
        self.session_name = session_name or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_start_time = time.time()
        
        # 总体统计
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.call_count = 0
        
        # 分类统计
        self.api_categories = {
            "RAG分析": {"prompt": 0, "completion": 0, "total": 0, "calls": 0, "cost": 0.0},
            "一致性检查": {"prompt": 0, "completion": 0, "total": 0, "calls": 0, "cost": 0.0},
            "向量生成": {"prompt": 0, "completion": 0, "total": 0, "calls": 0, "cost": 0.0},
            "ASCET数据提取": {"prompt": 0, "completion": 0, "total": 0, "calls": 0, "cost": 0.0},
            "基础分析": {"prompt": 0, "completion": 0, "total": 0, "calls": 0, "cost": 0.0},
            "其他API调用": {"prompt": 0, "completion": 0, "total": 0, "calls": 0, "cost": 0.0}
        }
        
        # 详细调用记录
        self.detailed_calls = []
        
        # 成本配置
        self.cost_config = {
            "deepseek_per_token": 0.000014,  # DeepSeek定价
            "embedding_per_token": 0.00002,  # 向量API定价
            "budget_warning": 1.0,  # 预算警告阈值（美元）
            "budget_limit": 5.0     # 预算限制（美元）
        }
        
        # 日志配置
        self.log_file = f"token_logs/token_log_{self.session_name}.json"
        self.enable_logging = True
        self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """确保日志目录存在"""
        try:
            os.makedirs("token_logs", exist_ok=True)
        except:
            self.enable_logging = False
    
    def record_from_response(self, response_json: Dict, api_name: str, 
                            api_type: str = "deepseek", context: str = ""):
        """从API响应中记录Token使用"""
        if not response_json:
            print(f"⚠️ Token统计: {api_name} - 无有效响应数据")
            return
        
        # 提取usage信息
        usage = response_json.get("usage", {})
        if not usage:
            print(f"⚠️ Token统计: {api_name} - 响应中未包含usage信息")
            return
            
        self.record_usage(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            api_name=api_name,
            api_type=api_type,
            context=context
        )
    
    def record_usage(self, prompt_tokens: int, completion_tokens: int, 
                    total_tokens: int = None, api_name: str = "Unknown API",
                    api_type: str = "deepseek", context: str = ""):
        """直接记录Token使用量"""
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens
        
        if total_tokens == 0:
            print(f"⚠️ Token统计: {api_name} - Token数量为0")
            return
        
        # 计算成本
        cost = self._calculate_cost(total_tokens, api_type)
        
        # 更新总体统计
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_tokens += total_tokens
        self.call_count += 1
        
        # 更新分类统计
        category = self._categorize_api_call(api_name)
        if category in self.api_categories:
            cat_stats = self.api_categories[category]
            cat_stats["prompt"] += prompt_tokens
            cat_stats["completion"] += completion_tokens
            cat_stats["total"] += total_tokens
            cat_stats["calls"] += 1
            cat_stats["cost"] += cost
        
        # 记录详细信息
        call_detail = {
            "call_number": self.call_count,
            "timestamp": datetime.now().isoformat(),
            "api_name": api_name,
            "api_type": api_type,
            "category": category,
            "context": context,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
            "session_time": time.time() - self.session_start_time
        }
        self.detailed_calls.append(call_detail)
        
        # 实时显示
        self._display_real_time_stats(api_name, prompt_tokens, completion_tokens, total_tokens, cost)
        
        # 检查预算
        self._check_budget_warnings()
        
        # 保存日志
        if self.enable_logging:
            self._save_to_log()
    
    def _calculate_cost(self, total_tokens: int, api_type: str) -> float:
        """计算API调用成本"""
        if api_type == "deepseek":
            return total_tokens * self.cost_config["deepseek_per_token"]
        elif api_type == "embedding":
            return total_tokens * self.cost_config["embedding_per_token"]
        else:
            return total_tokens * self.cost_config["deepseek_per_token"]
    
    def _categorize_api_call(self, api_name: str) -> str:
        """根据API名称分类"""
        api_name_lower = api_name.lower()
        
        if "rag" in api_name_lower or "增强分析" in api_name_lower:
            return "RAG增强分析"
        elif "一致性" in api_name_lower or "consistency" in api_name_lower:
            return "一致性检查"
        elif "向量" in api_name_lower or "embedding" in api_name_lower:
            return "向量生成"
        elif "ascet" in api_name_lower or "数据提取" in api_name_lower:
            return "ASCET数据提取"
        elif "基础" in api_name_lower or "basic" in api_name_lower:
            return "基础分析"
        else:
            return "其他API调用"
    
    def _display_real_time_stats(self, api_name: str, prompt: int, completion: int, total: int, cost: float):
        """显示实时统计"""
        print(f"🔢 Token消耗 ({api_name}): 输入{prompt:,}, 输出{completion:,}, 总计{total:,}, 成本${cost:.4f}")
        
        # 累计信息
        total_cost = sum(cat["cost"] for cat in self.api_categories.values())
        print(f"📊 累计: 第{self.call_count}次调用, 总Token{self.total_tokens:,}, 总成本${total_cost:.4f}")
    
    def _check_budget_warnings(self):
        """检查预算警告"""
        total_cost = sum(cat["cost"] for cat in self.api_categories.values())
        
        if total_cost >= self.cost_config["budget_limit"]:
            print(f"🚨 预算超限: 成本${total_cost:.4f}已超过限制${self.cost_config['budget_limit']:.2f}!")
        elif total_cost >= self.cost_config["budget_warning"]:
            print(f"⚠️ 预算警告: 成本${total_cost:.4f}接近预算${self.cost_config['budget_warning']:.2f}")
    
    def _save_to_log(self):
        """保存到日志文件"""
        if not self.enable_logging:
            return
            
        try:
            log_data = {
                "session_info": {
                    "session_name": self.session_name,
                    "start_time": datetime.fromtimestamp(self.session_start_time).isoformat(),
                    "last_update": datetime.now().isoformat(),
                    "duration_seconds": time.time() - self.session_start_time
                },
                "summary": {
                    "total_calls": self.call_count,
                    "total_prompt_tokens": self.total_prompt_tokens,
                    "total_completion_tokens": self.total_completion_tokens,
                    "total_tokens": self.total_tokens,
                    "total_cost": sum(cat["cost"] for cat in self.api_categories.values())
                },
                "categories": self.api_categories,
                "recent_calls": self.detailed_calls[-20:]  # 最近20次调用
            }
            
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"⚠️ 保存Token日志失败: {e}")
    
    def get_comprehensive_summary(self) -> str:
        """获取完整统计摘要"""
        if self.call_count == 0:
            return "📊 Token统计: 暂无API调用"
        
        total_cost = sum(cat["cost"] for cat in self.api_categories.values())
        session_duration = time.time() - self.session_start_time
        
        summary = f"""📊 Token统计摘要 - {self.session_name}
{'='*60}
🕒 会话信息:
   持续时间: {session_duration/60:.1f} 分钟
   调用频率: {self.call_count/(session_duration/60):.1f} 次/分钟

💰 成本统计:
   总成本: ${total_cost:.4f} USD
   平均每次: ${total_cost/self.call_count:.4f} USD

📈 Token总计:
   总调用: {self.call_count:,} 次
   输入Token: {self.total_prompt_tokens:,}
   输出Token: {self.total_completion_tokens:,}
   总Token: {self.total_tokens:,}

📋 分类统计:"""

        # 显示各类别统计
        for category, stats in self.api_categories.items():
            if stats["calls"] > 0:
                avg_tokens = stats["total"] / stats["calls"]
                summary += f"""
   📌 {category}: {stats['calls']}次调用, {stats['total']:,}tokens, ${stats['cost']:.4f}"""

        return summary
    
    def get_category_breakdown(self) -> Dict[str, Any]:
        """获取分类统计详情"""
        breakdown = {}
        total_cost = sum(cat["cost"] for cat in self.api_categories.values())
        
        for category, stats in self.api_categories.items():
            if stats["calls"] > 0:
                breakdown[category] = {
                    "calls": stats["calls"],
                    "tokens": stats["total"],
                    "cost": stats["cost"],
                    "cost_percentage": (stats["cost"] / total_cost * 100) if total_cost > 0 else 0,
                    "avg_tokens_per_call": stats["total"] / stats["calls"]
                }
        
        return breakdown
    
    def get_token_summary(self) -> str:
        """获取Token统计摘要（兼容旧接口）"""
        return self.get_comprehensive_summary()
    
    def get_summary(self) -> str:
        """获取简要统计摘要"""
        if self.call_count == 0:
            return "Token统计: 暂无API调用"
        
        total_cost = sum(cat["cost"] for cat in self.api_categories.values())
        return f"Token统计: {self.call_count}次调用, {self.total_tokens:,}tokens, ${total_cost:.4f}"
    
    def reset(self, session_name: str = None):
        """重置统计（开始新会话）"""
        if self.call_count > 0:
            print(f"📊 会话{self.session_name}结束: {self.call_count}次调用, {self.total_tokens:,}tokens")
        
        self.__init__(session_name)
        print(f"🔄 Token统计已重置 - 新会话: {self.session_name}")

# 全局统一Token跟踪器
global_token_tracker = UnifiedTokenTracker()

# ==================== 兼容性接口函数 ====================

def get_token_summary() -> str:
    """全局Token统计摘要函数（兼容性接口）"""
    return global_token_tracker.get_token_summary()

def track_response(response_json: Dict, api_name: str, api_type: str = "deepseek", context: str = ""):
    """记录API响应Token使用（兼容性接口）"""
    global_token_tracker.record_from_response(response_json, api_name, api_type, context)

def track_usage(prompt_tokens: int, completion_tokens: int, 
                total_tokens: int = None, api_name: str = "Unknown API",
                api_type: str = "deepseek", context: str = ""):
    """直接记录Token使用（兼容性接口）"""
    global_token_tracker.record_usage(prompt_tokens, completion_tokens, total_tokens, api_name, api_type, context)

def reset_token_tracker(session_name: str = None):
    """重置Token跟踪器（兼容性接口）"""
    global_token_tracker.reset(session_name)

def get_token_breakdown() -> Dict[str, Any]:
    """获取Token分类统计（兼容性接口）"""
    return global_token_tracker.get_category_breakdown()