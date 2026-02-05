"""
Test script for new validation algorithm
Tests 3 hotels with different characteristics
"""
import sys
sys.path.insert(0, '.')

from app.services.discovery import find_website
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

# Test cases: Hotels that likely have websites
test_hotels = [
    {"name": "DRAGUT POINT SOUTH HOTEL", "city": "MUĞLA", "reason": "Sister hotel of NORTH (found)"},
    {"name": "GRAND HYATT ISTANBUL", "city": "İSTANBUL", "reason": "International chain hotel"},
    {"name": "HILTON GARDEN INN ISTANBUL BEYLIKDUZU", "city": "İSTANBUL", "reason": "Hilton brand hotel"},
]

print("\n" + "="*80)
print("VALIDATION ALGORITHM TEST - 3 Hotels")
print("="*80)

results = []

for idx, hotel in enumerate(test_hotels, 1):
    print(f"\n[TEST {idx}/3] {hotel['name']} ({hotel['city']})")
    print(f"Reason: {hotel['reason']}")
    print("-" * 80)
    
    try:
        result = find_website(hotel['name'], hotel['city'])
        
        if result.get('url'):
            print(f"✓ SUCCESS: {result['url']}")
            print(f"  Score: {result['score']:.1f}")
            print(f"  Source: {result['source']}")
            status = "✓ FOUND"
        else:
            print(f"✗ FAILED: {result.get('reason', 'No website found')}")
            status = "✗ NOT FOUND"
        
        results.append({
            'name': hotel['name'],
            'status': status,
            'url': result.get('url', 'N/A'),
            'score': result.get('score', 0)
        })
        
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        results.append({
            'name': hotel['name'],
            'status': "✗ ERROR",
            'url': 'N/A',
            'score': 0
        })

print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

for r in results:
    score_str = f"{r['score']:.1f}" if r['score'] is not None else "0.0"
    url_str = (r['url'][:40] if r['url'] and len(r['url']) > 40 else r['url']) if r['url'] else 'N/A'
    print(f"{r['status']:15} | {r['name']:30} | {url_str:40} | Score: {score_str}")

success_count = sum(1 for r in results if '✓' in r['status'])
print(f"\nSuccess Rate: {success_count}/{len(results)} ({success_count/len(results)*100:.0f}%)")
print("="*80)
