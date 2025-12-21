import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from src.crawlers.base_crawler import BaseCrawler
from src.config import Config
import urllib.parse
from fake_useragent import UserAgent
from playwright_stealth import Stealth
import random

class TikTokCrawler(BaseCrawler):
    def __init__(self):
        super().__init__("tiktok")
        self.browser = None
        self.context = None
        self.playwright = None
        self.ua = UserAgent()

    async def _init_browser(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=Config.HEADLESS_MODE,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.ua.random,
                locale='en-US'
            )

    async def get_trending_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        接入 TikTok Creative Center 获取实时爆品数据
        """
        await self._init_browser()
        page = await self.context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        try:
            self.logger.info("正在通过 TikTok Creative Center 获取实时爆品...")
            # 访问 TikTok 爆品榜单 (最近7天)
            url = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/pc/en?period=7"
            await page.goto(url, timeout=60000)
            
            # 等待内容加载
            try:
                await page.wait_for_selector('div[class*="ItemCard"]', timeout=30000)
            except:
                self.logger.warning("TikTok 爆品榜单加载超时，可能需要手动处理验证或登录。")
                if not Config.HEADLESS_MODE:
                    await asyncio.sleep(60)

            # 解析爆品数据
            products = await page.evaluate(f"""(limit) => {{
                const results = [];
                const cards = document.querySelectorAll('div[class*="ItemCard"]');
                
                for (const card of cards) {{
                    if (results.length >= limit) break;
                    
                    const titleEl = card.querySelector('span[class*="ProductName"]');
                    const title = titleEl ? titleEl.innerText : "Unknown Product";
                    
                    const rankingEl = card.querySelector('div[class*="RankNumber"]');
                    const ranking = rankingEl ? rankingEl.innerText : "N/A";
                    
                    const indexEl = card.querySelector('span[class*="IndexNumber"]');
                    const hotIndex = indexEl ? indexEl.innerText : "N/A";
                    
                    results.push({{
                        "platform": "TikTok Shop (Trending)",
                        "title": title.strip(),
                        "ranking": ranking,
                        "hot_index": hotIndex,
                        "link": window.location.href
                    }});
                }}
                return results;
            }}""", limit)
            
            self.logger.info(f"成功获取 {len(products)} 个 TikTok 实时爆品")
            return products
            
        except Exception as e:
            self.logger.error(f"TikTok 爆品获取失败: {e}")
            return []
        finally:
            await page.close()

    async def search_products(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        在 TikTok Shop 搜索特定关键词的商品
        """
        await self._init_browser()
        page = await self.context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        try:
            self.logger.info(f"正在 TikTok Shop 搜索关键词: {keyword}")
            encoded_kw = urllib.parse.quote(keyword)
            url = f"https://www.tiktok.com/search/shop?q={encoded_kw}"
            await page.goto(url, timeout=60000)
            
            # 检测并关闭可能的弹窗
            try:
                close_btn = await page.query_selector('button[data-e2e="modal-close-icon"]')
                if close_btn: await close_btn.click()
            except: pass

            # 等待加载
            try:
                await page.wait_for_selector('div[data-e2e="shop-item"]', timeout=30000)
            except:
                self.logger.warning("TikTok Shop 搜索结果加载超时。")
            
            # 解析搜索结果
            products = await page.evaluate(f"""(limit) => {{
                const results = [];
                const items = document.querySelectorAll('div[data-e2e="shop-item"]');
                
                for (const item of items) {{
                    if (results.length >= limit) break;
                    
                    const titleEl = item.querySelector('h3');
                    const priceEl = item.querySelector('div[class*="price"]');
                    const soldEl = item.querySelector('span[class*="sold"]');
                    const linkEl = item.querySelector('a');
                    
                    results.push({{
                        "platform": "TikTok Shop",
                        "title": titleEl ? titleEl.innerText.trim() : "Unknown",
                        "price": priceEl ? priceEl.innerText.trim() : "N/A",
                        "sold": soldEl ? soldEl.innerText.trim() : "0",
                        "link": linkEl ? linkEl.href : ""
                    }});
                }}
                return results;
            }}""", limit)
            
            for p in products: p['keyword'] = keyword
            self.logger.info(f"TikTok Shop 搜索完成，找到 {len(products)} 个商品")
            return products
            
        except Exception as e:
            self.logger.error(f"TikTok Shop 搜索失败: {e}")
            return []
        finally:
            await page.close()

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """
        获取 TikTok 商品详情 (目前作为 BaseCrawler 的抽象方法实现占位)
        """
        return {}

    async def close(self):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
