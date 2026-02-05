"""
Quick debug: Why are PEARL and ALEXIA failing?
"""
from app.services.discovery import validate_hotel_content

test_urls = [
    {
        "url": "https://pearlhotelistanbul.com.tr/",
        "name": "PEARL ISTANBUL HOUSE",
        "city": "İSTANBUL"
    },
    {
        "url": "https://alexiaresort.com/",
        "name": "ALEXİA RESORT & SPA HOTEL",
        "city": "ANTALYA"
    },
    {
        "url": "https://www.admiralotel.com/otel/",
        "name": "ADMİRAL OTELİ",
        "city": "MERSİN"
    }
]

print("\n" + "="*100)
print("DEBUG: Validation Test for Previously Failed Hotels")
print("="*100 + "\n")

for test in test_urls:
    print(f"Testing: {test['name']} ({test['city']})")
    print(f"URL: {test['url']}")
    print("-" * 100)
    
    result = validate_hotel_content(test['url'], test['name'], test['city'])
    
    print(f"Result: {result['is_hotel']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Indicators: {result['indicators']}")
    print()

print("="*100)
