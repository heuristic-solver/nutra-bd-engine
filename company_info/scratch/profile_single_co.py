import sys, os
sys.path.insert(0, os.path.abspath("."))
import time
from company_info.models.company import CompanyProfile
from company_info.pipeline.orchestrator import CompanyIntelligenceEngine

profiles = [
    CompanyProfile(
        company_name="Glanbia Nutritionals",
        domain="glanbianutritionals.com",
        website="https://www.glanbianutritionals.com",
        country="United States",
        specialty="Nutritional Ingredients"
    ),
    CompanyProfile(
        company_name="ChromaDex",
        domain="chromadex.com",
        website="https://www.chromadex.com",
        country="United States",
        specialty="Dietary Supplements & Ingredients"
    ),
    CompanyProfile(
        company_name="Balchem",
        domain="balchem.com",
        website="https://www.balchem.com",
        country="United States",
        specialty="Specialty Ingredients"
    )
]

engine = CompanyIntelligenceEngine(max_workers=4)

t0 = time.time()
for p in profiles:
    t_start = time.time()
    rep = engine.scan_company(p)
    t_end = time.time()
    print(f"\n==================== {p.company_name} ({t_end - t_start:.2f}s) ====================")
    print(f"Total Signals: {rep.total_signals_discovered}")
    print(f"Roles ({len(rep.role_changes)}):")
    for r in rep.role_changes:
        print(f"  - [{r.movement_type.value}] {r.person_name} | {r.role_title} | Source: {r.source_name}")
    print(f"Funding ({len(rep.funding_events)}):")
    for f in rep.funding_events:
        print(f"  - [{f.round_type.value}] {f.announcement_title} | Amount: {f.amount_raw} | USD: {f.amount_usd}")
    print(f"Movements ({len(rep.strategic_movements)}):")
    for m in rep.strategic_movements:
        print(f"  - [{m.category.value}] {m.headline}")

print(f"\nTOTAL TIME for 3 companies: {time.time() - t0:.2f}s")
