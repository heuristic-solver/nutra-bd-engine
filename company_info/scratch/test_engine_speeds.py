import time
import requests
from bs4 import BeautifulSoup
import feedparser

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# 1. Google News RSS
t0 = time.time()
try:
    r = requests.get("https://news.google.com/rss/search?q=%2221st+Century+HealthCare%22&hl=en-US&gl=US&ceid=US:en", headers=headers, timeout=4)
    f = feedparser.parse(r.text)
    print(f"1. Google News RSS: {time.time()-t0:.2f}s, hits={len(f.entries)}")
except Exception as e:
    print(f"1. Google News RSS failed: {e}")

# 2. Bing
t1 = time.time()
try:
    r = requests.get("https://www.bing.com/search?q=%2221st+Century+HealthCare%22", headers=headers, timeout=4)
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select("li.b_algo")
    print(f"2. Bing HTML: {time.time()-t1:.2f}s, hits={len(items)}")
except Exception as e:
    print(f"2. Bing failed: {e}")

# 3. Yahoo
t2 = time.time()
try:
    r = requests.get("https://search.yahoo.com/search?p=%2221st+Century+HealthCare%22", headers=headers, timeout=4)
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select(".algo")
    print(f"3. Yahoo HTML: {time.time()-t2:.2f}s, hits={len(items)}")
except Exception as e:
    print(f"3. Yahoo failed: {e}")

# 4. DuckDuckGo html
t3 = time.time()
try:
    r = requests.post("https://html.duckduckgo.com/html/", data={"q": '"21st Century HealthCare"'}, headers=headers, timeout=4)
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select(".result__body")
    print(f"4. DDG HTML: {time.time()-t3:.2f}s, hits={len(items)}")
except Exception as e:
    print(f"4. DDG HTML failed: {e}")
