import os, sys, json, requests, time, re
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('.env')
akey = os.getenv('APOLLO_API_KEY')
headers_apollo = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'X-Api-Key': akey}

test_companies = [
    ('ChromaDex', 'chromadex.com'),
    ('Gencor Pacific', 'gencorpacific.com'),
    ('Kemin Industries', 'kemin.com'),
    ('Indena', 'indena.com'),
    ('Lycored', 'lycored.com'),
    ('AIDP', 'aidp.com'),
    ('Glanbia', 'glanbia.com'),
    ('Lonza', 'lonza.com'),
    ('Monteloeder', 'monteloeder.com'),
    ('Budenheim', 'budenheim.com'),
    ('Kappa Bioscience', 'kappabio.com'),
    ('Akay Natural', 'akaybioactives.com'),
    ('Gelita', 'gelita.com'),
    ('Kerry', 'kerry.com'),
    ('ADM Deerland', 'deerland.com')
]

for co_name, dom in test_companies:
    clean_brand = re.sub(r'[\s,]+(inc|llc|ltd|gmbh|corp|industries|pacific|nutritionals|capsules|natural|group).*$', '', co_name, flags=re.IGNORECASE).strip()
    r = requests.post('https://api.apollo.io/v1/mixed_people/api_search', headers=headers_apollo, json={'q_organization_domains': dom, 'per_page': 25})
    if r.status_code == 200:
        people = r.json().get('people', [])
        joined_active = []
        departed_left = []
        for p in people:
            fn = p.get('first_name', '')
            ln = p.get('last_name_obfuscated', '')
            title = p.get('title', '')
            cur_org = p.get('organization', {}).get('name', '') if p.get('organization') else 'Unknown'
            
            # Match current org
            is_cur = clean_brand.lower() in cur_org.lower() or cur_org.lower() in clean_brand.lower()
            if is_cur or not cur_org or cur_org == 'Unknown':
                joined_active.append({'name': f"{fn} {ln}".strip(), 'title': title, 'org': cur_org})
            else:
                departed_left.append({'name': f"{fn} {ln}".strip(), 'former_title': title, 'new_org': cur_org})
        
        print(f"\n========================================================")
        print(f"Company: {co_name} | Domain: {dom}")
        print(f"WHO LEFT / DEPARTED ({len(departed_left)} people):")
        for d in departed_left[:4]:
            print(f"  [-] {d['name']} | Former Role: {d['former_title']} | Left for: {d['new_org']}")
        print(f"WHO JOINED / CURRENT DECISION-MAKERS ({len(joined_active)} people):")
        for j in joined_active[:4]:
            print(f"  [+] {j['name']} | Title: {j['title']} | Current: {j['org']}")
