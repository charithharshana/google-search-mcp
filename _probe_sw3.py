import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from google_search_mcp.server import _do_google_weather, _do_google_shopping
async def main():
    print("WEATHER:", await _do_google_weather("London"))
    print("---")
    print("SHOP:", await _do_google_shopping("usb cable", 3))
asyncio.run(main())
