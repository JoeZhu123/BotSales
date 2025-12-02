import asyncio
from src.crawlers.amazon_crawler import AmazonCrawler
from src.sourcing.sourcer_1688 import Sourcer1688
from src.utils.translator import Translator
from src.analysis.market_analyzer import MarketAnalyzer
import pandas as pd
import os
from datetime import datetime
import sys
import io

# 强制设置标准输出为 utf-8，解决 Windows 控制台中文乱码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    print("=== AI Sales Bot Started ===")
    
    # 1. 获取用户输入 (演示模式下固定为 yoga mat)
    keyword = "yoga mat"
    print(f"Target Keyword: {keyword}")

    # 2. Amazon 数据采集
    print(f"\n[1/4] 正在从 Amazon 采集 '{keyword}' 的销售数据...")
    crawler = AmazonCrawler()
    products = await crawler.search_products(keyword, limit=5)
    await crawler.close()
    
    if not products:
        print("未能抓取到亚马逊数据，程序终止。")
        return
    
    print(f"成功抓取 {len(products)} 个商品。")
    
    # 3. 分析与翻译
    print(f"\n[2/4] 分析热门商品并翻译关键词...")
    translator = Translator()
    cn_keyword = translator.translate_to_chinese(keyword)
    print(f"目标中文关键词: {cn_keyword}")
    
    # 4. 1688 找货
    print(f"\n[3/4] 正在 1688 寻找 '{cn_keyword}' 的供应商...")
    sourcer = Sourcer1688()
    sources = await sourcer.search_source(cn_keyword, limit=5)
    
    # 5. 深度分析
    print(f"\n[4/4] 生成市场分析报告...")
    analyzer = MarketAnalyzer()
    analysis = analyzer.analyze_potential(products, sources)
    
    # 打印分析结果
    print("\n" + "="*50)
    print(f" 选品分析报告: {keyword}")
    print("="*50)
    print(f"亚马逊平均售价 (USD): ${analysis['avg_amazon_price_usd']}")
    print(f"1688平均进货价 (CNY): ¥{analysis['avg_sourcing_price_cny']}")
    print(f"预估毛利率: {analysis['estimated_margin']}")
    print(f"系统建议: {analysis['recommendation']}")
    print("-" * 50)
    
    print("\n--- 亚马逊市场 (Top Items) ---")
    for p in products:
        print(f"- [{p['price']}] {p['title'][:50]}...")
        
    print("\n--- 1688 供应链 (Top Suppliers) ---")
    if sources:
        for s in sources:
            print(f"- [{s['price']}] {s['supplier']} | {s['title'][:30]}...")
    else:
        print("未找到相关供应商（建议：首次使用请开启 HEADLESS_MODE=False 手动登录一次 1688）。")

    # 保存数据
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if products:
        pd.DataFrame(products).to_csv(f"data/amazon_{keyword}_{timestamp}.csv", index=False)
    if sources:
        pd.DataFrame(sources).to_csv(f"data/1688_{cn_keyword}_{timestamp}.csv", index=False, encoding='utf_8_sig')

if __name__ == "__main__":
    asyncio.run(main())
