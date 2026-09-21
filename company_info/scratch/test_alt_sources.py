import sys, os
sys.path.insert(0, os.path.abspath("."))
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from company_info.engines.news_wire_engine import IndustryWireScraper
from company_info.models.company import CompanyProfile

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# 1. Test Bing
t0 = time.time()
try:
    r_bing = requests.get(f"https://www.bing.com/search?q={urllib.parse.quote('\"Glanbia Nutritionals\" (appointed OR acquired OR expansion)')}", headers=headers, timeout=4)
    soup = BeautifulSoup(r_bing.text, "html.parser")
    items = soup.select("li.b_algo")
    print(f"1. Bing Search: {time.time()-t0:.2f}s, hits={len(items)}")
    for item in items[:2]:
        h2 = item.select_one("h2 a")
        print("   -", h2.get_text(strip=True) if h2 else "")
except Exception as e:
    print(f"1. Bing failed: {e}")

# 2. Test Industry Wire RSS (Pre-cached in RAM)
t1 = time.time()
scraper = IndustryWireScraper()
profile = CompanyProfile(company_name="Glanbia Nutritionals", domain="glanbianutritionals.com")
res = scraper.scan_industry_wires_for_company(profile)
print(f"2. Industry Wires RSS: {time.time()-t1:.2f}s, roles={len(res['roles'])}, moves={len(res['movements'])}")
for r in res['roles']:
    print(f"   - [ROLE] {r.person_name}: {r.role_title}")
for m in res['movements']:
    print(f"   - [MOVE] {m.headline}")

# 3. Test SEC EDGAR
t2 = time.time()
from company_info.engines.edgar_engine import EdgarFilingScraper
edgar = EdgarFilingScraper()
ed_res = edgar.harvest_events(profile)
print(f"3. SEC EDGAR: {time.time()-t2:.2f}s, events={len(ed_res['funding']) + len(ed_res['strategic'])}")
