import urllib.request, urllib.parse, json, re, requests
from bs4 import BeautifulSoup
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

companies = ['Indena', 'Sabinsa', 'AIDP', 'NutraScience Labs', 'Layn Natural Ingredients', 'Thorne Research', 'PLT Health Solutions']

print("=== 1. TEST BING SEARCH FOR LINKEDIN PROFILES ===")
for co in companies:
    q = f'site:linkedin.com/in "{co}"'
    url = f"https://www.bing.com/search?q={urllib.parse.quote(q)}"
    try:
        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all('li', class_='b_algo')
        print(f"\n{co}: Found {len(results)} Bing LinkedIn results")
        for res in results[:3]:
            h2 = res.find('h2')
            snip = res.find('p')
            title = h2.get_text() if h2 else ''
            p_text = snip.get_text() if snip else ''
            print(f"   • {title[:70]} | {p_text[:90]}")
    except Exception as e:
        print(f"{co}: Error {e}")
    time.sleep(1)

print("\n=== 2. TEST YAHOO SEARCH FOR LINKEDIN PROFILES ===")
for co in companies[:4]:
    q = f'site:linkedin.com/in "{co}"'
    url = f"https://search.yahoo.com/search?p={urllib.parse.quote(q)}"
    try:
        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all('div', class_='algo')
        print(f"\n{co}: Found {len(results)} Yahoo LinkedIn results")
        for res in results[:3]:
            h3 = res.find('h3')
            snip = res.find('div', class_='compText')
            title = h3.get_text() if h3 else ''
            p_text = snip.get_text() if snip else ''
            print(f"   • {title[:70]} | {p_text[:90]}")
    except Exception as e:
        print(f"{co}: Error {e}")
    time.sleep(1)
