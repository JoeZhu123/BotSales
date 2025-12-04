import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright, TimeoutError
import urllib.parse
from src.config import Config
import logging
import os

logger = logging.getLogger(__name__)

class Sourcer1688:
    """
    1688 找货器 (支持持久化登录)
    """
    def __init__(self):
        self.base_url = "https://www.1688.com/"
        self.user_data_dir = os.path.join(Config.DATA_DIR, "browser_data_1688")
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)
            
    async def _safe_screenshot(self, page, filename):
        """安全截图，防止因浏览器关闭而崩溃"""
        try:
            if not page.is_closed():
                await page.screenshot(path=filename)
        except Exception as e:
            logger.warning(f"截图失败 ({filename}): {e}")

    async def search_source(self, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        async with async_playwright() as p:
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=Config.HEADLESS_MODE,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--start-maximized',
                        '--no-sandbox'
                    ],
                    viewport=None,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
            except Exception as e:
                logger.error(f"启动浏览器失败: {e}")
                return []
            
            page = await context.new_page()
            
            try:
                logger.info(f"正在 1688 寻找货源: {keyword}")
                
                try:
                    await page.goto("https://www.1688.com/", timeout=60000)
                except Exception as e:
                    logger.warning(f"打开首页超时: {e}")

                # 人工介入检测
                if not Config.HEADLESS_MODE:
                    title = await page.title()
                    if "验证" in title or "安全" in title or "登录" in title:
                        logger.warning(">>> 检测到拦截，请在 60秒 内手动完成验证！<<<")
                        await asyncio.sleep(60)

                # 搜索流程
                try:
                    search_input = await page.wait_for_selector('#alisearch-keywords, .search-input-input, input[name="keywords"]', timeout=10000)
                    if search_input:
                        await search_input.click()
                        await search_input.fill(keyword)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press('Enter')
                    else:
                        raise Exception("Search input not found")
                except Exception as e:
                    logger.warning(f"首页搜索框未找到，尝试跳转 URL...")
                    url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={urllib.parse.quote(keyword)}"
                    await page.goto(url)

                if not Config.HEADLESS_MODE:
                    await asyncio.sleep(3) # 等待页面加载

                # -------------------------------------------------------
                # 改进后的 JS 解析逻辑 (基于 debug 结果优化)
                # -------------------------------------------------------
                logger.info("开始解析商品数据...")
                sources = await page.evaluate(f"""(limit) => {{
                    const results = [];
                    // 1. 找到所有包含图片的链接 (这通常是商品的主图)
                    const links = Array.from(document.querySelectorAll('a'));
                    
                    for (const link of links) {{
                        if (results.length >= limit) break;
                        
                        // 过滤条件：必须有子图片，且可见高度足够（避免小图标）
                        const img = link.querySelector('img');
                        if (!img || link.offsetHeight < 50) continue;
                        
                        // 2. 以这个链接为基准，向上寻找“商品卡片容器”
                        // 并在容器内寻找标题和价格
                        let container = link.parentElement;
                        let price = "";
                        let title = "";
                        
                        // 向上遍历 5 层，寻找包含价格信息的区域
                        for (let i = 0; i < 5; i++) {{
                            if (!container) break;
                            
                            // 获取容器内所有文本
                            const text = container.innerText;
                            
                            // 检查价格：找 "¥" 符号或纯数字价格模式
                            if (!price && (text.includes('¥') || /[0-9]+\\.[0-9]{{2}}/.test(text))) {{
                                // 尝试找到具体的价格节点
                                const priceNode = Array.from(container.querySelectorAll('*')).find(el => 
                                    el.innerText && (el.innerText.includes('¥') || /^\\d+(\\.\\d+)?$/.test(el.innerText.trim())) && el.innerText.length < 15
                                );
                                if (priceNode) price = priceNode.innerText.trim();
                                else if (text.includes('¥')) {{
                                    // 如果找不到节点，尝试正则提取
                                    const match = text.match(/¥\\s*([\\d\\.]+)/);
                                    if (match) price = match[0];
                                }}
                            }}
                            
                            // 检查标题：通常是除了价格以外最长的一段字
                            if (!title) {{
                                if (link.title) title = link.title;
                                else if (img.alt && img.alt.length > 5) title = img.alt;
                                else {{
                                    // 尝试找标题节点 (文本长度适中，不含价格)
                                    const titleNode = Array.from(container.querySelectorAll('div, span, a')).find(el => 
                                        el.innerText && el.innerText.length > 5 && el.innerText.length < 100 && !el.innerText.includes('¥')
                                    );
                                    if (titleNode) title = titleNode.innerText.trim();
                                }}
                            }}
                            
                            // 如果都找到了，就认为这是一个商品块
                            if (price && title) break;
                            
                            container = container.parentElement;
                        }}
                        
                        if (price && title) {{
                            // 去重
                            if (!results.find(r => r.link === link.href)) {{
                                results.push({{
                                    "platform": "1688",
                                    "title": title,
                                    "price": price,
                                    "supplier": "1688 Supplier",
                                    "link": link.href
                                }});
                            }}
                        }}
                    }}
                    return results;
                }}""", limit)
                
                for s in sources:
                    s["search_term"] = keyword

                if sources:
                    logger.info(f"成功解析 {len(sources)} 个商品")
                else:
                    logger.warning("未解析到数据。可能需要进一步调整 DOM 遍历深度。")
                    await self._safe_screenshot(page, "debug_1688_parse_fail.png")

                return sources
                
            except Exception as e:
                logger.error(f"1688 搜索过程出错: {e}")
                await self._safe_screenshot(page, "debug_1688_crash.png")
                return []
            finally:
                # 在主程序中通常需要关闭 context，但在持久化模式下可能希望能保持
                if context:
                    await context.close()
