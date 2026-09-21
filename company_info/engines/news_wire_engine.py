"""
news_wire_engine.py — Nutraceutical Industry Wire & PR Harvester
company_info / engines
"""

from __future__ import annotations
import feedparser
import time
from typing import List, Dict, Any, Optional

from company_info.engines.base_engine import BaseScraper
from company_info.config import INDUSTRY_RSS_FEEDS
from company_info.models.company import CompanyProfile
from company_info.models.role_change import RoleChangeEvent, MovementType
from company_info.models.funding import FundingEvent
from company_info.models.movement import StrategicMovementEvent
from company_info.extractors.name_extractor import extract_person_name_from_headline
from company_info.extractors.role_extractor import extract_role_from_text
from company_info.extractors.funding_parser import parse_funding_amount, classify_round_type, extract_investors
from company_info.extractors.movement_classifier import classify_person_movement, classify_strategic_movement


class IndustryWireScraper(BaseScraper):
    """
    Harvester for industry-specific RSS feeds & wires with high-speed in-memory caching:
      - NutraIngredients
      - Nutraceuticals World
      - Natural Products Insider
      - PR Newswire Health
      - GlobeNewswire Healthcare
    """

    _cached_entries: List[Dict[str, Any]] = []
    _last_cache_time: float = 0.0
    _CACHE_TTL_SEC: float = 3600.0  # 1 hour cache

    def __init__(self, timeout: int = 5, rate_limit_delay: float = 0.1):
        super().__init__(timeout=timeout, rate_limit_delay=rate_limit_delay)

    def _ensure_feeds_loaded(self) -> List[Dict[str, Any]]:
        """Fetch and cache all RSS feeds in memory once."""
        now = time.time()
        if self._cached_entries and (now - self._last_cache_time) < self._CACHE_TTL_SEC:
            return self._cached_entries

        entries = []
        for feed_info in INDUSTRY_RSS_FEEDS:
            feed_name = feed_info["name"]
            feed_url = feed_info["url"]
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    entries.append({
                        "feed_name": feed_name,
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                    })
            except Exception:
                continue

        IndustryWireScraper._cached_entries = entries
        IndustryWireScraper._last_cache_time = now
        return entries

    def scan_industry_wires_for_company(self, profile: CompanyProfile) -> Dict[str, List[Any]]:
        """
        Scans cached industry RSS feeds in sub-millisecond memory for mentions of the target company.
        """
        co_name = profile.company_name
        co_clean = co_name.lower()
        core_clean = profile.core_brand_name.lower()

        role_events: List[RoleChangeEvent] = []
        funding_events: List[FundingEvent] = []
        movement_events: List[StrategicMovementEvent] = []

        entries = self._ensure_feeds_loaded()
        for item in entries:
            title = item["title"]
            summary = item["summary"]
            link = item["link"]
            pub_date = item["published"]
            feed_name = item["feed_name"]

            full_text = f"{title} {summary}"
            t_low = full_text.lower()

            # Check if company or core brand is mentioned
            if co_clean not in t_low and (len(core_clean) < 4 or core_clean not in t_low):
                continue

            # 1. Check for Funding
            if any(w in full_text.lower() for w in ["funding", "raised", "series a", "series b", "investment", "valuation"]):
                amt_raw, amt_usd = parse_funding_amount(full_text)
                round_t = classify_round_type(full_text)
                lead_invs, part_invs = extract_investors(full_text)

                event = FundingEvent(
                    company_name=co_name,
                    round_type=round_t,
                    amount_raw=amt_raw,
                    amount_usd=amt_usd,
                    lead_investors=lead_invs,
                    participating_investors=part_invs,
                    date_str=pub_date,
                    announcement_title=title,
                    summary=summary[:300],
                    source_url=link,
                    source_name=feed_name,
                    confidence_score=0.90,
                )
                funding_events.append(event)

            # 2. Check for Strategic Movements (M&A, Expansions, Product Launches)
            strat_cat = classify_strategic_movement(full_text)
            if strat_cat:
                strat_event = StrategicMovementEvent(
                    company_name=co_name,
                    category=strat_cat,
                    headline=title,
                    summary=summary[:300] if summary else title,
                    date_str=pub_date,
                    source_url=link,
                    source_name=feed_name,
                    confidence_score=0.88,
                )
                movement_events.append(strat_event)

            # 3. Check for Role Changes / Personnel Appointments
            person_name = extract_person_name_from_headline(title, co_name)
            if person_name:
                role = extract_role_from_text(full_text, person_name) or "Executive Leader"
                mov_type = classify_person_movement(full_text) or MovementType.JOINED

                r_event = RoleChangeEvent(
                    person_name=person_name,
                    company_name=co_name,
                    movement_type=mov_type,
                    role_title=role,
                    date_str=pub_date,
                    evidence_snippet=title,
                    source_url=link,
                    source_name=feed_name,
                    confidence_score=0.92,
                )
                role_events.append(r_event)

        return {
            "roles": role_events,
            "funding": funding_events,
            "movements": movement_events,
        }
