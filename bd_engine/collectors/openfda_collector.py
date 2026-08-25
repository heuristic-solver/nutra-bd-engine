"""
openfda_collector.py — Nutraceutical BD Engine: openFDA Food Enforcement (Recalls) Collector

Tracks FDA product recalls across nutraceutical, dietary supplement, and food manufacturing firms.
Endpoint: https://api.fda.gov/food/enforcement.json
Cost: Free (US Government Public API)
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any


OPENFDA_ENFORCEMENT_URL = "https://api.fda.gov/food/enforcement.json"

# Severity weights for calculating Regulatory Risk Score
CLASSIFICATION_WEIGHTS = {
    "Class I": 10.0,   # Dangerous / high health risk (strongest recruitment trigger)
    "Class II": 5.0,   # Moderate / temporary health consequences
    "Class III": 2.0,  # Minor / technical cGMP labeling defect
}


class OpenFDACollector:
    """
    Collects FDA Food & Dietary Supplement Enforcement (Recall) data
    from the openFDA public API.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()

    def _query_api(self, search_query: str, limit: int = 25) -> list[dict]:
        """Execute a query against the openFDA food enforcement endpoint."""
        params = {
            "search": search_query,
            "limit": min(limit, 100),
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            resp = self.session.get(OPENFDA_ENFORCEMENT_URL, params=params, timeout=15)
            if resp.status_code == 404:
                # 404 in openFDA means 0 matching records found (normal)
                return []
            if not resp.ok:
                print(f"  [openFDA {resp.status_code}] Search: {search_query[:60]}")
                return []

            data = resp.json()
            return data.get("results", [])

        except Exception as e:
            print(f"  [openFDA ERROR] {e}")
            return []

    def get_company_recalls(
        self,
        company_name: str,
        lookback_years: int = 3,
        limit: int = 25,
    ) -> list[dict]:
        """
        Search for recalls where the company is the recalling firm.
        Searches by exact firm name and partial firm name matching.
        """
        # Calculate date window (format: YYYYMMDD)
        start_date = (datetime.now(timezone.utc) - timedelta(days=lookback_years * 365)).strftime("%Y%m%d")
        end_date = datetime.now(timezone.utc).strftime("%Y%m%d")

        # Clean company name (remove corporate suffixes like LLC, Inc., Corp for cleaner query)
        clean_name = (
            company_name.replace(" LLC", "")
            .replace(" Inc.", "")
            .replace(" Inc", "")
            .replace(" Corp.", "")
            .replace(" Corp", "")
            .replace(" Ltd.", "")
            .replace(" Ltd", "")
            .strip()
        )

        # Build openFDA query: recalling_firm search within date range
        # Note: openFDA syntax supports exact quotes and wildcards
        query = f'(recalling_firm:"{clean_name}" OR recalling_firm:"{company_name}") AND report_date:[{start_date} TO {end_date}]'

        results = self._query_api(query, limit=limit)

        # If strict search returned nothing, try fuzzy single-word search if name is distinctive
        if not results and " " not in clean_name and len(clean_name) > 3:
            query_fuzzy = f'recalling_firm:{clean_name}* AND report_date:[{start_date} TO {end_date}]'
            results = self._query_api(query_fuzzy, limit=limit)

        formatted_recalls = []
        for r in results:
            formatted_recalls.append(self._format_recall_item(r))

        return formatted_recalls

    @staticmethod
    def _format_recall_item(item: dict) -> dict:
        """Extract and clean raw openFDA recall records."""
        # Parse date YYYYMMDD -> YYYY-MM-DD
        raw_date = item.get("report_date", "")
        formatted_date = ""
        if len(raw_date) == 8:
            formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
        else:
            formatted_date = raw_date

        init_date = item.get("recall_initiation_date", "")
        if len(init_date) == 8:
            init_date = f"{init_date[:4]}-{init_date[4:6]}-{init_date[6:]}"

        return {
            "recall_number": item.get("recall_number", "N/A"),
            "recalling_firm": item.get("recalling_firm", "Unknown"),
            "classification": item.get("classification", "Class III"),
            "status": item.get("status", "Completed"),
            "voluntary_mandated": item.get("voluntary_mandated", "Voluntary"),
            "report_date": formatted_date,
            "recall_initiation_date": init_date,
            "product_description": item.get("product_description", "")[:250],
            "reason_for_recall": item.get("reason_for_recall", ""),
            "distribution_pattern": item.get("distribution_pattern", ""),
            "state": item.get("state", ""),
            "city": item.get("city", ""),
            "country": item.get("country", "US"),
        }

    def analyze_company(self, company_name: str, lookback_years: int = 3) -> dict:
        """
        Produce a full regulatory recall analysis and risk assessment for a company.
        """
        print(f"\n[openFDA] Fetching recall records for: {company_name} (past {lookback_years} yrs)...")
        recalls = self.get_company_recalls(company_name, lookback_years=lookback_years)

        class_1 = [r for r in recalls if r["classification"] == "Class I"]
        class_2 = [r for r in recalls if r["classification"] == "Class II"]
        class_3 = [r for r in recalls if r["classification"] == "Class III"]
        ongoing = [r for r in recalls if r["status"].lower() == "ongoing"]

        # Calculate Regulatory Risk Score (0 - 100 scale)
        risk_points = (
            len(class_1) * CLASSIFICATION_WEIGHTS["Class I"]
            + len(class_2) * CLASSIFICATION_WEIGHTS["Class II"]
            + len(class_3) * CLASSIFICATION_WEIGHTS["Class III"]
        )
        if ongoing:
            risk_points *= 1.5  # Ongoing active enforcement increases urgency

        regulatory_risk_score = min(100.0, round(risk_points, 1))

        # Generate Recruiter Pitch Hook based on recalls
        recruiter_hook = None
        if class_1:
            recruiter_hook = (
                f"HIGH URGENCY: Firm experienced {len(class_1)} Class I (critical) FDA recall(s). "
                f"Pitch Director of Quality Assurance & cGMP Remediation leads immediately."
            )
        elif ongoing:
            recruiter_hook = (
                f"ACTIVE COMPLIANCE PRESSURE: Firm currently has {len(ongoing)} ongoing FDA recall(s). "
                f"High willingness to hire QA/QC and Regulatory Affairs talent."
            )
        elif recalls:
            recruiter_hook = (
                f"MODERATE REGULATORY SIGNAL: {len(recalls)} FDA recall(s) recorded in trailing {lookback_years} years. "
                f"Strong angle for Validation & Quality Control specialists."
            )
        else:
            recruiter_hook = "No recent FDA food/supplement recalls on record."

        print(f"  [OK] Found {len(recalls)} recall records | Risk Score: {regulatory_risk_score}/100")

        return {
            "company_name": company_name,
            "lookback_years": lookback_years,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_recalls": len(recalls),
                "class_1_critical": len(class_1),
                "class_2_moderate": len(class_2),
                "class_3_minor": len(class_3),
                "ongoing_active": len(ongoing),
                "regulatory_risk_score": regulatory_risk_score,
            },
            "recruiter_hook": recruiter_hook,
            "recalls": recalls,
        }
