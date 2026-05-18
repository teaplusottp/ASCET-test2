# model_config.py
"""
AI模型配置管理模块

支持多种AI模型的统一配置管理，包括模型参数、推理能力、响应格式等。
"""

from typing import List, Dict, Optional


class ModelConfig:
    """AI模型配置管理类 - 统一管理不同模型的配置"""
    
    # 预定义的模型配置
    MODELS = {
        "DeepSeek-r1-0528-fp16-671b": {
            "model_name": "DeepSeek-r1-0528-fp16-671b",
            "supports_reasoning": True,
            "reasoning_field": "content",  # DeepSeek在content中使用<think>标签
            "reasoning_tokens_field": None,  # DeepSeek不单独统计reasoning tokens
            "response_format": "streaming",
            "temperature": 0.1,
            "max_completion_tokens": 8192,
            "stream": True,
            "api_type": "openai_compatible"
        },
        "gpt-oss-120b": {
            "model_name": "gpt-oss-120b", 
            "supports_reasoning": True,
            "reasoning_field": "reasoning_content",  # GPTOSS单独的reasoning字段
            "reasoning_tokens_field": "reasoning_tokens",  # GPTOSS单独统计reasoning tokens
            "response_format": "json_completion",
            "temperature": 0.1,
            "max_completion_tokens": 8192,
            "stream": False,  # GPTOSS不支持streaming
            "api_type": "openai_compatible"
        },
        "gpt5-mini": {
            "model_name": "gpt-5-mini",
            "supports_reasoning": True,
            "reasoning_field": "content",  # GPT-5 mini在content中提供推理过程
            "reasoning_tokens_field": "reasoning_tokens",  # GPT-5 mini单独统计reasoning tokens
            "response_format": "standard",
            # "temperature": 0.1,
            "max_completion_tokens": 8192,
            "stream": True,
            "api_type": "openai"
            },
        "gpt-5-mini": {
            "model_name": "gpt-5-mini",
            "supports_reasoning": True,
            "reasoning_field": "content",  # GPT-5 mini在content中提供推理过程
            "reasoning_tokens_field": "reasoning_tokens",  # GPT-5 mini单独统计reasoning tokens
            "response_format": "standard",
            # "temperature": 0.1,
            "max_completion_tokens": 8192,
            "stream": True,
            "api_type": "openai"
            },
            
        

    }
    
    def __init__(self, model_type: str = "gptoss"):
        """
        初始化模型配置
        
        Args:
            model_type (str): 模型类型，支持的模型类型见MODELS字典
            
        Raises:
            ValueError: 当模型类型不支持时抛出
        """
        if model_type not in self.MODELS:
            supported_models = list(self.MODELS.keys())
            raise ValueError(
                f"Unsupported model type: {model_type}. "
                f"Supported types: {supported_models}"
            )
        
        self.model_type = model_type
        self.config = self.MODELS[model_type].copy()
        
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.config["model_name"]
    
    def get_api_type(self) -> str:
        """获取API类型"""
        return self.config.get("api_type", "openai_compatible")
    
    def supports_reasoning(self) -> bool:
        """模型是否支持推理过程"""
        return self.config["supports_reasoning"]
    
    def get_reasoning_field(self) -> Optional[str]:
        """获取推理内容字段名"""
        return self.config.get("reasoning_field")
    
    def get_reasoning_tokens_field(self) -> Optional[str]:
        """获取推理tokens字段名"""
        return self.config.get("reasoning_tokens_field")
    
    def get_request_params(self, messages: List[Dict]) -> Dict:
        """
        获取API请求参数
        
        Args:
            messages (List[Dict]): 消息列表
            
        Returns:
            Dict: API请求参数
        """
        params = {
            "messages": messages,
            "model": self.config["model_name"],
            "max_completion_tokens": self.config["max_completion_tokens"]
        }
        
        # 添加可选参数
        if "temperature" in self.config and self.config["temperature"] is not None:
            params["temperature"] = self.config["temperature"]
            
        if "stream" in self.config and self.config["stream"]:
            params["stream"] = True
            
        # 特殊模型的额外参数
        if self.model_type == "gptoss":
            # GPTOSS可能需要特殊参数
            pass
        elif self.model_type == "deepseek":
            # DeepSeek的特殊参数
            pass
            
        return params
    
    def is_streaming(self) -> bool:
        """是否使用流式响应"""
        return self.config.get("stream", False)
    
    def update_config(self, **kwargs):
        """
        更新配置参数
        
        Args:
            **kwargs: 要更新的配置参数
        """
        self.config.update(kwargs)
    
    def get_config(self) -> Dict:
        """获取完整配置"""
        return self.config.copy()
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """获取支持的模型列表"""
        return list(cls.MODELS.keys())
    
    @classmethod
    def add_model(cls, model_type: str, config: Dict):
        """
        动态添加新模型配置
        
        Args:
            model_type (str): 模型类型标识
            config (Dict): 模型配置字典
        """
        required_fields = ["model_name", "supports_reasoning"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Model config missing required field: {field}")
        
        cls.MODELS[model_type] = config
    
    def validate_config(self) -> bool:
        """
        验证配置的有效性
        
        Returns:
            bool: 配置是否有效
        """
        required_fields = [
            "model_name", "supports_reasoning", "response_format", 
            "max_completion_tokens"
        ]
        
        for field in required_fields:
            if field not in self.config:
                return False
        
        # 如果支持推理，必须有推理字段配置
        if self.config["supports_reasoning"] and not self.config.get("reasoning_field"):
            return False
            
        return True
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"ModelConfig(type={self.model_type}, model={self.get_model_name()})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"ModelConfig(model_type='{self.model_type}', "
                f"model_name='{self.get_model_name()}', "
                f"supports_reasoning={self.supports_reasoning()})")


# 便捷函数
def create_model_config(model_type: str = "gptoss") -> ModelConfig:
    """
    创建模型配置的便捷函数
    
    Args:
        model_type (str): 模型类型
        
    Returns:
        ModelConfig: 模型配置实例
    """
    return ModelConfig(model_type)


def list_supported_models() -> List[str]:
    """
    列出所有支持的模型
    
    Returns:
        List[str]: 支持的模型列表
    """
    return ModelConfig.get_supported_models()


# 模块级别的常量
DEFAULT_MODEL_TYPE = "gptoss"
REASONING_SUPPORTED_MODELS = [
    model_type for model_type, config in ModelConfig.MODELS.items()
    if config["supports_reasoning"]
]

if __name__ == "__main__":
    # 模块测试代码
    print("支持的模型:")
    for model in list_supported_models():
        config = ModelConfig(model)
        reasoning = "✓" if config.supports_reasoning() else "✗" 
        streaming = "✓" if config.is_streaming() else "✗"
        print(f"  {model:12} | {config.get_model_name():30} | 推理: {reasoning} | 流式: {streaming}")
    
    # 测试GPTOSS配置
    gptoss_config = create_model_config("gptoss")
    print(f"\nGPTOSS配置: {gptoss_config}")
    print(f"推理字段: {gptoss_config.get_reasoning_field()}")
    print(f"推理Token字段: {gptoss_config.get_reasoning_tokens_field()}")