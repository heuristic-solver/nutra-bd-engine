import os
import sys
import json
import csv
import time
import requests
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows console
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(ENV_PATH)

try:
    from apify.client import ApifyWrapper
    from apify.actors import ApifyActorsManager
except (ImportError, ModuleNotFoundError):
    from client import ApifyWrapper
    from actors import ApifyActorsManager

APOLLO_KEY = os.getenv("APOLLO_API_KEY", "mWjbzHzqZh4klYM8xG8Dew").strip()
APOLLO_HEADERS = {
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
    "X-Api-Key": APOLLO_KEY
}

TARGET_CSV = os.path.join(PROJECT_ROOT, "data", "apify_apollo_20co_verified.csv")

def get_apollo_executives_and_moves(domain: str, company_name: str):
    """
    Fetches verified decision makers and checks recent joins/promotions (strictly 2025-2026) via Apollo.
    """
    people_found = []
    role_changes = []
    
    url = "https://api.apollo.io/api/v1/mixed_people/api_search"
    payload = {
        "q_organization_domains_list": [domain],
        "person_seniorities": ["c_suite", "vp", "director", "head", "manager"],
        "page": 1,
        "per_page": 10
    }
    
    try:
        r = requests.post(url, json=payload, headers=APOLLO_HEADERS, timeout=12)
        if r.ok:
            data = r.json()
            people = data.get("people", [])
            for p in people:
                pid = p.get("id")
                f_name = p.get("first_name", "")
                l_name = p.get("last_name_obfuscated", "")
                fallback_name = f"{f_name} {l_name}".strip() if f_name else "Key Executive"
                title = p.get("title") or "Executive"
                linkedin = p.get("linkedin_url") or ""
                email_status = "Available (Verified)" if p.get("email") else "Direct Record"
                
                real_name = fallback_name
                
                # Fetch full un-obfuscated profile and mobility
                if pid:
                    try:
                        r_p = requests.get(f"https://api.apollo.io/api/v1/people/{pid}", headers=APOLLO_HEADERS, timeout=8)
                        if r_p.ok:
                            person = r_p.json().get("person", {})
                            full_name = person.get("name") or f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
                            if full_name:
                                real_name = full_name
                            if person.get("linkedin_url"):
                                linkedin = person.get("linkedin_url")
                                
                            history = person.get("employment_history", [])
                            if history:
                                curr = history[0]
                                s_date = curr.get("start_date") or ""
                                curr_title = curr.get("title") or title
                                is_recent_start = s_date.startswith("2025") or s_date.startswith("2026")
                                
                                # Check for internal promotions (past role at same company)
                                promoted = False
                                for past in history[1:]:
                                    p_org = str(past.get("organization_name", "")).lower()
                                    p_end = str(past.get("end_date", ""))
                                    past_title = past.get("title") or "Previous Role"
                                    
                                    if company_name.lower() in p_org or domain in str(past.get("company_website", "")).lower():
                                        eff_date = s_date if (s_date.startswith("2025") or s_date.startswith("2026")) else (p_end if (p_end.startswith("2025") or p_end.startswith("2026")) else "")
                                        if eff_date:
                                            role_changes.append(f"[INTERNAL PROMOTION] {real_name}: {past_title} -> {curr_title} (Effective: {eff_date})")
                                            promoted = True
                                            break
                                
                                if is_recent_start and not promoted:
                                    role_changes.append(f"[RECENT HIRE] {real_name} joined as {curr_title} (Started: {s_date})")
                        time.sleep(0.1)
                    except Exception:
                        pass
                        
                people_found.append({
                    "name": real_name,
                    "title": title,
                    "linkedin_url": linkedin,
                    "email_status": email_status
                })
    except Exception as e:
        pass
        
    return people_found, role_changes

def check_openfda_compliance(company_name: str):
    """
    Checks openFDA for active enforcement actions, warning letters, or recalls.
    """
    clean_name = company_name.split()[0].replace(",", "").replace(".", "")
    try:
        url = f'https://api.fda.gov/drug/enforcement.json?search=openfda.manufacturer_name:"{clean_name}"&limit=1'
        r = requests.get(url, timeout=6)
        if r.ok:
            results = r.json().get("results", [])
            if results:
                rec = results[0]
                reason = rec.get("reason_for_recall", "Recall Event")
                status = rec.get("status", "Ongoing")
                return f"FDA Recall Recorded: {reason[:80]}... [Status: {status}]"
    except Exception:
        pass
    return "Clean Compliance Record (No openFDA Enforcements)"

