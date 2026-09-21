import requests
import feedparser

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

session = requests.Session()
session.headers.update(headers)

try:
    resp = session.get("https://news.google.com/rss/search?q=lonza+appointed&hl=en-US&gl=US&ceid=US:en", timeout=5)
    print("Full Headers Status:", resp.status_code)
    f = feedparser.parse(resp.text)
    print("Entries found:", len(f.entries))
    for e in f.entries[:3]:
        print(" -", e.title)
except Exception as e:
    print("Error:", e)
