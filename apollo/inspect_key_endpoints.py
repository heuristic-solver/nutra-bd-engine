import json

with open("apollo_openapi.json", encoding="utf-8") as f:
    spec = json.load(f)

paths = spec.get("paths", {})

def inspect_endpoint(path, method="post"):
    op = paths.get(path, {}).get(method, {})
    if not op:
        print(f"Endpoint {method.upper()} {path} not found")
        return
    
    print(f"\n==================================================")
    print(f"{method.upper()} {path} - {op.get('summary')}")
    print(f"==================================================")
    print("Description:", op.get("description", "").strip())
    
    # Query parameters
    params = op.get("parameters", [])
    if params:
        print("\nQuery / Path Parameters:")
        for p in params:
            req = " (REQUIRED)" if p.get("required") else ""
            print(f"  • {p.get('name')}{req} [{p.get('in')}]: {p.get('description', '')}")
            
    # Request Body
    req_body = op.get("requestBody", {})
    if req_body:
        content = req_body.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})
        props = schema.get("properties", {})
        required = schema.get("required", [])
        print(f"\nRequest Body Properties ({len(props)} fields):")
        for prop_name, prop_data in props.items():
            req_str = " [REQUIRED]" if prop_name in required else ""
            p_type = prop_data.get("type", "object")
            p_desc = prop_data.get("description", "")
            print(f"  • {prop_name}{req_str} ({p_type}): {p_desc[:80]}")

# Inspect primary search and enrichment endpoints
key_endpoints = [
    ("/mixed_people/api_search", "post"),
    ("/mixed_companies/search", "post"),
    ("/people/match", "post"),
    ("/people/bulk_match", "post"),
    ("/organizations/enrich", "get"),
    ("/organizations/bulk_enrich", "post"),
    ("/organizations/{organization_id}/job_postings", "get"),
    ("/news_articles/search", "post"),
    ("/emailer_campaigns/search", "post"),
    ("/emailer_campaigns/{sequence_id}/add_contact_ids", "post"),
    ("/usage_stats/api_usage_stats", "post"),
    ("/usage_stats/credit_usage_stats", "post"),
]

for ep, method in key_endpoints:
    inspect_endpoint(ep, method)
