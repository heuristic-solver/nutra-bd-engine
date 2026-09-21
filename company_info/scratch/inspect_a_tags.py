import urllib.parse
import requests
from bs4 import BeautifulSoup

url = f"https://www.bing.com/news/search?q={urllib.parse.quote('\"Aker BioMarine\" (merger OR acquisition OR appointed)')}"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=4)
soup = BeautifulSoup(r.text, "html.parser")

for c in soup.select(".news-card, .na_card, .t_s, .b_algo")[:3]:
    print("--- CARD ---")
    for a in c.find_all("a"):
        print(f"  <a> text: '{a.get_text(strip=True)}' | class: {a.get('class')} | href: {a.get('href')[:50]}...")
