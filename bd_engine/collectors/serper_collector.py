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
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Free search fallback (DuckDuckGo + Google News RSS) — used when Serper credits exhausted
try:
    from bd_engine.collectors.free_search import get_free_engine as _get_free_engine
    _FREE_SEARCH_AVAILABLE = True
except ImportError:
    try:
        from free_search import get_free_engine as _get_free_engine
        _FREE_SEARCH_AVAILABLE = True
    except ImportError:
        _FREE_SEARCH_AVAILABLE = False
        def _get_free_engine():
            return None

# Explicitly load .env from workspace root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_BASE_URL = "https://google.serper.dev"

# Serper tbs (time-based search) values:
#   qdr:m  = last 30 days
#   qdr:m3 = last 3 months (90 days) <- STRICT recency for BD pipeline
#   qdr:m6 = last 6 months (180 days)
#   qdr:y  = last 12 months
DEFAULT_RECENCY = "qdr:m3"   # Last 3 months (max 90 days)

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

# -------------------------------------------------------------------
# ROLE CHANGE DETECTION — MID-LEVEL (All Seniority Levels)
# -------------------------------------------------------------------
# Nutraceutical-specific roles to target in role-change queries
NUTRA_ROLE_TITLES = [
    "formulation scientist", "formulation manager", "formulation chemist",
    "regulatory affairs", "quality assurance", "quality manager", "QA manager",
    "QA director", "regulatory specialist", "VP regulatory",
    "R&D manager", "R&D director", "director of R&D", "innovation manager",
    "nutrition scientist", "nutritionist", "clinical research",
    "supply chain manager", "procurement manager", "operations manager",
    "plant manager", "manufacturing manager", "production manager",
    "sales manager", "account manager", "business development manager",
    "national accounts manager", "VP sales", "VP marketing",
    "brand manager", "marketing manager", "director of marketing",
]

# Seniority classification — ordered most-specific first
SENIORITY_TIERS = [
    ("C-Suite",  ["chief", "ceo", "coo", "cfo", "cto", "cmo", "president", "founder"]),
    ("VP",       ["vp ", "vice president", "svp", "evp"]),
    ("Director", ["director"]),
    ("Manager",  ["manager", "head of", "lead ", "principal", "senior "]),
    ("Mid-Level",["specialist", "scientist", "analyst", "engineer",
                  "associate", "consultant", "technician", "coordinator"]),
]

# Role-change query templates — nutra-anchored to avoid false positives
ROLE_CHANGE_QUERY_TEMPLATES = [
    # 1. Direct appointment/departure news press (captures PR Newswire, BusinessWire, Trade Press)
    '"{company}" (appoint OR appoints OR appointed OR named OR joins OR joined OR hires OR hired OR "steps down" OR left OR departs OR promoted) (leadership OR executive OR director OR VP OR scientist OR manager OR "Chief")',
    # 2. LinkedIn employee announcements (high quality post signals)
    '"{company}" ("excited to share" OR "joined" OR "starting a new" OR "thrilled to join" OR "happy to share" OR "my last day at" OR "moving on from") linkedin.com',
    # 3. LinkedIn profile updates & titles at company
    '"{company}" ("formulation scientist" OR "regulatory affairs" OR "quality assurance" OR "R&D director" OR "VP" OR "Director" OR "Manager") linkedin.com/in',
    # 4. Industry trade press transitions
    '"{company}" (joins OR appointed OR departed OR resigned OR "steps down" OR hires) (supplement OR nutraceutical OR nutrition OR ingredient)',
    # 5. LinkedIn company page announcements
    'site:linkedin.com "{company}" ("please welcome" OR "thrilled to announce" OR "excited to welcome" OR "delighted to announce" OR "new team member" OR "welcomes")',
    # 6. Press releases across major newswires
    '"{company}" ("hires" OR "appoints" OR "names" OR "welcomes" OR "announces appointment") (site:prnewswire.com OR site:businesswire.com OR site:globenewswire.com)',
    # 7. Nutra and functional food trade publications
    '"{company}" ("joins" OR "appointed" OR "named" OR "hired" OR "steps down") (site:nutraingredients-usa.com OR site:naturalproductsinsider.com OR site:nutraceuticalsworld.com)',
    # 8. Google News / general press with announcement language
    '"{company}" ("new hire" OR "newly appointed" OR "new role" OR "executive hire" OR "new chief" OR "new VP") 2025 OR 2026',
    # 9. Broader departure & alumni announcements
    'site:linkedin.com "{company}" ("my last day" OR "moving on" OR "next chapter" OR "new opportunity" OR "leaving" OR "farewell")',
]


