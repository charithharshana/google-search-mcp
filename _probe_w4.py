import asyncio, sys, inspect
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import google_search_mcp.server as s
print(inspect.getsource(s._do_google_weather)[:2500])
print("---CALL---")
print(asyncio.run(s._do_google_weather("London")))
