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

print("=" * 80)
print("Test 1: Query 'Fe' (limit: 5)")
print("=" * 80)
result = db.retrieve({'query': 'Fe', 'limit': 5})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

# Test 2: Query with nelements
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

# Test 3: Query with nsites

# Test 3: Query with nperiodic_dimensions
print("=" * 80)
print("Test 3: Query 'Fe' with nperiodic_dimensions=3 (limit: 5)")
print("=" * 80)
result = db.retrieve({
    'query': 'Fe',
    'limit': 5,
    'nperiodic_dimensions': 3
})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

# Test 4: Query for element Fe using 'query' parameter
print("=" * 80)
print("Test 4: Query for element 'Fe' (limit: 5)")
print("=" * 80)
result = db.retrieve({
    'query': 'Fe',
    'limit': 5
})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

# Test 5: Query with chemical_formula_descriptive
print("=" * 80)
print("Test 5: Query with chemical_formula_descriptive='Al2O3' (limit: 5)")
print("=" * 80)
result = db.retrieve({
    'query': '',
    'limit': 5,
    'chemical_formula_descriptive': 'Al2O3'
})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

print("=" * 80)
print("Testing complete!")
print("=" * 80)
