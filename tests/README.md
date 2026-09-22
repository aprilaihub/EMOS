# Tests

The tests are grouped by what they check.

## Standards

`standards/` checks whether a new Information Unit or Feature is set up
correctly in EMOS. It checks that each contribution:

- Has a non-empty `README.md` and an `__init__.py` file.
- Uses the expected class and file name.
- Has one matching entry in `devtools/metadata.json`.
- Inherits from the correct base class.
- Implements the required methods and input parameter names.

Run these checks before submitting a new contribution:

```bash
pytest -q tests/standards
```

## Contracts

`contracts/` checks the expected shape of data passed between Information
Units. It checks that:

- Database, generator, and predictor inputs contain the required fields.
- Database, generator, and predictor outputs contain the required fields.
- Values have the expected types, such as text, lists, and numbers.
- Missing or invalid fields are rejected.

Run these checks when changing shared input or output data:

```bash
pytest -q tests/contracts
```