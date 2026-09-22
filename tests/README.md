# Tests

The tests are grouped by what they check.

## Standards

`standards/` checks whether a new Information Unit or Feature is set up
correctly in EMOS. It checks that each contribution:

- Has a non-empty `README.md` and an `__init__.py` file.
- Uses the expected class and file name.
- Has one matching entry in `devtools/metadata.json`.
- Has one matching entry in `devtools/source_data.json`.
- Inherits from the correct base class.
- Implements the required methods and input parameter names.

Run these checks before submitting a new contribution:

```bash
pytest -q tests/standards
```

## IU Contracts

`iu_contracts/` checks the exact input and output shapes used by Information
Units. It checks that:

- Database inputs contain a string `target_compositions` and integer `batch_size`.
- Database outputs contain string `source`, dictionary `queries`, and a list of string `cif_strings`.
- Generator inputs contain integer `batch_size`.
- Generator outputs contain string `status` and `source`, dictionary `queries`, and a list of string `cif_strings`.
- Predictor inputs are lists of strings.
- Predictor outputs contain string `source` and a `results` list. Each result contains integer `index`, string `status`, dictionary `properties`, a list of string `warnings`, optional string `error` (or `None`), and string `cif_input`.
- Invalid examples, such as missing fields or incorrect value types, are rejected.

Run these checks when changing shared input or output data:

```bash
pytest -q tests/iu_contracts
```