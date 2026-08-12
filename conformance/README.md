# RTD conformance artifacts

This directory contains the draft language-neutral conformance artifacts for
`rtd-sensor`.

The JSON Schemas under `v1/schemas/` define the structure of conformance-v1
catalogs and vector sets. The catalog files `v1/characteristics.json` and
`v1/models.json` are generated from the authoritative built-in definitions used
by the Python runtime and are not maintained independently.

Regenerate the catalogs from the repository root with:

```bash
uv run python -m rtd_sensor._conformance_artifacts
```

Verify that committed catalogs are current without rewriting them with:

```bash
uv run python -m rtd_sensor._conformance_artifacts --check
```

Repository tests also validate the generated catalogs against their Draft
2020-12 schemas and require deterministic regeneration.
