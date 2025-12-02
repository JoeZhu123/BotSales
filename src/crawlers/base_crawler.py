from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaseCrawler(ABC):
    """
    所有电商爬虫的基类。
    强制子类实现特定的方法，保证系统的一致性。
    """
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.logger = logger

    @abstractmethod
    async def search_products(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        根据关键词搜索商品
        :param keyword: 搜索关键词
        :param limit: 抓取数量限制
        :return: 商品数据列表
        """
        pass

    @abstractmethod
    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """
        获取单个商品的详细信息（用于分析销量、评论等）
        :param product_id: 商品ID或URL
        :return: 商品详细数据
        """
        pass

    @abstractmethod
    async def close(self):
        """
        资源清理（关闭浏览器等）
        """
        pass
    
    def save_data(self, data: List[Dict], filename: str):
        """
        通用方法：保存数据到本地 data 目录
        """
        import pandas as pd
        import os
        from src.config import Config
        
        filepath = os.path.join(Config.DATA_DIR, filename)
        df = pd.DataFrame(data)
        
        # 简单的去重逻辑
        if os.path.exists(filepath):
            existing_df = pd.read_csv(filepath)
            df = pd.concat([existing_df, df]).drop_duplicates()
            
        df.to_csv(filepath, index=False)
        self.logger.info(f"数据已保存至: {filepath}")

