"""
role_change.py — Role Change & Personnel Movement Models
company_info / models
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class MovementType(str, Enum):
    JOINED = "JOINED"                     # New hire / executive arrival
    DEPARTED = "DEPARTED"                 # Resignation / departure / alumni
    PROMOTED = "PROMOTED"                 # Internal promotion
    BOARD_APPOINTMENT = "BOARD_APPOINTMENT"# Board member / advisory appointment
    CURRENT_LEADERSHIP = "CURRENT_LEADERSHIP" # Existing identified leader


class RoleChangeEvent(BaseModel):
    """Represents an individual person movement or role change event."""
    person_name: str
    company_name: str
    movement_type: MovementType
    role_title: str
    previous_role: Optional[str] = None
    department: Optional[str] = None
    date_str: Optional[str] = None
    evidence_snippet: str = ""
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "person_name": self.person_name,
            "company_name": self.company_name,
            "movement_type": self.movement_type.value,
            "role_title": self.role_title,
            "previous_role": self.previous_role or "",
            "department": self.department or "",
            "date": self.date_str or "",
            "evidence": self.evidence_snippet,
            "source_url": self.source_url or "",
            "source_name": self.source_name or "",
            "confidence": self.confidence_score,
        }
