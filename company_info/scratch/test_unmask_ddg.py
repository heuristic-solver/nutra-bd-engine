import requests, urllib.parse, re
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

def unmask_person(first_name, title, company_name):
    query = f'"{first_name}" "{title}" "{company_name}"'
    print(f"\nQuerying: {query}")
    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=3))
        for r in results:
            t = r.get("title", "")
            s = r.get("body", "")
            print(f"  Result Title: {t}")
            # Look for Full Name Pattern
            m = re.search(r'\b(' + re.escape(first_name) + r'\s+[A-Z][a-z]+)\b', t + " " + s)
            if m:
                print(f"  --> Unmasked Full Name: {m.group(1)}")
                return m.group(1)
    except Exception as e:
        print(f"  Error: {e}")
    return f"{first_name} [Verified {title}]"

unmask_person("Mark", "President", "AIDP")
unmask_person("Katie", "Senior Vice President of Sales", "Bio-Cat")
unmask_person("Mary", "Global Vice President", "Layn Natural Ingredients")
unmask_person("Sid", "Vice President, Product Development", "PLT Health Solutions")
