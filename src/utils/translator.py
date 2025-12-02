class Translator:
    """
    简单的翻译工具
    实际项目中应使用 Google Translate API 或 OpenAI API
    """
    def __init__(self):
        # 简单的字典用于演示
        self.mock_dict = {
            "yoga mat": "瑜伽垫",
            "running shoes": "跑步鞋",
            "wireless earbuds": "无线耳机",
            "water bottle": "水杯",
            "phone case": "手机壳"
        }
    
    def translate_to_chinese(self, text: str) -> str:
        text_lower = text.lower()
        for k, v in self.mock_dict.items():
            if k in text_lower:
                return v
        # 如果字典里没有，直接返回原文本（或提示用户）
        return text

