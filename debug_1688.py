import asyncio
from playwright.async_api import async_playwright
import os

async def test_1688():
    print("=== 1688 交互式调试模式 ===")
    print("1. 浏览器启动后，请手动在页面上操作（登录、过滑块、搜索关键词）。")
    print("2. 当你看到商品列表出现后，请在终端按回车，程序将尝试解析。")
    print("------------------------------------------------------------")

    user_data_dir = os.path.join("data", "browser_data_1688")
    
    async with async_playwright() as p:
        # 启动有头浏览器，且不自动关闭
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False, # 强制显示界面
            args=['--start-maximized', '--disable-blink-features=AutomationControlled'],
            viewport=None
        )
        page = await context.new_page()
        
        try:
            print("正在打开 1688...")
            await page.goto("https://www.1688.com/")
            
            # 等待用户手动操作
            input("\n>>> 请在浏览器中手动完成搜索，看到商品列表后，【切回这里按回车】继续...")
            
            print("正在尝试解析页面数据...")
            
            # 极简解析逻辑：打印页面上找到的所有链接和疑似价格
            # 这有助于我们看看到底读到了什么
            items = await page.evaluate("""() => {
                const results = [];
                const elements = document.querySelectorAll('a'); // 找所有链接
                
                for (const el of elements) {
                    // 只有包含图片且高度够大的链接才可能是商品卡片
                    if (el.offsetHeight > 100 && el.querySelector('img')) {
                        results.push({
                            text: el.innerText.replace(/\\n/g, ' ').substring(0, 50),
                            html: el.outerHTML.substring(0, 100)
                        });
                    }
                }
                return results;
            }""")
            
            print(f"\n找到了 {len(items)} 个疑似商品块。前 5 个示例:")
            for i, item in enumerate(items[:5]):
                print(f"[{i+1}] Text: {item['text']}")
                print(f"    HTML片段: {item['html']}...")
            
            print("\n如果不为空，说明页面内容是可读的，只是之前的解析规则太严。")
            print("如果为空，说明页面可能使用了 Shadow DOM 或 iframe，脚本无法直接读取。")
            
        except Exception as e:
            print(f"发生错误: {e}")
        finally:
            input("\n测试结束。按回车关闭浏览器...")
            await context.close()

if __name__ == "__main__":
    asyncio.run(test_1688())

