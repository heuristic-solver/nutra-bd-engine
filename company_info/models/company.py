"""
company.py — Company Data Models
company_info / models
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CompanyProfile(BaseModel):
    """Normalized profile representation of a target company."""
    company_name: str
    domain: Optional[str] = None
    website: Optional[str] = None
    headquarters: Optional[str] = None
    ownership: Optional[str] = "Private"
    source_sheet: Optional[str] = None
    specialty: Optional[str] = None
    segments: Dict[str, bool] = Field(default_factory=dict)
    key_ingredients: List[str] = Field(default_factory=list)
    branded_ingredients: List[str] = Field(default_factory=list)
    manufacturing_capabilities: List[str] = Field(default_factory=list)
    hiring_functions: List[str] = Field(default_factory=list)
    role_mapping: List[str] = Field(default_factory=list)
    raw_kb_data: Optional[Dict[str, Any]] = None

    @property
    def core_brand_name(self) -> str:
        """Strips legal suffixes (GmbH, Inc, LLC, Ltd, Co. Kg, Corp, etc.) to yield the core brand name."""
        cleaned = re.sub(r'\b(?:inc|inc\.|llc|corp|corp\.|corporation|ltd|ltd\.|llp|gmbh|co\.\s*kg|co|co\.|ag|sa|bv|nv|plc|limited|holdings|group)\b', '', self.company_name, flags=re.IGNORECASE)
        cleaned = re.sub(r'[,.\-+]+', ' ', cleaned).strip()
        return cleaned if len(cleaned) >= 2 else self.company_name

    @classmethod
    def from_kb_dict(cls, data: Dict[str, Any]) -> CompanyProfile:
        """Instantiate a CompanyProfile directly from a nutraceutical_kb.json dictionary record."""
        name = str(data.get("company_name") or data.get("name") or "Unknown").strip()
        website = str(data.get("known_website") or data.get("website") or "").strip()
        
        domain = None
        if website and website != "null":
            clean_ws = website.replace("https://", "").replace("http://", "").replace("www.", "").strip("/").split("/")[0]
            if "." in clean_ws and len(clean_ws) > 3:
                domain = clean_ws

        # Clean ingredients lists (filter out None, non-strings)
        raw_vit = []
        raw_bot = []
        if isinstance(data.get("ingredients"), dict):
            raw_vit = [str(x).strip() for x in (data["ingredients"].get("vitamins_minerals") or []) if x and isinstance(x, str)]
            raw_bot = [str(x).strip() for x in (data["ingredients"].get("botanicals") or []) if x and isinstance(x, str)]
        
        raw_branded = [str(x).strip() for x in (data.get("branded_ingredients") or []) if x and isinstance(x, str)]
        raw_mfg = [str(x).strip() for x in (data.get("manufacturing_capabilities") or []) if x and isinstance(x, str)]
        raw_hiring = [str(x).strip() for x in (data.get("hiring_functions") or []) if x and isinstance(x, str)]
        raw_roles = [str(x).strip() for x in (data.get("role_mapping") or []) if x and isinstance(x, str)]

        hq = data.get("headquarters") or data.get("known_hq")
        if hq == "null":
            hq = None

        spec = data.get("known_speciality")
        if spec == "null":
            spec = None

        return cls(
            company_name=name,
            domain=domain,
            website=website if website.startswith("http") else (f"https://{website}" if domain else None),
            headquarters=hq,
            ownership=data.get("ownership_structure") if data.get("ownership_structure") != "null" else "Private",
            source_sheet=data.get("source_sheet"),
            specialty=spec,
            segments=data.get("segments") if isinstance(data.get("segments"), dict) else {},
            key_ingredients=raw_vit + raw_bot,
            branded_ingredients=raw_branded,
            manufacturing_capabilities=raw_mfg,
            hiring_functions=raw_hiring,
            role_mapping=raw_roles,
            raw_kb_data=data,
        )
