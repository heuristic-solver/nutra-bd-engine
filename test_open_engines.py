import requests
import feedparser
from bs4 import BeautifulSoup
import urllib.parse
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# 1. Test Google News RSS
def test_google_news_rss(query):
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    print(f"Google News RSS for '{query}': {len(feed.entries)} items")
    for entry in feed.entries[:3]:
        print(f"  - Title: {entry.get('title')}")
        print(f"    Date: {entry.get('published')}")
        print(f"    Source: {(entry.get('source') or {}).get('title')}")
        print(f"    Link: {entry.get('link')}")

# 2. Test Yahoo News RSS
def test_yahoo_news_rss(query):
    url = f"https://news.search.yahoo.com/rss?p={urllib.parse.quote(query)}"
    feed = feedparser.parse(url)
    print(f"\nYahoo News RSS for '{query}': {len(feed.entries)} items")
    for entry in feed.entries[:3]:
        print(f"  - Title: {entry.get('title')}")
        print(f"    Date: {entry.get('published')}")
        print(f"    Link: {entry.get('link')}")

# 3. Test DuckDuckGo Lite GET
def test_ddg_lite(query):
    url = f"https://lite.duckduckgo.com/lite/"
    resp = requests.post(url, data={'q': query}, headers=headers, timeout=10)
    soup = BeautifulSoup(resp.text, 'html.parser')
    rows = soup.select('tr')
    results = []
    for r in rows:
        link_tag = r.select_one('a.result-link')
        snippet_tag = r.select_one('.result-snippet')
        if link_tag:
            results.append({'title': link_tag.get_text(strip=True), 'link': link_tag.get('href'), 'snippet': snippet_tag.get_text(strip=True) if snippet_tag else ''})
    print(f"\nDuckDuckGo Lite for '{query}': {len(results)} items")
    for res in results[:3]:
        print(f"  - Title: {res['title']}")
        print(f"    Snippet: {res['snippet']}")
        print(f"    Link: {res['link']}")

# 4. Test Bing Web Search Open Scraper
def test_bing_scrape(query):
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
    resp = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(resp.text, 'html.parser')
    items = soup.select('li.b_algo')
    print(f"\nBing Web Search for '{query}': {len(items)} items")
    for item in items[:3]:
        h2 = item.select_one('h2 a')
        snippet = item.select_one('.b_caption p') or item.select_one('.b_lineclamp2') or item.select_one('.b_lineclamp3')
        if h2:
            print(f"  - Title: {h2.get_text(strip=True)}")
            print(f"    Link: {h2.get('href')}")
            print(f"    Snippet: {snippet.get_text(strip=True) if snippet else ''}")

# 5. Test direct Nutraceutical Media RSS
def test_nutra_media():
    sources = [
        ("NutraIngredients", "https://www.nutraingredients.com/Info/RSS"),
        ("Nutraceuticals World", "https://www.nutraceuticalsworld.com/rss"),
        ("Natural Products Insider", "https://www.naturalproductsinsider.com/rss.xml"),
    ]
    for name, rss_url in sources:
        try:
            f = feedparser.parse(rss_url)
            print(f"\n{name} RSS: {len(f.entries)} items")
            for e in f.entries[:2]:
                print(f"  - {e.get('title')} ({e.get('published', '')})")
        except Exception as ex:
            print(f"{name} error:", ex)

print("Starting Search Engine Probe...")
test_google_news_rss("ChromaDex appointed OR funding OR acquisition")
test_yahoo_news_rss("ChromaDex appointed OR CEO OR funding")
test_ddg_lite("ChromaDex CEO CFO appointed")
test_bing_scrape("ChromaDex executive team leadership")
test_nutra_media()
