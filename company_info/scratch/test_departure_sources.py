import os, requests, json, time, re
from dotenv import load_dotenv

load_dotenv('.env')
akey = os.getenv('APOLLO_API_KEY')
apify_token = os.getenv('APIFY_API_TOKEN')

headers_apollo = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'X-Api-Key': akey}

# 1. Test Apollo API for ChromaDex, Kemin, Indena, Lonza, Glanbia, Gencor
test_doms = ['chromadex.com', 'kemin.com', 'indena.com', 'gencorpacific.com']

print("--- Testing Apollo parameters for alumni/departures ---")
param_tests = [
    ('past_organization_domains', {'past_organization_domains': ['chromadex.com'], 'per_page': 5}),
    ('q_past_organization_domains', {'q_past_organization_domains': 'chromadex.com', 'per_page': 5}),
    ('organization_domains', {'organization_domains': ['chromadex.com'], 'per_page': 5}),
    ('q_organization_domains', {'q_organization_domains': 'chromadex.com', 'per_page': 5}),
]

for name, payload in param_tests:
    try:
        r = requests.post('https://api.apollo.io/v1/mixed_people/api_search', headers=headers_apollo, json=payload, timeout=5)
        if r.status_code == 200:
            data = r.json()
            total = data.get('pagination', {}).get('total_entries', 0)
            people = data.get('people', [])
            print(f"Apollo [{name}]: Total={total}, Sample={len(people)}")
            for p in people[:2]:
                fn = p.get('first_name', '')
                ln = p.get('last_name_obfuscated', '')
                title = p.get('title', '')
                org = p.get('organization', {}).get('name', '') if p.get('organization') else 'N/A'
                print(f"   -> {fn} {ln} | {title} | Current Org: {org}")
        else:
            print(f"Apollo [{name}]: Status {r.status_code}")
    except Exception as e:
        print(f"Apollo [{name}]: Error {e}")

# 2. Test Apify Actor store for LinkedIn alumni/departure scrapers
print("\n--- Testing Apify for Departure/Alumni Scrapers ---")
if apify_token:
    try:
        r = requests.get(f'https://api.apify.com/v2/store?search=linkedin%20past%20company&token={apify_token}&limit=5')
        if r.status_code == 200:
            items = r.json().get('data', {}).get('items', [])
            print(f"Found {len(items)} Apify actors for past company:")
            for it in items[:5]:
                print(f"   Actor: {it.get('username')}/{it.get('name')} - {it.get('title')} (Runs: {it.get('stats', {}).get('totalRuns')})")
        else:
            print(f"Apify store error: {r.status_code}")
    except Exception as e:
        print(f"Apify error: {e}")

# 3. Test DuckDuckGo HTML / Web Dorking for departures
print("\n--- Testing Web Search Departure Dorks ---")
dork_queries = [
    'site:linkedin.com/in "formerly at ChromaDex"',
    'site:linkedin.com/in "ex-ChromaDex"',
    'site:linkedin.com/in "former * at ChromaDex"',
    'site:linkedin.com/in "previous * ChromaDex"',
    '"stepped down as" ChromaDex',
    '"leaves ChromaDex"'
]

for q in dork_queries:
    try:
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(q)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, 'html.parser')
            results = soup.find_all('div', class_='result')
            print(f"DDG Dork [{q}]: Found {len(results)} results")
            for res in results[:2]:
                title = res.find('a', class_='result__snippet')
                snippet = res.find('a', class_='result__snippet')
                text = snippet.get_text() if snippet else ""
                print(f"   Snippet: {text[:120]}...")
        else:
            print(f"DDG Dork [{q}]: Status {r.status_code}")
    except Exception as e:
        print(f"DDG Dork [{q}]: Error {e}")
