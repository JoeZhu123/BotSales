import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page
from src.crawlers.base_crawler import BaseCrawler
from src.config import Config
import random

class AmazonCrawler(BaseCrawler):
    def __init__(self):
        super().__init__("amazon")
        self.browser = None
        self.context = None
        self.playwright = None

    async def _init_browser(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            # 启动浏览器，headless=False 可以看到浏览器操作，方便调试
            # 在服务器上运行时建议设置为 True
            self.browser = await self.playwright.chromium.launch(
                headless=Config.HEADLESS_MODE,
                args=['--disable-blink-features=AutomationControlled'] # 简单的反爬绕过
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

    async def search_products(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        await self._init_browser()
        page = await self.context.new_page()
        
        try:
            self.logger.info(f"正在亚马逊搜索: {keyword}")
            # 访问亚马逊搜索页
            await page.goto(f"https://www.amazon.com/s?k={keyword}", timeout=60000)
            
            # 等待商品列表加载
            await page.wait_for_selector('div[data-component-type="s-search-result"]', timeout=30000)
            
            products = []
            results = await page.query_selector_all('div[data-component-type="s-search-result"]')
            
            for item in results[:limit]:
                try:
                    # 提取标题
                    title_el = await item.query_selector('h2 span')
                    title = await title_el.inner_text() if title_el else "Unknown Title"
                    
                    # 提取价格 (优化版)
                    # 尝试多种价格选择器
                    price = "N/A"
                    price_el = await item.query_selector('.a-price .a-offscreen')
                    if price_el:
                        price = await price_el.inner_text()
                    else:
                         # 备用：分段价格
                        price_whole = await item.query_selector('.a-price-whole')
                        price_fraction = await item.query_selector('.a-price-fraction')
                        if price_whole and price_fraction:
                            price = f"${await price_whole.inner_text()}.{await price_fraction.inner_text()}"

                        
                    # 提取 ASIN
                    asin = await item.get_attribute('data-asin')
                    
                    # 提取评分
                    rating_el = await item.query_selector('span[aria-label*="out of 5 stars"]')
                    rating = await rating_el.get_attribute('aria-label') if rating_el else "N/A"
                    
                    # 提取图片
                    img_el = await item.query_selector('img.s-image')
                    img_url = await img_el.get_attribute('src') if img_el else ""
                    
                    products.append({
                        "platform": "Amazon",
                        "keyword": keyword,
                        "title": title,
                        "price": price,
                        "rating": rating,
                        "asin": asin,
                        "image_url": img_url,
                        "product_url": f"https://www.amazon.com/dp/{asin}" if asin else ""
                    })
                    
                except Exception as e:
                    self.logger.error(f"解析单个商品出错: {e}")
                    continue
            
            self.logger.info(f"成功抓取 {len(products)} 个商品")
            return products
            
        except Exception as e:
            self.logger.error(f"Amazon 抓取失败: {e}")
            return []
        finally:
            await page.close()

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        # 暂未实现详细页抓取
        return {}

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

