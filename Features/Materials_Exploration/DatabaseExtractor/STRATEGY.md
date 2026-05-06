# Database Extractor — Implementation Strategy

## 1. UI for Input

**Properties Selection**
- Multi-select searchable dropdown populated from `common_properties.json`
- Group properties by their `category` field (structural, electronic, mechanical, etc.) for easier browsing

**Batch Size**
- Simple numeric input field (default: 100, max: 1000)

**Mode Selection**
- Radio button: **Strict** | **Lenient**
  - *Strict*: only databases that have all selected properties as `retrievable: true` in their source mapping will be queried
  - *Lenient*: all active databases are queried; non-retrievable properties are silently dropped per database

**Database Selection**
- Comes from the existing `active_databases` multi-select (already in the feature's `extract_inputs`)

---

## 2. UI for Output

- **Stats cards** (default view): one card per database showing "X/Y properties retrieved, Z records returned"
  - Keeps the default view clean regardless of how many properties were queried
- **Expandable transposed table** (per card, shown on demand):
  - Rows = properties queried, Columns = databases
  - Cells = ✓ (retrieved) / — (skipped/unavailable)
  - Scrolls vertically, which is natural since properties outnumber databases
- **Download button**: exports the full result dict as a `.json` file


---

## 3. Logic for Database Extraction

```
load_property_mappings(source_db)
  → returns: {common_property_key → {name, retrievable, range_support}}

for each selected database:
    mapping = load_property_mappings(database)

    if STRICT mode:
        skip database if any selected property is missing or retrievable=false

    if LENIENT mode:
        queryable_props = [p for p in selected_props if mapping[p].retrievable == true]
        (silently skip the rest)

    results[database] = db_instance.query(
        properties=queryable_props,
        limit=batch_size
    )

return {
    "query_properties": [...],          # original input properties
    "mode": "strict" | "lenient",
    "batch_size": N,
    "results": {
        "materialsproject": {
            "properties_used": [...],   # subset actually queried
            "properties_skipped": [...],
            "records": [...]
        },
        ...
    }
}
```

**Key design note**: The `property_loader.py` (already in `property_mappings/`) should be used to resolve common property keys → database-specific field names before querying. The `retrievable` flag in each source JSON is the ground truth for strict/lenient filtering.
