import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page
from src.crawlers.base_crawler import BaseCrawler
from src.config import Config
import random
from fake_useragent import UserAgent

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
        
        try:
            self.logger.info(f"正在亚马逊搜索: {keyword}")
            # 访问亚马逊搜索页
            await page.goto(f"https://www.amazon.com/s?k={keyword}", timeout=60000)
            
            # 等待商品列表加载
            try:
                await page.wait_for_selector('div[data-component-type="s-search-result"]', timeout=30000)
            except Exception:
                self.logger.warning("Amazon 页面加载可能超时或出现验证码")
                # 截图调试
                # await page.screenshot(path="debug_amazon_fail.png")
            
            products = []
            results = await page.query_selector_all('div[data-component-type="s-search-result"]')
            
            for item in results[:limit]:
                try:
                    # 提取标题
                    title_el = await item.query_selector('h2 span')
                    title = await title_el.inner_text() if title_el else "Unknown Title"
                    
                    # 提取价格 (优化版 - 增强兼容性)
                    price = "N/A"
                    # 策略1: 标准价格块
                    price_el = await item.query_selector('.a-price .a-offscreen')
                    if price_el:
                        price = await price_el.inner_text()
                    
                    # 策略2: 分段价格 (当策略1获取到的是隐藏文本时，可能需要这个)
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
                    rating_el = await item.query_selector('span[aria-label*="out of 5 stars"]') # 策略1
                    if rating_el:
                        rating = await rating_el.get_attribute('aria-label')
                    else:
                        # 策略2: 尝试查找 class="a-icon-alt"
                        rating_alt = await item.query_selector('i.a-icon-star-small span.a-icon-alt')
                        if rating_alt:
                            rating = await rating_alt.inner_text()

                    # 提取评论数 (新增)
                    reviews = "0"
                    reviews_el = await item.query_selector('span[aria-label*="ratings"]') # 有时是 ratings
                    if not reviews_el:
                         # 尝试查找链接文本，通常评论数在评分旁边
                        reviews_link = await item.query_selector('div[data-cy="reviews-block"] a span.a-size-base')
                        if reviews_link:
                            reviews = await reviews_link.inner_text()
                    else:
                        reviews = await reviews_el.get_attribute('aria-label')
                    
                    # 提取图片
                    img_el = await item.query_selector('img.s-image')
                    img_url = await img_el.get_attribute('src') if img_el else ""
                    
                    products.append({
                        "platform": "Amazon",
                        "keyword": keyword,
                        "title": title,
                        "price": price,
                        "rating": rating,
                        "reviews_count": reviews, # 新增字段
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
