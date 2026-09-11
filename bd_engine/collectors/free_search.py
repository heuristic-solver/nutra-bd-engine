"""
free_search.py — Zero-Cost Search Fallback Engine
BD Engine | bd_engine/collectors/

A drop-in fallback for Serper that uses:
  1. DuckDuckGo Web Search (duckduckgo_search v8+) — free, no API key
  2. DuckDuckGo News Search — free, covers recent events
  3. Google News RSS (feedparser) — free, highly current

Used automatically when Serper returns "Not enough credits" (HTTP 400).

Key methods match the Serper response shape so the rest of the pipeline
works without any changes:
  - search(query, endpoint, num, timelimit) -> List[dict]
      dict keys: title, link, snippet, source, date
"""

from __future__ import annotations

import re
import time
import feedparser
import urllib.parse
from typing import List, Optional
from datetime import datetime, timezone

try:
    from ddgs import DDGS  # Preferred: new package name
    _DDG_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS  # Legacy fallback
        _DDG_AVAILABLE = True
    except ImportError:
        _DDG_AVAILABLE = False


# ---------------------------------------------------------------------------
# TIME LIMIT MAPPING:  Serper tbs codes  ->  DDGS timelimit codes
# NOTE: DDG only has d/w/m/y — no 3-month or 6-month bucket.
# We use "y" (1 year) for all sub-year windows and rely on the SerperCollector's
# strict 90-day post-processing filter to enforce the actual recency ceiling.
# ---------------------------------------------------------------------------
_TBS_TO_DDGS = {
    "qdr:h":  "d",   # past hour  -> past day
    "qdr:d":  "d",   # past day
    "qdr:w":  "w",   # past week
    "qdr:m":  "m",   # past month
    "qdr:m3": "y",   # past 3 months -> use 1y, filter at processor (DDG has no 3m bucket)
    "qdr:m6": "y",   # past 6 months -> use 1y, filter at processor
    "qdr:y":  "y",   # past year
    "":       None,  # no restriction
}

_NOISE_DOMAINS = {
    "reddit.com", "quora.com", "pinterest.com", "facebook.com",
    "twitter.com", "x.com", "instagram.com", "tiktok.com", "youtube.com",
    "amazon.com", "ebay.com", "walmart.com", "target.com",
}

# Site: domains that DDG doesn't index well — convert to keyword anchors
_POOR_DDG_SITE_DOMAINS = [
    "linkedin.com/posts",
    "linkedin.com/in",
    "linkedin.com",
]


def _preprocess_for_ddg(query: str) -> str:
    """
    Transform a Serper/Google-style query into a DDG-compatible query.

    Key transforms:
      - site:linkedin.com/posts "X" (...) → "X" (...) linkedin.com
        (DDG ignores site: for LinkedIn; use domain as keyword instead)
      - Preserve quoted phrases and OR/AND logic
      - Remove unsupported Google-only operators
    """
    import re as _re

    # 1. Extract site: directive and convert to keyword
    site_match = _re.search(r'site:([^\s]+)', query)
    if site_match:
        site_val = site_match.group(1)  # e.g. 'linkedin.com/posts'
        # Remove the site: clause from the query
        q = _re.sub(r'\bsite:[^\s]+', '', query).strip()
        # Extract just the domain portion as a keyword anchor
        domain_keyword = site_val.split('/')[0]  # 'linkedin.com'
        # Append domain as a keyword (without site: prefix)
        if domain_keyword not in q:
            q = f"{q} {domain_keyword}"
        return _re.sub(r'\s+', ' ', q).strip()

    # 2. Handle multi-site OR patterns like: site:X OR site:Y
    multi_site_match = _re.search(r'site:\S+(?:\s+OR\s+site:\S+)+', query)
    if multi_site_match:
        # Extract all site values
        sites = _re.findall(r'site:(\S+)', query)
        q = _re.sub(r'site:\S+(?:\s+OR\s+site:\S+)+', '', query).strip()
        # Use just the first domain as anchor keyword
        if sites:
            domain_keyword = sites[0].split('/')[0]
            if domain_keyword not in q:
                q = f"{q} {domain_keyword}"
        return _re.sub(r'\s+', ' ', q).strip()

    return query


def _normalise_ddg_item(raw: dict) -> dict:
    body = (raw.get("body") or raw.get("description") or
            raw.get("snippet") or raw.get("summary") or "")
    date_raw = raw.get("published") or raw.get("date") or ""
    return {
        "title":   raw.get("title", ""),
        "link":    raw.get("href") or raw.get("url") or raw.get("link", ""),
        "snippet": body[:300],
        "source":  raw.get("source", "") or _domain(raw.get("href", "")),
        "date":    _fmt_date(date_raw),
    }


