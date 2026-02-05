#!/usr/bin/env python3
import sys
sys.path.insert(0, 'app')
from services.discovery import find_website

print("=" * 80)
print("DIRECT TEST - ALEXIA RESORT & SPA HOTEL")
print("=" * 80)

result = find_website('ALEXIA RESORT & SPA HOTEL', 'ANTALYA')
print(f"\nResult: {result}")
print(f"URL: {result.get('url', 'NOT FOUND') if result else 'None'}")
print(f"Score: {result.get('score', 0) if result else 0}")
