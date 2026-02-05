#!/usr/bin/env python3
"""
Check database for unique document types
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.database import SessionLocal
from backend.app.models import Facility
from sqlalchemy import func

db = SessionLocal()

# Get all unique types with counts
results = db.query(
    Facility.type, 
    func.count(Facility.id).label('count')
).filter(
    Facility.type.isnot(None)
).group_by(
    Facility.type
).order_by(
    func.count(Facility.id).desc()
).all()

print("=" * 80)
print("DATABASE DOCUMENT TYPES")
print("=" * 80)

total_facilities = db.query(Facility).count()
print(f"Total facilities: {total_facilities}\n")

for row in results:
    print(f"  {row[0]}: {row[1]} ({(row[1]/total_facilities)*100:.1f}%)")

print("\n" + "=" * 80)
print(f"Unique types: {len(results)}")

# Check for null types
null_count = db.query(Facility).filter(Facility.type == "" or Facility.type == None).count()
print(f"Empty/Null types: {null_count}")

db.close()
