import os, requests, json, time, re
from dotenv import load_dotenv

load_dotenv('.env')
akey = os.getenv('APOLLO_API_KEY')
headers_apollo = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'X-Api-Key': akey}

with open('company_info_output/kb_full/apollo_harvest_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

missing_keys = [k for k, v in cache.items() if len(v.get('people', [])) == 0]
print(f"Total missing companies in cache: {len(missing_keys)}")

resolved = 0
for i, k in enumerate(missing_keys[:30]):
    clean_k = re.sub(r'[\s,]+(inc\.?|llc\.?|ltd\.?|gmbh|corp\.?|co\.?|s\.?r\.?l\.?|s\.?a\.?|pvt\.?|private|limited|group|holdings|holding|usa|global|americas|pacific|international|ag|se|kgaa|solutions|technologies|laboratories|labs|pharma|nutraceuticals|nutra|nutrition|ingredients|gbr|bv|o|oy|ab).*$', '', k, flags=re.IGNORECASE).strip()
    clean_k = re.sub(r'^(chemische fabrik|laboratoires|laboratories|laboratorios|societe|institut|instituto|industria|industrias|compagnie|fabbrica)\s+', '', clean_k, flags=re.IGNORECASE).strip()
    clean_k = re.sub(r'\s+(by|a\s+unit\s+of|a\s+kerry\s+company|a\s+division\s+of)\s+.*$', '', clean_k, flags=re.IGNORECASE).strip()
    clean_k = re.sub(r'\(.*?\)', '', clean_k).strip()

    p = []
    # 1. q_keywords
    try:
        r = requests.post('https://api.apollo.io/v1/mixed_people/api_search', headers=headers_apollo, json={'q_keywords': k, 'per_page': 3}, timeout=5)
        if r.status_code == 200:
            p = r.json().get('people', [])
    except Exception:
        pass

    # 2. q_organization_name with clean_k
    if not p and clean_k and len(clean_k) >= 3:
        try:
            r2 = requests.post('https://api.apollo.io/v1/mixed_people/api_search', headers=headers_apollo, json={'q_organization_name': clean_k, 'per_page': 3}, timeout=5)
            if r2.status_code == 200:
                p = r2.json().get('people', [])
        except Exception:
            pass

    if p:
        resolved += 1
        names = [f"{x.get('first_name', '')} {x.get('last_name_obfuscated', '')} ({x.get('title', '')})" for x in p]
        print(f"[{i+1}/30] RESOLVED: {k} -> {len(p)} people: {names}")
    else:
        print(f"[{i+1}/30] STILL MISSING: {k} (clean: {clean_k})")

print(f"\nResolved in sample: {resolved} / 30 ({resolved/30*100:.1f}%)")
