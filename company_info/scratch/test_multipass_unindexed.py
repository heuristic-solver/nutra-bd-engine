import os, sys, json, requests, time, re
from bs4 import BeautifulSoup
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath("."))
load_dotenv('.env')

akey = os.getenv('APOLLO_API_KEY')
headers_apollo = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'X-Api-Key': akey}
headers_web = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

test_unindexed = [
    {"company_name": "Kemin Industries, Inc.", "domain": "kemin.com"},
    {"company_name": "Kaneka Americas Holding", "domain": "kaneka.com"},
    {"company_name": "Kappa Bioscience", "domain": "kappabio.com"},
    {"company_name": "Kensing", "domain": "kensingsolutions.com"},
    {"company_name": "Korres", "domain": "korres.com"},
    {"company_name": "Jiaherb", "domain": "jiaherbinc.com"},
    {"company_name": "KSM-66 Ashwagandha", "domain": "ksm66ashwagandhaa.com"},
    {"company_name": "Chemische Fabrik Budenheim", "domain": "budenheim.com"},
    {"company_name": "Akay Natural Ingredients", "domain": "akay-group.com"},
    {"company_name": "ADM Deerland Probiotics & Enzymes", "domain": "deerland.com"},
    {"company_name": "Gencor Pacific", "domain": "gencorpacific.com"},
    {"company_name": "Indena S.p.A.", "domain": "indena.com"},
    {"company_name": "Gelita AG", "domain": "gelita.com"},
    {"company_name": "Kerry Group", "domain": "kerry.com"},
    {"company_name": "Lonza Group", "domain": "lonza.com"}
]

print("=== TESTING MULTI-PASS HARVEST ON PREVIOUSLY UNINDEXED COMPANIES ===")

for item in test_unindexed:
    co_name = item["company_name"]
    dom = item["domain"]
    
    clean_brand = re.sub(r'[\s,]+(inc\.?|llc\.?|ltd\.?|gmbh|corp\.?|co\.?|s\.?r\.?l\.?|s\.?a\.?|pvt\.?|ag|se|kgaa|holding|americas|group|pacific).*$', '', co_name, flags=re.IGNORECASE).strip()
    
    found_people = []
    
    # 1. Apollo by exact domain
    if akey and dom:
        try:
            r = requests.post("https://api.apollo.io/v1/mixed_people/api_search", headers=headers_apollo, json={"q_organization_domains": dom, "page": 1, "per_page": 5}, timeout=5)
            if r.status_code == 200:
                p_list = r.json().get("people", [])
                for p in p_list:
                    fn = p.get("first_name", "")
                    ln = p.get("last_name_obfuscated", "")
                    title = p.get("title", "")
                    if title:
                        found_people.append({"name": f"{fn} {ln}".strip(), "title": title, "source": "Apollo Domain"})
        except Exception:
            pass

    # 2. Apollo by clean brand name
    if not found_people and akey:
        try:
            r = requests.post("https://api.apollo.io/v1/mixed_people/api_search", headers=headers_apollo, json={"q_organization_name": clean_brand, "page": 1, "per_page": 5}, timeout=5)
            if r.status_code == 200:
                p_list = r.json().get("people", [])
                for p in p_list:
                    fn = p.get("first_name", "")
                    ln = p.get("last_name_obfuscated", "")
                    title = p.get("title", "")
                    if title:
                        found_people.append({"name": f"{fn} {ln}".strip(), "title": title, "source": "Apollo Brand"})
        except Exception:
            pass

    # 3. Direct Website Team Crawler
    if not found_people and dom:
        for path in ["/about", "/about-us", "/team", "/leadership", "/management", "/company"]:
            try:
                url = f"https://www.{dom}{path}"
                r = requests.get(url, headers=headers_web, timeout=4, verify=False)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    text = soup.get_text(separator=" ", strip=True)
                    matches = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)\s*[-–|,]\s*(Chief [A-Za-z]+ Officer|CEO|CFO|COO|CTO|CMO|Vice President|VP [A-Za-z ]+|Director of [A-Za-z ]+|President|Founder)', text)
                    for m in matches[:3]:
                        found_people.append({"name": m[0], "title": m[1], "source": f"Website ({path})"})
                    if matches:
                        break
            except Exception:
                pass

    print(f"\n[{co_name} | {dom}] -> Discovered {len(found_people)} people:")
    for p in found_people[:3]:
        print(f"  • {p['name']} — {p['title']} [{p['source']}]")
        
    time.sleep(0.3)
