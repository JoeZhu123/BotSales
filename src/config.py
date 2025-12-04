import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class Config:
    # 1688 配置
    ALIBABA_API_KEY = os.getenv("ALIBABA_API_KEY")
    
    # LLM 配置 (支持 OpenAI, DeepSeek, Gemini 等兼容 OpenAI 接口的模型)
    # 默认使用 DeepSeek (性价比高)
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1") 
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
    
    # 爬虫通用配置
    # 修改为 False 以启用有头模式（显示浏览器界面），方便手动登录
    HEADLESS_MODE = os.getenv("HEADLESS_MODE", "False").lower() == "true"
    BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium") # chromium, firefox, webkit
    
    # 数据存储路径
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    @staticmethod
    def ensure_dirs():
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)

# 初始化目录
Config.ensure_dirs()