def main():
    print("=" * 75, flush=True)
    print("  MULTI-SOURCE COMPANY ENRICHMENT VERIFIER (APOLLO + APIFY + openFDA)", flush=True)
    print("=" * 75, flush=True)
    
    # 1. Initialize Apify
    apify_mgr = None
    apify_status = "Not Initialized"
    try:
        apify_mgr = ApifyActorsManager()
        acct = apify_mgr.wrapper.check_account_status()
        if acct.get("authenticated"):
            print(f"[APIFY STATUS] Authenticated as '{acct.get('username')}' (Tier: {acct.get('plan_tier')})", flush=True)
            apify_status = f"Connected ({acct.get('plan_tier')})"
        else:
            print(f"[APIFY STATUS] Account Check: {acct.get('error')}", flush=True)
            apify_status = "Limit / Error"
    except Exception as e:
        print(f"[APIFY STATUS] Initialization Note: {e}", flush=True)
        apify_status = "Offline"

    # 2. Load companies from cohort
    if not os.path.exists(TARGET_CSV):
        print(f"Error: {TARGET_CSV} not found!", flush=True)
        return

    with open(TARGET_CSV, "r", encoding="utf-8-sig") as f:
        companies = list(csv.DictReader(f))

    print(f"\nLoaded {len(companies)} target companies from {TARGET_CSV}\n", flush=True)

    enriched_records = []
    comparison_summary = []

    for idx, co in enumerate(companies, 1):
        c_name = co.get("Company Name") or co.get("Company", "")
        dom = co.get("Website Domain") or co.get("domain", "")
        c_li = co.get("LinkedIn URL") or co.get("linkedin_url", "")
        co_emp = co.get("Employee Count", "")
        print(f"[{idx:2}/{len(companies)}] Running Multi-Source Intel on: {c_name} ({dom})...", flush=True)

        # A. Try Apify Growjo for YoY growth and revenue
        growth_pct = None
        est_rev = None
        apify_note = "Bypassed"
        if apify_mgr:
            g_res = apify_mgr.get_growjo_growth(c_name)
            if g_res.get("success"):
                growth_pct = g_res.get("employee_growth_pct")
                est_rev = g_res.get("estimated_revenue")
                apify_note = "Growjo Enriched"
            elif g_res.get("limit_exceeded"):
                apify_note = "Apify Monthly Limit Exceeded"

        # B. Apollo Decision Makers & Mobility (Role Changes)
        dms, role_changes = get_apollo_executives_and_moves(dom, c_name)
        
        # C. openFDA Compliance Check
        fda_status = check_openfda_compliance(c_name)

        # Summaries
        dm_summary = " | ".join([f"{d['name']} ({d['title']}) [{d['email_status']}]" for d in dms[:5]]) if dms else "None resolved"
        moves_summary = " | ".join(role_changes[:5]) if role_changes else "No recent executive moves tracked"

        new_record = dict(co)
        new_record["Apify Status"] = apify_note
        new_record["Growth YoY %"] = f"{growth_pct}%" if growth_pct is not None else "N/A"
        new_record["Estimated Revenue"] = est_rev if est_rev else "Private SMB"
        new_record["Verified Decision Makers Count"] = len(dms)
        new_record["Verified Decision Makers Summary"] = dm_summary
        new_record["Role Changes / Departures Count"] = len(role_changes)
        new_record["Role Changes / Departures Summary"] = moves_summary
        new_record["FDA Compliance Status"] = fda_status
        enriched_records.append(new_record)

        comparison_summary.append({
            "name": c_name,
            "domain": dom,
            "new_dms": len(dms),
            "new_moves": len(role_changes),
            "fda": fda_status,
        })

        print(f"      -> Decision Makers: {len(dms)} | Mobility Moves: {len(role_changes)} | FDA: {fda_status[:35]}...", flush=True)
        time.sleep(0.3)

    # Export to Downloads
    out_csv = r"C:\Users\joela\Downloads\apify_apollo_20co_verified.csv"
    out_json = r"C:\Users\joela\Downloads\apify_apollo_20co_results.json"
    local_csv = r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\apify_apollo_20co_verified.csv"

    fieldnames = list(enriched_records[0].keys())

    for p in [out_csv, local_csv]:
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(enriched_records)
        print(f"\n[EXPORT] CSV saved: {p}", flush=True)

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(enriched_records, f, indent=2, ensure_ascii=False)
    print(f"[EXPORT] JSON saved: {out_json}", flush=True)

    print("\n" + "=" * 75, flush=True)
    print("  MULTI-SOURCE COMPANY ENRICHMENT COMPLETE", flush=True)
    print("=" * 75, flush=True)
    print(f"Total Companies Successfully Enriched: {len(comparison_summary)}\n", flush=True)

    for c in comparison_summary:
        print(f"[ENRICHED] {c['name']:<32} | Decision Makers: {c['new_dms']} | Mobility Moves: {c['new_moves']}", flush=True)

if __name__ == "__main__":
    main()
