"""
funding_parser.py — Funding Round, Capital, & Investor Parser
company_info / extractors
"""

from __future__ import annotations
import re
from typing import Optional, List, Tuple
from company_info.models.funding import FundingRoundType, FundingEvent


def parse_funding_amount(text: str) -> Tuple[Optional[str], Optional[float]]:
    """
    Extracts raw funding amount string and normalized USD numeric value.
    Example:
      '$25 million' -> ('$25M', 25000000.0)
      '$1.5B' -> ('$1.5B', 1500000000.0)
      '€10M' -> ('€10M', 10800000.0) # with approximate conversion
    """
    if not text:
        return None, None

    t_low = text.lower()
    # Filter out equity research price targets, EPS, and stock market noise
    if any(pt in t_low for pt in ["price target", "target price", "pt raised", "pt lowered", "per share", "/share", "pts per share", "fair value", "price objective"]):
        return None, None

    # Match currency patterns
    # Pattern 1: $X million/billion/M/B/k
    m = re.search(r'([$€£¥])\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|thousand|bn|m|b|k)?\b', text, re.IGNORECASE)
    if m:
        symbol = m.group(1)
        val_str = m.group(2)
        unit = (m.group(3) or "").lower()

        try:
            val = float(val_str)
            multiplier = 1.0

            if unit in ("billion", "b", "bn"):
                multiplier = 1_000_000_000.0
                raw = f"{symbol}{val_str}B"
            elif unit in ("million", "m"):
                multiplier = 1_000_000.0
                raw = f"{symbol}{val_str}M"
            elif unit in ("thousand", "k"):
                multiplier = 1_000.0
                raw = f"{symbol}{val_str}K"
            else:
                if val < 50_000:
                    # Ignore small dollar amounts without M/B/K unit (e.g. stock prices, product prices)
                    return None, None
                if val >= 1_000_000:
                    raw = f"{symbol}{val/1_000_000:.1f}M"
                else:
                    raw = f"{symbol}{val:,.0f}"

            amount_usd = val * multiplier
            # Approximate currency conversions
            if symbol == "€":
                amount_usd *= 1.08
            elif symbol == "£":
                amount_usd *= 1.28

            return raw, amount_usd
        except ValueError:
            pass

    return None, None


def classify_round_type(text: str) -> FundingRoundType:
    """
    Classifies the round type from context text or headline.
    """
    if not text:
        return FundingRoundType.UNDISCLOSED

    t_low = text.lower()

    if "pre-seed" in t_low:
        return FundingRoundType.PRE_SEED
    if "seed" in t_low and "round" in t_low:
        return FundingRoundType.SEED
    if "series a" in t_low:
        return FundingRoundType.SERIES_A
    if "series b" in t_low:
        return FundingRoundType.SERIES_B
    if "series c" in t_low:
        return FundingRoundType.SERIES_C
    if any(s in t_low for s in ["series d", "series e", "series f"]):
        return FundingRoundType.SERIES_D_PLUS
    if "growth equity" in t_low or "growth capital" in t_low:
        return FundingRoundType.GROWTH_EQUITY
    if any(pe in t_low for pe in ["private equity", "majority investment", "acquired majority", "buyout"]):
        return FundingRoundType.PRIVATE_EQUITY
    if any(d in t_low for d in ["debt financing", "credit facility", "term loan"]):
        return FundingRoundType.DEBT_FINANCING
    if "grant" in t_low or "nih grant" in t_low or "sbir" in t_low:
        return FundingRoundType.GRANT
    if "strategic investment" in t_low or "minority stake" in t_low:
        return FundingRoundType.STRATEGIC_INVESTMENT

    return FundingRoundType.UNDISCLOSED


def extract_investors(text: str) -> Tuple[List[str], List[str]]:
    """
    Extracts lead investors and participating investors from text.
    """
    lead_investors = []
    participating = []

    if not text:
        return lead_investors, participating

    # Lead investor pattern: led by [Investor]
    m_lead = re.search(r'\bled by\s+([A-Z][A-Za-z0-9\s&,\.\'\-]+?)(?:\s+with|\s+and|\s+alongside|\.|\,|$)', text)
    if m_lead:
        inv = m_lead.group(1).strip(" .,-")
        if len(inv) > 2 and len(inv) < 50 and not any(w in inv.lower() for w in ["the company", "ceo", "cfo"]):
            lead_investors.append(inv)

    # Participating investor pattern: participation from / joined by [Investors]
    m_part = re.search(r'\b(?:participation from|joined by|backed by|including)\s+([A-Z][A-Za-z0-9\s&,\.\'\-]+?)(?:\.|\;|$)', text)
    if m_part:
        invs = m_part.group(1).split(",")
        for i in invs:
            i_clean = i.replace(" and ", "").strip(" .,-")
            if len(i_clean) > 2 and len(i_clean) < 50 and not any(w in i_clean.lower() for w in ["the company", "existing"]):
                if i_clean not in lead_investors:
                    participating.append(i_clean)

    return lead_investors, participating


def extract_valuation(text: str) -> Optional[str]:
    """Extracts valuation string if present (e.g. '$250 Million Valuation')."""
    if not text:
        return None

    m = re.search(r'([$€£][0-9]+(?:\.[0-9]+)?\s*(?:billion|million|B|M)?\s+valuation)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None
