"""
serper_collector.py — Nutraceutical BD Engine: Serper Signal Collector

Covers:
  1. Trade Press Mentions (site-restricted to nutra industry publications)
  2. Executive Movements — structured events: name, title, date, function, direction (ARRIVAL/DEPARTURE), replacement flag
  3. New Facility / Plant Expansions
  4. Funding & M&A Rounds
  5. Regulatory Press (FDA Warning Letters, Recall News)
  6. NDI Filings (New Dietary Ingredient notifications — product expansion signal)

Serper API: https://serper.dev (POST /news + /search)

IMPORTANT: All queries are restricted to recent results only (default: last 6 months).
Old news (2014–2022 etc.) is NOT actionable for BD outreach.
No category scores 0 by default — only real signals increment the score.
"""

import os
import re
import time
import requests
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_BASE_URL = "https://google.serper.dev"

# Serper tbs (time-based search) values:
#   qdr:m  = last 30 days
#   qdr:m3 = last 3 months (90 days)
#   qdr:m6 = last 6 months (180 days) <- standard for BD pipeline
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
    "prnewswire.com",  # Keep for M&A, exclude for others
}

# -------------------------------------------------------------------
# NUTRA TRADE PRESS DOMAINS
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
# -------------------------------------------------------------------
SIGNAL_QUERY_TEMPLATES = {

    "trade_press": [
        '{company} site:nutraingredients-usa.com',
        '{company} site:naturalproductsinsider.com',
        '{company} site:nutraceuticalsworld.com',
        '{company} supplement nutrition',
    ],

    "exec_appointment": [
        '"{company}" "appointed" OR "joins" OR "named" OR "hires" VP OR Director OR "Chief" OR SVP supplement nutrition',
        '"{company}" "steps down" OR "leaves" OR "departs" OR "resigned" OR "transition" executive leadership',
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

    "ndi_filing": [
        '"{company}" "new dietary ingredient" OR "NDI" OR "GRAS" filing notification',
        '"{company}" "NDI notification" OR "new ingredient" supplement fda',
    ],
}

# Classify a mention type from article title + snippet keywords
MENTION_TYPE_KEYWORDS = {
    "Executive Appointment": ["appoint", "joins", "named", "hire", "coo", "ceo", "vp", "chief", "president", "director", "svp"],
    "Executive Departure":   ["steps down", "leaves", "departed", "resigned", "transition", "successor", "interim"],
    "Facility Expansion":    ["facility", "plant", "expansion", "manufacturing", "capacity", "opens", "launches", "sq ft"],
    "Funding / M&A":         ["raises", "funding", "acquired", "investment", "series", "private equity", "merger", "acquisition"],
    "Regulatory Alert":      ["fda", "warning", "recall", "enforcement", "cgmp", "violation", "483", "compliance"],
    "Product Launch":        ["launches", "new product", "new formula", "introduces", "unveils", "label", "sku"],
    "NDI Filing":            ["ndi", "new dietary ingredient", "gras", "new ingredient filing", "ndi notification"],
    "Trade Press":           ["supplement", "nutraceutical", "nutrition", "ingredient", "botanical", "probiotic", "vitamin"],
}

# -------------------------------------------------------------------
# EXEC FUNCTION CLASSIFICATION
# Maps role keywords -> BD-relevant function buckets (spec-aligned)
# -------------------------------------------------------------------
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

# Seniority words that indicate C-suite/VP level (spec: +15 pts trigger)
SENIOR_TITLE_KEYWORDS = [
    "ceo", "coo", "cfo", "cto", "cmo", "cso", "chief", "president",
    "svp", "evp", "vp ", "vice president", "senior vp", "managing director",
    "general manager", "executive director",
]

# Keywords strongly suggesting a departure (not an arrival)
DEPARTURE_KEYWORDS = [
    "steps down", "stepping down", "leaves", "left", "departed", "departure",
    "resigned", "resignation", "transition", "successor", "interim", "retirement",
    "retiring", "exited", "no longer", "former"
]

# Keywords strongly suggesting a replacement has been named
REPLACEMENT_KEYWORDS = [
    "successor", "replaces", "replace", "taking over", "filling the role",
    "effective immediately", "appointed as new", "named replacement"
]


class SerperCollector:
    """
    Pulls structured market intelligence signals for nutraceutical companies
    using Serper's Google Search and News APIs.

    Exec movements now return fully structured events:
      - executive_name, title, function, direction (ARRIVAL/DEPARTURE)
      - is_senior_level, replacement_detected, date, source_url
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
    ) -> List[dict]:
        """
        POST to Serper /news or /search endpoint with recency filtering.
        """
        url = f"{SERPER_BASE_URL}/{endpoint}"
        payload = {"q": query, "num": num, "tbs": recency}

        try:
            resp = self.session.post(url, json=payload, timeout=15)
            if not resp.ok:
                return []

            data = resp.json()
            items = data.get("news", []) or data.get("organic", [])

            if filter_noise:
                items = [
                    item for item in items
                    if not any(
                        noise in (item.get("link", "") + item.get("source", "")).lower()
                        for noise in NOISE_DOMAINS
                    )
                ]

            return items

        except Exception:
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
            "title":        item.get("title", ""),
            "url":          item.get("link", "") or item.get("url", ""),
            "source":       item.get("source", "") or item.get("domain", ""),
            "date":         item.get("date", ""),
            "snippet":      item.get("snippet", "")[:200],
            "mention_type": mention_type,
        }

    # ------------------------------------------------------------------
    # EXEC EVENT CLASSIFIER (Gap 1)
    # ------------------------------------------------------------------

    @staticmethod
    def classify_exec_direction(title: str, snippet: str) -> str:
        """Determine if an exec signal is an ARRIVAL or DEPARTURE."""
        combined = (title + " " + snippet).lower()
        if any(kw in combined for kw in DEPARTURE_KEYWORDS):
            return "DEPARTURE"
        return "ARRIVAL"

    @staticmethod
    def classify_exec_function(title: str, snippet: str) -> str:
        """Map a role description to a BD-relevant function bucket."""
        combined = (title + " " + snippet).lower()
        for function_name, keywords in EXEC_FUNCTION_MAP.items():
            if any(kw in combined for kw in keywords):
                return function_name
        return "General Management"

    @staticmethod
    def is_senior_level(title: str, snippet: str) -> bool:
        """Returns True if the title/snippet suggests C-suite or VP-level."""
        combined = (title + " " + snippet).lower()
        return any(kw in combined for kw in SENIOR_TITLE_KEYWORDS)

    @staticmethod
    def detect_replacement(title: str, snippet: str) -> bool:
        """Returns True if article suggests a named replacement was announced."""
        combined = (title + " " + snippet).lower()
        return any(kw in combined for kw in REPLACEMENT_KEYWORDS)

    @staticmethod
    def extract_exec_name_title(title: str, snippet: str) -> tuple:
        """
        Heuristically extract the executive name and title from article text.
        Returns (name, title) or (None, None) if not found.
        """
        combined = title + " " + snippet

        # Common patterns: "John Smith joins as VP of Sales" / "Dr. Sarah Lee appointed as CEO"
        name_patterns = [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+(?:-[A-Z][a-z]+)?)\b(?=\s+(?:joins|appointed|named|leaves|steps|resigned|departed|hired|promoted))',
            r'(?:appointed|named|hired|joins|welcomes)\s+([A-Z][a-z]+ [A-Z][a-z]+)',
        ]
        title_patterns = [
            r'\b(?:as|its new|new)\s+((?:Chief|VP|Vice President|SVP|EVP|President|Director|Head|Manager)[^,\.]{0,50})',
            r'\b((?:Chief|VP|SVP|EVP|President|Director|Head)[^,\.]{0,40})\b',
        ]

        exec_name = None
        exec_title = None

        for pat in name_patterns:
            m = re.search(pat, combined)
            if m:
                exec_name = m.group(1).strip()
                break

        for pat in title_patterns:
            m = re.search(pat, combined, re.IGNORECASE)
            if m:
                exec_title = m.group(1).strip()
                break

        return exec_name, exec_title

    def _build_exec_event(self, item: dict) -> dict:
        """Build a structured exec event from a Serper result."""
        title   = item.get("title", "")
        snippet = item.get("snippet", "")
        date    = item.get("date", "")
        url     = item.get("link", "") or item.get("url", "")
        source  = item.get("source", "")

        exec_name, exec_title = self.extract_exec_name_title(title, snippet)
        direction = self.classify_exec_direction(title, snippet)
        function  = self.classify_exec_function(title, snippet)
        senior    = self.is_senior_level(title, snippet)
        replaced  = self.detect_replacement(title, snippet)

        return {
            "event_type":            "EXECUTIVE_MOVEMENT",
            "direction":             direction,            # ARRIVAL | DEPARTURE
            "function":              function,             # Sales | QA/RA | Operations | R&D/Science | etc.
            "is_senior_level":       senior,               # True if C-suite / VP
            "replacement_detected":  replaced,             # True if article names a successor
            "executive_name":        exec_name or "Not extracted",
            "executive_title":       exec_title or "Not extracted",
            "date":                  date,
            "headline":              title,
            "snippet":               snippet[:200],
            "source":                source,
            "source_url":            url,
        }

    # ------------------------------------------------------------------
    # INDIVIDUAL SIGNAL FETCHERS
    # ------------------------------------------------------------------

    def get_trade_press(self, company_name: str, num: int = 5) -> List[dict]:
        """Pull industry trade press mentions from nutra publications."""
        results = []
        for site in NUTRA_TRADE_SITES[:3]:
            items = self._search(f'"{company_name}" site:{site}', endpoint="search", num=num)
            for item in items:
                mention_type = self.classify_mention(item.get("title", ""), item.get("snippet", ""))
                results.append(self.format_result(item, mention_type))
            if results:
                break
        return results

    def get_executive_signals(self, company_name: str, num: int = 8) -> List[dict]:
        """
        Pull structured executive movement events (ARRIVAL / DEPARTURE).
        Each event includes: name, title, function, direction, seniority, replacement flag.
        """
        raw_items = []
        for template in SIGNAL_QUERY_TEMPLATES["exec_appointment"]:
            query = template.format(company=company_name)
            items = self._search(query, endpoint="news", num=num)
            raw_items.extend(items)
            if raw_items:
                break

        # Deduplicate by URL
        seen_urls = set()
        structured_events = []
        for item in raw_items:
            url = item.get("link", "")
            if url not in seen_urls:
                seen_urls.add(url)
                structured_events.append(self._build_exec_event(item))

        return structured_events

    def get_facility_expansion(self, company_name: str, num: int = 5) -> List[dict]:
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

    def get_funding_ma(self, company_name: str, num: int = 5) -> List[dict]:
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

    def get_regulatory_press(self, company_name: str, num: int = 5) -> List[dict]:
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

    def get_ndi_signals(self, company_name: str, num: int = 5) -> List[dict]:
        """
        Pull New Dietary Ingredient (NDI) filing signals — product expansion proxy.
        NDI filings precede product launches and signal R&D/Regulatory hiring intent.
        """
        results = []
        for template in SIGNAL_QUERY_TEMPLATES["ndi_filing"]:
            query = template.format(company=company_name)
            items = self._search(query, endpoint="news", num=num)
            for item in items:
                results.append(self.format_result(item, "NDI Filing"))
            if results:
                break
        return results

    # ------------------------------------------------------------------
    # FULL COMPANY INTELLIGENCE PULL
    # ------------------------------------------------------------------

    def analyze_company(self, company_name: str, delay: float = 0.5) -> dict:
        """
        Run all signal searches for a company.
        Returns a structured dict of all market intelligence signals.

        Exec events are fully structured with direction, function, seniority,
        and replacement detection — not just a count.
        """
        print(f"\n[Serper] Fetching market signals for: {company_name}...")

        trade_press  = self.get_trade_press(company_name)
        time.sleep(delay)
        exec_signals = self.get_executive_signals(company_name)
        time.sleep(delay)
        facility     = self.get_facility_expansion(company_name)
        time.sleep(delay)
        funding      = self.get_funding_ma(company_name)
        time.sleep(delay)
        regulatory   = self.get_regulatory_press(company_name)
        time.sleep(delay)
        ndi_signals  = self.get_ndi_signals(company_name)

        # Derived exec summaries for scoring
        arrivals   = [e for e in exec_signals if e.get("direction") == "ARRIVAL"]
        departures = [e for e in exec_signals if e.get("direction") == "DEPARTURE"]
        senior_moves = [e for e in exec_signals if e.get("is_senior_level")]
        unresolved_departures = [
            e for e in departures if not e.get("replacement_detected")
        ]

        total_signals = (
            len(trade_press) + len(exec_signals) + len(facility)
            + len(funding) + len(regulatory) + len(ndi_signals)
        )
        print(f"  [OK] {total_signals} signals found — Exec: {len(exec_signals)} ({len(arrivals)} arrivals, {len(departures)} departures), Facility: {len(facility)}, Funding/M&A: {len(funding)}, NDI: {len(ndi_signals)}")

        return {
            "company_name":         company_name,
            "analysis_timestamp":   datetime.now(timezone.utc).isoformat(),
            "signal_summary": {
                "trade_press_count":            len(trade_press),
                "exec_signals_count":           len(exec_signals),
                "exec_arrivals":                len(arrivals),
                "exec_departures":              len(departures),
                "exec_senior_level_moves":      len(senior_moves),
                "exec_unresolved_departures":   len(unresolved_departures),
                "facility_count":               len(facility),
                "funding_ma_count":             len(funding),
                "regulatory_count":             len(regulatory),
                "ndi_filing_count":             len(ndi_signals),
                "total_signals":                total_signals,
            },
            "signals": {
                "trade_press":          trade_press,
                "exec_appointments":    exec_signals,   # structured events
                "facility_expansion":   facility,
                "funding_ma":           funding,
                "regulatory_press":     regulatory,
                "ndi_filings":          ndi_signals,
            },
        }
