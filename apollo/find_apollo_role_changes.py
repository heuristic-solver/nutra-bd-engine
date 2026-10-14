import os
import sys
import json
import time
import csv
from datetime import datetime
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\.env")

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

HEADERS = {
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
    "X-Api-Key": APOLLO_API_KEY
}

# Load our 20 companies results
with open(r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\apollo\apollo_20co_results.json", "r", encoding="utf-8") as f:
    companies = json.load(f)

print("=" * 70)
print("SCANNING APOLLO FOR RECENT ROLE CHANGES, JOINS & DEPARTURES (20 NUTRA COS)")
print("=" * 70)

role_changes = []

for idx, co in enumerate(companies, 1):
    c_name = co.get("matched_name") or co.get("company_name")
    domain = co.get("domain")
    apollo_id = co.get("apollo_id")
    
    print(f"\n[{idx}/20] Scanning {c_name} ({domain})...")
    
    # 1. Search for people associated with this domain
    url_peop = "https://api.apollo.io/api/v1/mixed_people/api_search"
    payload = {
        "q_organization_domains_list": [domain],
        "person_seniorities": ["c_suite", "vp", "director", "head", "manager"],
        "page": 1,
        "per_page": 10
    }
    
    try:
        r = requests.post(url_peop, json=payload, headers=HEADERS, timeout=12)
        if r.ok:
            people = r.json().get("people", [])
            for p in people:
                pid = p.get("id")
                if not pid:
                    continue
                
                # Fetch full employment history
                try:
                    r_p = requests.get(f"https://api.apollo.io/api/v1/people/{pid}", headers=HEADERS, timeout=8)
                    if not r_p.ok:
                        continue
                    person = r_p.json().get("person", {})
                    p_name = person.get("name") or p.get("name") or "Executive"
                    curr_title = person.get("title") or p.get("title") or "Executive"
                    curr_org = (person.get("organization") or {}).get("name") or c_name
                    p_linkedin = person.get("linkedin_url") or p.get("linkedin_url") or ""
                    p_loc = f"{person.get('city','')}, {person.get('country','')}".strip(", ")
                    emp_history = person.get("employment_history", [])
                    
                    if not emp_history:
                        continue
                    
                    # A. Check if they currently work at this company and joined in 2025 or 2026
                    curr_job = emp_history[0]
                    start_d = curr_job.get("start_date") or ""
                    is_current = curr_job.get("current", False) or domain in str(person.get("organization", {}).get("primary_domain", "")).lower()
                    
                    if is_current and start_d:
                        # Check if start date is 2025 or 2026
                        if start_d.startswith("2025") or start_d.startswith("2026"):
                            # Previous role before this one
                            prev_role_str = "N/A"
                            if len(emp_history) > 1:
                                prev_j = emp_history[1]
                                prev_role_str = f"{prev_j.get('title')} @ {prev_j.get('organization_name')}"
                            
                            change_item = {
                                "Target Company": c_name,
                                "Domain": domain,
                                "Person Name": p_name,
                                "Change Type": "RECENT JOIN / PROMOTION",
                                "Role / Title": curr_title,
                                "Effective Date": start_d,
                                "Details": f"Joined {c_name} as {curr_title} (Previous: {prev_role_str})",
                                "LinkedIn URL": p_linkedin,
                                "Location": p_loc
                            }
                            role_changes.append(change_item)
                            print(f"  [RECENT JOIN] {p_name} -> {curr_title} (Started: {start_d})")
                    
                    # B. Check if they previously worked at this company and LEFT (Alumni)
                    for j_idx, past_j in enumerate(emp_history[1:], 1):
                        past_org = str(past_j.get("organization_name", "")).lower()
                        if c_name.lower() in past_org or domain in str(past_j.get("company_website", "")).lower():
                            # They were at our target company in the past!
                            end_d = past_j.get("end_date") or "N/A"
                            past_title = past_j.get("title") or "Former Role"
                            
                            change_item = {
                                "Target Company": c_name,
                                "Domain": domain,
                                "Person Name": p_name,
                                "Change Type": "DEPARTURE / ALUMNI",
                                "Role / Title": f"Was: {past_title} -> NOW: {curr_title}",
                                "Effective Date": f"Left: {end_d}",
                                "Details": f"Departed {c_name} (Was: {past_title}) ──► Now at [{curr_org}] as {curr_title}",
                                "LinkedIn URL": p_linkedin,
                                "Location": p_loc
                            }
                            role_changes.append(change_item)
                            print(f"  [DEPARTURE] {p_name} LEFT {c_name} ({past_title}, left: {end_d}) ──► NOW [{curr_title} @ {curr_org}]")
                            break

                    time.sleep(0.12)
                except Exception as e:
                    pass
    except Exception as e:
        print(f"  Error: {e}")

    time.sleep(0.2)

# Save JSON
out_json = r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\apollo\apollo_20co_role_changes.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(role_changes, f, indent=2, default=str)

# Save CSV
out_csv = r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\apollo\apollo_20co_role_changes.csv"
if role_changes:
    fieldnames = list(role_changes[0].keys())
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(role_changes)

print(f"\n[COMPLETE] Found {len(role_changes)} total role changes (joins & departures) across the 20 companies!")
print(f"Saved to {out_csv} and {out_json}")
