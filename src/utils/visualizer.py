import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
from typing import List, Dict
import matplotlib.font_manager as fm

class DataVisualizer:
    def __init__(self, output_dir: str = "data/reports"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # 优化中文中文字体加载逻辑
        self._setup_chinese_font()
        plt.rcParams['axes.unicode_minus'] = False
        sns.set_theme(style="whitegrid", font=plt.rcParams['font.sans-serif'][0])

    def _setup_chinese_font(self):
        """
        根据操作系统自动选择并设置可用的中文中文字体
        """
        # 常见中文中文字体列表
        font_names = [
            'Microsoft YaHei',  # Windows 微软雅黑
            'SimHei',           # Windows 黑体
            'SimSun',           # Windows 宋体
            'PingFang SC',      # macOS 萍方
            'Arial Unicode MS', # 通用
            'STHeiti',          # 华文黑体
            'WenQuanYi Micro Hei' # Linux 文泉驿
        ]
        
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        chosen_font = None
        
        for font in font_names:
            if font in available_fonts:
                chosen_font = font
                break
        
        if chosen_font:
            plt.rcParams['font.sans-serif'] = [chosen_font] + plt.rcParams['font.sans-serif']
            print(f"✅ 已成功加载中文字体: {chosen_font}")
        else:
            print("⚠️ 未能在系统中找到预设的中文字体，图表中的中文可能显示为方块。")

    def generate_dashboard(self, keyword: str, analysis: Dict, sales_data: List[Dict], sourcing_data: List[Dict], trend_data: List[Dict] = []):
        """
        生成综合数据仪表盘图片
        """
        # 创建一个包含多个子图的大图
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle(f"选品趋势深度分析仪表盘 - 关键词: {keyword}", fontsize=20, fontweight='bold')

        # 1. 价格对比图 (左上)
        ax1 = fig.add_subplot(2, 2, 1)
        self._plot_price_comparison(ax1, sales_data, sourcing_data)

        # 2. 利润预估 (右上)
        ax2 = fig.add_subplot(2, 2, 2)
        self._plot_profit_margin(ax2, analysis)

        # 3. 创新趋势/众筹额 (左下)
        ax3 = fig.add_subplot(2, 2, 3)
        self._plot_trends(ax3, trend_data)

        # 4. 文本摘要 (右下)
        ax4 = fig.add_subplot(2, 2, 4)
        self._plot_summary_text(ax4, analysis)

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # 保存图片
        output_path = os.path.join(self.output_dir, f"Dashboard_{keyword}.png")
        plt.savefig(output_path, dpi=300)
        plt.close()
        return output_path

    def _plot_price_comparison(self, ax, sales_data, sourcing_data):
        # 准备数据
        plot_data = []
        for d in sales_data:
            try:
                price = float(str(d.get('price', '0')).replace('$', '').replace('¥', '').replace(',', ''))
                if d['platform'] == 'Amazon': price *= 7.2 # 粗略换算为人民币
                plot_data.append({"平台": d['platform'], "价格(RMB)": price})
            except: continue
        
        for d in sourcing_data:
            try:
                price = float(str(d.get('price', '0')).replace('¥', '').replace(',', ''))
                plot_data.append({"平台": d['platform'], "价格(RMB)": price})
            except: continue

        if plot_data:
            df = pd.DataFrame(plot_data)
            sns.barplot(data=df, x="平台", y="价格(RMB)", ax=ax, palette="viridis")
            ax.set_title("各平台价格对比 (换算为RMB)", fontsize=14)
        else:
            ax.text(0.5, 0.5, "价格数据不足", ha='center')

    def _plot_profit_margin(self, ax, analysis):
        # 饼图展示毛利率
        try:
            margin_str = analysis.get('estimated_margin', '0%').replace('%', '')
            margin = float(margin_str)
            costs = [margin, 100 - margin]
            labels = ['预估毛利', '成本/运营']
            colors = ['#2ecc71', '#e74c3c']
            ax.pie(costs, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors, explode=(0.1, 0))
            ax.set_title("预估利润空间分析", fontsize=14)
        except:
            ax.text(0.5, 0.5, "利润数据错误", ha='center')

    def _plot_trends(self, ax, trend_data):
        if not trend_data:
            ax.text(0.5, 0.5, "未发现 Kickstarter 众筹趋势数据", ha='center', fontsize=12)
            ax.set_title("创新趋势分析", fontsize=14)
            return

        # 展示众筹金额前5的项目
        plot_data = []
        for d in trend_data:
            try:
                pledged = float(str(d.get('pledged', '0')).replace('$', '').replace(',', '').replace('€', '').replace('£', ''))
                plot_data.append({"项目": d['title'][:15] + "...", "已筹金额($)": pledged})
            except: continue
        
        if plot_data:
            df = pd.DataFrame(plot_data).sort_values("已筹金额($)", ascending=False)
            sns.barplot(data=df, x="已筹金额($)", y="项目", ax=ax, palette="rocket")
            ax.set_title("Kickstarter 相关项目热度", fontsize=14)
        else:
            ax.text(0.5, 0.5, "众筹金额数据解析失败", ha='center')

    def _plot_summary_text(self, ax, analysis):
        ax.axis('off')
        summary_text = (
            f"【系统建议】: {analysis.get('recommendation', 'N/A')}\n\n"
            f"【Amazon均价】: ${analysis.get('avg_amazon_price_usd', 0)}\n"
            f"【国内采购均价】: ¥{analysis.get('avg_sourcing_price_cny', 0)}\n\n"
            f"【AI 点评摘要】:\n"
            f"{analysis.get('ai_analysis', '')[:300]}..."
        )
        ax.text(0.05, 0.95, summary_text, transform=ax.transAxes, fontsize=11, 
                verticalalignment='top', wrap=True, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
        ax.set_title("核心结论摘要", fontsize=14)

