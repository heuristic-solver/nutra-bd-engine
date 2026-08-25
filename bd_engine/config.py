# Nutraceutical industry keyword lists and scoring config for the BD Engine

# -------------------------------------------------------------------
# NUTRA COMPANY SEARCH KEYWORDS
# These are the keywords used to scope TheirStack queries to nutraceutical
# companies. Used in company-name and job-description filters.
# -------------------------------------------------------------------
NUTRA_INDUSTRY_KEYWORDS = [
    "nutraceutical",
    "dietary supplement",
    "nutritional supplement",
    "vitamins minerals supplements",
    "VMS",
    "sports nutrition",
    "protein supplement",
    "nootropic",
    "functional food",
    "functional beverage",
    "herbal supplement",
    "botanical extract",
    "probiotic",
    "prebiotic",
    "omega-3",
    "collagen supplement",
    "weight management supplement",
    "immune support supplement",
    "CDMO supplement",
    "contract manufacturer supplement",
    "gummy manufacturer",
    "softgel manufacturer",
    "encapsulation manufacturer",
    "natural health product",
    "OTC supplement",
    "private label supplement",
]

# -------------------------------------------------------------------
# NICHE NUTRA JOB TITLES
# Roles that are hard to fill internally, high search fee, strong BD signal
# Seniority weight is applied on top of these flags
# -------------------------------------------------------------------
NICHE_ROLE_KEYWORDS = [
    # Regulatory & Quality
    "regulatory affairs",
    "quality assurance",
    "quality systems",
    "cgmp",
    "cGMP",
    "gmp compliance",
    "quality control",
    "validation engineer",
    "microbiology",
    "analytical chemistry",
    "food safety",
    "dietary supplement compliance",
    "nsf certification",
    "fda compliance",
    "21 cfr",
    # Formulation & R&D
    "formulation scientist",
    "formulation chemist",
    "product development scientist",
    "nutraceutical scientist",
    "food scientist",
    "flavor scientist",
    "encapsulation scientist",
    "dietary supplement formulation",
    "sports nutrition formulation",
    # Supply Chain & Operations
    "raw material sourcing",
    "botanical sourcing",
    "ingredient procurement",
    "contract manufacturing",
    "cdmo management",
    "manufacturing operations",
    # Sales & Commercial
    "national accounts",
    "retail broker",
    "natural channel",
    "mass market supplement",
    "vitamin shoppe",
    "gnc account",
    "amazon supplement",
]

# -------------------------------------------------------------------
# SENIORITY WEIGHT MAP
# Higher seniority = higher placement fee = higher BD score weight
# -------------------------------------------------------------------
SENIORITY_WEIGHTS = {
    "c_suite": 3,     # CEO, CSO, COO, CFO, CMO, CTO
    "vp": 3,          # VP of anything
    "director": 2,    # Director of anything
    "senior_director": 2,
    "manager": 1,     # Manager / Senior Manager
    "lead": 1,        # Lead / Senior Lead
    "specialist": 1,
    "associate": 1,
    "default": 1,
}

SENIORITY_TITLE_PATTERNS = {
    "c_suite": ["chief", " cso", " coo", " ceo", " cfo", " cmo", " cto"],
    "vp": ["vice president", " vp "],
    "director": ["director", "sr. director", "senior director"],
    "manager": ["manager", "sr. manager", "senior manager"],
    "lead": ["lead ", "team lead", "tech lead"],
    "specialist": ["specialist", "analyst", "scientist", "engineer", "chemist"],
    "associate": ["associate", "coordinator", "jr.", "junior"],
}

# -------------------------------------------------------------------
# JOB STALENESS THRESHOLDS (days)
# -------------------------------------------------------------------
STALE_JOB_THRESHOLDS = {
    "watch":    30,   # Worth watching
    "pain":     60,   # Real talent pain
    "critical": 90,   # Critical — failed hires likely
}

# -------------------------------------------------------------------
# VELOCITY RATIO - SAMPLE SIZE CONFIDENCE MULTIPLIERS
# Prevent 1->2 posting noise from scoring as acceleration
# -------------------------------------------------------------------
VELOCITY_CONFIDENCE_MULTIPLIERS = {
    "low":    {"max_postings": 5,  "multiplier": 0.3},
    "medium": {"max_postings": 10, "multiplier": 0.6},
    "high":   {"max_postings": 999999, "multiplier": 1.0},
}

# -------------------------------------------------------------------
# NUTRA SEGMENT TAXONOMY
# -------------------------------------------------------------------
NUTRA_SEGMENTS = {
    "finished_brand_vms":        "Finished Goods Brand (VMS)",
    "finished_brand_sports":     "Finished Goods Brand (Sports Nutrition)",
    "finished_brand_nootropics": "Finished Goods Brand (Nootropics/Brain Health)",
    "finished_brand_functional": "Finished Goods Brand (Functional Bev/Food)",
    "cdmo":                      "Contract Manufacturer / CDMO",
    "ingredient_supplier":       "Raw Ingredient / Botanical Supplier",
    "testing_lab":               "Testing / Analytical Lab",
    "regulatory_consultancy":    "Regulatory / Quality Consultancy",
    "private_label":             "Private Label Manufacturer",
    "other":                     "Other Nutraceutical Adjacent",
}

# -------------------------------------------------------------------
# DEPARTMENT CLASSIFICATION KEYWORDS
# Maps job title keywords to functional department for BD insights
# -------------------------------------------------------------------
DEPT_KEYWORD_MAP = {
    "Quality / QA / QC": [
        "quality assurance", "quality control", "quality systems", "qa", "qc",
        "cgmp", "gmp", "food safety", "microbiology", "validation", "auditor",
    ],
    "Regulatory Affairs": [
        "regulatory affairs", "regulatory", "compliance", "fda", "21 cfr",
        "labeling", "claims", "registration",
    ],
    "R&D / Formulation": [
        "research", "r&d", "formulation", "scientist", "chemist", "product development",
        "innovation", "flavor", "analytical",
    ],
    "Operations / Manufacturing": [
        "operations", "manufacturing", "production", "plant", "facility",
        "supply chain", "procurement", "logistics", "warehouse",
    ],
    "Sales / Commercial": [
        "sales", "account", "business development", "commercial", "revenue",
        "broker", "retail", "channel", "national accounts",
    ],
    "Executive / General Management": [
        "chief", "president", "vp", "vice president", "director", "general manager",
        "managing director",
    ],
    "HR / Talent": [
        "human resources", "talent acquisition", "recruiter", "hrbp", "people",
        "hr manager", "workforce",
    ],
}

# -------------------------------------------------------------------
# SCORING WEIGHTS (sum = 100)
# Initial priors - calibrated via outcome regression over time
# -------------------------------------------------------------------
DEFAULT_SCORING_WEIGHTS = {
    "velocity":    20,
    "talent_pain": 20,
    "growth":      20,
    "expansion":   15,
    "domain_fit":  10,
    "regulatory":  15,
}

# -------------------------------------------------------------------
# API CONFIGURATION
# -------------------------------------------------------------------
THEIRSTACK_BASE_URL = "https://api.theirstack.com"
THEIRSTACK_JOBS_ENDPOINT = "/v1/jobs/search"
THEIRSTACK_COMPANIES_ENDPOINT = "/v1/companies/search"

DEFAULT_JOB_SEARCH_PARAMS = {
    "job_country_code_or": ["US"],
    "limit": 25,  # Free plan max is 25 per page
    "include_total_results": True,
    "order_by": [{"desc": True, "field": "date_posted"}],
}
