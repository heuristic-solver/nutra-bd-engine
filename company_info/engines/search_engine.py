"""
search_engine.py — Zero-Cost Multi-Engine Search Aggregator
company_info / engines
"""

from __future__ import annotations
import urllib.parse
import re
from typing import List, Dict, Any, Optional
import feedparser
from bs4 import BeautifulSoup

from company_info.engines.base_engine import BaseScraper
from company_info.models.company import CompanyProfile

NOISE_DOMAINS = {
    "reddit.com", "quora.com", "pinterest.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "tiktok.com", "youtube.com", "amazon.com", "ebay.com", "walmart.com",
    "target.com", "glassdoor.com", "indeed.com", "ziprecruiter.com", "comparably.com",
    "dnb.com", "zoominfo.com", "datanyze.com", "yelp.com", "tripadvisor.com"
}


class MultiEngineSearchScraper(BaseScraper):
    """
    Zero-cost multi-engine search scraper combining:
      1. Google News RSS Feeds (High recency & accurate publication dates)
      2. Bing Search Scraper (Alternative fallback)
    """

    _gnews_circuit_open_until: float = 0.0
    _gnews_consecutive_failures: int = 0

    def __init__(self, timeout: int = 2, rate_limit_delay: float = 0.05):
        super().__init__(timeout=timeout, max_retries=1, rate_limit_delay=rate_limit_delay)

    # -----------------------------------------------------------------------
    # Core Engine Search Methods
    # -----------------------------------------------------------------------

    def search_google_news(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Scrape Google News RSS for a given query with circuit-breaker protection."""
        import time
        # If circuit is open due to recent rate limit / timeout, fail fast immediately (0ms)
        if time.time() < MultiEngineSearchScraper._gnews_circuit_open_until:
            return []

        try:
            encoded = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
            resp = self.fetch_get(url)
            if not resp or resp.status_code != 200:
                MultiEngineSearchScraper._gnews_consecutive_failures += 1
                if MultiEngineSearchScraper._gnews_consecutive_failures >= 3:
                    MultiEngineSearchScraper._gnews_circuit_open_until = time.time() + 30.0  # 30s cooldown
                return []

            # Success -> reset circuit
            MultiEngineSearchScraper._gnews_consecutive_failures = 0
            feed = feedparser.parse(resp.text)
            results = []
            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                pub_date = entry.get("published", "")
                source_title = (entry.get("source") or {}).get("title", "")
                snippet = entry.get("summary", "")

                results.append({
                    "title": title,
                    "link": link,
                    "date": pub_date,
                    "source": source_title,
                    "snippet": snippet,
                    "engine": "google_news_rss"
                })
            return results
        except Exception:
            MultiEngineSearchScraper._gnews_consecutive_failures += 1
            if MultiEngineSearchScraper._gnews_consecutive_failures >= 3:
                MultiEngineSearchScraper._gnews_circuit_open_until = time.time() + 30.0
            return []

    def search_ddg_lite(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Scrape DuckDuckGo Lite HTML results."""
        try:
            url = "https://lite.duckduckgo.com/lite/"
            resp = self.fetch_post(url, data={"q": query})
            if not resp or resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.select("tr")
            results = []
            for r in rows:
                link_tag = r.select_one("a.result-link")
                snippet_tag = r.select_one(".result-snippet")
                if link_tag:
                    title = link_tag.get_text(strip=True)
                    href = link_tag.get("href", "")
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                    # Check noise domain
                    if any(nd in href.lower() for nd in NOISE_DOMAINS):
                        continue

                    results.append({
                        "title": title,
                        "link": href,
                        "date": "",
                        "source": urllib.parse.urlparse(href).netloc.replace("www.", ""),
                        "snippet": snippet,
                        "engine": "duckduckgo_lite"
                    })
                    if len(results) >= limit:
                        break
            return results
        except Exception:
            return []

    def search_bing_news(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Scrape Bing News search results."""
        try:
            url = f"https://www.bing.com/news/search?q={urllib.parse.quote(query)}"
            resp = self.fetch_get(url)
            if not resp or resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(".news-card, .na_card, .news-card-body, .t_s, .b_algo")
            results = []
            seen_titles = set()
            for c in cards[:limit]:
                title_tag = c.select_one("a.title") or c.select_one("a[class*='title']") or c.select_one("h2 a") or c.select_one("h2")
                p_tag = c.select_one(".snippet, .b_caption p, .b_lineclamp2, p")
                src_tag = c.select_one(".source, .news-source, .b_attribution")
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    href = title_tag.get("href", "")
                    if not title or len(title) < 10 or title.lower() in seen_titles:
                        continue
                    if any(nd in href.lower() for nd in NOISE_DOMAINS):
                        continue
                    seen_titles.add(title.lower())
                    results.append({
                        "title": title,
                        "link": href,
                        "date": "",
                        "source": src_tag.get_text(strip=True) if src_tag else "Bing News",
                        "snippet": p_tag.get_text(strip=True) if p_tag else "",
                        "engine": "bing_news"
                    })
            return results
        except Exception:
            return []

    def search_bing(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Scrape Bing web search results as fallback."""
        try:
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
            resp = self.fetch_get(url)
            if not resp or resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select("li.b_algo")
            results = []
            for item in items[:limit]:
                h2 = item.select_one("h2 a")
                snippet_tag = item.select_one(".b_caption p") or item.select_one(".b_lineclamp2") or item.select_one(".b_lineclamp3")
                if h2:
                    href = h2.get("href", "")
                    if any(nd in href.lower() for nd in NOISE_DOMAINS):
                        continue
                    results.append({
                        "title": h2.get_text(strip=True),
                        "link": href,
                        "date": "",
                        "source": urllib.parse.urlparse(href).netloc.replace("www.", ""),
                        "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                        "engine": "bing"
                    })
            return results
        except Exception:
            return []

    # -----------------------------------------------------------------------
    # Multi-Engine Query Executor
    # -----------------------------------------------------------------------

    def execute_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Executes search across Bing News (active & fast) and Google News RSS,
        with fallback to Bing Web, deduplicating results in milliseconds.
        """
        combined: List[Dict[str, Any]] = []
        seen_titles = set()

        # 1. Bing News first (fast, zero rate limiting)
        try:
            bnews_results = self.search_bing_news(query, limit=limit)
            for r in bnews_results:
                if r["title"].lower() not in seen_titles:
                    seen_titles.add(r["title"].lower())
                    combined.append(r)
        except Exception:
            pass

        # 2. Google News RSS (if circuit is closed)
        if len(combined) < limit:
            try:
                news_results = self.search_google_news(query, limit=limit)
                for r in news_results:
                    if r["title"].lower() not in seen_titles:
                        seen_titles.add(r["title"].lower())
                        combined.append(r)
            except Exception:
                pass

        # 3. Bing Web fallback if still sparse (< 2 results)
        if len(combined) < 2:
            try:
                bing_results = self.search_bing(query, limit=limit)
                for r in bing_results:
                    if r["title"].lower() not in seen_titles:
                        seen_titles.add(r["title"].lower())
                        combined.append(r)
            except Exception:
                pass

        return combined[:limit]

    # -----------------------------------------------------------------------
    # Contextual Dork Builders
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_anchor(profile: CompanyProfile) -> str:
        name = profile.company_name
        core_name = profile.core_brand_name
        domain = profile.domain

        anchor_terms = [f'"{core_name}"']
        if core_name.lower() != name.lower():
            anchor_terms.append(f'"{name}"')
        if domain:
            anchor_terms.append(f'"{domain}"')

        anchor = "(" + " OR ".join(anchor_terms) + ")"

        # Add contextual industry keywords for short acronyms (e.g. 'ADM', 'DSM', 'GNC') or single-word common names (e.g. 'Seed', 'Ritual', 'Liquid', 'Future', 'Pure')
        ind_kw = "supplement OR nutraceutical OR vitamins OR ingredient OR nutrition OR food OR wellness"
        if len(core_name) <= 4 or len(core_name.split()) == 1:
            anchor = f'({anchor} AND ({ind_kw}))'

        return anchor

    @staticmethod
    def build_unified_queries(profile: CompanyProfile) -> List[str]:
        """Generate a single consolidated high-yield query capturing roles, funding, and strategic movements."""
        anchor = MultiEngineSearchScraper._build_anchor(profile)
        return [
            f'{anchor} ("appointed" OR "named" OR "joined" OR "hired" OR "promoted" OR "steps down" OR "resigned" OR "departs" OR "CEO" OR "CFO" OR "VP" OR "Director" OR "funding" OR "raised" OR "Series A" OR "Series B" OR "acquired" OR "acquisition" OR "merger" OR "expansion" OR "facility" OR "launches" OR "partnership")'
        ]

    @staticmethod
    def build_role_change_queries(profile: CompanyProfile) -> List[str]:
        """Generate high-yield unified dork for role changes, appointments, promotions, and departures."""
        anchor = MultiEngineSearchScraper._build_anchor(profile)
        return [
            f'{anchor} ("appointed" OR "named" OR "joined" OR "welcomed" OR "hired" OR "promoted to" OR "steps down" OR "resigned" OR "departs" OR "leaves" OR "leaving" OR "interim" OR "transition" OR "new CEO" OR "new CFO" OR "new COO" OR "new VP" OR "new Director")'
        ]

    @staticmethod
    def build_funding_and_ma_queries(profile: CompanyProfile) -> List[str]:
        """Generate high-yield unified dork for funding rounds, capital raises, and M&A."""
        anchor = MultiEngineSearchScraper._build_anchor(profile)
        return [
            f'{anchor} ("funding" OR "raised" OR "Series A" OR "Series B" OR "Series C" OR "growth equity" OR "investment" OR "valuation" OR "acquired by" OR "acquisition of" OR "merger" OR "bought by" OR "private equity acquired" OR "all-cash transaction")'
        ]

    @staticmethod
    def build_strategic_movement_queries(profile: CompanyProfile) -> List[str]:
        """Generate high-yield unified dork for facility expansions, partnerships, and product launches."""
        anchor = MultiEngineSearchScraper._build_anchor(profile)
        return [
            f'{anchor} ("expansion" OR "facility" OR "manufacturing" OR "new plant" OR "lab expansion" OR "warehouse" OR "capacity" OR "partnership with" OR "joint venture" OR "launches" OR "rebrands" OR "restructuring" OR "solution")'
        ]
