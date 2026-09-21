import requests, xml.etree.ElementTree as ET, re
from urllib.parse import quote

companies = ['Lycored', 'AIDP', 'Lonza', 'Glanbia', 'ChromaDex', 'Kemin', 'Indena', 'Tersus Life Sciences', 'Barry Callebaut', 'Novozymes', 'Herbalife', 'Danone', 'Sprouts', 'Tate & Lyle']

def parse_press_movement(title: str):
    # Check Departed / Stepped Down / Retired / Resigned
    m_left = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:to\s+step\s+down|steps\s+down|stepped\s+down|resigns|resigned|departs|departed|leaves|retires|retired)\s+(?:as\s+)?([A-Za-z\s/&,-]+?)(?:\s+at|\s+of|\s+for|\s+by|\s+-|$)', title, flags=re.IGNORECASE)
    # Check 'as [Name] retires'
    m_retires = re.search(r'as\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:retires|steps\s+down|departs|leaves)', title, flags=re.IGNORECASE)
    # Check Joined / Appointed
    m_joined = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:Appointed|appointed|named|Named|Joins|joins|Hired|hired)\s+(?:as\s+)?([A-Za-z\s/&,-]+?)(?:\s+at|\s+of|\s+for|\s+by|\s+as|\s+-|$)', title)
    
    if m_left:
        return {'person': m_left.group(1).strip(), 'role': m_left.group(2).strip(), 'type': 'DEPARTED'}
    elif m_retires:
        return {'person': m_retires.group(1).strip(), 'role': 'Executive', 'type': 'DEPARTED'}
    elif m_joined:
        return {'person': m_joined.group(1).strip(), 'role': m_joined.group(2).strip(), 'type': 'JOINED'}
    return None

for co in companies:
    query = f'{co} (appointed OR named OR "stepped down" OR leaves OR joins OR departs OR retired OR resigned OR hired)'
    url = f'https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en'
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            items = root.findall('.//item')
            found = []
            for it in items:
                t = it.find('title').text if it.find('title') is not None else ''
                p = parse_press_movement(t)
                if p:
                    found.append((t, p))
            print(f"=== {co}: {len(items)} news items, {len(found)} structured movements ===")
            for t, p in found[:3]:
                print(f"   [{p['type']}] {p['person']} - Role: {p['role']} (Headline: {t[:75]}...)")
    except Exception as e:
        print(f"Error {co}: {e}")
