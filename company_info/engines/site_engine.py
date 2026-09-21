"""
site_engine.py — Direct Corporate Website Crawler & Leadership Harvester
company_info / engines
"""

from __future__ import annotations
import re
import urllib.parse
from typing import List, Dict, Any, Optional, Set
from bs4 import BeautifulSoup

from company_info.engines.base_engine import BaseScraper
from company_info.models.company import CompanyProfile
from company_info.models.role_change import RoleChangeEvent, MovementType
from company_info.models.movement import StrategicMovementEvent, MovementCategory
from company_info.extractors.name_extractor import clean_person_name, extract_person_name_from_headline
from company_info.extractors.role_extractor import clean_role_title, extract_role_from_text
from company_info.extractors.movement_classifier import classify_strategic_movement


class CompanySiteScraper(BaseScraper):
    """
    Direct crawler for company corporate websites.
    Extracts leadership teams, executive directories, and recent official news.
    """

    def __init__(self, timeout: int = 2, rate_limit_delay: float = 0.0):
        super().__init__(timeout=timeout, max_retries=0, rate_limit_delay=rate_limit_delay)

    def crawl_company_site(self, profile: CompanyProfile) -> Dict[str, List[Any]]:
        """
        Crawls target company website to extract current leadership and corporate news.
        """
        domain = profile.domain
        if not domain:
            return {"roles": [], "movements": []}

        base_url = f"https://{domain}"
        role_events: List[RoleChangeEvent] = []
        movement_events: List[StrategicMovementEvent] = []
        seen_names = set()

        try:
            # 1. Fetch Homepage
            home_resp = self.fetch_get(base_url)
            if not home_resp or home_resp.status_code != 200:
                return {"roles": [], "movements": []}

            soup = BeautifulSoup(home_resp.text, "html.parser")

            # 2. Discover Relevant Sub-Pages
            leadership_links: Set[str] = set()
            news_links: Set[str] = set()

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                full_url = urllib.parse.urljoin(base_url, href)
                parsed_url = urllib.parse.urlparse(full_url)

                if parsed_url.netloc == urllib.parse.urlparse(base_url).netloc:
                    path_low = parsed_url.path.lower()

                    if any(kw in path_low for kw in ["team", "leadership", "executive", "board", "management"]):
                        leadership_links.add(full_url)
                    elif any(kw in path_low for kw in ["news", "press", "media", "announcements"]):
                        news_links.add(full_url)

            # 3. Scrape Leadership Page (fast single page)
            for l_url in list(leadership_links)[:1]:
                try:
                    l_resp = self.fetch_get(l_url)
                    if not l_resp or l_resp.status_code != 200:
                        continue

                    l_soup = BeautifulSoup(l_resp.text, "html.parser")
                    text_content = l_soup.get_text(separator=" ", strip=True)

                    # Regex match patterns: Name - Role
                    matches = re.findall(
                        r'([A-Z][a-z]+ [A-Z][a-z]+)\s*[-–|:,]\s*(Chief [A-Za-z]+ Officer|CEO|CFO|COO|CTO|CMO|CSO|President|Vice President|VP of [A-Za-z\s]+|Director of [A-Za-z\s]+|Founder)',
                        text_content
                    )

                    for raw_n, raw_r in matches:
                        clean_n = clean_person_name(raw_n, profile.company_name)
                        clean_r = clean_role_title(raw_r, clean_n)

                        if clean_n and clean_r and clean_n.lower() not in seen_names:
                            seen_names.add(clean_n.lower())
                            event = RoleChangeEvent(
                                person_name=clean_n,
                                company_name=profile.company_name,
                                movement_type=MovementType.CURRENT_LEADERSHIP,
                                role_title=clean_r,
                                evidence_snippet=f"Identified on official website leadership page: {clean_n} - {clean_r}",
                                source_url=l_url,
                                source_name="Official Company Website",
                                confidence_score=0.95,
                            )
                            role_events.append(event)
                except Exception:
                    continue

            # 4. Scrape News / Press Pages
            for n_url in list(news_links)[:2]:
                try:
                    n_resp = self.fetch_get(n_url)
                    if not n_resp or n_resp.status_code != 200:
                        continue

                    n_soup = BeautifulSoup(n_resp.text, "html.parser")
                    # Extract article titles / headings
                    headings = n_soup.find_all(["h1", "h2", "h3", "h4", "a"])
                    for h in headings:
                        htext = h.get_text(strip=True)
                        if len(htext) < 20 or len(htext) > 160:
                            continue

                        # Check if it's a strategic movement or executive hire
                        strat_cat = classify_strategic_movement(htext)
                        if strat_cat:
                            move_event = StrategicMovementEvent(
                                company_name=profile.company_name,
                                category=strat_cat,
                                headline=htext,
                                summary=f"Official corporate press announcement from {profile.company_name}: {htext}",
                                source_url=n_url,
                                source_name="Company Newsroom",
                                confidence_score=0.90,
                            )
                            movement_events.append(move_event)
                        else:
                            # Check if executive hire
                            name = extract_person_name_from_headline(htext, profile.company_name)
                            if name:
                                role = extract_role_from_text(htext, name) or "Executive Leader"
                                if name.lower() not in seen_names:
                                    seen_names.add(name.lower())
                                    hire_event = RoleChangeEvent(
                                        person_name=name,
                                        company_name=profile.company_name,
                                        movement_type=MovementType.JOINED,
                                        role_title=role,
                                        evidence_snippet=htext,
                                        source_url=n_url,
                                        source_name="Company Newsroom",
                                        confidence_score=0.90,
                                    )
                                    role_events.append(hire_event)
                except Exception:
                    continue

        except Exception:
            pass

        return {
            "roles": role_events,
            "movements": movement_events,
        }
