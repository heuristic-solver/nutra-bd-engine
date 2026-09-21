import json
from collections import Counter

file_path = "company_info_output/kb_full/checkpoint_kb_full.jsonl"

total = 0
signals_count = 0
roles_count = 0
funding_count = 0
movements_count = 0

all_roles = []
all_funding = []
all_movements = []

with open(file_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        total += 1
        data = json.loads(line)
        roles = data.get("role_changes", [])
        funding = data.get("funding_events", [])
        moves = data.get("strategic_movements", [])
        
        all_roles.extend(roles)
        all_funding.extend(funding)
        all_movements.extend(moves)
        
        if roles or funding or moves:
            signals_count += 1
        if roles:
            roles_count += 1
        if funding:
            funding_count += 1
        if moves:
            movements_count += 1

print(f"Total Companies Scanned in Checkpoint: {total}")
print(f"Companies with Signals: {signals_count} ({signals_count/total*100:.1f}%)")
print(f"Companies with Roles: {roles_count}")
print(f"Companies with Funding: {funding_count}")
print(f"Companies with Movements: {movements_count}")
print(f"Total Role Events: {len(all_roles)}")
print(f"Total Funding Events: {len(all_funding)}")
print(f"Total Movement Events: {len(all_movements)}")

print("\nSample Role Events:")
for r in all_roles[:5]:
    print(f"  - [{r.get('movement_type')}] {r.get('person_name')} ({r.get('role_title')}) @ {r.get('company_name')} | Src: {r.get('source_name')}")

print("\nSample Strategic Movements:")
for m in all_movements[:5]:
    print(f"  - [{m.get('category')}] {m.get('company_name')}: {m.get('headline')}")
