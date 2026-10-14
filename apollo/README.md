# Complete Apollo.io Database & API Reference Manual
**Generated:** 2026-10-13 | **Total Endpoints:** 81 operations across 75 REST routes

---

## 1. Apollo Database Architecture & Data Entities

Apollo.io operates a dual-layer data architecture:

### A. The Global B2B Living Graph (275M+ People, 73M+ Companies)
- **People Entity (`person`):** Full name, first/last name, headline, current title, seniority level, departments, email address, email confidence score, email status (`verified`, `unverified`, `guessed`), direct dial/mobile phone numbers, LinkedIn URL, Twitter/Facebook handles, location (city, state, country), employment history array (past companies, past titles, start/end dates), education history.
- **Organization Entity (`organization`):** Company name, legal name, primary domain, website URL, LinkedIn URL, logo URL, estimated employee count, employee range, founded year, primary industry, industry tags, NAICS & SIC codes, revenue range ($ min/max), total funding raised, latest funding round (type, date, amount), investor list, technology stack (1,500+ indexed technologies), HQ address, phone, descriptions.
- **Hiring & Job Postings (`job_posting`):** Live job openings indexed across company career pages, title, department, location, date posted.
- **Corporate News & Events (`news_article`):** Executive moves, product launches, funding announcements, M&A press releases categorized by tag and publication date.
- **Intent & Technographics (`intent_topic` / `technology`):** High-intent surge topics and current active technologies used by accounts.

### B. Workspace CRM & Engagement Database
- **Accounts (`account`):** Accounts imported or tracked in the user's workspace, tied to sales reps (owners), pipeline stages (`account_stage`), and custom fields.
- **Contacts (`contact`):** People imported into the workspace CRM with contact stages (`contact_stage`), ownership permissions, sequence enrollment history, and deal associations.
- **Sequences (`emailer_campaign`):** Multi-step outbound cadences (automated emails, manual email tasks, phone call tasks, LinkedIn outreach tasks), sending schedules (`emailer_schedule`), and multi-mailbox rotation.
- **Outreach Messages (`emailer_message`):** Draft, scheduled, sent, and delivered outreach emails with open/click/reply tracking.
- **Deals / Opportunities (`opportunity`):** Sales pipelines, deal stages (`opportunity_stage`), expected revenue, close dates.
- **Tasks (`task`):** Action items for reps: call, email, action tasks with priority, due date, status (`completed`, `skipped`).
- **Conversations (`conversation`):** Recorded sales calls, AI transcription, speaker identification, and conversation intelligence.
- **Custom Fields (`typed_custom_field`):** Workspace-defined metadata fields extensible across contact and account records.
- **Lists & Labels (`label`):** Tagging and segmentation system for organizing records.


---

## 2. Complete API Endpoint Inventory by Category

### Category: AI ASSISTANT (1 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `POST` | `/agents/task` | Run an Assistant task | `run-an-assistant-task` |


### Category: ACCOUNTS (8 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `POST` | `/accounts` | Create an account | `create-an-account` |
| `PATCH` | `/accounts/{account_id}` | Update an account | `update-an-account` |
| `POST` | `/accounts/search` | Search for accounts | `search-for-accounts` |
| `POST` | `/accounts/bulk_create` | Bulk create accounts | `bulk-create-accounts` |
| `POST` | `/accounts/bulk_update` | Bulk update accounts | `bulk-update-accounts` |
| `POST` | `/accounts/update_owners` | Update account owner for multiple accounts | `update-account-ownership` |
| `GET` | `/account_stages` | List account stages | `list-account-stages` |
| `GET` | `/accounts/{id}` | View an account | `get_accounts{id}` |


### Category: ANALYTICS (1 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `POST` | `/reports/sync_report` | Query analytics report | `sync-report` |


### Category: CALLS (3 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `GET` | `/phone_calls/search` | Search for calls | `get_phone_callssearch` |
| `POST` | `/phone_calls` | Create call records | `phonecalls_create` |
| `PUT` | `/phone_calls/{id}` | Update call records | `put_phone_callsupdate` |


