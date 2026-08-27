"""
serper_collector.py — Nutraceutical BD Engine: Serper Signal Collector

Covers:
  1. Trade Press Mentions (site-restricted to nutra industry publications)
  2. Executive Appointments & Leadership Turnover
  3. New Facility / Plant Expansions
  4. Funding & M&A Rounds
  5. Regulatory Press (FDA Warning Letters, Recall News)

Serper API: https://serper.dev (POST /news + /search)

IMPORTANT: All queries are restricted to recent results only (default: last 90 days).
Old news (2014–2022 etc.) is NOT actionable for BD outreach.
"""

import os
import time
import requests
from datetime import datetime, timedelta
from datetime import datetime, timezone
from typing import Optional

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_BASE_URL = "https://google.serper.dev"

# Serper tbs (time-based search) values:
#   qdr:w  = last 7 days
#   qdr:m  = last 30 days
#   qdr:m3 = last 3 months (90 days)
#   qdr:m6 = last 6 months (180 days) ← standard for BD pipeline
#   qdr:y  = last 12 months
DEFAULT_RECENCY = "qdr:m6"   # Last 6 months

# Domains that produce low-quality noise (market research reports, not real company news)
NOISE_DOMAINS = {
    "futuremarketinsights.com",
    "marketresearchfuture.com",
    "factmr.com",
    "grandviewresearch.com",
    "mordorintelligence.com",
    "alliedmarketresearch.com",
    "transparencymarketresearch.com",
    "globenewswire.com",
    "prnewswire.com",  # Keep for M&A, remove for others
}

# -------------------------------------------------------------------
# NUTRA TRADE PRESS DOMAINS
# These publications cover supplement/nutraceutical industry exclusively
# Far higher hit rate than generic Google News for small private companies
# -------------------------------------------------------------------
NUTRA_TRADE_SITES = [
    "nutraingredients-usa.com",
    "naturalproductsinsider.com",
    "nutraceuticalsworld.com",
    "nutritioninsight.com",
    "foodnavigator-usa.com",
    "supplysideshow.com",
    "pilladvised.com",
]

# -------------------------------------------------------------------
# SIGNAL QUERY TEMPLATES
# Each template generates a targeted Google search query
# {company} is replaced with the actual company name
# -------------------------------------------------------------------
SIGNAL_QUERY_TEMPLATES = {

    "trade_press": [
        '{company} site:nutraingredients-usa.com',
        '{company} site:naturalproductsinsider.com',
        '{company} site:nutraceuticalsworld.com',
        '{company} supplement nutrition',
    ],

    "exec_appointment": [
        '"{company}" "appointed" OR "joins" OR "named" VP OR Director OR Chief supplement',
        '"{company}" executive leadership hire 2025 OR 2026',
    ],

    "facility_expansion": [
        '"{company}" "new facility" OR "expansion" OR "manufacturing plant" supplement',
        '"{company}" "opens" OR "launches" OR "capacity" manufacturing nutraceutical',
    ],

    "funding_ma": [
        '"{company}" "raises" OR "funding" OR "acquired" OR "investment" supplement nutrition',
        '"{company}" "series A" OR "series B" OR "private equity" nutraceutical',
    ],

    "regulatory_press": [
        '"{company}" "FDA warning" OR "FDA recall" OR "cGMP" OR "enforcement" supplement',
        '"{company}" site:nutraingredients-usa.com FDA compliance',
    ],
}

# Classify a mention type from article title + snippet keywords
MENTION_TYPE_KEYWORDS = {
    "Executive Appointment": ["appoint", "joins", "named", "hire", "coo", "ceo", "vp", "chief", "president", "director"],
    "Facility Expansion": ["facility", "plant", "expansion", "manufacturing", "capacity", "opens", "launches", "sq ft"],
    "Funding / M&A": ["raises", "funding", "acquired", "investment", "series", "private equity", "merger", "acquisition"],
    "Regulatory Alert": ["fda", "warning", "recall", "enforcement", "cgmp", "violation", "483", "compliance"],
    "Product Launch": ["launches", "new product", "new formula", "introduces", "unveils", "label", "sku"],
    "Trade Press": ["supplement", "nutraceutical", "nutrition", "ingredient", "botanical", "probiotic", "vitamin"],
}


