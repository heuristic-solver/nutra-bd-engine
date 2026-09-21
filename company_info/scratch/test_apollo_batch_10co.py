import os, json, requests, time
from dotenv import load_dotenv
load_dotenv('.env')

akey = os.getenv('APOLLO_API_KEY')
headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'X-Api-Key': akey}

test_companies = [
    {"name": "Indena", "domain": "indena.com"},
    {"name": "Sabinsa", "domain": "sabinsa.com"},
    {"name": "AIDP", "domain": "aidp.com"},
    {"name": "Beneo", "domain": "beneo.com"},
    {"name": "NutraScience Labs", "domain": "nutrasciencelabs.com"},
    {"name": "PLT Health Solutions", "domain": "plthealth.com"},
    {"name": "Layn Natural Ingredients", "domain": "layncorp.com"},
    {"name": "Bio-Cat", "domain": "bio-cat.com"},
    {"name": "4POTENTIA", "domain": "4potentia.com"},
    {"name": "A&A Pharmachem", "domain": "aapharmachem.com"}
]

print("=== TESTING APOLLO PEOPLE API SEARCH ===")
for c in test_companies:
    dom = c["domain"]
    name = c["name"]
    payload = {
        "q_organization_domains": dom,
        "page": 1,
        "per_page": 5
    }
    try:
        r = requests.post("https://api.apollo.io/v1/mixed_people/api_search", headers=headers, json=payload, timeout=8)
        print(f"\n[{name} ({dom})] Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            people = data.get("people", [])
            total = data.get("pagination", {}).get("total_entries", len(people))
            print(f"  Total Employees Indexed in Apollo: {total}")
            for p in people[:4]:
                fn = p.get("first_name", "")
                ln = p.get("last_name_obfuscated", "")
                title = p.get("title", "")
                print(f"   • {fn} {ln} — {title}")
        else:
            print(f"  Error: {r.text[:150]}")
    except Exception as e:
        print(f"  Exception: {e}")
    time.sleep(0.5)
