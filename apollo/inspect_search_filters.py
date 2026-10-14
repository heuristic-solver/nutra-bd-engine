import json

with open("apollo_openapi.json", encoding="utf-8") as f:
    spec = json.load(f)

paths = spec.get("paths", {})

def inspect_body_properties(path, method="post"):
    op = paths.get(path, {}).get(method, {})
    content = op.get("requestBody", {}).get("content", {}).get("application/json", {})
    props = content.get("schema", {}).get("properties", {})
    print(f"\nProperties for {method.upper()} {path} ({len(props)} total):")
    for k, v in props.items():
        desc = v.get("description", "")
        t = v.get("type", "")
        print(f"  • {k} ({t}): {desc[:90]}")

inspect_body_properties("/mixed_people/api_search")
inspect_body_properties("/mixed_companies/search")
inspect_body_properties("/people/match")
inspect_body_properties("/organizations/enrich", method="get")
