"""
bd_scorer.py — Nutraceutical Multi-Signal Propensity Scoring Engine

Merges signals across:
  1. Apify LinkedIn Headcount & Growth Trajectory (Weight: 30%)
  2. Serper 6-Month Facility Expansions & M&A (Weight: 25%)
  3. Serper 6-Month Executive Leadership Turnover (Weight: 20%)
  4. openFDA Regulatory Recalls & Compliance Pressure (Weight: 15%)
  5. Nutraceutical KB Domain Alignment & Segment Fit (Weight: 10%)

Outputs a normalized 0–100 Propensity Score ranking companies by their statistical
urgency and willingness to engage external executive search & recruitment agencies.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# -------------------------------------------------------------------
# SCORING DIMENSION WEIGHTS (Sum = 100)
# -------------------------------------------------------------------
WEIGHT_HEADCOUNT_GROWTH = 30.0   # Apify: Rapid headcount scaling or severe attrition
WEIGHT_FACILITY_EXPANSION = 25.0 # Serper: New plant openings, capacity upgrades, M&A
WEIGHT_EXEC_TURNOVER = 20.0      # Serper: C-Suite, VP, Director turnover & new appointments
WEIGHT_REGULATORY_RISK = 15.0    # openFDA: Class I/II product recalls & FDA audits
WEIGHT_DOMAIN_ALIGNMENT = 10.0   # KB: Verified nutra segment, cGMP certification, scale


class PropensityScorer:
    """
    Computes unified BD Propensity Scores (0–100) for nutraceutical targets.
    """

    def score_company(
        self,
        company_name: str,
        apify_data: Optional[Dict[str, Any]] = None,
        serper_data: Optional[Dict[str, Any]] = None,
        openfda_data: Optional[Dict[str, Any]] = None,
        kb_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Aggregates multi-source data and produces a comprehensive BD scorecard.
        """
        # 1. Score Headcount Growth Trajectory (Max: 30 pts)
        growth_score, growth_breakdown = self._score_headcount_growth(apify_data)

        # 2. Score Facility & Operational Expansions (Max: 25 pts)
        expansion_score, expansion_breakdown = self._score_expansions(serper_data)

        # 3. Score Executive Leadership Turnover (Max: 20 pts)
        turnover_score, turnover_breakdown = self._score_exec_turnover(serper_data)

        # 4. Score Regulatory & Compliance Pressure (Max: 15 pts)
        regulatory_score, regulatory_breakdown = self._score_regulatory(openfda_data)

        # 5. Score Domain & Segment Fit (Max: 10 pts)
        domain_score, domain_breakdown = self._score_domain_alignment(kb_data)

        # Total Composite Propensity Score (0 - 100)
        total_score = round(
            growth_score + expansion_score + turnover_score + regulatory_score + domain_score,
            1,
        )
        total_score = min(100.0, max(0.0, total_score))

        # Classify Tier & Outreach Urgency
        if total_score >= 70.0:
            tier = "TIER_1_IMMEDIATE_PITCH"
            urgency_label = "HIGH PROPENSITY — Contact Today"
            badge_color = "red" if regulatory_score >= 10 else "emerald"
        elif total_score >= 45.0:
            tier = "TIER_2_WARM_NURTURE"
            urgency_label = "MODERATE PROPENSITY — Nurture Account"
            badge_color = "amber"
        else:
            tier = "TIER_3_MONITORING"
            urgency_label = "LOW PROPENSITY — Baseline Monitoring"
            badge_color = "gray"

        # Generate Primary Recruiter Talking Point
        talking_point = self._generate_primary_talking_point(
            company_name=company_name,
            growth_breakdown=growth_breakdown,
            expansion_breakdown=expansion_breakdown,
            turnover_breakdown=turnover_breakdown,
            regulatory_breakdown=regulatory_breakdown,
        )

        return {
            "company_name": company_name,
            "propensity_score": total_score,
            "tier": tier,
            "urgency_label": urgency_label,
            "badge_color": badge_color,
            "primary_talking_point": talking_point,
            "score_breakdown": {
                "headcount_growth": {
                    "score": round(growth_score, 1),
                    "max_points": WEIGHT_HEADCOUNT_GROWTH,
                    "details": growth_breakdown,
                },
                "facility_expansions": {
                    "score": round(expansion_score, 1),
                    "max_points": WEIGHT_FACILITY_EXPANSION,
                    "details": expansion_breakdown,
                },
                "executive_turnover": {
                    "score": round(turnover_score, 1),
                    "max_points": WEIGHT_EXEC_TURNOVER,
                    "details": turnover_breakdown,
                },
                "regulatory_pressure": {
                    "score": round(regulatory_score, 1),
                    "max_points": WEIGHT_REGULATORY_RISK,
                    "details": regulatory_breakdown,
                },
                "domain_alignment": {
                    "score": round(domain_score, 1),
                    "max_points": WEIGHT_DOMAIN_ALIGNMENT,
                    "details": domain_breakdown,
                },
            },
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # DIMENSION 1: Headcount Growth (Max 30 pts)
    # ------------------------------------------------------------------
    @staticmethod
    def _score_headcount_growth(apify_data: Optional[Dict[str, Any]]) -> (float, Dict[str, Any]):
        if not apify_data:
            return 10.0, {"status": "NO_DATA", "reason": "Baseline neutral score"}

        growth_info = apify_data.get("headcount_growth") or {}
        trajectory = growth_info.get("trajectory", "STABLE")
        growth_pct = growth_info.get("growth_pct", 0.0)
        current_emp = (apify_data.get("firmographics") or {}).get("employee_count", 0)

        if trajectory == "HYPER_GROWTH":
            score = 30.0
            detail = f"Hyper-growth ({growth_pct:+.1f}%): internal talent acquisition capacity is overwhelmed."
        elif trajectory == "STEADY_EXPANSION":
            score = 22.0
            detail = f"Steady hiring expansion ({growth_pct:+.1f}%)."
        elif trajectory == "SEVERE_ATTRITION":
            score = 26.0  # High score because rapid departures create emergency backfill needs
            detail = f"Staffing deficit & attrition ({growth_pct:+.1f}%): urgent need for immediate replacements."
        elif trajectory == "MODERATE_CONTRACTION":
            score = 12.0
            detail = "Moderate contraction."
        else:
            # Stable baseline
            score = 15.0 if current_emp > 50 else 10.0
            detail = f"Stable headcount ({current_emp} employees)."

        return score, {
            "trajectory": trajectory,
            "growth_pct": growth_pct,
            "current_headcount": current_emp,
            "detail": detail,
        }

    # ------------------------------------------------------------------
    # DIMENSION 2: Facility & Operational Expansions (Max 25 pts)
    # ------------------------------------------------------------------
    @staticmethod
    def _score_expansions(serper_data: Optional[Dict[str, Any]]) -> (float, Dict[str, Any]):
        if not serper_data:
            return 0.0, {"facility_count": 0, "funding_count": 0}

        summary = serper_data.get("signal_summary", {})
        facility_count = summary.get("facility_count", 0)
        funding_count = summary.get("funding_ma_count", 0)

        score = 0.0
        if facility_count >= 2:
            score += 15.0
        elif facility_count == 1:
            score += 10.0

        if funding_count >= 2:
            score += 10.0
        elif funding_count == 1:
            score += 7.0

        score = min(WEIGHT_FACILITY_EXPANSION, score)
        return score, {
            "facility_expansions": facility_count,
            "funding_ma_rounds": funding_count,
            "detail": f"{facility_count} new plant/facility signals, {funding_count} M&A/investment signals in last 6M.",
        }

    # ------------------------------------------------------------------
    # DIMENSION 3: Executive Leadership Turnover (Max 20 pts)
    # ------------------------------------------------------------------
    @staticmethod
    def _score_exec_turnover(serper_data: Optional[Dict[str, Any]]) -> (float, Dict[str, Any]):
        if not serper_data:
            return 0.0, {"exec_signals": 0}

        exec_count = serper_data.get("signal_summary", {}).get("exec_signals_count", 0)
        if exec_count >= 3:
            score = 20.0
        elif exec_count == 2:
            score = 15.0
        elif exec_count == 1:
            score = 10.0
        else:
            score = 0.0

        return score, {
            "exec_signals_count": exec_count,
            "detail": f"{exec_count} executive appointment/turnover signals in last 6M.",
        }

    # ------------------------------------------------------------------
    # DIMENSION 4: Regulatory & Compliance Pressure (Max 15 pts)
    # ------------------------------------------------------------------
    @staticmethod
    def _score_regulatory(openfda_data: Optional[Dict[str, Any]]) -> (float, Dict[str, Any]):
        if not openfda_data:
            return 0.0, {"total_recalls": 0, "risk_score": 0}

        summary = openfda_data.get("summary", {})
        c1 = summary.get("class_1_critical", 0)
        ongoing = summary.get("ongoing_active", 0)
        risk_score = summary.get("regulatory_risk_score", 0.0)

        # Scale raw openFDA risk score (0-100) into 15 max points
        scaled_score = (risk_score / 100.0) * WEIGHT_REGULATORY_RISK

        # Critical multipliers
        if c1 > 0 or ongoing > 0:
            scaled_score = max(12.0, scaled_score)

        scaled_score = min(WEIGHT_REGULATORY_RISK, scaled_score)
        return scaled_score, {
            "total_recalls": summary.get("total_recalls", 0),
            "class_1_critical": c1,
            "ongoing_active": ongoing,
            "fda_risk_score": risk_score,
            "hook": openfda_data.get("recruiter_hook", ""),
        }

    # ------------------------------------------------------------------
    # DIMENSION 5: Domain Alignment & Segment Fit (Max 10 pts)
    # ------------------------------------------------------------------
    @staticmethod
    def _score_domain_alignment(kb_data: Optional[Dict[str, Any]]) -> (float, Dict[str, Any]):
        if not kb_data:
            return 5.0, {"status": "Standard Nutra Target"}

        segments = kb_data.get("segments", {})
        active_segs = [k for k, v in segments.items() if v]

        score = 5.0
        # CDMOs and Contract Manufacturers hire agencies at higher volume
        if segments.get("contract_manufacturer"):
            score += 3.0
        if segments.get("supplement_brand") or segments.get("ingredient_supplier"):
            score += 2.0

        score = min(WEIGHT_DOMAIN_ALIGNMENT, score)
        return score, {
            "active_segments": active_segs,
            "known_specialty": kb_data.get("known_speciality", "N/A"),
        }

    # ------------------------------------------------------------------
    # RECRUITER TALKING POINT GENERATOR
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_primary_talking_point(
        company_name: str,
        growth_breakdown: dict,
        expansion_breakdown: dict,
        turnover_breakdown: dict,
        regulatory_breakdown: dict,
    ) -> str:
        # Priority 1: Regulatory Recall Crisis
        if regulatory_breakdown.get("class_1_critical", 0) > 0 or regulatory_breakdown.get("ongoing_active", 0) > 0:
            return (
                f"Urgent QA remediation trigger: {company_name} has active FDA recall pressure. "
                f"Pitch Director of Quality Systems & cGMP Compliance leads immediately."
            )

        # Priority 2: New Plant / Facility Expansion
        if expansion_breakdown.get("facility_expansions", 0) > 0:
            return (
                f"Operational expansion trigger: {company_name} announced new manufacturing facility investments. "
                f"Pitch Plant Operations Managers, Process Engineers, and Validation Leads."
            )

        # Priority 3: Hyper-Growth Trajectory
        if growth_breakdown.get("trajectory") == "HYPER_GROWTH":
            return (
                f"Hyper-growth trigger: Headcount expanded by {growth_breakdown.get('growth_pct'):+.1f}%. "
                f"Internal talent acquisition is constrained; pitch fractional or retained search."
            )

        # Priority 4: Executive Leadership Turnover
        if turnover_breakdown.get("exec_signals_count", 0) > 0:
            return (
                f"Executive restructuring trigger: Recent C-Suite / VP appointments recorded. "
                f"Target newly installed leaders as they rebuild their departmental teams."
            )

        # Priority 5: Attrition Replacement
        if growth_breakdown.get("trajectory") == "SEVERE_ATTRITION":
            return (
                f"Staffing deficit trigger: Net headcount dropped by {growth_breakdown.get('growth_pct'):.1f}%. "
                f"Pitch emergency backfills for key technical positions."
            )

        return f"{company_name} is stable in the nutraceutical sector. Maintain periodic BD touchpoints."
