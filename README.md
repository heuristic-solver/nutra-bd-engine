# Nutraceutical Business Development (BD) Engine

An automated intelligence and reasoning pipeline built specifically for executive recruiting, talent acquisition, and business development in the **Nutraceutical, Dietary Supplement, Functional Food, and Pharmaceutical Contract Manufacturing (CDMO)** sectors.

The engine replaces generic cold pitching with factual, multi-source operational diagnostics by fusing job staleness, corporate hiring velocity, verified leadership transitions, industrial automation stacks, and regulatory compliance records.

---

## Architecture & Integration Modules

```
bd-engine/
├── bd_engine.py                               # Master BD Engine (Sourcing, Enrichment, Scoring & Reasoning)
│
├── apollo/                                    # Apollo.io Intelligence Subsystem
│   ├── apollo_openapi.json                    # Official Apollo OpenAPI v2 specification
│   ├── apollo_endpoints_catalog.json          # Cataloged 75 endpoints & 81 operations
│   └── README.md                              # Comprehensive Apollo API & endpoint reference
│
├── theirstack/                                # TheirStack Job Telemetry & Account Discovery
│   ├── theirstack_openapi.json                # Complete OpenAPI 3.0 specification (49 endpoints)
│   └── README.md                              # Job search filters & credit optimization reference
│
├── apify/                                     # Apify Cloud Scraper Subsystem (Cookie-Free)
│   ├── client.py                              # Safe wrapper with rate limit & quota protections
│   ├── actors.py                              # 0-Day LinkedIn post radar & company feed scrapers
│   └── runner.py                              # Verification & test runner
│
├── data/                                      # Data Store & Benchmark Cohorts
│   ├── scrape_sample.csv                      # Sample 10-job benchmark cohort
│   ├── stale_jobs_live.csv                    # Live stale requisitions (>= 45 days open)
│   └── random_10_companies.csv                # Account test cohort
│
├── .env.example                               # Environment template
├── requirements.txt                           # Python dependencies
└── LICENSE                                    # License
```

---

## Data Providers & Multi-Source Signal Layers

### 1. TheirStack Telemetry & Job Sourcing (`theirstack/`)
* **Autonomous Stale Job Hunting (`/v1/jobs/search`):** Sources live US manufacturing and QA jobs that have been open for $\ge 45$ days across hundreds of ATS platforms, automatically stripping out third-party recruiting agencies.
* **Hiring Velocity Metric (`num_jobs_last_30_days`):** Measures 30-day corporate hiring momentum to detect expansion crunches versus hiring freezes.
* **Credit Optimized:** Company queries locked to `"limit": 1` to strictly consume 3 credits flat.

### 2. Apollo.io Intelligence Engine (`apollo/`)
* **Organization Firmographics:** Verified employee headcounts, estimated revenues, and installed technology stacks (ERP, QMS, SCADA/PLC).
* **Executive Decision-Makers:** Identification and contact unmasking of VPs, Directors, and C-Suite hiring authorities.
* **Verified Mobility Tracking:** Automated parsing of `employment_history[]` arrays tracking internal promotions and external hires strictly for 2025–2026.

### 3. openFDA Compliance Scanner
* **Regulatory Radar:** Real-time query of the FDA drug and dietary supplement enforcement database.
* **Audit Exposure:** Detects active warning letters, Class I/II/III recalls, and CGMP deviations (e.g. raw material excipient contaminations).

### 4. Apify LinkedIn Social Radar (`apify/`)
* **0-Day Post Search (`harvestapi/linkedin-post-search`):** Captures individual posts announcing departures (*"my last day..."*, *"new chapter..."*) and joins without requiring personal LinkedIn cookies or accounts.
* **Company Feed Monitor (`harvestapi/linkedin-company-posts`):** Scrapes official company posts for welcome announcements, promotions, and facility expansions.

### 5. Multi-Signal Reasoning Engine (Claude)
* **Anthropic Claude Integration:** Powered by Anthropic's Claude API (`claude-sonnet-5` / `claude-haiku-5-5`) for high-order executive diagnostic thesis generation.
* **Structural Pattern Discovery:** Uncovers non-obvious operational relations (`COMMERCIAL_PLANT_IMBALANCE`, `UNANNOUNCED_DEPARTURE`, `COMPLIANCE_FIRE_DRILL`, `TECH_STACK_BOTTLENECK`).
* **Financial Drag Modeling:** Estimates monthly operational drag ($35,000–$60,000/month in overtime burn, lot holds, and batch release delays).
* **Deterministic Fallback:** Robust heuristic backup ensures the pipeline completes successfully even if network or API limits occur.

---

## Setup & Execution

### 1. Environment Configuration
```bash
cp .env.example .env
```
Fill in your active API keys in `.env`:
* `APOLLO_API_KEY`: Apollo.io API key
* `THEIRSTACK_API_KEY`: TheirStack API key
* `APIFY_TOKEN`: Apify API token (optional, for 0-day LinkedIn post scraping)
* `PDL_API_KEY`: People Data Labs API key (optional)
* `ANTHROPIC_API_KEY`: Anthropic API key for Claude reasoning
* `ANTHROPIC_MODEL`: Claude model to use (default: `claude-sonnet-5`)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Running the Engine

#### Run on a custom input CSV:
```bash
python bd_engine.py --csv data/scrape_sample.csv
```

#### Run autonomous stale job hunt (fetch live jobs >= 45 days open from TheirStack):
```bash
python bd_engine.py --fetch-stale --min-age 45 --limit 20
```

#### Run in database-only mode (bypassing Apify post queries):
```bash
python bd_engine.py --csv data/scrape_sample.csv --no-social
```

#### Backtest evaluation date against a specific historical baseline:
```bash
python bd_engine.py --csv data/scrape_sample.csv --date 2026-10-01
```

---

## Output Files
* `job_bd_leads_scored.csv`: Complete ranked and scored spreadsheet. Automatically copied to your local `Downloads` folder upon run completion.
* `job_bd_leads_full.json`: Full JSON output containing all qualitative reasoning, hidden relations, and operational drag models.

