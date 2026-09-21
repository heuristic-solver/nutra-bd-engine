import urllib.parse
import requests
from bs4 import BeautifulSoup

q = '"Lonza" (expansion OR facility OR acquisition)'
url = f"https://www.bing.com/news/search?q={urllib.parse.quote(q)}"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=4)
soup = BeautifulSoup(r.text, "html.parser")

cards = soup.select(".news-card, .na_card, .t_s, .b_algo")
print(f"Total cards found: {len(cards)}")
for i, c in enumerate(cards[:4]):
    print(f"\n--- CARD {i+1} ---")
    title_a = c.select_one("a.title")
    h2 = c.select_one("h2")
    snippet_div = c.select_one(".snippet, .b_caption, p")
    source_div = c.select_one(".source, .news-source, .b_attribution")
    
    print("Title <a> text:", title_a.get_text(strip=True) if title_a else "None")
    print("<h2> text:", h2.get_text(strip=True) if h2 else "None")
    print("Snippet text:", snippet_div.get_text(strip=True) if snippet_div else "None")
    print("Source text:", source_div.get_text(strip=True) if source_div else "None")
