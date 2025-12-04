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
import shutil

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
    
    # 5. 深度分析 & 报告生成
    print(f"\n[4/4] 生成市场分析报告...")
    analyzer = MarketAnalyzer()
    analysis = analyzer.analyze_potential(products, sources)
    
    # 打印控制台摘要
    print("\n" + "="*50)
    print(f" 选品分析报告: {keyword}")
    print("="*50)
    print(f"亚马逊平均售价 (USD): ${analysis['avg_amazon_price_usd']}")
    print(f"1688平均进货价 (CNY): ¥{analysis['avg_sourcing_price_cny']}")
    print(f"预估毛利率: {analysis['estimated_margin']}")
    print(f"系统建议: {analysis['recommendation']}")
    
    if 'ai_analysis' in analysis:
        print("-" * 30)
        print("🤖 AI 智能点评:")
        print(analysis['ai_analysis'])
        
    print("-" * 50)

    # === 数据保存与清理逻辑 ===
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = os.path.join("data", "reports")
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
        
    # 1. 生成综合报告 (Excel)
    report_file = os.path.join(report_dir, f"Analysis_{keyword}_{timestamp}.xlsx")
    
    with pd.ExcelWriter(report_file, engine='openpyxl') as writer:
        # 概览页
        summary_df = pd.DataFrame([analysis])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # 亚马逊详情页
        if products:
            pd.DataFrame(products).to_excel(writer, sheet_name='Amazon_Data', index=False)
            
        # 1688详情页
        if sources:
            pd.DataFrame(sources).to_excel(writer, sheet_name='1688_Data', index=False)
            
    print(f"\n✅ 最终报告已生成: {report_file}")
    
    # 2. 清理临时的 raw csv 文件 (如果有的话，之前版本会生成)
    # 检查 data 目录下所有以 .csv 结尾的非报告文件
    for filename in os.listdir("data"):
        if filename.endswith(".csv"):
            try:
                os.remove(os.path.join("data", filename))
                print(f"已清理临时文件: {filename}")
            except Exception as e:
                print(f"清理失败 {filename}: {e}")

if __name__ == "__main__":
    # 需要安装 openpyxl 库来支持 Excel 写入
    # pip install openpyxl
    asyncio.run(main())
