import os
import sys
import json
import time
import csv
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

PDL_API_KEY = os.getenv("PDL_API_KEY")

DEMO_COMPANIES = [
    {"name": "API Co., Ltd.",                    "domain": "api-odm.com",            "alt_name": "API Co"},
    {"name": "Apis Flora",                        "domain": "apisflora.com.br",       "alt_name": "Apis Flora"},
    {"name": "Cmbio",                             "domain": "cmbio.io",               "alt_name": "Cmbio"},
    {"name": "Caltron Clays & Chemicals Pvt. Ltd.", "domain": "caltronclays.com",   "alt_name": "Caltron Clays"},
    {"name": "Greenspace Herbs",                  "domain": "greenspaceherbs.com",    "alt_name": "Greenspace Herbs"},
    {"name": "Wisesorbent Technology LLC",        "domain": "wisesorbent.com",        "alt_name": "Wisesorbent"},
    {"name": "PRONTO",                            "domain": "prontous.com",           "alt_name": "Pronto"},
]

HEADERS = {
    "X-Api-Key": PDL_API_KEY,
    "Content-Type": "application/json"
}

def clean_emails(p):
    emails = []
    raw_emails = p.get("emails")
    if isinstance(raw_emails, list):
        for e in raw_emails:
            if isinstance(e, dict) and e.get("address"):
                emails.append(f"{e.get('address')}")
            elif isinstance(e, str):
                emails.append(e)
    w_email = p.get("work_email")
    if isinstance(w_email, str):
        emails.append(w_email)
    p_emails = p.get("personal_emails")
    if isinstance(p_emails, list):
        for pe in p_emails:
            if isinstance(pe, str):
                emails.append(pe)
    return list(dict.fromkeys(emails))

def clean_phones(p):
    phones = []
    raw_phones = p.get("phone_numbers")
    if isinstance(raw_phones, list):
        for ph in raw_phones:
            if isinstance(ph, str):
                phones.append(ph)
            elif isinstance(ph, dict) and ph.get("number"):
                phones.append(ph.get("number"))
    m_phone = p.get("mobile_phone")
    if isinstance(m_phone, str):
        phones.append(m_phone)
    return list(dict.fromkeys(phones))

def clean_socials(p):
    socials = {}
    if p.get("linkedin_url"):
        socials["linkedin"] = p.get("linkedin_url")
    if p.get("twitter_url"):
        socials["twitter"] = p.get("twitter_url")
    if p.get("facebook_url"):
        socials["facebook"] = p.get("facebook_url")
    for prof in p.get("profiles", []):
        if isinstance(prof, dict) and prof.get("network") and prof.get("url"):
            socials[prof["network"]] = prof["url"]
    return socials

results = {}
csv_rows = []

print("=" * 70)
print("RUNNING PDL EXTRACTION & GENERATING FULL RESULTS CSV")
print("=" * 70)

