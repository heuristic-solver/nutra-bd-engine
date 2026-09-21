import os, sys, requests, json, time
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('.env')
akey = os.getenv('APOLLO_API_KEY')
headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'X-Api-Key': akey}

test_doms = ['indena.com', 'glanbia.com', 'lonza.com', 'lycored.com', 'aidp.com', 'gelita.com', 'budenheim.com', 'kappabio.com', 'akaybioactives.com', 'chromadex.com', 'gencorpacific.com']

for dom in test_doms:
    try:
        # Step 1: Enrich domain to get org ID
        r_enrich = requests.get('https://api.apollo.io/v1/organizations/enrich', headers=headers, params={'domain': dom}, timeout=5)
        if r_enrich.status_code == 200:
            org = r_enrich.json().get('organization', {})
            org_id = org.get('id')
            co_name = org.get('name', dom)
            if not org_id:
                print(f"Domain: {dom} -> No org ID")
                continue

            # Step 2: Query Current Employees
            r_curr = requests.post('https://api.apollo.io/v1/mixed_people/api_search', headers=headers, json={'organization_ids': [org_id], 'per_page': 5}, timeout=5)
            curr_people = r_curr.json().get('people', []) if r_curr.status_code == 200 else []

            # Step 3: Query Past Employees (Who Left!)
            r_past = requests.post('https://api.apollo.io/v1/mixed_people/api_search', headers=headers, json={'person_past_organization_ids': [org_id], 'per_page': 10}, timeout=5)
            past_people = r_past.json().get('people', []) if r_past.status_code == 200 else []

            departed = []
            for p in past_people:
                fn = p.get('first_name', '')
                ln = p.get('last_name_obfuscated', '')
                t = p.get('title', '')
                cur_org = p.get('organization', {}).get('name', '') if p.get('organization') else 'Unknown'
                # If current org is DIFFERENT from co_name, they left!
                if co_name.lower() not in cur_org.lower() and cur_org != 'Unknown':
                    departed.append(f"{fn} {ln} (Former Role: {t} -> Left for: {cur_org})")

            joined = [f"{p.get('first_name', '')} {p.get('last_name_obfuscated', '')} ({p.get('title', '')})" for p in curr_people]

            print("=" * 70)
            print(f"Company: {co_name} ({dom}) | Org ID: {org_id}")
            print(f"  [WHO CURRENTLY THERE / JOINED ({len(joined)})]: {joined[:3]}")
            print(f"  [WHO LEFT / VACATED ROLES ({len(departed)})]: {departed[:4]}")
        else:
            print(f"Enrich failed for {dom}: {r_enrich.status_code}")
    except Exception as e:
        print(f"Error {dom}: {e}")
