"""
movement.py — Strategic Company Movements & Milestone Models
company_info / models
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class MovementCategory(str, Enum):
    MERGER_ACQUISITION = "MERGER_ACQUISITION"     # M&A, asset acquisition, buyout
    FACILITY_EXPANSION = "FACILITY_EXPANSION"     # New manufacturing plant, lab expansion, warehouse
    RESTRUCTURING = "RESTRUCTURING"               # Reorganization, layoffs, operational pivot
    STRATEGIC_PARTNERSHIP = "STRATEGIC_PARTNERSHIP"# Joint venture, distribution deal, co-development
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"             # Major new ingredient, branded supplement line, clinical study
    REGULATORY_MILESTONE = "REGULATORY_MILESTONE" # FDA clearance, GRAS notification, patent award
    REBRANDING = "REBRANDING"                     # Company name change, division spinout


class StrategicMovementEvent(BaseModel):
    """Represents a major operational, strategic, or corporate milestone."""
    company_name: str
    category: MovementCategory
    headline: str
    summary: str
    counterparty: Optional[str] = None            # e.g., Acquired company, partner firm, investor
    location: Optional[str] = None                # e.g., "Salt Lake City facility", "Europe division"
    date_str: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "category": self.category.value,
            "headline": self.headline,
            "summary": self.summary,
            "counterparty": self.counterparty or "",
            "location": self.location or "",
            "date": self.date_str or "",
            "source_url": self.source_url or "",
            "source_name": self.source_name or "",
            "confidence": self.confidence_score,
        }
