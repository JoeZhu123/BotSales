import pandas as pd
from typing import List, Dict
import re

class MarketAnalyzer:
    """
    市场分析器：计算利润空间和推荐指数
    """
    
    @staticmethod
    def clean_price(price_str: str) -> float:
        """清理价格字符串，转换为浮点数"""
        if not price_str or price_str == "N/A":
            return 0.0
        # 移除非数字字符（保留小数点）
        clean = re.sub(r'[^\d\.]', '', price_str)
        try:
            return float(clean)
        except:
            return 0.0

    def analyze_potential(self, amazon_data: List[Dict], source_data: List[Dict]) -> Dict:
        """
        分析选品潜力
        """
        # 1. 计算亚马逊平均售价
        amz_prices = [self.clean_price(p['price']) for p in amazon_data if p['price'] != "N/A"]
        avg_amz_price = sum(amz_prices) / len(amz_prices) if amz_prices else 0
        
        # 2. 计算1688平均进货价
        src_prices = [self.clean_price(p['price']) for p in source_data if p['price'] != "N/A"]
        avg_src_price = sum(src_prices) / len(src_prices) if src_prices else 0
        
        # 3. 汇率估算 (假设 1 USD = 7.2 CNY)
        # 注意：亚马逊抓取到的价格通常是美元符号$，1688是人民币￥
        # 这里简化处理，假设amz_prices是美元，src_prices是人民币
        exchange_rate = 7.2
        avg_amz_price_cny = avg_amz_price * exchange_rate
        
        # 4. 粗略毛利计算
        gross_margin = 0
        if avg_amz_price_cny > 0:
            gross_margin = (avg_amz_price_cny - avg_src_price) / avg_amz_price_cny
            
        return {
            "avg_amazon_price_usd": round(avg_amz_price, 2),
            "avg_sourcing_price_cny": round(avg_src_price, 2),
            "estimated_margin": f"{gross_margin*100:.1f}%",
            "recommendation": "High Potential" if gross_margin > 0.4 else "Medium/Low Potential"
        }

