# Generator IU Tutorial

This page provides a minimal, end-to-end demo Generator Information Unit (IU) example you can add to EMOS.

Before implementing a generator IU, read the [required IU data contracts](iu-data-contracts.md).

## Demo Example: Add a CIF Generator IU

Goal: add a small generator Information Unit (IU) named **CIF Demo Generator** that returns CIF structures in response to a requested batch size.

### Step 1: Add one generator entry in `devtools/source_data.json`

In this step, you register a new IU in the source-of-truth metadata so EMOS can derive its id, folder/class naming, and UI listing metadata.

Under `information_units -> generators`, add one new key:

```json
"CIF Demo Generator": "Demo generator that returns hardcoded CIF structures for testing"
```

### Step 2: Generate scaffolding

In this step, EMOS generates the backend IU template files and updates factory wiring for your new generator IU.

```bash
python devtools/contribution_tool.py
```

This generates a new IU folder and updates the generator factory.
It also creates a property mapping template at:

`Information_Units/property_mappings/sources/generators/cif_demo_generator.json`

The script is interactive. When prompted to apply detected changes, confirm with `yes` (or `y`).

### Step 3: Implement the generated generator class

In this step, you replace the stub generation logic with a small implementation that returns CIF output in batch form.

Open the generated file (expected path):

`Information_Units/Generators/CifDemoGenerator/CifDemoGeneratorGenerator.py`

Replace `generate()` with:

```python
def generate(self, inputs: dict) -> dict:
    num_structures = int(inputs.get("num_structures", 1) or 1)
    if num_structures < 1:
        num_structures = 1

    cif_string = """data_demo_nacl
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

    cif_strings = [cif_string] * num_structures

    return {
        "status": "success",
        "message": f"Generated {num_structures} demo structure(s)",
        "source": "cif_demo_generator",
        "queries": inputs,
        "cif_strings": cif_strings,
        "num_structures": num_structures,
    }
```

### Step 4: Update the generated property mapping template

In this step, you define which properties the UI should expose for filtering and display for this IU.

Open:

`Information_Units/property_mappings/sources/generators/cif_demo_generator.json`

and update `properties` to include the fields you want exposed in the UI, for example:

```json
{
  "description": "Source-specific mappings for cif_demo_generator (generators).",
  "version": "2.0",
  "source_type": "generators",
  "source": "cif_demo_generator",
  "properties": {
    "chemical_formula_descriptive": {
      "name": "chemical_formula_descriptive",
      "retrievable": true
    },
    "elements": {
      "name": "elements",
      "retrievable": true
    }
  }
}
```

### Step 5: Add IU feature button/panel wiring

In this step, you add frontend wiring so the generator IU appears as a clickable panel in the Information Units UI.

```bash
python devtools/iu_features/manage_iu_features.py
```

This script is interactive. Choose:
- IU type: `generator`
- Action: `add`
- IU id: `cif_demo_generator`

### Step 6: Run and verify

In this step, you run EMOS end-to-end and verify that one generation request returns multiple CIF outputs/files.

1. Start backend: `python backend/app.py`
2. Open the UI by opening `index.html` in your browser.
3. In the Information Units section, open and run the new **CIF Demo Generator** IU.
4. Set `num_structures` to `10` and run.
5. Confirm the result includes 10 CIF strings (the same demo CIF repeated), and exports as 10 CIF files.

> **Optional Docker execution:** Developers are welcome to run the IU's `generate()` function in a Docker container instead of directly in the host environment. This can help avoid library or dependency conflicts, and it can keep model execution and its dependencies isolated for privacy-sensitive workflows. Make sure the container exposes the inputs and outputs required by the IU and follows the same generation response contract described above.

### Step 7: Run the contribution tests

Run the existing standards and IU contract tests before submitting the contribution:

```bash
pytest -q tests/standards tests/iu_contracts
```

The standards tests check the contribution's files, class and file names, metadata entries, inheritance, and required method signatures. The IU contract tests check that the documented input and output shapes use the required fields and value types.

## Remove the Generator IU (cleanup)

When you are done testing, remove the generator IU in this order:

1. Remove the IU feature implementation:

   ```bash
   python devtools/iu_features/manage_iu_features.py
   ```

   Choose:
   - IU type: `generator`
   - Action: `remove`
   - IU id: `cif_demo_generator`

   This removes the IU feature JS/wiring and also cleans the source mapping plus exclusive entries in `common_properties.json`.

2. Remove the IU entry for **CIF Demo Generator** from `devtools/source_data.json` under `information_units -> generators`.

3. Run contribution tool to remove the IU backend scaffold/factory wiring:

   ```bash
   python devtools/contribution_tool.py
   ```

   Confirm the detected removal changes when prompted.

This demo generator IU is intentionally simple and safe; once it works, use the same flow for real generation models.
