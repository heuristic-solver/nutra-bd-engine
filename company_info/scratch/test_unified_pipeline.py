import sys, os
sys.path.insert(0, os.path.abspath("."))
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup

from company_info.models.company import CompanyProfile
from company_info.models.role_change import RoleChangeEvent, MovementType
from company_info.models.funding import FundingEvent
from company_info.models.movement import StrategicMovementEvent, MovementCategory

from company_info.extractors.name_extractor import clean_person_name, extract_person_name_from_headline
from company_info.extractors.role_extractor import clean_role_title, extract_role_from_text
from company_info.extractors.funding_parser import parse_funding_amount, classify_round_type, extract_investors, extract_valuation
from company_info.extractors.movement_classifier import classify_person_movement, classify_strategic_movement

test_cos = [
    CompanyProfile(company_name="Glanbia Nutritionals", domain="glanbianutritionals.com"),
    CompanyProfile(company_name="ChromaDex", domain="chromadex.com"),
    CompanyProfile(company_name="Balchem", domain="balchem.com"),
    CompanyProfile(company_name="Lonza", domain="lonza.com"),
    CompanyProfile(company_name="AB Enzymes", domain="abenzymes.com"),
    CompanyProfile(company_name="Kemin Industries", domain="kemin.com"),
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

for p in test_cos:
    t0 = time.time()
    co = p.company_name
    q = f'"{co}" ("appointed" OR "named" OR "joined" OR "CEO" OR "CFO" OR "VP" OR "Director" OR "funding" OR "raised" OR "acquired" OR "acquisition" OR "expansion" OR "launches" OR "partnership")'
    
    # Try Google News RSS
    hits = []
    try:
        url_g = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url_g, headers=headers, timeout=2.0)
        if r.status_code == 200:
            import feedparser
            f = feedparser.parse(r.text)
            for e in f.entries[:8]:
                hits.append({"title": e.title, "snippet": e.get("summary", ""), "link": e.link, "date": e.get("published", ""), "source": "Google News"})
    except Exception:
        pass

    # If news timed out, try Bing News
    if not hits:
        try:
            url_b = f"https://www.bing.com/news/search?q={urllib.parse.quote(q)}"
            r = requests.get(url_b, headers=headers, timeout=2.0)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for c in soup.select(".news-card, .na_card, .t_s, .b_algo")[:8]:
                    h = c.select_one("a.title, h2 a, h2, a")
                    p_tag = c.select_one(".snippet, p")
                    if h and len(h.get_text(strip=True)) > 10:
                        hits.append({"title": h.get_text(strip=True), "snippet": p_tag.get_text(strip=True) if p_tag else "", "link": h.get("href", ""), "date": "", "source": "Bing News"})
        except Exception:
            pass

    roles = []
    fundings = []
    movements = []

    for h in hits:
        title = h["title"]
        snip = h["snippet"]
        full = f"{title} {snip}"

        # 1. Role
        pname = extract_person_name_from_headline(title, co) or extract_person_name_from_headline(snip, co)
        if pname:
            role = extract_role_from_text(full, pname)
            if role:
                roles.append(f"{pname} ({role})")

        # 2. Funding
        if any(w in full.lower() for w in ["funding round", "capital raise", "series a", "series b", "series c", "growth equity", "raised $"]):
            amt_raw, _ = parse_funding_amount(full)
            fundings.append(f"{title[:60]} (Amt: {amt_raw})")

        # 3. Movements
        strat = classify_strategic_movement(full)
        if strat:
            movements.append(f"[{strat.value}] {title[:70]}")

    print(f"\n==================== {co} ({time.time()-t0:.2f}s) ====================")
    print(f"Hits: {len(hits)} | Roles: {len(roles)} | Funding: {len(fundings)} | Movements: {len(movements)}")
    if roles:
        print("  Roles:", roles)
    if fundings:
        print("  Funding:", fundings)
    if movements:
        print("  Movements:", movements[:3])
