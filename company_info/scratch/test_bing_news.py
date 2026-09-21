import urllib.parse
import time
import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

companies = ["Glanbia Nutritionals", "Lonza", "Balchem", "ChromaDex", "ADM"]

for co in companies:
    t0 = time.time()
    # 1. Bing News
    q_news = f'"{co}" (appointed OR named OR CEO OR acquisition OR expansion OR funding)'
    url_bing_news = f"https://www.bing.com/news/search?q={urllib.parse.quote(q_news)}"
    r = requests.get(url_bing_news, headers=headers, timeout=4)
    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select(".news-card, .na_card, .news-card-body, .t_s, .b_algo")
    print(f"\n==================== {co} ({time.time()-t0:.2f}s) ====================")
    print(f"Bing News cards: {len(cards)}")
    for c in cards[:3]:
        t = c.select_one("a.title, a.href, h2, a")
        p = c.select_one(".snippet, .b_caption, p")
        if t:
            print(" - TITLE:", t.get_text(strip=True)[:100])
        if p:
            print("   SNIP:", p.get_text(strip=True)[:120])
