import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

PDL_API_KEY = os.getenv("PDL_API_KEY")

DEMO_COMPANIES = [
    {"name": "API Co., Ltd.",                   "domain": "api-odm.com",            "alt_name": "API Co"},
    {"name": "Apis Flora",                       "domain": "apisflora.com.br",       "alt_name": "Apis Flora"},
    {"name": "Cmbio",                            "domain": "cmbio.io",               "alt_name": "Cmbio"},
    {"name": "Caltron Clays & Chemicals Pvt. Ltd.", "domain": "caltronclays.com",   "alt_name": "Caltron Clays"},
    {"name": "Greenspace Herbs",                 "domain": "greenspaceherbs.com",    "alt_name": "Greenspace Herbs"},
    {"name": "Wisesorbent Technology LLC",       "domain": "wisesorbent.com",        "alt_name": "Wisesorbent Technology"},
    {"name": "PRONTO",                           "domain": "prontous.com",           "alt_name": "Pronto"},
]

HEADERS = {
    "X-Api-Key": PDL_API_KEY,
    "Content-Type": "application/json"
}

def test_company_enrichment():
    print("=" * 70)
    print("STEP 1: PDL COMPANY ENRICHMENT API")
    print("=" * 70)
    results = {}
    
    for co in DEMO_COMPANIES:
        name = co["name"]
        domain = co["domain"]
        print(f"\n[ENRICHING COMPANY] {name} ({domain})...")
        
        # Try by website first
        url = f"https://api.peopledatalabs.com/v2/company/enrich?website={domain}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            results[name] = data
            print(f"  [SUCCESS 200] Match: {data.get('display_name') or data.get('name')}")
            print(f"    • Headcount: {data.get('employee_count')} (range: {data.get('employee_count_range')})")
            print(f"    • Founded: {data.get('founded')}")
            print(f"    • Industry: {data.get('industry')}")
            print(f"    • Location: {data.get('location', {}).get('locality')}, {data.get('location', {}).get('country')}")
            print(f"    • Size Bucket: {data.get('size')}")
            print(f"    • LinkedIn: {data.get('linkedin_url')}")
            tags = data.get('tags', [])
            if tags:
                print(f"    • Tech/Keywords: {', '.join(tags[:8])}")
        elif resp.status_code == 404:
            # Fallback to name search
            print(f"  [404 on domain {domain}] -> Trying company name lookup...")
            url_name = f"https://api.peopledatalabs.com/v2/company/enrich?name={co['alt_name']}"
            resp_name = requests.get(url_name, headers=HEADERS, timeout=15)
            if resp_name.status_code == 200:
                data = resp_name.json()
                results[name] = data
                print(f"  [SUCCESS 200 via Name] Match: {data.get('display_name') or data.get('name')}")
                print(f"    • Headcount: {data.get('employee_count')}")
                print(f"    • Location: {data.get('location', {}).get('locality')}, {data.get('location', {}).get('country')}")
            else:
                print(f"  [NOT FOUND] Status {resp_name.status_code}")
                results[name] = {"error": "Not found in PDL"}
        else:
            print(f"  [ERROR {resp.status_code}] {resp.text[:150]}")
            results[name] = {"error": resp.text}
        
        time.sleep(0.5)

    with open("pdl_company_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    return results

def test_person_search_roster():
    print("\n" + "=" * 70)
    print("STEP 2: PDL PERSON SEARCH - CURRENT EMPLOYEES & DECISION MAKERS")
    print("=" * 70)
    roster_results = {}
    
    for co in DEMO_COMPANIES:
        name = co["name"]
        domain = co["domain"]
        alt_name = co["alt_name"]
        print(f"\n[SEARCHING CURRENT STAFF] {name}...")
        
        # PDL SQL query
        sql_query = f"""
        SELECT full_name, job_title, job_title_levels, job_company_name, work_email, personal_emails, mobile_phone, phone_numbers, linkedin_url, job_start_date
        FROM person
        WHERE job_company_website = '{domain}' OR job_company_name = '{alt_name}'
        LIMIT 10
        """
        
        url = "https://api.peopledatalabs.com/v2/person/search"
        payload = {"sql": sql_query.strip(), "size": 10}
        
        try:
            resp = requests.post(url, headers=HEADERS, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                people = data.get("data", [])
                total = data.get("total", len(people))
                roster_results[name] = people
                print(f"  [SUCCESS] Found {total} total records (showing up to {len(people)}):")
                for p in people:
                    work_email = p.get("work_email") or (p.get("personal_emails", [None])[0])
                    phone = p.get("mobile_phone") or (p.get("phone_numbers", [None])[0])
                    start = p.get("job_start_date", "N/A")
                    print(f"    • {p.get('full_name')} | {p.get('job_title')} (Started: {start})")
                    if work_email or phone or p.get("linkedin_url"):
                        print(f"      Contact: Email={work_email} | Phone={phone} | LinkedIn={p.get('linkedin_url')}")
            else:
                print(f"  [ERROR {resp.status_code}] {resp.text[:150]}")
                roster_results[name] = {"error": resp.text}
        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            roster_results[name] = {"error": str(e)}

        time.sleep(0.5)

    with open("pdl_roster_results.json", "w", encoding="utf-8") as f:
        json.dump(roster_results, f, indent=2)
    return roster_results

def test_person_search_departures():
    print("\n" + "=" * 70)
    print("STEP 3: PDL PERSON SEARCH - DEPARTURES & ALUMNI (WHO LEFT & WHERE)")
    print("=" * 70)
    departure_results = {}
    
    for co in DEMO_COMPANIES:
        name = co["name"]
        domain = co["domain"]
        alt_name = co["alt_name"]
        print(f"\n[SEARCHING DEPARTURES / ALUMNI] {name}...")
        
        # Search people whose past experience includes this company, but current job is different
        sql_query = f"""
        SELECT full_name, job_title, job_company_name, job_company_website, experience, work_email, linkedin_url
        FROM person
        WHERE (experience.company.website = '{domain}' OR experience.company.name = '{alt_name}')
        AND job_company_website != '{domain}'
        LIMIT 10
        """
        
        url = "https://api.peopledatalabs.com/v2/person/search"
        payload = {"sql": sql_query.strip(), "size": 10}
        
        try:
            resp = requests.post(url, headers=HEADERS, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                people = data.get("data", [])
                total = data.get("total", len(people))
                departure_results[name] = people
                print(f"  [SUCCESS] Found {total} alumni / departures (showing top {len(people)}):")
                for p in people:
                    curr_co = p.get("job_company_name") or p.get("job_company_website") or "Unknown"
                    curr_title = p.get("job_title") or "Unknown"
                    
                    # Extract previous role at our target company
                    prev_roles = []
                    for exp in p.get("experience", []):
                        exp_co = (exp.get("company") or {}).get("name", "")
                        exp_site = (exp.get("company") or {}).get("website", "")
                        if domain in str(exp_site).lower() or alt_name.lower() in str(exp_co).lower():
                            exp_title = (exp.get("title") or {}).get("name", "N/A")
                            end_dt = exp.get("end_date", "N/A")
                            prev_roles.append(f"{exp_title} (left: {end_dt})")
                    
                    prev_str = " | ".join(prev_roles) if prev_roles else "Former Employee"
                    print(f"    • {p.get('full_name')}: Was [{prev_str}] ──► NOW [{curr_title} @ {curr_co}]")
                    if p.get("work_email") or p.get("linkedin_url"):
                        print(f"      Contact: {p.get('work_email')} | {p.get('linkedin_url')}")
            else:
                print(f"  [ERROR {resp.status_code}] {resp.text[:150]}")
                departure_results[name] = {"error": resp.text}
        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            departure_results[name] = {"error": str(e)}

        time.sleep(0.5)

    with open("pdl_departures_results.json", "w", encoding="utf-8") as f:
        json.dump(departure_results, f, indent=2)
    return departure_results

def test_person_enrichment():
    print("\n" + "=" * 70)
    print("STEP 4: PDL PERSON ENRICHMENT (KEY CONTACT IDENTITIES)")
    print("=" * 70)
    
    # Let's test enriching key personnel discovered previously
    targets = [
        {"name": "Kelly Moffat", "company": "Cmbio", "website": "cmbio.io"},
        {"name": "Prashant Halbe", "company": "Pronto", "website": "prontous.com"},
        {"name": "Marcelo Gobara", "company": "Apis Flora", "website": "apisflora.com.br"},
    ]
    
    enrich_results = {}
    for t in targets:
        print(f"\n[ENRICHING PERSON] {t['name']} @ {t['company']}...")
        url = f"https://api.peopledatalabs.com/v2/person/enrich?name={t['name']}&company={t['company']}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                enrich_results[t['name']] = data
                print(f"  [SUCCESS 200] Match: {data.get('full_name')} | Title: {data.get('job_title')}")
                print(f"    • Work Email: {data.get('work_email')}")
                print(f"    • Personal Emails: {data.get('personal_emails')}")
                print(f"    • Phone: {data.get('mobile_phone') or data.get('phone_numbers')}")
                print(f"    • LinkedIn: {data.get('linkedin_url')}")
                print(f"    • Location: {data.get('location_name')}")
            else:
                print(f"  [STATUS {resp.status_code}] {resp.text[:120]}")
        except Exception as e:
            print(f"  [ERROR] {e}")
        time.sleep(0.5)

    with open("pdl_enrichment_results.json", "w", encoding="utf-8") as f:
        json.dump(enrich_results, f, indent=2)

if __name__ == "__main__":
    test_company_enrichment()
    test_person_search_roster()
    test_person_search_departures()
    test_person_enrichment()
    print("\n" + "=" * 70)
    print("ALL PDL RUNS COMPLETE! Results saved to JSON files.")
    print("=" * 70)
