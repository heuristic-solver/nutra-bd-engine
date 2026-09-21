"""
api.py — FastAPI REST API Server for Company Intelligence
company_info
"""

from __future__ import annotations
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel

from company_info.models import CompanyProfile, CompanyIntelligenceReport
from company_info.pipeline import get_kb_loader, CompanyIntelligenceEngine

app = FastAPI(
    title="Company Intelligence & Movement Engine API",
    description="Zero-Cost Multi-Engine Intelligence Harvester for Role Changes, Funding Rounds, and Strategic Corporate Movements.",
    version="1.0.0",
)

engine = CompanyIntelligenceEngine(max_workers=5)


class BatchScanRequest(BaseModel):
    companies: List[str]
    limit: Optional[int] = 10


@app.get("/health")
def health_check():
    kb = get_kb_loader()
    return {
        "status": "healthy",
        "kb_companies_loaded": kb.total_count,
        "engine_version": "1.0.0",
        "third_party_paid_apis_required": False,
    }


@app.get("/kb/search")
def search_kb(q: str = Query(..., description="Company name, ingredient, or specialty keyword")):
    kb = get_kb_loader()
    results = [
        {
            "name": c.company_name,
            "domain": c.domain,
            "specialty": c.specialty,
            "headquarters": c.headquarters,
            "segments": c.segments,
        }
        for c in kb.get_all()
        if q.lower() in c.company_name.lower() or (c.specialty and q.lower() in c.specialty.lower())
    ]
    return {"query": q, "total_matches": len(results), "matches": results[:50]}


@app.get("/company/scan", response_model=CompanyIntelligenceReport)
def scan_company_endpoint(name: str = Query(..., description="Company name"), domain: Optional[str] = None):
    kb = get_kb_loader()
    profile = kb.find_by_name(name)
    if not profile:
        profile = CompanyProfile(
            company_name=name,
            domain=domain or name.lower().replace(" ", "") + ".com",
        )

    try:
        report = engine.scan_company(profile)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/scan", response_model=List[CompanyIntelligenceReport])
def batch_scan_endpoint(req: BatchScanRequest):
    kb = get_kb_loader()
    profiles = []
    for c_name in req.companies[:req.limit or 10]:
        prof = kb.find_by_name(c_name)
        if not prof:
            prof = CompanyProfile(company_name=c_name, domain=c_name.lower().replace(" ", "") + ".com")
        profiles.append(prof)

    reports = engine.scan_batch(profiles)
    return reports
