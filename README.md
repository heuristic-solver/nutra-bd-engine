# Nutraceutical Business Development (BD) Engine

A proactive, multi-signal Business Development intelligence engine built specifically for **Nutraceutical, Dietary Supplement, Functional Food, and Natural Health Products** talent acquisition and executive search.

---

## System Overview

The platform identifies, scores, and ranks nutraceutical companies with the highest propensity to hire external recruitment agencies by aggregating live signals across:

1. **Hiring Velocity Acceleration ($V_{R,\text{adj}}$)**: Sample-size-dampened velocity ratios tracking sudden hiring surges.
2. **Talent Pain Index (TPI)**: Multiplies open-role vacancy aging ($>30, 60, 90$ days) against seniority weights ($1\times, 2\times, 3\times$) and niche nutra role classifications.
3. **6-Month Trade Press & Market Expansion**: Tracks new facility construction, plant openings, M&A buyouts, and executive appointments across 8 leading industry publications.
4. **FDA Regulatory & Compliance Pressure**: Real-time product recall tracking (Class I, II, III) via openFDA to identify urgent QA/QC & Regulatory remediation hiring needs.
5. **Nutraceutical Knowledge Base**: Pre-seeded database of **1,022 verified nutraceutical companies** across Finished Brands, CDMOs, Raw Ingredient Suppliers, and Testing CROs.

---

## Repository Architecture

```
bd-engine/
├── bd_engine/                           # Core Engine Package
│   ├── __init__.py
│   ├── config.py                        # Taxonomies, seniority weights, & scoring rules
│   └── collectors/                      # Data Source Collectors
│       ├── __init__.py
│       ├── theirstack_collector.py      # Live Jobs, Velocity, & TPI calculations
│       ├── serper_collector.py          # 6-Month Trade Press, Expansions, M&A, Exec Hires
│       └── openfda_collector.py         # Official FDA Recalls & Compliance Risk
│
├── app.py                               # FastAPI REST Server
├── run_pipeline.py                       # Unified 360° BD Scan CLI Runner
├── run_theirstack.py                    # Dedicated TheirStack Prospector CLI
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
THEIRSTACK_API_TOKEN=your_theirstack_jwt_token
SERPER_API_KEY=your_serper_api_key
OPENFDA_API_KEY=your_openfda_key_optional
```

### 4. Running a 360° BD Intelligence Scan

Scan any company from `nutraceutical_kb.json` via CLI:

```bash
python run_pipeline.py --company "Herbalife"
python run_pipeline.py --company "NOW Health Group"
python run_pipeline.py --company "OmniActive Health Technologies"
```

### 5. Starting the FastAPI REST Server

```bash
python app.py
```
The server will start on `http://127.0.0.1:8000`:
- **Summary Badge (for Job Cards)**: `GET http://127.0.0.1:8000/api/v1/bd/summary?company_name=Herbalife`
- **Full 360° Dossier**: `GET http://127.0.0.1:8000/api/v1/bd/company?company_name=Herbalife`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

---

## Signal Formulas and Dimensions

| Signal Dimension | Data Source | Math & Logic |
| :--- | :--- | :--- |
| **Hiring Velocity ($V_{R,\text{adj}}$)** | TheirStack | $\frac{\text{Jobs Posted (Last 30d)}}{\text{Jobs Posted (31-90d)} / 2} \times \text{Confidence Multiplier}$ |
| **Talent Pain Index (TPI)** | TheirStack | $\sum \min\left(1.0, \frac{\text{Days Open}}{90}\right) \times \text{Seniority Weight} \times \text{Niche Multiplier}$ |
| **Market Expansion Signals** | Serper (6-Month) | Detects new plant construction, lab additions, and M&A integration |
| **Compliance Pressure** | openFDA | Computes automated 0–100 Regulatory Risk score from Class I/II/III recalls |
