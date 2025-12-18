import pandas as pd
from typing import List, Dict
import re
from src.utils.llm_client import LLMClient
import logging

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """
    市场分析器：计算利润空间 + AI 智能点评 (全网版)
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

    def analyze_potential(self, sales_data: List[Dict], sourcing_data: List[Dict], trend_data: List[Dict] = []) -> Dict:
        """
        分析选品潜力 (Sales + Sourcing + Trends)
        """
        # 1. 基础数据计算 (以 Amazon 为主)
        amazon_items = [p for p in sales_data if p['platform'] == 'Amazon']
        amz_prices = [self.clean_price(p['price']) for p in amazon_items if p['price'] != "N/A"]
        avg_amz_price = sum(amz_prices) / len(amz_prices) if amz_prices else 0
        
        src_prices = [self.clean_price(p['price']) for p in sourcing_data if p['price'] != "N/A"]
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
                # 提取各平台摘要
                sales_summary = "\n".join([f"- [{item['platform']}] {item['title'][:30]}... (${item['price']})" for item in sales_data[:4]])
                sourcing_summary = "\n".join([f"- [{item['platform']}] {item['title'][:20]}... (¥{item['price']})" for item in sourcing_data[:4]])
                trend_summary = "No Trend Data"
                if trend_data:
                    trend_summary = "\n".join([f"- [Kickstarter] {item['title'][:40]}... (Raised: {item['pledged']})" for item in trend_data[:3]])
                
                # 构建 Prompt
                prompt = f"""
                You are a Product Strategy Expert. Analyze the following e-commerce data for a specific niche.
                
                Product Keyword: {sales_data[0]['keyword'] if sales_data else 'Unknown'}
                
                1. CURRENT MARKET (Amazon/AliExpress):
                {sales_summary}
                Average Selling Price: ${avg_amz_price:.2f}
                
                2. SUPPLY CHAIN (1688/YiwuGo):
                {sourcing_summary}
                Average Cost: ¥{avg_src_price:.2f}
                Estimated Margin: {gross_margin*100:.1f}%
                
                3. FUTURE TRENDS (Kickstarter Innovation):
                {trend_summary}
                
                Please provide a strategic report (in Chinese) covering:
                1. **Profitability**: Is the margin healthy?
                2. **Innovation Gap**: Compare Amazon products with Kickstarter projects. What features are missing in the mass market?
                3. **Actionable Advice**: How should I differentiate my product? (e.g., "Combine the cheap cost of 1688 with the new feature X from Kickstarter...")
                """
                
                logger.info("正在调用 LLM 生成全网分析报告...")
                ai_comment = self.llm.get_completion(prompt)
            except Exception as e:
                logger.error(f"AI 分析生成失败: {e}")
                ai_comment = f"AI 分析生成过程中发生错误: {e}"

        return {
            "avg_amazon_price_usd": round(avg_amz_price, 2),
            "avg_sourcing_price_cny": round(avg_src_price, 2),
            "estimated_margin": f"{gross_margin*100:.1f}%",
            "recommendation": "High Potential" if gross_margin > 0.4 else "Medium/Low Potential",
            "ai_analysis": ai_comment
        }
