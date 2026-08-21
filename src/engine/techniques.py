"""
Techniques Directory Engine - Python version
38 techniques comprehensive directory
"""

import json
from pathlib import Path

dir_path = Path(__file__).parent.parent.parent / "data" / "comprehensive_manual_therapy_directory.json"
with open(dir_path, 'r', encoding='utf-8') as f:
    DIRECTORY = json.load(f)

def get_all_techniques():
    all_techs = []
    for cat in DIRECTORY['categories']:
        all_techs.extend(cat['techniques'])
    return all_techs

def get_by_id(tid):
    for t in get_all_techniques():
        if t['id'] == tid:
            return t
    return None

def get_by_region_and_finding(region, finding_type, irritability='medium'):
    region_lower = region.lower()
    filtered = []
    for t in get_all_techniques():
        regions = [r.lower() for r in t['best_for_regions']]
        matches_region = any(region_lower in r or r in region_lower or 'all' in r or 'whole' in r for r in regions)
        matches_finding = finding_type in t['finding_type_match']
        if matches_region and matches_finding:
            filtered.append(t)
    return filtered

def get_by_finding(finding_type):
    return [t for t in get_all_techniques() if finding_type in t['finding_type_match']]

def get_by_author(author):
    al = author.lower()
    return [t for t in get_all_techniques() if al in t['origin'].lower() or al in t['name'].lower()]

def search(query):
    q = query.lower()
    results = []
    for t in get_all_techniques():
        blob = f"{t['name']} {t['acronym']} {t['id']} {t['origin']} {t['classification']} {' '.join(t['best_for_regions'])} {' '.join(t['finding_type_match'])}".lower()
        if q in blob:
            results.append(t)
    return results

def demo():
    print(f"Total techniques: {len(get_all_techniques())}")
    print("\n--- Lumbar weak medium ---")
    for t in get_by_region_and_finding('Lumbar', 'weak', 'medium'):
        print(f"{t['id']}: {t['name']} [{t['evidence_level']}]")
    print("\n--- Painful techniques ---")
    for t in get_by_finding('painful')[:10]:
        print(t['name'])
    print("\n--- Ali Marzok Methods ---")
    for t in get_by_author('Ali Marzok'):
        print(f"{t['id']}: {t['name']} - {t['origin']}")

if __name__ == "__main__":
    demo()
