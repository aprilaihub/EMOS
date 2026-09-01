# Contributing to EMOS

Typical contributions to EMOS are either Information Units (IUs) or Features. Databases are IUs that retrieve candidate structures and metadata from external or curated sources. Generators are IUs that create new candidate materials, often guided by constraints or property targets. Predictors are IUs that estimate material properties from structure inputs. Materials Exploration features help users search, filter, and compare materials/design candidates across IUs. Electronics Application features focus on device-relevant analysis and property workflows for electronics-oriented use cases.

The EMOS devtools automate UI generation and backend integration. Define your component in `devtools/ui_data.json`, run the contribution tool, and it generates functional templates. Then implement your Python-based algorithms—no frontend knowledge required.

## Quick Start

All contributions follow this workflow:

1. **Edit** `devtools/ui_data.json` (ONE change only)
2. **Run**: `python devtools/contribution_tool.py`
3. **Implement** your code in the generated files

> ⚠️ **Important**: Make only ONE change at a time (add/remove one component per commit)

## Adding an Information Unit

Information units are the building blocks: **Databases**, **Generators**, and **Predictors**.

### Example: Adding a Database

**1. Add one new database entry in `devtools/ui_data.json`:**

In `information_units -> databases`, add exactly one new key/value line for your database display name and description.

Example (add only the new line shown):

```json
{
  "information_units": {
    "databases": {
      "Materials Project": "...",
      "New Database": "Description of your database and its capabilities"
    }
  }
}
```

**2. Run contribution tool:**

```bash
python devtools/contribution_tool.py
# Type 'yes' when prompted
```

This creates:
- `Information_Units/Databases/NewDatabase/` folder
- `NewDatabaseDatabase.py` with boilerplate code
- `README.md` and `__init__.py`
- Updates `DatabaseFactory.py` automatically

**3. Implement the `retrieve()` method (and property mapping):**

Navigate to the generated file and add your logic:

```python
def retrieve(self, inputs: dict) -> str:
    """Your implementation here"""
    search_query = inputs.get('search_criteria', '')
    
    if self.logger:
        self.logger.log(f"Searching: {search_query}", 'info')
    
    # Implement your database query logic
    results = your_database_api_call(search_query)
    return results
```

Add helper files in the same folder if needed.

Create/update your mapping in:

- `Information_Units/property_mappings/sources/databases/<database_id>.json`

This mapping drives IU input rendering and backend payload keys in the IU panel.

