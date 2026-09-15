# Toy IU Tutorial

This page provides a minimal, end-to-end toy Information Unit (IU) example you can add to EMOS.

## Toy Example: Add a Demo Database IU

Goal: add a tiny database Information Unit (IU) named **Toy CIF Demo** that always returns one hardcoded CIF string.

### Step 1: Add one database entry in `devtools/source_data.json`

Under `information_units -> databases`, add one new key:

```json
"Toy CIF Demo": "Tutorial IU that returns one hardcoded CIF string for testing"
```

### Step 2: Generate scaffolding

```bash
python devtools/contribution_tool.py
```

This generates a new IU folder and updates the database factory.

### Step 3: Implement the generated database class

Open the generated file (expected path):

`Information_Units/Databases/ToyCifDemo/ToyCifDemoDatabase.py`

Replace `retrieve()` with:

```python
def retrieve(self, inputs: dict) -> dict:
    queries = {k: v for k, v in inputs.items() if v is not None and v != ''}

    cif_string = """data_toy_nacl
_symmetry_space_group_name_H-M 'F m -3 m'
_cell_length_a 5.6402
_cell_length_b 5.6402
_cell_length_c 5.6402
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_symmetry_Int_Tables_number 225
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Na1 Na 0.0 0.0 0.0
Cl1 Cl 0.5 0.5 0.5
"""

    return {
        "source": "toy_cif_demo",
        "queries": queries,
        "cif_strings": [cif_string],
    }
```

### Step 4: Add property mapping

Create:

`Information_Units/property_mappings/sources/databases/toy_cif_demo.json`

With this minimal content:

```json
{
  "description": "Source-specific mappings for toy_cif_demo (databases).",
  "version": "2.0",
  "source_type": "databases",
  "source": "toy_cif_demo",
  "properties": {
    "chemical_formula_descriptive": {
      "name": "chemical_formula_descriptive",
      "retrievable": true
    },
    "elements": {
      "name": "elements",
      "retrievable": true
    },
    "id": {
      "name": "id",
      "retrievable": true
    }
  }
}
```

### Step 5: Add IU feature button/panel wiring

```bash
python devtools/iu_features/manage_iu_features.py
```

Choose:
- IU type: `database`
- Action: `add`
- IU id: `toy_cif_demo`

### Step 6: Run and verify

1. Start backend: `python backend/app.py`
2. Open the UI and run the new **Toy CIF Demo** IU.
3. Confirm the result includes one CIF string.

This toy IU is intentionally simple and safe; once it works, use the same flow for real APIs.
