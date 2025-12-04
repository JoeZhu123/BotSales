import pandas as pd
from typing import List, Dict
import re
from src.utils.llm_client import LLMClient
import logging

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """
    市场分析器：计算利润空间 + AI 智能点评
    """
    def __init__(self):
        self.llm = LLMClient()
    
    @staticmethod
    def clean_price(price_str: str) -> float:
        """清理价格字符串，转换为浮点数"""
        if not price_str or price_str == "N/A":
            return 0.0
        clean = re.sub(r'[^\d\.]', '', price_str)
        try:
            return float(clean)
        except:
            return 0.0

    def analyze_potential(self, amazon_data: List[Dict], source_data: List[Dict]) -> Dict:
        """
        分析选品潜力
        """
        # 1. 基础数据计算
        amz_prices = [self.clean_price(p['price']) for p in amazon_data if p['price'] != "N/A"]
        avg_amz_price = sum(amz_prices) / len(amz_prices) if amz_prices else 0
        
        src_prices = [self.clean_price(p['price']) for p in source_data if p['price'] != "N/A"]
        avg_src_price = sum(src_prices) / len(src_prices) if src_prices else 0
        
        exchange_rate = 7.2
        avg_amz_price_cny = avg_amz_price * exchange_rate
        
        gross_margin = 0
        if avg_amz_price_cny > 0:
            gross_margin = (avg_amz_price_cny - avg_src_price) / avg_amz_price_cny
            
        # 2. AI 智能点评
        ai_comment = "AI 分析未启用或配置错误。"
        if self.llm.client:
            try:
                # 构建 Prompt
                prompt = f"""
                Please act as a professional e-commerce data analyst. I have collected some product data from Amazon and 1688.
                
                Product Keyword: {amazon_data[0]['keyword'] if amazon_data else 'Unknown'}
                
                Amazon Market Data (Competitors):
                - Average Price: ${avg_amz_price:.2f}
                - Top Listings: {[p['title'][:30] + '... ($' + str(p['price']) + ')' for p in amazon_data[:3]]}
                
                1688 Sourcing Data (Cost):
                - Average Cost: ¥{avg_src_price:.2f}
                - Top Suppliers: {[s['title'][:20] + '... (¥' + str(s['price']) + ')' for s in source_data[:3]]}
                
                Estimated Gross Margin: {gross_margin*100:.1f}%
                
                Please provide a short, strategic analysis (in Chinese) covering:
                1. Profitability analysis.
                2. Market competitiveness.
                3. Suggestion: "Highly Recommended", "Cautious", or "Avoid".
                """
                
                logger.info("正在调用 LLM 生成分析报告...")
                ai_comment = self.llm.get_completion(prompt)
            except Exception as e:
                logger.error(f"AI 分析生成失败: {e}")
                ai_comment = "AI 分析生成过程中发生错误。"

        return {
            "avg_amazon_price_usd": round(avg_amz_price, 2),
            "avg_sourcing_price_cny": round(avg_src_price, 2),
            "estimated_margin": f"{gross_margin*100:.1f}%",
            "recommendation": "High Potential" if gross_margin > 0.4 else "Medium/Low Potential",
            "ai_analysis": ai_comment # 新增字段
        }
