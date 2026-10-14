import csv
import json

# Comprehensive consolidation of all extracted intelligence from PDL, Apify, and Signalbase

company_firmographics = {
    "API Co., Ltd.": {
        "domain": "api-odm.com",
        "pdl_name": "API Co,. Ltd.",
        "employee_count": 4,
        "hq": "Gifu, Japan",
        "industry": "Food & Dietary Supplement OEM Manufacturing",
        "people": [
            {"name": "Mengmeng Tong", "type": "Current Key Personnel", "role": "Chief, Procurement Department", "date": "2016-02 (Tenure)", "landing": "Current", "source": "PDL"},
            {"name": "An Shimojo", "type": "Current Key Personnel", "role": "Sales and Marketing Specialist", "date": "2021-04 (Tenure)", "landing": "Current", "source": "PDL"},
            {"name": "Miwa Niikawa", "type": "Current Key Personnel", "role": "新規戦略企画 主任 (New Strategy Planning Lead)", "date": "2020-05 (Tenure)", "landing": "Current", "source": "PDL"},
            {"name": "Alex Shulman", "type": "Alumni / Departure (Left)", "role": "Was: Co-Founder & Senior Software Engineer", "date": "Left: 2019-01", "landing": "Senior Software Engineer @ NVIDIA", "source": "PDL"},
            {"name": "Derwayne Moore", "type": "Alumni / Departure (Left)", "role": "Was: Loss Prevention", "date": "Left: 2012-03", "landing": "Agent Manager @ Manic Focus", "source": "PDL"},
        ]
    },
    "Apis Flora": {
        "domain": "apisflora.com.br",
        "pdl_name": "Apis Flora Industrial e Comercial Ltda.",
        "employee_count": 101,
        "hq": "Ribeirão Preto, Brazil",
        "industry": "Pharmaceuticals and Healthcare Products",
        "people": [
            {"name": "Michelangelo Rodrigues", "type": "Current Decision Maker", "role": "Coordenador de Suprimentos (Head of Supply Chain / Procurement)", "date": "Started: 2024-12", "landing": "Current", "source": "PDL"},
            {"name": "Giovanna Borini", "type": "Current Key Personnel", "role": "Pesquisadora Senior (Senior R&D Researcher)", "date": "Started: 2022-02", "landing": "Current", "source": "PDL"},
            {"name": "Hector Zanardo", "type": "Current Key Personnel", "role": "Analista de TI (IT Systems Analyst)", "date": "Started: 2022-12", "landing": "Current", "source": "PDL"},
            {"name": "Marcelo Gobara", "type": "Current Decision Maker", "role": "Chief Revenue Officer (CRO)", "date": "Joined", "landing": "Current", "source": "Data-Slayer / LinkedIn"},
            {"name": "Hériton FÁBIO dos Santos", "type": "Current Key Personnel", "role": "Consultor Farmacêutico", "date": "Started: 2026-05-01", "landing": "Current", "source": "Data-Slayer"},
            {"name": "Rachel Machado", "type": "Alumni / Departure (Left)", "role": "Was: Iniciação Científica (R&D)", "date": "Left: 2016-03", "landing": "Bioprocess Associate Scientist @ Corteva Agriscience", "source": "PDL"},
            {"name": "Leticia Nandes", "type": "Alumni / Departure (Left)", "role": "Was: Marketing & Communications Specialist", "date": "Left: 2019-01", "landing": "Social Media Executive @ Media Social", "source": "PDL"},
            {"name": "Marcos Lima", "type": "Alumni / Departure (Left)", "role": "Was: Representante Comercial de Vendas", "date": "Former", "landing": "Sales Representative @ Black Skull USA", "source": "PDL"},
        ]
    },
    "Cmbio": {
        "domain": "cmbio.io",
        "pdl_name": "cmbio",
        "employee_count": 86,
        "hq": "Copenhagen, Denmark",
        "industry": "Biotechnology Research",
        "people": [
            {"name": "Kelly Moffat", "type": "Current C-Suite / Decision Maker", "role": "Chief Operating Officer (COO)", "date": "Started: 2026-03-01", "landing": "Current", "source": "PDL / Data-Slayer"},
            {"name": "Huai Li", "type": "Current Decision Maker", "role": "Vice President of Engineering", "date": "Started: 2024-12-01", "landing": "Current", "source": "PDL"},
            {"name": "Mike Waddington", "type": "Current Decision Maker", "role": "Senior Manager, Quality Assurance", "date": "Started: 2022-04", "landing": "Current", "source": "PDL"},
            {"name": "Anders Mohr Christensen", "type": "Current C-Suite / Decision Maker", "role": "Chief Financial Officer (CFO)", "date": "Started: 2025-01-01", "landing": "Current", "source": "Data-Slayer"},
            {"name": "Ken McGrath", "type": "Current Decision Maker", "role": "BD Innovation Manager (APAC)", "date": "Started: 2026-04-01", "landing": "Current", "source": "Data-Slayer"},
            {"name": "Manoj Dadlani", "type": "Alumni / Departure (Left)", "role": "Was: Chief Commercial Officer (CCO) / Executive Chairman", "date": "Left: 2024", "landing": "President @ cosmos-hub", "source": "PDL"},
            {"name": "Dana Walsh", "type": "Alumni / Departure (Left)", "role": "Was: Senior Microbiome Scientist", "date": "Left: 2026-08", "landing": "Transitioning / Independent", "source": "PDL"},
            {"name": "Maria Santoro", "type": "Alumni / Departure (Left)", "role": "Was: Business Development Manager", "date": "Left: 2025-07", "landing": "Biotech Partnerships", "source": "PDL"},
            {"name": "Cecelia Garcia", "type": "Alumni / Departure (Left)", "role": "Was: Scientific Project Coordinator", "date": "Left: 2026-03-01", "landing": "Project Lead", "source": "Data-Slayer"},
        ]
    },
    "Caltron Clays & Chemicals Pvt. Ltd.": {
        "domain": "caltronclays.com",
        "pdl_name": "Caltron Clays & Chemicals Pvt Ltd",
        "employee_count": 15,
        "hq": "Mumbai, India",
        "industry": "Pharmaceutical Manufacturing",
        "people": [
            {"name": "Ashwini Suvarna", "type": "Current Key Personnel", "role": "Digital Marketing Manager", "date": "Started: 2025-01", "landing": "Current", "source": "PDL"},
            {"name": "Vidhyashree Sagvekar", "type": "Current Key Personnel", "role": "Human Resources Generalist", "date": "Started: 2025-08", "landing": "Current", "source": "PDL"},
            {"name": "Mayuri Jadhav", "type": "Current Key Personnel", "role": "Quality Control Executive", "date": "Recent Join", "landing": "Current", "source": "Serper / LinkedIn"},
        ]
    },
    "Greenspace Herbs": {
        "domain": "greenspaceherbs.com",
        "pdl_name": "Greenspace Herbs",
        "employee_count": 30,
        "hq": "Surat, Gujarat, India",
        "industry": "Nutraceutical & Herbal Manufacturing",
        "people": [
            {"name": "Dr. Sonali Bhokare", "type": "Current Key Personnel", "role": "Expert in Nutraceutical & Herbal Formulations", "date": "Active", "landing": "Current", "source": "Thirdwatch"},
            {"name": "Reetika K.", "type": "Current Key Personnel", "role": "Senior Quality & Operations Lead", "date": "Active", "landing": "Current", "source": "Thirdwatch"},
            {"name": "Latha Divakar", "type": "Current Key Personnel", "role": "Senior Officer Microbiology", "date": "Active", "landing": "Current", "source": "Thirdwatch"},
            {"name": "Dr. Vrinda", "type": "Current Key Personnel", "role": "Ayurveda Researcher & Scientific Writer", "date": "Active", "landing": "Current", "source": "Thirdwatch"},
        ]
    },
    "Wisesorbent Technology LLC": {
        "domain": "wisesorbent.com",
        "pdl_name": "Wisesorbent Technology",
        "employee_count": 12,
        "hq": "Marlton, NJ, United States",
        "industry": "Desiccant & Packaging Solutions for Pharma",
        "people": [
            {"name": "Philippe Depois", "type": "Current C-Suite / Decision Maker", "role": "Chief Operating Officer (COO)", "date": "Active", "landing": "Current", "source": "Thirdwatch / LinkedIn"},
            {"name": "Ricky Zhu", "type": "Current Decision Maker", "role": "Technical Sales Specialist", "date": "Active", "landing": "Current", "source": "Thirdwatch"},
            {"name": "Sophia Fan", "type": "Current Key Personnel", "role": "Moisture-Proof Packaging Engineer", "date": "Active", "landing": "Current", "source": "Thirdwatch"},
            {"name": "Thomas Rice", "type": "Current Key Personnel", "role": "Commercial Operations Manager", "date": "Active", "landing": "Current", "source": "Thirdwatch"},
        ]
    },
    "PRONTO": {
        "domain": "prontous.com",
        "pdl_name": "PRONTO Manufacturing & Fulfillment",
        "employee_count": 13,
        "hq": "Manassas, VA, United States",
        "industry": "Supplement Contract Manufacturing & Packaging",
        "people": [
            {"name": "Prashant Halbe", "type": "Current Decision Maker (High Intent)", "role": "Head of Brand", "date": "Announced: 2026-09-04 (25 days ago)", "landing": "Current (30-day buying window)", "source": "Inovaflow / News"},
            {"name": "Justina Zdan", "type": "Current Key Personnel", "role": "Talent Acquisition Lead & Partner", "date": "Started: 2026-06-01", "landing": "Current", "source": "Data-Slayer / Signalbase"},
            {"name": "Kęstutis Gabrielius Šaulys", "type": "Current Key Personnel", "role": "Senior Research and Development Specialist", "date": "Started: 2025-03-01", "landing": "Current", "source": "Data-Slayer"},
        ]
    }
}

