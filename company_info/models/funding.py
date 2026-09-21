"""
funding.py — Funding, Capital, and Investment Data Models
company_info / models
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class FundingRoundType(str, Enum):
    SEED = "Seed"
    PRE_SEED = "Pre-Seed"
    SERIES_A = "Series A"
    SERIES_B = "Series B"
    SERIES_C = "Series C"
    SERIES_D_PLUS = "Series D+"
    GROWTH_EQUITY = "Growth Equity"
    PRIVATE_EQUITY = "Private Equity"
    DEBT_FINANCING = "Debt Financing"
    GRANT = "Grant"
    STRATEGIC_INVESTMENT = "Strategic Investment"
    UNDISCLOSED = "Undisclosed / Venture Round"


class FundingEvent(BaseModel):
    """Represents a funding round, equity financing, or capital investment event."""
    company_name: str
    round_type: FundingRoundType = FundingRoundType.UNDISCLOSED
    amount_raw: Optional[str] = None           # e.g., "$25M", "€10M", "Undisclosed"
    amount_usd: Optional[float] = None         # Normalized numeric USD amount in dollars (e.g. 25000000.0)
    lead_investors: List[str] = Field(default_factory=list)
    participating_investors: List[str] = Field(default_factory=list)
    valuation_raw: Optional[str] = None        # e.g. "$250M Valuation"
    date_str: Optional[str] = None
    announcement_title: str = ""
    summary: str = ""
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "round_type": self.round_type.value,
            "amount_raw": self.amount_raw or "Undisclosed",
            "amount_usd": self.amount_usd,
            "lead_investors": ", ".join(self.lead_investors) if self.lead_investors else "",
            "participating_investors": ", ".join(self.participating_investors) if self.participating_investors else "",
            "valuation": self.valuation_raw or "",
            "date": self.date_str or "",
            "announcement_title": self.announcement_title,
            "summary": self.summary,
            "source_url": self.source_url or "",
            "source_name": self.source_name or "",
            "confidence": self.confidence_score,
        }
