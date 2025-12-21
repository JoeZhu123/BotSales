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
        # 1. 基础数据计算
        platforms = ["Amazon", "AliExpress", "Temu", "Shopee"]
        platform_stats = {}
        
        all_sales_prices_cny = []
        exchange_rate = 7.2
        
        for p_name in platforms:
            items = [p for p in sales_data if p_name in p['platform']]
            prices = [self.clean_price(p['price']) for p in items if p['price'] != "N/A"]
            avg = sum(prices) / len(prices) if prices else 0
            platform_stats[p_name] = avg
            
            # 统一换算为 CNY 用于计算毛利
            # 假设 Shopee/Temu 也是以 USD 采集或类似汇率，这里简化处理
            for pr in prices:
                all_sales_prices_cny.append(pr * exchange_rate)

        avg_sales_price_cny = sum(all_sales_prices_cny) / len(all_sales_prices_cny) if all_sales_prices_cny else 0
        
        src_prices = [self.clean_price(p['price']) for p in sourcing_data if p['price'] != "N/A"]
        avg_src_price = sum(src_prices) / len(src_prices) if src_prices else 0
        
        gross_margin = 0
        if avg_sales_price_cny > 0:
            gross_margin = (avg_sales_price_cny - avg_src_price) / avg_sales_price_cny
            
        # 2. AI 智能点评
        ai_comment = "AI 分析未启用或配置错误。"
        if self.llm.client:
            try:
                # 提取各平台摘要
                sales_summary = "\n".join([f"- [{item['platform']}] {item['title'][:30]}... ({item['price']})" for item in sales_data[:10]])
                sourcing_summary = "\n".join([f"- [{item['platform']}] {item['title'][:20]}... (¥{item['price']})" for item in sourcing_data[:6]])
                trend_summary = "No Trend Data"
                if trend_data:
                    trend_summary = "\n".join([f"- [Kickstarter] {item['title'][:40]}... (Raised: {item['pledged']})" for item in trend_data[:3]])
                
                # 构建 Prompt
                prompt = f"""
                You are a Global E-commerce Strategy Expert. Analyze data from Amazon, AliExpress, Temu, Shopee, and 1688.
                
                Product Keyword: {sales_data[0]['keyword'] if sales_data else 'Unknown'}
                
                1. GLOBAL MARKET SNAPSHOT (Sales):
                {sales_summary}
                - Amazon Avg: ${platform_stats.get('Amazon', 0):.2f}
                - Temu Avg: ${platform_stats.get('Temu', 0):.2f}
                - Shopee Avg: ${platform_stats.get('Shopee', 0):.2f}
                
                2. SUPPLY CHAIN (1688/YiwuGo):
                {sourcing_summary}
                Average Cost: ¥{avg_src_price:.2f}
                Estimated Global Margin: {gross_margin*100:.1f}%
                
                3. FUTURE TRENDS (Innovation):
                {trend_summary}
                
                Please provide a strategic report (in Chinese):
                1. **Global Pricing Strategy**: Compare pricing across Amazon (premium), Temu (ultra-low), and Shopee (regional). Where is the best profit?
                2. **Profitability**: Is the sourcing cost low enough to compete on Temu while maintaining Amazon-level quality?
                3. **Innovation & Differentiation**: What features from Kickstarter can be used to avoid a price war on Temu/Shopee?
                4. **Actionable Advice**: Recommend which platform to focus on first.
                """
                
                logger.info("正在调用 LLM 生成全网深度分析报告...")
                ai_comment = self.llm.get_completion(prompt)
            except Exception as e:
                logger.error(f"AI 分析生成失败: {e}")
                ai_comment = f"AI 分析生成过程中发生错误: {e}"

        return {
            "avg_amazon_price_usd": round(platform_stats.get('Amazon', 0), 2),
            "avg_sourcing_price_cny": round(avg_src_price, 2),
            "estimated_margin": f"{gross_margin*100:.1f}%",
            "recommendation": "High Potential" if gross_margin > 0.4 else "Medium/Low Potential",
            "ai_analysis": ai_comment,
            "platform_stats": platform_stats
        }
