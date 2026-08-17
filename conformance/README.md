# RTD conformance artifacts

This directory contains the stable language-neutral conformance-v1 artifacts for
`rtd-sensor`.

The JSON Schemas under `v1/schemas/` define the structure of conformance-v1
catalogs and vector sets. The catalog files `v1/characteristics.json`,
`v1/models.json`, and `v1/model-fixtures.json`, together with the conversion
vector sets under `v1/vectors/`, are generated from authoritative built-in
definitions, explicit synthetic custom-model fixtures, and validated Python
runtime behavior. They are not maintained independently.

The successful built-in vector sets publish both `binary64_reference` and
`binary32_compatible` acceptance profiles. Successful characterized PT-385
reference-resistance fixtures also publish both profiles; other custom-fixture
families remain `binary64_reference` only and do not inherit the binary32
tolerance without their own empirical study. Built-in and custom status vector
sets exercise finite inputs outside declared model ranges, non-finite inputs,
and zero/negative resistance handling. The one-sided custom CVD fixtures also
verify that 0 °C remains outside their declared validity intervals. Invalid
custom-model semantics are represented by `expected_status: "invalid_model"`
in the fixture catalog. The built-in and characterized-R0 binary32 derivations
are documented under `consumers/c11/BINARY32.md` and
`consumers/c11/BINARY32_CHARACTERIZED_R0.md`.

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

## Release bundle and manifest

`v1/manifest.json` is generated with the catalogs and vectors and records the
package version, contract version/status, and SHA-256 plus byte size for every
machine-readable JSON file in the conformance-v1 tree except the manifest
itself. The manifest records `contract_status: "stable"`; conformance contract v1 has
completed its acceptance/schema-freeze review and is governed by the versioning
rules in `docs/CONFORMANCE.md`.

Verify the committed release tree without building an archive with:

```bash
uv run python -m rtd_sensor._conformance_release --check
```

Build the deterministic release ZIP and its SHA-256 sidecar with:

```bash
uv run python -m rtd_sensor._conformance_release --output-dir dist
```

The ZIP contains exactly `manifest.json` plus the files named by the manifest.
It uses stored ZIP entries with fixed metadata so repeated builds from the same
release tree are byte-identical. Production firmware still does not need a JSON
parser; the bundle is intended for vendoring, code generation, test harnesses,
and CI.

`v1/schemas/conformance-claim.schema.json` defines the initial machine-readable
shape for implementation claims. Claims are per capability and subject set, so
a consumer can claim built-in `binary32_compatible` conversion without implying
that arbitrary custom fixtures have the same acceptance profile. A validated
example is committed under `v1/examples/`.

## Independent C11 consumer

`conformance/consumers/c11/` contains a small independent implementation used
to prove that the published built-in and custom-fixture contract can be
reproduced without importing or linking against the Python package. The pytest
driver reads the committed JSON artifacts, supplies their model/characteristic
and fixture data to the C11 consumer, compiles it with an available C compiler,
and runs all published built-in and custom binary64 conversion/status cases. It
also requires the C consumer to reproduce every fixture's expected `ok` or
`invalid_model` construction status. The float consumer separately executes the
characterized-R0 binary32 fixture subset and a deterministic stress study over
1,320,843 characterized-R0 cases.

Run that verification directly with:

```bash
uv run --locked pytest tests/test_c_conformance_consumer.py -v
```

The C consumer intentionally uses a single bounded global-bisection inverse for
all characteristic kinds rather than reproducing Python's curve-specific
inversion algorithms. Passing the same behavioral vectors therefore tests the
contract rather than implementation identity.
