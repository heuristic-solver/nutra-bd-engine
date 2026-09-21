"""
company_info — Zero-API Custom Company Intelligence & Movement Harvester
========================================================================

A versatile, modular, zero-third-party-cost intelligence engine for tracking:
  1. Role Changes & Executive Movements (Joined, Promoted, Departed, Alumni)
  2. Funding & Capital Structure (Rounds, Amounts, Lead Investors, Valuations)
  3. Strategic Company Milestones (M&A, Facility Expansions, Restructuring, Partnerships)

Designed for nutraceutical and health/wellness enterprises.
"""

from company_info.models import (
    CompanyProfile,
    RoleChangeEvent,
    MovementType,
    FundingEvent,
    FundingRoundType,
    StrategicMovementEvent,
    MovementCategory,
    CompanyIntelligenceReport,
)

from company_info.pipeline import (
    NutraceuticalKBLoader,
    get_kb_loader,
    CompanyIntelligenceEngine,
)

from company_info.exporters import (
    CSVExporter,
    JSONExporter,
    MarkdownReporter,
)

__version__ = "1.0.0"

__all__ = [
    "CompanyProfile",
    "RoleChangeEvent",
    "MovementType",
    "FundingEvent",
    "FundingRoundType",
    "StrategicMovementEvent",
    "MovementCategory",
    "CompanyIntelligenceReport",
    "NutraceuticalKBLoader",
    "get_kb_loader",
    "CompanyIntelligenceEngine",
    "CSVExporter",
    "JSONExporter",
    "MarkdownReporter",
]
