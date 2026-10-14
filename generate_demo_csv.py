import os
import sys
import json
import csv
import time
import requests

def load_api_key():
    key = os.environ.get("SIGNALBASE_API_KEY")
    if not key and os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("SIGNALBASE_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return key

API_KEY = load_api_key()
BASE_URL = "https://www.trysignalbase.com/api/v2"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 1. Load the target companies from CSV
input_csv = "Demo List - Sheet1.csv"
companies_input = []
with open(input_csv, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        companies_input.append({
            "name": row.get("Name", "").strip(),
            "linkedin_url": row.get("LinkedIn", "").strip()
        })

print(f"Loaded {len(companies_input)} companies from {input_csv}", flush=True)

# 2. Check if we have cached enrichment_result.json
enrichment_map = {}
if os.path.exists("enrichment_result.json"):
    with open("enrichment_result.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        for res in data.get("data", {}).get("results", []):
            inp_li = res.get("input", {}).get("linkedin_url", "")
            inp_name = res.get("input", {}).get("company_name", "")
            enrichment_map[inp_li] = res
            enrichment_map[inp_name] = res

final_rows = []

for idx, comp in enumerate(companies_input, 1):
    c_name = comp["name"]
    c_li = comp["linkedin_url"]
    print(f"\n[{idx}/{len(companies_input)}] Processing: {c_name} ({c_li})", flush=True)
    
    # Check enrichment data
    res_enrich = enrichment_map.get(c_li) or enrichment_map.get(c_name) or {}
    co_data = res_enrich.get("company") or {}
    signals = res_enrich.get("signals") or {}
    
    co_id = res_enrich.get("companyId")
    domain = co_data.get("domain") or ""
    industry = co_data.get("industry") or ""
    country = co_data.get("country") or ""
    emp_count = co_data.get("employeeCount")
    
    # 3. Query direct company endpoint if extra firmographics needed
    founded_year = None
    description = ""
    specialties = []
    
    try:
        co_res = requests.get(f"{BASE_URL}/companies", headers=HEADERS, params={"linkedin_url": c_li}, timeout=10)
        if co_res.status_code == 200:
            c_items = co_res.json().get("data", [])
            if c_items:
                c_item = c_items[0]
                if not domain and c_item.get("website"):
                    domain = c_item.get("website")
                if not industry and c_item.get("industry"):
                    industry = c_item.get("industry")
                if not country and c_item.get("headquartersCountry"):
                    country = c_item.get("headquartersCountry")
                if emp_count is None and c_item.get("employeeCount") is not None:
                    emp_count = c_item.get("employeeCount")
                founded_year = c_item.get("foundedYear")
                description = c_item.get("description") or ""
                specialties = c_item.get("specialties") or []
    except Exception as e:
        print(f"  Error fetching /companies: {e}", flush=True)
    
    # 4. Query direct hiring endpoint for full open roles
    hiring_roles = signals.get("hiring") or []
    try:
        h_params = {"limit": 20}
        if domain:
            h_params["company_domain"] = domain
        else:
            h_params["company_linkedin_url"] = c_li
            
        h_res = requests.get(f"{BASE_URL}/signals/hiring", headers=HEADERS, params=h_params, timeout=10)
        if h_res.status_code == 200:
            h_data = h_res.json().get("data", [])
            if len(h_data) > len(hiring_roles):
                hiring_roles = h_data
    except Exception as e:
        print(f"  Error fetching /signals/hiring: {e}", flush=True)

    # 5. Query direct job changes endpoint
    job_changes = signals.get("job_change") or []
    try:
        jc_params = {"limit": 20}
        if domain:
            jc_params["company_domain"] = domain
        else:
            jc_params["company_linkedin_url"] = c_li
            
        jc_res = requests.get(f"{BASE_URL}/signals/job-changes", headers=HEADERS, params=jc_params, timeout=10)
        if jc_res.status_code == 200:
            jc_data = jc_res.json().get("data", [])
            if len(jc_data) > len(job_changes):
                job_changes = jc_data
    except Exception as e:
        print(f"  Error fetching /signals/job-changes: {e}", flush=True)

    # 6. Query people endpoint for key personnel / executives
    people_records = []
    try:
        p_params = {"limit": 20}
        if domain:
            p_params["company_domain"] = domain
        else:
            p_params["company_linkedin_url"] = c_li
            
        p_res = requests.get(f"{BASE_URL}/people", headers=HEADERS, params=p_params, timeout=10)
        if p_res.status_code == 200:
            people_records = p_res.json().get("data", [])
    except Exception as e:
        print(f"  Error fetching /people: {e}", flush=True)

    # 7. Synthesize summaries
    # Funding summary
    funding_list = signals.get("funding") or []
    funding_summaries = []
    for f_item in funding_list:
        rtype = f_item.get("roundType") or "Round"
        amt = f_item.get("amount")
        curr = f_item.get("currency") or "USD"
        dt = f_item.get("announcedDate") or "Date N/A"
        invs = ", ".join(f_item.get("investors") or [])
        inv_str = f" (Investors: {invs})" if invs else ""
        if amt:
            funding_summaries.append(f"{rtype.upper()} - {curr} {amt:,.0f} [{dt}]{inv_str}")
        else:
            funding_summaries.append(f"{rtype.upper()} [{dt}]{inv_str}")
    funding_summary_str = " | ".join(funding_summaries) if funding_summaries else "None recorded"

    # Acquisition summary
    acq_list = signals.get("acquisition") or []
    acq_summaries = []
    for a_item in acq_list:
        acq_co = a_item.get("acquiringCompanyName") or "Unknown"
        amt = a_item.get("amount")
        curr = a_item.get("currency") or "USD"
        dt = a_item.get("announcedDate") or "Date N/A"
        if amt:
            acq_summaries.append(f"Acquired by {acq_co} for {curr} {amt:,.0f} [{dt}]")
        else:
            acq_summaries.append(f"Acquired by {acq_co} [{dt}]")
    acq_summary_str = " | ".join(acq_summaries) if acq_summaries else "None recorded"

    # Hiring / Job Openings summary
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
    hiring_summary_str = " | ".join(hiring_titles) if hiring_titles else "No active postings recorded"
    hiring_urls_str = " | ".join(hiring_urls) if hiring_urls else ""

    # Job Changes summary
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
    jc_summary_str = " | ".join(jc_summaries) if jc_summaries else "No recent job changes recorded"

    # People / Roster summary
    people_summaries = []
    for p in people_records:
        pn = p.get("name") or "Person"
        pt = p.get("title") or "Role"
        pli = p.get("linkedin_url") or ""
        entry = f"{pn} ({pt})"
        if pli:
            entry += f" - {pli}"
        people_summaries.append(entry)
    people_summary_str = " | ".join(people_summaries) if people_summaries else "None recorded"

    row_data = {
        "Company Name": c_name,
        "Website Domain": domain,
        "LinkedIn URL": c_li,
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
        "Funding Summary": funding_summary_str,
        "Acquisitions Summary": acq_summary_str,
        "Company Description": description
    }
    final_rows.append(row_data)

# 8. Export to CSV in Downloads and Workspace
downloads_dir = os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\joela"), "Downloads")
downloads_csv_path = os.path.join(downloads_dir, "signalbase_demo_enriched.csv")
workspace_csv_path = "signalbase_demo_enriched.csv"

fieldnames = [
    "Company Name",
    "Website Domain",
    "LinkedIn URL",
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

print(f"\nWriting {len(final_rows)} enriched rows to {workspace_csv_path} and {downloads_csv_path}...", flush=True)

with open(workspace_csv_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(final_rows)

try:
    with open(downloads_csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)
    print(f"Successfully saved to {downloads_csv_path}!", flush=True)
except Exception as e:
    print(f"Error saving to Downloads: {e}", flush=True)

print("Export completed successfully!", flush=True)
