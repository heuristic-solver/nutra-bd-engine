import json
from collections import defaultdict

with open("apollo_openapi.json", encoding="utf-8") as f:
    spec = json.load(f)

paths = spec.get("paths", {})
by_tag = defaultdict(list)
all_endpoints = []

for path, methods in paths.items():
    for method, details in methods.items():
        if method.lower() in ["get", "post", "put", "patch", "delete"]:
            tags = details.get("tags", ["Untagged"])
            summary = details.get("summary", "")
            desc = details.get("description", "")
            op_id = details.get("operationId", "")
            tag = tags[0] if tags else "Untagged"
            item = {
                "method": method.upper(),
                "path": path,
                "summary": summary,
                "description": desc,
                "operation_id": op_id,
                "tag": tag,
                "parameters": [p.get("name") for p in details.get("parameters", [])],
                "request_body": "requestBody" in details
            }
            by_tag[tag].append(item)
            all_endpoints.append(item)

print(f"Total endpoints found: {len(all_endpoints)}")
print("\nBreakdown by Category / Tag:")
for tag, eps in sorted(by_tag.items()):
    print(f"\n==========================================")
    print(f"=== {tag.upper()} ({len(eps)} Endpoints) ===")
    print(f"==========================================")
    for ep in eps:
        m = ep["method"]
        p = ep["path"]
        s = ep["summary"]
        print(f"  {m:6} {p:45} | {s}")

# Save detailed analysis
with open("apollo_endpoints_catalog.json", "w", encoding="utf-8") as f:
    json.dump({
        "total_endpoints": len(all_endpoints),
        "categories": {tag: eps for tag, eps in sorted(by_tag.items())},
        "all_endpoints": all_endpoints
    }, f, indent=2)
print("\nCatalog saved to apollo_endpoints_catalog.json")
