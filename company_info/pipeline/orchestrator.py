"""
orchestrator.py — Unified Company Intelligence Engine
company_info / pipeline
"""

from __future__ import annotations
import time
import re
import concurrent.futures
from typing import List, Dict, Any, Optional, Set

from company_info.models.company import CompanyProfile
from company_info.models.role_change import RoleChangeEvent, MovementType
from company_info.models.funding import FundingEvent, FundingRoundType
from company_info.models.movement import StrategicMovementEvent, MovementCategory
from company_info.models.report import CompanyIntelligenceReport

from company_info.engines.search_engine import MultiEngineSearchScraper
from company_info.engines.linkedin_public_engine import LinkedInPublicScraper
from company_info.engines.edgar_engine import EdgarFilingScraper
from company_info.engines.site_engine import CompanySiteScraper
from company_info.engines.news_wire_engine import IndustryWireScraper

from company_info.extractors.name_extractor import clean_person_name, extract_person_name_from_headline
from company_info.extractors.role_extractor import clean_role_title, extract_role_from_text
from company_info.extractors.funding_parser import parse_funding_amount, classify_round_type, extract_investors, extract_valuation
from company_info.extractors.movement_classifier import classify_person_movement, classify_strategic_movement


class CompanyIntelligenceEngine:
    """
    Unified intelligence orchestrator coordinating multi-source custom scrapers
    (Google News RSS, DuckDuckGo Lite, LinkedIn Public, SEC EDGAR, Corporate Site, Industry Wires)
    with 100% custom code and ZERO paid third-party APIs.
    """

    def __init__(
        self,
        timeout: int = 4,
        rate_limit_delay: float = 0.02,
        max_workers: int = 10,
    ):
        self.max_workers = max_workers
        self.search_scraper = MultiEngineSearchScraper(timeout=timeout, rate_limit_delay=rate_limit_delay)
        self.linkedin_scraper = LinkedInPublicScraper(search_scraper=self.search_scraper)
        self.edgar_scraper = EdgarFilingScraper(timeout=3)
        self.site_scraper = CompanySiteScraper(timeout=2.5, rate_limit_delay=0.01)
        self.wire_scraper = IndustryWireScraper(timeout=timeout, rate_limit_delay=rate_limit_delay)

    def _is_relevant_to_company(self, text: str, profile: CompanyProfile) -> bool:
        """
        Validates that the text passage or headline actually refers to the target company.
        """
        if not text:
            return False
        t_low = text.lower()
        co_low = profile.company_name.lower()
        core_low = profile.core_brand_name.lower()

        # Handle short names / acronyms (<= 4 chars, e.g. "ADM", "DSM", "BASF")
        if len(core_low) <= 4:
            has_acronym = bool(re.search(rf'\b{re.escape(core_low)}\b', t_low))
            if has_acronym:
                # Require domain or industry token to prevent false positives with tech/general acronyms
                ind_tokens = ["nutrition", "ingredient", "supplement", "food", "beverage", "crop", "feed", "biotech", "plant", "wellness", "health", "vitamin", "pharma", "flavors"]
                if (profile.domain and profile.domain.split(".")[0] in t_low) or any(tok in t_low for tok in ind_tokens):
                    return True
            return False

        # Check full company name
        if co_low in t_low:
            return True

        # Check core brand name (e.g. "AB Enzymes" for "AB Enzymes GmbH")
        if len(core_low) >= 3 and core_low in t_low:
            return True

        # Check domain keyword
        if profile.domain and len(profile.domain.split(".")[0]) >= 4 and profile.domain.split(".")[0] in t_low:
            return True

        # Check distinct company name words (e.g. "Vitaquest" in "Vitaquest International")
        co_words = [w for w in re.sub(r'[^\w\s]', '', co_low).split() if len(w) > 3 and w not in {"international", "health", "technologies", "group", "labs", "inc", "llc", "corp", "gmbh", "limited", "nutrition", "ingredients", "science"}]
        if any(w in t_low for w in co_words):
            return True

        return False

    # -----------------------------------------------------------------------
    # Single Company Full Intelligence Scan
    # -----------------------------------------------------------------------

    def scan_company(self, profile: CompanyProfile) -> CompanyIntelligenceReport:
        """
        Executes a 360-degree intelligence scan for a single target company.
        """
        start_t = time.time()
        co_name = profile.company_name
        data_sources_scraped: List[str] = []

        all_roles: List[RoleChangeEvent] = []
        all_funding: List[FundingEvent] = []
        all_movements: List[StrategicMovementEvent] = []

        seen_people: Set[str] = set()
        seen_funding_titles: Set[str] = set()
        seen_movement_headlines: Set[str] = set()

        # -------------------------------------------------------------------
        # 1. Multi-Engine News & Open Web Search (Bing News + Google News RSS)
        # -------------------------------------------------------------------
        try:
            unified_queries = self.search_scraper.build_unified_queries(profile)
            for q in unified_queries:
                search_hits = self.search_scraper.execute_search(q, limit=10)
                for hit in search_hits:
                    title = hit.get("title", "")
                    snippet = hit.get("snippet", "")
                    full_text = f"{title} {snippet}"
                    link = hit.get("link", "")
                    date_val = hit.get("date", "")
                    source = hit.get("source", "Industry News")

                    # Validate company relevance
                    if not self._is_relevant_to_company(full_text, profile):
                        continue

                    # 1. Extract Role Changes
                    person_name = extract_person_name_from_headline(title, co_name)
                    if not person_name:
                        person_name = extract_person_name_from_headline(snippet, co_name)

                    if person_name and person_name.lower() not in seen_people:
                        role = extract_role_from_text(full_text, person_name)
                        if role:
                            mov_type = classify_person_movement(full_text) or MovementType.JOINED
                            event = RoleChangeEvent(
                                person_name=person_name,
                                company_name=co_name,
                                movement_type=mov_type,
                                role_title=role,
                                date_str=date_val,
                                evidence_snippet=title,
                                source_url=link,
                                source_name=source,
                                confidence_score=0.92,
                            )
                            seen_people.add(person_name.lower())
                            all_roles.append(event)

                    # 2. Extract Funding
                    if not any(noise in full_text.lower() for noise in ["price target", "target price", "pt raised", "/share", "per share", "downgrades", "upgrades", "q1 results", "q2 results", "q3 results", "q4 results", "financial results"]):
                        amt_raw, amt_usd = parse_funding_amount(full_text)
                        is_true_funding = (
                            any(w in full_text.lower() for w in ["funding round", "capital raise", "series a", "series b", "series c", "seed round", "growth equity", "pre-seed", "venture funding", "secures funding", "closes funding", "closed funding", "raised $", "raised €", "secured $", "secured €"]) or
                            (any(w in full_text.lower() for w in ["raised", "funding", "seed", "financing"]) and amt_raw is not None)
                        )
                        if is_true_funding and title.lower() not in seen_funding_titles:
                            seen_funding_titles.add(title.lower())
                            f_event = FundingEvent(
                                company_name=co_name,
                                round_type=classify_round_type(full_text),
                                amount_raw=amt_raw,
                                amount_usd=amt_usd,
                                lead_investors=extract_investors(full_text)[0],
                                participating_investors=extract_investors(full_text)[1],
                                valuation_raw=extract_valuation(full_text),
                                date_str=date_val,
                                announcement_title=title,
                                summary=snippet[:300] if snippet else title,
                                source_url=link,
                                source_name=source,
                                confidence_score=0.88,
                            )
                            all_funding.append(f_event)

                    # 3. Extract Strategic Movements
                    strat_cat = classify_strategic_movement(full_text)
                    if strat_cat and title.lower() not in seen_movement_headlines:
                        seen_movement_headlines.add(title.lower())
                        m_event = StrategicMovementEvent(
                            company_name=co_name,
                            category=strat_cat,
                            headline=title,
                            summary=snippet[:300] if snippet else title,
                            date_str=date_val,
                            source_url=link,
                            source_name=source,
                            confidence_score=0.88,
                        )
                        all_movements.append(m_event)

            data_sources_scraped.append("Multi-Engine News & Web Search")
        except Exception:
            pass

        # -------------------------------------------------------------------
        # 2. LinkedIn Public Signals (Joins, Departures, Alumni)
        # -------------------------------------------------------------------
        try:
            li_events = self.linkedin_scraper.harvest_company_signals(profile)
            for li_e in li_events:
                if li_e.person_name.lower() not in seen_people:
                    seen_people.add(li_e.person_name.lower())
                    all_roles.append(li_e)
            if li_events:
                data_sources_scraped.append("LinkedIn Public Signals")
        except Exception:
            pass

        # -------------------------------------------------------------------
        # 3. SEC EDGAR Open Filings (Form D & 8-K)
        # -------------------------------------------------------------------
        try:
            edgar_results = self.edgar_scraper.harvest_events(profile)
            for f_ev in edgar_results.get("funding", []):
                all_funding.append(f_ev)
            for s_ev in edgar_results.get("strategic", []):
                if s_ev.headline.lower() not in seen_movement_headlines:
                    seen_movement_headlines.add(s_ev.headline.lower())
                    all_movements.append(s_ev)
            if edgar_results.get("funding") or edgar_results.get("strategic"):
                data_sources_scraped.append("SEC EDGAR Open Filings")
        except Exception:
            pass

        # -------------------------------------------------------------------
        # 4. Direct Corporate Website Crawling
        # -------------------------------------------------------------------
        if profile.domain:
            try:
                site_results = self.site_scraper.crawl_company_site(profile)
                for r_ev in site_results.get("roles", []):
                    if r_ev.person_name.lower() not in seen_people:
                        seen_people.add(r_ev.person_name.lower())
                        all_roles.append(r_ev)
                for m_ev in site_results.get("movements", []):
                    if m_ev.headline.lower() not in seen_movement_headlines:
                        seen_movement_headlines.add(m_ev.headline.lower())
                        all_movements.append(m_ev)
                if site_results.get("roles") or site_results.get("movements"):
                    data_sources_scraped.append(f"Official Website ({profile.domain})")
            except Exception:
                pass

        # -------------------------------------------------------------------
        # 5. Industry Wires & Media RSS
        # -------------------------------------------------------------------
        try:
            wire_results = self.wire_scraper.scan_industry_wires_for_company(profile)
            for r_ev in wire_results.get("roles", []):
                if r_ev.person_name.lower() not in seen_people:
                    seen_people.add(r_ev.person_name.lower())
                    all_roles.append(r_ev)
            for f_ev in wire_results.get("funding", []):
                if f_ev.announcement_title.lower() not in seen_funding_titles:
                    seen_funding_titles.add(f_ev.announcement_title.lower())
                    all_funding.append(f_ev)
            for m_ev in wire_results.get("movements", []):
                if m_ev.headline.lower() not in seen_movement_headlines:
                    seen_movement_headlines.add(m_ev.headline.lower())
                    all_movements.append(m_ev)
            if wire_results.get("roles") or wire_results.get("funding") or wire_results.get("movements"):
                data_sources_scraped.append("Nutraceutical Industry Wires & RSS")
        except Exception:
            pass

        exec_time = round(time.time() - start_t, 2)
        total_signals = len(all_roles) + len(all_funding) + len(all_movements)

        return CompanyIntelligenceReport(
            company_name=co_name,
            domain=profile.domain,
            website=profile.website,
            profile=profile,
            role_changes=all_roles,
            funding_events=all_funding,
            strategic_movements=all_movements,
            execution_time_sec=exec_time,
            data_sources_scraped=data_sources_scraped,
            total_signals_discovered=total_signals,
        )

    # -----------------------------------------------------------------------
    # Batch Processing for Multiple Companies with Checkpointing & Resumption
    # -----------------------------------------------------------------------

    def scan_batch(
        self,
        profiles: List[CompanyProfile],
        checkpoint_file: Optional[str] = None,
        resume: bool = True,
        on_progress=None,
    ) -> List[CompanyIntelligenceReport]:
        """
        Scans a cohort of companies concurrently using ThreadPoolExecutor with
        thread-safe streaming JSONL checkpointing and automatic resumption.
        """
        import os
        import threading
        import json

        reports: List[CompanyIntelligenceReport] = []
        completed_companies: Set[str] = set()
        write_lock = threading.Lock()

        # 1. Resume from checkpoint if present
        if checkpoint_file and resume and os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                rep = CompanyIntelligenceReport.model_validate(data)
                                reports.append(rep)
                                completed_companies.add(rep.company_name.lower().strip())
                            except Exception:
                                pass
            except Exception:
                pass

        # 2. Filter remaining companies to scan
        remaining_profiles = [p for p in profiles if p.company_name.lower().strip() not in completed_companies]

        if checkpoint_file and not os.path.exists(checkpoint_file):
            os.makedirs(os.path.dirname(os.path.abspath(checkpoint_file)), exist_ok=True)

        # Notify initial state if resuming
        if on_progress and len(reports) > 0:
            on_progress(len(reports), len(profiles), f"Loaded {len(reports)} cached from checkpoint")

        if not remaining_profiles:
            return reports

        # 3. Process remaining companies in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_co = {executor.submit(self.scan_company, p): p for p in remaining_profiles}
            for future in concurrent.futures.as_completed(future_to_co):
                profile = future_to_co[future]
                try:
                    rep = future.result()
                except Exception:
                    rep = CompanyIntelligenceReport(
                        company_name=profile.company_name,
                        domain=profile.domain,
                        profile=profile,
                    )

                reports.append(rep)

                # Thread-safe atomic append to checkpoint file
                if checkpoint_file:
                    with write_lock:
                        try:
                            with open(checkpoint_file, "a", encoding="utf-8") as cf:
                                cf.write(rep.model_dump_json() + "\n")
                                cf.flush()
                        except Exception:
                            pass

                if on_progress:
                    on_progress(len(reports), len(profiles), profile.company_name)

        return reports
