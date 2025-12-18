import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
import urllib.parse
from src.config import Config
import logging
import os

logger = logging.getLogger(__name__)

class SourcerYiwuGo:
    """
    义乌购找货器
    """
    def __init__(self):
        self.base_url = "https://www.yiwugo.com/search/s.html"
        # 义乌购可能也需要 Cookie，但通常匿名搜索较宽松
        
    async def search_source(self, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=Config.HEADLESS_MODE,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                logger.info(f"正在 义乌购 寻找货源: {keyword}")
                # 义乌购搜索 URL 格式
                url = f"{self.base_url}?q={urllib.parse.quote(keyword)}"
                await page.goto(url, timeout=30000)
                
                # 等待商品列表
                # 义乌购商品项通常是 li.pro_item 或 div.product_list
                try:
                    await page.wait_for_selector('.pro_list_product_img, .pro_item', timeout=10000)
                except:
                    logger.warning("义乌购加载超时或无结果")
                    
                items = await page.query_selector_all('.pro_item')
                
                sources = []
                for item in items[:limit]:
                    try:
                        # 标题
                        title_el = await item.query_selector('.product_title a')
                        title = await title_el.get_attribute('title') if title_el else "Unknown"
                        
                        # 价格 (义乌购价格通常是范围，或者是 "¥12.5")
                        price_el = await item.query_selector('.pri-num em, .pri_price')
                        price = await price_el.inner_text() if price_el else "N/A"
                        
                        # 供应商
                        company_el = await item.query_selector('.shop_name a, .company_name')
                        company = await company_el.inner_text() if company_el else "Unknown Shop"
                        
                        # 链接
                        link_el = await item.query_selector('.product_title a')
                        link = await link_el.get_attribute('href') if link_el else ""
                        if link and not link.startswith('http'):
                            link = f"https://www.yiwugo.com{link}"
                            
                        sources.append({
                            "platform": "YiwuGo",
                            "search_term": keyword,
                            "title": title.strip(),
                            "price": price.strip(),
                            "supplier": company.strip(),
                            "link": link
                        })
                    except Exception as e:
                        continue
                        
                logger.info(f"成功在义乌购找到 {len(sources)} 个货源")
                return sources
                
            except Exception as e:
                logger.error(f"义乌购 搜索出错: {e}")
                return []
            finally:
                await browser.close()

