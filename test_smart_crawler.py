# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

def discover_and_crawl_site(domain):
    base_url = f"https://{domain}" if not domain.startswith("http") else domain
    print(f"\nScanning: {base_url}")
    try:
        r = requests.get(base_url, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"  Failed status: {r.status_code}")
            return
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Find links
        found_links = set()
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            full_url = urllib.parse.urljoin(base_url, href)
            # Only keep internal links matching relevant sections
            if urllib.parse.urlparse(full_url).netloc == urllib.parse.urlparse(base_url).netloc:
                path = urllib.parse.urlparse(full_url).path.lower()
                if any(kw in path for kw in ['team', 'leadership', 'about', 'execut', 'manage', 'news', 'press', 'board', 'career']):
                    found_links.add(full_url)
                    
        print(f"  Discovered {len(found_links)} relevant pages:")
        for link in list(found_links)[:6]:
            print(f"    - {link}")
            
        # Crawl top 2 leadership/team pages
        leadership_links = [l for l in found_links if any(k in l.lower() for k in ['team', 'leadership', 'execut', 'manage', 'board'])]
        for l_url in leadership_links[:2]:
            lr = requests.get(l_url, headers=headers, timeout=8)
            lsoup = BeautifulSoup(lr.text, 'html.parser')
            text = lsoup.get_text(separator=' ', strip=True)
            # Extract names & titles
            matches = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)\s*[-–|,:]\s*(Chief [A-Za-z]+ Officer|CEO|CFO|COO|CTO|CMO|Vice President|VP [A-Za-z ]+|Director of [A-Za-z ]+|Founder|President)', text)
            print(f"    -> From {l_url}: {len(matches)} leadership matches:")
            for m in matches[:4]:
                print(f"       * {m[0]} : {m[1]}")
    except Exception as e:
        print(f"  Error: {e}")

discover_and_crawl_site("lieflabs.com")
discover_and_crawl_site("vitaquest.com")
discover_and_crawl_site("gencorpacific.com")