class SerperCollector:
    """
    Pulls structured market intelligence signals for nutraceutical companies
    using Serper's Google Search and News APIs.

    Exec movements now return fully structured events:
      - executive_name, title, function, direction (ARRIVAL/DEPARTURE)
      - is_senior_level, replacement_detected, date, source_url
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SERPER_API_KEY", "") or SERPER_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        })

    # ------------------------------------------------------------------
    # CORE API CALL
    # ------------------------------------------------------------------

    def _serper_credits_ok(self) -> bool:
        """Returns False when the API key has no credits left."""
        return getattr(self, "_serper_ok", True)

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
        Falls back to DuckDuckGo + Google News RSS if Serper credits are exhausted.
        """
        # If Serper has already been flagged as out of credits, skip directly to fallback
        if not getattr(self, '_serper_ok', True):
            return self._free_search(query, endpoint=endpoint, num=num,
                                     tbs=recency, filter_noise=filter_noise)

        url = f"{SERPER_BASE_URL}/{endpoint}"
        payload = {"q": query, "num": num, "tbs": recency}

        try:
            resp = self.session.post(url, json=payload, timeout=15)

            # Detect credit exhaustion
            if resp.status_code == 400:
                try:
                    err = resp.json().get("message", "")
                    if "credit" in err.lower() or "quota" in err.lower():
                        self._serper_ok = False
                        print("  [Serper] Credits exhausted — switching to free search (DDG + Google News RSS)")
                        return self._free_search(query, endpoint=endpoint, num=num,
                                                 tbs=recency, filter_noise=filter_noise)
                except Exception:
                    pass

            if not resp.ok:
                # Non-credit failure — still try free fallback
                return self._free_search(query, endpoint=endpoint, num=num,
                                         tbs=recency, filter_noise=filter_noise)

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
            return self._free_search(query, endpoint=endpoint, num=num,
                                     tbs=recency, filter_noise=filter_noise)

    def _free_search(
        self,
        query: str,
        endpoint: str = "search",
        num: int = 10,
        tbs: str = "qdr:m3",
        filter_noise: bool = True,
    ) -> List[dict]:
        """Delegate to the free DuckDuckGo + Google News RSS engine."""
        if not _FREE_SEARCH_AVAILABLE:
            return []
        engine = _get_free_engine()
        if engine is None:
            return []
        return engine.search(query, endpoint=endpoint, num=num, tbs=tbs,
                             filter_noise=filter_noise)

    # ------------------------------------------------------------------
    # SIGNAL TYPE CLASSIFIERS
    # ------------------------------------------------------------------

    @staticmethod
    def get_event_age_days(date_str: str, text: str = "") -> tuple:
        """
        Calculates exact event age in days and enforces strict 90-day (3-month) ceiling.
        Returns: (is_within_90d: bool, age_days: int, parsed_date_label: str)
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        d_clean = (date_str or "").strip()
        t_lower = (text or "").lower()

        # 1. Relative period enforcement
        m_mo = re.search(r'\b(\d+)\s+months?\s+ago\b', d_clean.lower()) or re.search(r'\b(\d+)\s+mos?\s+ago\b', d_clean.lower())
        if m_mo:
            n_mo = int(m_mo.group(1))
            age_days = n_mo * 30
            return (age_days <= 90, age_days, f"{n_mo} months ago")

        m_yr = re.search(r'\b(\d+)\s+years?\s+ago\b', d_clean.lower()) or re.search(r'\b(\d+)\s+yrs?\s+ago\b', d_clean.lower())
        if m_yr:
            n_yr = int(m_yr.group(1))
            return (False, n_yr * 365, f"{n_yr} years ago")

        m_wk = re.search(r'\b(\d+)\s+weeks?\s+ago\b', d_clean.lower()) or re.search(r'\b(\d+)\s+wks?\s+ago\b', d_clean.lower())
        if m_wk:
            n_wk = int(m_wk.group(1))
            age_days = n_wk * 7
            return (age_days <= 90, age_days, f"{n_wk} weeks ago")

        m_day = re.search(r'\b(\d+)\s+days?\s+ago\b', d_clean.lower())
        if m_day:
            n_d = int(m_day.group(1))
            return (n_d <= 90, n_d, f"{n_d} days ago")

        if "yesterday" in d_clean.lower():
            return (True, 1, "1 day ago")
        if "today" in d_clean.lower() or "hour" in d_clean.lower() or "minute" in d_clean.lower():
            return (True, 0, "Today")

        # 2. Absolute date enforcement
        if d_clean:
            clean_d = re.sub(r'(?:am|pm|est|edt|pst|pdt|utc|gmt)', '', d_clean, flags=re.IGNORECASE).strip()
            for fmt in ('%b %d, %Y', '%B %d, %Y', '%d %b %Y', '%d %B %Y', '%Y-%m-%d', '%Y-%m', '%b %Y', '%B %Y'):
                try:
                    dt = datetime.strptime(clean_d, fmt)
                    delta_days = (now - dt).days
                    is_valid = (-5 <= delta_days <= 90)
                    return (is_valid, max(0, delta_days), dt.strftime('%Y-%m-%d'))
                except ValueError:
                    continue

        # 3. Text mention rejection
        if re.search(r'\b(?:[4-9]|1[0-2])\s+months?\s+ago\b', t_lower) or re.search(r'\b\d+\s+years?\s+ago\b', t_lower):
            return (False, 120, "Text mentions >3 months ago")

        return (True, 45, "Within 90d window (qdr:m3)")

    @classmethod
    def is_within_3_months(cls, date_str: str, text: str = "") -> bool:
        """Strict 90-day (3-month) maximum recency check."""
        is_valid, _, _ = cls.get_event_age_days(date_str, text)
        return is_valid

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
        """Determine if a role change signal is an ARRIVAL or DEPARTURE."""
        combined = (title + " " + snippet).lower()
        departure_cues = [
            "steps down", "stepping down", "leaves", "left", "departed", "departure",
            "resigned", "resignation", "transition", "successor", "interim", "retirement",
            "retiring", "exited", "no longer", "former", "ex-", "last day at", "previously at",
            "saying goodbye", "farewell", "moving on from"
        ]
        if any(kw in combined for kw in departure_cues):
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
    def clean_person_name(name: Optional[str]) -> Optional[str]:
        """Clean and validate that a string is a real human person name, not an organization, headline or noise."""
        if not name or name.lower() in ("not extracted", "unknown", "?", "none", "", "et now"):
            return None

        # Strip credential suffixes, post labels, and leading digits
        suffix_pat = re.compile(r'\b(CNS|MD|PHD|MS|MBA|RD|RDN|OD|FAAO|FAAP|FACHE|MBE|OLY|DR|BSC|CPG|CPA|IHP|ND)\b', re.IGNORECASE)
        clean = suffix_pat.sub('', name).strip()
        clean = re.sub(r'[\'’]s?\s+Post.*$', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'\s+on\s+LinkedIn.*$', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'^\d+\s+', '', clean).strip()
        clean = re.sub(r'[^a-zA-Z\s\'-]', '', clean).strip()
        clean = re.sub(r'\s+', ' ', clean).strip()

        words = clean.split()
        if not (2 <= len(words) <= 4):
            return None

        # Real names do not contain prepositions, conjunctions, or action verbs
        stopwords_in_names = {
            "in", "on", "at", "to", "for", "with", "from", "by", "of", "and", "or",
            "the", "a", "an", "through", "about", "into", "over", "after", "is",
            "are", "was", "were", "be", "been", "has", "have", "had", "will"
        }
        if any(w.lower() in stopwords_in_names for w in words):
            return None

        # Reject if string contains job title words
        job_title_words = {
            'analyst', 'manager', 'director', 'officer', 'specialist', 'engineer', 'lead',
            'head', 'vice', 'president', 'chief', 'advisor', 'consultant', 'associate',
            'intern', 'planner', 'recruiter', 'buyer', 'supervisor', 'technician',
            'assistant', 'program', 'project', 'coordinator', 'scientist', 'chemist', 'fellow',
            'partner', 'founder', 'member'
        }
        lower_words = [re.sub(r'[^a-zA-Z0-9]', '', w).lower() for w in words]
        if any(w in job_title_words for w in lower_words):
            return None

        non_person = {
            "podcast", "media", "news", "official", "research", "insights", "group",
            "association", "browser", "advice", "future", "channel", "magazine",
            "digest", "network", "report", "corporation", "inc", "llc", "ltd", "gmbh",
            "holdings", "reviews", "solutions", "partners", "over", "thing", "express",
            "foods", "food", "supplement", "supplements", "nutrition", "nutraceutical",
            "wellness", "health", "pharma", "campaign", "digestive", "post", "tackles",
            "guys", "forms", "organizations", "fertility", "trade", "global", "ivf",
            "thorne", "ritual", "seed", "solgar", "olly", "jarrow", "megafood",
            "designs", "xymogen", "pure", "integrative", "vital", "life", "extension",
            "nature", "chapter", "hanzo", "two-phase", "vrm", "align", "success", "dairy",
            "fiscal", "growth", "approach", "treatment", "fund", "women", "sustainability",
            "update", "evidensia", "transformation", "agricultural", "leadership", "executive",
            "discussed", "discusses", "explained", "explaining", "science", "oil", "oils",
            "orchards", "orchard", "chickens", "chicken", "fungal", "biodiversity",
            "institute", "innovators", "innovator", "coach", "coaching", "uk", "pepsico",
            "launch", "practice", "clinical", "creatine", "evidence", "healthspan", "animals",
            "animal", "products", "product", "bayer", "brand", "brands", "delivery", "complex",
            "extending", "millennials", "broiler", "supplementation", "conscienhealth", "gmo",
            "press", "release", "responds", "respond", "opportunities", "opportunity", "local",
            "patient-centered", "centered", "care", "computer-aided", "aided", "machinora",
            "corp", "zipchat", "ai", "infra", "engineers", "limited", "mikromol", "lgc",
            "india", "market", "probiotics", "probiotic", "services", "technologies", "technology",
            "enviro", "screen", "unity", "industry", "skills", "skill", "basic",
            "demand", "scope", "alliance", "reliable", "data", "daily", "poultry", "biosecurity",
            "program", "celleste", "bio", "family", "business", "zealand", "molecular", "design",
            "skin", "borders", "supp", "co", "corston", "architectural", "detail", "sabinsagroup",
            "ox8", "cf", "center", "centre", "system", "systems", "platform", "team", "department",
            "division", "office", "agency", "council", "academy", "university", "college", "school",
            "lab", "laboratory", "laboratories", "venture", "ventures", "capital", "enterprises",
            "industries", "international", "company", "consulting", "advisors", "digital",
            "analytics", "intelligence", "studies", "study", "guide", "forum", "summit", "conference",
            "event", "events", "award", "awards", "weekly", "monthly", "quarterly", "journal",
            "bulletin", "dispatch", "chronicle", "tribune", "herald", "times", "gazette", "monitor",
            "wire", "newswire", "pr", "comms", "communications", "start", "heads",
            "vitafoods", "supplyside", "expo", "asia", "europe", "america", "apac", "emea", "usa",
            "north", "south", "east", "west", "xpo", "nrg", "cat", "dog", "disney", "movies",
            "actor", "ingredient", "ingredients", "energy", "drink", "jobs", "careers",
            "linkedin", "strategy", "review", "dave", "called", "shelter", "hilarious",
            "hydrogen", "corona", "eamino", "max", "astragin", "cognizin", "curcumin", "extract",
            "advanced", "insider", "shoppe", "biomarine", "herb", "pharm", "framework", "software",
            "wealth", "petfood", "microbiome", "therapeutics", "american", "rep", "state", "turn",
            "earth", "ridge", "projects", "simple", "eats", "test", "rein", "wikborg", "natix",
            "diet", "ideas", "affiliate", "support", "splash", "standard", "process", "campden",
            "bri", "robinson", "country", "solaray", "futureceuticals", "kyowa", "hakko", "euromed",
            "sofgen", "nutrivo", "balchem", "sabinsa", "kemin", "swanson", "ancient", "nordic",
            "naturals", "nutritional", "outlook", "now", "gencor", "nevada", "asphalt", "paving"
        }

        if any(w in non_person for w in lower_words):
            return None

        for w in words:
            w_clean = re.sub(r'[^a-zA-Z]', '', w)
            if len(w_clean) < 2 or not w[0].isupper():
                return None
            if re.search(r'\d', w):
                return None
            # Reject all-uppercase 2-letter tokens (e.g. 'ET', 'LT')
            if len(w_clean) == 2 and w_clean.isupper():
                return None

        return clean

    @staticmethod
    def clean_role_title(role: Optional[str]) -> Optional[str]:
        """Clean and validate that a string is a legitimate executive or job role title."""
        if not role or role.lower() in ("not extracted", "unknown", "?", "none", "", "former employee / alumni", "former employee", "alumni"):
            return None

        # Clean noise prefixes & numbers
        clean = re.sub(r'^(?:its\s+first|a\s+|an\s+|the\s+|our\s+|\d+\s+|former\s+|ex-\s*|past:?\s*|previously\s+)', '', role, flags=re.IGNORECASE).strip()
        # Strip trailing context and prepositional phrases
        clean = re.sub(r'\b(?:at|for|with|in|posted)\b.*$', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'\b(?:Good|Now|Foods|XYMOGEN|Ritual|Thorne|Solgar|Seed|PLT|Bio-Cat|Layn|Verdant|Health|Solutions|Ingredients|Gencor|Pharmavite)\b.*$', '', clean, flags=re.IGNORECASE).strip()
        # Strip noise trailing clauses like 'on a day', 'to create', 'to dig deeper', 'Circle', 'Optibio', 'into the tech world'
        clean = re.sub(r'\s+(?:on\s+a\s+day|to\s+create|to\s+dig\s+deeper|into\s+the\s+.*|Circle|Optibio|Views\s+are\s+my.*|1099|Remote)$', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'[^\w\s/&-]', '', clean).strip()
        clean = re.sub(r'\s+(?:of|and|&|for|at|the|a|an)$', '', clean, flags=re.IGNORECASE).strip()

        # Reject sentence snippets
        if any(v in clean.lower().split() for v in ("delivery", "complex", "paparazzi", "still", "little", "not", "new", "begins", "release", "partner")):
            if not any(v in clean.lower() for v in ("managing partner", "general partner", "business partner")):
                pass

        valid_role_words = {
            'chief', 'vp', 'president', 'director', 'manager', 'head', 'lead', 'officer',
            'scientist', 'chemist', 'specialist', 'engineer', 'coordinator', 'analyst',
            'executive', 'partner', 'advisor', 'consultant', 'associate', 'founder', 'buyer',
            'supervisor', 'technician', 'intern', 'planner', 'recruiter', 'svp', 'evp',
            'cfo', 'ceo', 'coo', 'cmo', 'cso', 'cto', 'development', 'sales', 'marketing',
            'regulatory', 'quality', 'operations', 'formulation', 'strategist', 'r&d', 'qa', 'ra',
            'counsel', 'retention', 'merchandising', 'procurement'
        }

        words = set(re.findall(r'\b[a-z]+\b', clean.lower()))
        if not (words & valid_role_words):
            return None

        if len(clean) < 3 or len(clean) > 55:
            return None

        # Normalize standard industry titles
        lower_clean = clean.lower()
        if lower_clean in ("chief oper", "chief op"):
            clean = "Chief Operating Officer"
        elif lower_clean in ("chief f", "chief fin"):
            clean = "Chief Financial Officer"
        elif lower_clean in ("chief market", "chief mark"):
            clean = "Chief Marketing Officer"
        elif "vp quality" in lower_clean and "regul" in lower_clean:
            clean = "VP of Quality & Regulatory"
        elif "director of oper" in lower_clean or lower_clean == "director oper":
            clean = "Director of Operations"
        elif "vice president of oper" in lower_clean:
            clean = "Vice President of Operations"
        elif lower_clean in ("vp f", "vp-f"):
            clean = "Vice President of Finance"
        elif lower_clean.endswith("director f"):
            clean = re.sub(r'\s+f$', ' of Formulation', clean, flags=re.IGNORECASE)
        elif lower_clean.startswith("director commercial"):
            clean = "Director of Commercial Strategy"

        return clean

    @staticmethod
    def extract_exec_name_title(title: str, snippet: str) -> tuple:
        """
        Heuristically extract the executive/employee name and title from article or LinkedIn post text.
        Returns (name, title) or (None, None) if not found.
        """
        combined = title + " " + snippet
        exec_name = None
        exec_title = None

        # 1. Profile headline: "Name - Title at Company" or "Name - Title | LinkedIn"
        m_prof = re.search(r'^([A-Z][A-Za-z\'-]+(?:\s+[A-Z][A-Za-z\'-]+){1,3})\s*[-–|]\s*([^–\-|@]+?)(?:\s+(?:at|@)\s+[^–\-|]+|\s*[-–|]|\s*$)', title)
        if m_prof:
            cand_n = SerperCollector.clean_person_name(m_prof.group(1).strip())
            cand_t = SerperCollector.clean_role_title(m_prof.group(2).strip())
            if cand_n and cand_t:
                exec_name = cand_n
                exec_title = cand_t

        # 2. Appointment headlines with "as/to": "Company Appoints/Names/Hires Name as Title"
        if not exec_name:
            m_app_as = re.search(r'(?:appoints?|names?|hires?|welcomes?|promotes?)\s+([A-Z][A-Za-z\'-]+(?:\s+[A-Z][A-Za-z\'-]+){1,2})\s+(?:as|to|as\s+its\s+new|as\s+new)\s+([A-Za-z/ &,-]{3,50}?)(?:\s*[-–|]|\s+for\b|\s+at\b|\s*$)', title, re.IGNORECASE)
            if m_app_as:
                cand_n = SerperCollector.clean_person_name(m_app_as.group(1).strip())
                cand_t = SerperCollector.clean_role_title(m_app_as.group(2).strip())
                if cand_n and cand_t:
                    exec_name = cand_n
                    exec_title = cand_t

        # 3. Direct appointment: "Company Appoints/Names/Hires Name Title"
        if not exec_name:
            m_app_dir = re.search(r'(?:appoints?|names?|hires?|welcomes?|promotes?)\s+([A-Z][A-Za-z\'-]+(?:\s+[A-Z][A-Za-z\'-]+){1,2})\s+((?:Chief|President|Vice President|VP|SVP|EVP|Director|Head|Manager|Lead|Scientist|Chemist)[A-Za-z/ &,-]{2,40}?)(?:\s*[-–|]|\s+for\b|\s+at\b|\s*$)', title, re.IGNORECASE)
            if m_app_dir:
                cand_n = SerperCollector.clean_person_name(m_app_dir.group(1).strip())
                cand_t = SerperCollector.clean_role_title(m_app_dir.group(2).strip())
                if cand_n and cand_t:
                    exec_name = cand_n
                    exec_title = cand_t

        # 4. Check LinkedIn post titles
        if not exec_name:
            m_post = re.search(r'([A-Z][A-Za-z\'-]+(?:\s+[A-Z][A-Za-z\'-]+){1,3})(?:,\s*[^’\']*)?[\'’]s?\s+Post', title)
            if not m_post:
                m_post = re.search(r'([A-Z][A-Za-z\'-]+(?:\s+[A-Z][A-Za-z\'-]+){1,3})(?:,\s*[^’\']*)?[\'’]s?\s+Post', snippet)
            m_post_on = re.search(r'([A-Z][A-Za-z\'-]+(?:\s+[A-Z][A-Za-z\'-]+){1,3})\s+on\s+LinkedIn', title)
            if m_post:
                exec_name = SerperCollector.clean_person_name(m_post.group(1).strip())
            elif m_post_on:
                exec_name = SerperCollector.clean_person_name(m_post_on.group(1).strip())

        # 5. General press patterns if name not yet found
        if not exec_name:
            name_patterns = [
                r'\b([A-Z][A-Za-z\'-]+ [A-Z][A-Za-z\'-]+)\b(?=\s+(?:joins|joined|appointed|appoints|named|names|leaves|steps|resigned|departed|hired|hires|promoted|promotes|started))',
                r'(?:appointed|appoints|named|names|hired|hires|joins|joined|welcomes|recruited)\s+([A-Z][A-Za-z\'-]+ [A-Z][A-Za-z\'-]+)',
            ]
            for pat in name_patterns:
                m = re.search(pat, combined, re.IGNORECASE)
                if m:
                    cand = m.group(1).strip()
                    if SerperCollector.clean_person_name(cand):
                        exec_name = cand
                        break
                    elif not exec_title and SerperCollector.clean_role_title(cand):
                        exec_title = SerperCollector.clean_role_title(cand)

        # Validate name
        exec_name = SerperCollector.clean_person_name(exec_name)

        # 6. Extract title from snippet if not yet found
        if not exec_title:
            role_cues = [
                r'(?:as|joined as|appointed as|started as|new role as|promoted to|hired as)\s+(?:a\s+|an\s+|the\s+)?([A-Za-z/ &]{3,40}?)(?:[!\.\,\;]|\sat\b|\sfor\b|\swith\b|\sto\b)',
                r'\b((?:Chief|VP|Vice President|SVP|EVP|President|Director|Head|Manager|Scientist|Chemist|Specialist|Lead|Engineer)\s+(?:of\s+)?[A-Za-z/ &]{2,35})\b',
            ]
            for pat in role_cues:
                m = re.search(pat, combined, re.IGNORECASE)
                if m:
                    candidate = m.group(1).strip() if m.groups() else m.group(0).strip()
                    exec_title = SerperCollector.clean_role_title(candidate)
                    if exec_title:
                        break

        exec_title = SerperCollector.clean_role_title(exec_title)
        return exec_name, exec_title

    @staticmethod
    def extract_name_from_url(url: str) -> Optional[str]:
        """Extract a clean person name from a LinkedIn profile or post URL."""
        if not url or "linkedin.com" not in url:
            return None
        try:
            m_in = re.search(r'linkedin\.com/in/([a-zA-Z0-9-]+)', url)
            m_post = re.search(r'linkedin\.com/posts/([a-zA-Z0-9-]+?)(?:_[a-z0-9-]+|-\d+)', url)
            slug = None
            if m_in:
                slug = m_in.group(1)
            elif m_post:
                slug = m_post.group(1)

            if slug:
                # Remove trailing hash or random alphanumeric strings
                clean_slug = re.sub(r'-[0-9a-fA-F]{5,}', '', slug)
                clean_slug = re.sub(r'-[0-9]{5,}', '', clean_slug)
                parts = clean_slug.split('-')
                if 2 <= len(parts) <= 4:
                    words = [p.capitalize() for p in parts if p.lower() not in ('phd', 'ms', 'mba', 'md', 'rd', 'rdn', 'dr', 'activity')]
                    if len(words) >= 2:
                        return ' '.join(words)
        except Exception:
            pass
        return None

    def get_key_personnel_signals(self, company_name: str, num: int = 6) -> List[dict]:
        """
        Extract verified active key functional decision makers & leadership contacts
        (Formulation/R&D, QA/RA, Operations/Supply Chain, Commercial/Sales, Executive).
        Provides rich baseline contact intelligence for SMBs where 90d turnover is 0.
        """
        queries = [
            f'"{company_name}" ("Director" OR "VP" OR "Head" OR "Scientist" OR "Manager" OR "Formulation" OR "Quality" OR "Regulatory" OR "Sales" OR "Operations") linkedin.com/in',
            f'"{company_name}" ("Chief" OR "President" OR "Director" OR "Scientist" OR "Quality" OR "Regulatory") site:linkedin.com',
            f'"{company_name}" leadership team "Director" OR "VP" OR "Head" OR "Scientist" supplement OR nutrition',
        ]

        found_contacts = []
        seen = set()

        for q in queries:
            items = self._search(q, endpoint="search", num=num, recency="qdr:y", filter_noise=False)
            for item in items:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                url = item.get("link", "") or item.get("url", "")

                name, role = self.extract_exec_name_title(title, snippet)
                if not name:
                    url_name = self.extract_name_from_url(url)
                    name = self.clean_person_name(url_name)

                name = self.clean_person_name(name)
                role = self.clean_role_title(role)

                if name and role:
                    key = f"{name.lower()}::{role.lower()}"
                    if key not in seen:
                        seen.add(key)
                        fn = self.classify_exec_function(title, snippet)
                        senior = self.is_senior_level(title, snippet)
                        found_contacts.append({
                            "person_name": name,
                            "role_title": role,
                            "function": fn,
                            "is_senior_level": senior,
                            "headline": title,
                            "source_url": url,
                        })
            if len(found_contacts) >= 4:
                break

        return found_contacts


    def _build_exec_event(self, item: dict) -> dict:
        """Build a structured exec event from a Serper result."""
        title   = item.get("title", "")
        snippet = item.get("snippet", "")
        date    = item.get("date", "")
        url     = item.get("link", "") or item.get("url", "")
        source  = item.get("source", "")

        is_valid, age_days, date_label = self.get_event_age_days(date, title + " " + snippet)

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
            "date":                  date_label or date,
            "age_days":              age_days,
            "recency_verified":      is_valid,
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

        # Deduplicate by URL and filter to past 3 months
        seen_urls = set()
        structured_events = []
        for item in raw_items:
            url = item.get("link", "")
            if url not in seen_urls:
                seen_urls.add(url)
                ev = self._build_exec_event(item)
                # Strict 3-month recency filter
                if not self.is_within_3_months(ev.get("date", ""), item.get("title", "") + " " + item.get("snippet", "")):
                    continue
                structured_events.append(ev)

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

    def get_role_change_signals(self, company_name: str, num: int = 8) -> List[dict]:
        """
        Detect role changes at ALL seniority levels using Google/Serper search with
        automatic DuckDuckGo + Google News RSS fallback.

        Strategy:
          Pass 1 — 3-month window (templates 1-4, strict recency)
          Pass 2 — 6-month window (ALL templates, if Pass 1 yields < 2 events)
                   Used for small/medium companies with low LinkedIn post frequency.
          Pass 3 — Unrestricted (if Pass 2 still yields 0, rare)

        Returns list of role-change event dicts (same schema as exec events).
        """
        raw_items = []
        seen_urls = set()

        # ---- Derive simplified domain for template 10 ----
        company_domain = (
            company_name.lower()
            .replace(" ", "")
            .replace("'", "")
            .replace(".", "")
            + ".com"
        )

        def _run_templates(templates, recency):
            """Run a subset of templates with a given recency and return raw items."""
            found = []
            for template in templates:
                try:
                    query = template.format(company=company_name,
                                           company_domain=company_domain)
                except KeyError:
                    query = template.replace("{company}", company_name)
                items = self._search(query, endpoint="search", num=num,
                                     recency=recency, filter_noise=False)
                if not items:
                    items = self._search(query, endpoint="news", num=num,
                                         recency=recency, filter_noise=False)
                for item in items:
                    url = item.get("link", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        found.append(item)
                if len(seen_urls) >= 10:
                    break
            return found

        # Pass 1 — original 4 templates, strict 3-month window
        raw_items = _run_templates(ROLE_CHANGE_QUERY_TEMPLATES[:4], "qdr:m3")

        # Pass 2 — all 12 templates, relaxed 6-month window (for low-signal companies)
        if len(raw_items) < 2:
            raw_items += _run_templates(ROLE_CHANGE_QUERY_TEMPLATES[4:], "qdr:m6")

        # Pass 3 — last resort: unrestricted for the first template only
        if not raw_items:
            raw_items = _run_templates(ROLE_CHANGE_QUERY_TEMPLATES[:2], "")

        events = []
        # Industry keywords or company name in snippet/title
        industry_anchors = [
            "supplement", "nutraceutical", "nutrition", "formulation", "ingredient",
            "regulatory", "quality", "r&d", "wellness", "vitamin", "probiotic",
            "dietary", "clinical", "botanica", "pharma", "manufacturing", "supply chain",
            "linkedin.com", company_name.lower(),
        ]
        for item in raw_items:
            title   = item.get("title", "")
            snippet = item.get("snippet", "")
            item_date = item.get("date", "")
            combined = (title + " " + snippet).lower()

            # Strict 3-month (90-day) ceiling enforcement
            is_valid, age_days, date_label = self.get_event_age_days(item_date, combined)
            if not is_valid:
                continue

            # Must mention a movement word
            movement_words = [
                "join", "hired", "appointed", "left", "depart", "resign",
                "promoted", "named", "steps down", "new role", "excited to", "happy to",
                "starting", "thrilled to", "position at", "transition", "moving on",
            ]
            if not any(mw in combined for mw in movement_words):
                continue

            # Must also mention nutra industry context or company
            if not any(anchor in combined for anchor in industry_anchors):
                continue

            # Build structured event
            direction  = self.classify_exec_direction(title, snippet)
            function   = self.classify_exec_function(title, snippet)
            senior     = self.is_senior_level(title, snippet)
            replaced   = self.detect_replacement(title, snippet)
            exec_name, exec_title = self.extract_exec_name_title(title, snippet)

            item_url = item.get("link", "") or item.get("url", "")
            if not exec_name:
                url_name = self.extract_name_from_url(item_url)
                exec_name = self.clean_person_name(url_name)

            # Seniority classification
            title_for_seniority = (exec_title or combined)
            seniority = "Mid-Level"
            for tier_name, kws in SENIORITY_TIERS:
                if any(kw in title_for_seniority.lower() for kw in kws):
                    seniority = tier_name
                    break

            events.append({
                "event_type":           "ROLE_CHANGE",
                "direction":            direction,
                "function":             function,
                "seniority":            seniority,
                "is_senior_level":      senior,
                "replacement_detected": replaced,
                "person_name":          exec_name or "Not extracted",
                "role_title":           exec_title or "Not extracted",
                "date":                 date_label or item_date,
                "age_days":             age_days,
                "recency_verified":     True,
                "headline":             title,
                "snippet":              snippet[:200],
                "source":               item.get("source", ""),
                "source_url":           item.get("link", "") or item.get("url", ""),
            })

        return events

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

        trade_press   = self.get_trade_press(company_name)
        time.sleep(delay)
        exec_signals  = self.get_executive_signals(company_name)
        time.sleep(delay)
        role_changes  = self.get_role_change_signals(company_name)
        time.sleep(delay)
        facility      = self.get_facility_expansion(company_name)
        time.sleep(delay)
        funding       = self.get_funding_ma(company_name)
        time.sleep(delay)
        regulatory    = self.get_regulatory_press(company_name)
        time.sleep(delay)
        ndi_signals   = self.get_ndi_signals(company_name)

        # Derived exec summaries for scoring
        arrivals   = [e for e in exec_signals if e.get("direction") == "ARRIVAL"]
        departures = [e for e in exec_signals if e.get("direction") == "DEPARTURE"]
        senior_moves = [e for e in exec_signals if e.get("is_senior_level")]
        unresolved_departures = [
            e for e in departures if not e.get("replacement_detected")
        ]

        # Role change summaries (all levels)
        rc_arrivals   = [e for e in role_changes if e.get("direction") == "ARRIVAL"]
        rc_departures = [e for e in role_changes if e.get("direction") == "DEPARTURE"]

        total_signals = (
            len(trade_press) + len(exec_signals) + len(role_changes) + len(facility)
            + len(funding) + len(regulatory) + len(ndi_signals)
        )
        print(
            f"  [OK] {total_signals} signals — "
            f"Exec: {len(exec_signals)} ({len(arrivals)}A/{len(departures)}D), "
            f"RoleChanges: {len(role_changes)} ({len(rc_arrivals)}A/{len(rc_departures)}D), "
            f"Facility: {len(facility)}, Funding: {len(funding)}, NDI: {len(ndi_signals)}"
        )

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
                "role_change_count":            len(role_changes),
                "role_change_arrivals":         len(rc_arrivals),
                "role_change_departures":       len(rc_departures),
                "facility_count":               len(facility),
                "funding_ma_count":             len(funding),
                "regulatory_count":             len(regulatory),
                "ndi_filing_count":             len(ndi_signals),
                "total_signals":                total_signals,
            },
            "signals": {
                "trade_press":          trade_press,
                "exec_appointments":    exec_signals,   # C-suite / VP level
                "role_changes":         role_changes,   # all levels
                "facility_expansion":   facility,
                "funding_ma":           funding,
                "regulatory_press":     regulatory,
                "ndi_filings":          ndi_signals,
            },
        }
