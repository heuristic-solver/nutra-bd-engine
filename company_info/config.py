"""
config.py — Central Configuration & Settings
company_info
"""

import os
from typing import List, Dict, Any

# Random User-Agent Rotation Pool
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
]

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": USER_AGENTS[0],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

SEC_EDGAR_HEADERS: Dict[str, str] = {
    "User-Agent": "NutraceuticalResearchCorp contact@nutraengine-research.org",
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov",
}

# Concurrency & Networking Defaults
DEFAULT_TIMEOUT_SEC: int = 12
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_CONCURRENCY: int = 5
RATE_LIMIT_DELAY_SEC: float = 1.0

# Noise / Blacklisted Entity Tokens (Prevent false person names)
BUSINESS_ENTITY_TOKENS: set = {
    "inc", "inc.", "llc", "corp", "corp.", "corporation", "ltd", "ltd.", "llp", "gmbh", "ag", "sa", "bv", "nv", "plc",
    "co", "co.", "company", "group", "holdings", "enterprises", "brands", "labs",
    "laboratories", "solutions", "nutrition", "nutraceuticals", "pharma", "pharmaceuticals",
    "bioscience", "biosciences", "health", "healthcare", "wellness", "therapeutics", "biotech",
    "technologies", "tech", "global", "international", "usa", "americas", "europe", "asia",
    "press", "release", "news", "newswire", "businesswire", "globenewswire", "pr", "media",
    "market", "markets", "insider", "report", "review", "journal", "digest", "times",
    "standard", "process", "advanced", "express", "simple", "eats", "campden", "bri",
    "alumni", "employee", "former", "executive", "team", "board", "leadership", "staff",
    "capital", "partners", "ventures", "equity", "management", "investments", "advisors",
    "associates", "innovations", "specialties", "natural", "products", "ingredients",
    "consulting", "analytics", "industries", "council", "alliance", "association",
    "foundation", "institute", "center", "services", "manufacturing", "logistics", "supply",
}

# Industry News Feeds (Open RSS)
INDUSTRY_RSS_FEEDS: List[Dict[str, str]] = [
    {"name": "NutraIngredients", "url": "https://www.nutraingredients.com/Info/RSS"},
    {"name": "Nutraceuticals World", "url": "https://www.nutraceuticalsworld.com/rss"},
    {"name": "Natural Products Insider", "url": "https://www.naturalproductsinsider.com/rss.xml"},
    {"name": "PR Newswire Health", "url": "https://www.prnewswire.com/rss/health-latest-news/health-latest-news-list.rss"},
    {"name": "GlobeNewswire Healthcare", "url": "https://www.globenewswire.com/RssFeed/industry/4370-Pharmaceuticals%2C%20Biotechnology%20%26%20Life%20Sciences/feedTitle/GlobeNewswire%20-%20Industry%20News"},
]
