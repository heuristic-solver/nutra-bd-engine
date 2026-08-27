# Nutraceutical Business Development (BD) Engine

A proactive, multi-signal Business Development intelligence engine built specifically for **Nutraceutical, Dietary Supplement, Functional Food, and Natural Health Products** talent acquisition and executive search.

---

## System Overview

The platform identifies, scores, and ranks nutraceutical companies with the highest propensity to hire external recruitment agencies by aggregating live signals across:

1. **LinkedIn Headcount Growth Trajectory (30% Weight)**: Real-time employee headcount tracking and growth percentage deltas via Apify.
2. **6-Month Facility Expansions & M&A (25% Weight)**: Tracks new plant openings, capacity expansions, and private equity investments via Serper.
3. **Executive Leadership Turnover (20% Weight)**: Real-time alerts on C-Suite and VP appointments and departures via Serper.
4. **FDA Regulatory & Compliance Pressure (15% Weight)**: Real-time product recall tracking (Class I, II, III) and cGMP risk scoring via openFDA.
5. **Nutraceutical Domain Alignment (10% Weight)**: Pre-seeded taxonomy of **1,022 verified nutraceutical companies** across Finished Brands, CDMOs, Raw Ingredient Suppliers, and Testing CROs.

---

## Repository Architecture

```
bd-engine/
├── bd_engine/                           # Core Engine Package
│   ├── __init__.py
│   ├── config.py                        # Taxonomies, seniority weights, & scoring rules
│   ├── bd_scorer.py                     # Master 0-100 Propensity Scoring Engine
│   └── collectors/                      # Multi-Signal Data Collectors
│       ├── __init__.py
│       ├── apify_collector.py           # LinkedIn Headcount & Growth Rate Scraper
│       ├── serper_collector.py          # 6-Month Trade Press, Expansions, M&A, Exec Hires
│       └── openfda_collector.py         # Official FDA Recalls & Compliance Risk
│
├── app.py                               # FastAPI REST Server
├── run_pipeline.py                       # Unified 360° BD Propensity Scanner CLI
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

### 4. Running a 360° BD Intelligence Scan

Scan any company from `nutraceutical_kb.json` via CLI:

```bash
python run_pipeline.py --company "Herbalife"
python run_pipeline.py --company "NOW Health Group"
python run_pipeline.py --company "OmniActive Health Technologies" --linkedin "https://www.linkedin.com/company/omniactive-health-technologies"
```

### 5. Starting the FastAPI REST Server

```bash
python app.py
```
The server will start on `http://127.0.0.1:8000`:
- **Propensity Scorecard**: `GET http://127.0.0.1:8000/api/v1/bd/score?company_name=Herbalife`
- **Summary Badge (for Job Cards)**: `GET http://127.0.0.1:8000/api/v1/bd/summary?company_name=Herbalife`
- **Full 360° Dossier**: `GET http://127.0.0.1:8000/api/v1/bd/company?company_name=Herbalife`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

---

## Signal Dimensions & Propensity Weights

$$\text{Propensity Score} = \text{Growth (30)} + \text{Expansion (25)} + \text{Turnover (20)} + \text{Compliance (15)} + \text{Fit (10)}$$

| Dimension | Data Source | Max Points | What It Measures |
| :--- | :--- | :---: | :--- |
| **Headcount Growth Trajectory** | Apify | **30 pts** | Hyper-growth ($\ge 15\%$) scaling strain or severe attrition deficit |
| **Facility Expansions & M&A** | Serper (6-Month) | **25 pts** | New manufacturing plant openings, capacity upgrades, capital rounds |
| **Executive Leadership Moves** | Serper (6-Month) | **20 pts** | C-Suite/VP leadership turnover and team restructuring |
| **Compliance Pressure** | openFDA | **15 pts** | Class I/II product recalls and active FDA inspection audits |
| **Domain & Segment Alignment** | Knowledge Base | **10 pts** | Vertical alignment (CDMO, Finished Brand, Raw Ingredient Lab) |
