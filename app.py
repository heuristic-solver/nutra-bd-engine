"""
app.py — Unified Nutraceutical Business Development (BD) Engine API Server

Powered by:
  1. Apify Collector (LinkedIn Headcount & Growth Percentage)
  2. Serper Collector (6-Month Market Intelligence, Expansions, M&A, Exec Hires)
  3. openFDA Collector (Product Recalls & Enforcement Risk)
  4. Propensity Scorer (Unified 0–100 Multi-Signal Ranking Math)

Run with:
    python app.py
"""

from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from bd_engine.collectors.serper_collector import SerperCollector
from bd_engine.collectors.openfda_collector import OpenFDACollector
from bd_engine.collectors.apify_collector import ApifyCollector
from bd_engine.bd_scorer import PropensityScorer

app = FastAPI(
    title="Nutraceutical BD Intelligence API",
    description="Multi-signal BD propensity engine for nutraceutical talent acquisition.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core collectors & scoring engine
serper = SerperCollector()
openfda = OpenFDACollector()
apify = ApifyCollector()
scorer = PropensityScorer()


@app.get("/")
def root():
    return {
        "system": "Nutraceutical BD Intelligence Engine",
        "version": "2.0.0",
        "status": "online",
        "collectors": [
            "Apify (LinkedIn Headcount & Growth %)",
            "Serper (6M Expansions, M&A, Exec Turnover)",
            "openFDA (Product Recalls & Risk)",
            "Propensity Scorer (0–100 Scorecard Engine)",
        ],
        "endpoints": {
            "score_company": "/api/v1/bd/score?company_name=...",
            "summary_badge": "/api/v1/bd/summary?company_name=...",
            "full_dossier": "/api/v1/bd/company?company_name=...",
        },
    }


# ======================================================================
# ENDPOINT 1: Unified 0–100 BD Propensity Scorecard
# ======================================================================
@app.get("/api/v1/bd/score")
def get_company_score(
    company_name: str = Query(..., description="Target company name"),
    linkedin_url: Optional[str] = Query(None, description="LinkedIn company page URL"),
    previous_headcount: Optional[int] = Query(None, description="Previous headcount baseline"),
):
    """
    Computes the master 0–100 Propensity Score, Tier classification,
    and granular dimension breakdowns across Apify, Serper, and openFDA.
    """
    try:
        # Collect signals in parallel / sequence
        serper_data = serper.analyze_company(company_name)
        openfda_data = openfda.analyze_company(company_name, lookback_years=3)
        apify_data = apify.analyze_company(
            company_name,
            linkedin_url=linkedin_url,
            previous_headcount=previous_headcount,
        )

        # Compute unified BD scorecard
        scorecard = scorer.score_company(
            company_name=company_name,
            apify_data=apify_data,
            serper_data=serper_data,
            openfda_data=openfda_data,
        )

        return scorecard

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================================
# ENDPOINT 2: Lightweight Badge for Job Cards & AI Candidate Matcher
# ======================================================================
@app.get("/api/v1/bd/summary")
def get_company_summary(company_name: str = Query(..., description="Target company name")):
    """
    Lightweight BD summary badge for embedding directly into Job Cards next to candidate matches.
    """
    try:
        fda_data = openfda.analyze_company(company_name, lookback_years=3)
        serper_data = serper.analyze_company(company_name)

        scorecard = scorer.score_company(
            company_name=company_name,
            serper_data=serper_data,
            openfda_data=fda_data,
        )

        return {
            "company_name": company_name,
            "propensity_score": scorecard["propensity_score"],
            "tier": scorecard["tier"],
            "urgency_label": scorecard["urgency_label"],
            "badge_color": scorecard["badge_color"],
            "talking_point": scorecard["primary_talking_point"],
            "signals": {
                "fda_recalls": fda_data["summary"]["total_recalls"],
                "expansions_6m": serper_data["signal_summary"]["facility_count"],
                "funding_ma_6m": serper_data["signal_summary"]["funding_ma_count"],
                "exec_turnover_6m": serper_data["signal_summary"]["exec_signals_count"],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================================
# ENDPOINT 3: Full 360° Company Intelligence Dossier
# ======================================================================
@app.get("/api/v1/bd/company")
def get_company_dossier(
    company_name: str = Query(..., description="Target company name"),
    linkedin_url: Optional[str] = Query(None, description="LinkedIn company page URL"),
    previous_headcount: Optional[int] = Query(None, description="Previous headcount baseline"),
):
    """
    Full 360° company intelligence dossier containing raw signal feeds and master scorecard.
    """
    try:
        serper_data = serper.analyze_company(company_name)
        openfda_data = openfda.analyze_company(company_name, lookback_years=3)
        apify_data = apify.analyze_company(
            company_name,
            linkedin_url=linkedin_url,
            previous_headcount=previous_headcount,
        )

        scorecard = scorer.score_company(
            company_name=company_name,
            apify_data=apify_data,
            serper_data=serper_data,
            openfda_data=openfda_data,
        )

        return {
            "company_name": company_name,
            "scorecard": scorecard,
            "raw_signals": {
                "linkedin_headcount": apify_data,
                "market_intelligence_6m": serper_data,
                "regulatory_compliance": openfda_data,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("\nStarting Unified BD Engine API on http://127.0.0.1:8000 ...")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
