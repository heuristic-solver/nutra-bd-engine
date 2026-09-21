import urllib.parse
import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

queries = [
    'site:linkedin.com/in "21st Century HealthCare" ("Chief" OR "Director" OR "VP" OR "President")',
    'site:linkedin.com/in ("ex-21st Century HealthCare" OR "formerly at 21st Century HealthCare")',
]

for q in queries:
    url = f"https://www.bing.com/search?q={urllib.parse.quote(q)}"
    r = requests.get(url, headers=headers, timeout=5)
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select("li.b_algo")
    print(f"\nQuery: {q}")
    print(f"Status: {r.status_code}, Found {len(items)} results:")
    for item in items[:3]:
        h2 = item.select_one("h2 a")
        p = item.select_one(".b_caption p") or item.select_one(".b_lineclamp2")
        title = h2.get_text(strip=True) if h2 else ""
        link = h2.get("href", "") if h2 else ""
        snippet = p.get_text(strip=True) if p else ""
        print(f" - Title: {title}")
        print(f"   Snippet: {snippet[:120]}...")
