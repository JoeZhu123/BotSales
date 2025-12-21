import asyncio
from src.crawlers.amazon_crawler import AmazonCrawler
from src.crawlers.aliexpress_crawler import AliExpressCrawler
from src.crawlers.temu_crawler import TemuCrawler
from src.crawlers.shopee_crawler import ShopeeCrawler
from src.crawlers.tiktok_crawler import TikTokCrawler
from src.crawlers.kickstarter_crawler import KickstarterCrawler
from src.sourcing.sourcer_1688 import Sourcer1688
from src.sourcing.sourcer_yiwugo import SourcerYiwuGo
from src.utils.translator import Translator
from src.analysis.market_analyzer import MarketAnalyzer
from src.utils.visualizer import DataVisualizer
from src.utils.report_generator import ReportGenerator
import pandas as pd
import os
from datetime import datetime
import sys
import io

# 强制设置标准输出为 utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    print("=== AI 全球电商选品系统 v3.0 (含众筹趋势) ===")
    
    keyword = "yoga mat" # 默认演示关键词
    safe_keyword = keyword.replace(" ", "_")
    print(f"Target Keyword: {keyword}")

    # === 1. 销售端数据 (Sales) ===
    sales_data = []
    
    # Task 1: Amazon
    print(f"\n[1/6] 正在采集 Amazon 数据...")
    amz = AmazonCrawler()
    res = await amz.search_products(keyword, limit=5)
    await amz.close()
    if res:
        print(f"✅ Amazon: {len(res)} items")
        sales_data.extend(res)
    
    # Task 2: AliExpress
    print(f"\n[2/6] 正在采集 AliExpress 数据...")
    ali = AliExpressCrawler()
    res = await ali.search_products(keyword, limit=5)
    await ali.close()
    if res:
        print(f"✅ AliExpress: {len(res)} items")
        sales_data.extend(res)

    # Task 2.1: Temu
    print(f"\n[新增] 正在采集 Temu 数据...")
    temu = TemuCrawler()
    res = await temu.search_products(keyword, limit=5)
    await temu.close()
    if res:
        print(f"✅ Temu: {len(res)} items")
        sales_data.extend(res)

    # Task 2.2: Shopee
    print(f"\n[新增] 正在采集 Shopee 数据...")
    shopee = ShopeeCrawler()
    res = await shopee.search_products(keyword, limit=5)
    await shopee.close()
    if res:
        print(f"✅ Shopee: {len(res)} items")
        sales_data.extend(res)

    print(f"\n[新增] 正在通过 TikTok 接口采集实时爆品...")
    tiktok = TikTokCrawler()
    # 1. 搜索特定关键词商品
    res_search = await tiktok.search_products(keyword, limit=5)
    sales_data.extend(res_search)
    # 2. 获取全网实时爆品榜单作为参考
    res_trending = await tiktok.get_trending_products(limit=5)
    # 趋势榜单数据存入 trend_data 供 AI 分析
    await tiktok.close()
    if res_search: print(f"✅ TikTok Shop: {len(res_search)} items")
    if res_trending: print(f"✅ TikTok Trending: {len(res_trending)} hot items")

    if not sales_data:
        print("❌ 未能采集到任何平台的销售数据，程序终止。")
        return

    # === 2. 趋势端数据 (Trends) ===
    trend_data = []
    if res_trending:
        trend_data.extend(res_trending)
    print(f"\n[3/6] 正在采集 Kickstarter 创新趋势...")
    ks = KickstarterCrawler()
    res = await ks.search_products(keyword, limit=5)
    await ks.close()
    if res:
        print(f"✅ Kickstarter: {len(res)} projects")
        trend_data.extend(res)
    else:
        print("⚠️ 未找到相关 Kickstarter 项目 (可能该品类较传统)")

    # === 3. 翻译关键词 ===
    print(f"\n[4/6] 智能翻译关键词...")
    translator = Translator()
    cn_keyword = translator.translate_to_chinese(keyword)
    print(f"目标中文关键词: {cn_keyword}")
    
    # === 4. 供应链端数据 (Sourcing) ===
    sourcing_data = []
    
    # Task 3: 1688
    print(f"\n[5/6] 正在采集 1688 货源...")
    s1688 = Sourcer1688()
    res = await s1688.search_source(cn_keyword, limit=5)
    if res:
        print(f"✅ 1688: {len(res)} suppliers")
        sourcing_data.extend(res)
        
    # Task 4: YiwuGo
    print(f"      正在采集 义乌购 货源...")
    sy = SourcerYiwuGo()
    res = await sy.search_source(cn_keyword, limit=5)
    if res:
        print(f"✅ YiwuGo: {len(res)} suppliers")
        sourcing_data.extend(res)
    
    # === 5. 深度分析 & 报告生成 ===
    print(f"\n[6/6] 生成全网趋势分析报告...")
    analyzer = MarketAnalyzer()
    
    analysis = analyzer.analyze_potential(sales_data, sourcing_data, trend_data)
    
    # 打印简报
    print("\n" + "="*50)
    print(f" 选品分析简报: {keyword}")
    print("="*50)
    print(f"Amazon 均价: ${analysis.get('avg_amazon_price_usd', 0)}")
    print(f"供应链均价: ¥{analysis.get('avg_sourcing_price_cny', 0)}")
    
    if 'ai_analysis' in analysis:
        print("-" * 30)
        print("🤖 AI 创新洞察:")
        print(analysis['ai_analysis'])
    print("-" * 50)

    # === 6. 生成可视化图表 ===
    print(f"\n正在绘制数据仪表盘图表...")
    visualizer = DataVisualizer()
    viz_path = visualizer.generate_dashboard(safe_keyword, analysis, sales_data, sourcing_data, trend_data)
    print(f"✅ 可视化仪表盘已生成: {viz_path}")

    # === 7. 生成 Word 深度分析报告 ===
    print(f"\n正在生成 Word 深度分析报告...")
    report_gen = ReportGenerator()
    docx_path = report_gen.generate_word_report(keyword, analysis, sales_data, sourcing_data, trend_data, viz_path)
    print(f"✅ Word 深度报告已生成: {docx_path}")

    # === 数据保存 ===
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = os.path.join("data", "reports")
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
        
    report_file = os.path.join(report_dir, f"TrendAnalysis_{safe_keyword}_{timestamp}.xlsx")
    
    with pd.ExcelWriter(report_file, engine='openpyxl') as writer:
        pd.DataFrame([analysis]).to_excel(writer, sheet_name='Summary', index=False)
        if sales_data:
            pd.DataFrame(sales_data).to_excel(writer, sheet_name='Sales', index=False)
        if sourcing_data:
            pd.DataFrame(sourcing_data).to_excel(writer, sheet_name='Sourcing', index=False)
        if trend_data:
            pd.DataFrame(trend_data).to_excel(writer, sheet_name='Trends_Kickstarter', index=False)
            
    print(f"\n✅ 趋势报告已生成: {report_file}")
    
    # 清理临时文件
    for filename in os.listdir("data"):
        if filename.endswith(".csv"):
            try:
                os.remove(os.path.join("data", filename))
            except:
                pass

if __name__ == "__main__":
    asyncio.run(main())
