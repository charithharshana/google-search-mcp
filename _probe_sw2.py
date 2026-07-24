import asyncio, sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
import google_search_mcp.server as s

async def main():
    # weather with and without cookies
    for use_cookies in (False, True):
        async with async_playwright() as pw:
            browser, context = await s._launch_browser(pw)
            page = await context.new_page()
            if use_cookies:
                await s._load_cookies(context)
            await page.goto("https://www.google.com/search?q=weather+London&hl=en", wait_until="domcontentloaded", timeout=30000)
            await s._dismiss_consent(page)
            await page.wait_for_timeout(2500)
            data = await page.evaluate("""() => {
              const g = id => { const e=document.querySelector(id); return e?e.innerText.trim():''; };
              return {
                loc: g('#wob_loc'), tm: g('#wob_tm'), ttm: g('#wob_ttm'), dc: g('#wob_dc'),
                pp: g('#wob_pp'), hm: g('#wob_hm'), ws: g('#wob_ws'), dts: g('#wob_dts'),
                days: document.querySelectorAll('.wob_df').length,
                blocked: document.body.innerText.includes('unusual traffic'),
              };
            }""")
            print("weather cookies=", use_cookies, data)
            await browser.close()

    # shopping variants
    for url in [
        "https://www.google.com/search?q=usb+cable&hl=en&tbm=shop",
        "https://www.google.com/search?q=usb+cable&hl=en&udm=28",
        "https://www.google.com/search?q=buy+usb+cable&hl=en",
    ]:
        async with async_playwright() as pw:
            browser, context = await s._launch_browser(pw)
            page = await context.new_page()
            await s._load_cookies(context)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await s._dismiss_consent(page)
            await page.wait_for_timeout(3000)
            data = await page.evaluate("""() => {
              const text = (document.body?.innerText||'').slice(0,500);
              const selectors = {
                docid: document.querySelectorAll('[data-docid]').length,
                sh_dgr: document.querySelectorAll('.sh-dgr__content').length,
                i0X6df: document.querySelectorAll('.i0X6df').length,
                KZmu8e: document.querySelectorAll('.KZmu8e').length,
                shPr: document.querySelectorAll('.sh-pr__product-result').length,
                product: document.querySelectorAll('[data-product-id], [data-offer-id]').length,
                h3: document.querySelectorAll('h3').length,
                a_shop: document.querySelectorAll('a[href*=\"/shopping/\"]').length,
                prices: ((document.body?.innerText||'').match(/(?:US?\\$|£|€)\\s*[\\d,.]+/g)||[]).slice(0,8),
              };
              // sample product card html
              const card = document.querySelector('[data-docid], .sh-dgr__content, .i0X6df, .KZmu8e, a[href*="/shopping/product"]');
              return { url: location.href, selectors, sample: card ? card.outerHTML.slice(0,400) : null, text };
            }""")
            print("SHOP", url)
            print(json.dumps(data, ensure_ascii=True)[:1500])
            await browser.close()

asyncio.run(main())
