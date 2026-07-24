import asyncio
from google_search_mcp.server import _launch_browser
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as pw:
        b, c = await _launch_browser(pw)
        p = await c.new_page()
        await p.goto("https://www.google.com/search?q=Northern+Lights&hl=en&tbm=isch",
                     wait_until="domcontentloaded", timeout=30000)
        await p.wait_for_timeout(3000)
        consent = await p.get_by_role("button", name="I agree").count()
        imgres = await p.locator('a[href^="/imgres"]').count()
        imgs = await p.locator("img").count()
        big_imgs = await p.locator("img").evaluate_all(
            "els => els.filter(e => e.naturalWidth > 100 && e.naturalHeight > 100).length"
        )
        print("url=" + p.url)
        print("title=" + (await p.title()))
        print("agree_buttons=" + str(consent))
        print("imgres=" + str(imgres))
        print("imgs=" + str(imgs))
        print("big_imgs=" + str(big_imgs))
        await b.close()

asyncio.run(run())
