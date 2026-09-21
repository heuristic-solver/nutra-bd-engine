import time
import requests
import feedparser

FEEDS = [
    ("NutraIngredients", "https://www.nutraingredients.com/content/view/feed/425"),
    ("Nutritional Outlook", "https://www.nutritionaloutlook.com/rss"),
    ("WholeFoods Magazine", "https://wholefoodsmagazine.com/feed/"),
    ("Nutraceuticals World", "https://www.nutraceuticalsworld.com/rss"),
    ("Natural Products Insider", "https://www.naturalproductsinsider.com/rss.xml"),
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"}

total_articles = 0
for name, url in FEEDS:
    t0 = time.time()
    try:
        r = requests.get(url, headers=headers, timeout=5)
        f = feedparser.parse(r.text)
        print(f"[{name}] Status: {r.status_code}, Entries: {len(f.entries)}, Time: {time.time()-t0:.2f}s")
        total_articles += len(f.entries)
        if f.entries:
            print(f"   Sample: {f.entries[0].get('title', '')}")
    except Exception as e:
        print(f"[{name}] Error: {e}")

print(f"\nTOTAL Trade Press Articles Cached in Memory: {total_articles}")
