from openai import OpenAI
from src.config import Config
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.client = None
        if Config.LLM_API_KEY:
            try:
                self.client = OpenAI(
                    api_key=Config.LLM_API_KEY,
                    base_url=Config.LLM_BASE_URL
                )
                logger.info(f"LLM Client 初始化成功 (Model: {Config.LLM_MODEL})")
            except Exception as e:
                logger.error(f"LLM Client 初始化失败: {e}")
        else:
            logger.warning("未配置 LLM_API_KEY，AI 功能将不可用。")

    def get_completion(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
        """
        调用 LLM 获取回复
        """
        if not self.client:
            return "Error: LLM not configured"

        try:
            response = self.client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"Error calling LLM: {str(e)}"

