#!/usr/bin/env python3
"""Test script for COD database with property mapping"""

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

# Test 2: Using standard property name 'nelements' (maps to COD: nelements)
print("=" * 80)
print("Test 2: Query 'Al2O3' with nelements=2 (standard name maps to COD) (limit: 5)")
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

# Test 3: Using standard property name 'natoms' with range (maps to COD: natoms)
print("=" * 80)
print("Test 3: Query 'Si' with natoms range [1, 8] (standard name maps to COD) (limit: 5)")
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

# Test 4: Using standard property name 'volume' (maps to COD: volume)
print("=" * 80)
print("Test 4: Query 'Fe' with volume range [20, 100] (standard name maps to COD) (limit: 5)")
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

# Test 5: Using standard property name 'spacegroup_number' (maps to COD: spacegroup_number)
print("=" * 80)
print("Test 5: Query 'Fe' with spacegroup_number=229 (standard name maps to COD) (limit: 5)")
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

# Test 6: Multiple standard property filters combined
print("=" * 80)
print("Test 6: Multiple filters using standard names (all mapped to COD) (limit: 5)")
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

# Test 7: Using standard property name 'lattice_a' (maps to COD: _cod_a)
print("=" * 80)
print("Test 7: Query 'Al' with lattice_a range (standard name maps to _cod_a in COD) (limit: 5)")
print("=" * 80)
result = db.retrieve({
    'query': 'Al',
    'limit': 5,
    'lattice_a': [3.0, 4.0]
})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

print("=" * 80)
print("Testing complete!")
print("=" * 80)
