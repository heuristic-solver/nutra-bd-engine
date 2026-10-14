import os
import sys
import json
import time
import csv
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\.env")

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

if not APOLLO_API_KEY:
    print("[ERROR] APOLLO_API_KEY is missing from .env!")
    sys.exit(1)

HEADERS = {
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
    "X-Api-Key": APOLLO_API_KEY
}

# 1. Load companies from nutraceutical_kb.json
kb_path = r"c:\Users\joela\OneDrive\Documents\Python\company-research\matcher\nutraceutical_kb.json"
with open(kb_path, "r", encoding="utf-8") as f:
    kb = json.load(f)

def clean_domain(url_or_domain):
    if not url_or_domain:
        return ""
    raw = url_or_domain.strip().lower()
    if "://" in raw:
        parsed = urlparse(raw)
        netloc = parsed.netloc
    else:
        netloc = raw.split("/")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc

target_cohort = []
seen_domains = set()

for item in kb:
    name = item.get("company_name", "").strip()
    raw_web = item.get("domain") or item.get("known_website") or item.get("website")
    domain = clean_domain(raw_web)
    if domain and "." in domain and domain not in seen_domains and len(name) > 2:
        if domain not in ["linkedin.com", "facebook.com", "twitter.com", "instagram.com"]:
            seen_domains.add(domain)
            target_cohort.append({"name": name, "domain": domain})
    if len(target_cohort) >= 20:
        break

print(f"Loaded {len(target_cohort)} companies. Running enrichment & resolving full names...")

results = []
all_contacts = []

for idx, co in enumerate(target_cohort, 1):
    c_name = co["name"]
    c_domain = co["domain"]
    print(f"\n[{idx}/20] Processing {c_name} ({c_domain})...")
    
    org_record = {
        "company_name": c_name,
        "matched_name": "N/A",
        "domain": c_domain,
        "apollo_id": "N/A",
        "estimated_employees": "N/A",
        "founded_year": "N/A",
        "industry": "N/A",
        "hq_location": "N/A",
        "annual_revenue": "N/A",
        "total_funding": "N/A",
        "active_tech_stack": "",
        "active_job_postings_count": 0,
        "top_job_openings": "",
        "decision_makers_found": 0,
        "key_decision_makers_summary": "",
        "company_linkedin": "N/A"
    }
    
    # 1. Organization Match
    try:
        url_org = "https://api.apollo.io/api/v1/organizations/enrich"
        resp_org = requests.get(url_org, params={"domain": c_domain, "name": c_name}, headers=HEADERS, timeout=12)
        if resp_org.ok:
            data = resp_org.json().get("organization", {})
            if data:
                org_record["matched_name"] = data.get("name") or c_name
                org_record["apollo_id"] = data.get("id") or "N/A"
                org_record["company_linkedin"] = data.get("linkedin_url") or "N/A"
                org_record["estimated_employees"] = data.get("estimated_num_employees") or "N/A"
                org_record["founded_year"] = data.get("founded_year") or "N/A"
                org_record["industry"] = data.get("industry") or "N/A"
                city = data.get("city") or ""
                country = data.get("country") or ""
                org_record["hq_location"] = f"{city}, {country}".strip(", ")
                org_record["annual_revenue"] = data.get("annual_revenue_printed") or "N/A"
                org_record["total_funding"] = data.get("total_funding_printed") or "N/A"
                techs = [t.get("name") for t in data.get("current_technologies", [])[:6] if isinstance(t, dict)]
                org_record["active_tech_stack"] = "; ".join(techs)
    except Exception as e:
        print(f"  Org error: {e}")

    time.sleep(0.2)

    # 2. Decision Maker Search
    try:
        url_peop = "https://api.apollo.io/api/v1/mixed_people/api_search"
        payload = {
            "q_organization_domains_list": [c_domain],
            "person_seniorities": ["c_suite", "vp", "director", "head", "manager"],
            "page": 1,
            "per_page": 5
        }
        resp_peop = requests.post(url_peop, json=payload, headers=HEADERS, timeout=12)
        if resp_peop.ok:
            p_data = resp_peop.json()
            people = p_data.get("people", [])
            org_record["decision_makers_found"] = len(people)
            
            dm_list = []
            for p in people:
                pid = p.get("id")
                full_name = p.get("name")
                p_title = p.get("title") or "Executive"
                p_seniority = p.get("seniority") or "N/A"
                p_linkedin = p.get("linkedin_url") or "N/A"
                p_loc = p.get("city") or p.get("country") or "N/A"
                
                # If name is only single word or first name, resolve full identity via GET /people/{id}
                if pid and (not full_name or " " not in full_name.strip()):
                    try:
                        r_single = requests.get(f"https://api.apollo.io/api/v1/people/{pid}", headers=HEADERS, timeout=8)
                        if r_single.ok:
                            s_data = r_single.json().get("person", {})
                            if s_data.get("name"):
                                full_name = s_data.get("name")
                            if s_data.get("linkedin_url"):
                                p_linkedin = s_data.get("linkedin_url")
                            if s_data.get("city") or s_data.get("country"):
                                p_loc = f"{s_data.get('city','')}, {s_data.get('country','')}".strip(", ")
                        time.sleep(0.15)
                    except Exception:
                        pass
                
                full_name = full_name or p.get("first_name") or "Executive"
                dm_list.append(f"{full_name} ({p_title})")
                
                all_contacts.append({
                    "Company Name": org_record["matched_name"],
                    "Domain": c_domain,
                    "Person Name": full_name,
                    "Title": p_title,
                    "Seniority": p_seniority,
                    "Location": p_loc,
                    "LinkedIn URL": p_linkedin,
                    "Apollo Person ID": pid or "N/A"
                })
            
            org_record["key_decision_makers_summary"] = " | ".join(dm_list)
            print(f"  Matched {len(people)} leaders: {', '.join(dm_list[:3])}")
    except Exception as e:
        print(f"  People error: {e}")

    time.sleep(0.2)

    # 3. Job Postings
    if org_record["apollo_id"] != "N/A":
        try:
            url_jobs = f"https://api.apollo.io/api/v1/organizations/{org_record['apollo_id']}/job_postings"
            resp_jobs = requests.get(url_jobs, headers=HEADERS, timeout=8)
            if resp_jobs.ok:
                jobs = resp_jobs.json().get("job_postings", [])
                org_record["active_job_postings_count"] = len(jobs)
                org_record["top_job_openings"] = "; ".join([j.get("title") for j in jobs[:4] if j.get("title")])
        except Exception:
            pass

    results.append(org_record)
    time.sleep(0.15)

# Save JSON results
json_out = r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\apollo\apollo_20co_results.json"
with open(json_out, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

# Save CSV 1: Companies Enriched
csv_co_out = r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\apollo\apollo_20co_companies_enriched.csv"
fieldnames_co = list(results[0].keys())
with open(csv_co_out, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames_co)
    writer.writeheader()
    writer.writerows(results)

# Save CSV 2: Decision Makers
csv_dm_out = r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\apollo\apollo_20co_decision_makers.csv"
if all_contacts:
    fieldnames_dm = list(all_contacts[0].keys())
    with open(csv_dm_out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames_dm)
        writer.writeheader()
        writer.writerows(all_contacts)

print("\nSaved full results to JSON and CSV!")