# 1. Write dedicated people and departures CSV
csv_rows = []
for co, data in company_firmographics.items():
    for p in data["people"]:
        csv_rows.append({
            "Target Company": co,
            "Domain": data["domain"],
            "PDL Matched Name": data["pdl_name"],
            "Verified Headcount": data["employee_count"],
            "HQ Location": data["hq"],
            "Industry": data["industry"],
            "Person Name": p["name"],
            "Record Type": p["type"],
            "Role / Title": p["role"],
            "Date / Timing": p["date"],
            "Landing Company / Status": p["landing"],
            "Data Source": p["source"]
        })

out_csv = r"C:\Users\joela\OneDrive\Documents\Python\bd-engine\pdl_people_and_departures.csv"
fieldnames = [
    "Target Company", "Domain", "PDL Matched Name", "Verified Headcount", "HQ Location", "Industry",
    "Person Name", "Record Type", "Role / Title", "Date / Timing", "Landing Company / Status", "Data Source"
]

with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(csv_rows)

print(f"Successfully generated {out_csv} with {len(csv_rows)} structured intelligence rows!")

# 2. Update master signalbase_demo_enriched.csv with verified headcount and rich roster
master_rows = []
with open(r"C:\Users\joela\OneDrive\Documents\Python\bd-engine\signalbase_demo_enriched.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    m_fieldnames = reader.fieldnames
    for r in reader:
        co = r["Company Name"]
        for target_key, info in company_firmographics.items():
            if target_key.lower() in co.lower() or co.lower() in target_key.lower():
                r["Employee Count"] = str(info["employee_count"])
                
                # Format Movement / Departures
                movements = [f"[{p['type'].upper()}] {p['name']} -> {p['role']} ({p['date']})" for p in info["people"] if "Alumni" in p["type"] or "Left" in p["type"] or "High Intent" in p["type"] or "Joined" in p["date"] or "Started" in p["date"]]
                if movements:
                    r["Job Changes Count"] = str(len(movements))
                    r["Job Changes / Movement Summary"] = " | ".join(movements)
                
                # Format Key Roster
                roster = [f"{p['name']} ({p['role']})" for p in info["people"] if "Current" in p["type"]]
                if roster:
                    r["Key People / Roster Summary"] = "; ".join(roster)
        master_rows.append(r)

with open(r"C:\Users\joela\OneDrive\Documents\Python\bd-engine\signalbase_demo_enriched.csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=m_fieldnames)
    writer.writeheader()
    writer.writerows(master_rows)

print(f"Successfully updated master signalbase_demo_enriched.csv!")
