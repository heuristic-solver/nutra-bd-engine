"""
kb_loader.py — Nutraceutical Knowledge Base Loader & Query Manager
company_info / pipeline
"""

from __future__ import annotations
import os
import json
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

from company_info.models.company import CompanyProfile

DEFAULT_KB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "nutraceutical_kb.json"))


class NutraceuticalKBLoader:
    """
    Manager and query index for the 1,022 companies in nutraceutical_kb.json.
    """

    def __init__(self, kb_path: str = DEFAULT_KB_PATH):
        self.kb_path = kb_path
        self._companies: List[CompanyProfile] = []
        self._name_index: Dict[str, CompanyProfile] = {}
        self._domain_index: Dict[str, CompanyProfile] = {}
        self._load_kb()

    def _load_kb(self) -> None:
        """Loads and indexes the JSON knowledge base."""
        if not os.path.exists(self.kb_path):
            return

        try:
            with open(self.kb_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            records = data if isinstance(data, list) else list(data.values())
            for item in records:
                if not isinstance(item, dict):
                    continue
                try:
                    profile = CompanyProfile.from_kb_dict(item)
                    self._companies.append(profile)

                    # Index by lowercase name
                    self._name_index[profile.company_name.lower()] = profile

                    # Index by domain
                    if profile.domain:
                        self._domain_index[profile.domain.lower()] = profile
                except Exception:
                    continue

        except Exception as e:
            print(f"Error loading nutraceutical KB from {self.kb_path}: {e}")

    @property
    def total_count(self) -> int:
        return len(self._companies)

    def get_all(self) -> List[CompanyProfile]:
        """Returns all loaded company profiles."""
        return list(self._companies)

    def find_by_name(self, name: str) -> Optional[CompanyProfile]:
        """
        Looks up a company by exact name, substring, or fuzzy similarity match.
        """
        if not name:
            return None

        clean_name = name.strip().lower()

        # 1. Exact match
        if clean_name in self._name_index:
            return self._name_index[clean_name]

        # 2. Substring match
        for k, v in self._name_index.items():
            if clean_name in k or k in clean_name:
                return v

        # 3. Domain match
        for d, v in self._domain_index.items():
            if clean_name in d:
                return v

        # 4. Fuzzy match (>0.75 ratio)
        best_ratio = 0.0
        best_match = None
        for k, v in self._name_index.items():
            ratio = SequenceMatcher(None, clean_name, k).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = v

        if best_ratio >= 0.75:
            return best_match

        return None

    def filter_by_segment(self, segment_key: str) -> List[CompanyProfile]:
        """
        Filters companies by segment key:
          'supplement_brand', 'contract_manufacturer', 'ingredient_supplier',
          'packaging', 'testing_cro_consulting'
        """
        results = []
        for c in self._companies:
            if c.segments.get(segment_key) is True:
                results.append(c)
        return results

    def filter_by_specialty(self, specialty_query: str) -> List[CompanyProfile]:
        """Filters companies by specialty substring."""
        q = specialty_query.lower()
        return [c for c in self._companies if c.specialty and q in c.specialty.lower()]

    def filter_by_ingredient(self, ingredient_name: str) -> List[CompanyProfile]:
        """Filters companies supplying or utilizing a specific ingredient."""
        q = ingredient_name.lower()
        results = []
        for c in self._companies:
            all_ing = [i.lower() for i in c.key_ingredients + c.branded_ingredients]
            if any(q in ing for ing in all_ing):
                results.append(c)
        return results

    def get_top_cohort(self, limit: int = 50) -> List[CompanyProfile]:
        """Returns a curated cohort of prominent companies with valid websites."""
        valid_cos = [c for c in self._companies if c.domain and c.company_name]
        return valid_cos[:limit]


# Global singleton instance
_kb_loader: Optional[NutraceuticalKBLoader] = None


def get_kb_loader() -> NutraceuticalKBLoader:
    global _kb_loader
    if _kb_loader is None:
        _kb_loader = NutraceuticalKBLoader()
    return _kb_loader
