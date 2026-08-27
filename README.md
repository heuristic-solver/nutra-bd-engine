# Nutraceutical Business Development (BD) Engine

A multi-signal Business Development intelligence engine built specifically for Nutraceutical, Dietary Supplement, Functional Food, and Natural Health Products talent acquisition and executive search.

---

## System Overview

The platform identifies, scores, and ranks nutraceutical companies with the highest propensity to hire external recruitment agencies by aggregating live signals across:

1. **Headcount Growth & Hiring Velocity (30% Weight)**: YoY headcount growth percentage, real-time hiring velocity, and open requisition volume via Growjo and Career Traffic collectors.
2. **Facility Expansions, M&A & Web Traffic Surges (25% Weight)**: New plant openings, capacity upgrades, verified corporate acquisitions, and domain web traffic momentum via Serper, Owler, and Web Traffic collectors.
3. **Executive Leadership Turnover (20% Weight)**: C-Suite and VP appointments and departures tracked within a 6-month recency window via Serper.
4. **FDA Regulatory & Compliance Pressure (15% Weight)**: Official FDA Class I/II product recall enforcement and cGMP compliance risk scoring via openFDA.
5. **Nutraceutical Domain Alignment (10% Weight)**: Pre-seeded taxonomy of 1,022 verified nutraceutical companies across Finished Brands, Contract Manufacturers (CDMOs), Raw Ingredient Suppliers, and Testing CROs.

---

## Repository Architecture

```
bd-engine/
├── bd_engine/                           # Core Engine Package
│   ├── __init__.py                      # Package initialization & auto-env loading
│   ├── config.py                        # Taxonomies, seniority weights, & scoring rules
│   ├── bd_scorer.py                     # Master 0-100 Propensity Scoring Engine
│   └── collectors/                      # Multi-Signal Data Collectors
│       ├── __init__.py
│       ├── growjo_collector.py          # YoY Headcount Growth %, Revenue, Funding, Valuation
│       ├── owler_collector.py           # Revenue Bands, Acquisitions, Competitor Tracking
│       ├── career_traffic_collector.py  # Career Page & ATS Discovery, Open Roles, Traffic Index
│       ├── web_traffic_collector.py     # Monthly Web Visits, Signed 90-Day % Growth (Increments & Declines)
│       ├── apify_collector.py           # LinkedIn Headcount & Follower Snapshots
│       ├── serper_collector.py          # 6-Month Trade Press, Expansions, M&A, Exec Hires
│       └── openfda_collector.py         # Official FDA Recalls & Compliance Risk
│
├── app.py                               # FastAPI REST Server
├── run_pipeline.py                      # Unified 360-degree BD Scanner CLI
├── generate_bd_report.py                # Batch Intelligence Generator with Consolidated Primary Columns
├── nutraceutical_kb.json                # Knowledge Base (1,022 Verified Nutra Companies)
├── requirements.txt                     # Dependencies
└── .env.example                         # Environment Variables Template
```

---

## Setup and Quick Start

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Installation

```bash
git clone https://github.com/heuristic-solver/nutra-bd-engine.git
cd nutra-bd-engine
pip install -r requirements.txt
```

### 3. Environment Setup

Copy `.env.example` to `.env` and fill in your API credentials:

```bash
cp .env.example .env
```

```env
SERPER_API_KEY=your_serper_api_key
APIFY_API_TOKEN=your_apify_token
OPENFDA_API_KEY=your_openfda_key_optional
```

### 4. Running a 360-Degree BD Intelligence Scan

Scan any target company via CLI:

```bash
python run_pipeline.py --company "Thorne Research" --domain "thorne.com"
python run_pipeline.py --company "Nordic Naturals" --domain "nordicnaturals.com"
```

### 5. Running Batch Intelligence Reports

Run batch scanning across target companies to produce consolidated CSV reports:

```bash
python generate_bd_report.py
```

### 6. Starting the FastAPI REST Server

```bash
python app.py
```
The server will start on `http://127.0.0.1:8000`:
- **Propensity Scorecard**: `GET http://127.0.0.1:8000/api/v1/bd/score?company_name=Thorne+Research`
- **Summary Badge**: `GET http://127.0.0.1:8000/api/v1/bd/summary?company_name=Thorne+Research`
- **Full Dossier**: `GET http://127.0.0.1:8000/api/v1/bd/company?company_name=Thorne+Research`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

---

## Signal Dimensions & Propensity Weights

$$\text{Propensity Score} = \text{Growth (30)} + \text{Expansion (25)} + \text{Turnover (20)} + \text{Compliance (15)} + \text{Fit (10)}$$

| Dimension | Data Collectors | Max Points | What It Measures |
| :--- | :--- | :---: | :--- |
| **Headcount Growth & Hiring Velocity** | Growjo, Career Traffic, Apify | **30 pts** | Hyper-growth (+15% YoY), active hiring velocity, 30-day open roles, or staffing deficit |
| **Facility Expansions, M&A & Web Surges** | Serper (6-Month), Owler, Web Traffic | **25 pts** | New plant openings, M&A acquisitions, capital rounds, web traffic surges (+15%) |
| **Executive Leadership Moves** | Serper (6-Month) | **20 pts** | C-Suite/VP leadership appointments and department restructuring |
| **Compliance Pressure** | openFDA | **15 pts** | Class I/II product recalls and active FDA inspection audits |
| **Domain & Segment Alignment** | Knowledge Base | **10 pts** | Vertical alignment (CDMO, Finished Brand, Raw Ingredient Supplier) |

