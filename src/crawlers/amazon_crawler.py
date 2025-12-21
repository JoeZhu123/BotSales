import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page
from src.crawlers.base_crawler import BaseCrawler
from src.config import Config
import random
from fake_useragent import UserAgent
from playwright_stealth import Stealth

class AmazonCrawler(BaseCrawler):
    def __init__(self):
        super().__init__("amazon")
        self.browser = None
        self.context = None
        self.playwright = None
        self.ua = UserAgent()

    async def _init_browser(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            
            # 随机 User-Agent
            user_agent = self.ua.random
            self.logger.info(f"使用 User-Agent: {user_agent}")
            
            self.browser = await self.playwright.chromium.launch(
                headless=Config.HEADLESS_MODE,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=user_agent
            )

    async def search_products(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        await self._init_browser()
        page = await self.context.new_page()
        
        # 应用 Stealth 插件，隐藏自动化特征
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        try:
            self.logger.info(f"正在亚马逊搜索: {keyword}")
            # 访问亚马逊搜索页
            await page.goto(f"https://www.amazon.com/s?k={keyword}", timeout=60000)
            
            # --- 检测验证码 ---
            async def check_captcha():
                title = await page.title()
                content = await page.content()
                if "Robot Check" in title or "Captcha" in title or "验证码" in title or "sp-cc-container" in content:
                    self.logger.warning("⚠️ 检测到亚马逊验证码/拦截！请在浏览器中手动完成验证。")
                    if not Config.HEADLESS_MODE:
                        # 循环检查直到验证码消失或超时
                        for _ in range(60):
                            await asyncio.sleep(1)
                            new_title = await page.title()
                            if "Robot Check" not in new_title and "Captcha" not in new_title:
                                self.logger.info("✅ 验证码已处理。")
                                return True
                        return False
                return True

            await check_captcha()

            # 等待商品列表加载
            try:
                # Amazon 的选择器可能因地区不同而异
                await page.wait_for_selector('div[data-component-type="s-search-result"], .s-result-item, [data-asin]', timeout=20000)
            except Exception:
                self.logger.warning("Amazon 页面加载超时，尝试最后一次人工介入机会...")
                await check_captcha()
                # 截图方便排查
                await page.screenshot(path="data/reports/amazon_debug.png")
            
            products = []
            results = await page.query_selector_all('div[data-component-type="s-search-result"]')
            
            if not results:
                # 尝试更宽泛的选择器
                results = await page.query_selector_all('.s-result-item[data-asin]')

            for item in results[:limit]:
                try:
                    # 提取标题
                    title_el = await item.query_selector('h2 span')
                    title = await title_el.inner_text() if title_el else "Unknown Title"
                    
                    # 提取价格 (优化版 - 增强兼容性)
                    price = "N/A"
                    price_el = await item.query_selector('.a-price .a-offscreen')
                    if price_el:
                        price = await price_el.inner_text()
                    
                    if price == "N/A" or not price:
                        price_whole = await item.query_selector('.a-price-whole')
                        price_fraction = await item.query_selector('.a-price-fraction')
                        if price_whole:
                            whole = await price_whole.inner_text()
                            frac = await price_fraction.inner_text() if price_fraction else "00"
                            price = f"${whole}.{frac}"
                            
                    # 提取 ASIN
                    asin = await item.get_attribute('data-asin')
                    
                    # 提取评分
                    rating = "N/A"
                    rating_el = await item.query_selector('span[aria-label*="out of 5 stars"]')
                    if rating_el:
                        rating = await rating_el.get_attribute('aria-label')

                    # 提取评论数
                    reviews = "0"
                    reviews_el = await item.query_selector('span[aria-label*="ratings"], a .a-size-base')
                    if reviews_el:
                        reviews = await reviews_el.inner_text()
                    
                    # 提取图片
                    img_el = await item.query_selector('img.s-image')
                    img_url = await img_el.get_attribute('src') if img_el else ""
                    
                    products.append({
                        "platform": "Amazon",
                        "keyword": keyword,
                        "title": title.strip(),
                        "price": price.strip(),
                        "rating": rating,
                        "reviews_count": reviews,
                        "asin": asin,
                        "image_url": img_url,
                        "product_url": f"https://www.amazon.com/dp/{asin}" if asin else ""
                    })
                    
                except Exception as e:
                    continue
            
            self.logger.info(f"成功抓取 {len(products)} 个 Amazon 商品")
            return products
            
        except Exception as e:
            self.logger.error(f"Amazon 抓取失败: {e}")
            return []
        finally:
            await page.close()

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        return {}

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
