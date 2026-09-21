import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import urllib.parse
import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

companies = ["Glanbia Nutritionals", "ChromaDex", "Balchem", "Lonza", "NutraScience Labs"]

for co in companies:
    q = f'"{co}" ("appointed" OR "named" OR "CEO" OR "CFO" OR "VP" OR "acquisition" OR "expansion" OR "facility")'
    url = f"https://www.bing.com/search?q={urllib.parse.quote(q)}"
    r = requests.get(url, headers=headers, timeout=4)
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select("li.b_algo")
    print(f"\n==================== {co} ====================")
    print(f"Bing Web hits: {len(items)}")
    for item in items[:3]:
        h2 = item.select_one("h2 a")
        p = item.select_one(".b_caption p, .b_lineclamp2, .b_lineclamp3, p")
        title = h2.get_text(strip=True) if h2 else ""
        link = h2.get("href", "") if h2 else ""
        snippet = p.get_text(strip=True) if p else ""
        print(f" - {title}")
        print(f"   {snippet[:100]}...")
