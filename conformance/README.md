# RTD conformance artifacts

This directory contains the draft language-neutral conformance artifacts for
`rtd-sensor`.

The JSON Schemas under `v1/schemas/` define the structure of conformance-v1
catalogs and vector sets. The catalog files `v1/characteristics.json` and
`v1/models.json`, together with the built-in conversion vector sets under
`v1/vectors/`, are generated from the authoritative built-in definitions and
validated Python runtime behavior. They are not maintained independently.

The successful-result vector sets publish both `binary64_reference` and
`binary32_compatible` acceptance profiles for built-in conversion anchors.
Separate status vector sets exercise finite inputs immediately outside each
built-in model range, non-finite inputs, and zero/negative resistance handling.
The binary32 profile derivation is documented under `consumers/c11/BINARY32.md`.

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
to prove that the published built-in contract can be reproduced without
importing or linking against the Python package. The pytest driver reads the
committed JSON artifacts, supplies their model/characteristic data to the C11
consumer, compiles it with an available C compiler, and runs all published
built-in conversion and status cases.

Run that verification directly with:

```bash
uv run --locked pytest tests/test_c_conformance_consumer.py -v
```

The C consumer intentionally uses a single bounded global-bisection inverse for
all characteristic kinds rather than reproducing Python's curve-specific
inversion algorithms. Passing the same behavioral vectors therefore tests the
contract rather than implementation identity.
