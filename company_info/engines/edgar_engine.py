"""
edgar_engine.py — SEC EDGAR Open Filing & Capital Event Harvester
company_info / engines
"""

from __future__ import annotations
import urllib.parse
from typing import List, Dict, Any, Optional
from datetime import datetime

from company_info.engines.base_engine import BaseScraper
from company_info.config import SEC_EDGAR_HEADERS
from company_info.models.company import CompanyProfile
from company_info.models.funding import FundingEvent, FundingRoundType
from company_info.models.movement import StrategicMovementEvent, MovementCategory
from company_info.models.role_change import RoleChangeEvent, MovementType
from company_info.extractors.funding_parser import parse_funding_amount, classify_round_type
from company_info.extractors.name_extractor import extract_person_name_from_headline, clean_person_name
from company_info.extractors.role_extractor import extract_role_from_text


class EdgarFilingScraper(BaseScraper):
    """
    Open SEC EDGAR Filing Scraper.
    Harvests Form D (Private Offering/Funding), Form 8-K (Executive Changes & M&A),
    and 10-K/10-Q filings with 0 API keys.
    """

    def __init__(self, timeout: int = 10, rate_limit_delay: float = 0.2):
        super().__init__(timeout=timeout, rate_limit_delay=rate_limit_delay)

    def search_filings(self, company_name: str, forms: str = "8-K,D", limit: int = 15) -> List[Dict[str, Any]]:
        """Query SEC EDGAR full-text search index."""
        try:
            encoded_query = urllib.parse.quote(f'"{company_name}"')
            url = f"https://efts.sec.gov/LATEST/search-index?q={encoded_query}&forms={forms}"
            resp = self.fetch_get(url, custom_headers=SEC_EDGAR_HEADERS)
            if not resp or resp.status_code != 200:
                return []

            data = resp.json()
            raw_hits = data.get("hits", {}).get("hits", [])
            results = []

            for h in raw_hits[:limit]:
                src = h.get("_source", {})
                form_type = src.get("form", "")
                file_date = src.get("file_date", "")
                doc_title = src.get("display_names", [""])[0] if src.get("display_names") else ""
                file_id = src.get("file_num", "")
                adsh = src.get("adsh", "")
                entity_name = src.get("entity_name", "") or company_name

                doc_url = f"https://www.sec.gov/Archives/edgar/data/{adsh.replace('-', '')}/{adsh}.txt" if adsh else "https://www.sec.gov/edgar/searchedgar/companysearch"

                results.append({
                    "form": form_type,
                    "date": file_date,
                    "title": doc_title,
                    "adsh": adsh,
                    "url": doc_url,
                    "entity": entity_name,
                })

            return results
        except Exception:
            return []

    def harvest_events(self, profile: CompanyProfile) -> Dict[str, List[Any]]:
        """
        Harvests funding rounds and strategic events from SEC EDGAR filings for a company.
        """
        co_name = profile.company_name
        filings = self.search_filings(co_name, forms="8-K,D", limit=15)

        funding_events: List[FundingEvent] = []
        strategic_movements: List[StrategicMovementEvent] = []
        role_events: List[RoleChangeEvent] = []

        for f in filings:
            form = f.get("form")
            date_str = f.get("date")
            doc_url = f.get("url")

            # 1. Form D: Notice of Exempt Offering of Securities (Venture / Private Equity Funding)
            if form == "D":
                event = FundingEvent(
                    company_name=co_name,
                    round_type=FundingRoundType.PRIVATE_EQUITY,
                    amount_raw="SEC Form D Notice",
                    date_str=date_str,
                    announcement_title=f"SEC Form D Filing: Notice of Exempt Offering of Securities",
                    summary=f"Official SEC Form D notice filed for {co_name} indicating private securities offering / equity capital raise.",
                    source_url=doc_url,
                    source_name="SEC EDGAR Form D",
                    confidence_score=0.95,
                )
                funding_events.append(event)

            # 2. Form 8-K: Material Corporate Events
            elif form == "8-K":
                # Create strategic event
                strat_event = StrategicMovementEvent(
                    company_name=co_name,
                    category=MovementCategory.MERGER_ACQUISITION,
                    headline=f"SEC Form 8-K: Material Corporate Event",
                    summary=f"Material corporate disclosure filed with SEC regarding executive governance or strategic agreement for {co_name}.",
                    date_str=date_str,
                    source_url=doc_url,
                    source_name="SEC EDGAR 8-K",
                    confidence_score=0.90,
                )
                strategic_movements.append(strat_event)

        return {
            "funding": funding_events,
            "strategic": strategic_movements,
            "roles": role_events,
        }
