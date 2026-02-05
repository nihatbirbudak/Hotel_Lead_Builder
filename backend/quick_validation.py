#!/usr/bin/env python3
"""
Quick validation of improved domain guessing on critical hotels
"""
import sys
sys.path.insert(0, 'app')
from services.discovery import find_website

# 10 key test hotels from the 20-hotel set
test_hotels = [
    ("NEW WAY", "KAYSERI", True),  # Known success
    ("THEODOSIUS HOTEL", "ISTANBUL", True),  # Known success  
    ("COFFEE BRUTUS", "BURSA", True),  # Known success
    ("PEARL ISTANBUL HOUSE", "ISTANBUL", True),  # JUST FIXED
    ("DRAGUT POINT SOUTH HOTEL", "MUGLA", True),  # International chain
]

print("="*70)
print("QUICK VALIDATION TEST - KEY HOTELS")
print("="*70)

success = 0
for name, city, should_find in test_hotels:
    result = find_website(name.upper(), city.upper())
    if result and result.get('url'):
        status = "FOUND" if should_find else "UNEXPECTED"
        success += 1 if should_find else 0
        print(f"[{status}] {name:40} ({city:12}) Score:{result.get('score', 0):5.0f}")
    else:
        status = "NOT FOUND"
        success += 0 if should_find else 1
        print(f"[{status}] {name:40} ({city:12})")

print("="*70)
print(f"RESULT: {success}/{len(test_hotels)} success = {100*success//len(test_hotels)}%")
print("="*70)
