import sys, os
sys.path.insert(0, os.path.abspath("."))
import time
from company_info.models.company import CompanyProfile
from company_info.pipeline.orchestrator import CompanyIntelligenceEngine

p = CompanyProfile(
    company_name="ChromaDex",
    domain="chromadex.com",
    website="https://www.chromadex.com",
    country="United States",
    specialty="Dietary Supplements & Ingredients"
)

engine = CompanyIntelligenceEngine(max_workers=1)

print("Starting ChromaDex test...")
t0 = time.time()

# 1. Search Scraper
t = time.time()
rq = engine.search_scraper.build_role_change_queries(p)
hits = engine.search_scraper.execute_search(rq[0], limit=6)
print(f"1. SearchScraper: {time.time()-t:.2f}s, hits={len(hits)}")

# 2. LinkedIn Scraper
t = time.time()
li = engine.linkedin_scraper.harvest_company_signals(p)
print(f"2. LinkedInScraper: {time.time()-t:.2f}s, hits={len(li)}")

# 3. Edgar
t = time.time()
ed = engine.edgar_scraper.harvest_events(p)
print(f"3. EdgarScraper: {time.time()-t:.2f}s")

# 4. Site Scraper
t = time.time()
st = engine.site_scraper.crawl_company_site(p)
print(f"4. SiteScraper: {time.time()-t:.2f}s, roles={len(st.get('roles', []))}, moves={len(st.get('movements', []))}")

# 5. Wire Scraper
t = time.time()
wr = engine.wire_scraper.scan_industry_wires_for_company(p)
print(f"5. WireScraper: {time.time()-t:.2f}s")

print(f"Total time: {time.time()-t0:.2f}s")
