#!/usr/bin/env python3
"""
Test script for discovery algorithm
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.discovery import find_website
import logging

# Setup logging to see detailed output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s'
)

# Test hotels
test_hotels = [
    ("Sarp", "Rize"),
    ("1249 SARUHAN", "Istanbul"),
    ("14 SUİT PANSİYON", "Samsun"),
    ("OTEL PARIS", "Ankara"),
]

print("=" * 80)
print("DISCOVERY TEST")
print("=" * 80)

for hotel_name, city in test_hotels:
    print(f"\n\nTesting: {hotel_name} ({city})")
    print("-" * 80)
    result = find_website(hotel_name, city)
    if result:
        print(f"✓ FOUND: {result['url']} (score: {result['score']:.1f})")
    else:
        print(f"✗ NOT FOUND")
    print("-" * 80)

print("\n\nTEST COMPLETE")
