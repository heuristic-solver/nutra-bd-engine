import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("PDL_API_KEY")
headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

# 1. Person Search
url_person = "https://api.peopledatalabs.com/v5/person/search"
payload = {
    "sql": "SELECT * FROM person WHERE job_company_website = 'cmbio.io'",
    "size": 5
}
resp_person = requests.post(url_person, headers=headers, json=payload)
print(f"Person Search status: {resp_person.status_code}")
data = resp_person.json()
print(f"Total found: {data.get('total')}")
for p in data.get('data', [])[:3]:
    print(f"  • {p.get('full_name')} | {p.get('job_title')} | Work Email: {p.get('work_email')} | Phone: {p.get('mobile_phone')}")

# 2. Person Enrich
url_enrich = "https://api.peopledatalabs.com/v5/person/enrich?name=Prashant+Halbe&company=Pronto"
resp_enrich = requests.get(url_enrich, headers=headers)
print(f"\nPerson Enrich status: {resp_enrich.status_code}")
data_en = resp_enrich.json().get('data', {})
print(f"Enrich name: {data_en.get('full_name')} | Title: {data_en.get('job_title')} | Work email: {data_en.get('work_email')}")
