#!/usr/bin/env python3
"""
Debug domain generation to see which domains are created
"""
import sys
sys.path.insert(0, 'app')

from services.discovery import find_website

test_cases = [
    ("PEARL ISTANBUL HOUSE", "İSTANBUL"),
    ("ALEXİA RESORT & SPA HOTEL", "ANTALYA"),
    ("ADMİRAL OTELİ", "MERSİN"),
]

for hotel_name, city in test_cases:
    print(f"\n{'='*80}")
    print(f"Testing: {hotel_name}")
    print(f"City: {city}")
    print(f"{'='*80}")
    
    # Call find_website - it logs domain generation
    result = find_website(hotel_name, city)
    
    print(f"\nResult: {result}")
