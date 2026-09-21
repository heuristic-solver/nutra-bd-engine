"""
company_info / extractors package
"""

from company_info.extractors.name_extractor import clean_person_name, extract_person_name_from_headline
from company_info.extractors.role_extractor import clean_role_title, extract_role_from_text
from company_info.extractors.funding_parser import (
    parse_funding_amount,
    classify_round_type,
    extract_investors,
    extract_valuation,
)
from company_info.extractors.movement_classifier import (
    classify_person_movement,
    classify_strategic_movement,
)

__all__ = [
    "clean_person_name",
    "extract_person_name_from_headline",
    "clean_role_title",
    "extract_role_from_text",
    "parse_funding_amount",
    "classify_round_type",
    "extract_investors",
    "extract_valuation",
    "classify_person_movement",
    "classify_strategic_movement",
]
