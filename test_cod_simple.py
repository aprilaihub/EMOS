#!/usr/bin/env python3
"""Simple test for COD database"""

from Information_Units.Databases.Cod.CodDatabase import CodDatabase


class SimpleLogger:
    def log(self, message):
        print(f"[LOG] {message}")


# Test
logger = SimpleLogger()
db = CodDatabase(logger=logger)

print(f"Database: {db.info()}")
print()

# Test 1: Query Fe
print("Test 1: Query 'Fe'")
result = db.retrieve({'query': 'Fe', 'limit': 1})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

# Test 2: Query with nelements
print("Test 2: Query 'Al2O3' with nelements=2")
result = db.retrieve({'query': 'Al2O3', 'limit': 1, 'nelements': 2})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

# Test 3: Query with nperiodic_dimensions
print("Test 3: Query 'Fe' with nperiodic_dimensions=3")
result = db.retrieve({'query': 'Fe', 'limit': 1, 'nperiodic_dimensions': 3})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()


# Test 4: Query for element Fe using 'query' parameter
print("Test 4: Query for element 'Fe'")
result = db.retrieve({'query': 'Fe', 'limit': 1})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()

# Test 5: Query with chemical_formula_descriptive
print("Test 5: Query with chemical_formula_descriptive='Al2O3'")
result = db.retrieve({'query': '', 'limit': 1, 'chemical_formula_descriptive': 'Al2O3'})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
print()
