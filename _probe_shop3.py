import asyncio, sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
import google_search_mcp.server as s

async def main():
    async with async_playwright() as pw:
        browser, context = await s._launch_browser(pw)
        page = await context.new_page()
        await page.goto("https://www.google.com/search?q=Anker+USB+C+cable&hl=en", wait_until="domcontentloaded", timeout=30000)
        await s._dismiss_consent(page)
        await page.wait_for_timeout(3000)
        data = await page.evaluate("""() => {
          const out = {
            prices: ((document.body.innerText||'').match(/(?:US?\\$|£|€|Rs\\.?\\s?)[\\d,.]+/g)||[]).slice(0,20),
            commercial: [],
            pla: [],
          };
          // product listing ads / shopping carousel
          document.querySelectorAll('[data-dtld], .pla-unit, .sh-np__click-target, a[href*="aclk"], .commercial-unit-desktop-rhs a, .cu-container a').forEach((a,i)=>{
            if (i>15) return;
            const t = (a.innerText||'').trim().slice(0,200);
            if (t) out.pla.push({text:t, href:(a.href||'').slice(0,120)});
          });
          // organic results with prices
          document.querySelectorAll('#search .g, #rso .MjjYud, #rso .Gx5Zad').forEach((el,i)=>{
            if (i>10) return;
            const title = el.querySelector('h3')?.innerText||'';
            const text = el.innerText||'';
            const price = (text.match(/(?:US?\\$|£|€|Rs\\.?\\s?)[\\d,.]+/)||[])[0]||'';
            const a = el.querySelector('a[href^="http"]');
            if (title) out.commercial.push({title, price, url:a?.href||'', snip:text.slice(0,180)});
          });
          return out;
        }""")
        print(json.dumps(data, ensure_ascii=True, indent=2)[:3000])
        await browser.close()
asyncio.run(main())
