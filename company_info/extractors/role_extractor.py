"""
role_extractor.py — Functional Role Title Extractor & Normalizer
company_info / extractors
"""

from __future__ import annotations
import re
from typing import Optional

VALID_ROLE_KEYWORDS = {
    "chief", "ceo", "cfo", "coo", "cto", "cmo", "cso", "cbo", "cro", "cpo", "cio", "cco",
    "officer", "president", "founder", "co-founder", "partner", "principal", "managing",
    "vice", "vp", "evp", "svp", "avp", "director", "head", "lead", "manager", "specialist",
    "scientist", "formulator", "chemist", "biochemist", "toxicologist", "microbiologist",
    "engineer", "technologist", "operator", "supervisor", "coordinator", "analyst",
    "regulatory", "compliance", "quality", "qa", "qc", "rd", "r&d", "operations", "supply",
    "manufacturing", "production", "formulation", "commercial", "sales", "marketing",
    "business", "development", "procurement", "sourcing", "logistics", "account",
}

ROLE_NORMALIZATIONS = {
    r"\bchief executive officer\b": "Chief Executive Officer (CEO)",
    r"\bchief financial officer\b": "Chief Financial Officer (CFO)",
    r"\bchief operating officer\b": "Chief Operating Officer (COO)",
    r"\bchief commercial officer\b": "Chief Commercial Officer (CCO)",
    r"\bchief scientific officer\b": "Chief Scientific Officer (CSO)",
    r"\bchief marketing officer\b": "Chief Marketing Officer (CMO)",
    r"\bchief technology officer\b": "Chief Technology Officer (CTO)",
    r"\bchief business officer\b": "Chief Business Officer (CBO)",
    r"\bexecutive vice president\b": "Executive Vice President",
    r"\bsenior vice president\b": "Senior Vice President",
    r"\bvp\b": "Vice President",
    r"\bsvp\b": "Senior Vice President",
    r"\bevp\b": "Executive Vice President",
    r"\br&d\b": "R&D",
    r"\bqa/qc\b": "QA/QC",
}

NOISE_SUFFIXES = [
    r'\s+on a day.*$',
    r'\s+to create.*$',
    r'\s+to dig deeper.*$',
    r'\s+into the tech.*$',
    r'\s+in the.*$',
    r'\s+at.*$',
    r'\s+for.*$',
    r'\s+with.*$',
    r'\s+by.*$',
    r'\s+from.*$',
    r'\s+[-–|/\\•·].*$',
]


