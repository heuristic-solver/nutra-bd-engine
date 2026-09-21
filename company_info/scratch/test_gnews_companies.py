import urllib.parse
import feedparser
import requests

companies = [
    "AB Enzymes",
    "Glanbia Nutritionals",
    "Lonza",
    "Nordic Naturals",
    "NutraScience Labs",
    "ChromaDex",
    "Balchem",
    "Kemin Industries",
]

for co in companies:
    # Query 1: Roles
    q_role = f'"{co}" (appointed OR named OR hired OR joins OR joined OR promoted OR "steps down" OR resigned OR departs OR CEO OR CFO OR COO OR VP OR Director)'
    url_role = f"https://news.google.com/rss/search?q={urllib.parse.quote(q_role)}&hl=en-US&gl=US&ceid=US:en"
    r = requests.get(url_role, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
    f = feedparser.parse(r.text)
    
    # Query 2: Milestones & Funding
    q_mile = f'"{co}" (funding OR raised OR acquisition OR acquired OR merger OR expansion OR facility OR plant OR launches OR partnership)'
    url_mile = f"https://news.google.com/rss/search?q={urllib.parse.quote(q_mile)}&hl=en-US&gl=US&ceid=US:en"
    r2 = requests.get(url_mile, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
    f2 = feedparser.parse(r2.text)

    print(f"\n==================== {co} ====================")
    print(f"Role Hits: {len(f.entries)} | Milestone Hits: {len(f2.entries)}")
    for e in f.entries[:3]:
        print(f" [ROLE] {e.title} ({e.published[:16] if 'published' in e else ''})")
    for e in f2.entries[:3]:
        print(f" [MILE] {e.title} ({e.published[:16] if 'published' in e else ''})")
