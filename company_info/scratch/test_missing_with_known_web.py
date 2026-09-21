import json, os, requests
from dotenv import load_dotenv
load_dotenv('.env')

akey = os.getenv('APOLLO_API_KEY')
headers_apollo = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'X-Api-Key': akey}

test_list = [
    {"name": "NuLiv Science", "web": "nulivscience.com"},
    {"name": "Natreon", "web": "natreoninc.com"},
    {"name": "Lehmann & Voss", "web": "lehvoss.com"},
    {"name": "Nuritas", "web": "nuritas.com"},
    {"name": "Natac", "web": "natacgroup.com"},
    {"name": "Nutrition21", "web": "nutrition21.com"},
    {"name": "Nutraland USA", "web": "nutralandusa.com"},
    {"name": "Nutrifusion", "web": "nutrifusion.com"},
    {"name": "Nitta Gelatin", "web": "nitta-gelatin.com"},
    {"name": "Naturalin Bio-Resources", "web": "naturalin.com"}
]

for t in test_list:
    dom = t["web"]
    name = t["name"]
    r = requests.post("https://api.apollo.io/v1/mixed_people/api_search", headers=headers_apollo, json={"q_organization_domains": dom, "page": 1, "per_page": 5}, timeout=5)
    print(f"\n[{name} | {dom}] -> Status: {r.status_code}")
    if r.status_code == 200:
        p_list = r.json().get("people", [])
        print(f"  Found {len(p_list)} people:")
        for p in p_list:
            print(f"    • {p.get('first_name')} {p.get('last_name_obfuscated')} — {p.get('title')}")
