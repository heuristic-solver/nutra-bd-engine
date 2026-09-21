"""
csv_exporter.py — Segregated CSV Exporters
company_info / exporters
"""

from __future__ import annotations
import csv
from typing import List
from company_info.models.report import CompanyIntelligenceReport


import re


def _sanitize_dict(d: dict) -> dict:
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, str):
            # Strip well-formed HTML tags
            v_clean = re.sub(r'<[^>]+>', ' ', v)
            # Strip unclosed / truncated HTML tags like <a href="...
            v_clean = re.sub(r'<[a-zA-Z\/][^>]*$', ' ', v_clean)
            # Collapse multiple spaces
            v_clean = re.sub(r'\s+', ' ', v_clean).strip()
            cleaned[k] = v_clean
        else:
            cleaned[k] = v
    return cleaned


class CSVExporter:
    """
    Exports company intelligence reports into clean, segregated CSV datasets.
    """

    @staticmethod
    def export_master_summary(reports: List[CompanyIntelligenceReport], filepath: str) -> None:
        """
        Exports master company intelligence overview (1 row per company).
        """
        fieldnames = [
            "company_name",
            "domain",
            "headquarters",
            "specialty",
            "joined_count",
            "joined_people",
            "departed_count",
            "departed_people",
            "target_hiring_functions",
            "mapped_target_roles",
            "recruitment_intelligence",
            "funding_rounds_count",
            "funding_history",
            "total_funding_est_usd",
            "strategic_movements_count",
            "strategic_movements",
            "sources_scraped",
            "scan_timestamp",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in reports:
                writer.writerow(_sanitize_dict(r.to_summary_dict()))

    @staticmethod
    def export_role_targets(reports: List[CompanyIntelligenceReport], filepath: str) -> None:
        """
        Exports granular organizational role targets and functional hiring mappings across all companies.
        """
        fieldnames = [
            "company_name",
            "domain",
            "headquarters",
            "specialty",
            "target_role_title",
            "hiring_functions",
            "recruitment_intelligence",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in reports:
                roles = r.mapped_target_roles if r.mapped_target_roles else ["General Operational / Technical Specialist"]
                for role_title in roles:
                    row = {
                        "company_name": r.company_name,
                        "domain": r.domain or "",
                        "headquarters": r.profile.headquarters or "",
                        "specialty": r.profile.specialty or "",
                        "target_role_title": role_title,
                        "hiring_functions": ", ".join(r.target_hiring_functions) if r.target_hiring_functions else "",
                        "recruitment_intelligence": r.recruitment_intelligence or "",
                    }
                    writer.writerow(_sanitize_dict(row))

    @staticmethod
    def export_role_changes(reports: List[CompanyIntelligenceReport], filepath: str) -> None:
        """
        Exports detailed role change and personnel movement event logs.
        """
        fieldnames = [
            "person_name",
            "company_name",
            "movement_type",
            "role_title",
            "previous_role",
            "department",
            "date",
            "evidence",
            "source_url",
            "source_name",
            "confidence",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in reports:
                for event in r.role_changes:
                    writer.writerow(_sanitize_dict(event.to_dict()))

    @staticmethod
    def export_funding_events(reports: List[CompanyIntelligenceReport], filepath: str) -> None:
        """
        Exports detailed funding, capital raise, and investment events.
        """
        fieldnames = [
            "company_name",
            "round_type",
            "amount_raw",
            "amount_usd",
            "lead_investors",
            "participating_investors",
            "valuation",
            "date",
            "announcement_title",
            "summary",
            "source_url",
            "source_name",
            "confidence",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in reports:
                for fund_ev in r.funding_events:
                    writer.writerow(_sanitize_dict(fund_ev.to_dict()))

    @staticmethod
    def export_strategic_movements(reports: List[CompanyIntelligenceReport], filepath: str) -> None:
        """
        Exports detailed strategic company movements (M&A, facility expansions, restructuring, partnerships).
        """
        fieldnames = [
            "company_name",
            "category",
            "headline",
            "summary",
            "counterparty",
            "location",
            "date",
            "source_url",
            "source_name",
            "confidence",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in reports:
                for mov_ev in r.strategic_movements:
                    writer.writerow(_sanitize_dict(mov_ev.to_dict()))
