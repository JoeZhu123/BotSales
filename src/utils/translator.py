from src.utils.llm_client import LLMClient
import logging

logger = logging.getLogger(__name__)

class Translator:
    """
    智能翻译工具：优先使用 LLM，失败则回退到字典
    """
    def __init__(self):
        self.llm = LLMClient()
        self.mock_dict = {
            "yoga mat": "瑜伽垫",
            "running shoes": "跑步鞋",
            "wireless earbuds": "无线耳机",
            "water bottle": "水杯",
            "phone case": "手机壳"
        }
    
    def translate_to_chinese(self, text: str) -> str:
        # 1. 尝试 LLM 翻译
        if self.llm.client:
            try:
                prompt = f"Please translate the following Amazon product keyword into a concise Chinese search term for 1688 sourcing. Only return the Chinese term, no explanation.\n\nKeyword: {text}"
                result = self.llm.get_completion(prompt, system_prompt="You are a professional e-commerce sourcing assistant.")
                if result and "Error" not in result:
                    logger.info(f"LLM 翻译结果: {text} -> {result}")
                    return result
            except Exception as e:
                logger.warning(f"LLM 翻译失败，回退到字典模式: {e}")

        # 2. 回退到字典模式
        text_lower = text.lower()
        for k, v in self.mock_dict.items():
            if k in text_lower:
                return v
        
        return text
