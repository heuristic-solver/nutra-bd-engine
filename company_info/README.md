# Company Info Intelligence & Movement Engine
**100% Zero-API Company Intelligence Scraper for the Nutraceutical Industry**

A fully custom-built, zero-paid-dependency intelligence gathering platform designed to scrape, extract, classify, and track:
1. **Role Changes & Key Personnel Movements**: Names of people who **joined**, were **promoted**, or **departed / left** companies, their past & new role titles, dates/recency, evidence snippets, and source URLs.
2. **Funding & Capital Structure**: Seed, Series A-D+, Growth Equity, Private Equity, Debt Financing, Grant rounds, normalized USD values, lead/participating investors, and valuations.
3. **Strategic Movements & Milestones**: Mergers & Acquisitions (M&A), plant & facility expansions, leadership restructuring, strategic partnerships, clinical trial publications, and product launches.
4. **Nutraceutical Knowledge Base Integration**: Instant native support for the 1,018-company `nutraceutical_kb.json` database.

---

## 🏗️ Architecture & Engines (Zero Paid APIs)

| Engine | Open Data Source | Signals Captured |
|---|---|---|
| **Multi-Engine Search** | Google News RSS, DuckDuckGo Lite, Bing Open Search | Executive appointments, departures, funding announcements, M&A, plant expansions. |
| **Public LinkedIn Harvester** | Open SERP Snippets & LinkedIn Public Headers | High-precision executive names, current roles, promotions, and alumni departures (`ex-`, `formerly at`). |
| **SEC EDGAR Harvester** | Open SEC EDGAR REST API | Form D (private offering equity funding notices) and Form 8-K (material corporate events/management changes). |
| **Direct Site Crawler** | Corporate Website (`/about`, `/team`, `/leadership`, `/press`, `/news`) | Current verified leadership rosters, press release announcements. |
| **Industry News Wire Harvester**| NutraIngredients, Nutraceuticals World, Natural Products Insider, PR Newswire Health RSS feeds | Verified nutraceutical industry appointments, clinical trials, product launches. |

---

## 📂 Folder Structure

```
company_info/
├── __init__.py               # Package root & exports
├── config.py                 # User agents, scrapers configuration, regex patterns
├── cli.py                    # Rich interactive terminal CLI
├── api.py                    # FastAPI REST API backend with Swagger UI
├── models/                   # Pydantic data models
│   ├── company.py            # CompanyProfile model & KB deserializer
│   ├── role_change.py        # RoleChangeEvent & MovementType (JOINED / DEPARTED / PROMOTED)
│   ├── funding.py            # FundingEvent & FundingRoundType with USD normalization
│   ├── movement.py           # StrategicMovementEvent & MovementCategory
│   └── report.py             # CompanyIntelligenceReport & summary aggregator
├── extractors/               # Precision regex & NLP heuristic parsers
│   ├── name_extractor.py     # Honorific-stripping human name extractor & entity filter
│   ├── role_extractor.py     # Functional title standardizer (C-Suite, VP, Director, Scientist)
│   ├── funding_parser.py     # Dollar/Euro amount normalizer, round classifier, investor parser
│   └── movement_classifier.py# Strategic corporate milestone classifier
├── engines/                  # Zero-API HTTP scrapers
│   ├── base_engine.py        # Resilient HTTP client with UA rotation & exponential backoff
│   ├── search_engine.py      # Multi-Search (Google RSS, DuckDuckGo Lite, Bing)
│   ├── linkedin_public_engine.py # Public LinkedIn signal parser
│   ├── edgar_engine.py       # SEC EDGAR Form D & 8-K REST harvester
│   ├── site_engine.py        # Autonomous corporate site crawler
│   └── news_wire_engine.py   # Industry RSS wire aggregator
├── pipeline/                 # Core orchestration & KB loading
│   ├── kb_loader.py          # 1,018-company KB search & filter engine
│   └── orchestrator.py       # CompanyIntelligenceEngine parallel orchestrator
├── exporters/                # Multi-format data exporters
│   ├── csv_exporter.py       # Segregated CSV datasets (Master, Roles, Funding, Movements)
│   ├── json_exporter.py      # Full nested JSON exports
│   └── markdown_reporter.py  # Executive markdown briefings
└── tests/                    # Unit & integration test suites
    ├── test_extractors.py    # Unit tests for name/role/funding/movement parsers
    ├── test_kb_loader.py     # Unit tests for KB querying & filtering
    └── test_end_to_end.py    # Live integration test suite
```

---

## 🚀 Quick Start & CLI Usage

### 1. Scan a Single Company
```bash
python -m company_info.cli scan "Vitaquest International"
```
Or specify a custom domain:
```bash
python -m company_info.cli scan "Gencor Pacific" --domain "gencorpacific.com"
```

### 2. Search & Filter the Nutraceutical KB (1,018 Companies)
```bash
# Search by keyword / name
python -m company_info.cli search-kb "ChromaDex"

# Filter by segment (e.g. Contract Manufacturing)
python -m company_info.cli search-kb "" --segment "Contract Manufacturing" --limit 15
```

### 3. Run Batch Intelligence Scans
```bash
# Scan 10 Contract Manufacturing companies from KB and export to CSV/JSON/MD
python -m company_info.cli batch-kb --limit 10 --segment "Contract Manufacturing" --workers 4 --output-dir "company_info_output/cohort_10co"
```

---

## 🌐 FastAPI REST Server

Launch the REST server:
```bash
python -m company_info.api
# Or via uvicorn:
uvicorn company_info.api:app --host 0.0.0.0 --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- Endpoints:
  - `POST /company/scan`: Scan a single company on-demand
  - `POST /batch/scan`: Scan a batch of companies with parallel workers
  - `GET /kb/search`: Query the 1,018-company nutraceutical knowledge base

---

## 📊 Exported Datasets

When running batch or single company scans, the engine generates four dedicated datasets:
1. `*_master_summary.csv`: Comprehensive overview with joined count, departed count, total funding USD, and strategic movement counts.
2. `*_role_changes.csv`: Granular row-by-row personnel changes segregated by `JOINED`, `DEPARTED`, `PROMOTED`, person name, role title, previous role, date, evidence, and source URL.
3. `*_funding_events.csv`: Granular row-by-row funding records with round type, raw amount, normalized USD amount, lead investors, and valuations.
4. `*_strategic_movements.csv`: Granular row-by-row corporate milestones (M&A, plant expansions, restructuring, partnerships).
5. `*.json`: Full nested JSON document.
6. `*.md`: Executive markdown intelligence briefing with markdown tables and clickable links.
