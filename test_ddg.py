#!/usr/bin/env python3
"""
Test DDG API response structure
"""
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

query = "Sarp website otel"

print(f"Testing DDG HTML API with query: '{query}'")
print("=" * 80)

try:
    resp = requests.post(
        "https://html.duckduckgo.com/html/",
        data={'q': query},
        headers=HEADERS,
        timeout=10
    )
    
    print(f"Status Code: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('content-type')}")
    print(f"Content Length: {len(resp.text)}")
    print("\n" + "=" * 80)
    print("HTML Response (first 3000 chars):")
    print("=" * 80)
    print(resp.text[:3000])
    
    print("\n" + "=" * 80)
    print("Parsing with BeautifulSoup...")
    print("=" * 80)
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Find all links
    links = soup.find_all('a', limit=10)
    print(f"Found {len(links)} links:")
    for i, link in enumerate(links):
        href = link.get('href', 'NO HREF')
        text = link.get_text(strip=True)[:60]
        print(f"  {i+1}. {href[:80]}")
        print(f"     Text: {text}...")
    
    # Check for result containers
    results = soup.find_all(class_='result', limit=5)
    print(f"\nFound {len(results)} result containers")
    
    # Check all divs with class containing 'result'
    result_divs = soup.find_all('div', class_=lambda x: x and 'result' in x.lower(), limit=5)
    print(f"Found {len(result_divs)} divs with 'result' in class")
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
