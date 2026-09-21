import urllib.parse
import requests
from bs4 import BeautifulSoup

co = "Aker BioMarine"
q_complex = f'(("{co}") AND (supplement OR nutraceutical)) ("appointed" OR "named" OR "joined" OR "CEO" OR "acquisition" OR "merger")'
q_simple = f'"{co}" (appointed OR named OR CEO OR acquisition OR merger OR expansion)'

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

url1 = f"https://www.bing.com/news/search?q={urllib.parse.quote(q_complex)}"
r1 = requests.get(url1, headers=headers, timeout=4)
soup1 = BeautifulSoup(r1.text, "html.parser")
cards1 = soup1.select(".news-card, .na_card, .t_s, .b_algo")
print(f"Complex Query Cards: {len(cards1)}")

url2 = f"https://www.bing.com/news/search?q={urllib.parse.quote(q_simple)}"
r2 = requests.get(url2, headers=headers, timeout=4)
soup2 = BeautifulSoup(r2.text, "html.parser")
cards2 = soup2.select(".news-card, .na_card, .t_s, .b_algo")
print(f"Simple Query Cards: {len(cards2)}")
for c in cards2[:3]:
    t = c.select_one("a.title, h2 a, h2, a")
    print(" -", t.get_text(strip=True) if t else "")
