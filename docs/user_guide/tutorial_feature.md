# Toy Feature Tutorial

This page provides a minimal, end-to-end toy Feature example you can add to EMOS.

## Toy Example: Add a Demo Feature

Goal: add a tiny feature named **Toy Echo** that returns the input text in uppercase.

### Step 1: Add one feature entry in `devtools/ui_data.json`

Under `features -> materials_exploration`, add one new key:

```json
"Toy Echo": "Tutorial feature that echoes user text in uppercase"
```

### Step 2 (optional): Define simple feature I/O

Under `feature_inputs_outputs`, add:

```json
"Toy Echo": {
  "inputs": [
    {
      "name": "message",
      "display_name": "Message",
      "type": "text",
      "required": true,
      "placeholder": "type something"
    }
  ],
  "outputs": [
    {
      "name": "result",
      "display_name": "Result",
      "type": "text"
    }
  ]
}
```

### Step 3: Generate scaffolding

```bash
python devtools/contribution_tool.py
```

Expected generated files include:

- `Features/Materials_Exploration/ToyEcho/ToyEchoFeature.py`
- `Features/Materials_Exploration/ToyEcho/ToyEcho.js`

### Step 4: Implement the generated feature class

Open `Features/Materials_Exploration/ToyEcho/ToyEchoFeature.py` and keep these methods minimal:

```python
def extract_inputs(self, input_data):
    return {
        'message': input_data.get('message', '')
    }

def process_feature(self, inputs):
    message = str(inputs.get('message', ''))
    return {
        'status': 'completed',
        'original': message,
        'result': message.upper(),
    }

def format_outputs(self, results):
    return {
        'status': results.get('status', 'unknown'),
        'original': results.get('original', ''),
        'result': results.get('result', ''),
    }
```

### Step 5: Run and verify

1. Start backend: `python backend/app.py`
2. Open EMOS, launch **Toy Echo**, and enter text.
3. Confirm output `result` is uppercase.

This toy Feature gives a complete contribution path (metadata -> generated files -> implementation -> UI run) with minimal logic.
