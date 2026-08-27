"""
app.py — Unified Nutraceutical Business Development (BD) Engine API Server

Combines:
  1. TheirStack Collector (Hiring Velocity & Talent Pain Index)
  2. Serper Collector (6-Month Market Intelligence, Expansions, M&A)
  3. openFDA Collector (Product Recalls & Enforcement Risk)
  4. Apify Collector (LinkedIn Headcount & Growth Percentage)

Run with:
    python app.py
"""

from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from bd_engine.collectors.theirstack_collector import TheirStackCollector
from bd_engine.collectors.serper_collector import SerperCollector
from bd_engine.collectors.openfda_collector import OpenFDACollector
from bd_engine.collectors.apify_collector import ApifyCollector
import run_theirstack

app = FastAPI(
    title="Nutraceutical BD Intelligence API",
    description="Multi-signal BD intelligence engine for nutraceutical talent acquisition.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize collectors
theirstack = TheirStackCollector(api_token=run_theirstack.API_TOKEN)
serper = SerperCollector()
openfda = OpenFDACollector()
apify = ApifyCollector()


@app.get("/")
def root():
    return {
        "system": "Nutraceutical BD Intelligence Engine",
        "status": "online",
        "collectors": [
            "TheirStack (Jobs & Velocity)",
            "Serper (6M Market & Trade Press)",
            "openFDA (Recalls & Risk)",
            "Apify (LinkedIn Headcount & Growth %)",
        ],
        "endpoints": {
            "summary_badge": "/api/v1/bd/summary?company_name=...",
            "full_dossier": "/api/v1/bd/company?company_name=...",
            "growth_rate": "/api/v1/bd/growth?company_name=...&previous_headcount=...",
        },
    }


# ======================================================================
# ENDPOINT 1: Lightweight Badge for Job Cards & AI Candidate Matcher
# ======================================================================
@app.get("/api/v1/bd/summary")
def get_company_summary(company_name: str = Query(..., description="Target company name")):
    """
    Lightweight BD summary for embedding directly into Job Cards next to candidate matches.
    """
    # 1. Fetch FDA recalls
    fda_data = openfda.analyze_company(company_name, lookback_years=3)
    fda_summary = fda_data["summary"]

    # 2. Fetch Serper signals
    serper_data = serper.analyze_company(company_name)
    serper_summary = serper_data["signal_summary"]

    # Determine Urgency Level
    if fda_summary["class_1_critical"] > 0 or fda_summary["ongoing_active"] > 0:
        urgency = "CRITICAL_REGULATORY"
        badge_color = "red"
        talking_point = fda_data["recruiter_hook"]
    elif serper_summary["facility_count"] > 0:
        urgency = "EXPANSION_SURGE"
        badge_color = "emerald"
        talking_point = f"{company_name} announced new facility expansion in recent months. High plant & QA hiring demand."
    elif serper_summary["funding_ma_count"] > 0:
        urgency = "M&A_RESTRUCTURING"
        badge_color = "purple"
        talking_point = f"{company_name} underwent recent M&A / capital investment. Team restructuring in progress."
    else:
        urgency = "NORMAL"
        badge_color = "gray"
        talking_point = f"{company_name} monitored across BD signals."

    return {
        "company_name": company_name,
        "urgency_level": urgency,
        "badge_color": badge_color,
        "signals": {
            "fda_recalls_count": fda_summary["total_recalls"],
            "fda_risk_score": fda_summary["regulatory_risk_score"],
            "market_expansion_signals": serper_summary["facility_count"],
            "ma_funding_signals": serper_summary["funding_ma_count"],
            "trade_press_signals": serper_summary["trade_press_count"],
        },
        "talking_point": talking_point,
    }


# ======================================================================
# ENDPOINT 2: Full 360° Company BD Intelligence Dossier
# ======================================================================
@app.get("/api/v1/bd/company")
def get_company_dossier(
    company_name: str = Query(..., description="Target company name"),
    company_domain: Optional[str] = Query(None, description="Company domain"),
    linkedin_url: Optional[str] = Query(None, description="LinkedIn company page URL"),
):
    """
    Full 360° company intelligence combining Job Velocity, Market Signals, FDA Compliance, and LinkedIn Headcount.
    """
    try:
        # Pull Serper market signals (6-month window)
        serper_res = serper.analyze_company(company_name)

        # Pull openFDA recall signals
        fda_res = openfda.analyze_company(company_name, lookback_years=3)

        # Pull Apify LinkedIn headcount data if configured
        apify_res = apify.analyze_company(company_name, linkedin_url=linkedin_url)

        return {
            "company_name": company_name,
            "company_domain": company_domain,
            "regulatory_compliance": fda_res,
            "market_signals_6m": serper_res,
            "linkedin_headcount": apify_res,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================================
# ENDPOINT 3: Headcount Growth Rate Calculator
# ======================================================================
@app.get("/api/v1/bd/growth")
def get_headcount_growth(
    company_name: str = Query(..., description="Company name"),
    current_headcount: int = Query(..., description="Current employee count"),
    previous_headcount: int = Query(..., description="Previous employee count"),
    days_between: int = Query(30, description="Days between snapshots"),
):
    """
    Computes exact hiring % growth delta and annualized trajectory.
    """
    return {
        "company_name": company_name,
        "analysis": apify.calculate_headcount_growth(
            current_headcount=current_headcount,
            previous_headcount=previous_headcount,
            days_between=days_between,
        ),
    }


if __name__ == "__main__":
    import uvicorn
    print("\nStarting Unified BD Engine API on http://127.0.0.1:8000 ...")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
