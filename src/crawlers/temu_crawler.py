import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from src.crawlers.base_crawler import BaseCrawler
from src.config import Config
import urllib.parse
from fake_useragent import UserAgent
from playwright_stealth import Stealth

class TemuCrawler(BaseCrawler):
    def __init__(self):
        super().__init__("temu")
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
            # Temu 建议模拟移动端或大屏桌面
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent=self.ua.random,
                locale='en-US'
            )

    async def search_products(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        await self._init_browser()
        page = await self.context.new_page()
        
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        try:
            self.logger.info(f"正在 Temu 搜索: {keyword}")
            # Temu 搜索 URL
            url = f"https://www.temu.com/search_result.html?search_key={urllib.parse.quote(keyword)}"
            await page.goto(url, timeout=60000)
            
            # --- 检测拦截 ---
            async def check_interception():
                title = await page.title()
                content = await page.content()
                if "Security" in title or "Verification" in title or "Robot" in content or "验证" in content:
                    self.logger.warning("⚠️ 检测到 Temu 验证拦截！请在 60 秒内手动完成。")
                    if not Config.HEADLESS_MODE:
                        for _ in range(60):
                            await asyncio.sleep(1)
                            new_content = await page.content()
                            if "Robot" not in new_content:
                                self.logger.info("✅ 验证已完成。")
                                return True
                        return False
                return True

            await check_interception()

            # 等待商品加载
            try:
                # Temu 使用很多 div 嵌套
                await page.wait_for_selector('div[id*="goods_list"], a[href*="goods_id"]', timeout=20000)
            except:
                self.logger.warning("Temu 加载超时，尝试人工介入...")
                await check_interception()
                await page.screenshot(path="data/reports/temu_debug.png")

            # 模拟滚动以触发懒加载
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(1)

            # 强力 JS 解析
            products = await page.evaluate(f"""(limit) => {{
                const results = [];
                const cards = document.querySelectorAll('a[href*="goods_id"]');
                
                for (const card of cards) {{
                    if (results.length >= limit) break;
                    
                    const text = card.innerText;
                    // Temu 价格通常包含 $
                    if (!text.includes('$')) continue;
                    
                    let title = "";
                    const titleEl = card.querySelector('div[class*="title"], span[class*="name"]');
                    if (titleEl) title = titleEl.innerText;
                    
                    let price = "N/A";
                    const priceMatch = text.match(/\\$\\s*([\\d\\.,]+)/);
                    if (priceMatch) price = priceMatch[1];
                    
                    let sold = "0";
                    const soldMatch = text.match(/([\\d\\.,]+K?)\\+?\\s+sold/i);
                    if (soldMatch) sold = soldMatch[1];
                    
                    const link = card.href;
                    if (!results.find(r => r.link === link)) {{
                        results.push({{
                            "platform": "Temu",
                            "title": title.trim(),
                            "price": price,
                            "sold": sold,
                            "link": link
                        }});
                    }}
                }}
                return results;
            }}""", limit)
            
            for p in products:
                p['keyword'] = keyword
            
            self.logger.info(f"成功抓取 {len(products)} 个 Temu 商品")
            return products
            
        except Exception as e:
            self.logger.error(f"Temu 抓取失败: {e}")
            return []
        finally:
            await page.close()

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        return {}

    async def close(self):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()

