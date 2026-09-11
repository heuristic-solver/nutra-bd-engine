"""
linkedin_role_collector.py — BD Engine: LinkedIn Role Change Detector

Detects employee arrivals and departures at nutraceutical companies at ALL seniority
levels (not just C-suite). Uses:

  1. Serper to resolve LinkedIn company URL from company name
  2. Apify harvestapi~linkedin-company-employees actor to pull:
       a. Recent hires (joined < 12 months)
       b. People who recently changed jobs (recentlyChangedJobs=True)

Output per event:
  {
    "event_type":       "ROLE_CHANGE",
    "direction":        "ARRIVAL" | "DEPARTURE" | "INTERNAL_MOVE",
    "person_name":      "Jane Smith",
    "role_title":       "Formulation Scientist",
    "function":         "R&D / Science",
    "seniority":        "Mid-Level" | "Manager" | "Director" | "VP" | "C-Suite",
    "company":          "Seed Health",
    "linkedin_url":     "https://linkedin.com/in/...",
    "change_date":      "2025-08",
    "source":           "LinkedIn Employee Scraper"
  }

Cost: ~$4/1k short profiles (harvestapi pay-per-event), ~$0.08 per 20 profiles per company.
"""

import os
import re
import time
import requests
import json
from typing import Optional, List, Dict, Any

SERPER_API_KEY   = os.environ.get("SERPER_API_KEY", "")
APIFY_API_TOKEN  = os.environ.get("APIFY_API_TOKEN", "")

APIFY_BASE        = "https://api.apify.com/v2"
ACTOR_ID          = "harvestapi~linkedin-company-employees"
MAX_PROFILES      = 25      # per run, cost-controlled
PROFILE_MODE      = "Short ($4 per 1k)"   # harvestapi exact enum string
ACTOR_TIMEOUT     = 150     # seconds to wait for actor run

# Nutraceutical-relevant role keywords to filter employees
NUTRA_ROLE_KEYWORDS = [
    "formulation", "scientist", "regulatory", "quality", "r&d", "research",
    "development", "innovation", "lab", "clinical", "nutrition", "scientific",
    "qa", "qc", "supply chain", "procurement", "operations", "manufacturing",
    "sales", "business development", "marketing", "brand", "technical",
    "manager", "director", "specialist", "analyst", "associate",
]

# Seniority classification — ordered most-senior first
SENIORITY_TIERS = [
    ("C-Suite",  ["chief", "ceo", "coo", "cfo", "cto", "cmo", "cso", "president", "founder", "owner"]),
    ("VP",       ["vp ", "vice president", "svp", "evp", "senior vice"]),
    ("Director", ["director"]),
    ("Manager",  ["manager", "head of", "lead", "principal", "senior"]),
    ("Mid-Level",["specialist", "scientist", "analyst", "engineer", "coordinator",
                  "associate", "consultant", "advisor", "technician", "officer"]),
]

# BD-relevant function buckets (same as serper_collector)
EXEC_FUNCTION_MAP = {
    "Sales":         ["sales", "commercial", "revenue", "business development", "account", "channel", "trade"],
    "QA / RA":       ["quality", "qa", "qc", "regulatory", "compliance", "validation", "gmp", "ra", "affairs", "safety"],
    "Operations":    ["operations", "ops", "supply chain", "manufacturing", "production", "plant", "logistics", "procurement"],
    "R&D / Science": ["r&d", "research", "development", "science", "formulation", "innovation", "lab", "clinical", "nutrition", "scientific"],
    "Finance":       ["cfo", "finance", "financial", "treasurer", "controller", "accounting", "investment"],
    "Marketing":     ["marketing", "brand", "digital", "communications", "pr", "media", "creative"],
    "HR / People":   ["hr", "human resources", "people", "talent", "recruiting", "culture", "workforce"],
    "Technology":    ["cto", "cio", "technology", "it", "digital", "engineering", "software", "data"],
    "General / CEO": ["ceo", "president", "chief executive", "managing director", "general manager", "md"],
}


def _classify_seniority(title: str) -> str:
    t = title.lower()
    for tier_name, keywords in SENIORITY_TIERS:
        if any(kw in t for kw in keywords):
            return tier_name
    return "Mid-Level"