class SerperCollector:
    """
    Pulls market intelligence signals for nutraceutical companies
    using Serper's Google Search and News APIs.
    """

    def __init__(self, api_key: str = SERPER_API_KEY):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        })

    # ------------------------------------------------------------------
    # CORE API CALL
    # ------------------------------------------------------------------

    def _search(
        self,
        query: str,
        endpoint: str = "news",
        num: int = 10,
        recency: str = DEFAULT_RECENCY,
        filter_noise: bool = True,
    ) -> list[dict]:
        """
        POST to Serper /news or /search endpoint with recency filtering.

        Args:
            query:        Google search query string
            endpoint:     'news' or 'search' (organic results)
            num:          Max number of results to request
            recency:      Serper tbs value — default is last 90 days (qdr:m3)
            filter_noise: Remove results from known low-quality market report domains
        """
        url = f"{SERPER_BASE_URL}/{endpoint}"
        payload = {"q": query, "num": num, "tbs": recency}

        try:
            resp = self.session.post(url, json=payload, timeout=15)
            if not resp.ok:
                print(f"  [Serper {resp.status_code}] Query: {query[:60]}")
                return []

            data = resp.json()
            items = data.get("news", []) or data.get("organic", [])

            # Strip out market research report noise
            if filter_noise:
                items = [
                    item for item in items
                    if not any(
                        noise in (item.get("link", "") + item.get("source", "")).lower()
                        for noise in NOISE_DOMAINS
                    )
                ]

            return items

        except Exception as e:
            print(f"  [Serper ERROR] {e}")
            return []

    # ------------------------------------------------------------------
    # SIGNAL TYPE CLASSIFIERS
    # ------------------------------------------------------------------

    @staticmethod
    def classify_mention(title: str, snippet: str = "") -> str:
        """Classify a news/article mention into a signal type."""
        combined = (title + " " + snippet).lower()
        for mention_type, keywords in MENTION_TYPE_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                return mention_type
        return "General News"

    @staticmethod
    def format_result(item: dict, mention_type: str) -> dict:
        """Normalize a Serper result item into a clean signal dict."""
        return {
            "title": item.get("title", ""),
            "url": item.get("link", "") or item.get("url", ""),
            "source": item.get("source", "") or item.get("domain", ""),
            "date": item.get("date", ""),
            "snippet": item.get("snippet", "")[:200],
            "mention_type": mention_type,
        }

    # ------------------------------------------------------------------
    # INDIVIDUAL SIGNAL FETCHERS
    # ------------------------------------------------------------------

    def get_trade_press(self, company_name: str, num: int = 5) -> list[dict]:
        """Pull industry trade press mentions from nutra publications."""
        results = []
        for site in NUTRA_TRADE_SITES[:3]:
            items = self._search(f'"{company_name}" site:{site}', endpoint="search", num=num)
            for item in items:
                mention_type = self.classify_mention(item.get("title", ""), item.get("snippet", ""))
                results.append(self.format_result(item, mention_type))
            if results:
                break  # Stop after first site that returns results
        return results

    def get_executive_signals(self, company_name: str, num: int = 5) -> list[dict]:
        """Pull executive appointment and leadership change signals."""
        results = []
        for template in SIGNAL_QUERY_TEMPLATES["exec_appointment"]:
            query = template.format(company=company_name)
            items = self._search(query, endpoint="news", num=num)
            for item in items:
                results.append(self.format_result(item, "Executive Appointment"))
            if results:
                break
        return results

    def get_facility_expansion(self, company_name: str, num: int = 5) -> list[dict]:
        """Pull facility expansion, new plant, and manufacturing growth signals."""
        results = []
        for template in SIGNAL_QUERY_TEMPLATES["facility_expansion"]:
            query = template.format(company=company_name)
            items = self._search(query, endpoint="news", num=num)
            for item in items:
                results.append(self.format_result(item, "Facility Expansion"))
            if results:
                break
        return results

    def get_funding_ma(self, company_name: str, num: int = 5) -> list[dict]:
        """Pull funding rounds and M&A activity signals."""
        results = []
        for template in SIGNAL_QUERY_TEMPLATES["funding_ma"]:
            query = template.format(company=company_name)
            items = self._search(query, endpoint="news", num=num)
            for item in items:
                results.append(self.format_result(item, "Funding / M&A"))
            if results:
                break
        return results

    def get_regulatory_press(self, company_name: str, num: int = 5) -> list[dict]:
        """Pull FDA regulatory and compliance-related press signals."""
        results = []
        for template in SIGNAL_QUERY_TEMPLATES["regulatory_press"]:
            query = template.format(company=company_name)
            items = self._search(query, endpoint="news", num=num)
            for item in items:
                results.append(self.format_result(item, "Regulatory Alert"))
            if results:
                break
        return results

    # ------------------------------------------------------------------
    # FULL COMPANY INTELLIGENCE PULL
    # ------------------------------------------------------------------

    def analyze_company(self, company_name: str, delay: float = 0.5) -> dict:
        """
        Run all 5 Serper signal searches for a company.
        Returns a structured dict of all market intelligence signals.
        """
        print(f"\n[Serper] Fetching market signals for: {company_name}...")

        trade_press     = self.get_trade_press(company_name)
        time.sleep(delay)
        exec_signals    = self.get_executive_signals(company_name)
        time.sleep(delay)
        facility        = self.get_facility_expansion(company_name)
        time.sleep(delay)
        funding         = self.get_funding_ma(company_name)
        time.sleep(delay)
        regulatory      = self.get_regulatory_press(company_name)

        total_signals = len(trade_press) + len(exec_signals) + len(facility) + len(funding) + len(regulatory)
        print(f"  [OK] {total_signals} signals found across 5 signal types.")

        return {
            "company_name": company_name,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "signal_summary": {
                "trade_press_count":    len(trade_press),
                "exec_signals_count":   len(exec_signals),
                "facility_count":       len(facility),
                "funding_ma_count":     len(funding),
                "regulatory_count":     len(regulatory),
                "total_signals":        total_signals,
            },
            "signals": {
                "trade_press":       trade_press,
                "exec_appointments": exec_signals,
                "facility_expansion": facility,
                "funding_ma":        funding,
                "regulatory_press":  regulatory,
            },
        }
