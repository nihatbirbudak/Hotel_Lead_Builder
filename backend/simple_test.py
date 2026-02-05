#!/usr/bin/env python3
import sys
sys.path.insert(0, 'app')
from services.discovery import find_website

hotels = [
    ("PEARL ISTANBUL HOUSE", "ISTANBUL", "pearlhotelistanbul"),
    ("ALEXIA RESORT & SPA HOTEL", "ANTALYA", "alexiaresort"),  
    ("ADMIRAL OTELI", "MERSIN", "admiralotel"),
]

print("=" * 80)
print("FINAL DOMAIN GUESSING TEST")
print("=" * 80)

found = 0
for name, city, expected_domain in hotels:
    print(f"\n{name} ({city})")
    result = find_website(name, city)
    if result and result.get('url'):
        url = result['url']
        score = result.get('score', 0)
        print(f"Found: {url} (Score: {score:.0f})")
        if expected_domain.lower() in url.lower():
            print("SUCCESS")
            found += 1
        else:
            print("FOUND BUT WRONG DOMAIN")
    else:
        print("NOT FOUND")

print(f"\n{'='*80}")
print(f"Result: {found}/3 success rate = {found*100//3}%")
print(f"{'='*80}")
