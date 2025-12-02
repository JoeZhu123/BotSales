import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
import urllib.parse
from src.config import Config
import logging
import os

logger = logging.getLogger(__name__)

class Sourcer1688:
    """
    1688 找货器 (支持持久化登录)
    """
    def __init__(self):
        self.base_url = "https://s.1688.com/selloffer/offer_search.htm"
        # 设置用户数据目录，用于保存 Cookie 和登录状态
        self.user_data_dir = os.path.join(Config.DATA_DIR, "browser_data_1688")
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)
        
    async def search_source(self, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        encoded_keyword = urllib.parse.quote(keyword.encode('gbk'))
        
        async with async_playwright() as p:
            # 使用 launch_persistent_context 来保持登录状态
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=Config.HEADLESS_MODE, # 如果需要首次登录，请在配置中暂时改为 False
                args=['--disable-blink-features=AutomationControlled'],
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            try:
                logger.info(f"正在 1688 寻找货源: {keyword}")
                url = f"{self.base_url}?keywords={keyword}&n=y&netType=1%2C11%2C16"
                await page.goto(url, timeout=30000)
                
                # 检查是否被验证码拦截或需要登录
                title = await page.title()
                if "登录" in title or "验证" in title:
                    logger.warning("检测到可能需要登录或验证。如果是首次运行，请将 HEADLESS_MODE 设置为 False 并手动登录。")
                    # 这里可以加一个 input 等待用户手动操作，但在后台运行模式下不适用
                
                # 等待结果加载
                try:
                    await page.wait_for_load_state('networkidle', timeout=15000)
                    await page.wait_for_selector('.sm-offer-item, .offer-list-row-offer, .common-offer-card', timeout=10000)
                except:
                    logger.warning("等待商品列表超时，尝试直接解析...")

                # 尝试多种选择器兼容
                items = await page.query_selector_all('.sm-offer-item, .offer-list-row-offer, .common-offer-card, .offer-list-row')
                
                sources = []
                for item in items[:limit]:
                    try:
                        # 标题
                        title_el = await item.query_selector('.offer-title a, .title a, .offer-title')
                        title = await title_el.inner_text() if title_el else "Unknown"
                        
                        # 价格
                        price_el = await item.query_selector('.price, .offer-price')
                        price = await price_el.inner_text() if price_el else "N/A"
                        
                        # 供应商
                        company_el = await item.query_selector('.company-name a, .company-name')
                        company = await company_el.inner_text() if company_el else "Unknown Company"
                        
                        sources.append({
                            "platform": "1688",
                            "search_term": keyword,
                            "title": title.strip(),
                            "price": price.strip(),
                            "supplier": company.strip(),
                            "link": "https://s.1688.com" # 简化，实际需提取 href
                        })
                    except Exception as e:
                        continue
                        
                return sources
                
            except Exception as e:
                logger.error(f"1688 搜索出错: {e}")
                return []
            finally:
                await context.close()
