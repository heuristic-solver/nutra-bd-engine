import os, sys, json, requests, time, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath("."))
load_dotenv('.env')

akey = os.getenv('APOLLO_API_KEY')
headers_apollo = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'X-Api-Key': akey}

def clean_co_name(name: str) -> str:
    if not name or name == "None":
        return ""
    try:
        clean = name.encode('latin-1').decode('utf-8')
    except Exception:
        clean = name
    return clean.strip()

def resolve_domain(item: dict) -> str:
    web = item.get("known_website") or item.get("website") or ""
    if web and web != "null" and web != "None":
        d = web.replace("http://", "").replace("https://", "").replace("www.", "").strip("/")
        return d.split("/")[0].lower()
    co_name = clean_co_name(item.get("company_name", ""))
    clean = re.sub(r'[\s,]+(inc\.?|llc\.?|ltd\.?|gmbh|corp\.?|co\.?|s\.?r\.?l\.?|s\.?a\.?|pvt\.?|private|limited|group|holdings|usa|global).*$', '', co_name, flags=re.IGNORECASE).strip()
    slug = re.sub(r'[^a-zA-Z0-9]', '', clean).lower()
    if len(slug) < 3:
        slug = re.sub(r'[^a-zA-Z0-9]', '', co_name).lower()
    return f"{slug}.com"

def fetch_company_personnel(item: dict) -> dict:
    co_name = clean_co_name(item.get("company_name", ""))
    domain = resolve_domain(item)
    
    people_found = []
    
    # 1. Apollo People API Search
    if akey and domain:
        try:
            payload = {"q_organization_domains": domain, "page": 1, "per_page": 6}
            r = requests.post("https://api.apollo.io/v1/mixed_people/api_search", headers=headers_apollo, json=payload, timeout=6)
            if r.status_code == 200:
                p_list = r.json().get("people", [])
                for p in p_list:
                    fn = p.get("first_name", "")
                    ln = p.get("last_name_obfuscated", "")
                    title = p.get("title", "")
                    if title:
                        name_str = f"{fn} {ln}".strip() if fn or ln else "Verified Lead"
                        people_found.append({
                            "person_name": name_str,
                            "role_title": title,
                            "source": "Apollo B2B Org Graph"
                        })
        except Exception:
            pass

    return {
        "company_name": co_name,
        "domain": domain,
        "people": people_found,
        "count": len(people_found)
    }

def main():
    with open("nutraceutical_kb.json", "r", encoding="utf-8") as f:
        kb_raw = json.load(f)
        
    test_cohort = [k for k in kb_raw if k.get("company_name") and k.get("company_name") != "None"][:30]
    print(f"Testing parallel Apollo personnel extraction on {len(test_cohort)} companies...")
    
    start = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_company_personnel, item): item for item in test_cohort}
        for future in as_completed(futures):
            try:
                res = future.result()
                results.append(res)
                print(f"[{len(results):02d}/{len(test_cohort)}] {res['company_name'][:25]:<25} ({res['domain']:<22}) -> Found {res['count']} people")
            except Exception as e:
                print(f"Error: {e}")
                
    elapsed = time.time() - start
    hit_count = sum(1 for r in results if r["count"] > 0)
    print(f"\nCompleted in {elapsed:.2f}s!")
    print(f"Hit Rate: {hit_count} / {len(results)} ({hit_count/len(results)*100:.1f}%)")

if __name__ == "__main__":
    main()
