"""
apify_collector.py — Nutraceutical BD Engine: Apify LinkedIn Company & Headcount Collector

Integrates with Apify Actor: `automation-lab/linkedin-company-scraper`
Pulls verified LinkedIn firmographics, exact employee count, follower growth,
and computes historical headcount growth deltas (%).
"""

import os
import time
import requests
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
APIFY_BASE_URL = "https://api.apify.com/v2"
ACTOR_ID = "automation-lab~linkedin-company-scraper"


class ApifyCollector:
    """
    Collects LinkedIn company firmographics and exact employee headcount data
    using Apify's LinkedIn Company Scraper actor.
    """

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or APIFY_API_TOKEN or os.environ.get("APIFY_API_TOKEN", "")
        self.session = requests.Session()

    def is_configured(self) -> bool:
        """Check if an Apify API token is configured."""
        return bool(self.api_token and len(self.api_token) > 5)

    def scrape_companies_batch(
        self,
        company_urls: List[str],
        timeout_secs: int = 180,
    ) -> List[Dict[str, Any]]:
        """
        Run Apify Actor on a list of LinkedIn company URLs using asynchronous run
        with automatic polling to avoid synchronous gateway timeouts.

        Args:
            company_urls: List of LinkedIn company URLs
            timeout_secs: Maximum total wait time
        """
        if not self.is_configured():
            print("  [Apify WARN] APIFY_API_TOKEN not configured.")
            return []

        if not company_urls:
            return []

        # 1. Start the Actor Run asynchronously
        start_url = f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/runs"
        params = {"token": self.api_token}
        payload = {
            "companyUrls": company_urls,
            "maxConcurrency": 5,
        }

        try:
            resp = self.session.post(start_url, params=params, json=payload, timeout=20)
            if not resp.ok:
                print(f"  [Apify ERROR {resp.status_code}] {resp.text[:200]}")
                return []

            run_data = resp.json().get("data", {})
            run_id = run_data.get("id")
            dataset_id = run_data.get("defaultDatasetId")

            if not run_id or not dataset_id:
                print("  [Apify ERROR] Failed to obtain run ID from actor launch.")
                return []

            print(f"  [Apify] Run started (ID: {run_id}). Polling for results...")

            # 2. Poll run status until SUCCEEDED or timeout
            start_time = time.time()
            while time.time() - start_time < timeout_secs:
                time.sleep(5)
                status_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
                status_resp = self.session.get(status_url, params=params, timeout=15)
                if status_resp.ok:
                    status = status_resp.json().get("data", {}).get("status")
                    if status == "SUCCEEDED":
                        break
                    elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                        print(f"  [Apify ERROR] Run ended with status: {status}")
                        return []

            # 3. Fetch dataset items
            items_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items"
            items_resp = self.session.get(items_url, params=params, timeout=20)
            if items_resp.ok:
                items = items_resp.json()
                if isinstance(items, list):
                    return [self._format_company_record(item) for item in items]
            return []

        except Exception as e:
            print(f"  [Apify ERROR] {e}")
            return []

    def scrape_company(
        self,
        company_name: str,
        linkedin_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Scrapes a single company's LinkedIn profile data."""
        target_url = linkedin_url
        if not target_url:
            clean_slug = (
                company_name.lower()
                .replace(" ", "-")
                .replace("&", "and")
                .replace(",", "")
                .replace(".", "")
                .strip("-")
            )
            target_url = f"https://www.linkedin.com/company/{clean_slug}"

        results = self.scrape_companies_batch([target_url], timeout_secs=60)
        return results[0] if results else None

    @staticmethod
    def _format_company_record(item: dict) -> dict:
        """Normalize raw Apify actor output into a clean schema."""
        raw_emp = item.get("employeeCount") or item.get("employeesCount") or item.get("staffCount") or 0
        try:
            emp_count = int(raw_emp) if raw_emp else 0
        except (ValueError, TypeError):
            emp_count = 0

        raw_followers = item.get("followerCount") or item.get("followersCount") or 0
        try:
            follower_count = int(raw_followers) if raw_followers else 0
        except (ValueError, TypeError):
            follower_count = 0

        return {
            "company_name": item.get("name") or item.get("companyName", ""),
            "linkedin_url": item.get("url") or item.get("linkedinUrl", ""),
            "website": item.get("website", ""),
            "employee_count": emp_count,
            "employee_range": item.get("employeeRange") or item.get("companySize", "Unknown"),
            "follower_count": follower_count,
            "industry": item.get("industry", "Nutraceutical / Health & Wellness"),
            "headquarters": {
                "city": item.get("headquartersCity") or item.get("city", ""),
                "state": item.get("headquartersState") or item.get("state", ""),
                "country": item.get("headquartersCountry") or item.get("country", "US"),
            },
            "specialties": item.get("specialties", []),
            "description": item.get("description", "")[:300],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def calculate_headcount_growth(
        current_headcount: int,
        previous_headcount: int,
        days_between: int = 30,
    ) -> dict:
        """Computes exact headcount growth percentage and annualized trajectory."""
        if not previous_headcount or previous_headcount <= 0:
            return {
                "current_headcount": current_headcount,
                "previous_headcount": previous_headcount,
                "growth_pct": 0.0,
                "annualized_growth_pct": 0.0,
                "status": "INITIAL_BASELINE",
                "trajectory": "STABLE",
            }

        delta = current_headcount - previous_headcount
        growth_pct = round((delta / previous_headcount) * 100.0, 2)
        annualized_pct = round(growth_pct * (365.0 / max(1, days_between)), 2)

        if growth_pct >= 15.0:
            trajectory = "HYPER_GROWTH"
        elif growth_pct >= 5.0:
            trajectory = "STEADY_EXPANSION"
        elif growth_pct > -5.0:
            trajectory = "STABLE"
        elif growth_pct > -15.0:
            trajectory = "MODERATE_CONTRACTION"
        else:
            trajectory = "SEVERE_ATTRITION"

        return {
            "current_headcount": current_headcount,
            "previous_headcount": previous_headcount,
            "net_headcount_delta": delta,
            "days_between": days_between,
            "growth_pct": growth_pct,
            "annualized_growth_pct": annualized_pct,
            "trajectory": trajectory,
            "status": "CALCULATED",
        }

    def analyze_company(
        self,
        company_name: str,
        linkedin_url: Optional[str] = None,
        previous_headcount: Optional[int] = None,
        days_since_last_check: int = 30,
    ) -> dict:
        """Full BD analysis for a company's LinkedIn presence and headcount growth."""
        if not self.is_configured():
            return {
                "company_name": company_name,
                "status": "UNCONFIGURED_TOKEN",
                "message": "APIFY_API_TOKEN not configured.",
                "firmographics": None,
                "headcount_growth": None,
            }

        company_data = self.scrape_company(company_name, linkedin_url=linkedin_url)
        if not company_data:
            return {
                "company_name": company_name,
                "status": "NOT_FOUND",
                "firmographics": None,
                "headcount_growth": None,
            }

        current_headcount = company_data.get("employee_count", 0)
        growth_analysis = self.calculate_headcount_growth(
            current_headcount=current_headcount,
            previous_headcount=previous_headcount or current_headcount,
            days_between=days_since_last_check,
        )

        return {
            "company_name": company_name,
            "status": "SUCCESS",
            "firmographics": company_data,
            "headcount_growth": growth_analysis,
        }
