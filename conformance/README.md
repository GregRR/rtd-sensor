# RTD conformance artifacts

This directory contains the draft language-neutral conformance artifacts for
`rtd-sensor`.

The JSON Schemas under `v1/schemas/` define the structure of conformance-v1
catalogs and vector sets. The catalog files `v1/characteristics.json` and
`v1/models.json`, together with the built-in conversion vector sets under
`v1/vectors/`, are generated from the authoritative built-in definitions and
validated Python runtime behavior. They are not maintained independently.

The successful-result vector sets publish the `binary64_reference` acceptance
profile for built-in conversion anchors. Separate status vector sets exercise
finite inputs immediately outside each built-in model range, non-finite inputs,
and zero/negative resistance handling. The `binary32_compatible` profile remains
a later conformance layer.

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
