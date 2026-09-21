import time
import requests
import json

companies = ["Lonza Group", "Glanbia", "ChromaDex", "Balchem", "Archer Daniels Midland", "Novozymes", "Twinlab"]

print("1. Testing DuckDuckGo Instant Answer API...")
for co in companies[:3]:
    t0 = time.time()
    url = f"https://api.duckduckgo.com/?q={co}&format=json&no_html=1&skip_disambig=1"
    try:
        r = requests.get(url, timeout=4)
        data = r.json()
        abstract = data.get("AbstractText", "")
        heading = data.get("Heading", "")
        print(f"[{co}] Status: {r.status_code}, Time: {time.time()-t0:.2f}s")
        print(f"   Heading: {heading}")
        print(f"   Abstract: {abstract[:120]}...")
    except Exception as e:
        print(f"[{co}] Error: {e}")

print("\n2. Testing Wikipedia Open API...")
for co in companies:
    t0 = time.time()
    url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts|pageprops&exintro=1&explaintext=1&titles={co}"
    try:
        r = requests.get(url, timeout=4, headers={"User-Agent": "NutraIntelligenceBot/1.0 (contact@nutraintel.org)"})
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for pid, pdata in pages.items():
            if pid != "-1":
                title = pdata.get("title", "")
                extract = pdata.get("extract", "")
                print(f"[{co}] Found Wikipedia: '{title}' ({time.time()-t0:.2f}s)")
                print(f"   Summary: {extract[:150]}...")
    except Exception as e:
        print(f"[{co}] Error: {e}")
