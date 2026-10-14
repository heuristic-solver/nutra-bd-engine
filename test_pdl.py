import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

PDL_API_KEY = os.getenv("PDL_API_KEY")

DEMO_DOMAINS = [
    {"name": "API Co., Ltd.",            "domain": "api-odm.com"},
    {"name": "Apis Flora",                "domain": "apisflora.com.br"},
    {"name": "Cmbio",                     "domain": "cmbio.io"},
    {"name": "Caltron Clays & Chemicals", "domain": "caltronclays.com"},
    {"name": "Greenspace Herbs",          "domain": "greenspaceherbs.com"},
    {"name": "Wisesorbent Technology",    "domain": "wisesorbent.com"},
    {"name": "PRONTO",                    "domain": "prontous.com"},
]

HEADERS = {
    "X-Api-Key": PDL_API_KEY or "",
    "Content-Type": "application/json"
}

def check_pdl_access():
    if not PDL_API_KEY:
        print("[ERROR] PDL_API_KEY is not set in environment or .env file.")
        print("To run PDL on the demo list, please provide your People Data Labs API key.")
        return False
    return True

def enrich_companies():
    if not check_pdl_access():
        return
    
    print("=" * 60)
    print("1. RUNNING PDL COMPANY ENRICHMENT ON DEMO LIST")
    print("=" * 60)
    
    company_results = {}
    for co in DEMO_DOMAINS:
        name = co["name"]
        domain = co["domain"]
        print(f"\n[COMPANY LOOKUP] {name} ({domain})...")
        
        url = f"https://api.peopledatalabs.com/v2/company/enrich?website={domain}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                company_results[name] = data
                print(f"  [OK] Found: {data.get('display_name', name)}")
                print(f"       Employee Count: {data.get('employee_count')}")
                print(f"       Industry: {data.get('industry')}")
                print(f"       Location: {data.get('location', {}).get('locality')}, {data.get('location', {}).get('country')}")
                print(f"       Technologies: {', '.join(data.get('tags', [])[:6])}")
            elif resp.status_code == 404:
                print(f"  [404] No company record found in PDL for domain {domain}")
            else:
                print(f"  [STATUS {resp.status_code}] {resp.text[:120]}")
        except Exception as e:
            print(f"  [ERROR] {e}")

    with open("pdl_company_results.json", "w", encoding="utf-8") as f:
        json.dump(company_results, f, indent=2)

def search_role_changes_and_departures():
    if not check_pdl_access():
        return

    print("\n" + "=" * 60)
    print("2. SEARCHING PDL FOR RECENT DEPARTURES & ROLE CHANGES")
    print("=" * 60)
    
    movement_results = {}
    for co in DEMO_DOMAINS:
        name = co["name"]
        domain = co["domain"]
        print(f"\n[MOVEMENT SEARCH] Searching departures / former employees for {name} ({domain})...")
        
        # PDL Person Search SQL query
        sql_query = f"""
        SELECT * FROM person
        WHERE experience.company.website = '{domain}'
        AND experience.end_date >= '2025-01-01'
        AND job_company_website != '{domain}'
        LIMIT 20
        """
        
        url = "https://api.peopledatalabs.com/v2/person/search"
        payload = {
            "sql": sql_query.strip(),
            "size": 20
        }
        
        try:
            resp = requests.post(url, headers=HEADERS, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("data", [])
                movement_results[name] = records
                print(f"  [OK] Found {len(records)} departures / alumni moves")
                for person in records[:3]:
                    p_name = person.get("full_name")
                    curr_title = person.get("job_title")
                    curr_co = person.get("job_company_name")
                    emails = [e.get("address") for e in person.get("emails", []) if e.get("type") == "professional"]
                    print(f"    - {p_name} | NOW: {curr_title} @ {curr_co} | Email: {emails[0] if emails else 'N/A'}")
            else:
                print(f"  [STATUS {resp.status_code}] {resp.text[:120]}")
        except Exception as e:
            print(f"  [ERROR] {e}")

    with open("pdl_movement_results.json", "w", encoding="utf-8") as f:
        json.dump(movement_results, f, indent=2)

if __name__ == "__main__":
    enrich_companies()
    search_role_changes_and_departures()
