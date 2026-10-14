import json

with open("apollo_openapi.json", encoding="utf-8") as f:
    spec = json.load(f)

components = spec.get("components", {})
schemas = components.get("schemas", {})

print(f"Total schemas in components: {len(schemas)}")
print("\nKey Database Entity Schemas:")
for s_name in sorted(schemas.keys()):
    schema = schemas[s_name]
    props = schema.get("properties", {})
    p_names = list(props.keys())
    print(f"\n--- {s_name} ({len(p_names)} fields) ---")
    print(f"  Sample Fields: {', '.join(p_names[:15])}")
