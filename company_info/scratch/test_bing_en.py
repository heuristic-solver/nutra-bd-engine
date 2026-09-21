import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import urllib.parse
import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

co = "Glanbia Nutritionals"
q = f'"{co}" (appointed OR acquired OR expansion)'
url = f"https://www.bing.com/search?q={urllib.parse.quote(q)}&setlang=en-us&cc=us"
r = requests.get(url, headers=headers, timeout=4)
soup = BeautifulSoup(r.text, "html.parser")
items = soup.select("li.b_algo")
print(f"Bing with en-US hits: {len(items)}")
for item in items[:5]:
    h2 = item.select_one("h2 a")
    p = item.select_one(".b_caption p, .b_lineclamp2, p")
    print(" -", h2.get_text(strip=True) if h2 else "")
    print("   ", p.get_text(strip=True)[:100] if p else "")
