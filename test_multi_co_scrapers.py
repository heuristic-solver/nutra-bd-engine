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

def search_ddg_lite(query, limit=5):
    url = "https://lite.duckduckgo.com/lite/"
    try:
        resp = requests.post(url, data={'q': query}, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = soup.select('tr')
        results = []
        for r in rows:
            link_tag = r.select_one('a.result-link')
            snippet_tag = r.select_one('.result-snippet')
            if link_tag:
                title = link_tag.get_text(strip=True)
                href = link_tag.get('href', '')
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ''
                results.append({'title': title, 'link': href, 'snippet': snippet})
                if len(results) >= limit:
                    break
        return results
    except Exception as e:
        return []

def search_bing_open(query, limit=5):
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.select('li.b_algo')
        results = []
        for item in items[:limit]:
            h2 = item.select_one('h2 a')
            snippet = item.select_one('.b_caption p') or item.select_one('.b_lineclamp2')
            if h2:
                results.append({
                    'title': h2.get_text(strip=True),
                    'link': h2.get('href'),
                    'snippet': snippet.get_text(strip=True) if snippet else ''
                })
        return results
    except Exception as e:
        return []

test_companies = [
    ("Thorne HealthTech", "thorne.com"),
    ("Lief Labs", "lieflabs.com"),
    ("Gencor Pacific", "gencorpacific.com"),
    ("Ritual", "ritual.com"),
    ("Vitaquest International", "vitaquest.com")
]

for co_name, co_domain in test_companies:
    print("=" * 60)
    print(f"TESTING COMPANY: {co_name} ({co_domain})")
    print("=" * 60)
    
    # 1. Appointments & New Hires
    q_hires = f'"{co_name}" "appointed" OR "named" OR "promoted" OR "joins" OR "joined"'
    res_hires = search_google_news(q_hires, limit=3)
    print(f"\n[HIRES / APPOINTMENTS] ({len(res_hires)} Google News items):")
    for r in res_hires:
        print(f"  • {r['title']} | {r['date']}")
        
    # 2. Departures / Resignations
    q_dep = f'"{co_name}" "steps down" OR "resigned" OR "departs" OR "leaving" OR "transition"'
    res_dep = search_google_news(q_dep, limit=3)
    print(f"\n[DEPARTURES / RESIGNATIONS] ({len(res_dep)} Google News items):")
    for r in res_dep:
        print(f"  • {r['title']} | {r['date']}")

    # 3. Funding / Investments / M&A
    q_fund = f'"{co_name}" "funding" OR "raised" OR "acquired" OR "acquisition" OR "investment" OR "Series"'
    res_fund = search_google_news(q_fund, limit=3)
    print(f"\n[FUNDING / M&A] ({len(res_fund)} Google News items):")
    for r in res_fund:
        print(f"  • {r['title']} | {r['date']}")

    # 4. Strategic Expansions & Operational Movements
    q_exp = f'"{co_name}" "expansion" OR "facility" OR "manufacturing" OR "partnership" OR "launches"'
    res_exp = search_google_news(q_exp, limit=3)
    print(f"\n[STRATEGIC MOVEMENTS & EXPANSIONS] ({len(res_exp)} Google News items):")
    for r in res_exp:
        print(f"  • {r['title']} | {r['date']}")
        
    # 5. LinkedIn Profile / Public Signals via DDG Lite / Bing
    q_li = f'site:linkedin.com "{co_name}" "Chief" OR "Director" OR "Vice President" OR "joined"'
    res_li = search_ddg_lite(q_li, limit=3)
    if not res_li:
        res_li = search_bing_open(q_li, limit=3)
    print(f"\n[PUBLIC LINKEDIN SIGNALS] ({len(res_li)} items):")
    for r in res_li:
        print(f"  • {r['title']} -> {r.get('snippet', '')[:80]}...")
