import time
import requests
import feedparser

t0 = time.time()
url = "https://news.google.com/rss/search?q=%2221st+Century+HealthCare%22&hl=en-US&gl=US&ceid=US:en"
resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
print(f"Google News status: {resp.status_code}, time: {time.time()-t0:.3f}s")
f = feedparser.parse(resp.text)
print(f"Google News entries: {len(f.entries)}")

t1 = time.time()
ddg_url = "https://lite.duckduckgo.com/lite/"
ddg_resp = requests.post(ddg_url, data={"q": '"21st Century HealthCare"'}, timeout=5, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
print(f"DDG Lite status: {ddg_resp.status_code}, time: {time.time()-t1:.3f}s")
