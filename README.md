# Nutraceutical Business Development (BD) Engine

A multi-source talent acquisition and business development intelligence engine built specifically for Nutraceutical, Functional Food, Dietary Supplement, and Natural Health Products recruitment.

---

## Architecture & Integration Modules

```
bd-engine/
├── apollo/                                    # Apollo.io Intelligence Subsystem
│   ├── apollo_openapi.json                    # Full official Apollo OpenAPI v2 specification
│   ├── apollo_endpoints_catalog.json          # Cataloged 75 endpoints & 81 operations
│   ├── run_apollo_20co_rich.py                # 20-company live enrichment & executive discovery
│   ├── find_apollo_role_changes.py            # Deep leadership join & departure tracking
│   ├── apollo_20co_companies_enriched.csv     # Master firmographics & technology stack
│   ├── apollo_20co_decision_makers.csv        # Key senior recruitment decision-makers
│   ├── apollo_20co_role_changes.csv           # 101 tracked career events (joins, departures)
│   └── README.md                              # Comprehensive Apollo API & endpoint reference
│
├── run_signalbase_20co.py                     # SignalBase runner for 20 nutraceutical companies
├── generate_demo_csv.py                       # SignalBase core signal enrichment & formatting
├── update_demo_csv.py                         # SignalBase signal updater
├── signalbase_demo_enriched.csv               # Enriched SignalBase dataset
├── signalbase_20co_enriched.csv               # 20-company SignalBase run dataset
│
├── run_pdl_demo.py                            # People Data Labs (PDL) demo enrichment
├── run_pdl_full.py                            # PDL full dataset enrichment pipeline
├── export_pdl_results.py                      # PDL output exporter
├── build_full_results.py                      # Multi-source intelligence consolidator
│
├── Demo List - Sheet1.csv                     # Primary nutraceutical input targets
├── .env.example                               # Environment template
└── LICENSE                                    # License
```

---

## Data Providers & Signal Pipelines

### 1. Apollo.io Intelligence Engine (`apollo/`)
* **Endpoint Catalog:** Fully mapped and parsed 75 REST routes.
* **Firmographics & Stack:** Organization enrichment, annual revenues, employee ranges, tech stacks, and active job openings count.
* **Executive Decision-Makers:** Identification of VP, Director, and C-Suite contacts.
* **Role Change & Departure Detection:** Automated parsing of `employment_history[]` arrays tracking recent leadership joins and departures across candidate pools.

### 2. SignalBase Signals (`run_signalbase_20co.py`, `generate_demo_csv.py`)
* Connects to `https://www.trysignalbase.com/api/v2`.
* Tracks hiring surges, executive job changes, funding events, and corporate acquisitions.

### 3. People Data Labs (PDL) (`run_pdl_demo.py`, `run_pdl_full.py`)
* Company firmographics and person roster enrichment.
* Historical career transitions and leadership departure analytics.

---

## Setup & Execution

### 1. Environment Setup
```bash
cp .env.example .env
```
Fill in the respective API keys (`APOLLO_API_KEY`, `SIGNALBASE_API_KEY`, `PDL_API_KEY`).

### 2. Running Apollo Enrichment
```bash
python apollo/run_apollo_20co_rich.py
python apollo/find_apollo_role_changes.py
```

### 3. Running SignalBase Pipeline
```bash
python run_signalbase_20co.py
```

### 4. Running PDL Pipeline
```bash
python run_pdl_demo.py
```