for co in DEMO_COMPANIES:
    name = co["name"]
    domain = co["domain"]
    alt_name = co["alt_name"]
    
    co_data = {
        "company_info": {},
        "current_roster": [],
        "departures_alumni": [],
        "stats": {}
    }
    
    print(f"\n[*] Processing {name} ({domain})...")
    
    # 1. Company Enrichment
    try:
        url_co = f"https://api.peopledatalabs.com/v5/company/enrich?website={domain}"
        resp_co = requests.get(url_co, headers=HEADERS, timeout=10)
        if resp_co.status_code == 200:
            c_json = resp_co.json()
            tags = c_json.get("tags") or []
            co_data["company_info"] = {
                "name": c_json.get("display_name") or c_json.get("name"),
                "employee_count": c_json.get("employee_count"),
                "size_bucket": c_json.get("size"),
                "founded": c_json.get("founded"),
                "industry": c_json.get("industry") or c_json.get("industry_v2"),
                "location": f"{c_json.get('location', {}).get('locality', '')}, {c_json.get('location', {}).get('country', '')}".strip(", "),
                "linkedin_url": c_json.get("linkedin_url"),
                "technologies": tags[:8] if isinstance(tags, list) else []
            }
            print(f"  [Company Profile] Matched {co_data['company_info']['name']} (Employees: {co_data['company_info']['employee_count']})")
        else:
            co_data["company_info"] = {"status": f"Status {resp_co.status_code}"}
    except Exception as e:
        print(f"  [Company Error]: {e}")
        co_data["company_info"] = {"error": str(e)}

    # 2. Current Staff
    try:
        url_person = "https://api.peopledatalabs.com/v5/person/search"
        sql_roster = f"SELECT * FROM person WHERE job_company_website = '{domain}' OR job_company_name = '{alt_name}'"
        resp_roster = requests.post(url_person, headers=HEADERS, json={"sql": sql_roster.strip(), "size": 10}, timeout=10)
        if resp_roster.status_code == 200:
            r_json = resp_roster.json()
            total_staff = r_json.get("total", 0)
            co_data["stats"]["total_current_staff_in_pdl"] = total_staff
            for p in r_json.get("data", []):
                item = {
                    "name": p.get("full_name"),
                    "title": p.get("job_title"),
                    "seniority": p.get("job_title_levels", []),
                    "company": p.get("job_company_name") or name,
                    "start_date": p.get("job_start_date"),
                    "location": p.get("location_name"),
                    "emails": clean_emails(p),
                    "phones": clean_phones(p),
                    "linkedin": clean_socials(p).get("linkedin", p.get("linkedin_url"))
                }
                co_data["current_roster"].append(item)
                csv_rows.append({
                    "Target Company": name,
                    "Domain": domain,
                    "Person Name": item["name"],
                    "Record Type": "Current Employee / Decision Maker",
                    "Role / Title": item["title"],
                    "Start Date / Left Date": item["start_date"] or "N/A",
                    "Landing Company (if left)": "N/A (Current)",
                    "Emails": "; ".join(item["emails"]),
                    "Phone Numbers": "; ".join(item["phones"]),
                    "LinkedIn URL": item["linkedin"] or "",
                    "Location": item["location"] or ""
                })
            print(f"  [Current Staff] Found {total_staff} total (saved top {len(co_data['current_roster'])})")
        else:
            print(f"  [Staff Search Status {resp_roster.status_code}]: {resp_roster.text[:80]}")
    except Exception as e:
        print(f"  [Staff Error]: {e}")

    # 3. Departures
    try:
        url_person = "https://api.peopledatalabs.com/v5/person/search"
        sql_departures = f"SELECT * FROM person WHERE (experience.company.website = '{domain}' OR experience.company.name = '{alt_name}') AND (job_company_website != '{domain}' OR job_company_website IS NULL)"
        resp_dep = requests.post(url_person, headers=HEADERS, json={"sql": sql_departures.strip(), "size": 10}, timeout=10)
        if resp_dep.status_code == 200:
            d_json = resp_dep.json()
            total_dep = d_json.get("total", 0)
            co_data["stats"]["total_alumni_departures_in_pdl"] = total_dep
            for p in d_json.get("data", []):
                prev_roles = []
                left_date = "N/A"
                for exp in p.get("experience", []):
                    exp_site = str((exp.get("company") or {}).get("website", "")).lower()
                    exp_name = str((exp.get("company") or {}).get("name", "")).lower()
                    if domain in exp_site or alt_name.lower() in exp_name:
                        role_title = (exp.get("title") or {}).get("name") or "Team Member"
                        left_date = exp.get("end_date") or exp.get("start_date") or "N/A"
                        prev_roles.append(f"{role_title} (left: {left_date})")
                
                prev_title_str = " | ".join(prev_roles) if prev_roles else "Former Role"
                curr_title = p.get("job_title") or "N/A"
                curr_co = p.get("job_company_name") or p.get("job_company_website") or "Unknown / Self-Employed"
                
                dep_item = {
                    "name": p.get("full_name"),
                    "previous_roles": prev_title_str,
                    "left_date": left_date,
                    "current_landing_title": curr_title,
                    "current_landing_company": curr_co,
                    "emails": clean_emails(p),
                    "phones": clean_phones(p),
                    "linkedin": clean_socials(p).get("linkedin", p.get("linkedin_url")),
                    "location": p.get("location_name")
                }
                co_data["departures_alumni"].append(dep_item)
                csv_rows.append({
                    "Target Company": name,
                    "Domain": domain,
                    "Person Name": dep_item["name"],
                    "Record Type": "Alumni / Departure (Left Company)",
                    "Role / Title": f"Was: {prev_title_str} -> NOW: {curr_title}",
                    "Start Date / Left Date": left_date,
                    "Landing Company (if left)": curr_co,
                    "Emails": "; ".join(dep_item["emails"]),
                    "Phone Numbers": "; ".join(dep_item["phones"]),
                    "LinkedIn URL": dep_item["linkedin"] or "",
                    "Location": dep_item["location"] or ""
                })
            print(f"  [Departures] Found {total_dep} alumni (saved top {len(co_data['departures_alumni'])})")
        else:
            print(f"  [Departure Search Status {resp_dep.status_code}]: {resp_dep.text[:80]}")
    except Exception as e:
        print(f"  [Departure Error]: {e}")

    results[name] = co_data
    time.sleep(0.3)

# Save JSON
out_json = r"C:\Users\joela\OneDrive\Documents\Python\bd-engine\pdl_demo_results.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\n[SAVED JSON] -> {out_json}")

# Save CSV
out_csv = r"C:\Users\joela\OneDrive\Documents\Python\bd-engine\pdl_people_and_departures.csv"
fieldnames = [
    "Target Company", "Domain", "Person Name", "Record Type", "Role / Title",
    "Start Date / Left Date", "Landing Company (if left)", "Emails", "Phone Numbers",
    "LinkedIn URL", "Location"
]

with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(csv_rows)

print(f"[SAVED CSV] -> {out_csv} ({len(csv_rows)} total rows)")
