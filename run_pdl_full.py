import os
import sys
import json
import time
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
    # check p.get("emails")
    raw_emails = p.get("emails")
    if isinstance(raw_emails, list):
        for e in raw_emails:
            if isinstance(e, dict) and e.get("address"):
                emails.append(f"{e.get('address')} ({e.get('type','general')})")
            elif isinstance(e, str):
                emails.append(e)
    # check work_email
    w_email = p.get("work_email")
    if isinstance(w_email, str):
        emails.append(f"{w_email} (work)")
    # check personal_emails
    p_emails = p.get("personal_emails")
    if isinstance(p_emails, list):
        for pe in p_emails:
            if isinstance(pe, str):
                emails.append(f"{pe} (personal)")
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

print("=" * 70)
print("PEOPLE DATA LABS (PDL) FULL INTELLIGENCE RUN ACROSS DEMO LIST")
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
    
    print(f"\n==================================================")
    print(f"[*] TARGET: {name} (domain: {domain})")
    print(f"==================================================")
    
    # -------------------------------------------------------------
    # 1. Company Enrichment
    # -------------------------------------------------------------
    print("  --> [1/3] Fetching Company Profile...")
    url_co = f"https://api.peopledatalabs.com/v5/company/enrich?website={domain}"
    resp_co = requests.get(url_co, headers=HEADERS, timeout=15)
    
    if resp_co.status_code == 200:
        c_json = resp_co.json()
        co_data["company_info"] = {
            "name": c_json.get("display_name") or c_json.get("name"),
            "employee_count": c_json.get("employee_count"),
            "size_bucket": c_json.get("size"),
            "founded": c_json.get("founded"),
            "industry": c_json.get("industry") or c_json.get("industry_v2"),
            "location": f"{c_json.get('location', {}).get('locality', '')}, {c_json.get('location', {}).get('country', '')}".strip(", "),
            "linkedin_url": c_json.get("linkedin_url"),
            "technologies": c_json.get("tags", [])[:10],
            "profiles": c_json.get("profiles", [])
        }
        print(f"      [OK] Matched: {co_data['company_info']['name']} | Employees: {co_data['company_info']['employee_count']} | HQ: {co_data['company_info']['location']}")
    elif resp_co.status_code == 404:
        # Fallback to name
        url_co_name = f"https://api.peopledatalabs.com/v5/company/enrich?name={alt_name}"
        resp_co_name = requests.get(url_co_name, headers=HEADERS, timeout=15)
        if resp_co_name.status_code == 200:
            c_json = resp_co_name.json()
            co_data["company_info"] = {
                "name": c_json.get("display_name") or c_json.get("name"),
                "employee_count": c_json.get("employee_count"),
                "size_bucket": c_json.get("size"),
                "founded": c_json.get("founded"),
                "industry": c_json.get("industry"),
                "location": f"{c_json.get('location', {}).get('locality', '')}, {c_json.get('location', {}).get('country', '')}".strip(", "),
                "linkedin_url": c_json.get("linkedin_url"),
                "technologies": c_json.get("tags", [])[:10],
            }
            print(f"      [OK via Name] Matched: {co_data['company_info']['name']} | Employees: {co_data['company_info']['employee_count']}")
        else:
            print(f"      [NOT FOUND] Company record not found in PDL dataset")
            co_data["company_info"] = {"status": "Not Found"}
    else:
        print(f"      [ERROR {resp_co.status_code}]: {resp_co.text[:100]}")
    
    time.sleep(0.4)

    # -------------------------------------------------------------
    # 2. Current Employees & Decision Makers
    # -------------------------------------------------------------
    print("  --> [2/3] Searching Current Decision Makers & Staff...")
    url_person = "https://api.peopledatalabs.com/v5/person/search"
    
    sql_roster = f"""
    SELECT *
    FROM person
    WHERE job_company_website = '{domain}' OR job_company_name = '{alt_name}'
    """
    
    resp_roster = requests.post(url_person, headers=HEADERS, json={"sql": sql_roster.strip(), "size": 15}, timeout=15)
    if resp_roster.status_code == 200:
        r_json = resp_roster.json()
        total_staff = r_json.get("total", 0)
        co_data["stats"]["total_current_staff_in_pdl"] = total_staff
        for p in r_json.get("data", []):
            item = {
                "name": p.get("full_name"),
                "title": p.get("job_title"),
                "seniority": p.get("job_title_levels", []),
                "company": p.get("job_company_name"),
                "start_date": p.get("job_start_date"),
                "location": p.get("location_name"),
                "emails": clean_emails(p),
                "phones": clean_phones(p),
                "socials": clean_socials(p)
            }
            co_data["current_roster"].append(item)
        print(f"      [OK] Found {total_staff} total current profiles in PDL (retrieved top {len(co_data['current_roster'])})")
        for item in co_data["current_roster"][:3]:
            print(f"        • {item['name']} | {item['title']} | Start: {item['start_date']} | Emails: {item['emails'][:2]}")
    else:
        print(f"      [ERROR {resp_roster.status_code}]: {resp_roster.text[:100]}")
        co_data["stats"]["total_current_staff_in_pdl"] = 0

    time.sleep(0.4)

    # -------------------------------------------------------------
    # 3. Departures & Alumni (Who Left & Where They Landed)
    # -------------------------------------------------------------
    print("  --> [3/3] Searching Departures & Alumni (Who Left)...")
    sql_departures = f"""
    SELECT *
    FROM person
    WHERE (experience.company.website = '{domain}' OR experience.company.name = '{alt_name}')
    AND (job_company_website != '{domain}' OR job_company_website IS NULL)
    """
    
    resp_dep = requests.post(url_person, headers=HEADERS, json={"sql": sql_departures.strip(), "size": 15}, timeout=15)
    if resp_dep.status_code == 200:
        d_json = resp_dep.json()
        total_dep = d_json.get("total", 0)
        co_data["stats"]["total_alumni_departures_in_pdl"] = total_dep
        for p in d_json.get("data", []):
            # Extract previous role at our target co
            prev_roles = []
            for exp in p.get("experience", []):
                exp_site = str((exp.get("company") or {}).get("website", "")).lower()
                exp_name = str((exp.get("company") or {}).get("name", "")).lower()
                if domain in exp_site or alt_name.lower() in exp_name:
                    role_title = (exp.get("title") or {}).get("name") or "Team Member"
                    end_d = exp.get("end_date") or "N/A"
                    start_d = exp.get("start_date") or "N/A"
                    prev_roles.append({
                        "title": role_title,
                        "start_date": start_d,
                        "end_date": end_d
                    })
            
            dep_item = {
                "name": p.get("full_name"),
                "previous_roles_at_target": prev_roles,
                "current_landing_title": p.get("job_title"),
                "current_landing_company": p.get("job_company_name") or p.get("job_company_website"),
                "emails": clean_emails(p),
                "phones": clean_phones(p),
                "socials": clean_socials(p),
                "location": p.get("location_name")
            }
            co_data["departures_alumni"].append(dep_item)
        print(f"      [OK] Found {total_dep} total alumni/departures in PDL (retrieved top {len(co_data['departures_alumni'])})")
        for dep in co_data["departures_alumni"][:3]:
            prev_desc = dep["previous_roles_at_target"][0]["title"] if dep["previous_roles_at_target"] else "Former"
            prev_end = dep["previous_roles_at_target"][0]["end_date"] if dep["previous_roles_at_target"] else "N/A"
            print(f"        • {dep['name']}: was [{prev_desc} (left: {prev_end})] ──► NOW [{dep['current_landing_title']} @ {dep['current_landing_company']}]")
    else:
        print(f"      [ERROR {resp_dep.status_code}]: {resp_dep.text[:100]}")
        co_data["stats"]["total_alumni_departures_in_pdl"] = 0

    results[name] = co_data
    time.sleep(0.5)

# Save consolidated outputs
out_file = r"C:\Users\joela\OneDrive\Documents\Python\bd-engine\pdl_demo_results.json"
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print("\n" + "=" * 70)
print(f"ALL 7 DEMO COMPANIES PROCESSED THROUGH PDL! Saved -> {out_file}")
print("=" * 70)
