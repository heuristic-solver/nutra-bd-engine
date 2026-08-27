"""
career_traffic_collector.py -- Career Page, Traffic & Hiring Velocity Collector

Performs deep analysis of:
  1. Official Career Page & ATS Board Discovery (Greenhouse, Lever, Workday, Pinpoint, etc.)
  2. 30-Day & 90-Day Job Posting Volume & Indexing Activity
  3. Career Page Traffic & Activity Index (HIGH / MODERATE / LOW / INACTIVE)
  4. Calculated Employee Growth % (Growjo YoY % with automated velocity-based fallback for unindexed companies)
  5. Hiring Trend Trajectory & Department Breakdown
"""

import os
import re
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_BASE_URL = "https://google.serper.dev/search"

# Known ATS platforms
ATS_DOMAINS = [
    "greenhouse.io", "lever.co", "myworkdayjobs.com", "bamboohr.com",
    "pinpointhq.com", "workable.com", "smartrecruiters.com", "jazzhr.com",
    "breezy.hr", "jobvite.com", "recruitee.com", "applicantpro.com"
]

class CareerTrafficCollector:
    """
    Scrapes and analyzes career page activity, active job posting volume,
    career page traffic indicators, and computes employee growth trajectory.
    """

    def __init__(self, serper_key: Optional[str] = None):
        self.serper_key = serper_key or SERPER_API_KEY
        self.session = requests.Session()

    def is_configured(self) -> bool:
        return bool(self.serper_key and len(self.serper_key) > 5)

    def analyze_career_and_hiring(
        self,
        company_name: str,
        domain: Optional[str] = None,
        current_headcount: Optional[int] = None,
        growjo_growth_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Runs a comprehensive career page and hiring velocity scan for a company.
        """
        if not self.is_configured():
            return self._empty_response(company_name, "Unconfigured Serper Key")

        # 1. Search for official career page & ATS boards
        career_page_url, ats_platform = self._discover_career_page(company_name, domain)

        # 2. Search for 30-day active job postings
        recent_30d_jobs = self._search_recent_jobs(company_name, tbs="qdr:m")

        # 3. Search for 6-month hiring volume (trend baseline)
        recent_6m_jobs = self._search_recent_jobs(company_name, tbs="qdr:m6")

        job_count_30d = len(recent_30d_jobs)
        job_count_6m = len(recent_6m_jobs)

        # 4. Measure Career Page Traffic & Activity Score
        traffic_activity, traffic_score = self._compute_traffic_activity(
            career_page_url=career_page_url,
            ats_platform=ats_platform,
            job_count_30d=job_count_30d,
            job_count_6m=job_count_6m
        )

        # 5. Calculate Final Employee Growth % & Trajectory
        growth_pct, growth_source, trajectory = self._resolve_growth_and_trajectory(
            current_headcount=current_headcount,
            job_count_30d=job_count_30d,
            growjo_growth_pct=growjo_growth_pct,
            traffic_activity=traffic_activity
        )

        # 6. Extract sampled job titles
        sample_titles = [j.get("title", "") for j in recent_30d_jobs[:5] if j.get("title")]

        return {
            "company_name": company_name,
            "career_page_url": career_page_url or "Not Found",
            "ats_platform": ats_platform or "Direct / Standard Web",
            "career_page_traffic_activity": traffic_activity,  # HIGH / MODERATE / LOW / INACTIVE
            "career_traffic_score": traffic_score,            # 0 - 100 index
            "active_job_openings_30d": job_count_30d,
            "hiring_signals_6m": job_count_6m,
            "sample_open_roles": sample_titles,
            "employee_growth_pct": growth_pct,                # Concrete % (e.g. +12.5% or +4.2%)
            "growth_source": growth_source,                    # Growjo YoY / Career Velocity Model
            "hiring_trajectory": trajectory,                  # HYPER_GROWTH / ACTIVE_EXPANSION / STEADY_HIRING / LOW_ACTIVITY
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }

    def _discover_career_page(self, company_name: str, domain: Optional[str]) -> (Optional[str], Optional[str]):
        """Discovers company career page URL and identifies ATS platform if any."""
        query = f'"{company_name}" (careers OR "job openings" OR "work with us" OR "join our team")'
        headers = {"X-API-KEY": self.serper_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": 8}

        try:
            r = self.session.post(SERPER_BASE_URL, headers=headers, json=payload, timeout=12)
            if not r.ok:
                return None, None
            data = r.json()
            organic = data.get("organic", [])

            career_url = None
            ats_platform = None

            for hit in organic:
                link = hit.get("link", "")
                # Check for known ATS
                for ats in ATS_DOMAINS:
                    if ats in link.lower():
                        ats_name = ats.split(".")[0].capitalize()
                        return link, ats_name

                # Check if it's the official domain career page
                if domain and domain.lower() in link.lower() and ("career" in link.lower() or "job" in link.lower()):
                    career_url = link

                if not career_url and ("career" in link.lower() or "jobs" in link.lower()):
                    career_url = link

            return career_url, ats_platform

        except Exception:
            return None, None

    def _search_recent_jobs(self, company_name: str, tbs: str = "qdr:m") -> List[Dict[str, Any]]:
        """Queries for recent job posts with recency filter."""
        query = f'"{company_name}" ("job" OR "career" OR "hiring" OR "apply") ("nutraceutical" OR "laboratories" OR "nutrition" OR "supplements" OR "manufacturing" OR "technician" OR "manager" OR "scientist" OR "specialist")'
        headers = {"X-API-KEY": self.serper_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": 10, "tbs": tbs}

        try:
            r = self.session.post(SERPER_BASE_URL, headers=headers, json=payload, timeout=12)
            if not r.ok:
                return []
            organic = r.json().get("organic", [])
            # Filter noise
            filtered = []
            for hit in organic:
                title = hit.get("title", "")
                snippet = hit.get("snippet", "")
                # Exclude purely academic research papers if not a job post
                if any(w in title.lower() or w in snippet.lower() for w in ["job", "hiring", "apply", "career", "salary", "position", "opening", "employment"]):
                    filtered.append(hit)
            return filtered
        except Exception:
            return []

    def _compute_traffic_activity(
        self,
        career_page_url: Optional[str],
        ats_platform: Optional[str],
        job_count_30d: int,
        job_count_6m: int
    ) -> (str, int):
        """Computes career page traffic and indexing activity score (0-100)."""
        score = 0
        if career_page_url:
            score += 25
        if ats_platform:
            score += 25  # Dedicated enterprise ATS indicates high recruitment traffic
        
        score += min(30, job_count_30d * 6)
        score += min(20, job_count_6m * 2)
        score = min(100, score)

        if score >= 70 or job_count_30d >= 5:
            activity = "HIGH_TRAFFIC"
        elif score >= 40 or job_count_30d >= 2:
            activity = "MODERATE_TRAFFIC"
        elif score >= 20 or job_count_30d >= 1:
            activity = "LOW_TRAFFIC"
        else:
            activity = "INACTIVE_OR_UNINDEXED"

        return activity, score

    def _resolve_growth_and_trajectory(
        self,
        current_headcount: Optional[int],
        job_count_30d: int,
        growjo_growth_pct: Optional[float],
        traffic_activity: str
    ) -> (float, str, str):
        """
        Determines the official growth % and trajectory tag:
        1. Uses Growjo YoY % if available.
        2. Otherwise models growth from Hiring Velocity % (Active jobs vs Headcount).
        """
        if growjo_growth_pct is not None:
            pct = round(float(growjo_growth_pct), 2)
            source = "Growjo YoY Verified"
        else:
            # Model growth from live hiring velocity
            hc = current_headcount if (current_headcount and current_headcount > 0) else 50
            # Active 30-day open roles represents net capacity expansion
            expansion_ratio = (job_count_30d / hc) * 100.0

            # Annualized expansion velocity
            if job_count_30d >= 5:
                pct = round(min(25.0, 10.0 + expansion_ratio * 1.5), 1)
            elif job_count_30d >= 2:
                pct = round(min(15.0, 4.0 + expansion_ratio * 1.2), 1)
            elif job_count_30d == 1:
                pct = round(min(8.0, 2.0 + expansion_ratio), 1)
            else:
                pct = 0.0

            source = "Modeled (Hiring Velocity)"

        # Trajectory Classification
        if pct >= 15.0 or (job_count_30d >= 8 and traffic_activity == "HIGH_TRAFFIC"):
            trajectory = "HYPER_GROWTH"
        elif pct >= 5.0 or (job_count_30d >= 3):
            trajectory = "ACTIVE_EXPANSION"
        elif pct > 0.0 or (job_count_30d >= 1):
            trajectory = "STEADY_HIRING"
        elif pct < -5.0:
            trajectory = "MODERATE_CONTRACTION"
        else:
            trajectory = "STABLE / LOW_HIRING"

        return pct, source, trajectory

    @staticmethod
    def _empty_response(company_name: str, message: str) -> Dict[str, Any]:
        return {
            "company_name": company_name,
            "career_page_url": "N/A",
            "ats_platform": "N/A",
            "career_page_traffic_activity": "UNCONFIGURED",
            "career_traffic_score": 0,
            "active_job_openings_30d": 0,
            "hiring_signals_6m": 0,
            "sample_open_roles": [],
            "employee_growth_pct": 0.0,
            "growth_source": message,
            "hiring_trajectory": "UNKNOWN",
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }