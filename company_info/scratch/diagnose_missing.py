import json, os

with open('company_info_output/kb_full/apollo_harvest_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

with open('nutraceutical_kb.json', 'r', encoding='utf-8') as f:
    kb_raw = json.load(f)

kb_map = {k.get('company_name', '').strip().lower(): k for k in kb_raw if k.get('company_name')}

missing = [k for k, v in cache.items() if len(v.get('people', [])) == 0]
print(f"Total missing companies: {len(missing)}")

print("\nSample missing companies and their KB details:")
for i, m in enumerate(missing[:30]):
    kb_item = kb_map.get(m, {})
    web = kb_item.get('known_website') or kb_item.get('website') or 'No Website'
    hq = kb_item.get('headquarters') or kb_item.get('known_hq') or 'No HQ'
    spec = kb_item.get('known_speciality') or kb_item.get('specialty') or 'No Spec'
    print(f"{i+1:02d}. {m:<35} | Web: {web:<30} | HQ: {hq:<15}")
