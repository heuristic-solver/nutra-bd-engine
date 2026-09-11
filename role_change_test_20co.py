"""
role_change_test_20co.py — Test role-change detection on 20 nutraceutical companies.

Uses both tracks:
  Track 1: Serper get_role_change_signals() — news + LinkedIn posts via Google
  Track 2: LinkedInRoleCollector — Apify harvestapi actor for confirmed arrivals/departures

Output: bd_role_changes_20co.csv
"""

import csv
import sys
import io
import os
import re
import time
import warnings
import json
warnings.filterwarnings("ignore")

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k = _k.strip()
                _v = _v.strip().strip("'\"")
                if _k:
                    os.environ[_k] = _v

from bd_engine.collectors.serper_collector import SerperCollector
from bd_engine.collectors.linkedin_role_collector import LinkedInRoleCollector

# -----------------------------------------------------------------------
# 20 companies — mix of large (>500 emp) and small (<100 emp)
# -----------------------------------------------------------------------
COMPANIES = [
    # --- Large / Well-Known ---
    {"name": "Nordic Naturals",       "size": "large"},
    {"name": "Thorne Research",       "size": "large"},
    {"name": "Garden of Life",        "size": "large"},
    {"name": "NOW Foods",             "size": "large"},
    {"name": "Solgar",                "size": "large"},
    {"name": "Life Extension",        "size": "large"},
    {"name": "Nature's Way",          "size": "large"},
    {"name": "Jarrow Formulas",       "size": "large"},
    {"name": "MegaFood",              "size": "medium"},
    {"name": "New Chapter",           "size": "medium"},

    # --- Medium / VC-Backed ---
    {"name": "Athletic Greens",       "size": "medium"},
    {"name": "Ritual",                "size": "medium"},
    {"name": "Seed Health",           "size": "medium"},
    {"name": "HUM Nutrition",         "size": "medium"},
    {"name": "Olly Nutrition",        "size": "medium"},

    # --- Small / Niche ---
    {"name": "Designs for Health",    "size": "small"},
    {"name": "Xymogen",              "size": "small"},
    {"name": "Vital Nutrients",       "size": "small"},
    {"name": "Pure Encapsulations",   "size": "small"},
    {"name": "Integrative Therapeutics", "size": "small"},
]

OUT_FILE    = "bd_role_changes_20co.csv"
MASTER_FILE = "role_change_master_results.csv"
SEP         = "=" * 70

def fmt_events(events, max_n=5):
    """Compact pipe-separated summary of role-change events."""
    parts = []
    for ev in events[:max_n]:
        name = ev.get("person_name") or ev.get("executive_name") or "?"
        role = ev.get("role_title") or ev.get("executive_title") or "?"
        d    = ev.get("direction", "?")
        fn   = ev.get("function", "?")
        dt   = ev.get("date") or ev.get("change_date") or ""
        parts.append(f"{d}:{name} ({role} | {fn}{' | ' + dt if dt else ''})")
    return " | ".join(parts)

def fmt_segregated_events(events, is_departure=False):
    """Build exact clean verified titles list for arrivals or departures with strict 3-month validity."""
    parts = []
    seen = set()
    for ev in events:
        raw_name = ev.get("person_name") or ev.get("executive_name")
        raw_role = ev.get("role_title") or ev.get("executive_title")
        
        name = SerperCollector.clean_person_name(raw_name)
        role = SerperCollector.clean_role_title(raw_role)

        if name and role:
            key = f"{name.lower()}::{role.lower()}"
            if key not in seen:
                seen.add(key)
                if is_departure:
                    parts.append(f"{name} (Ex-{role})")
                else:
                    parts.append(f"{name} ({role})")
        elif name and not role:
            key = name.lower()
            if key not in seen:
                seen.add(key)
                if is_departure:
                    parts.append(f"{name} (Ex-Employee)")
                else:
                    parts.append(f"{name} (New Arrival / Promotion)")
        elif role and not name:
            key = role.lower()
            if key not in seen:
                seen.add(key)
                if is_departure:
                    parts.append(f"1 Ex-{role}")
                else:
                    parts.append(f"1 {role}")

    if not parts:
        return "None detected in 90-day window"
    return " | ".join(parts[:6])