def _domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _fmt_date(raw: str) -> str:
    if not raw:
        return ""
    low = raw.lower()
    if any(w in low for w in ("ago", "today", "yesterday", "hour", "minute")):
        return raw
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ",
                "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT",
                "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw[:25].strip(), fmt)
            now_utc = datetime.now(timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            days = (now_utc - dt).days
            if days == 0:
                return "Today"
            if days == 1:
                return "1 day ago"
            if days < 7:
                return f"{days} days ago"
            if days < 30:
                return f"{days // 7} weeks ago"
            if days < 365:
                return f"{days // 30} months ago"
            return dt.strftime("%b %Y")
        except Exception:
            continue
    return raw[:20]


class FreeSearchEngine:
    """
    Zero-cost search engine using DuckDuckGo and Google News RSS.
    API mirrors SerperCollector._search() so the pipeline needs no changes.
    """

    def __init__(self, delay: float = 1.5):
        self.delay = delay
        self._last_ts: float = 0.0

    def _throttle(self):
        elapsed = time.time() - self._last_ts
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_ts = time.time()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def search(
        self,
        query: str,
        endpoint: str = "search",
        num: int = 10,
        tbs: str = "qdr:m3",
        filter_noise: bool = True,
    ) -> List[dict]:
        """Search DuckDuckGo + Google News RSS. Returns Serper-shaped dicts."""
        timelimit = _TBS_TO_DDGS.get(tbs, "m")
        results: List[dict] = []

        if _DDG_AVAILABLE:
            if endpoint == "news":
                results = self._ddg_news(query, num=num, timelimit=timelimit)
            else:
                results = self._ddg_text(query, num=num, timelimit=timelimit)

            # Supplement with news if web returned too few
            if len(results) < 3 and endpoint == "search":
                news = self._ddg_news(query, num=num, timelimit=timelimit)
                seen = {r["link"] for r in results}
                results += [r for r in news if r["link"] not in seen]

        # Always add Google News RSS for news endpoint or low results
        if endpoint == "news" or len(results) < 3:
            rss = self._google_news_rss(query, num=num)
            seen = {r["link"] for r in results}
            results += [r for r in rss if r["link"] not in seen]

        if filter_noise:
            results = [r for r in results
                       if not any(nd in r.get("link", "") for nd in _NOISE_DOMAINS)]

        return results[:num]

    # -----------------------------------------------------------------------
    # DuckDuckGo Web
    # -----------------------------------------------------------------------

    def _ddg_text(self, query: str, num: int = 10, timelimit: Optional[str] = "m") -> List[dict]:
        if not _DDG_AVAILABLE:
            return []
        self._throttle()
        ddg_query = _preprocess_for_ddg(query)  # convert site: to keyword anchors
        try:
            with DDGS() as d:
                raw = d.text(keywords=ddg_query, timelimit=timelimit,
                             max_results=min(num, 20), safesearch="off")
            return [_normalise_ddg_item(r) for r in (raw or [])]
        except Exception as ex:
            if "ratelimit" in str(ex).lower() or "timeout" in str(ex).lower():
                time.sleep(5)
            return []

    # -----------------------------------------------------------------------
    # DuckDuckGo News
    # -----------------------------------------------------------------------

    def _ddg_news(self, query: str, num: int = 10, timelimit: Optional[str] = "m") -> List[dict]:
        if not _DDG_AVAILABLE:
            return []
        self._throttle()
        ddg_query = _preprocess_for_ddg(query)  # convert site: to keyword anchors
        try:
            with DDGS() as d:
                raw = d.news(keywords=ddg_query, timelimit=timelimit,
                             max_results=min(num, 20))
            return [_normalise_ddg_item(r) for r in (raw or [])]
        except Exception as ex:
            if "ratelimit" in str(ex).lower() or "timeout" in str(ex).lower():
                time.sleep(5)
            return []

    # -----------------------------------------------------------------------
    # Google News RSS
    # -----------------------------------------------------------------------

    def _google_news_rss(self, query: str, num: int = 10) -> List[dict]:
        """100% free Google News via RSS — no key, no quota."""
        try:
            encoded = urllib.parse.quote(query)
            url = (f"https://news.google.com/rss/search?q={encoded}"
                   "&hl=en-US&gl=US&ceid=US:en")
            feed = feedparser.parse(url)
            out = []
            for entry in feed.entries[:num]:
                out.append({
                    "title":   entry.get("title", ""),
                    "link":    entry.get("link", ""),
                    "snippet": entry.get("summary", "")[:300],
                    "source":  (entry.get("source") or {}).get("title", ""),
                    "date":    _fmt_date(entry.get("published", "")),
                })
            return out
        except Exception:
            return []


# Module-level singleton
_engine: Optional[FreeSearchEngine] = None

def get_free_engine() -> FreeSearchEngine:
    global _engine
    if _engine is None:
        _engine = FreeSearchEngine()
    return _engine
