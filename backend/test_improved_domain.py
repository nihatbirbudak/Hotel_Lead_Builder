"""
Test improved domain guessing: Can we find the previously failed hotels?
"""
from app.services.discovery import find_website

test_cases = [
    {"name": "PEARL ISTANBUL HOUSE", "city": "İSTANBUL", "expected": "pearlhotelistanbul.com.tr"},
    {"name": "ALEXİA RESORT & SPA HOTEL", "city": "ANTALYA", "expected": "alexiaresort.com"},
    {"name": "ADMİRAL OTELİ", "city": "MERSİN", "expected": "admiralotel.com"},
]

print("\n" + "="*120)
print("TEST: Improved Domain Guessing Algorithm")
print("="*120 + "\n")

for idx, test in enumerate(test_cases, 1):
    name = test['name']
    city = test['city']
    
    print(f"[{idx}/3] Testing: {name}")
    print(f"  City: {city}")
    print(f"  Expected domain: {test['expected']}")
    print("-" * 120)
    
    result = find_website(name, city)
    
    if result.get('url'):
        print(f"  [FOUND] {result['url']}")
        print(f"  Score: {result['score']:.1f}")
        print(f"  Source: {result['source']}")
        
        # Check if expected domain is in URL
        if test['expected'].split('/')[0] in result['url'].lower():
            print(f"  ✓ CORRECT DOMAIN!")
        else:
            print(f"  ~ Different domain (but valid)")
    else:
        print(f"  [NOT FOUND] Reason: {result.get('reason', 'unknown')}")
    
    print()

print("="*120)
