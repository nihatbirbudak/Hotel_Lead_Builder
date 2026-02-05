#!/usr/bin/env python3
import sys
sys.path.insert(0, 'app')
from services.discovery import find_website

hotels = [
    ("PEARL ISTANBUL HOUSE", "İSTANBUL", "https://pearlhotelistanbul.com.tr/"),
    ("ALEXİA RESORT & SPA HOTEL", "ANTALYA", "https://alexiaresort.com/"),
    ("ADMİRAL OTELİ", "MERSİN", "https://www.admiralotel.com/"),
]

print("="*80)
print("FINAL DOMAIN GUESSING TEST")
print("="*80)

found = 0
for name, city, expected_url in hotels:
    print(f"\n{name} ({city})")
    print(f"Expected: {expected_url}")
    result = find_website(name, city)
    if result and result.get('url'):
        print(f"Found:    {result['url']}")
        print(f"Score:    {result.get('score', 0):.1f}")
        found += 1
        print("✓ SUCCESS")
    else:
        print("✗ FAILED")

print(f"\n{'='*80}")
print(f"Result: {found}/3 found ({found*100//3}%)")
print(f"{'='*80}")
