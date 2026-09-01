"""
crunchbase_collector.py — Nutraceutical BD Engine: Apify Crunchbase Funding & Investment Collector

Integrates with Apify Crunchbase Scrapers:
  - Primary: `saswave~crunchbase-company-organization-scraper`
  - Fallback: `pratikdani~crunchbase-companies-bulk-scraper-no-cookies`

Pulls verified funding rounds, funding types, round amounts, announcement dates,
lead investors, acquisitions list, founder identifiers, and operating status.

Cost: ~$1.50 per 1,000 profiles (Pay-as-you-go via existing Apify account, no enterprise API required)
"""

import os
import re
import time
import requests
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
APIFY_BASE_URL  = "https://api.apify.com/v2"
ACTOR_PRIMARY   = "saswave~crunchbase-company-organization-scraper"
ACTOR_FALLBACK  = "pratikdani~crunchbase-companies-bulk-scraper-no-cookies"


class CrunchbaseCollector:
    """
    Collects structured investment, funding rounds, lead investors,
    and acquisition history using Apify's Crunchbase Scraper actors.
    """

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or APIFY_API_TOKEN or os.environ.get("APIFY_API_TOKEN", "")
        self.session = requests.Session()

    def is_configured(self) -> bool:
        """Check if an Apify token is available."""
        return bool(self.api_token and len(self.api_token) > 5)

    @staticmethod
    def slugify(name: str) -> str:
        """Converts company name to a Crunchbase URL slug."""
        clean = re.sub(r"[^\w\s-]", "", name).strip().lower()
        return re.sub(r"[-\s]+", "-", clean)

    def fetch_companies_funding_batch(
        self,
        companies: List[Dict[str, str]],
        timeout_secs: int = 180,
    ) -> List[Dict[str, Any]]:
        """
        Scrapes Crunchbase funding, rounds, and investors in a batch.

        Args:
            companies: List of dicts with 'name', optional 'crunchbase_url', optional 'domain'
            timeout_secs: Maximum wait time for the Apify cloud run
        """
        if not self.is_configured():
            print("  [Crunchbase WARN] APIFY_API_TOKEN not configured.")
            return []

        if not companies:
            return []

        # Prepare target URLs
        urls = []
        name_map = {}
        for c in companies:
            cb_url = c.get("crunchbase_url")
            if not cb_url:
                slug = self.slugify(c["name"])
                cb_url = f"https://www.crunchbase.com/organization/{slug}"
            urls.append(cb_url)
            name_map[cb_url.lower()] = c["name"]
            slug_key = cb_url.rstrip("/").split("/")[-1].lower()
            name_map[slug_key] = c["name"]

        print(f"\n[Crunchbase] Starting Apify run for {len(urls)} companies...")

        start_url = f"{APIFY_BASE_URL}/acts/{ACTOR_PRIMARY}/runs"
        params = {"token": self.api_token}
        payload = {"urls": urls}

        try:
            resp = self.session.post(start_url, params=params, json=payload, timeout=20)
            if not resp.ok:
                print(f"  [Crunchbase ERROR] Failed to start Actor: {resp.status_code} - {resp.text[:120]}")
                return []

            run_data = resp.json().get("data", {})
            run_id = run_data.get("id")
            dataset_id = run_data.get("defaultDatasetId")
            print(f"  [Crunchbase] Run started (ID: {run_id}). Polling...")

            # Poll for completion
            poll_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
            elapsed = 0
            poll_interval = 5

            while elapsed < timeout_secs:
                time.sleep(poll_interval)
                elapsed += poll_interval

                poll_resp = self.session.get(poll_url, params={"token": self.api_token}, timeout=15)
                if not poll_resp.ok:
                    continue

                status = poll_resp.json().get("data", {}).get("status")
                if status == "SUCCEEDED":
                    print(f"  [Crunchbase] Run SUCCEEDED in {elapsed}s.")
                    break
                elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    print(f"  [Crunchbase] Run ended with status: {status}")
                    return []
            else:
                print(f"  [Crunchbase WARN] Timed out waiting for Actor run ({timeout_secs}s).")
                return []

            # Fetch dataset items
            items_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items"
            items_resp = self.session.get(items_url, params={"token": self.api_token, "limit": 100}, timeout=20)
            if not items_resp.ok:
                return []

            raw_items = items_resp.json()
            results = []
            for item in raw_items:
                results.append(self._normalize_item(item, name_map))

            print(f"  [Crunchbase OK] Retrieved funding records for {len(results)} companies.")
            return results

        except Exception as e:
            print(f"  [Crunchbase ERROR] Exception: {e}")
            return []

    def _normalize_item(self, item: Dict[str, Any], name_map: Dict[str, str]) -> Dict[str, Any]:
        """Normalizes raw Crunchbase actor JSON into structured BD fields."""
        url = item.get("url") or item.get("crunchbase_url") or ""
        permalink = item.get("permalink", "")
        slug = (permalink or (url.rstrip("/").split("/")[-1] if url else "")).lower()
        comp_name = name_map.get(url.lower()) or name_map.get(slug) or item.get("title") or item.get("value") or item.get("name") or "Unknown"

        # Funding / Financials
        funding_info = item.get("funding") or item.get("financials") or {}
        total_funding_raw = (
            item.get("total_funding_amount")
            or item.get("totalFunding")
            or funding_info.get("total_funding_usd")
            or funding_info.get("totalFunding")
        )

        rounds_list = item.get("funding_rounds_list") or []
        last_round = rounds_list[0] if rounds_list else (item.get("last_funding_round") or item.get("latest_funding_round") or {})

        if isinstance(last_round, str):
            round_type = last_round
            round_date = ""
            round_amount = ""
            investors = []
        else:
            round_type   = last_round.get("funding_type") or last_round.get("investment_type") or last_round.get("type") or ""
            round_date   = last_round.get("announced_on") or last_round.get("date") or ""
            round_amount = last_round.get("money_raised") or last_round.get("amount") or ""
            investors    = last_round.get("investors") or last_round.get("lead_investors") or []

        if isinstance(investors, list):
            investors_str = ", ".join(
                inv.get("name", str(inv)) if isinstance(inv, dict) else str(inv)
                for inv in investors[:4]
            )
        else:
            investors_str = str(investors)

        # Acquisitions
        acquisitions_list = item.get("acquisitions_list") or []
        num_acquisitions = len(acquisitions_list) or int(item.get("num_acquisitions") or 0)
        acquisitions_summary = ", ".join(
            a.get("acquiree_identifier", {}).get("value", a.get("name", "Unknown"))
            for a in acquisitions_list[:3]
        )

        num_rounds = len(rounds_list) or int(item.get("num_funding_rounds") or 0)
        operating_status = item.get("overview_fields_extended", {}).get("operating_status") or item.get("operating_status", "Active")

        return {
            "company_name":             comp_name,
            "crunchbase_url":           url or f"https://www.crunchbase.com/organization/{slug}",
            "total_funding":            self._format_money(total_funding_raw),
            "last_funding_round_type":  round_type or "Private / Self-Funded",
            "last_funding_date":        round_date or "N/A",
            "last_funding_amount":      self._format_money(round_amount),
            "lead_investors":           investors_str or "N/A",
            "num_funding_rounds":       num_rounds,
            "num_acquisitions":         num_acquisitions,
            "recent_acquisitions":      acquisitions_summary or "None",
            "operating_status":         operating_status.capitalize() if operating_status else "Active",
            "ipo_status":               item.get("ipo_status") or ("Public" if item.get("stock_symbol") else "Private"),
            "scraped_at":               datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _format_money(val: Any) -> str:
        """Formats numbers into standard currency string."""
        if not val or str(val) in ("0", "$0", "None", "null"):
            return "N/A"
        if isinstance(val, str) and ("$" in val or "€" in val or "£" in val or "M" in val or "B" in val):
            return val
        try:
            num = float(val)
            if num >= 1_000_000_000:
                return f"${num / 1_000_000_000:.2f}B"
            elif num >= 1_000_000:
                return f"${num / 1_000_000:.1f}M"
            elif num >= 1_000:
                return f"${num / 1_000:.0f}K"
            elif num > 0:
                return f"${num:,.0f}"
            return "N/A"
        except (ValueError, TypeError):
            return str(val)
