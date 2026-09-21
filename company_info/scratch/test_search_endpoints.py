import urllib.parse
import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# Test 1: Yahoo News
url_yn = f"https://news.search.yahoo.com/search?p={urllib.parse.quote('\"Glanbia\" (appointed OR acquired OR expansion)')}"
try:
    r = requests.get(url_yn, headers=headers, timeout=4)
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select(".NewsArticle, .algo, h4")
    print("1. Yahoo News status:", r.status_code, "items:", len(items))
    for item in items[:3]:
        print("  -", item.get_text(strip=True)[:100])
except Exception as e:
    print("1. Yahoo News error:", e)

# Test 2: Google Search Web HTML
url_g = f"https://www.google.com/search?q={urllib.parse.quote('\"Glanbia Nutritionals\" (appointed OR acquired)')}&hl=en"
try:
    r = requests.get(url_g, headers=headers, timeout=4)
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select("h3")
    print("2. Google Web status:", r.status_code, "items:", len(items))
    for item in items[:3]:
        print("  -", item.get_text(strip=True)[:100])
except Exception as e:
    print("2. Google Web error:", e)
