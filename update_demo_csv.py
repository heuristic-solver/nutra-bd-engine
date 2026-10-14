import csv
import json
import re

# Load all scraped data
with open("data_slayer_results.json", encoding="utf-8") as f:
    data_slayer = json.load(f)

with open("inovaflow_results.json", encoding="utf-8") as f:
    inovaflow = json.load(f)

with open("thirdwatch_results.json", encoding="utf-8") as f:
    thirdwatch = json.load(f)

with open("george_dev_results.json", encoding="utf-8") as f:
    george_dev = json.load(f)

# Read existing CSV
rows = []
with open("signalbase_demo_enriched.csv", mode="r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        rows.append(row)

print("Fieldnames:", fieldnames)

for row in rows:
    co_name = row["Company Name"]
    
    # 1. Enrich PRONTO
    if "PRONTO" in co_name:
        events = []
        # Inovaflow leadership change
        for ino in inovaflow:
            events.append(f"[LEADERSHIP HIRE] {ino.get('person')} -> {ino.get('newTitle')} (Announced: {ino.get('announcedDate')}) [Window: {ino.get('buyingWindow')}]")
        # Data-slayer
        for ev in data_slayer.get("by_company", {}).get("PRONTO", []):
            ev_type = ev.get("event_type", "").upper()
            p_name = ev.get("person_full_name") or (ev.get("person") or {}).get("full_name")
            p_title = ev.get("title_current") or ((ev.get("title") or {}).get("current"))
            p_url = ev.get("person_linkedin_url") or ((ev.get("person") or {}).get("linkedin_url"))
            dt = (ev.get("changed_at") or "")[:10]
            events.append(f"[{ev_type}] {p_name} -> {p_title} ({dt}) - {p_url}")
        
        row["Job Changes Count"] = str(len(events))
        row["Job Changes / Movement Summary"] = " | ".join(events)
        row["Key People / Roster Summary"] = "Prashant Halbe (Head of Brand); Justina Zdan (Talent Acquisition Partner)"

    # 2. Enrich Cmbio
    elif "Cmbio" in co_name:
        events = []
        key_people = []
        for ev in data_slayer.get("by_company", {}).get("Cmbio", []):
            ev_type = ev.get("event_type", "").upper()
            p_name = ev.get("person_full_name") or (ev.get("person") or {}).get("full_name")
            p_title = ev.get("title_current") or ((ev.get("title") or {}).get("current"))
            p_prev = ev.get("title_previous") or ((ev.get("title") or {}).get("previous"))
            p_url = ev.get("person_linkedin_url") or ((ev.get("person") or {}).get("linkedin_url"))
            dt = (ev.get("changed_at") or "")[:10]
            
            if ev_type == "LEFT":
                events.append(f"[DEPARTED/LEFT] {p_name} (Role: {p_title or p_prev}, {dt}) - {p_url}")
            elif ev_type == "TITLE_CHANGE":
                events.append(f"[PROMOTED/TITLE CHANGE] {p_name} ({p_prev} -> {p_title}, {dt}) - {p_url}")
            else:
                events.append(f"[JOINED] {p_name} -> {p_title} ({dt}) - {p_url}")
            
            if p_name and (p_title or p_prev):
                key_people.append(f"{p_name} ({p_title or p_prev})")

        row["Job Changes Count"] = str(len(events))
        row["Job Changes / Movement Summary"] = " | ".join(events[:12]) + (f" | (+{len(events)-12} more changes)" if len(events) > 12 else "")
        row["Key People / Roster Summary"] = "; ".join(key_people[:8])

    # 3. Enrich Apis Flora
    elif "Apis Flora" in co_name:
        events = []
        key_people = []
        for ev in data_slayer.get("by_company", {}).get("Apis Flora", []):
            ev_type = ev.get("event_type", "").upper()
            p_name = ev.get("person_full_name") or (ev.get("person") or {}).get("full_name")
            p_title = ev.get("title_current") or ((ev.get("title") or {}).get("current"))
            p_url = ev.get("person_linkedin_url") or ((ev.get("person") or {}).get("linkedin_url"))
            dt = (ev.get("changed_at") or "")[:10]
            events.append(f"[{ev_type}] {p_name} -> {p_title} ({dt}) - {p_url}")
            if p_name and p_title:
                key_people.append(f"{p_name} ({p_title})")
        
        row["Job Changes Count"] = str(len(events))
        row["Job Changes / Movement Summary"] = " | ".join(events)
        row["Key People / Roster Summary"] = "; ".join(key_people)

    # 4. Enrich Caltron Clays
    elif "Caltron Clays" in co_name:
        row["Job Changes Count"] = "1"
        row["Job Changes / Movement Summary"] = "[JOINED] Mayuri J. -> Quality Control Executive (https://www.linkedin.com/in/mayuri-jadhav-514bbb389)"
        row["Key People / Roster Summary"] = "Mayuri J. (Quality Control Executive)"

    # 5. Enrich Greenspace Herbs
    elif "Greenspace Herbs" in co_name:
        profiles = thirdwatch.get("by_company", {}).get("Greenspace Herbs", [])
        if not profiles and "all_profiles" in thirdwatch:
            profiles = [p for p in thirdwatch["all_profiles"] if "greenspace" in (p.get("headline","")+p.get("currentTitle","")+str(p.get("company",""))).lower()]
        key_roster = [f"{p.get('fullName')} ({p.get('headline') or p.get('currentTitle')})" for p in profiles[:5] if p.get('fullName')]
        if key_roster:
            row["Key People / Roster Summary"] = "; ".join(key_roster)

    # 6. Enrich Wisesorbent Technology
    elif "Wisesorbent" in co_name:
        profiles = thirdwatch.get("by_company", {}).get("Wisesorbent", [])
        if not profiles and "all_profiles" in thirdwatch:
            profiles = [p for p in thirdwatch["all_profiles"] if "wisesorbent" in (p.get("headline","")+p.get("currentTitle","")+str(p.get("company",""))).lower()]
        key_roster = [f"{p.get('fullName')} ({p.get('headline') or p.get('currentTitle')})" for p in profiles[:5] if p.get('fullName')]
        if key_roster:
            row["Key People / Roster Summary"] = "; ".join(key_roster)

# Save back to signalbase_demo_enriched.csv
with open("signalbase_demo_enriched.csv", mode="w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Successfully updated signalbase_demo_enriched.csv!")
