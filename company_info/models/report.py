"""
report.py — Comprehensive Company Intelligence Report Model
company_info / models
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from company_info.models.company import CompanyProfile
from company_info.models.role_change import RoleChangeEvent, MovementType
from company_info.models.funding import FundingEvent
from company_info.models.movement import StrategicMovementEvent


class CompanyIntelligenceReport(BaseModel):
    """Complete 360-degree intelligence report for a company."""
    company_name: str
    domain: Optional[str] = None
    website: Optional[str] = None
    profile: CompanyProfile
    role_changes: List[RoleChangeEvent] = Field(default_factory=list)
    target_hiring_functions: List[str] = Field(default_factory=list)
    mapped_target_roles: List[str] = Field(default_factory=list)
    recruitment_intelligence: str = ""
    strategic_insights: str = ""
    funding_events: List[FundingEvent] = Field(default_factory=list)
    strategic_movements: List[StrategicMovementEvent] = Field(default_factory=list)
    scan_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_sec: float = 0.0
    data_sources_scraped: List[str] = Field(default_factory=list)
    total_signals_discovered: int = 0

    # Quick Access Computed Properties
    @property
    def people_joined(self) -> List[RoleChangeEvent]:
        return [r for r in self.role_changes if r.movement_type in (MovementType.JOINED, MovementType.PROMOTED, MovementType.BOARD_APPOINTMENT)]

    @property
    def people_departed(self) -> List[RoleChangeEvent]:
        return [r for r in self.role_changes if r.movement_type == MovementType.DEPARTED]

    @property
    def total_funding_usd(self) -> float:
        return sum(f.amount_usd or 0.0 for f in self.funding_events)

    def to_summary_dict(self) -> Dict[str, Any]:
        """Compact summary dictionary for table views and master CSV export."""
        joined_names = [f"{r.person_name} ({r.role_title})" for r in self.people_joined]
        departed_names = [f"{r.person_name} ({r.role_title})" for r in self.people_departed]
        funding_summaries = [f"{f.round_type.value}: {f.amount_raw or 'Undisclosed'} ({f.date_str or 'Recent'})" for f in self.funding_events]
        movement_summaries = [f"[{m.category.value}] {m.headline}" for m in self.strategic_movements]

        return {
            "company_name": self.company_name,
            "domain": self.domain or "",
            "headquarters": self.profile.headquarters or "",
            "specialty": self.profile.specialty or "",
            "joined_count": len(self.people_joined),
            "joined_people": " | ".join(joined_names) if joined_names else "None detected",
            "departed_count": len(self.people_departed),
            "departed_people": " | ".join(departed_names) if departed_names else "None detected",
            "target_hiring_functions": ", ".join(self.target_hiring_functions) if self.target_hiring_functions else "",
            "mapped_target_roles": " | ".join(self.mapped_target_roles) if self.mapped_target_roles else "",
            "recruitment_intelligence": self.recruitment_intelligence or "",
            "funding_rounds_count": len(self.funding_events),
            "funding_history": " | ".join(funding_summaries) if funding_summaries else "None detected",
            "total_funding_est_usd": self.total_funding_usd,
            "strategic_movements_count": len(self.strategic_movements),
            "strategic_movements": " | ".join(movement_summaries) if movement_summaries else "None detected",
            "sources_scraped": ", ".join(self.data_sources_scraped),
            "scan_timestamp": self.scan_timestamp.isoformat(),
        }
