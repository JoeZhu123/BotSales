import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from src.crawlers.base_crawler import BaseCrawler
from src.config import Config
import urllib.parse
from fake_useragent import UserAgent

class AliExpressCrawler(BaseCrawler):
    def __init__(self):
        super().__init__("aliexpress")
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
            # 设置 Cookie 以固定为 美国/英语/美元
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.ua.random,
                locale='en-US'
            )
            # 预注入 Cookie (aep_usuc_f 是速卖通控制地区语言的关键 Cookie)
            # region=US, site=glo, b_locale=en_US, c_tp=USD
            await self.context.add_cookies([{
                "name": "aep_usuc_f",
                "value": "region=US&site=glo&b_locale=en_US&c_tp=USD",
                "domain": ".aliexpress.com",
                "path": "/"
            }])

    async def search_products(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        await self._init_browser()
        page = await self.context.new_page()
        
        try:
            self.logger.info(f"正在 AliExpress 搜索: {keyword}")
            # 使用速卖通搜索接口
            url = f"https://www.aliexpress.com/wholesale?SearchText={urllib.parse.quote(keyword)}"
            await page.goto(url, timeout=60000)
            
            # 等待商品列表 (速卖通的结构经常变，通常是大容器 list--gallery--...)
            try:
                await page.wait_for_selector('div[class*="list--gallery"]', timeout=20000)
            except:
                self.logger.warning("AliExpress 页面加载可能超时或遇到滑块。")
                
            # 滚动页面以触发懒加载
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(2)

            products = []
            # 查找商品卡片 (尝试通用选择器)
            # 通常是 <a> 标签包裹着商品信息
            cards = await page.query_selector_all('a[class*="manhattan--container"], div[class*="search-item-card-wrapper-gallery"] a')
            
            if not cards:
                 # 备用选择器：有时候是 div 结构
                 cards = await page.query_selector_all('div.list--gallery--34Vad4b > a') # 这种 hash class 容易失效，仅作示例

            # 使用 JS 解析更稳健
            products = await page.evaluate(f"""(limit) => {{
                const results = [];
                // 查找所有明显是商品卡片的容器
                // 特征：包含图片、有价格符号、有销量
                const candidates = document.querySelectorAll('a[href*="/item/"]');
                
                for (const card of candidates) {{
                    if (results.length >= limit) break;
                    
                    const text = card.innerText;
                    // 必须包含价格
                    if (!text.includes('$') && !text.includes('US $')) continue;
                    
                    // 提取标题
                    let title = "";
                    const titleEl = card.querySelector('h1, h3, div[class*="title"]');
                    if (titleEl) title = titleEl.innerText;
                    else title = card.innerText.split('\\n')[0]; // 盲猜第一行是标题
                    
                    // 提取价格
                    let price = "N/A";
                    const priceMatch = text.match(/US\\s*\\$\\s*([\\d\\.]+)/);
                    if (priceMatch) price = priceMatch[1];
                    
                    // 提取销量
                    let sold = "0";
                    const soldMatch = text.match(/(\\d+[\\d\\.]*\\w*)\\s+sold/i);
                    if (soldMatch) sold = soldMatch[1];
                    
                    if (title && price !== "N/A") {{
                        results.push({{
                            "platform": "AliExpress",
                            "keyword": "",
                            "title": title,
                            "price": price,
                            "sold": sold,
                            "link": card.href
                        }});
                    }}
                }}
                return results;
            }}""", limit)
            
            for p in products:
                p['keyword'] = keyword
            
            self.logger.info(f"成功抓取 {len(products)} 个 AliExpress 商品")
            return products
            
        except Exception as e:
            self.logger.error(f"AliExpress 抓取失败: {e}")
            return []
        finally:
            await page.close()

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """
        速卖通详情页抓取（暂未实现）
        """
        return {}

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

