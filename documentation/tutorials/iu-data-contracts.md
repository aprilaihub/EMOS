# Required IU Data Contracts

Every Information Unit (IU) must follow the input and output contract for its type. These contracts help Features use IUs consistently.

## Database IUs

Implement:

```text
retrieve(inputs: dict) -> dict
```

Required inputs:

- `target_compositions: str`
- `batch_size: int`

Required outputs:

- `source: str`
- `queries: dict`
- `cif_strings: list[str]`

Additional properies can be added as new keys to the `inputs` dictionary.

## Generator IUs

Implement:

```text
generate(inputs: dict) -> dict
```

Required input:

- `batch_size: int`

Required outputs:

- `status: str`
- `source: str`
- `queries: dict`
- `cif_strings: list[str]`

Additional properies can be added as new keys to the `inputs` dictionary.

## Predictor IUs

Implement:

```text
predict(input_data: list[str]) -> dict
```

The input is a list of CIF strings.

Required outputs:

- `source: str`
- `results: list[dict]`

Each result must contain:

- `index: int`
- `status: str`
- `properties: dict`
- `warnings: list[str]`
- `error: str | None`
- `cif_input: str`

A predictor may return additional properties within the `properties` dictionary.

## Before submitting

Check that:

- The IU accepts the required inputs.
- The IU returns every required output.
- Output types match this contract.
- Errors are reported in the expected fields.
- Tests cover a successful request and a basic error case.
