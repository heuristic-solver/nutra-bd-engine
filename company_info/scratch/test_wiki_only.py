import time
import requests
import json

companies = ["Lonza Group", "Glanbia", "ChromaDex", "Balchem", "Archer Daniels Midland", "Novozymes", "Twinlab"]

print("Testing Wikipedia Open API...")
for co in companies:
    t0 = time.time()
    url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts|pageprops&exintro=1&explaintext=1&titles={requests.utils.quote(co)}"
    try:
        r = requests.get(url, timeout=4, headers={"User-Agent": "NutraIntelligenceBot/1.0 (contact@nutraintel.org)"})
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for pid, pdata in pages.items():
            if pid != "-1":
                title = pdata.get("title", "")
                extract = pdata.get("extract", "")
                print(f"[{co}] Found Wikipedia: '{title}' ({time.time()-t0:.2f}s)")
                print(f"   Summary: {extract[:120]}...")
            else:
                print(f"[{co}] Not found on Wikipedia ({time.time()-t0:.2f}s)")
    except Exception as e:
        print(f"[{co}] Error: {e}")
