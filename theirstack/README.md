# TheirStack Intelligence Integration

This directory houses the OpenAPI 3.0 specification, integration blueprints, and API references for **TheirStack** (`https://api.theirstack.com`) within the Nutraceutical BD Engine.

## Files
- `theirstack_openapi.json`: Complete OpenAPI 3.0 specification covering all 49 endpoints across `/v0/` and `/v1/`.

## Key Capabilities Integrated into BD Engine (`bd_engine.py`)
1. **Company Discovery & Verification (`POST /v1/companies/search`):**
   - Automatically resolves company names, primary domains, and linked Apollo IDs (`apollo_id`).
   - Retrieves live 30-day hiring velocity (`num_jobs_last_30_days`) and total job counts.
2. **Reverse Account Search by Hiring Threshold (`job_filters` & `min_num_jobs_found`):**
   - Ability to filter nutraceutical accounts that have $\ge 2$ or $\ge 3$ open manufacturing/QA roles.
3. **Surveillance Lists (`/v0/company_lists`):**
   - Pre-configured target account surveillance for ongoing cohort tracking.
4. **Job Closure Tracking (`is_closed: true`, `closed_at_gte`):**
   - Detects newly filled leadership searches to trigger downstream recruiter outreach.
