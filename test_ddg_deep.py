import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

def test_ddg_parser(query):
    url = "https://html.duckduckgo.com/html/"
    resp = requests.post(url, data={"q": query}, headers=headers, timeout=12)
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for r in soup.select(".result"):
        title_tag = r.select_one(".result__title a")
        snippet_tag = r.select_one(".result__snippet")
        url_tag = r.select_one(".result__url")
        if title_tag and snippet_tag:
            title = title_tag.get_text(strip=True)
            snippet = snippet_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            if "uddg=" in href:
                # Extract real URL from DDG redirect
                m = re.search(r'uddg=([^&]+)', href)
                if m:
                    href = urllib.parse.unquote(m.group(1))
            results.append({"title": title, "snippet": snippet, "url": href})
    return results

# Test role change queries for a known nutra company: Thorne HealthTech
print("--- TEST 1: Role Changes on DDG for Thorne ---")
res_roles = test_ddg_parser('site:linkedin.com/in "Thorne" "joined" OR "appointed" OR "promoted" OR "Chief"')
print(f"Found {len(res_roles)} results")
for item in res_roles[:4]:
    print("Title:", item["title"])
    print("Snippet:", item["snippet"])
    print("URL:", item["url"])
    print("-" * 40)

# Test departures on DDG for Thorne
print("\n--- TEST 2: Departures on DDG for Thorne ---")
res_dep = test_ddg_parser('site:linkedin.com/in "Thorne" "ex-" OR "former" OR "previously at"')
print(f"Found {len(res_dep)} results")
for item in res_dep[:4]:
    print("Title:", item["title"])
    print("Snippet:", item["snippet"])
    print("URL:", item["url"])
    print("-" * 40)

# Test funding / M&A on DDG for Thorne
print("\n--- TEST 3: Funding / M&A for Thorne ---")
res_fund = test_ddg_parser('"Thorne HealthTech" "funding" OR "acquired" OR "acquisition" OR "Series" OR "private equity"')
print(f"Found {len(res_fund)} results")
for item in res_fund[:4]:
    print("Title:", item["title"])
    print("Snippet:", item["snippet"])
    print("URL:", item["url"])
    print("-" * 40)
