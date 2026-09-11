"""
apollo_collector.py — Nutraceutical BD Engine: Apollo B2B Intelligence Collector

Pulls verified organizational data, employee counts, department breakdowns, and key decision
makers across R&D, Formulation, Regulatory, Quality, Sales, and Executive leadership.
"""

import os
import re
import time
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY", "")
APOLLO_BASE_URL = "https://api.apollo.io/v1"


class ApolloCollector:
    """
    Integrates Apollo.io API to fetch verified B2B organization intelligence,
    verified company domains, real headcounts, and key department personnel.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("APOLLO_API_KEY", "") or APOLLO_API_KEY
        self.headers = {
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
        }

    def enrich_organization(self, company_name: str, domain: Optional[str] = None) -> dict:
        """
        Enrich company organization metadata via Apollo.
        Returns: {name, domain, linkedin_url, estimated_headcount, industry, city, state, country}
        """
        if not self.api_key:
            return {}

        url = f"{APOLLO_BASE_URL}/organizations/enrich"
        params = {"name": company_name}
        if domain:
            params["domain"] = domain

        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=12)
            if not resp.ok:
                return {}
            data = resp.json().get("organization", {})
            return {
                "name": data.get("name", company_name),
                "domain": data.get("primary_domain") or data.get("website_url", ""),
                "linkedin_url": data.get("linkedin_url", ""),
                "estimated_headcount": data.get("estimated_num_employees"),
                "industry": data.get("industry", ""),
                "city": data.get("city", ""),
                "state": data.get("state", ""),
                "country": data.get("country", ""),
                "raw": data
            }
        except Exception:
            return {}

    def search_key_personnel(
        self,
        company_name: str,
        per_page: int = 15,
        target_titles: Optional[List[str]] = None
    ) -> List[dict]:
        """
        Search for key personnel at the company across target functions
        (Formulation, Science, QA/RA, Operations, Commercial/Sales, Executive).
        """
        if not self.api_key:
            return []

        url = f"{APOLLO_BASE_URL}/mixed_people/api_search"
        payload = {
            "q_organization_name": company_name,
            "page": 1,
            "per_page": per_page,
        }
        if target_titles:
            payload["person_titles"] = target_titles

        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=12)
            if not resp.ok:
                return []
            people = resp.json().get("people", [])
            out = []
            for p in people:
                fn = p.get("first_name", "")
                ln = p.get("last_name", "")
                full_name = f"{fn} {ln}".strip() or p.get("name", "")
                title = p.get("title", "")
                if not title:
                    continue
                out.append({
                    "first_name": fn,
                    "last_name": ln,
                    "name": full_name,
                    "title": title,
                    "seniority": p.get("seniority", ""),
                    "departments": p.get("departments", []),
                    "linkedin_url": p.get("linkedin_url", ""),
                    "id": p.get("id", ""),
                })
            return out
        except Exception:
            return []
