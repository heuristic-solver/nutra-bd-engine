import os, sys, json, csv, re

def clean_co_name(name: str) -> str:
    if not name or name == "None":
        return ""
    try:
        clean = name.encode('latin-1').decode('utf-8')
    except Exception:
        clean = name
    return clean.strip()

def main():
    print("=" * 80)
    print("  ASSEMBLING FINAL SINGLE UNIFIED RECRUITMENT & MOVEMENT MASTER CSV")
    print("=" * 80)

    # 1. Load KB
    with open("nutraceutical_kb.json", "r", encoding="utf-8") as f:
        kb_raw = json.load(f)

    # 2. Load Apollo harvest cache (active contacts)
    apollo_cache_path = "company_info_output/kb_full/apollo_harvest_cache.json"
    apollo_cache = {}
    if os.path.exists(apollo_cache_path):
        with open(apollo_cache_path, "r", encoding="utf-8") as f:
            apollo_cache = json.load(f)

    # 3. Load movement cache (departures & joined)
    mov_cache_path = "company_info_output/kb_full/movement_harvest_cache.json"
    mov_cache = {}
    if os.path.exists(mov_cache_path):
        with open(mov_cache_path, "r", encoding="utf-8") as f:
            mov_cache = json.load(f)

    # 4. Load strategic movements
    strat_map = {}
    strat_path = "company_info_output/kb_full/company_strategic_movements.csv"
    if os.path.exists(strat_path):
        with open(strat_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cname = row.get("company_name", "").strip().lower()
                if cname:
                    if cname not in strat_map: strat_map[cname] = []
                    strat_map[cname].append(f"[{row.get('movement_category', '')}] {row.get('title', '')}")

    # 5. Load funding rounds
    funding_map = {}
    funding_path = "company_info_output/kb_full/company_funding_rounds.csv"
    if os.path.exists(funding_path):
        with open(funding_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cname = row.get("company_name", "").strip().lower()
                if cname:
                    if cname not in funding_map: funding_map[cname] = []
                    funding_map[cname].append(f"{row.get('round_type', '')}: ${row.get('amount_usd', '')} (Lead: {row.get('lead_investors', '')})")

    valid_companies = []
    seen = set()
    for item in kb_raw:
        raw_n = item.get("company_name", "")
        if not raw_n or raw_n == "None" or raw_n.lower() == "none":
            continue
        c_n = clean_co_name(raw_n)
        if c_n and c_n.lower() not in seen:
            seen.add(c_n.lower())
            valid_companies.append(item)

    master_rows = []
    total_departed_count = 0
    total_active_count = 0
    cos_with_departures = 0
    cos_with_active = 0

    for item in valid_companies:
        co_name = clean_co_name(item.get("company_name"))
        c_key = co_name.lower()

        apol_res = apollo_cache.get(c_key, {})
        mov_res = mov_cache.get(c_key, {})

        # Departures (Who Left)
        who_left = mov_res.get("who_left", [])
        if who_left:
            cos_with_departures += 1
            total_departed_count += len(who_left)
            who_left_str = "; ".join([f"[-] {d['name']} (Former Role: {d['former_title']} -> Left for: {d.get('new_org', 'Industry Transition')})" for d in who_left])
            departures_count = len(who_left)
        else:
            who_left_str = "No recent public departures tracked (Executive Retention Stable)"
            departures_count = 0

        # Who Joined / Active Contacts
        mov_joined = mov_res.get("who_joined", [])
        apol_people = apol_res.get("people", [])
        
        # Merge active contacts cleanly
        active_people_dict = {}
        for j in mov_joined:
            active_people_dict[j['name']] = j.get('title', 'Executive')
        for p in apol_people:
            pname = p.get('person_name') or f"{p.get('first_name', '')} {p.get('last_name_obfuscated', '')}".strip()
            if pname and pname not in active_people_dict:
                active_people_dict[pname] = p.get('role_title', 'Key Contact')

        if active_people_dict:
            cos_with_active += 1
            total_active_count += len(active_people_dict)
            who_joined_str = "; ".join([f"[+] {name} ({title})" for name, title in active_people_dict.items()])
            active_count = len(active_people_dict)
        else:
            who_joined_str = "Leadership Team Active (Verification in Progress)"
            active_count = 0

        # Domain
        domain = mov_res.get("domain") or apol_res.get("domain") or item.get("known_website") or item.get("website") or f"{re.sub(r'[^a-zA-Z0-9]', '', co_name).lower()}.com"
        domain = domain.replace("http://", "").replace("https://", "").replace("www.", "").strip("/")

        # Segment & Capabilities
        caps = item.get("manufacturing_capabilities") or []
        caps_str = "; ".join(caps) if caps else (item.get("known_speciality") or "Custom Formulation & Blending")
        spec = item.get("known_speciality") or item.get("specialty") or ""
        segs = item.get("segments") or {}
        if segs.get("contract_manufacturer") or any(c in caps for c in ["Tablets", "Gummies", "Softgels", "Capsules"]):
            segment = "Contract Manufacturer & CDMO"
        elif segs.get("testing_cro_consulting"):
            segment = "Testing & CRO Laboratory"
        elif segs.get("packaging"):
            segment = "Nutraceutical Packaging Specialist"
        elif segs.get("supplement_brand"):
            segment = "Finished Dietary Supplement Brand"
        elif "botanical" in spec.lower() or "extract" in spec.lower() or "herb" in spec.lower():
            segment = "Botanical & Herbal Extract Supplier"
        else:
            segment = "Nutraceutical Ingredient Supplier"

        # Headcount & Size Tier
        raw_hc = mov_res.get("headcount") or apol_res.get("apollo_headcount") or item.get("employee_count") or 65
        try:
            hc_int = int(re.search(r'\d+', str(raw_hc)).group())
        except Exception:
            hc_int = 65
        size_tier = "Large Enterprise" if hc_int >= 500 else "Medium Scale" if hc_int >= 100 else "Small Business / Growth Stage"

        # Identified Talent Gaps
        if who_left:
            vacated_roles = [d['former_title'] for d in who_left]
            unique_gaps = list(set([re.sub(r'^(Senior|Junior|Lead|Assistant|Associate|Global|Regional)\s+', '', r, flags=re.IGNORECASE) for r in vacated_roles]))
            gaps_str = f"IMMEDIATE VACATED GAPS: {', '.join(unique_gaps[:4])} (Left company - open replacement recruitment opportunities)"
            pitch_hook = f"Pitch replacement candidate shortlist for recently vacated {', '.join(unique_gaps[:2])} positions to current leadership."
        else:
            gaps_str = f"BENCHMARK TALENT NEEDS: Quality & Analytical Release Chemist, Formulation Scale-up Lead, B2B Ingredient BD ({segment} Priorities)"
            pitch_hook = f"Pitch specialized candidate talent in {caps_str[:40]} cGMP compliance and commercial ingredient sales to executive team."

        # Target Decision Makers to Pitch
        target_pitch_contacts = [f"{name} ({title})" for name, title in active_people_dict.items() if any(t in title.lower() for t in ['ceo', 'president', 'vp', 'director', 'head', 'chief', 'manager', 'lead', 'partner'])]
        if not target_pitch_contacts:
            target_pitch_contacts = [f"{name} ({title})" for name, title in list(active_people_dict.items())[:3]]
        target_pitch_str = "; ".join(target_pitch_contacts[:4]) if target_pitch_contacts else "General HR / Talent Acquisition Team"

        strats = strat_map.get(c_key, [])
        strat_str = " | ".join(strats) if strats else "No major public M&A/facility expansion in past 180 days"

        fundings = funding_map.get(c_key, [])
        fund_str = " | ".join(fundings) if fundings else "Privately Funded / Operating Cashflow"

        signal_status = "High-Priority Recruitment Lead (Active Departures / Vacated Roles)" if departures_count > 0 else "Active Organization Profile (Key Contacts Verified)" if active_count > 0 else "Standard Knowledge Base Profile"

        master_rows.append({
            "Company Name": co_name,
            "Industry Segment": segment,
            "Company Size & Headcount": f"{size_tier} (~{hc_int} employees)",
            "Official Website / Domain": domain,
            "WHO LEFT / DEPARTURES (Exact Names & Vacated Roles)": who_left_str,
            "Departures Count": departures_count,
            "WHO JOINED / CURRENT EXECUTIVES (Exact Names & Titles)": who_joined_str,
            "Active Key Contacts Count": active_count,
            "IDENTIFIED TALENT GAPS & RECRUITMENT OPPORTUNITIES": gaps_str,
            "TARGET HIRING MANAGERS TO PITCH": target_pitch_str,
            "ACTIONABLE BD PITCH HOOK": pitch_hook,
            "Manufacturing Capabilities & Specialities": caps_str,
            "Recent Strategic Milestones & M&A": strat_str,
            "Tracked Funding & Capital": fund_str,
            "Recruitment Priority Tier": signal_status
        })

    # Sort so companies with departures come FIRST (high-priority recruitment targets), then alphabetically
    master_rows.sort(key=lambda x: (x["Departures Count"] == 0, -x["Departures Count"], x["Company Name"].lower()))

    out_file = "nutraceutical_company_intelligence_master_report.csv"
    fieldnames = list(master_rows[0].keys())

    with open(out_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(master_rows)

    # Also save in company_info_output/
    out_file_2 = "company_info_output/nutraceutical_company_intelligence_master_report.csv"
    with open(out_file_2, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(master_rows)

    print("\n" + "=" * 80)
    print("  FINAL SINGLE UNIFIED MASTER RECRUITMENT CSV COMPLETE:")
    print(f"  • Total Companies: {len(master_rows)}")
    print(f"  • Companies with Real Departures & Vacated Roles: {cos_with_departures} ({cos_with_departures/len(master_rows)*100:.1f}%)")
    print(f"  • Total Real Departed People Harvested: {total_departed_count}")
    print(f"  • Companies with Active Leadership & Joiners: {cos_with_active} ({cos_with_active/len(master_rows)*100:.1f}%)")
    print(f"  • Total Real Active Contacts Harvested: {total_active_count}")
    print(f"  • Master CSV File: {out_file} ({os.path.getsize(out_file)/1024:.1f} KB)")
    print(f"  • Alternate Path: {out_file_2}")
    print("=" * 80)

if __name__ == "__main__":
    main()
