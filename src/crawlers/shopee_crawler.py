import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from src.crawlers.base_crawler import BaseCrawler
from src.config import Config
import urllib.parse
from fake_useragent import UserAgent
from playwright_stealth import Stealth

class ShopeeCrawler(BaseCrawler):
    def __init__(self, region: str = "com.my"):
        super().__init__(f"shopee_{region}")
        self.region = region
        self.base_url = f"https://shopee.{region}"
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
                viewport={'width': 1280, 'height': 800},
                user_agent=self.ua.random
            )

    async def search_products(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        await self._init_browser()
        page = await self.context.new_page()
        
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        try:
            self.logger.info(f"正在 Shopee({self.region}) 搜索: {keyword}")
            # Shopee 搜索 URL
            url = f"{self.base_url}/search?keyword={urllib.parse.quote(keyword)}"
            await page.goto(url, timeout=60000)
            
            # --- 处理可能的语言选择弹窗 ---
            try:
                # 尝试点击 English 按钮 (常见于 Shopee 弹窗)
                lang_btn = await page.query_selector('button:has-text("English")')
                if lang_btn: await lang_btn.click()
            except: pass

            # --- 检测验证码 ---
            async def check_captcha():
                content = await page.content()
                if "captcha" in content.lower() or "verify" in content.lower():
                    self.logger.warning("⚠️ 检测到 Shopee 验证拦截！请在 60 秒内手动完成。")
                    if not Config.HEADLESS_MODE:
                        await asyncio.sleep(60)
            
            await check_captcha()

            # 等待列表加载
            try:
                await page.wait_for_selector('div.shopee-search-item-result__items, a[data-sqe="link"]', timeout=30000)
            except:
                self.logger.warning("Shopee 加载超时，尝试截图...")
                await page.screenshot(path="data/reports/shopee_debug.png")

            # 滚动加载
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(2)

            # 解析逻辑
            products = await page.evaluate(f"""(limit) => {{
                const results = [];
                const items = document.querySelectorAll('a[data-sqe="link"]');
                
                for (const item of items) {{
                    if (results.length >= limit) break;
                    
                    let title = "";
                    const titleEl = item.querySelector('div[data-sqe="name"]');
                    if (titleEl) title = titleEl.innerText;
                    
                    let price = "N/A";
                    const priceEl = item.querySelector('div.shopee-item-card__current-price, span._2v09_B');
                    if (priceEl) price = priceEl.innerText;
                    
                    // 如果没找到，尝试在整个内容中找数字
                    if (price === "N/A") {{
                        const text = item.innerText;
                        const match = text.match(/[\\d\\.,]+/);
                        if (match) price = match[0];
                    }}

                    let sold = "0";
                    const soldEl = item.querySelector('div.shopee-item-card__sold-count, div.Znr67M');
                    if (soldEl) sold = soldEl.innerText;

                    results.push({{
                        "platform": "Shopee",
                        "title": title.trim(),
                        "price": price,
                        "sold": sold,
                        "link": item.href
                    }});
                }}
                return results;
            }}""", limit)
            
            for p in products:
                p['keyword'] = keyword
            
            self.logger.info(f"成功抓取 {len(products)} 个 Shopee 商品")
            return products
            
        except Exception as e:
            self.logger.error(f"Shopee 抓取失败: {e}")
            return []
        finally:
            await page.close()

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        return {}

    async def close(self):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
