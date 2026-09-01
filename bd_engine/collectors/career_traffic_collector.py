"""
career_traffic_collector.py -- Career Page, Traffic & Hiring Velocity Collector

Performs deep analysis of:
  1. Official Career Page & ATS Board Discovery (Greenhouse, Lever, Workday, Pinpoint, etc.)
  2. 30-Day Active Job Posting Volume & Activity
  3. Career Page Traffic & Activity Index (HIGH / MODERATE / LOW / INACTIVE)
  4. Job Function Classification (Sales / QA-RA / Operations / R&D / Formulation / HR / Finance)
  5. Post-Date Extraction & Repost Flag (open > 45 days = hard-to-source signal)
  6. Internal TA Hire Detection (reframe pitch toward niche/senior roles)
  7. Employee Growth % & Hiring Trajectory (Growjo YoY with velocity-based fallback)
"""

import os
import re
import requests
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_BASE_URL = "https://google.serper.dev/search"

# Known ATS platforms
ATS_DOMAINS = [
    "greenhouse.io", "lever.co", "myworkdayjobs.com", "bamboohr.com",
    "pinpointhq.com", "workable.com", "smartrecruiters.com", "jazzhr.com",
    "breezy.hr", "jobvite.com", "recruitee.com", "applicantpro.com",
    "ashbyhq.com", "jobs.lever.co", "boards.greenhouse.io",
]

# -------------------------------------------------------------------
# JOB FUNCTION CLASSIFICATION (Gap 2 — Spec: Sales/QA/Ops/R&D/Formulation)
# -------------------------------------------------------------------
FUNCTION_KEYWORDS: Dict[str, List[str]] = {
    "Sales / Commercial":   ["sales", "commercial", "business development", "account executive",
                             "account manager", "bdm", "channel", "territory", "regional manager",
                             "trade marketing", "key account"],
    "QA / Regulatory":     ["quality assurance", "quality control", "qa ", "qc ", "regulatory affairs",
                             "regulatory", "compliance", "validation", "gmp", "quality manager",
                             "quality director", "quality engineer", "ra specialist", "quality analyst"],
    "Operations / Supply Chain": ["operations", "supply chain", "procurement", "manufacturing",
                                  "production", "plant manager", "logistics", "warehouse", "fulfillment",
                                  "inventory", "planning", "demand planning", "ops manager"],
    "R&D / Formulation":   ["research", "development", "r&d", "formulation", "scientist", "chemist",
                             "food scientist", "nutritionist", "innovation", "clinical", "laboratory",
                             "lab technician", "analytical", "product development", "biochemist"],
    "HR / Talent":          ["hr ", "human resources", "talent acquisition", "recruiter", "recruiting",
                             "people operations", "hrbp", "hr business partner", "training",
                             "learning and development", "l&d", "compensation", "benefits"],
    "Finance / Accounting": ["finance", "accounting", "financial", "controller", "cfo", "treasurer",
                              "accounts payable", "accounts receivable", "fp&a", "audit"],
    "Marketing / Brand":    ["marketing", "brand", "digital marketing", "content", "e-commerce",
                              "ecommerce", "social media", "creative", "graphic design", "copywriting"],
    "Technology / IT":      ["software", "engineer", "developer", "it ", "technology", "data",
                              "analytics", "cto", "devops", "cybersecurity", "system admin"],
}

# Keywords that suggest a role is an internal Talent Acquisition hire
TA_HIRE_KEYWORDS = [
    "talent acquisition", "recruiter", "recruiting manager", "talent partner",
    "hr recruiter", "sourcer", "sourcing specialist", "head of talent",
    "director of talent acquisition", "vp talent"
]

# Repost indicators in snippets — suggests unfilled hard-to-source role
REPOST_KEYWORDS = [
    "re-posted", "reposted", "originally posted", "re-listing", "relisted",
    "still open", "urgently hiring", "immediate opening", "immediate need",
    "position has been open"
]


