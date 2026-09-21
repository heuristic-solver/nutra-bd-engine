"""
json_exporter.py — JSON Exporter
company_info / exporters
"""

from __future__ import annotations
import json
from typing import List
from company_info.models.report import CompanyIntelligenceReport


class JSONExporter:
    """Exports intelligence reports to JSON."""

    @staticmethod
    def export(reports: List[CompanyIntelligenceReport], filepath: str) -> None:
        data = [r.model_dump(mode="json") for r in reports]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
