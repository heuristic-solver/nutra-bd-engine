import requests
import json

def get_wikidata_company_info(company_name: str):
    # 1. Search entity ID
    search_url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={requests.utils.quote(company_name)}&language=en&format=json"
    r = requests.get(search_url, headers={"User-Agent": "NutraIntel/1.0"}, timeout=4)
    data = r.json()
    results = data.get("search", [])
    if not results:
        return None
    entity_id = results[0]["id"]
    label = results[0].get("label", "")
    desc = results[0].get("description", "")

    # 2. Get claims for CEO (P169), Chairperson (P488), Founder (P112), Inception (P571)
    entity_url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={entity_id}&props=claims|labels&languages=en&format=json"
    r2 = requests.get(entity_url, headers={"User-Agent": "NutraIntel/1.0"}, timeout=4)
    ent_data = r2.json().get("entities", {}).get(entity_id, {})
    claims = ent_data.get("claims", {})

    def resolve_item_label(item_id: str) -> str:
        try:
            u = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={item_id}&props=labels&languages=en&format=json"
            res = requests.get(u, headers={"User-Agent": "NutraIntel/1.0"}, timeout=3).json()
            return res.get("entities", {}).get(item_id, {}).get("labels", {}).get("en", {}).get("value", item_id)
        except Exception:
            return item_id

    # Resolve CEO (P169)
    ceos = []
    for c in claims.get("P169", []):
        try:
            val_id = c["mainsnak"]["datavalue"]["value"]["id"]
            ceos.append(resolve_item_label(val_id))
        except Exception:
            pass

    # Resolve Founder (P112)
    founders = []
    for c in claims.get("P112", []):
        try:
            val_id = c["mainsnak"]["datavalue"]["value"]["id"]
            founders.append(resolve_item_label(val_id))
        except Exception:
            pass

    return {
        "entity_id": entity_id,
        "label": label,
        "description": desc,
        "ceos": ceos,
        "founders": founders
    }

for co in ["Lonza Group", "Glanbia", "ChromaDex", "Balchem", "ADM"]:
    info = get_wikidata_company_info(co)
    print(f"\n[{co}]: {info}")
