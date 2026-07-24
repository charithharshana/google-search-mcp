import asyncio
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
import google_search_mcp.server as s

async def probe(name, url, selectors):
    async with async_playwright() as pw:
        browser, context = await s._launch_browser(pw)
        page = await context.new_page()
        try:
            await s._load_cookies(context)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await s._dismiss_consent(page)
            await page.wait_for_timeout(3000)
            title = await page.title()
            blocked = await s._is_blocked(page)
            stats = await page.evaluate("""(sels) => {
              const out = { title: document.title, url: location.href, body: (document.body?.innerText||'').slice(0,1200) };
              out.counts = {};
              for (const [k,v] of Object.entries(sels)) {
                try { out.counts[k] = document.querySelectorAll(v).length; } catch(e) { out.counts[k] = 'err'; }
              }
              // weather-specific
              out.wob = {
                wob_loc: !!document.querySelector('#wob_loc'),
                wob_tm: !!document.querySelector('#wob_tm'),
                wob_dc: !!document.querySelector('#wob_dc'),
                wob_hm: !!document.querySelector('#wob_hm'),
                weather: !!document.querySelector('#wob_wc, .wob_wc, [data-attrid*="weather"]'),
                attrids: Array.from(document.querySelectorAll('[data-attrid]')).slice(0,15).map(e=>e.getAttribute('data-attrid')),
              };
              // shopping
              out.shop = {
                cards: document.querySelectorAll('[data-docid], .sh-dgr__content, .i0X6df, .KZmu8e').length,
                h3: document.querySelectorAll('h3').length,
                prices: (document.body?.innerText||'').match(/(?:US?\\$|£|€)\\s*[\\d,.]+/g)?.slice(0,10) || [],
              };
              return out;
            }""", selectors)
            print("===", name, "===")
            print("title", title, "blocked", blocked, "url", page.url)
            print("counts", stats.get("counts"))
            print("wob", stats.get("wob"))
            print("shop", stats.get("shop"))
            print("body", stats.get("body","")[:800])
            await s._save_cookies(context)
        finally:
            await browser.close()

async def main():
    await probe("weather", f"https://www.google.com/search?q={quote_plus('weather London')}&hl=en", {
        "wob_loc": "#wob_loc", "wob_tm": "#wob_tm", "main": "#search"
    })
    await probe("shopping", f"https://www.google.com/search?q={quote_plus('usb cable')}&hl=en&tbm=shop", {
        "docid": "[data-docid]", "sh": ".sh-dgr__content", "h3": "h3"
    })
    await probe("shopping2", f"https://www.google.com/search?q={quote_plus('usb cable')}&hl=en&udm=28", {
        "docid": "[data-docid]", "sh": ".sh-dgr__content", "h3": "h3"
    })

asyncio.run(main())
