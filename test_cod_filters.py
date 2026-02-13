#!/usr/bin/env python3
"""Test script for COD database with advanced filters"""

from Information_Units.Databases.Cod.CodDatabase import CodDatabase


class SimpleLogger:
    def log(self, message):
        print(f"[LOG] {message}")


# Initialize database
logger = SimpleLogger()
db = CodDatabase(logger=logger)

print(f"Database: {db.info()}")
print()

# Test 1: Simple composition query
print("=" * 80)
print("Test 1: Query 'Fe' (limit: 5)")
print("=" * 80)
result = db.retrieve({'query': 'Fe', 'limit': 5})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

# Test 2: Composition with nelements filter
print("=" * 80)
print("Test 2: Query 'Al2O3' with nelements=2 (limit: 5)")
print("=" * 80)
result = db.retrieve({
    'query': 'Al2O3',
    'limit': 5,
    'nelements': 2
})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

# Test 3: Composition with natoms filter
print("=" * 80)
print("Test 3: Query 'Si' with natoms range [1, 8] (limit: 5)")
print("=" * 80)
result = db.retrieve({
    'query': 'Si',
    'limit': 5,
    'natoms': [1, 8]
})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

# Test 4: Composition with volume filter
print("=" * 80)
print("Test 4: Query 'Fe' with volume range [20, 100] (limit: 5)")
print("=" * 80)
result = db.retrieve({
    'query': 'Fe',
    'limit': 5,
    'volume': [20, 100]
})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

# Test 5: Composition with spacegroup_number filter
print("=" * 80)
print("Test 5: Query 'Fe' with spacegroup_number=229 (Im-3m, cubic) (limit: 5)")
print("=" * 80)
result = db.retrieve({
    'query': 'Fe',
    'limit': 5,
    'spacegroup_number': 229
})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

# Test 6: Multiple filters combined
print("=" * 80)
print("Test 6: Query 'Al' with multiple filters (nelements=1, natoms=[1,4], volume=[10,50]) (limit: 5)")
print("=" * 80)
result = db.retrieve({
    'query': 'Al',
    'limit': 5,
    'nelements': 1,
    'natoms': [1, 4],
    'volume': [10, 50]
})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

print("=" * 80)
print("Testing complete!")
print("=" * 80)
