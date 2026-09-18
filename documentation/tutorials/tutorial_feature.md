# Feature Tutorial

This page provides a minimal, end-to-end demo Feature example you can add to EMOS.

## Demo Example: Add a Feature

Goal: add a small feature named **Demo Echo** that repeats a selected message, returns it in uppercase, and provides a downloadable JSON report.

### Step 1: Add one feature entry in `devtools/source_data.json`

Under `features -> materials_exploration`, add one new key:

```json
"Demo Echo": "Demo feature that echoes user text in uppercase and provides a downloadable JSON report"
```

### Step 2 (optional): Define simple feature I/O

Under `feature_inputs_outputs`, add:

```json
"Demo Echo": {
  "inputs": [
    {
      "name": "message",
      "display_name": "Message",
      "type": "select",
      "required": true,
      "options": [
        {"value": "hello", "text": "Hello"},
        {"value": "welcome", "text": "Welcome"}
      ],
      "default": "hello"
    },
    {
      "name": "repeat_count",
      "display_name": "Repeat Count",
      "type": "number",
      "required": true,
      "min": 1,
      "max": 10,
      "default": 1
    }
  ],
  "outputs": [
    {
      "name": "result",
      "display_name": "Result",
      "type": "text"
    },
    {
      "name": "report",
      "display_name": "Report",
      "type": "link"
    }
  ]
}
```

### Step 3: Generate scaffolding

```bash
python devtools/contribution_tool.py
```

Expected generated files include:

- `Features/Materials_Exploration/DemoEcho/DemoEchoFeature.py`
- `Features/Materials_Exploration/DemoEcho/DemoEcho.js`

### Step 4: Implement the generated feature class

Open `Features/Materials_Exploration/DemoEcho/DemoEchoFeature.py` and keep these methods minimal:

```python
def extract_inputs(self, input_data):
    return {
      'message': input_data.get('message', ''),
      'repeat_count': input_data.get('repeat_count', 1),
    }

def process_feature(self, inputs):
    message = str(inputs.get('message', ''))
    repeat_count = int(inputs.get('repeat_count', 1))
    repeated_message = message * max(repeat_count, 1)
    return {
        'status': 'completed',
      'result': repeated_message.upper(),
      'report': {
        'message': message,
        'repeat_count': repeat_count,
        'result': repeated_message.upper(),
      },
    }

def format_outputs(self, results):
    return {
        'status': results.get('status', 'unknown'),
        'result': results.get('result', ''),
        'report': results.get('report', ''),
    }
```

### Step 5: Run and verify

1. Start backend: `python backend/app.py`
2. Open EMOS, launch **Demo Echo**, select a message, and set a repeat count.
3. Confirm output `result` is uppercase and `report` appears as a **Download JSON** link.

> **Optional Docker execution and updates:** Developers are welcome to implement and run the feature in a Docker container if they prefer to isolate dependencies or keep execution private. The feature input and output definitions in `devtools/source_data.json` do not need to be updated when only the implementation changes; update them when the feature's interface changes.

## Remove the Demo Feature (cleanup)

When you are done testing, remove the demo feature in this order:

1. Remove the feature entry for **Demo Echo** from `devtools/source_data.json` under `features -> materials_exploration`.
2. Remove the **Demo Echo** input and output definition from `feature_inputs_outputs` in `devtools/source_data.json`.
3. Run the contribution tool to remove the generated feature scaffolding and UI wiring:

  ```bash
  python devtools/contribution_tool.py
  ```

  Confirm the detected removal changes when prompted.

4. Confirm that the generated files have been removed:
  - `Features/Materials_Exploration/DemoEcho/DemoEchoFeature.py`
  - `Features/Materials_Exploration/DemoEcho/DemoEcho.js`

This demo Feature gives a complete contribution path (metadata -> generated files -> implementation -> UI run) with minimal logic.
