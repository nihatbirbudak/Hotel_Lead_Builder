"""
Comprehensive Test: 20 Hotels from Turizm İşletmesi Belgesi Category
Tests real hotel discovery with detailed failure analysis
"""
import json
import logging
from app.services.discovery import find_website
import sys
import os

# Fix encoding for Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(message)s')

# Load test set
with open('test_set.json', 'r', encoding='utf-8') as f:
    test_hotels = json.load(f)

print("\n" + "="*120)
print("COMPREHENSIVE DISCOVERY TEST - 20 Premium Hotels")
print("Category: Turizm İşletmesi Belgesi (Expected >99% have websites)")
print("="*120 + "\n")

results = []
found_count = 0

for idx, hotel in enumerate(test_hotels, 1):
    name = hotel['name']
    city = hotel['city']
    
    print(f"[{idx:2}/20] Testing: {name:50} ({city})")
    print("-" * 120)
    
    try:
        result = find_website(name, city)
        
        if result.get('url'):
            found_count += 1
            print(f"  [FOUND] {result['url']}")
            print(f"    Score: {result['score']:.1f} | Source: {result['source']}")
            status = "FOUND"
            url = result['url']
            score = result['score']
        else:
            reason = result.get('reason', 'unknown')
            print(f"  [FAILED] Reason: {reason}")
            status = "FAILED"
            url = None
            score = 0
        
        results.append({
            'name': name,
            'city': city,
            'status': status,
            'url': url,
            'score': score,
            'reason': result.get('reason', 'N/A')
        })
        
    except Exception as e:
        print(f"  [ERROR] {str(e)[:100]}")
        results.append({
            'name': name,
            'city': city,
            'status': "ERROR",
            'url': None,
            'score': 0,
            'reason': str(e)[:50]
        })
    
    print()

# ============================================================================
# ANALYSIS
# ============================================================================
print("\n" + "="*120)
print("TEST RESULTS SUMMARY")
print("="*120 + "\n")

# By status
found = [r for r in results if 'FOUND' in r['status']]
failed = [r for r in results if 'FAILED' in r['status']]
errors = [r for r in results if 'ERROR' in r['status']]

print(f"[FOUND]        {len(found):2}/20 ({len(found)/len(results)*100:5.1f}%)")
print(f"[FAILED]       {len(failed):2}/20 ({len(failed)/len(results)*100:5.1f}%)")
print(f"[ERROR]        {len(errors):2}/20 ({len(errors)/len(results)*100:5.1f}%)")
print()

# By reason
from collections import Counter
failure_reasons = Counter([r['reason'] for r in failed])
print("Failure Reasons:")
for reason, count in failure_reasons.most_common():
    print(f"  - {reason:30} : {count:2} hotels")

print("\n" + "="*120)
print("DETAILED RESULTS")
print("="*120 + "\n")

for idx, r in enumerate(results, 1):
    status_symbol = "[OK]" if "FOUND" in r['status'] else "[XX]"
    print(f"{idx:2}. {status_symbol} {r['name']:50} | {r['city']:15} | Score: {r['score']:5.1f}")
    if r['url']:
        print(f"    URL: {r['url'][:80]}")
    if r['reason'] != 'N/A' and 'FAILED' in r['status']:
        print(f"    Reason: {r['reason']}")

print("\n" + "="*120)
print(f"OVERALL SUCCESS RATE: {len(found)}/{len(results)} = {len(found)/len(results)*100:.1f}%")
print("="*120 + "\n")

# Save detailed report
with open('test_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[OK] Detailed report saved to: test_results.json")
