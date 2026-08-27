"""
owler_collector.py -- Owler company intelligence collector via Apify.

Actor: johnvc/owler-company-api
Returns: revenue, estimatedAnnualRevenue, employeeCount, totalFunding,
         totalAcquisitions, totalCompetitors, competitors list, founded,
         ownership, address, phone, industry, ticker/exchange.

Input field: companyUrls (list of Owler profile URLs)
"""

import os
import time
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
APIFY_BASE  = "https://api.apify.com/v2"
ACTOR_ID    = "johnvc~owler-company-api"

# How we build an Owler URL from a company name / domain
# e.g.  "Nordic Naturals"  -> nordicnaturals
#        "Garden of Life"  -> gardenoflife
def _company_to_owler_slug(name: str) -> str:
    return (
        name.lower()
        .replace(" & ", "")
        .replace(" ", "")
        .replace(",", "")
        .replace(".", "")
        .replace("-", "")
        .replace("'", "")
        .strip()
    )


class OwlerCollector:
    """
    Fetches comprehensive firmographic intelligence (revenue, funding,
    competitors, acquisitions) for nutraceutical targets via Owler / Apify.
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
        Run the Owler actor for a list of company names.
        Builds Owler URLs from names automatically.
        Returns a list of normalised company dicts.
        """
        if not self.is_configured():
            print("  [Owler WARN] APIFY_API_TOKEN not configured.")
            return []
        if not company_names:
            return []

        owler_urls = [
            f"https://www.owler.com/company/{_company_to_owler_slug(n)}"
            for n in company_names
        ]

        payload = {"companyUrls": owler_urls}
        raw_items = self._run_actor(payload, timeout_secs)
        return [self._normalise(item) for item in raw_items]

    def fetch_company(
        self,
        company_name: str,
        timeout_secs: int = 180,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single company.  Returns None on miss."""
        results = self.fetch_companies([company_name], timeout_secs)
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
            print(f"  [Owler NET ERROR] {exc}")
            return []

        if not resp.ok:
            print(f"  [Owler ERROR {resp.status_code}] {resp.text[:300]}")
            return []

        data       = resp.json().get("data", {})
        run_id     = data.get("id")
        dataset_id = data.get("defaultDatasetId")

        if not run_id:
            print("  [Owler] Could not obtain run ID.")
            return []

        print(f"  [Owler] Run {run_id} started -- polling...")

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
                    print(f"  [Owler] Run SUCCEEDED.")
                    break
                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    print(f"  [Owler] Run ended: {status}")
                    return []
        else:
            print("  [Owler] Run timed out.")
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
        """Map raw Owler fields into a clean, engine-friendly schema."""
        def _safe_int(val) -> Optional[int]:
            try:
                return int(val) if val is not None else None
            except (ValueError, TypeError):
                return None

        competitor_names = []
        for c in (item.get("competitors") or []):
            if isinstance(c, dict) and c.get("name"):
                competitor_names.append(c["name"])

        return {
            # Identity
            "company_name":              item.get("companyName", ""),
            "domain":                    item.get("domain", ""),
            "website":                   item.get("website", ""),
            "owler_url":                 item.get("profileUrl", ""),
            "description":               (item.get("description") or "")[:300],
            # Financials
            "revenue":                   _safe_int(item.get("revenue")),
            "estimated_annual_revenue":  item.get("estimatedAnnualRevenue", ""),
            "total_funding":             _safe_int(item.get("totalFunding")),
            # Headcount
            "employee_count":            _safe_int(item.get("employeeCount")),
            "estimated_employees":       item.get("estimatedEmployees", ""),
            # Corporate activity
            "total_acquisitions":        _safe_int(item.get("totalAcquisitions")),
            "total_competitors":         _safe_int(item.get("totalCompetitors")),
            "competitor_names":          competitor_names,
            # Firmographics
            "industry":                  item.get("industry", ""),
            "founded":                   _safe_int(item.get("founded")),
            "ownership":                 item.get("ownership", ""),
            "city":                      item.get("city", ""),
            "state":                     item.get("state", ""),
            "country":                   item.get("country", ""),
            "street_address":            item.get("streetAddress", ""),
            "phone":                     item.get("phoneNumber", ""),
            # Public market data (if available)
            "ticker":                    item.get("ticker", ""),
            "exchange":                  item.get("exchange", ""),
            # Metadata
            "owler_followers":           _safe_int(item.get("followers")),
            "fetched_at":                datetime.now(timezone.utc).isoformat(),
            "source":                    "owler",
        }