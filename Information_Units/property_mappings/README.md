# Property mapping metadata

This folder contains the shared canonical property registry in [common_properties.json](./common_properties.json) and source-specific property mapping files under [sources/](./sources).

## Shared metadata fields

In addition to the existing `type`, `description`, `category`, and optional `unit` fields, canonical property entries may include the following standardized metadata fields:

- `dimensionality`: the structural form of the value. Controlled values should be used conservatively, for example `scalar`, `vector`, `matrix`, `tensor`, `array`, or `categorical`.
- `structure_identity`: identifies which structure representation the property refers to. Suggested values are `input_structure`, `relaxed_structure`, `unrelaxed_structure`, or the conservative fallback `associated_structure` when a more specific assignment is not explicitly supported.
- `provenance_type`: identifies how the value is obtained. Suggested values are `metadata`, `computed`, `predicted`, or `derived`.
- `calculation_method`: a concise method label taken directly from repository evidence, for example `AEL`, `AGL`, `SynthNN`, or `direct_from_source`.

## Assignment rules

These fields must be assigned conservatively and only from evidence already present in the repository.

### `dimensionality`

Assign from the existing `type` and explicit property semantics:

- `float`, `int`, or similar numeric scalar values should be annotated as `scalar`.
- `string` values that represent labels, classes, identifiers, or discrete states should be annotated as `categorical`.
- `array` values should only be annotated as `vector`, `matrix`, or `tensor` when the property name or description clearly supports that interpretation.
- If an `array` value is not explicitly identifiable as a vector, matrix, or tensor, annotate it conservatively as `array`.

### `structure_identity`

Assign only when the target structure is explicit in the property name or description:

- properties with suffixes such as `_orig` should be annotated as `unrelaxed_structure`.
- properties with suffixes such as `_relax` should be annotated as `relaxed_structure`.
- predictor input descriptors that clearly refer to the supplied structure, such as atomic composition or atomic-number arrays, should be annotated as `input_structure`.
- if the relevant structure cannot be determined unambiguously from the repository, annotate as `associated_structure`.

### `provenance_type`

Assign from explicit wording in the property definition or source context:

- labels, identifiers, prototype assignments, and descriptive fields should be annotated as `metadata`.
- properties described as calculated by a named workflow should be annotated as `computed`.
- properties whose descriptions say they are calculated or returned using a named workflow context, even when phrased as “for the AEL/AGL calculations,” should also be annotated as `computed`.
- predictor outputs from ML models should be annotated as `predicted`.
- values derived from other stored values without being direct source fields may be annotated as `derived`.

### `calculation_method`

Use only method names or source semantics that are directly supported by the repository:

- use named workflows such as `AEL` or `AGL` when they appear in the property description.
- use source-specific model names such as `SynthNN` when the property is defined as a model prediction from that source.
- use `direct_from_source` for metadata or values taken directly from the source without a named computational workflow.
- do not infer undocumented workflows or expand abbreviations beyond what is stated in the repository.

## Annotation policy

All four standardized metadata fields are assigned using a conservative evidence-based policy. Annotations are added only when supported by existing repository evidence such as the canonical property name, property description, or source context, and no field should encode assumptions that cannot be justified from those materials. When a property is clearly scalar, categorical, predicted, or tied to an explicitly named workflow such as AEL, AGL, or SynthNN, the corresponding metadata should be recorded directly. When a more specific interpretation is not explicit—especially for structure identity or higher-dimensional array semantics—the annotation should fall back to a neutral value such as `associated_structure` or `array` rather than overstate provenance or meaning. This policy is intended to improve auditability while keeping the schema accurate, reproducible, and defensible.