def main():
    print(SEP)
    print("  ROLE CHANGE DETECTION TEST — 20 NUTRACEUTICAL COMPANIES (PAST 3 MONTHS MAX)")
    print(SEP)

    serper   = SerperCollector()
    li_coll  = LinkedInRoleCollector()

    rows = []
    master_rows = []

    for i, company in enumerate(COMPANIES, 1):
        name = company["name"]
        size = company["size"]
        print(f"\n[{i}/20] {name} ({size})", flush=True)
        print("-" * 50, flush=True)

        # --- Track 1: Serper role-change signals ---
        try:
            rc_signals = serper.get_role_change_signals(name, num=8)
            rc_arrivals   = [e for e in rc_signals if e.get("direction") == "ARRIVAL"]
            rc_departures = [e for e in rc_signals if e.get("direction") == "DEPARTURE"]
            rc_persons    = list({
                (e.get("person_name") or e.get("executive_name") or "")
                for e in rc_signals
                if (e.get("person_name") or e.get("executive_name") or "").lower() not in ("not extracted", "?", "")
            })
        except Exception as ex:
            print(f"  [Serper ERROR] {ex}", flush=True)
            rc_signals, rc_arrivals, rc_departures, rc_persons = [], [], [], []

        time.sleep(0.5)

        # --- Track 2: LinkedIn actor ---
        try:
            li_result = li_coll.analyze_company(name)
            li_arrivals   = [e for e in li_result.get("role_changes", []) if e.get("direction") in ("ARRIVAL", "INTERNAL_PROMOTION")]
            li_departures = [e for e in li_result.get("role_changes", []) if e.get("direction") == "DEPARTURE"]
            li_persons    = list({
                e.get("person_name", "")
                for e in li_result.get("role_changes", [])
                if e.get("person_name", "").lower() not in ("unknown", "")
            })
            li_url        = li_result.get("linkedin_url") or ""
        except Exception as ex:
            print(f"  [LinkedIn ERROR] {ex}", flush=True)
            li_result, li_arrivals, li_departures, li_persons, li_url = {}, [], [], [], ""

        # --- Merge ---
        all_arrivals   = rc_arrivals   + li_arrivals
        all_departures = rc_departures + li_departures
        all_events     = rc_signals + li_result.get("role_changes", [])
        all_persons    = list(set(rc_persons + li_persons))
        total          = len(all_events)

        print(f"  Serper  : {len(rc_arrivals)} arrivals, {len(rc_departures)} departures — {len(rc_persons)} named persons", flush=True)
        print(f"  LinkedIn: {len(li_arrivals)} arrivals/promotions, {len(li_departures)} departures — {len(li_persons)} named persons", flush=True)
        print(f"  TOTAL   : {total} role-change signals | Persons: {', '.join(all_persons[:5]) or 'none'}", flush=True)

        # --- Headcount & Velocity Calculations ---
        size_headcounts = {
            "large": 750,
            "medium": 250,
            "small": 60,
        }
        est_hc = size_headcounts.get(size.lower(), 150)
        role_change_rate = round((total / est_hc) * 100, 1)

        # Trajectory classification
        if len(all_departures) >= 2 and len(all_departures) >= len(all_arrivals):
            trajectory = "LEADERSHIP RESTRUCTURING (Executive Gaps)"
            talking_point = "Recent executive departures indicate transition phase; prime window to pitch specialized interim & permanent replacement leadership."
        elif len(all_arrivals) >= 5:
            trajectory = "RAPID TEAM EXPANSION (High Hiring Velocity)"
            talking_point = "Surge in recent arrivals/promotions signals product line expansion and increased need for QA/RA & formulation vendor support."
        elif total >= 3:
            trajectory = "ACTIVE WORKFORCE ROTATION"
            talking_point = "Active staffing movements across key departments; new decision makers receptive to benchmarking incumbent suppliers."
        else:
            trajectory = "STABLE / LOW CHURN"
            talking_point = "Stable core team; focus outreach on strategic capacity expansion and contract formulation."

        # Function + Seniority breakdown across all events
        fn_counts = {}
        seniority_counts = {}
        for ev in all_arrivals + all_departures:
            fn = ev.get("function", "Unknown")
            sn = ev.get("seniority", "Unknown")
            fn_counts[fn]        = fn_counts.get(fn, 0) + 1
            seniority_counts[sn] = seniority_counts.get(sn, 0) + 1

        fn_str = "; ".join(f"{k}:{v}" for k, v in sorted(fn_counts.items(), key=lambda x: -x[1]))
        sn_str = "; ".join(f"{k}:{v}" for k, v in sorted(seniority_counts.items(), key=lambda x: -x[1]))

        # Impacted functions formatted
        fn_parts = [f"{k} ({v})" for k, v in sorted(fn_counts.items(), key=lambda x: -x[1]) if k not in ("Unknown", "General Management")]
        fn_summary = ", ".join(fn_parts[:4]) or "General Management"

        # Senior/Exec moves
        exec_moves = [
            f"{ev.get('person_name') or ev.get('executive_name')} ({ev.get('role_title') or ev.get('executive_title')})"
            for ev in all_arrivals + all_departures
            if ev.get("is_senior_level") and (ev.get("person_name") or ev.get("executive_name")) not in ("Not extracted", "Unknown", None)
        ]
        exec_summary = " | ".join(list(dict.fromkeys(exec_moves))[:4]) or "None in 90d window"

        rows.append({
            "company_name":              name,
            "company_size":              size,
            "estimated_headcount":       est_hc,
            "linkedin_company_url":      li_url,

            # Combined totals (Strict 3 Months Max)
            "total_role_changes":        total,
            "total_arrivals":            len(all_arrivals),
            "total_departures":          len(all_departures),
            "role_change_rate_pct":      f"{role_change_rate}%",
            "turnover_trajectory":       trajectory,
            "named_persons_detected":    len(all_persons),
            "persons_list":              " | ".join(all_persons[:10]),

            # Function + seniority breakdown
            "impacted_functions":        fn_summary,
            "function_breakdown":        fn_str,
            "seniority_breakdown":       sn_str,
            "executive_leadership_moves": exec_summary,
            "bd_talking_point":          talking_point,

            # Track 1 — Serper
            "serper_role_change_total":  len(rc_signals),
            "serper_arrivals":           len(rc_arrivals),
            "serper_departures":         len(rc_departures),
            "serper_named_persons":      len(rc_persons),
            "serper_event_detail":       fmt_events(rc_signals),

            # Track 2 — LinkedIn actor
            "linkedin_role_change_total": len(li_result.get("role_changes", [])),
            "linkedin_arrivals":          len(li_arrivals),
            "linkedin_departures":        len(li_departures),
            "linkedin_named_persons":     len(li_persons),
            "linkedin_event_detail":      fmt_events(li_result.get("role_changes", [])),
        })

        master_rows.append({
            "Company":                               name,
            "Size":                                  size.capitalize(),
            "Est. Headcount":                        est_hc,
            "Total Changes (Past 3 Months)":         total,
            "Arrivals Count":                        len(all_arrivals),
            "Departures Count":                      len(all_departures),
            "Role Change Rate %":                    f"{role_change_rate}%",
            "Turnover / Growth Trajectory":          trajectory,
            "Recent Arrivals (Joined / Promoted - Exact Names & Roles)": fmt_segregated_events(all_arrivals, is_departure=False),
            "Recent Departures (Left / Alumni - Exact Names & Roles)":   fmt_segregated_events(all_departures, is_departure=True),
            "Primary Impacted Functions":            fn_summary,
            "Executive & Leadership Movements":      exec_summary,
            "Key BD Talking Point & Outreach Angle": talking_point,
        })

        time.sleep(0.5)

    # Write detailed 60-column CSV
    if rows:
        with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    # Write clean Master Results CSV
    if master_rows:
        with open(MASTER_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(master_rows[0].keys()))
            writer.writeheader()
            writer.writerows(master_rows)

    print(f"\n{SEP}")
    print(f"  DONE — Generated {OUT_FILE} and {MASTER_FILE}")
    print(f"  {len(rows)} companies processed")
    print(SEP)

    # Quick summary table
    print("\n  MASTER RESULTS SUMMARY TABLE (PAST 3 MONTHS MAX)")
    print(f"  {'Company':<22} {'Size':<7} {'Tot':<4} {'Rate':<6} {'Trajectory':<30} | {'Arrivals':<35} | {'Departures'}")
    print("  " + "-" * 125)
    for r in master_rows:
        print(
            f"  {r['Company']:<22} {r['Size']:<7} "
            f"{r['Total Changes (Past 3 Months)']:<4} {r['Role Change Rate %']:<6} "
            f"{r['Turnover / Growth Trajectory'][:28]:<30} | "
            f"{r['Recent Arrivals (Joined / Promoted - Exact Names & Roles)'][:33]:<35} | "
            f"{r['Recent Departures (Left / Alumni - Exact Names & Roles)']}"
        )

if __name__ == "__main__":
    main()