def clean_role_title(raw_role: str, person_name: Optional[str] = None) -> Optional[str]:
    """
    Cleans, normalizes, and validates a role title string.
    """
    if not raw_role or not isinstance(raw_role, str):
        return None

    role = raw_role.strip()

    # 1. Remove duplicate person name prefix if present
    if person_name:
        for name_token in person_name.split():
            if len(name_token) > 2:
                role = re.sub(rf'^{re.escape(name_token)}\b\s*', '', role, flags=re.IGNORECASE)

    # 2. Strip leading preposition/article noise ("as", "to", "the", "new", "as the", "appointed as", "its", "as its")
    role = re.sub(r'^(?:as\s+its|as\s+the|appointed\s+as|named\s+as|promoted\s+to|its\s+new|its|as|to|the|new)\s+', '', role, flags=re.IGNORECASE).strip()

    # 3. Strip noise suffixes
    for pattern in NOISE_SUFFIXES:
        role = re.sub(pattern, '', role, flags=re.IGNORECASE).strip()

    # 4. Clean punctuation
    role = re.sub(r'^[,\-–|:\s]+|[,\-–|:\s]+$', '', role).strip()

    if len(role) < 3 or len(role) > 85:
        return None

    # 5. Check tokens & reject incomplete trailing initials/cutoffs (e.g. "Chief F", "Chief Oper")
    tokens = [t.lower().strip(".,/-()'") for t in role.split() if t]
    if not tokens:
        return None

    # If the last token is a single letter and not a known valid suffix -> reject fragment
    if len(tokens[-1]) == 1 and tokens[-1] not in {"a", "i"}:
        return None

    # If trailing token is truncated like "oper" -> expand if follows "chief"
    if tokens[-1] == "oper" and len(tokens) >= 2:
        role = re.sub(r'\boper\b', 'Operating Officer (COO)', role, flags=re.IGNORECASE)
    elif tokens[-1] == "exec" and len(tokens) >= 2:
        role = re.sub(r'\bexec\b', 'Executive Officer (CEO)', role, flags=re.IGNORECASE)

    has_valid_keyword = any(t in VALID_ROLE_KEYWORDS for t in tokens)
    if not has_valid_keyword:
        return None

    # 6. Apply standard title casing & normalizations
    for pattern, replacement in ROLE_NORMALIZATIONS.items():
        role = re.sub(pattern, replacement, role, flags=re.IGNORECASE)

    # Capitalize title words cleanly while preserving acronyms in parentheses
    words = role.split()
    capitalized_words = []
    acronym_set = {"CEO", "CFO", "COO", "CTO", "CMO", "CSO", "CBO", "CRO", "CCO", "CPO", "CIO", "VP", "SVP", "EVP", "R&D", "QA", "QC", "QA/QC"}

    for w in words:
        clean_w = w.strip("()")
        if clean_w.upper() in acronym_set:
            if w.startswith("(") and w.endswith(")"):
                capitalized_words.append(f"({clean_w.upper()})")
            else:
                capitalized_words.append(clean_w.upper())
        elif w.lower() in {"and", "of", "the", "in", "for", "to"}:
            capitalized_words.append(w.lower())
        else:
            capitalized_words.append(w.capitalize())

    return " ".join(capitalized_words)


def extract_role_from_text(text: str, person_name: Optional[str] = None) -> Optional[str]:
    """
    Extracts a role title from a snippet, headline, or text passage.
    """
    if not text:
        return None

    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text).strip()

    # Pattern A: named/appointed/as [Role]
    m_as = re.search(r'\b(?:named\s+as|named|appointed\s+as|appointed|promoted\s+to|as\s+the\s+new|as\s+new|as|to\s+the\s+role\s+of|tapped\s+as|hired\s+as|to\s+head|to\s+lead)\s+([A-Za-z\s/&\-]{2,70}?)(?:\b(?:at|for|in|with|of|to|from)\b|\.|\,|$|\(|\)|[-–|])', text, re.IGNORECASE)
    if m_as:
        candidate = m_as.group(1).strip()
        cleaned = clean_role_title(candidate, person_name)
        if cleaned:
            return cleaned

    # Pattern B: [Name], [Role] at [Company]
    if person_name:
        m_name_role = re.search(rf'{re.escape(person_name)}[,\s\-–|]+([A-Za-z\s/&\-]{3,70}?)(?:\b(?:at|for|with|of|in|to|from)\b|\.|\,|$|\(|\)|[-–|])', text, re.IGNORECASE)
        if m_name_role:
            candidate = m_name_role.group(1).strip()
            cleaned = clean_role_title(candidate, person_name)
            if cleaned:
                return cleaned

    # Pattern C: Standard executive title regex
    m_title = re.search(r'\b(Executive Vice President and Chief [A-Za-z]+ Officer|Senior Vice President and Chief [A-Za-z]+ Officer|Chief [A-Za-z]+ Officer|Chief Executive Officer|Chief Operating Officer|Chief Financial Officer|Chief Scientific Officer|Chief Commercial Officer|Chief Marketing Officer|Chief Technology Officer|President|Executive Vice President|Senior Vice President|Vice President of [A-Za-z\s]+|VP of [A-Za-z\s]+|Director of [A-Za-z\s]+|Head of [A-Za-z\s]+|Head|Senior [A-Za-z\s]+ Scientist|Formulation Scientist|Plant Manager|Marketing Manager|CEO|CFO|COO|CTO|CMO|CSO|CRO|CCO)\b', text, re.IGNORECASE)
    if m_title:
        candidate = m_title.group(1).strip()
        cleaned = clean_role_title(candidate, person_name)
        if cleaned:
            return cleaned

    return None