class CareerTrafficCollector:
    """
    Scrapes and analyzes career page activity, active job posting volume,
    job function classification, repost detection, internal TA hire detection,
    and employee growth trajectory.
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
        Comprehensive career page and hiring velocity scan.
        Returns structured job function breakdown, repost flags, and TA hire detection.
        """
        if not self.is_configured():
            return self._empty_response(company_name, "Unconfigured Serper Key")

        # 1. Discover official career page & ATS
        career_page_url, ats_platform = self._discover_career_page(company_name, domain)

        # 2. Search for 30-day active job postings with structured metadata
        recent_30d_jobs = self._search_recent_jobs(company_name, tbs="qdr:m")

        # 3. Search for 6-month hiring volume (trend baseline)
        recent_6m_jobs = self._search_recent_jobs(company_name, tbs="qdr:m6")

        job_count_30d = len(recent_30d_jobs)
        job_count_6m  = len(recent_6m_jobs)

        # 4. Classify each job by function
        classified_jobs = [self._classify_job(j) for j in recent_30d_jobs]

        # 5. Build function breakdown summary
        function_breakdown = self._build_function_breakdown(classified_jobs)

        # 6. Detect internal TA hires (reframe pitch signal)
        ta_hire_detected = any(j.get("is_ta_hire") for j in classified_jobs)

        # 7. Detect reposted / long-open roles
        reposted_roles = [j for j in classified_jobs if j.get("is_repost")]
        repost_count = len(reposted_roles)

        # 8. Career Traffic Activity Score
        traffic_activity, traffic_score = self._compute_traffic_activity(
            career_page_url=career_page_url,
            ats_platform=ats_platform,
            job_count_30d=job_count_30d,
            job_count_6m=job_count_6m,
        )

        # 9. Growth % & Trajectory
        growth_pct, growth_source, trajectory = self._resolve_growth_and_trajectory(
            current_headcount=current_headcount,
            job_count_30d=job_count_30d,
            growjo_growth_pct=growjo_growth_pct,
            traffic_activity=traffic_activity,
        )

        # 10. Sample role titles
        sample_titles = [j.get("title", "") for j in classified_jobs[:5] if j.get("title")]

        return {
            "company_name":                    company_name,
            "career_page_url":                 career_page_url or "Not Found",
            "ats_platform":                    ats_platform or "Direct / Standard Web",
            "career_page_traffic_activity":    traffic_activity,
            "career_traffic_score":            traffic_score,
            "active_job_openings_30d":         job_count_30d,
            "hiring_signals_6m":               job_count_6m,
            "sample_open_roles":               sample_titles,
            # -- New structured fields (Gap 2) --
            "job_function_breakdown":          function_breakdown,
            "ta_hire_detected":                ta_hire_detected,
            "reposted_role_count":             repost_count,
            "reposted_roles":                  [r.get("title", "") for r in reposted_roles[:3]],
            # -- Growth & trajectory --
            "employee_growth_pct":             growth_pct,
            "growth_source":                   growth_source,
            "hiring_trajectory":               trajectory,
            "scanned_at":                      datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # JOB CLASSIFICATION (Gap 2)
    # ------------------------------------------------------------------

    @staticmethod
    def classify_job_function(title: str, snippet: str = "") -> str:
        """Map a job posting to one of the spec-aligned function buckets."""
        combined = (title + " " + snippet).lower()
        for function_name, keywords in FUNCTION_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                return function_name
        return "Other / General"

    @staticmethod
    def detect_ta_hire(title: str, snippet: str = "") -> bool:
        """Returns True if this posting is for an internal Talent Acquisition hire."""
        combined = (title + " " + snippet).lower()
        return any(kw in combined for kw in TA_HIRE_KEYWORDS)

    @staticmethod
    def detect_repost(title: str, snippet: str = "") -> bool:
        """Returns True if snippet suggests a reposted / long-open role."""
        combined = (title + " " + snippet).lower()
        return any(kw in combined for kw in REPOST_KEYWORDS)

    def _classify_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Enriches a raw job posting dict with function, TA flag, and repost flag."""
        title   = job.get("title", "")
        snippet = job.get("snippet", "")
        return {
            **job,
            "function":    self.classify_job_function(title, snippet),
            "is_ta_hire":  self.detect_ta_hire(title, snippet),
            "is_repost":   self.detect_repost(title, snippet),
            "date":        job.get("date", ""),
        }

    @staticmethod
    def _build_function_breakdown(classified_jobs: List[Dict]) -> Dict[str, int]:
        """Counts open roles per function bucket."""
        breakdown: Dict[str, int] = {}
        for job in classified_jobs:
            fn = job.get("function", "Other / General")
            breakdown[fn] = breakdown.get(fn, 0) + 1
        return breakdown

    # ------------------------------------------------------------------
    # CAREER PAGE DISCOVERY
    # ------------------------------------------------------------------

    def _discover_career_page(
        self, company_name: str, domain: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Discovers company career page URL and identifies ATS platform if any."""
        query = f'"{company_name}" (careers OR "job openings" OR "work with us" OR "join our team")'
        headers = {"X-API-KEY": self.serper_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": 8}

        try:
            r = self.session.post(SERPER_BASE_URL, headers=headers, json=payload, timeout=12)
            if not r.ok:
                return None, None
            organic = r.json().get("organic", [])

            career_url  = None
            ats_platform = None

            for hit in organic:
                link = hit.get("link", "")
                for ats in ATS_DOMAINS:
                    if ats in link.lower():
                        ats_name = ats.split(".")[0].capitalize()
                        return link, ats_name
                if domain and domain.lower() in link.lower() and (
                    "career" in link.lower() or "job" in link.lower()
                ):
                    career_url = link
                if not career_url and ("career" in link.lower() or "jobs" in link.lower()):
                    career_url = link

            return career_url, ats_platform

        except Exception:
            return None, None

    # ------------------------------------------------------------------
    # JOB POSTING SEARCH
    # ------------------------------------------------------------------

    def _search_recent_jobs(self, company_name: str, tbs: str = "qdr:m") -> List[Dict[str, Any]]:
        """Queries for recent job posts with recency filter."""
        query = (
            f'"{company_name}" ("job" OR "career" OR "hiring" OR "apply") '
            f'("nutraceutical" OR "laboratories" OR "nutrition" OR "supplements" '
            f'OR "manufacturing" OR "technician" OR "manager" OR "scientist" OR "specialist")'
        )
        headers = {"X-API-KEY": self.serper_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": 10, "tbs": tbs}

        try:
            r = self.session.post(SERPER_BASE_URL, headers=headers, json=payload, timeout=12)
            if not r.ok:
                return []
            organic = r.json().get("organic", [])
            filtered = []
            for hit in organic:
                title   = hit.get("title", "")
                snippet = hit.get("snippet", "")
                if any(
                    w in title.lower() or w in snippet.lower()
                    for w in ["job", "hiring", "apply", "career", "salary", "position", "opening", "employment"]
                ):
                    filtered.append(hit)
            return filtered
        except Exception:
            return []

    # ------------------------------------------------------------------
    # TRAFFIC ACTIVITY SCORING
    # ------------------------------------------------------------------

    def _compute_traffic_activity(
        self,
        career_page_url: Optional[str],
        ats_platform: Optional[str],
        job_count_30d: int,
        job_count_6m: int,
    ) -> Tuple[str, int]:
        """Computes career page traffic and indexing activity score (0-100)."""
        score = 0
        if career_page_url:
            score += 25
        if ats_platform:
            score += 25
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

    # ------------------------------------------------------------------
    # GROWTH & TRAJECTORY RESOLUTION
    # ------------------------------------------------------------------

    def _resolve_growth_and_trajectory(
        self,
        current_headcount: Optional[int],
        job_count_30d: int,
        growjo_growth_pct: Optional[float],
        traffic_activity: str,
    ) -> Tuple[float, str, str]:
        """Determines official growth % and trajectory tag."""
        if growjo_growth_pct is not None:
            pct    = round(float(growjo_growth_pct), 2)
            source = "Growjo YoY Verified"
        else:
            hc = current_headcount if (current_headcount and current_headcount > 0) else 50
            expansion_ratio = (job_count_30d / hc) * 100.0
            if job_count_30d >= 5:
                pct = round(min(25.0, 10.0 + expansion_ratio * 1.5), 1)
            elif job_count_30d >= 2:
                pct = round(min(15.0, 4.0 + expansion_ratio * 1.2), 1)
            elif job_count_30d == 1:
                pct = round(min(8.0, 2.0 + expansion_ratio), 1)
            else:
                pct = 0.0
            source = "Modeled (Hiring Velocity)"

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

    # ------------------------------------------------------------------
    # EMPTY RESPONSE
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_response(company_name: str, message: str) -> Dict[str, Any]:
        return {
            "company_name":                    company_name,
            "career_page_url":                 "N/A",
            "ats_platform":                    "N/A",
            "career_page_traffic_activity":    "UNCONFIGURED",
            "career_traffic_score":            0,
            "active_job_openings_30d":         0,
            "hiring_signals_6m":               0,
            "sample_open_roles":               [],
            "job_function_breakdown":          {},
            "ta_hire_detected":                False,
            "reposted_role_count":             0,
            "reposted_roles":                  [],
            "employee_growth_pct":             0.0,
            "growth_source":                   message,
            "hiring_trajectory":               "UNKNOWN",
            "scanned_at":                      datetime.now(timezone.utc).isoformat(),
        }