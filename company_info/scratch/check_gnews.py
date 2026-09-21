import requests
import feedparser

url = "https://news.google.com/rss/search?q=test&hl=en-US&gl=US&ceid=US:en"
resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
print("Google News RSS status:", resp.status_code)
f = feedparser.parse(resp.text)
print("Entries:", len(f.entries))
