import urllib.parse
import time
import requests
import feedparser

companies = [
    "Glanbia Nutritionals",
    "Lonza",
    "ChromaDex",
    "Balchem",
    "Kemin Industries",
    "ADM",
    "Novozymes",
    "Naturex"
]

for co in companies:
    t0 = time.time()
    # Simplified clean query for Google News
    q = f'"{co}"'
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        f = feedparser.parse(r.text)
        print(f"[{co}] Status: {r.status_code}, Entries: {len(f.entries)}, Time: {time.time()-t0:.2f}s")
        for e in f.entries[:2]:
            print(f"   - {e.title}")
    except Exception as e:
        print(f"[{co}] Error: {e}")
    time.sleep(0.2)
