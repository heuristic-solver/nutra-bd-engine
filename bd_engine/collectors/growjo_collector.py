"""
growjo_collector.py -- Growjo company intelligence collector via Apify.

Actor: scrapesage/growjo-scraper
Returns: employeeGrowthPercent (YoY %), estimatedRevenue, totalFunding,
         currentEmployees, lastEmployees, jobOpenings, valuation,
         leadScore, competitors, linkedinUrl, and more.

Input field: companyNames (list of strings)
"""

import os
import time
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

APIFY_TOKEN  = os.environ.get("APIFY_API_TOKEN", "")
APIFY_BASE   = "https://api.apify.com/v2"
ACTOR_ID     = "scrapesage~growjo-scraper"


class GrowjoCollector:
    """
    Fetches year-over-year employee growth %, revenue, funding, and
    lead intelligence for nutraceutical companies via Growjo / Apify.
    """

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or APIFY_TOKEN
        self.session   = requests.Session()

    def is_configured(self) -> bool:
        return bool(self.api_token and len(self.api_token) > 5)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def fetch_companies(
        self,
        company_names: List[str],
        timeout_secs: int = 180,
    ) -> List[Dict[str, Any]]:
        """
        Run the Growjo actor for a list of company names.
        Returns a list of normalised company dicts.
        """
        if not self.is_configured():
            print("  [Growjo WARN] APIFY_API_TOKEN not configured.")
            return []
        if not company_names:
            return []

        payload = {
            "companyNames": company_names,
            "scrapeTopGrowing": False,
            "includeCompanyDetails": True,
            "includeContacts": False,
            "maxCompanies": len(company_names) * 2,
            "proxyConfiguration": {"useApifyProxy": True},
        }

        raw_items = self._run_actor(payload, timeout_secs)
        return [self._normalise(item) for item in raw_items]

    def fetch_company(
        self,
        company_name: str,
        timeout_secs: int = 180,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single company.  Returns None on miss."""
        results = self.fetch_companies([company_name], timeout_secs)
        # Best-match: exact name first, then first result
        for r in results:
            if r.get("company_name", "").lower() == company_name.lower():
                return r
        return results[0] if results else None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _run_actor(self, payload: dict, timeout: int) -> list:
        """Launch actor, poll until done, return raw dataset items."""
        params = {"token": self.api_token}

        try:
            resp = self.session.post(
                f"{APIFY_BASE}/acts/{ACTOR_ID}/runs",
                params=params,
                json=payload,
                timeout=25,
            )
        except Exception as exc:
            print(f"  [Growjo NET ERROR] {exc}")
            return []

        if not resp.ok:
            print(f"  [Growjo ERROR {resp.status_code}] {resp.text[:300]}")
            return []

        data      = resp.json().get("data", {})
        run_id    = data.get("id")
        dataset_id = data.get("defaultDatasetId")

        if not run_id:
            print("  [Growjo] Could not obtain run ID.")
            return []

        print(f"  [Growjo] Run {run_id} started — polling...")

        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(7)
            sr = self.session.get(
                f"{APIFY_BASE}/actor-runs/{run_id}",
                params=params,
                timeout=15,
            )
            if sr.ok:
                status = sr.json().get("data", {}).get("status")
                if status == "SUCCEEDED":
                    print(f"  [Growjo] Run SUCCEEDED.")
                    break
                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    print(f"  [Growjo] Run ended: {status}")
                    return []
        else:
            print("  [Growjo] Run timed out.")
            return []

        items_resp = self.session.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={**params, "format": "json", "limit": 200},
            timeout=20,
        )
        if items_resp.ok:
            raw = items_resp.json()
            return raw if isinstance(raw, list) else []
        return []

    @staticmethod
    def _normalise(item: dict) -> dict:
        """Map raw Growjo fields into a clean, engine-friendly schema."""
        def _safe_float(val) -> Optional[float]:
            try:
                return float(val) if val is not None else None
            except (ValueError, TypeError):
                return None

        def _safe_int(val) -> Optional[int]:
            try:
                return int(val) if val is not None else None
            except (ValueError, TypeError):
                return None

        growth_pct = _safe_float(item.get("employeeGrowthPercent"))

        # Categorise trajectory (same thresholds as ApifyCollector)
        if growth_pct is None:
            trajectory = "UNKNOWN"
        elif growth_pct >= 15.0:
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
            # Identity
            "company_name":        item.get("companyName", ""),
            "domain":              item.get("domain", ""),
            "website":             item.get("website", ""),
            "linkedin_url":        item.get("linkedinUrl", ""),
            "growjo_url":          item.get("growjoUrl", ""),
            # Location
            "city":                item.get("city", ""),
            "state":               item.get("state", ""),
            "country":             item.get("country", ""),
            # Headcount
            "current_employees":   _safe_int(item.get("currentEmployees")),
            "last_employees":      _safe_int(item.get("lastEmployees")),
            "employee_growth_pct": growth_pct,    # YoY %  <-- the key signal
            "trajectory":          trajectory,
            "job_openings":        _safe_int(item.get("jobOpenings")),
            # Financials
            "estimated_revenue":   _safe_int(item.get("estimatedRevenue")),
            "valuation":           _safe_int(item.get("valuation")),
            "valuation_as_of":     item.get("valuationAsOf", ""),
            "total_funding":       item.get("totalFunding", ""),
            "lead_investors":      item.get("leadInvestors", ""),
            # Firmographics
            "industry":            item.get("industry", ""),
            "keywords":            item.get("keywords", ""),
            "founded_year":        _safe_int(item.get("foundedYear")),
            "description":         (item.get("description") or "")[:300],
            # Intelligence
            "lead_score":          _safe_int(item.get("leadScore")),
            "competitors":         item.get("competitors", []),
            "growjo_id":           item.get("growjoId"),
            "updated_at":          item.get("updatedAt", ""),
            "scraped_at":          datetime.now(timezone.utc).isoformat(),
            # Source flag
            "source":              "growjo",
        }