import time
import requests
import feedparser

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

t0 = time.time()
try:
    resp = requests.get("https://news.google.com/rss/search?q=nutraceutical&hl=en-US&gl=US&ceid=US:en", timeout=6, headers=headers)
    print(f"Status: {resp.status_code}, time: {time.time()-t0:.2f}s")
    f = feedparser.parse(resp.text)
    print("Entries:", len(f.entries))
except Exception as e:
    print("Error:", e)
