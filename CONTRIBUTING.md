# Contributing to EMOS

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

**1. Edit core metadata** (`devtools/ui_data.json`):

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

**4. Implement the `retrieve()` method:**

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

> **Note**: Generators and Predictors follow the same workflow. Implement `generate()` for generators and `predict()` for predictors instead of `retrieve()`.

### Required I/O Contracts (Information Units)

- `retrieve(inputs: dict) -> dict`  
  Required input keys: `target_compositions` (`str`), `batch_size` (`int`)  
  Required output keys: `source` (`str`), `queries` (`dict`), `cif_strings` (`list[str]`)  
  Additional database-specific filter keys may be included in `inputs`.

- `generate(inputs: dict) -> dict`  
  Required input keys: `batch_size` (`int`)   
  Required output keys: `status` (`str`), `source` (`str`), `queries` (`dict`), `cif_strings` (`list[str]`)  
  Additional generator-specific keys may be included in `inputs`.

- `predict(input_data: list[str]) -> dict`  
  Required input: `input_data` as CIF strings (`list[str]`)  
  Required output keys: `source` (`str`), `results` (`list[dict]`)  
  Required keys per result item: `index` (`int`), `status` (`str`), `properties` (`dict`), `warnings` (`list[str]`), `error` (`str | None`)  
  Additional predictor-specific options/properties may be included.

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
    
    # Use information units
    self._process_information_units(inputs)
    
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
