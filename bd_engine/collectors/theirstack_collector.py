"""
TheirStack Collector — Nutraceutical BD Engine

Pulls all TheirStack-based signals:
  - Job velocity & acceleration (7d, 30d, 90d, 180d windows)
  - Stale role detection (days_open, repost flags)
  - Department breakdown
  - Posting channel diversity
  - Niche nutra role flagging
  - Per-company aggregated hiring intelligence

Uses ONLY the /v1/jobs/search endpoint — no credit waste on unrelated data.
"""

import os
import re
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional

from bd_engine.config import (
    THEIRSTACK_BASE_URL,
    THEIRSTACK_JOBS_ENDPOINT,
    NUTRA_INDUSTRY_KEYWORDS,
    NICHE_ROLE_KEYWORDS,
    SENIORITY_WEIGHTS,
    SENIORITY_TITLE_PATTERNS,
    STALE_JOB_THRESHOLDS,
    VELOCITY_CONFIDENCE_MULTIPLIERS,
    DEPT_KEYWORD_MAP,
    DEFAULT_JOB_SEARCH_PARAMS,
)


class TheirStackCollector:
    """
    Pulls job postings for nutraceutical companies from TheirStack API,
    then computes all velocity, staleness, and department-level BD signals.
    """

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = THEIRSTACK_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        })

    # ------------------------------------------------------------------
    # CORE API CALL
    # ------------------------------------------------------------------

    def _search_jobs(self, payload: dict, retries: int = 3) -> dict:
        """
        POST to /v1/jobs/search with exponential backoff on rate limits.
        Returns full JSON response or raises.
        """
        url = f"{self.base_url}{THEIRSTACK_JOBS_ENDPOINT}"

        for attempt in range(retries):
            resp = self.session.post(url, json=payload, timeout=30)

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 429:
                wait = 2 ** attempt
                print(f"  [rate limit] Waiting {wait}s before retry {attempt + 1}/{retries}...")
                time.sleep(wait)
                continue

            # Non-retryable — print body for diagnosis before raising
            try:
                err_body = resp.json()
            except Exception:
                err_body = resp.text
            print(f"  [API ERROR {resp.status_code}] {err_body}")
            resp.raise_for_status()

        raise RuntimeError(f"TheirStack API failed after {retries} retries")

    # ------------------------------------------------------------------
    # RAW DATA FETCHERS — one per time window
    # ------------------------------------------------------------------

    def fetch_jobs_by_window(
        self,
        company_name: Optional[str] = None,
        company_domain: Optional[str] = None,
        max_age_days: int = 180,
        limit: int = 25,
    ) -> list[dict]:
        """
        Fetch nutraceutical job postings for a specific company or across
        all nutra companies within the given day window.
        """
        payload = {
            **DEFAULT_JOB_SEARCH_PARAMS,
            "posted_at_max_age_days": max_age_days,
            "limit": limit,
        }

        if company_name:
            payload["company_name_or"] = [company_name]
        if company_domain:
            payload["company_domain_or"] = [company_domain]

        # Broad nutra search: job_title_or works on its own with posted_at_max_age_days
        # (confirmed via API diagnostic). Do NOT pass company_name_or for broad searches
        # as it requires exact matches and filters out most results.
        if not company_name and not company_domain:
            payload["job_title_or"] = [
                "Quality Assurance",
                "Regulatory Affairs",
                "Formulation Scientist",
                "Nutraceutical",
                "Dietary Supplement",
                "Food Scientist",
                "cGMP",
                "GMP Compliance",
                "Supplement",
                "Sports Nutrition",
                "Botanical Extract",
                "Probiotic",
            ]

        data = self._search_jobs(payload)
        return data.get("data", [])

    def fetch_nutra_companies_jobs(
        self,
        max_age_days: int = 180,
        limit: int = 25,
    ) -> list[dict]:
        """
        Pull the most recent nutraceutical industry job postings across
        all companies — scoped by nutra-specific job title keywords.
        This is the broad "prospecting" pull.
        """
        return self.fetch_jobs_by_window(max_age_days=max_age_days, limit=limit)

    # ------------------------------------------------------------------
    # SIGNAL COMPUTATION
    # ------------------------------------------------------------------

    @staticmethod
    def classify_seniority(title: str) -> tuple[str, int]:
        """
        Classify a job title into a seniority tier and return its weight.
        Returns (tier_name, weight).
        """
        title_lower = title.lower()
        for tier, patterns in SENIORITY_TITLE_PATTERNS.items():
            if any(p in title_lower for p in patterns):
                return tier, SENIORITY_WEIGHTS.get(tier, 1)
        return "default", SENIORITY_WEIGHTS["default"]

    @staticmethod
    def classify_department(title: str) -> str:
        """
        Classify a job title into a functional department.
        Returns department label string.
        """
        title_lower = title.lower()
        for dept, keywords in DEPT_KEYWORD_MAP.items():
            if any(kw in title_lower for kw in keywords):
                return dept
        return "Other"

    @staticmethod
    def is_niche_nutra_role(title: str, description: str = "") -> bool:
        """
        Returns True if the job is a hard-to-fill nutraceutical niche role.
        Checks both title and description.
        """
        combined = (title + " " + description).lower()
        return any(kw.lower() in combined for kw in NICHE_ROLE_KEYWORDS)

    @staticmethod
    def compute_days_open(job: dict) -> int:
        """
        Calculate how many days a job has been open.
        Uses 'date_posted' field from TheirStack. Falls back to 0 if missing.
        """
        date_str = job.get("date_posted") or job.get("posted_at")
        if not date_str:
            return 0
        try:
            posted = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return max(0, (now - posted).days)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def compute_velocity_ratio(
        jobs_30d: int,
        jobs_31_90d: int,
    ) -> float:
        """
        V_R = Jobs Posted (Last 30d) / (Jobs Posted (Days 31-90) / 2)
        Returns 0.0 if denominator is 0 (no baseline activity = no ratio).
        """
        if jobs_31_90d == 0:
            return float(jobs_30d) if jobs_30d > 0 else 0.0
        return jobs_30d / (jobs_31_90d / 2)

    @staticmethod
    def compute_velocity_confidence(total_postings_90d: int) -> tuple[str, float]:
        """
        Returns (sample_size_flag, confidence_multiplier) based on total 90d postings.
        Low volume dampens noisy velocity signals.
        """
        for label, cfg in VELOCITY_CONFIDENCE_MULTIPLIERS.items():
            if total_postings_90d <= cfg["max_postings"]:
                return label, cfg["multiplier"]
        return "high", 1.0

    @staticmethod
    def compute_tpi(jobs: list[dict]) -> float:
        """
        Talent Pain Index (TPI):
          TPI = sum( min(1.0, days_open/90) x seniority_weight x niche_multiplier )

        Higher TPI = deeper talent pain = stronger BD case for agency engagement.
        """
        tpi = 0.0
        for job in jobs:
            days = TheirStackCollector.compute_days_open(job)
            aging_score = min(1.0, days / STALE_JOB_THRESHOLDS["critical"])
            _, seniority_weight = TheirStackCollector.classify_seniority(
                job.get("job_title", "")
            )
            niche_multiplier = 1.5 if TheirStackCollector.is_niche_nutra_role(
                job.get("job_title", ""),
                job.get("description", ""),
            ) else 1.0
            tpi += aging_score * seniority_weight * niche_multiplier
        return round(tpi, 2)

    @staticmethod
    def get_staleness_label(days: int) -> str:
        """Returns a human-readable staleness label."""
        if days >= STALE_JOB_THRESHOLDS["critical"]:
            return "CRITICAL"
        elif days >= STALE_JOB_THRESHOLDS["pain"]:
            return "HIGH"
        elif days >= STALE_JOB_THRESHOLDS["watch"]:
            return "WATCH"
        else:
            return "FRESH"

    # ------------------------------------------------------------------
    # FULL COMPANY-LEVEL ANALYSIS
    # ------------------------------------------------------------------

    def analyze_company(
        self,
        company_name: str,
        company_domain: Optional[str] = None,
    ) -> dict:
        """
        Full TheirStack signal analysis for a single nutraceutical company.

        Returns a structured dict containing all hiring signals needed
        for the BD propensity score.
        """
        print(f"\n[TheirStack] Fetching jobs for: {company_name}...")

        # Fetch all jobs in 180d window for this company
        all_jobs_180d = self.fetch_jobs_by_window(
            company_name=company_name,
            company_domain=company_domain,
            max_age_days=180,
            limit=25,
        )

        now = datetime.now(timezone.utc)

        # Bucket jobs into time windows
        jobs_7d, jobs_30d, jobs_31_90d, jobs_91_180d = [], [], [], []

        for job in all_jobs_180d:
            days = self.compute_days_open(job)
            if days <= 7:
                jobs_7d.append(job)
            if days <= 30:
                jobs_30d.append(job)
            elif days <= 90:
                jobs_31_90d.append(job)
            else:
                jobs_91_180d.append(job)

        total_90d = len(jobs_30d) + len(jobs_31_90d)

        # --- Velocity ---
        raw_vr = self.compute_velocity_ratio(len(jobs_30d), len(jobs_31_90d))
        sample_flag, confidence_mult = self.compute_velocity_confidence(total_90d)
        adjusted_vr = round(raw_vr * confidence_mult, 2)

        # --- TPI on all currently open jobs (0-90d jobs) ---
        open_jobs = [j for j in all_jobs_180d if self.compute_days_open(j) <= 180]
        tpi = self.compute_tpi(open_jobs)

        # --- Department breakdown ---
        dept_counts = defaultdict(int)
        for job in open_jobs:
            dept = self.classify_department(job.get("job_title", ""))
            dept_counts[dept] += 1

        # --- Stale roles analysis ---
        stale_roles = []
        for job in open_jobs:
            days = self.compute_days_open(job)
            if days >= STALE_JOB_THRESHOLDS["watch"]:
                _, seniority_weight = self.classify_seniority(job.get("job_title", ""))
                stale_roles.append({
                    "job_id": job.get("id"),
                    "title": job.get("job_title", "Unknown"),
                    "days_open": days,
                    "staleness_label": self.get_staleness_label(days),
                    "seniority_weight": seniority_weight,
                    "is_niche_role": self.is_niche_nutra_role(
                        job.get("job_title", ""),
                        job.get("description", ""),
                    ),
                    "url": job.get("url", ""),
                    "location": job.get("location", ""),
                })

        # Sort stale roles by days open descending
        stale_roles.sort(key=lambda x: x["days_open"], reverse=True)

        # --- Posting channel diversity ---
        channels = set()
        for job in open_jobs:
            sources = job.get("sources") or []
            if isinstance(sources, list):
                channels.update(sources)
        channel_diversity = sorted(list(channels))

        # --- Niche role count ---
        niche_role_count = sum(
            1 for j in open_jobs
            if self.is_niche_nutra_role(j.get("job_title", ""), j.get("description", ""))
        )

        # --- Unique role diversity (count of distinct titles) ---
        unique_titles = set(j.get("job_title", "").strip().lower() for j in open_jobs)
        unique_role_diversity = len(unique_titles)

        print(f"  [OK] {len(all_jobs_180d)} jobs in 180d | VR_adj={adjusted_vr} | TPI={tpi} | Stale={len(stale_roles)}")

        return {
            "company_name": company_name,
            "company_domain": company_domain,
            "analysis_timestamp": now.isoformat(),

            # --- Volume by window ---
            "job_counts": {
                "last_7d": len(jobs_7d),
                "last_30d": len(jobs_30d),
                "days_31_to_90": len(jobs_31_90d),
                "days_91_to_180": len(jobs_91_180d),
                "total_90d": total_90d,
                "total_180d": len(all_jobs_180d),
            },

            # --- Velocity ---
            "velocity": {
                "raw_velocity_ratio": round(raw_vr, 2),
                "sample_size_flag": sample_flag,
                "confidence_multiplier": confidence_mult,
                "adjusted_velocity_ratio": adjusted_vr,
            },

            # --- Talent Pain ---
            "talent_pain": {
                "tpi_score": tpi,
                "stale_roles_count": len(stale_roles),
                "critical_roles": [r for r in stale_roles if r["staleness_label"] == "CRITICAL"],
                "high_pain_roles": [r for r in stale_roles if r["staleness_label"] == "HIGH"],
                "watch_roles": [r for r in stale_roles if r["staleness_label"] == "WATCH"],
                "all_stale_roles": stale_roles,
            },

            # --- Department ---
            "department_breakdown": dict(dept_counts),

            # --- Role diversity ---
            "niche_role_count": niche_role_count,
            "unique_role_diversity": unique_role_diversity,

            # --- Channel diversity ---
            "posting_channel_diversity": channel_diversity,
        }

    # ------------------------------------------------------------------
    # BATCH ANALYSIS — Multiple companies
    # ------------------------------------------------------------------

    def analyze_companies(
        self,
        companies: list[dict],
        delay_seconds: float = 0.5,
    ) -> list[dict]:
        """
        Run full TheirStack analysis across a list of companies.

        companies = list of dicts with keys: "name", optionally "domain"
        delay_seconds = pause between API calls to stay within rate limits

        Returns list of company analysis dicts.
        """
        results = []
        for i, company in enumerate(companies):
            name = company.get("name", "")
            domain = company.get("domain")
            if not name:
                continue
            print(f"\n[{i+1}/{len(companies)}] Analyzing: {name}")
            try:
                result = self.analyze_company(name, domain)
                results.append(result)
            except Exception as e:
                print(f"  [ERROR] {name}: {e}")
                results.append({
                    "company_name": name,
                    "company_domain": domain,
                    "error": str(e),
                })
            time.sleep(delay_seconds)
        return results

    # ------------------------------------------------------------------
    # BROAD NUTRA PROSPECTING — No specific company
    # ------------------------------------------------------------------

    def prospect_nutra_market(self, max_age_days: int = 90) -> dict:
        """
        Pull all nutraceutical job postings across the market (no company filter).
        Groups by company name to surface top BD targets.
        
        Returns a ranked dict: {company_name: signal_summary}
        """
        print(f"\n[TheirStack] Broad nutra market prospecting (last {max_age_days}d)...")
        jobs = self.fetch_nutra_companies_jobs(max_age_days=max_age_days, limit=25)

        if not jobs:
            print("  [WARN] No jobs returned from broad search.")
            return {}

        # Group by company
        company_jobs = defaultdict(list)
        for job in jobs:
            # TheirStack returns company info in a nested 'company' object
            # Guard against both dict and string types
            raw_co = job.get("company")
            if isinstance(raw_co, dict):
                company_obj = raw_co
            else:
                company_obj = {}
            company = (
                company_obj.get("name")
                or job.get("company_name")
                or company_obj.get("domain")
                or (raw_co if isinstance(raw_co, str) else None)
                or "Unknown"
            )
            company_jobs[company].append(job)

        # Quick-compute signals per company without a second API call
        ranked = {}
        for company, company_job_list in company_jobs.items():
            if company == "Unknown":
                continue

            tpi = self.compute_tpi(company_job_list)
            stale_count = sum(
                1 for j in company_job_list
                if self.compute_days_open(j) >= STALE_JOB_THRESHOLDS["watch"]
            )
            niche_count = sum(
                1 for j in company_job_list
                if self.is_niche_nutra_role(j.get("job_title", ""), j.get("description", ""))
            )
            dept_counts = defaultdict(int)
            for job in company_job_list:
                dept = self.classify_department(job.get("job_title", ""))
                dept_counts[dept] += 1

            ranked[company] = {
                "total_open_roles": len(company_job_list),
                "tpi_score": tpi,
                "stale_roles_count": stale_count,
                "niche_roles_count": niche_count,
                "department_breakdown": dict(dept_counts),
                "sample_jobs": [
                    {
                        "title": j.get("job_title"),
                        "days_open": self.compute_days_open(j),
                        "staleness": self.get_staleness_label(self.compute_days_open(j)),
                        "url": j.get("url", ""),
                    }
                    for j in sorted(company_job_list, key=lambda x: self.compute_days_open(x), reverse=True)[:5]
                ],
            }

        # Sort by TPI descending
        ranked = dict(sorted(ranked.items(), key=lambda x: x[1]["tpi_score"], reverse=True))
        print(f"  [OK] Found {len(ranked)} nutraceutical companies with active postings.")
        return ranked
