#!/usr/bin/env python3
"""Simple test for AFLOWLIB database"""

from Information_Units.Databases.Aflowlib.AflowlibDatabase import AflowlibDatabase


class SimpleLogger:
    def log(self, message):
        print(f"[LOG] {message}")


# Test
logger = SimpleLogger()
db = AflowlibDatabase(logger=logger)

print(f"Database: {db.info()}")
print()

# Test 1: Query Fe
print("Test 1: Query 'Fe'")
result = db.retrieve({'query': 'Fe', 'limit': 1})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")

print()

# Test 2: Query Al2O3
print("Test 2: Query 'Al2O3'")
result = db.retrieve({'query': 'Al2O3', 'limit': 1})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")

print()

# Test 3: Query all (limit 2)
print("Test 3: Query all (limit 2)")
result = db.retrieve({'query': '', 'limit': 2})
print(f"Result: {len(result)} files")
for f in result:
    print(f"  - {f}")
