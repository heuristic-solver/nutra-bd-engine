import urllib.request
import json

url = "https://api.apify.com/v2/store?search=people%20data%20labs&limit=20"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        items = data.get("data", {}).get("items", [])
        print(f"Found {len(items)} actors matching 'people data labs':")
        for it in items:
            username = it.get("username")
            name = it.get("name")
            title = it.get("title")
            pricing = it.get("pricingModel")
            print(f"  {username}/{name}: {title} [{pricing}]")
except Exception as e:
    print("Error:", e)

# Also search for 'pdl'
url2 = "https://api.apify.com/v2/store?search=pdl&limit=20"
req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req2) as resp:
        data2 = json.loads(resp.read().decode("utf-8"))
        items2 = data2.get("data", {}).get("items", [])
        print(f"\nFound {len(items2)} actors matching 'pdl':")
        for it in items2:
            username = it.get("username")
            name = it.get("name")
            title = it.get("title")
            pricing = it.get("pricingModel")
            print(f"  {username}/{name}: {title} [{pricing}]")
except Exception as e:
    print("Error:", e)
