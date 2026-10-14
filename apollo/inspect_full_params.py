import json
from collections import defaultdict

with open("apollo_openapi.json", encoding="utf-8") as f:
    spec = json.load(f)

paths = spec.get("paths", {})

def print_endpoint_details(path, method):
    op = paths.get(path, {}).get(method, {})
    if not op:
        return
    summary = op.get("summary", "")
    params = op.get("parameters", [])
    print(f"\n{'='*70}")
    print(f"{method.upper()} {path} ({len(params)} parameters) - {summary}")
    print(f"{'='*70}")
    for p in params:
        name = p.get("name")
        req = " [REQUIRED]" if p.get("required") else ""
        in_loc = p.get("in")
        desc = p.get("description", "").replace("\n", " ").strip()
        print(f"  • {name}{req} ({in_loc}): {desc[:100]}")

print("=== 1. SEARCH: PEOPLE (POST /mixed_people/api_search) ===")
print_endpoint_details("/mixed_people/api_search", "post")

print("\n=== 2. SEARCH: COMPANIES (POST /mixed_companies/search) ===")
print_endpoint_details("/mixed_companies/search", "post")

print("\n=== 3. ENRICHMENT: PEOPLE MATCH (POST /people/match) ===")
print_endpoint_details("/people/match", "post")

print("\n=== 4. ENRICHMENT: ORG ENRICH (GET /organizations/enrich) ===")
print_endpoint_details("/organizations/enrich", "get")
