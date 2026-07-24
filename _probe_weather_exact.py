import asyncio, sys, traceback
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
import google_search_mcp.server as s

async def main():
    location = "London"
    encoded_location = quote_plus(f"weather {location}")
    url = f"https://www.google.com/search?q={encoded_location}&hl=en"
    async with async_playwright() as pw:
        browser, context = await s._launch_browser(pw)
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await s._dismiss_consent(page)
            await page.wait_for_timeout(2000)
            data = await page.evaluate(
                """
                () => {
                    const data = {};
                    const locEl = document.querySelector('#wob_loc');
                    data.location = locEl ? locEl.innerText.trim() : '';
                    const tempEl = document.querySelector('#wob_tm');
                    data.temp_c = tempEl ? tempEl.innerText.trim() : '';
                    const tempFEl = document.querySelector('#wob_ttm');
                    data.temp_f = tempFEl ? tempFEl.innerText.trim() : '';
                    const condEl = document.querySelector('#wob_dc');
                    data.condition = condEl ? condEl.innerText.trim() : '';
                    const precipEl = document.querySelector('#wob_pp');
                    data.precipitation = precipEl ? precipEl.innerText.trim() : '';
                    const humidEl = document.querySelector('#wob_hm');
                    data.humidity = humidEl ? humidEl.innerText.trim() : '';
                    const windEl = document.querySelector('#wob_ws');
                    data.wind = windEl ? windEl.innerText.trim() : '';
                    const timeEl = document.querySelector('#wob_dts');
                    data.time = timeEl ? timeEl.innerText.trim() : '';
                    data.forecast = [];
                    const forecastDays = document.querySelectorAll('.wob_df');
                    for (const day of forecastDays) {
                        const dayName = day.querySelector('.Z1VzSb, .QrNVmd');
                        const temps = day.querySelectorAll('.wob_t span:first-child');
                        let high = '', low = '';
                        if (temps.length >= 2) {
                            high = temps[0].innerText.trim();
                            low = temps[1].innerText.trim();
                        }
                        const iconEl = day.querySelector('img');
                        if (dayName) {
                            data.forecast.push({
                                day: dayName.innerText.trim(),
                                high: high,
                                low: low,
                                condition: iconEl ? iconEl.alt || '' : ''
                            });
                        }
                    }
                    return data;
                }
                """
            )
            print("DATA:", data)
            print("check", not data.get("temp_c"), not data.get("location"), data.get("temp_c"), data.get("location"))
            if not data.get("temp_c") and not data.get("location"):
                print("Would fail")
            else:
                print("Would succeed")
        except Exception:
            traceback.print_exc()
        finally:
            await browser.close()

asyncio.run(main())
