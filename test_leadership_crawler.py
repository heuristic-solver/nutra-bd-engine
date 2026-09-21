# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import feedparser
from bs4 import BeautifulSoup
import urllib.parse
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def search_google_news(query, limit=5):
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:limit]:
        title = entry.get('title', '')
        source = (entry.get('source') or {}).get('title', '')
        date = entry.get('published', '')
        link = entry.get('link', '')
        results.append({'title': title, 'source': source, 'date': date, 'link': link})
    return results

print("=== TEST CONTEXT-ANCHORED QUERIES FOR RITUAL ===")
q_ritual_hires = '("Ritual" OR "ritual.com") (vitamins OR supplements OR health OR "Kat Schneider") (appointed OR named OR joined OR promoted OR CEO OR CFO OR VP)'
res = search_google_news(q_ritual_hires, limit=5)
for r in res:
    print(f"  • {r['title']} | {r['date']}")

q_ritual_fund = '("Ritual" OR "ritual.com") (vitamins OR supplements OR "Kat Schneider") (funding OR raised OR Series OR investment OR valuation OR revenue)'
res_fund = search_google_news(q_ritual_fund, limit=5)
print("\n[RITUAL FUNDING]:")
for r in res_fund:
    print(f"  • {r['title']} | {r['date']}")

print("\n=== TEST DIRECT WEBSITE SCRAPING FOR TEAM / LEADERSHIP ===")
def crawl_leadership(url):
    try:
        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        # find potential team/executive elements
        text = soup.get_text(separator=' ', strip=True)
        print(f"URL: {url} -> Status: {r.status_code}, Length: {len(text)}")
        # Look for titles
        matches = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)\s*[-–|,]\s*(Chief [A-Za-z]+ Officer|CEO|CFO|COO|CTO|CMO|Vice President|VP [A-Za-z ]+|Director of [A-Za-z ]+|Founder)', text)
        print(f"  Extracted {len(matches)} leadership matches:")
        for m in matches[:5]:
            print(f"    - {m[0]} -> {m[1]}")
    except Exception as e:
        print(f"Error crawling {url}: {e}")

crawl_leadership("https://www.thorne.com/about/leadership")
crawl_leadership("https://www.niagenbioscience.com/pages/leadership")
crawl_leadership("https://lieflabs.com/about/")
crawl_leadership("https://vitaquest.com/leadership/")
