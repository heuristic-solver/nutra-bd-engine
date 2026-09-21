import os, json, requests, time, re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv('.env')

akey = os.getenv('APOLLO_API_KEY')
headers_apollo = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'X-Api-Key': akey}
headers_web = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

test_cohort = [
    {"name": "Indena", "domain": "indena.com"},
    {"name": "Sabinsa", "domain": "sabinsa.com"},
    {"name": "AIDP", "domain": "aidp.com"},
    {"name": "Beneo", "domain": "beneo.com"},
    {"name": "NutraScience Labs", "domain": "nutrasciencelabs.com"},
    {"name": "PLT Health Solutions", "domain": "plthealth.com"},
    {"name": "Layn Natural Ingredients", "domain": "layncorp.com"},
    {"name": "Bio-Cat", "domain": "bio-cat.com"},
    {"name": "4POTENTIA", "domain": "4potentia.com"},
    {"name": "A&A Pharmachem", "domain": "aapharmachem.com"},
    {"name": "Thorne Research", "domain": "thorne.com"},
    {"name": "Metagenics", "domain": "metagenics.com"},
    {"name": "Kyowa Hakko USA", "domain": "kyowa-usa.com"},
    {"name": "FutureCeuticals", "domain": "futureceuticals.com"},
    {"name": "NuLiv Science", "domain": "nulivscience.com"}
]

print("=" * 80)
print("  MULTI-SOURCE LIVE PERSONNEL HARVESTING TEST (15 COMPANIES)")
print("=" * 80)

results = []

for item in test_cohort:
    name = item["name"]
    dom = item["domain"]
    print(f"\nScanning: {name:<30} | Domain: {dom}")
    
    found_people = []
    
    # 1. Apollo People Search
    if akey and dom:
        try:
            payload = {"q_organization_domains": dom, "page": 1, "per_page": 5}
            r = requests.post("https://api.apollo.io/v1/mixed_people/api_search", headers=headers_apollo, json=payload, timeout=6)
            if r.status_code == 200:
                p_list = r.json().get("people", [])
                for p in p_list:
                    fn = p.get("first_name", "")
                    ln = p.get("last_name_obfuscated", "")
                    title = p.get("title", "")
                    if title:
                        name_str = f"{fn} {ln}".strip() if fn or ln else "Verified Contact"
                        found_people.append({"name": name_str, "role": title, "source": "Apollo B2B Org Graph"})
        except Exception as e:
            pass

    # 2. Website Team / Leadership Page Crawler
    if dom:
        team_paths = ["/about", "/about-us", "/team", "/leadership", "/our-team", "/management", "/company"]
        for p in team_paths:
            try:
                url = f"https://www.{dom}{p}"
                r = requests.get(url, headers=headers_web, timeout=4, verify=False)
                if r.status_code == 200 and len(r.text) > 500:
                    soup = BeautifulSoup(r.text, "html.parser")
                    text = soup.get_text(separator=" ", strip=True)
                    # Extract Name - Role matches
                    matches = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)\s*[-–|,]\s*(Chief [A-Za-z]+ Officer|CEO|CFO|COO|CTO|CMO|Vice President|VP [A-Za-z ]+|Director of [A-Za-z ]+|Founder|President|Plant Manager|Quality Director)', text)
                    for m in matches[:3]:
                        found_people.append({"name": m[0], "role": m[1], "source": f"Website ({p})"})
                    if matches:
                        break
            except Exception:
                pass

    print(f"  --> Discovered {len(found_people)} Real Personnel Records:")
    for fp in found_people[:4]:
        print(f"      • {fp['name']:<25} | {fp['role'][:45]:<45} [{fp['source']}]")
        
    results.append({"name": name, "domain": dom, "count": len(found_people)})
    time.sleep(0.3)

print("\n" + "=" * 80)
total_with_people = sum(1 for r in results if r["count"] > 0)
print(f"SUMMARY: {total_with_people} / {len(results)} companies ({total_with_people/len(results)*100:.1f}%) returned real personnel records!")
print("=" * 80)
