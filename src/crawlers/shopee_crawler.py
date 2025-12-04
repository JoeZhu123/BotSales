import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from src.crawlers.base_crawler import BaseCrawler
from src.config import Config
import urllib.parse

class ShopeeCrawler(BaseCrawler):
    def __init__(self, region: str = "my"):
        """
        :param region: 地区后缀, e.g., 'my' (马来西亚), 'sg' (新加坡), 'tw' (台湾)
        """
        super().__init__("shopee")
        self.region = region
        self.base_url = f"https://shopee.{region}"
        self.browser = None
        self.context = None
        self.playwright = None

    async def _init_browser(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=Config.HEADLESS_MODE,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

    async def search_products(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        await self._init_browser()
        page = await self.context.new_page()
        
        try:
            self.logger.info(f"正在 Shopee ({self.region}) 搜索: {keyword}")
            encoded_kw = urllib.parse.quote(keyword)
            url = f"{self.base_url}/search?keyword={encoded_kw}"
            
            await page.goto(url, timeout=60000)
            
            # Shopee 搜索结果列表选择器
            # 这是一个动态类名，通常包含 'shopee-search-item-result__item'
            await page.wait_for_selector('div[data-sqe="item"]', timeout=20000)
            
            products = []
            items = await page.query_selector_all('div[data-sqe="item"]')
            
            for item in items[:limit]:
                try:
                    # 提取标题
                    # 这里的 selector 需要根据实际 Shopee DOM 调整
                    title_el = await item.query_selector('div[data-sqe="name"] > div')
                    title = await title_el.inner_text() if title_el else "Unknown"
                    
                    # 提取价格
                    price_el = await item.query_selector('span[class*="_24JoLh"]') # 示例混淆类名
                    if not price_el:
                        # 尝试通用结构
                        price_el = await item.query_selector('div > span:nth-child(2)')
                    
                    price = await price_el.inner_text() if price_el else "N/A"
                    
                    # 提取销量 (e.g., "1.2k sold")
                    sold_el = await item.query_selector('div:has-text("sold")') 
                    sold = await sold_el.inner_text() if sold_el else "0"
                    
                    # 链接
                    link_el = await item.query_selector('a')
                    link = await link_el.get_attribute('href') if link_el else ""
                    
                    products.append({
                        "platform": f"Shopee-{self.region}",
                        "keyword": keyword,
                        "title": title,
                        "price": price,
                        "sold": sold,
                        "link": f"{self.base_url}{link}"
                    })
                except Exception as e:
                    continue
            
            self.logger.info(f"成功抓取 {len(products)} 个 Shopee 商品")
            return products
            
        except Exception as e:
            self.logger.error(f"Shopee 抓取失败: {e}")
            return []
        finally:
            await page.close()

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

