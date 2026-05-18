# response_handler.py
"""
AI模型响应处理模块

处理不同AI模型的响应格式差异，统一提取内容、推理过程和Token使用信息。
"""

import re
from typing import Dict, Optional
from src.ai_core.model_config import ModelConfig
from typing import Dict, Any, Optional, List

class ResponseHandler:
    """通用响应处理器 - 适配不同模型的响应格式"""
    
    def __init__(self, model_config: ModelConfig):
        """
        初始化响应处理器
        
        Args:
            model_config (ModelConfig): 模型配置实例
        """
        self.model_config = model_config
    
    def extract_reasoning_content(self, response_data: Dict) -> Optional[str]:
        """
        从响应中提取推理过程内容
        
        Args:
            response_data (Dict): 完整的API响应数据
            
        Returns:
            Optional[str]: 推理过程内容，如果不存在则返回None
        """
        if not self.model_config.supports_reasoning():
            return None
        
        reasoning_field = self.model_config.get_reasoning_field()
        if not reasoning_field:
            return None
        
        try:
            # 根据不同模型提取推理内容
            if self.model_config.model_type == "deepseek":
                return self._extract_deepseek_reasoning(response_data)
            elif self.model_config.model_type == "gptoss":
                return self._extract_gptoss_reasoning(response_data)
            else:
                # 通用推理内容提取
                return self._extract_generic_reasoning(response_data, reasoning_field)
            
        except Exception as e:
            print(f"提取推理内容失败: {e}")
            return None
        
        return None
    
    def _extract_deepseek_reasoning(self, response_data: Dict) -> Optional[str]:
        """提取DeepSeek的推理内容（从<think>标签）"""
        choices = response_data.get("choices", [])
        if not choices:
            return None
        
        content = choices[0].get("message", {}).get("content", "")
        return self._extract_think_tags(content)
    
    def _extract_gptoss_reasoning(self, response_data: Dict) -> Optional[str]:
        """提取GPTOSS的推理内容（从reasoning_content字段）"""
        choices = response_data.get("choices", [])
        if not choices:
            return None
        
        reasoning_content = choices[0].get("message", {}).get("reasoning_content", "")
        return reasoning_content if reasoning_content else None
    
    def _extract_generic_reasoning(self, response_data: Dict, reasoning_field: str) -> Optional[str]:
        """通用推理内容提取"""
        choices = response_data.get("choices", [])
        if not choices:
            return None
        
        message = choices[0].get("message", {})
        reasoning_content = message.get(reasoning_field, "")
        return reasoning_content if reasoning_content else None
    
    def _extract_think_tags(self, content: str) -> Optional[str]:
        """从content中提取<think>标签内容（DeepSeek专用）"""
        if not content:
            return None
        
        # 使用正则表达式提取<think>...</think>内容
        think_pattern = r'<think>(.*?)</think>'
        matches = re.findall(think_pattern, content, re.DOTALL)
        
        if matches:
            # 如果有多个think标签，合并它们
            return "\n\n".join(match.strip() for match in matches)
        
        return None
    
    def extract_main_content(self, response_data: Dict) -> str:
        """
        从响应中提取主要内容（排除推理过程）
        
        Args:
            response_data (Dict): 完整的API响应数据
            
        Returns:
            str: 主要内容
        """
        try:
            choices = response_data.get("choices", [])
            if not choices:
                return ""
            
            content = choices[0].get("message", {}).get("content", "")
            
            # 如果是DeepSeek，需要移除<think>标签
            if self.model_config.model_type == "deepseek":
                content = self._remove_think_tags(content)
            
            return content
            
        except Exception as e:
            print(f"提取主要内容失败: {e}")
            return ""
    
    def extract_ai_json_content(self, content: str) -> List[Dict]:
        """从AI响应中提取JSON格式的错误信息"""
        import re
        import json
        
        json_results = []
        
        # 查找所有JSON代码块
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        json_matches = re.findall(json_pattern, content, re.DOTALL)
        
        for json_str in json_matches:
            try:
                json_data = json.loads(json_str)
                json_results.append(json_data)
            except json.JSONDecodeError:
                continue
        
        return json_results


    def _remove_think_tags(self, content: str) -> str:
        """移除DeepSeek的<think>标签"""
        # 移除所有<think>...</think>标签及其内容
        think_pattern = r'<think>.*?</think>'
        content = re.sub(think_pattern, '', content, flags=re.DOTALL)
        return content.strip()
    
    def extract_usage_info(self, response_data: Dict) -> Dict:
        """
        从响应中提取token使用信息
        
        Args:
            response_data (Dict): 完整的API响应数据
            
        Returns:
            Dict: token使用信息
        """
        try:
            usage = response_data.get("usage", {})
            
            result = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "reasoning_tokens": 0  # 默认值
            }
            
            # 提取reasoning_tokens（支持嵌套结构）
            reasoning_tokens_field = self.model_config.get_reasoning_tokens_field()
            if reasoning_tokens_field:
                # 先在顶级字段查找
                if reasoning_tokens_field in usage:
                    result["reasoning_tokens"] = usage[reasoning_tokens_field]
                # 然后在completion_tokens_details中查找（gpt5-mini特殊处理）
                elif "completion_tokens_details" in usage:
                    details = usage["completion_tokens_details"]
                    if reasoning_tokens_field in details:
                        result["reasoning_tokens"] = details[reasoning_tokens_field]
            
            # 特殊处理：确保total_tokens正确计算
            if result["total_tokens"] == 0:
                result["total_tokens"] = result["prompt_tokens"] + result["completion_tokens"] + result["reasoning_tokens"]
            
            return result
            
        except Exception as e:
            print(f"提取token使用信息失败: {e}")
            return {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "reasoning_tokens": 0
            }
    
    def format_reasoning_content(self, reasoning_content: str) -> str:
        """
        格式化推理内容为适合展示的格式
        
        Args:
            reasoning_content (str): 原始推理内容
            
        Returns:
            str: 格式化后的推理内容
        """
        if not reasoning_content:
            return ""
        
        if self.model_config.model_type == "gptoss":
            # GPTOSS：包装为可折叠的HTML详情
            return f"""
<details>
<summary>🤖 AI推理过程（点击展开）</summary>

```
{reasoning_content}
```

</details>
"""
        elif self.model_config.model_type == "deepseek":
            # DeepSeek：包装为可折叠的HTML详情
            return f"""
<details>
<summary>💭 AI思考过程（点击展开）</summary>

```
{reasoning_content}
```

</details>
"""
        else:
            # 其他模型：简单格式
            return f"""
**AI推理过程:**
```
{reasoning_content}
```
"""
    
    def process_complete_response(self, response_data: Dict) -> Dict:
        """
        完整处理响应数据，提取所有相关信息
        
        Args:
            response_data (Dict): 完整的API响应数据
            
        Returns:
            Dict: 处理后的响应信息
        """
        # 提取主要内容
        main_content = self.extract_main_content(response_data)
        
        # 提取推理内容
        reasoning_content = self.extract_reasoning_content(response_data)
        
        # 提取Token使用信息
        usage_info = self.extract_usage_info(response_data)
        
        # 格式化推理内容
        formatted_reasoning = ""
        if reasoning_content:
            formatted_reasoning = self.format_reasoning_content(reasoning_content)
        
        # 构建完整响应
        complete_content = main_content
        if formatted_reasoning:
            complete_content = formatted_reasoning + "\n\n" + main_content
        
        return {
            "main_content": main_content,
            "reasoning_content": reasoning_content,
            "formatted_reasoning": formatted_reasoning,
            "complete_content": complete_content,
            "usage_info": usage_info,
            "has_reasoning": bool(reasoning_content),
            "model_type": self.model_config.model_type
        }
    
    def validate_response(self, response_data: Dict) -> tuple[bool, str]:
        """
        验证响应数据的有效性
        
        Args:
            response_data (Dict): API响应数据
            
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        if not response_data:
            return False, "响应数据为空"
        
        if "choices" not in response_data:
            return False, "响应缺少choices字段"
        
        choices = response_data["choices"]
        if not choices:
            return False, "choices为空"
        
        first_choice = choices[0]
        if "message" not in first_choice:
            return False, "第一个choice缺少message字段"
        
        message = first_choice["message"]
        if "content" not in message:
            return False, "message缺少content字段"
        
        # 检查推理内容（如果模型支持）
        if self.model_config.supports_reasoning():
            reasoning_field = self.model_config.get_reasoning_field()
            if reasoning_field and reasoning_field == "content":
                # DeepSeek类型：content中应包含<think>标签
                content = message["content"]
                if self.model_config.model_type == "deepseek" and "<think>" not in content:
                    return False, "DeepSeek响应content中缺少<think>标签"
            elif reasoning_field and reasoning_field not in message:
                # 其他推理模型：应有独立推理字段
                return False, f"推理模型响应缺少{reasoning_field}字段"
        
        return True, ""
    
    def get_model_info(self) -> Dict:
        """获取当前模型的信息"""
        return {
            "model_type": self.model_config.model_type,
            "model_name": self.model_config.get_model_name(),
            "supports_reasoning": self.model_config.supports_reasoning(),
            "reasoning_field": self.model_config.get_reasoning_field(),
            "reasoning_tokens_field": self.model_config.get_reasoning_tokens_field(),
            "is_streaming": self.model_config.is_streaming()
        }


# 便捷函数
def create_response_handler(model_type: str = "gptoss") -> ResponseHandler:
    """
    创建响应处理器的便捷函数
    
    Args:
        model_type (str): 模型类型
        
    Returns:
        ResponseHandler: 响应处理器实例
    """
    model_config = ModelConfig(model_type)
    return ResponseHandler(model_config)


def process_model_response(response_data: Dict, model_type: str = "gptoss") -> Dict:
    """
    处理模型响应的便捷函数
    
    Args:
        response_data (Dict): API响应数据
        model_type (str): 模型类型
        
    Returns:
        Dict: 处理后的响应信息
    """
    handler = create_response_handler(model_type)
    return handler.process_complete_response(response_data)


if __name__ == "__main__":
    # 模块测试代码
    from src.ai_core.model_config import ModelConfig, list_supported_models
    
    print("响应处理器测试:")
    
    # 测试不同模型的处理器创建
    for model_type in list_supported_models()[:3]:  # 测试前3个模型
        try:
            handler = create_response_handler(model_type)
            info = handler.get_model_info()
            print(f"  {model_type:10} | 推理支持: {'✓' if info['supports_reasoning'] else '✗'} | 推理字段: {info['reasoning_field'] or 'None'}")
        except Exception as e:
            print(f"  {model_type:10} | 错误: {e}")
    
    # 测试GPTOSS响应处理
    print("\nGPTOSS响应格式测试:")
    gptoss_handler = create_response_handler("gptoss")
    
    # 模拟GPTOSS响应格式
    sample_gptoss_response = {
        "choices": [{
            "message": {
                "content": "这是主要回答内容",
                "reasoning_content": "这是推理过程：\n1. 分析问题\n2. 考虑方案\n3. 得出结论"
            }
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "reasoning_tokens": 50,
            "total_tokens": 350
        }
    }
    
    result = gptoss_handler.process_complete_response(sample_gptoss_response)
    print(f"主要内容: {result['main_content']}")
    print(f"推理内容: {result['reasoning_content'][:50]}...")
    print(f"Token使用: {result['usage_info']}")