### Category: CONTACTS (10 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `POST` | `/contacts` | Create a contact | `create-a-contact` |
| `PATCH` | `/contacts/{contact_id}` | Update a contact | `update-a-contact` |
| `GET` | `/contacts/{contact_id}` | View a contact | `view-a-contact` |
| `POST` | `/contacts/{contact_id}/opportunities` | View associated deals | `view-associated-deals` |
| `POST` | `/contacts/search` | Search for contacts | `search-for-contacts` |
| `POST` | `/contacts/update_stages` | Update contact stage for multiple contacts | `update-contact-stage` |
| `POST` | `/contacts/update_owners` | Update contact owner for multiple contacts | `update-contact-ownership` |
| `POST` | `/contacts/bulk_create` | Bulk create contacts | `bulk-create-contacts` |
| `POST` | `/contacts/bulk_update` | Bulk update contacts | `bulk-update-contacts` |
| `GET` | `/contact_stages` | List contact stages | `list-contact-stages` |


### Category: CONVERSATIONS (4 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `POST` | `/conversations/search` | Search conversations | `search-conversations` |
| `GET` | `/conversations/{id}` | Get conversations info | `get-conversations-info` |
| `POST` | `/conversations/export` | Export conversations | `export-conversations` |
| `GET` | `/conversations/export/{id}` | Get conversations export | `get-conversations-export` |


### Category: DEALS (5 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `POST` | `/opportunities` | Create deal | `create-deal` |
| `GET` | `/opportunities/search` | List all deals | `list-all-deals` |
| `GET` | `/opportunities/{opportunity_id}` | View deal | `view-deal` |
| `PATCH` | `/opportunities/{opportunity_id}` | Update deal | `update-deal` |
| `GET` | `/opportunity_stages` | List deal stages | `list-deal-stages` |


### Category: EMAILER MESSAGES (4 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `POST` | `/emailer_messages` | Create an email draft | `create-an-email-draft` |
| `POST` | `/emailer_messages/{id}/send_now` | Send email now | `send-email-now` |
| `POST` | `/emailer_messages/get_content` | Get email content | `get-email-content` |
| `POST` | `/emailer_messages/email_send_status` | Check email send status | `check-email-send-status` |


### Category: ENRICHMENT (4 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `POST` | `/people/match` | People enrichment | `people-enrichment` |
| `POST` | `/people/bulk_match` | Bulk people enrichment | `bulk-people-enrichment` |
| `GET` | `/organizations/enrich` | Organization enrichment | `organization-enrichment` |
| `POST` | `/organizations/bulk_enrich` | Bulk organization enrichment | `bulk-organization-enrichment` |


### Category: FIELDS (4 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `GET` | `/fields` | Get a list of fields | `get-a-list-of-fields` |
| `POST` | `/fields` | Create a custom field | `create-a-custom-field` |
| `PATCH` | `/fields` | Update a custom field | `update-a-custom-field` |
| `GET` | `/typed_custom_fields` | Get a list of all custom fields | `get-a-list-of-all-custom-fields` |


### Category: MISCELLANEOUS (11 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `GET` | `/users/search` | Get a list of users | `get-a-list-of-users` |
| `GET` | `/email_accounts` | Get a list of email accounts | `get-a-list-of-email-accounts` |
| `GET` | `/labels` | Get a list of all lists | `get-a-list-of-all-lists` |
| `POST` | `/labels` | Create a list | `create-a-list` |
| `PATCH` | `/labels/{id}` | Update a list | `update-a-list` |
| `POST` | `/labels/add_entity_ids_to_label_names` | Add records to a list | `add-records-to-a-list` |
| `POST` | `/labels/remove_entity_ids_from_label_names` | Remove records from a list | `remove-records-from-a-list` |
| `GET` | `/webhook_result/{request_id}` | Poll webhook result | `poll-webhook-result` |
| `POST` | `/usage_stats/credit_usage_stats` | View credit usage stats | `view-credit-usage-stats` |
| `POST` | `/usage_stats/api_usage_stats` | View API usage stats and rate limits | `post_apiusage` |
| `GET` | `/notes` | Get a list of notes | `get-a-list-of-notes` |


