import os
import sys
import json
import csv
import time
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\.env")

API_KEY = os.getenv("SIGNALBASE_API_KEY")
BASE_URL = "https://www.trysignalbase.com/api/v2"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 1. Load the 20 companies from the enriched Apollo output
input_csv = r"C:\Users\joela\Downloads\apollo\nutraceutical_20_companies_apollo_enriched.csv"
companies_input = []

with open(input_csv, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        companies_input.append({
            "name": row.get("Company Name", "").strip(),
            "domain": row.get("Website Domain", "").strip(),
            "linkedin_url": row.get("Company LinkedIn URL", "").strip()
        })

print(f"Loaded {len(companies_input)} companies from {input_csv}")
print("Checking SignalBase API subscription and connectivity...\n")

# Check subscription status
sub_active = True
sub_error_msg = ""
try:
    test_res = requests.get(f"{BASE_URL}/companies", headers=HEADERS, params={"domain": "adm.com"}, timeout=10)
    if test_res.status_code == 403:
        err_json = test_res.json()
        if err_json.get("code") == "subscription_expired":
            sub_active = False
            sub_error_msg = err_json.get("error")
            print(f"[ALERT] SignalBase API returned 403 Forbidden: {sub_error_msg}\n")
except Exception as e:
    print(f"[WARN] Connection check exception: {e}\n")

final_rows = []

for idx, comp in enumerate(companies_input, 1):
    c_name = comp["name"]
    c_dom = comp["domain"]
    c_li = comp["linkedin_url"]
    print(f"[{idx:2}/{len(companies_input)}] Processing: {c_name} (Domain: {c_dom} | LI: {c_li})")

    domain = c_dom
    industry = ""
    country = ""
    emp_count = None
    founded_year = None
    description = ""
    specialties = []
    hiring_roles = []
    job_changes = []
    people_records = []
    funding_list = []
    acq_list = []

    if sub_active:
        # /companies
        try:
            params = {}
            if c_li and c_li != "N/A":
                params["linkedin_url"] = c_li
            elif domain:
                params["domain"] = domain
            if params:
                co_res = requests.get(f"{BASE_URL}/companies", headers=HEADERS, params=params, timeout=10)
                if co_res.status_code == 200:
                    c_items = co_res.json().get("data", [])
                    if c_items:
                        c_item = c_items[0]
                        domain = domain or c_item.get("website", "")
                        industry = c_item.get("industry", "")
                        country = c_item.get("headquartersCountry", "")
                        emp_count = c_item.get("employeeCount")
                        founded_year = c_item.get("foundedYear")
                        description = c_item.get("description") or ""
        except Exception as e:
            print(f"   Error fetching /companies: {e}")

        # /signals/hiring
        try:
            h_params = {"limit": 20}
            if domain:
                h_params["company_domain"] = domain
            elif c_li and c_li != "N/A":
                h_params["company_linkedin_url"] = c_li
            h_res = requests.get(f"{BASE_URL}/signals/hiring", headers=HEADERS, params=h_params, timeout=10)
            if h_res.status_code == 200:
                hiring_roles = h_res.json().get("data", [])
        except Exception as e:
            print(f"   Error fetching /signals/hiring: {e}")

        # /signals/job-changes
        try:
            jc_params = {"limit": 20}
            if domain:
                jc_params["company_domain"] = domain
            elif c_li and c_li != "N/A":
                jc_params["company_linkedin_url"] = c_li
            jc_res = requests.get(f"{BASE_URL}/signals/job-changes", headers=HEADERS, params=jc_params, timeout=10)
            if jc_res.status_code == 200:
                job_changes = jc_res.json().get("data", [])
        except Exception as e:
            print(f"   Error fetching /signals/job-changes: {e}")

        # /people
        try:
            p_params = {"limit": 20}
            if domain:
                p_params["company_domain"] = domain
            elif c_li and c_li != "N/A":
                p_params["company_linkedin_url"] = c_li
            p_res = requests.get(f"{BASE_URL}/people", headers=HEADERS, params=p_params, timeout=10)
            if p_res.status_code == 200:
                people_records = p_res.json().get("data", [])
        except Exception as e:
            print(f"   Error fetching /people: {e}")
    else:
        # Note the subscription expired status in remarks
        pass

    # Synthesize hiring summary
    hiring_titles = []
    hiring_urls = []
    for h in hiring_roles:
        t = h.get("title") or "Unknown Title"
        loc = h.get("location") or ""
        dp = h.get("datePosted") or ""
        url = h.get("jobUrl") or ""
        entry = f"{t} ({loc})" if loc else t
        if dp:
            entry += f" [Posted: {dp[:10]}]"
        hiring_titles.append(entry)
        if url:
            hiring_urls.append(url)

    hiring_summary_str = " | ".join(hiring_titles) if hiring_titles else ("No active postings recorded" if sub_active else "Blocked: SignalBase subscription expired")
    hiring_urls_str = " | ".join(hiring_urls) if hiring_urls else ""

    # Synthesize job changes summary
    jc_summaries = []
    for jc in job_changes:
        p_name = jc.get("personName") or "Executive"
        n_role = jc.get("newRole") or "New Role"
        occ = jc.get("occurredAt") or ""
        p_url = jc.get("personLinkedinUrl") or ""
        entry = f"{p_name} -> {n_role}"
        if occ:
            entry += f" [{occ[:10]}]"
        if p_url:
            entry += f" ({p_url})"
        jc_summaries.append(entry)

    jc_summary_str = " | ".join(jc_summaries) if jc_summaries else ("No recent job changes recorded" if sub_active else "Blocked: SignalBase subscription expired")

    # Synthesize people / roster summary
    people_summaries = []
    for p in people_records:
        pn = p.get("name") or "Person"
        pt = p.get("title") or "Role"
        pli = p.get("linkedin_url") or ""
        entry = f"{pn} ({pt})"
        if pli:
            entry += f" - {pli}"
        people_summaries.append(entry)

    people_summary_str = " | ".join(people_summaries) if people_summaries else ("None recorded" if sub_active else "Blocked: SignalBase subscription expired")

    row_data = {
        "Company Name": c_name,
        "Website Domain": domain,
        "LinkedIn URL": c_li,
        "SignalBase API Status": "Success (Live Query)" if sub_active else "HTTP 403 (Subscription Expired)",
        "HQ Country": country,
        "Industry": industry,
        "Employee Count": emp_count if emp_count is not None else "",
        "Founded Year": founded_year if founded_year is not None else "",
        "Active Job Postings Count": len(hiring_roles),
        "Active Job Postings Summary": hiring_summary_str,
        "Active Job Postings URLs": hiring_urls_str,
        "Job Changes Count": len(job_changes),
        "Job Changes / Movement Summary": jc_summary_str,
        "Key People / Roster Summary": people_summary_str,
        "Funding Rounds Count": len(funding_list),
        "Funding Summary": "None recorded" if sub_active else "N/A",
        "Acquisitions Summary": "None recorded" if sub_active else "N/A",
        "Company Description": description if sub_active else f"SignalBase query attempted via key {API_KEY[:8]}... but API returned: subscription_expired. Please renew subscription to pull live SignalBase data."
    }
    final_rows.append(row_data)

# Export to CSV
out_fields = [
    "Company Name",
    "Website Domain",
    "LinkedIn URL",
    "SignalBase API Status",
    "HQ Country",
    "Industry",
    "Employee Count",
    "Founded Year",
    "Active Job Postings Count",
    "Active Job Postings Summary",
    "Active Job Postings URLs",
    "Job Changes Count",
    "Job Changes / Movement Summary",
    "Key People / Roster Summary",
    "Funding Rounds Count",
    "Funding Summary",
    "Acquisitions Summary",
    "Company Description"
]

out_paths = [
    r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\signalbase_20co_enriched.csv",
    r"C:\Users\joela\Downloads\signalbase_20co_enriched.csv",
    r"C:\Users\joela\Downloads\apollo\signalbase_20co_enriched.csv"
]

for p in out_paths:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(final_rows)
    print(f"Exported: {p}")

print("\nProcess finished.")
