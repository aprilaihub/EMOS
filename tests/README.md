# Testing fixtures

This folder contains the contribution standards test and shared CIF fixtures.

## IU data-contract test

`test_iu_data_contracts.py` checks the documented IU input and output schemas
without importing or running external services or models. It verifies required
keys and value types for database, generator, and predictor payloads, including
predictor result fields, and checks representative invalid payloads are rejected.

Run it separately with:

```bash
pytest -q tests/test_iu_data_contracts.py
```

## Contribution standards test

`test_contribution_standards.py` uses static source inspection and checks every
registered contribution for:

- A non-empty `README.md` and an `__init__.py` file.
- The expected class and file name.
- Exactly one matching entry in `devtools/metadata.json`.

Information Units are checked by type:

- Databases subclass `BaseDatabase` and implement `retrieve(inputs)`.
- Generators subclass `BaseGenerator` and implement `generate(inputs)`.
- Predictors subclass `BasePredictor` and implement `predict(input_data)`.

Features must subclass `BaseFeature` and implement `info`, `extract_inputs`, `process_feature`, and `format_outputs`. The CIF files support separate predictor and service tests.

Run it separately with:

```bash
pytest -q tests/test_contribution_standards.py
```