> **Note**: Generators and Predictors follow the same workflow. Implement `generate()` for generators and `predict()` for predictors instead of `retrieve()`, and ensure each implementation follows the input/output requirements in [Required I/O Contracts (Information Units)](#required-io-contracts-information-units).

**4. Add IU feature buttons (IU UI panels):**

Run:

```bash
python devtools/iu_features/manage_iu_features.py
```

Then select:
- IU type: `database`
- Action: `add`
- Your new database IU id

This wires the IU panel button in `index.html`, registers the IU panel module in `script.js`, and creates the IU feature JS panel implementation.

See [Adding IU Feature Buttons (IU UI Panels)](#adding-iu-feature-buttons-iu-ui-panels) for full details and non-interactive commands.

### Required I/O Contracts (Information Units)

- `retrieve(inputs: dict) -> dict`  
  Required input keys: `target_compositions` (`str`), `batch_size` (`int`)  
  Required output keys: `source` (`str`), `queries` (`dict`), `cif_strings` (`list[str]`)  
  Additional database-specific filter keys may be included in `inputs`.

- `generate(inputs: dict) -> dict`  
  Required input keys: `batch_size` (`int`)   
  Required output keys: `status` (`str`), `source` (`str`), `queries` (`dict`), `cif_strings` (`list[str]`)  
  Additional generator-specific keys may be included in `inputs`.

   `predict(input_data: list[str]) -> dict`  
    Required input: `input_data` as CIF strings (`list[str]`)  
    Required output keys: `source` (`str`), `results` (`list[dict]`)  
    Required keys per result item: `index` (`int`), `status` (`str`), `properties` (`dict`), `warnings` (`list[str]`), `error` (`str | None`), `cif_input` (`str`)  
    Additional predictor-specific options/properties may be included.

### Adding IU Feature Buttons (IU UI Panels)

After your IU implementation works (`retrieve`/`generate`/`predict`) and your property mapping is defined, add the IU feature button + panel wiring so users can open the IU-specific UI from the sidebar.

**Prerequisites (required):**
- Your IU is registered in its factory via `devtools/contribution_tool.py` output.
- Your IU method is implemented and tested: `retrieve()` for databases, `generate()` for generators, or `predict()` for predictors, following the contract in [Required I/O Contracts (Information Units)](#required-io-contracts-information-units).
- A mapping file exists in `Information_Units/property_mappings/sources/<iu_type>/<iu_id>.json`:
  - Databases: `Information_Units/property_mappings/sources/databases/`
  - Generators: `Information_Units/property_mappings/sources/generators/`
  - Predictors: `Information_Units/property_mappings/sources/predictors/`
- Mapping properties are correctly marked for UI behavior (`retrievable`, `generatable`, or `predictable`, plus optional `range_support`).

**Recommended workflow:**

1. **Run unified IU feature manager**

```bash
python devtools/iu_features/manage_iu_features.py
```

2. **Choose IU type** (`database`, `generator`, or `predictor`) when prompted.
3. **Choose action** (`add`) and select your IU from the list.

This updates:
- `index.html` (adds IU feature button row)
- `script.js` (adds IU feature module entry)
- `Features/IU_Features/<IUType>/<GeneratedClassName>.js` (creates IU panel implementation)

**Useful non-interactive commands:**

```bash
# List IU feature status for all IU types
python devtools/iu_features/manage_iu_features.py --list

# Add an IU feature directly
python devtools/iu_features/manage_iu_features.py --type generator --add <generator_id> --yes

# Remove an IU feature directly
python devtools/iu_features/manage_iu_features.py --type predictor --remove <predictor_id> --yes
```

> Tip: If the script warns that mapping is missing, add/fix `Information_Units/property_mappings/sources/<iu_type>/<iu_id>.json` first so the generated IU panel can render property-driven inputs correctly.

## Adding a Feature

Features are user-facing functionality that combines information units.

### Example: Adding a Feature

**1. Edit core metadata:**

```json
{
  "features": {
    "materials_exploration": {
      "Material Search": "...",
      "Your Feature": "Clear description of what this feature does"
    }
  }
}
```

**2. (Optional) Define custom inputs/outputs:**

Available input types are defined in `devtools/ui_data.json` under `ui_input_types`. See `feature_inputs_outputs` for examples.

```json
{
  "feature_inputs_outputs": {
    "Your Feature": {
      "inputs": [
        {
          "name": "elementSymbol",
          "display_name": "Element",
          "type": "text",
          "required": true,
          "placeholder": "e.g., Fe"
        }
      ],
      "outputs": [
        {
          "name": "results",
          "display_name": "Results",
          "type": "table"
        }
      ]
    }
  }
}
```

**3. Run contribution tool:**

```bash
python devtools/contribution_tool.py
```

This creates both Python and JavaScript files, updates factory and UI automatically.

**4. Implement feature logic:**

Edit `YourFeatureFeature.py`:

```python
def process_feature(self, inputs):
    """Main feature logic"""
    element = inputs.get('elementSymbol', '')
    
    # Your implementation
    results = your_analysis(element)
    
    return {
        'status': 'completed',
        'message': 'Analysis complete',
        'data': results
    }

def format_outputs(self, results):
    """Format for frontend"""
    return {
        'results': results.get('data', [])
    }
```

If the feature uses Information Units, add selectors inside that feature's input
UI and instantiate the selected factory entries explicitly. Do not rely on a
global Information Unit selection.

Edit `YourFeature.js` for custom UI behavior if needed.

## Removing Components

**1. Delete the entry from `ui_data.json`**

**2. Run contribution tool:**

```bash
python devtools/contribution_tool.py
# Type 'yes' to confirm removal
```

The tool automatically:
- Deletes the component folder
- Updates factory files
- Removes UI elements

## Key Rules

✅ **DO:**
- Make one change per commit
- Use clear, descriptive display names
- Write meaningful descriptions
- Document your implementation in the component's README
- Test before committing: `python backend/app.py`
- Keep helper files in the component folder

❌ **DON'T:**
- Add multiple components at once
- Edit `metadata.json` directly (always use `ui_data.json`)

## File Organization

Keep all related files within your component's folder. This keeps the codebase modular and makes your contribution self-contained:

```
Information_Units/Databases/YourDatabase/
├── README.md
├── __init__.py
├── YourDatabaseDatabase.py     # Main implementation
├── helper_module.py             # Your helper files
└── config/                      # Configuration files
```

## Testing

Before committing:

```bash
# 1. Start backend
python backend/app.py

# 2. Open browser to http://localhost:5001
# 3. Test your component
# 4. Verify outputs are correct
```

## Submitting Your Contribution

Once your implementation is tested and working:

1. **Commit your changes:**
   ```bash
   git add .
   git commit -m "Add [ComponentName] component"
   ```

2. **Raise a Pull Request** with:
   - Clear description of what the component does
   - Any dependencies or setup needed
   - Reference to related issues (if applicable)

We review PRs regularly and will provide feedback if needed.

## Need Help?

- Check existing implementations in `Information_Units/` and `Features/`
- Review `BaseFeature.py`, `BaseDatabase.py`, etc. for available methods
- Look at git history for similar changes

---

**Questions?** Open an issue with details about what you're trying to add.
