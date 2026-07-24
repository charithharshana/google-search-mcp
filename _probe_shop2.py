import asyncio, sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
import google_search_mcp.server as s

async def main():
    urls = [
        "https://www.google.com/search?q=usb+cable&tbm=shop&hl=en&gl=us&pws=0",
        "https://shopping.google.com/search?q=usb+cable&hl=en&gl=us",
        "https://www.google.com/search?q=usb+cable&ibp=oshop&hl=en&gl=us",
        "https://www.google.com/search?q=usb+cable+price&hl=en&gl=us",
    ]
    for url in urls:
        async with async_playwright() as pw:
            browser, context = await s._launch_browser(pw)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await s._dismiss_consent(page)
            await page.wait_for_timeout(3500)
            data = await page.evaluate("""() => {
              const prices = ((document.body?.innerText||'').match(/(?:US?\\$|£|€|Rs\\.?\\s?)[\\d,.]+/g)||[]).slice(0,12);
              return {
                href: location.href,
                title: document.title,
                docid: document.querySelectorAll('[data-docid]').length,
                product: document.querySelectorAll('a[href*="/shopping/product"]').length,
                sh: document.querySelectorAll('.sh-dgr__content,.i0X6df,.KZmu8e,.sh-pr__product-result').length,
                cards: document.querySelectorAll('[jscontroller][data-hveid]').length,
                prices,
                text: (document.body?.innerText||'').slice(0,600),
              };
            }""")
            print("URL", url)
            print(json.dumps(data, ensure_ascii=True)[:1200])
            print("---")
            await browser.close()
asyncio.run(main())
