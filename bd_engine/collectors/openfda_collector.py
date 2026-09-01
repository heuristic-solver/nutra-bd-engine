"""
openfda_collector.py — Nutraceutical BD Engine: openFDA Collector

Tracks two data types:
  1. FDA Food Enforcement (Recalls) — Class I/II/III, risk scoring, recruiter hooks
  2. FDA Facility Registrations — New facility registrations as an early-warning
     expansion signal that precedes Ops/QA hiring by months

Endpoints:
  - Recalls:     https://api.fda.gov/food/enforcement.json
  - Facilities:  https://api.fda.gov/food/registrationlisting.json

Cost: Free (US Government public API — no API key required, key optional for higher rate limits)
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any


OPENFDA_ENFORCEMENT_URL     = "https://api.fda.gov/food/enforcement.json"
OPENFDA_REGISTRATION_URL    = "https://api.fda.gov/food/registrationlisting.json"

# Severity weights for Regulatory Risk Score
CLASSIFICATION_WEIGHTS = {
    "Class I":   10.0,   # Dangerous / high health risk
    "Class II":   5.0,   # Moderate / temporary health consequences
    "Class III":  2.0,   # Minor / technical cGMP labeling defect
}

# FDA registration type codes relevant to nutraceuticals
FACILITY_TYPE_MAP = {
    "Dietary Supplement":                  "Dietary Supplement Manufacturer",
    "Food or Color Additive":              "Food / Additive Manufacturer",
    "Infant Formula":                      "Infant Formula Manufacturer",
    "Low Acid Canned Food":                "LACF Manufacturer",
    "Acidified Food":                      "Acidified Food Manufacturer",
    "Juice":                               "Juice Processor",
    "Fish/Fishery Products":               "Seafood Processor",
    "Human Food By-products for Animals":  "By-product Processor",
}


class OpenFDACollector:
    """
    Collects two signal types from the openFDA public API:
      1. Recall enforcement actions (risk signal)
      2. Facility registrations (expansion early-warning signal)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()

    def _query_enforcement(self, search_query: str, limit: int = 25) -> List[dict]:
        """Execute a query against the openFDA food enforcement endpoint."""
        params = {"search": search_query, "limit": min(limit, 100)}
        if self.api_key:
            params["api_key"] = self.api_key
        try:
            resp = self.session.get(OPENFDA_ENFORCEMENT_URL, params=params, timeout=15)
            if resp.status_code == 404:
                return []
            if not resp.ok:
                return []
            return resp.json().get("results", [])
        except Exception:
            return []

    def _query_registration(self, search_query: str, limit: int = 25) -> List[dict]:
        """Execute a query against the openFDA food facility registration endpoint."""
        params = {"search": search_query, "limit": min(limit, 100)}
        if self.api_key:
            params["api_key"] = self.api_key
        try:
            resp = self.session.get(OPENFDA_REGISTRATION_URL, params=params, timeout=15)
            if resp.status_code == 404:
                return []
            if not resp.ok:
                return []
            return resp.json().get("results", [])
        except Exception:
            return []

    # ------------------------------------------------------------------
    # RECALL DATA
    # ------------------------------------------------------------------

    def get_company_recalls(
        self,
        company_name: str,
        lookback_years: int = 3,
        limit: int = 25,
    ) -> List[dict]:
        """Search for recalls where the company is the recalling firm."""
        start_date = (datetime.now(timezone.utc) - timedelta(days=lookback_years * 365)).strftime("%Y%m%d")
        end_date   = datetime.now(timezone.utc).strftime("%Y%m%d")

        clean_name = (
            company_name.replace(" LLC", "").replace(" Inc.", "").replace(" Inc", "")
            .replace(" Corp.", "").replace(" Corp", "").replace(" Ltd.", "").replace(" Ltd", "")
            .strip()
        )

        query = f'(recalling_firm:"{clean_name}" OR recalling_firm:"{company_name}") AND report_date:[{start_date} TO {end_date}]'
        results = self._query_enforcement(query, limit=limit)

        if not results and " " not in clean_name and len(clean_name) > 3:
            query_fuzzy = f'recalling_firm:{clean_name}* AND report_date:[{start_date} TO {end_date}]'
            results = self._query_enforcement(query_fuzzy, limit=limit)

        return [self._format_recall_item(r) for r in results]

    @staticmethod
    def _format_recall_item(item: dict) -> dict:
        """Extract and clean raw openFDA recall records."""
        raw_date = item.get("report_date", "")
        formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else raw_date

        init_date = item.get("recall_initiation_date", "")
        if len(init_date) == 8:
            init_date = f"{init_date[:4]}-{init_date[4:6]}-{init_date[6:]}"

        return {
            "recall_number":            item.get("recall_number", "N/A"),
            "recalling_firm":           item.get("recalling_firm", "Unknown"),
            "classification":           item.get("classification", "Class III"),
            "status":                   item.get("status", "Completed"),
            "voluntary_mandated":       item.get("voluntary_mandated", "Voluntary"),
            "report_date":              formatted_date,
            "recall_initiation_date":   init_date,
            "product_description":      item.get("product_description", "")[:250],
            "reason_for_recall":        item.get("reason_for_recall", ""),
            "distribution_pattern":     item.get("distribution_pattern", ""),
            "state":                    item.get("state", ""),
            "city":                     item.get("city", ""),
            "country":                  item.get("country", "US"),
        }

    # ------------------------------------------------------------------
    # FACILITY REGISTRATION DATA (Gap 3)
    # ------------------------------------------------------------------

    def get_company_facility_registrations(
        self,
        company_name: str,
        lookback_months: int = 18,
        limit: int = 10,
    ) -> List[dict]:
        """
        Search for FDA facility registrations associated with this company.
        Newly registered or recently updated facilities signal expansion
        that typically precedes Ops/QA/Manufacturing hiring.
        """
        clean_name = (
            company_name.replace(" LLC", "").replace(" Inc.", "").replace(" Inc", "")
            .replace(" Corp.", "").replace(" Corp", "").replace(" Ltd.", "").replace(" Ltd", "")
            .strip()
        )

        # Search by legal name or owner operator name
        queries = [
            f'owner_operator_name:"{clean_name}"',
            f'legal_name:"{clean_name}"',
        ]
        if " " in clean_name:
            # Also try first meaningful word for partial match
            first_word = clean_name.split()[0]
            if len(first_word) > 4:
                queries.append(f'owner_operator_name:{first_word}*')

        results = []
        for q in queries:
            r = self._query_registration(q, limit=limit)
            if r:
                results = r
                break

        cutoff_year = (datetime.now(timezone.utc) - timedelta(days=lookback_months * 30)).year
        formatted = []
        for r in results:
            formatted.append(self._format_facility_item(r, cutoff_year))

        return formatted

    @staticmethod
    def _format_facility_item(item: dict, cutoff_year: int) -> dict:
        """Extract key fields from an FDA facility registration record."""
        reg_number    = item.get("registration", {}).get("registration_number", "N/A")
        owner_name    = item.get("owner_operator", {}).get("firm_name", "")
        legal_name    = item.get("legal_name", "")
        address       = item.get("address", {})
        city          = address.get("city", "")
        state_code    = address.get("state_code", "")
        country_code  = address.get("country_code", "")
        postal_code   = address.get("postal_code", "")
        food_cats     = item.get("registration", {}).get("food_categories", [])
        facility_type = "Unknown"
        for cat in food_cats:
            cat_name = cat.get("food_category", {}).get("name", "")
            facility_type = FACILITY_TYPE_MAP.get(cat_name, cat_name) or "Food Manufacturer"
            break

        # Reg year from registration number prefix (e.g., "12345678901" — digits 5-8 are year in some formats)
        reg_year = item.get("registration", {}).get("initial_importer_flag", "")
        is_recent = False  # Without a dated field, we flag based on food category presence

        return {
            "registration_number":  reg_number,
            "owner_name":           owner_name or legal_name,
            "facility_type":        facility_type,
            "city":                 city,
            "state":                state_code,
            "country":              country_code,
            "postal_code":          postal_code,
            "food_categories":      [c.get("food_category", {}).get("name", "") for c in food_cats],
        }

    # ------------------------------------------------------------------
    # FULL ANALYZE_COMPANY
    # ------------------------------------------------------------------

    def analyze_company(self, company_name: str, lookback_years: int = 3) -> dict:
        """
        Full regulatory + facility analysis for a company.
        Returns recall risk score plus facility registration expansion signals.
        """
        print(f"\n[openFDA] Fetching recall & facility records for: {company_name} (past {lookback_years} yrs)...")

        # 1. Recalls
        recalls  = self.get_company_recalls(company_name, lookback_years=lookback_years)
        class_1  = [r for r in recalls if r["classification"] == "Class I"]
        class_2  = [r for r in recalls if r["classification"] == "Class II"]
        class_3  = [r for r in recalls if r["classification"] == "Class III"]
        ongoing  = [r for r in recalls if r["status"].lower() == "ongoing"]

        risk_points = (
            len(class_1) * CLASSIFICATION_WEIGHTS["Class I"]
            + len(class_2) * CLASSIFICATION_WEIGHTS["Class II"]
            + len(class_3) * CLASSIFICATION_WEIGHTS["Class III"]
        )
        if ongoing:
            risk_points *= 1.5
        regulatory_risk_score = min(100.0, round(risk_points, 1))

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

        # 2. Facility Registrations
        facilities = self.get_company_facility_registrations(company_name, lookback_months=18)

        facility_expansion_signal = len(facilities) > 0
        facility_states = list({f.get("state", "") for f in facilities if f.get("state")})

        print(
            f"  [OK] Found {len(recalls)} recall records | Risk Score: {regulatory_risk_score}/100 "
            f"| FDA Registered Facilities: {len(facilities)}"
        )

        return {
            "company_name":         company_name,
            "lookback_years":       lookback_years,
            "analysis_timestamp":   datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_recalls":                len(recalls),
                "class_1_critical":             len(class_1),
                "class_2_moderate":             len(class_2),
                "class_3_minor":                len(class_3),
                "ongoing_active":               len(ongoing),
                "regulatory_risk_score":        regulatory_risk_score,
                # Facility expansion fields (Gap 3)
                "fda_registered_facilities":    len(facilities),
                "facility_expansion_signal":    facility_expansion_signal,
                "facility_states":              facility_states,
            },
            "recruiter_hook":   recruiter_hook,
            "recalls":          recalls,
            "facilities":       facilities,
        }
