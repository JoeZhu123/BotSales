import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from src.crawlers.base_crawler import BaseCrawler
from src.config import Config
import urllib.parse
from fake_useragent import UserAgent

class KickstarterCrawler(BaseCrawler):
    def __init__(self):
        super().__init__("kickstarter")
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

    async def search_products(self, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        在 Kickstarter 搜索相关项目
        """
        await self._init_browser()
        page = await self.context.new_page()
        
        try:
            self.logger.info(f"正在 Kickstarter 探索创新项目: {keyword}")
            # Kickstarter 搜索 URL
            # sort=magic (推荐), sort=popularity (热门)
            url = f"https://www.kickstarter.com/discover/advanced?term={urllib.parse.quote(keyword)}&sort=popularity"
            await page.goto(url, timeout=60000)
            
            # 等待项目卡片加载
            try:
                await page.wait_for_selector('div.js-react-proj-card', timeout=15000)
            except:
                self.logger.warning("Kickstarter 加载超时或无结果")
            
            projects = []
            
            # 使用 JS 解析
            projects = await page.evaluate(f"""(limit) => {{
                const results = [];
                // 找到所有项目卡片
                const cards = document.querySelectorAll('div.js-react-proj-card');
                
                for (const card of cards) {{
                    if (results.length >= limit) break;
                    
                    try {{
                        // 提取标题
                        const titleEl = card.querySelector('h3 a, a.soft-black');
                        const title = titleEl ? titleEl.innerText : "Unknown";
                        const link = titleEl ? titleEl.href : "";
                        
                        // 提取简介 (Blurb)
                        const descEl = card.querySelector('p.type-12, p.type-13');
                        const description = descEl ? descEl.innerText : "";
                        
                        // 提取筹款进度
                        // pledged: class="type-12 type-13-md type-14-lg medium soft-black"
                        // backers: 
                        
                        // 尝试从 footer 或 stats 区域提取数据
                        // Kickstarter 的 class 经常变，尝试找特定文本
                        const text = card.innerText;
                        
                        // 提取筹款金额 ($12,345 pledged)
                        let pledged = "N/A";
                        const pledgedMatch = text.match(/([$€£¥][\\d,]+)\\s+pledged/i);
                        if (pledgedMatch) pledged = pledgedMatch[1];
                        
                        // 提取进度 (%)
                        let percent = "N/A";
                        const percentMatch = text.match(/(\\d+)%\\s+funded/);
                        if (percentMatch) percent = percentMatch[1] + "%";
                        
                        // 提取剩余天数
                        let days = "N/A";
                        const daysMatch = text.match(/(\\d+)\\s+days?\\s+to\\s+go/i);
                        if (daysMatch) days = daysMatch[1];
                        
                        if (title && link) {{
                            results.push({{
                                "platform": "Kickstarter",
                                "keyword": "",
                                "title": title,
                                "description": description,
                                "pledged": pledged,
                                "percent_funded": percent,
                                "days_to_go": days,
                                "link": link
                            }});
                        }}
                    }} catch (e) {{
                        continue;
                    }}
                }}
                return results;
            }}""", limit)
            
            for p in projects:
                p['keyword'] = keyword
            
            self.logger.info(f"成功抓取 {len(projects)} 个 Kickstarter 项目")
            return projects
            
        except Exception as e:
            self.logger.error(f"Kickstarter 抓取失败: {e}")
            return []
        finally:
            await page.close()

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """
        Kickstarter 详情页抓取（暂未实现）
        """
        return {}

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

