import requests
import xml.etree.ElementTree as ET

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

# 1. Test Google News RSS
rss_url = 'https://news.google.com/rss/search?q=ChromaDex+appointed+OR+funding+OR+acquisition&hl=en-US&gl=US&ceid=US:en'
r = requests.get(rss_url, headers=headers, timeout=10)
print('Google News RSS Status:', r.status_code)
if r.status_code == 200:
    root = ET.fromstring(r.text)
    items = root.findall('.//item')
    print(f'Google News RSS items found: {len(items)}')
    for item in items[:3]:
        title = item.find('title').text if item.find('title') is not None else ''
        pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
        print(f'  - [{pubDate}] {title}')

# 2. Test DuckDuckGo HTML / Lite
ddg_url = 'https://html.duckduckgo.com/html/'
r2 = requests.post(ddg_url, data={'q': 'ChromaDex CEO OR CFO appointed OR joined'}, headers=headers, timeout=10)
print('DuckDuckGo HTML Status:', r2.status_code, 'Content length:', len(r2.text))

# 3. Test SEC EDGAR
sec_headers = {'User-Agent': 'NutraEngine Research Bot contact@nutraengine.org'}
sec_url = 'https://data.sec.gov/submissions/CIK0001394238.json'
try:
    r3 = requests.get(sec_url, headers=sec_headers, timeout=10)
    print('SEC EDGAR Status:', r3.status_code, 'Company:', r3.json().get('name') if r3.status_code == 200 else 'N/A')
except Exception as e:
    print('SEC EDGAR error:', e)

# 4. Test Yahoo Finance RSS / Search
yahoo_rss = 'https://finance.yahoo.com/rss/headline?s=CDXC'
r4 = requests.get(yahoo_rss, headers=headers, timeout=10)
print('Yahoo RSS Status:', r4.status_code, 'Content length:', len(r4.text))
