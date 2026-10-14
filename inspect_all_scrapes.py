import json
import csv
import glob

print("=== INSPECTING ALL DATASETS ===")
# 1. data-slayer
with open("data_slayer_results.json", encoding="utf-8") as f:
    ds = json.load(f)

# 2. inovaflow
with open("inovaflow_results.json", encoding="utf-8") as f:
    ino = json.load(f)

# 3. thirdwatch
with open("thirdwatch_results.json", encoding="utf-8") as f:
    tw = json.load(f)

# 4. george_dev
with open("george_dev_results.json", encoding="utf-8") as f:
    gd = json.load(f)

# 5. exuberant_volley
with open("exuberant_volley_results.json", encoding="utf-8") as f:
    ev = json.load(f)

print(f"data_slayer keys: {list(ds.keys())}")
print(f"inovaflow len: {len(ino)}")
print(f"thirdwatch keys: {list(tw.keys()) if isinstance(tw, dict) else len(tw)}")
print(f"george_dev keys: {list(gd.keys()) if isinstance(gd, dict) else len(gd)}")
print(f"exuberant_volley len: {len(ev) if isinstance(ev, list) else len(ev.get('items', []))}")

# Check company details in thirdwatch
if isinstance(tw, dict):
    for k, v in tw.items():
        if isinstance(v, list):
            print(f"thirdwatch[{k}]: {len(v)} items")
            for item in v[:2]:
                print(f"  {item.get('fullName')} | {item.get('headline') or item.get('currentTitle')} | {item.get('url')}")

# Check company details in george_dev
if isinstance(gd, dict):
    for k, v in gd.items():
        if isinstance(v, list):
            print(f"george_dev[{k}]: {len(v)} items")
            for item in v[:2]:
                print(f"  {item.get('fullName')} | {item.get('title')} | {item.get('url')}")
