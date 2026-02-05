#!/usr/bin/env python3
import sys
sys.path.insert(0, 'app')
from services.discovery import find_website

result = find_website('ALEXIA RESORT & SPA HOTEL', 'ANTALYA')
print(f"\n\nFINAL RESULT FOR ALEXIA:")
print(f"URL: {result.get('url', 'NOT FOUND') if result else 'None'}")
print(f"Score: {result.get('score', 0) if result else 0}")
print(f"Source: {result.get('source', 'unknown') if result else 'unknown'}")