def _classify_function(title: str) -> str:
    t = title.lower()
    for fn_name, keywords in EXEC_FUNCTION_MAP.items():
        if any(kw in t for kw in keywords):
            return fn_name
    return "General Management"


def _is_nutra_relevant(title: str) -> bool:
    """Return True if role title is relevant to nutraceutical BD."""
    t = title.lower()
    return any(kw in t for kw in NUTRA_ROLE_KEYWORDS)


class LinkedInRoleCollector:
    """
    Detects role changes (arrivals and departures) at nutraceutical companies
    using LinkedIn company employee data via the Apify harvestapi actor.
    """

    def __init__(self, api_token: Optional[str] = None, serper_key: Optional[str] = None):
        self.api_token  = api_token or os.environ.get("APIFY_API_TOKEN", "")
        self.serper_key = serper_key or os.environ.get("SERPER_API_KEY", "")
        self._session   = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # LINKEDIN URL RESOLUTION
    # ------------------------------------------------------------------

    def resolve_linkedin_url(self, company_name: str) -> Optional[str]:
        """
        Resolve a LinkedIn company page URL via multiple strategies:
        1. Direct slug construction (e.g. 'Seed Health' -> .../company/seed-health)
        2. Serper search query fallbacks
        Returns e.g. 'https://www.linkedin.com/company/seed-health' or None.
        """
        import re as _re

        # --- Strategy 1: Direct slug from name ---
        slug = company_name.lower().strip()
        slug = _re.sub(r"[^a-z0-9\s-]", "", slug)   # strip punctuation
        slug = _re.sub(r"\s+", "-", slug)              # spaces → hyphens
        slug = _re.sub(r"-+", "-", slug).strip("-")
        direct_url = f"https://www.linkedin.com/company/{slug}"

        # --- Strategy 2: Serper search with multiple query formats ---
        queries = [
            f'linkedin.com/company "{company_name}" supplement OR nutraceutical OR nutrition',
            f'site:linkedin.com "{company_name}" company employees',
            f'"{company_name}" linkedin company page supplement nutrition',
        ]

        for query in queries:
            try:
                resp = requests.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                    json={"q": query, "num": 5},
                    timeout=10,
                )
                if not resp.ok:
                    continue
                items = resp.json().get("organic", [])
                # Also normalize any found URL to strip subpaths
                for item in items:
                    url = item.get("link", "")
                    if "linkedin.com/company/" in url:
                        url = url.split("?")[0].rstrip("/")
                        # Strip subpaths: keep only /company/<slug>
                        parts = url.split("/company/")
                        if len(parts) == 2:
                            slug_part = parts[1].split("/")[0]
                            url = f"https://www.linkedin.com/company/{slug_part}"
                        return url
            except Exception:
                continue

        # Fall back to constructed slug URL
        # Normalize: strip any LinkedIn subpaths (/life, /about, /jobs, /people etc)
        if direct_url:
            base = direct_url.split("/company/")
            if len(base) == 2:
                slug_part = base[1].split("/")[0]  # take only the slug, not subpaths
                direct_url = f"https://www.linkedin.com/company/{slug_part}"
        return direct_url

    # ------------------------------------------------------------------
    # APIFY ACTOR RUNNER
    # ------------------------------------------------------------------

    def _run_actor(self, actor_input: dict) -> List[dict]:
        """
        Run the harvestapi~linkedin-company-employees actor and return results.
        Polls until done or timeout.
        """
        token = self.api_token or os.environ.get("APIFY_API_TOKEN", "")
        if not token:
            return []

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Start run (with retry for concurrency)
        run_id = None
        for attempt in range(2):
            try:
                run_resp = requests.post(
                    f"{APIFY_BASE}/acts/{ACTOR_ID}/runs",
                    headers=headers,
                    json=actor_input,
                    timeout=30,
                )
                if run_resp.status_code == 429:
                    time.sleep(6)
                    continue
                if not run_resp.ok:
                    print(f" [Apify error {run_resp.status_code}]: {run_resp.text[:80]}", end="")
                    return []
                run_id = run_resp.json().get("data", {}).get("id")
                if run_id:
                    break
            except Exception:
                return []


        # Poll for completion
        deadline = time.time() + ACTOR_TIMEOUT
        while time.time() < deadline:
            time.sleep(5)
            try:
                status_resp = requests.get(
                    f"{APIFY_BASE}/actor-runs/{run_id}",
                    headers=headers,
                    timeout=15,
                )
                status = status_resp.json().get("data", {}).get("status", "")
                if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                    break
            except Exception:
                continue

        # Fetch dataset
        try:
            ds_resp = requests.get(
                f"{APIFY_BASE}/actor-runs/{run_id}/dataset/items?limit=100",
                headers=headers,
                timeout=30,
            )
            if ds_resp.ok:
                return ds_resp.json()
        except Exception:
            pass
        return []

    # ------------------------------------------------------------------
    # PROFILE PARSING
    # ------------------------------------------------------------------

    def _parse_experience_dates(self, exp: dict) -> tuple:
        """
        Extract start/end dates from a LinkedIn experience entry.
        Returns (start_str, end_str) — end_str is None if still there.
        """
        # harvestapi returns dates in various shapes
        start = exp.get("startDate") or exp.get("start") or {}
        end   = exp.get("endDate")   or exp.get("end")   or {}

        def fmt(d):
            if not d:
                return None
            if isinstance(d, str):
                return d[:7]   # "2025-03"
            if isinstance(d, dict):
                y = d.get("year", "")
                m = d.get("month", "")
                return f"{y}-{str(m).zfill(2)}" if y else None
            return None

        return fmt(start), fmt(end)

    def _is_recent(self, date_str: Optional[str], months: int = 3) -> bool:
        """Return True if date_str (YYYY-MM or YYYY-MM-DD) is within the last `months` months."""
        if not date_str:
            return False
        try:
            from datetime import datetime, timezone
            dt = datetime.strptime(date_str[:7], "%Y-%m")
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            delta = (now.year - dt.year) * 12 + (now.month - dt.month)
            return 0 <= delta <= months
        except Exception:
            return False

    def _build_role_event(
        self,
        profile: dict,
        company_name: str,
        direction: str,
        role_title: str,
        change_date: Optional[str],
    ) -> dict:
        fname = profile.get("firstName", "")
        lname = profile.get("lastName", "")
        full = (fname + " " + lname).strip()
        name = full or profile.get("fullName") or profile.get("name") or "Unknown"
        url  = profile.get("linkedinUrl") or profile.get("profileUrl") or profile.get("url") or ""
        return {
            "event_type":    "ROLE_CHANGE",
            "direction":     direction,
            "person_name":   name,
            "role_title":    role_title,
            "function":      _classify_function(role_title),
            "seniority":     _classify_seniority(role_title),
            "company":       company_name,
            "linkedin_url":  url,
            "change_date":   change_date or "",
            "source":        "LinkedIn Employee Scraper",
        }

    # ------------------------------------------------------------------
    # RECENT ARRIVALS & ROLE CHANGES (Past 3 Months Max)
    # ------------------------------------------------------------------

    def get_recent_arrivals(self, company_name: str, linkedin_url: str) -> List[dict]:
        """
        Pull employees who recently joined the company (<= 3 months tenure)
        or recently experienced a role change / promotion at the company (<= 3 months).
        """
        # Run recentlyChangedJobs first (proven high yield for exact roles like Formulation Scientist)
        actor_input = {
            "companies": [linkedin_url],
            "recentlyChangedJobs": True,
            "maxItems": MAX_PROFILES,
            "profileScraperMode": PROFILE_MODE,
        }

        profiles = self._run_actor(actor_input)

        events = []
        seen_names = set()

        for p in profiles:
            positions = p.get("currentPositions") or p.get("positions") or p.get("experience") or []
            role = ""
            start_date = ""
            direction = "ARRIVAL"
            pos_months = 0
            co_months = 0

            for pos in positions:
                role = pos.get("title") or pos.get("role") or ""
                started = pos.get("startedOn")
                if isinstance(started, dict):
                    y = started.get("year")
                    m = started.get("month", 1)
                    if y:
                        start_date = f"{y}-{str(m).zfill(2)}"
                elif isinstance(started, str):
                    start_date = started[:7]

                # Check tenure at company vs position
                tenure_co = pos.get("tenureAtCompany", {})
                tenure_pos = pos.get("tenureAtPosition", {})
                co_months = tenure_co.get("numMonths", 0) + (tenure_co.get("numYears", 0) * 12)
                pos_months = tenure_pos.get("numMonths", 0) + (tenure_pos.get("numYears", 0) * 12)

                if co_months > 3 and pos_months <= 3:
                    direction = "INTERNAL_PROMOTION"
                else:
                    direction = "ARRIVAL"
                break

            # STRICT 3-MONTH RECENCY FILTER:
            # 1. If start_date is known, verify delta <= 3 months
            if start_date:
                if not self._is_recent(start_date, months=3):
                    continue
            # 2. If tenure in position is reported, ensure <= 3 months
            if pos_months > 3:
                continue
            # 3. If tenure at company is reported and pos_months is 0, ensure co_months <= 3
            if pos_months == 0 and co_months > 3:
                continue

            if not role:
                role = p.get("headline") or p.get("jobTitle") or "Specialist"

            # Must be relevant to nutraceutical functions
            if not _is_nutra_relevant(role):
                continue

            ev = self._build_role_event(p, company_name, direction, role, start_date)
            name_key = ev["person_name"].lower()
            if name_key and name_key != "unknown" and name_key not in seen_names:
                seen_names.add(name_key)
                events.append(ev)

        return events

    # ------------------------------------------------------------------
    # RECENT DEPARTURES
    # ------------------------------------------------------------------

    def get_recent_departures(self, company_name: str, linkedin_url: str) -> List[dict]:
        """
        Identify departures by checking profiles where past positions match the target company
        with an end date in the last 12 months.
        """
        # harvestapi companies filter targets current employees.
        # Departure detection is primarily supplemented by Serper's targeted LinkedIn former employee queries.
        return []

    # ------------------------------------------------------------------
    # MAIN ENTRY POINT
    # ------------------------------------------------------------------

    def analyze_company(self, company_name: str) -> dict:
        """
        Full role change analysis for a company.
        Returns structured dict with arrivals, departures, and metadata.
        """
        print(f"  [LinkedIn] Role change scan: {company_name}...", end=" ")

        linkedin_url = self.resolve_linkedin_url(company_name)
        if not linkedin_url:
            print("(no LinkedIn URL found, skipping actor)")
            return self._empty_result(company_name, error="LinkedIn URL not resolved")

        print(f"URL={linkedin_url}")

        arrivals   = self.get_recent_arrivals(company_name, linkedin_url)
        time.sleep(1)
        departures = self.get_recent_departures(company_name, linkedin_url)

        all_events = arrivals + departures

        # Seniority breakdown
        seniority_counts = {}
        for ev in all_events:
            s = ev.get("seniority", "Unknown")
            seniority_counts[s] = seniority_counts.get(s, 0) + 1

        # Function breakdown
        fn_counts = {}
        for ev in all_events:
            fn = ev.get("function", "Unknown")
            fn_counts[fn] = fn_counts.get(fn, 0) + 1

        print(f"    -> {len(arrivals)} arrivals, {len(departures)} departures detected")

        return {
            "company_name":      company_name,
            "linkedin_url":      linkedin_url,
            "role_changes":      all_events,
            "summary": {
                "total_role_changes":  len(all_events),
                "arrivals_count":      len(arrivals),
                "departures_count":    len(departures),
                "seniority_breakdown": seniority_counts,
                "function_breakdown":  fn_counts,
            },
        }

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_result(company_name: str, error: str = "") -> dict:
        return {
            "company_name": company_name,
            "linkedin_url": None,
            "role_changes": [],
            "summary": {
                "total_role_changes": 0,
                "arrivals_count":     0,
                "departures_count":   0,
                "seniority_breakdown": {},
                "function_breakdown":  {},
                "error": error,
            },
        }
