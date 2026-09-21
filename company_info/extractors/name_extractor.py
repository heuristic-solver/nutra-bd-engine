"""
name_extractor.py — Precision Human Name Extractor & Entity Filter
company_info / extractors
"""

from __future__ import annotations
import re
from typing import Optional, Set
from company_info.config import BUSINESS_ENTITY_TOKENS

# Normalized honorifics and degree suffixes (all dots removed for matching)
HONORIFICS = {
    "dr", "mr", "mrs", "ms", "prof", "phd", "md", "nd", "rph", "pharmd", "cfa", "cpa", "esq", "mba"
}

# Non-name verb, conjunction, and noise word blacklist
DISQUALIFIED_NAME_WORDS = {
    "appointed", "appoints", "named", "names", "joined", "joins", "started", "starts",
    "promoted", "promotes", "resigned", "resigns", "departs", "departed", "stepped", "steps",
    "announced", "announces", "leads", "heading", "welcomed", "welcoming", "hires", "hiring",
    "leaves", "leaving", "retired", "retires", "founded", "founders", "co-founder", "co-founders",
    "expanded", "expands", "acquired", "acquires", "invests", "invested", "raises", "raised",
    "the", "a", "an", "and", "or", "to", "for", "with", "at", "in", "on", "by", "from", "of", "as",
    "senior", "junior", "chief", "officer", "vice", "president", "director", "manager", "lead",
    "head", "specialist", "executive", "team", "board", "member", "advisor", "alumni", "employee",
    "today", "yesterday", "tomorrow", "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december", "monday", "tuesday",
    "wednesday", "thursday", "friday", "saturday", "sunday", "annual", "quarterly", "global",
    "housing", "heavy", "hitter", "veteran", "industry", "pharma", "biotech", "expert", "leader",
    "pioneer", "insider", "analyst", "longtime", "former", "interim", "designated", "incoming",
    "outgoing", "seasoned", "experienced", "parachuted", "tapped", "picked", "selected",
    "new", "ceo", "cfo", "coo", "cto", "cmo", "cso", "vp", "gm", "svp", "evp"
}


def clean_person_name(raw_name: str, target_company: Optional[str] = None) -> Optional[str]:
    """
    Sanitizes and validates a candidate person name string.
    Returns None if the string is an entity, company, sentence fragment, or invalid.
    """
    if not raw_name or not isinstance(raw_name, str):
        return None

    # 1. Clean HTML, punctuation artifacts, pipes, hyphens
    cleaned = re.sub(r'[\r\n\t]+', ' ', raw_name)
    cleaned = re.sub(r'\s*[-–|/\\•·]\s*.*$', '', cleaned) # Cut off after role separator
    cleaned = re.sub(r'[^\w\s\.\'\-]', '', cleaned).strip()

    # 2. Tokenize
    raw_tokens = [t for t in cleaned.split() if t]
    if len(raw_tokens) < 2 or len(raw_tokens) > 5:
        return None

    # 3. Strip leading honorifics and descriptors
    while raw_tokens and (raw_tokens[0].lower().replace(".", "").strip("'-") in HONORIFICS or raw_tokens[0].lower() in DISQUALIFIED_NAME_WORDS):
        raw_tokens.pop(0)

    # 4. Strip trailing degrees/suffixes
    while raw_tokens and raw_tokens[-1].lower().replace(".", "").strip("'-") in HONORIFICS:
        raw_tokens.pop()

    # 5. Strip trailing connective words like "as", "at", "for"
    while raw_tokens and raw_tokens[-1].lower() in {"as", "at", "to", "for", "in", "on", "of", "and"}:
        raw_tokens.pop()

    if len(raw_tokens) < 2 or len(raw_tokens) > 3:
        return None

    # 6. Check each token against blacklists
    normalized_tokens = []
    for t in raw_tokens:
        t_clean = t.replace(".", "").strip("'-")
        t_low = t_clean.lower()

        if len(t_clean) < 2:
            return None
        if not t_clean.isalpha():
            return None
        if t_low in BUSINESS_ENTITY_TOKENS:
            return None
        if t_low in DISQUALIFIED_NAME_WORDS:
            return None

        # Proper capitalisation check
        normalized_tokens.append(t_clean.capitalize())

    # 7. Check company name substring collision
    full_name = " ".join(normalized_tokens)
    if target_company:
        co_clean = re.sub(r'[^\w\s]', '', target_company).lower()
        co_words = set(co_clean.split())
        name_words = {t.lower() for t in normalized_tokens}
        # If the name shares words with the company name (e.g. "Standard Process", "Lief Labs") -> reject
        if len(co_words.intersection(name_words)) > 0:
            return None

    return full_name


def extract_person_name_from_headline(headline: str, company_name: str) -> Optional[str]:
    """
    Extracts a human name from press release headlines with leading descriptor removal.
    """
    if not headline:
        return None

    # Strip common leading headline descriptors (e.g. "Industry Veteran", "Former FDA Official", "CDMO Vet")
    h_clean = re.sub(r'^(?:Industry\s+Veteran|Former\s+[A-Za-z\s]+|CDMO\s+Vet|Pharma\s+Executive|Housing\s+Heavy\s+Hitter|Veteran\s+Leader)\s+', '', headline, flags=re.IGNORECASE)

    # Pattern A: Company Appoints/Names [Name] as/to [Role]
    m_a = re.search(r'(?:Appoints?|Names?|Welcomes?|Hires?|Taps?|Promotes?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}?)\s+(?:as\b|to\b|for\b|Chief\b|VP\b|Vice\b|Director\b|President\b|as the\b)', h_clean, re.IGNORECASE)
    if m_a:
        candidate = m_a.group(1).strip()
        cleaned = clean_person_name(candidate, company_name)
        if cleaned:
            return cleaned

    # Pattern B: [Name] Appointed/Named/Joins as [Role]
    m_b = re.search(r'(?:^|[,\-\–]\s*)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}?)\s+(?:Appointed|Named|Joins?|Promoted|Steps Down|Resigns?|Departed|Leaves?)\s+(?:as\b|to\b|Chief\b|VP\b|CEO\b|CFO\b|COO\b|President\b|Director\b|from\b|at\b)', h_clean, re.IGNORECASE)
    if m_b:
        candidate = m_b.group(1).strip()
        cleaned = clean_person_name(candidate, company_name)
        if cleaned:
            return cleaned

    # Pattern C: [Role] [Name] steps down / joins
    m_c = re.search(r'(?:CEO|CFO|COO|President|Founder|Director)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}?)\s+(?:steps down|resigns|departs|joins|appointed)', h_clean, re.IGNORECASE)
    if m_c:
        candidate = m_c.group(1).strip()
        cleaned = clean_person_name(candidate, company_name)
        if cleaned:
            return cleaned

    return None
