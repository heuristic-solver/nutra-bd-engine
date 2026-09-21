"""
linkedin_public_engine.py — Zero-Auth Public LinkedIn Signal Harvester
company_info / engines
"""

from __future__ import annotations
import re
import urllib.parse
from typing import List, Optional

from company_info.engines.search_engine import MultiEngineSearchScraper
from company_info.models.company import CompanyProfile
from company_info.models.role_change import RoleChangeEvent, MovementType
from company_info.extractors.name_extractor import clean_person_name
from company_info.extractors.role_extractor import clean_role_title, extract_role_from_text
from company_info.extractors.movement_classifier import classify_person_movement


class LinkedInPublicScraper:
    """
    Harvester for public LinkedIn role change, arrival, and departure signals.
    Requires 0 credentials and 0 third-party APIs.
    """

    def __init__(self, search_scraper: Optional[MultiEngineSearchScraper] = None):
        self.search_scraper = search_scraper or MultiEngineSearchScraper()

    def harvest_company_signals(self, profile: CompanyProfile) -> List[RoleChangeEvent]:
        """
        Executes public LinkedIn dorks and parses people who joined, were promoted, or departed.
        """
        co_name = profile.company_name
        events: List[RoleChangeEvent] = []
        seen_names = set()

        # Single high-yield LinkedIn & trade press query
        q_unified = f'"{profile.core_brand_name}" ("appointed" OR "joined" OR "named" OR "promoted" OR "resigned" OR "steps down" OR "leaves")'
        try:
            raw_results = self.search_scraper.search_bing_news(q_unified, limit=6)
            for r in raw_results:
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                link = r.get("link", "")

                # 1. Parse Person Name from LinkedIn Title format: "FirstName LastName - Role - Company | LinkedIn"
                name_cand = None
                role_cand = None

                # Format: Name - Role - Company | LinkedIn
                parts = re.split(r'[-–|]', title)
                if len(parts) >= 2:
                    name_part = parts[0].strip()
                    cleaned_name = clean_person_name(name_part, co_name)
                    if cleaned_name and len(cleaned_name.split()) >= 2:
                        name_cand = cleaned_name
                        role_cand = clean_role_title(parts[1].strip(), cleaned_name)

                # Fallback: Check if snippet has context
                if not role_cand:
                    role_cand = extract_role_from_text(f"{title} {snippet}", name_cand)

                if not name_cand or not role_cand:
                    continue

                # Deduplicate person
                if name_cand.lower() in seen_names:
                    continue
                seen_names.add(name_cand.lower())

                # Determine Movement Type from context
                detected_mov = classify_person_movement(f"{title} {snippet}") or MovementType.JOINED

                event = RoleChangeEvent(
                    person_name=name_cand,
                    company_name=co_name,
                    movement_type=detected_mov,
                    role_title=role_cand,
                    evidence_snippet=snippet[:250] if snippet else title,
                    source_url=link,
                    source_name="LinkedIn / Trade Signal",
                    confidence_score=0.85 if detected_mov == MovementType.JOINED else 0.80,
                )
                events.append(event)
        except Exception:
            pass

        return events
