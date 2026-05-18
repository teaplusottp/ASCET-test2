# -*- coding: utf-8 -*-
class ModelConfig:
    MODELS = {
        "DeepSeek-r1-0528-fp16-671b": {
            "supports_reasoning": True,
            "reasoning_field": "content",
            "temperature": 0.1
        },
        "gpt-oss-120b": {
            "supports_reasoning": True,
            "reasoning_field": "reasoning_content",
            "temperature": 0.2
        }
    }
    def __init__(self, model_type="DeepSeek-r1-0528-fp16-671b"):
        self.model_type = model_type
        self.config = self.MODELS.get(model_type, self.MODELS["DeepSeek-r1-0528-fp16-671b"])
        
    def supports_reasoning(self):
        return self.config["supports_reasoning"]
    def get_reasoning_field(self):
        return self.config["reasoning_field"]