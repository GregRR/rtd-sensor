# RTD conformance artifacts

This directory contains the draft language-neutral conformance artifacts for
`rtd-sensor`.

The JSON Schemas under `v1/schemas/` define the structure of conformance-v1
catalogs and vector sets. The catalog files `v1/characteristics.json`,
`v1/models.json`, and `v1/model-fixtures.json`, together with the conversion
vector sets under `v1/vectors/`, are generated from authoritative built-in
definitions, explicit synthetic custom-model fixtures, and validated Python
runtime behavior. They are not maintained independently.

The successful built-in vector sets publish both `binary64_reference` and
`binary32_compatible` acceptance profiles. Successful custom-fixture vectors
publish `binary64_reference` only; built-in binary32 tolerances are not assumed
to apply to arbitrary custom coefficients. Built-in and custom status vector
sets exercise finite inputs outside declared model ranges, non-finite inputs,
and zero/negative resistance handling. The one-sided custom CVD fixtures also
verify that 0 °C remains outside their declared validity intervals. Invalid
custom-model semantics are represented by `expected_status: "invalid_model"`
in the fixture catalog. The binary32 profile derivation is documented under
`consumers/c11/BINARY32.md`.

Regenerate all generated artifacts from the repository root with:

```bash
uv run python -m rtd_sensor._conformance_artifacts
```

Verify that committed artifacts are current without rewriting them with:

```bash
uv run python -m rtd_sensor._conformance_artifacts --check
```

Repository tests also validate the generated artifacts against their Draft
2020-12 schemas, exercise cross-file/runtime integrity, and require deterministic
regeneration.

## Independent C11 consumer

`conformance/consumers/c11/` contains a small independent implementation used
to prove that the published built-in and custom-fixture contract can be
reproduced without importing or linking against the Python package. The pytest
driver reads the committed JSON artifacts, supplies their model/characteristic
and fixture data to the C11 consumer, compiles it with an available C compiler,
and runs all published built-in and custom binary64 conversion/status cases. It
also requires the C consumer to reproduce every fixture's expected `ok` or
`invalid_model` construction status.

Run that verification directly with:

```bash
uv run --locked pytest tests/test_c_conformance_consumer.py -v
```

The C consumer intentionally uses a single bounded global-bisection inverse for
all characteristic kinds rather than reproducing Python's curve-specific
inversion algorithms. Passing the same behavioral vectors therefore tests the
contract rather than implementation identity.