### Category: SEARCH (6 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `POST` | `/mixed_people/api_search` | People API search | `people-api-search` |
| `POST` | `/mixed_companies/search` | Organization search | `organization-search` |
| `GET` | `/organizations/{organization_id}/job_postings` | Organization job postings | `organization-jobs-postings` |
| `GET` | `/organizations/{id}` | Get complete organization info | `get_organizations{id}` |
| `GET` | `/people/{id}` | Get complete person info | `get_people{id}` |
| `POST` | `/news_articles/search` | News articles search | `news_articles_search` |


### Category: SEQUENCES (12 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `GET` | `/emailer_schedules` | List email schedules | `list-email-schedules` |
| `POST` | `/emailer_campaigns/search` | Search for sequences | `search-for-sequences` |
| `POST` | `/emailer_campaigns/{sequence_id}/add_contact_ids` | Add contacts to a sequence | `add-contacts-to-sequence` |
| `POST` | `/emailer_campaigns/remove_or_stop_contact_ids` | Update contact status in a sequence | `update-contact-status-sequence` |
| `POST` | `/sequences` | Create a sequence | `create-sequence` |
| `PUT` | `/sequences/{id}` | Update a sequence | `update-sequence` |
| `GET` | `/emailer_messages/{id}/activities` | Check email stats | `get_emailstats` |
| `GET` | `/emailer_messages/search` | Search for outreach emails | `emailer_messages/search` |
| `POST` | `/emailer_campaigns/activity_feed` | Get contact sequence activity | `get-contact-sequence-activity` |
| `POST` | `/emailer_campaigns/{sequence_id}/approve` | Activate a sequence | `approve-sequence` |
| `POST` | `/emailer_campaigns/{sequence_id}/abort` | Deactivate a sequence | `abort-sequence` |
| `POST` | `/emailer_campaigns/{sequence_id}/archive` | Archive a sequence | `archive-sequence` |


### Category: TASKS (7 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `POST` | `/tasks` | Create a task | `create-a-task` |
| `POST` | `/tasks/bulk_create` | Bulk create tasks | `bulk-create-tasks` |
| `GET` | `/tasks/{id}` | Get a task | `get-a-task` |
| `PATCH` | `/tasks/{id}` | Update a task | `update-a-task` |
| `POST` | `/tasks/{id}/complete` | Complete a task | `complete-a-task` |
| `POST` | `/tasks/{id}/skip` | Skip a task | `skip-a-task` |
| `POST` | `/tasks/search` | Search for tasks | `search-tasks` |


### Category: UNTAGGED (1 Endpoints)

| Method | Endpoint Route | Description / Purpose | Operation ID |
|---|---|---|---|
| `GET` | `/users/api_profile` | Get current user profile | `get-current-user-profile` |



---

## 3. Authentication, Credits & Rate Limits

### Authentication Header
```http
X-Api-Key: YOUR_APOLLO_API_KEY
Content-Type: application/json
Cache-Control: no-cache
```
> Note: Some endpoints (such as `usage_stats`, `reports/sync_report`, or bulk operations) require a **Master API Key** generated by an account administrator.

### Credit Consumption Matrix
| Credit Type | Key | Operations Funded |
|---|---|---|
| Lead Credit | `lead_credit` | Email reveals, email verification, people enrichment (`POST /people/match`) |
| Direct Dial Credit | `direct_dial_credit` | Mobile and direct phone number reveals (`reveal_phone_number=true`) |
| Export Credit | `export_credit` | CSV data exports |
| Search Credit | `1 credit / page` | Job postings (`GET /organizations/{id}/job_postings`), News (`POST /news_articles/search`) |
| Free (0 Credits) | `0 credits` | People Search (`POST /mixed_people/api_search`), Org Search (`POST /mixed_companies/search`), CRM CRUD, Tasks, Sequences |

### Rate Limits Monitoring
- Endpoint: `POST /api/v1/usage_stats/api_usage_stats` (returns per-minute, per-hour, and daily request thresholds)
- Endpoint: `POST /api/v1/usage_stats/credit_usage_stats` (returns cycle limit, consumed, and left_over balances for all credit pools)
