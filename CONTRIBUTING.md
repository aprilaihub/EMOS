# Contributing to EMOS

The EMOS devtools automate UI generation and backend integration, allowing developers to contribute new features and information units using only Python. You define your component in metadata, implement your algorithm, and the tooling handles the rest—no frontend knowledge required.

## Quick Start

EMOS uses a metadata-driven architecture. All contributions follow this workflow:

1. **Edit** `devtools/ui_data.json` (ONE change only)
2. **Generate** full metadata: `python devtools/make_metadata.py`
3. **Create templates**: `python devtools/contribution_tool.py`
4. **Implement** your code in the generated files

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

**2. Generate metadata:**

```bash
python devtools/make_metadata.py
```

**3. Run contribution tool:**

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

**3. Generate and create templates:**

```bash
python devtools/make_metadata.py
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

**2. Regenerate and run tool:**

```bash
python devtools/make_metadata.py
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
- Skip running `make_metadata.py` after editing UI data

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

## Need Help?

- Check existing implementations in `Information_Units/` and `Features/`
- Review `BaseFeature.py`, `BaseDatabase.py`, etc. for available methods
- Look at git history for similar changes

---

**Questions?** Open an issue with details about what you're trying to add.
