"""
Generate 20 random hotels from "Turizm İşletmesi Belgesi" category for testing
"""
import sqlite3
import random

db_path = '../data/leads.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all Turizm İşletmesi Belgesi hotels
cursor.execute("""
    SELECT id, name, sehir, ilce, type 
    FROM facilities 
    WHERE type = 'Turizm İşletmesi Belgesi'
    ORDER BY RANDOM()
    LIMIT 20
""")

hotels = cursor.fetchall()
conn.close()

print("\n" + "="*100)
print("TEST SET: 20 Random 'Turizm İşletmesi Belgesi' Hotels")
print("="*100 + "\n")

for idx, hotel in enumerate(hotels, 1):
    print(f"{idx:2}. {hotel['name']:50} | {hotel['sehir']:15} | {hotel['ilce']}")

# Save to JSON for test script
import json
test_data = [
    {
        'name': hotel['name'],
        'city': hotel['sehir'],
        'district': hotel['ilce'],
        'type': hotel['type'],
        'id': hotel['id']
    }
    for hotel in hotels
]

with open('test_set.json', 'w', encoding='utf-8') as f:
    json.dump(test_data, f, indent=2, ensure_ascii=False)

print(f"\n✓ Saved to test_set.json: {len(test_data)} hotels")
print("="*100)
