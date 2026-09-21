"""
movement_classifier.py — Strategic & Personnel Movement Classifier
company_info / extractors
"""

from __future__ import annotations
import re
from typing import Optional
from company_info.models.role_change import MovementType
from company_info.models.movement import MovementCategory


# Pattern definitions for role change movements
JOINED_PATTERNS = [
    r'\b(?:appointed|appoints|named|names|hired|hires|welcomed|welcomes|taps|joins|joined|started as|new role as|thrilled to join|excited to start)\b',
    r'\bwelcoming\s+[A-Z][a-z]+\s+as\b',
    r'\bnew (?:CEO|CFO|COO|CTO|CMO|CCO|President|Director|VP)\b',
]

DEPARTED_PATTERNS = [
    r'\b(?:steps down|stepped down|resigns|resigned|leaves|left|departs|departed|stepping down|leaving|transitioning out|exits|exited|farewell|last day at|moving on from)\b',
    r'\b(?:ex-|former|previously at|former employee|former executive)\b',
]

PROMOTED_PATTERNS = [
    r'\b(?:promoted to|promotes|elevation to|named new|internal promotion|elevated to)\b',
]

BOARD_PATTERNS = [
    r'\b(?:board of directors|advisory board|appointed to board|joins board|board member|director on board)\b',
]


def classify_person_movement(text: str) -> Optional[MovementType]:
    """
    Determines whether a text passage describes a person joining, departing, being promoted, or joining the board.
    """
    if not text:
        return None

    t_low = text.lower()

    # 1. Board appointment
    if any(re.search(p, t_low) for p in BOARD_PATTERNS):
        return MovementType.BOARD_APPOINTMENT

    # 2. Promotion
    if any(re.search(p, t_low) for p in PROMOTED_PATTERNS):
        return MovementType.PROMOTED

    # 3. Departure / Resignation
    if any(re.search(p, t_low) for p in DEPARTED_PATTERNS):
        return MovementType.DEPARTED

    # 4. Joined / New Hire / Appointment
    if any(re.search(p, t_low) for p in JOINED_PATTERNS):
        return MovementType.JOINED

    return None


def classify_strategic_movement(text: str) -> Optional[MovementCategory]:
    """
    Categorizes a corporate strategic milestone or event.
    """
    if not text:
        return None

    t_low = text.lower()

    # 1. Rebranding / Spinout
    if any(re.search(r'\b(?:rebrands to|rebranding|spins out|spinout|new identity|formerly known as|name change|rebranded as)\b', t_low) for _ in [1]):
        return MovementCategory.REBRANDING

    # 2. M&A / Buyouts / Divestments
    if any(re.search(r'\b(?:acquired|acquires|acquisition|merger|merges|bought|buyout|takeover|all-cash transaction|sale of|purchased|purchases|divestment|divests)\b', t_low) for _ in [1]):
        return MovementCategory.MERGER_ACQUISITION

    # 3. Facility & Manufacturing Expansion / Capital Investment
    if any(re.search(r'\b(?:expands facility|new facility|opens plant|manufacturing expansion|new warehouse|lab expansion|capacity buildout|expanded capacity|breaks ground|expands manufacturing|invests in facility|facility investment|expansion in|new production line|new site|plant expansion)\b', t_low) for _ in [1]) or re.search(r'\binvest\w*\s+(?:\$\d+|\d+\s*million|in)\b.*\b(?:facility|plant|manufacturing|expansion)\b', t_low):
        return MovementCategory.FACILITY_EXPANSION

    # 4. Strategic Partnership, Distribution & Licensing
    if any(re.search(r'\b(?:partnership with|strategic alliance|joint venture|licensing agreement|distribution deal|collaborates with|distribution partnership|partners with|commercial agreement|co-development|distributor for|exclusive distribution)\b', t_low) for _ in [1]) or re.search(r'\bappoints\s+.*\s+for\s+(?:north america|europe|asia|southeast asia|global|latam|emea|us|sales|distribution)\b', t_low):
        return MovementCategory.STRATEGIC_PARTNERSHIP

    # 5. Product Launch, Formulation Solution & Clinical Science
    if any(re.search(r'\b(?:launches|launch of|introducing new|introduces|unveils|debuts|rollout|new ingredient|line expansion|clinical trial results|published study|patent awarded|patent granted|branded ingredient|clinical study|novel ingredient|new formulation|unveil)\b', t_low) for _ in [1]) or re.search(r'\b\w+\s+solution\s*[-–|]\s*', t_low):
        return MovementCategory.PRODUCT_LAUNCH

    # 6. Regulatory Milestone
    if any(re.search(r'\b(?:fda clearance|gras status|gras notification|usp certified|regulatory approval|novel food approval|efsa opinion|tga approval|health canada npn|patent approved)\b', t_low) for _ in [1]):
        return MovementCategory.REGULATORY_MILESTONE

    # 7. Restructuring & Layoffs
    if any(re.search(r'\b(?:layoffs|restructuring|downsizing|workforce reduction|closing facility|operations streamlined|cost reduction|closing plant)\b', t_low) for _ in [1]):
        return MovementCategory.RESTRUCTURING

    return None
