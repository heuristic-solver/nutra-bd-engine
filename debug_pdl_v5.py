import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("PDL_API_KEY")
headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

print("Testing v5 endpoints...")

# 1. Company Enrich v5
url_co = "https://api.peopledatalabs.com/v5/company/enrich?website=cmbio.io"
resp_co = requests.get(url_co, headers=headers)
print(f"Company Enrich status: {resp_co.status_code}")
print(f"Company Enrich response: {resp_co.text[:300]}")

# 2. Person Search v5
url_person = "https://api.peopledatalabs.com/v5/person/search"
payload = {
    "sql": "SELECT * FROM person WHERE job_company_website = 'cmbio.io' LIMIT 2"
}
resp_person = requests.post(url_person, headers=headers, json=payload)
print(f"\nPerson Search status: {resp_person.status_code}")
print(f"Person Search response: {resp_person.text[:300]}")
