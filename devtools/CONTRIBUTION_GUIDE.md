# EMOS Contribution Guide

**Quick guide for adding Information Units (Databases, Generators, Predictors)**

## 🚀 Quick Start

### Add a New Information Unit

**1. Edit the source metadata**
```bash
nano devtools/core_metadata.json
```

Add your component under the appropriate section:
```json
{
  "information_units": {
    "databases": {
      "Your Display Name": "Brief description of your database"
    }
  }
}
```

**2. Generate full metadata**
```bash
cd metadata
python3 core_utilities.py
```

**3. Run contribution tool**
```bash
python3 contribution_tool.py
```

The tool will:
- ✅ Create folder structure
- ✅ Generate template files (README.md, __init__.py, class file)
- ✅ Update Factory.py
- ✅ Sync UI checkboxes

**Done!** Your component is now integrated.

---

## 📝 Naming Convention

Everything is auto-derived from your display name:

| Display Name | Folder | ID | Class | File |
|--------------|--------|----|----|------|
| `Material Search` | `MaterialSearch` | `material_search` | `MaterialSearchFeature` | `MaterialSearchFeature.py` |
| `Esen` | `Esen` | `esen` | `EsenPredictor` | `EsenPredictor.py` |
| `MaterialsProject` | `Materialsproject` | `materialsproject` | `MaterialsprojectDatabase` | `MaterialsprojectDatabase.py` |

**Just provide the display name - everything else is automatic!**

---

## 🎯 Component Types

### Databases
- **Base Class**: `BaseDatabase`
- **Location**: `Information_Units/Databases/`
- **Method**: `retrieve(inputs: dict) -> str`

### Generators
- **Base Class**: `BaseGenerator`
- **Location**: `Information_Units/Generators/`
- **Method**: `generate(inputs: dict) -> str`

### Predictors
- **Base Class**: `BasePredictor`
- **Location**: `Information_Units/Predictors/`
- **Method**: `predict(inputs: dict) -> str`

---

## 🔧 Implement Your Logic

After scaffolding is created, edit your class file:

```python
def retrieve(self, inputs: dict) -> str:  # or generate/predict
    """
    Implement your logic here
    
    Args:
        inputs: Dictionary with required parameters
        
    Returns:
        Results as string or appropriate format
    """
    # Your implementation
    if self.logger:
        self.logger.log(f"Retrieved from {self.display_name}")
    
    return results
```

---

## ⚠️ Important Rules

1. **One change at a time** - Add or remove only ONE component per contribution
2. **Edit core_metadata.json** - Not metadata.json (it's auto-generated)
3. **Run in order** - core_utilities.py → contribution_tool.py
4. **Confirm prompts** - The tool asks for confirmation before making changes

---

## 🗑️ Remove an Information Unit

**1. Remove from core_metadata.json**
Delete the entry from the appropriate section

**2. Regenerate metadata**
```bash
python3 core_utilities.py
```

**3. Run contribution tool**
```bash
python3 contribution_tool.py
```

The tool will detect the removal and clean up all files.

---

## 📚 Full Documentation

For detailed metadata system documentation, see [README.md](README.md)
