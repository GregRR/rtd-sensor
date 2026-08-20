---
title: portable API
description: Quick API reference for rtd_sensor.portable model definition serialization and reconstruction.
---

# `rtd_sensor.portable`

The portable-model API was **introduced in rtd-sensor 0.6.0**.

## `PortableRTDModel`

**Introduced in:** rtd-sensor 0.6.0

A public type alias covering the model families supported by portable format
version 1: `IEC60751RTDModel`, `CallendarVanDusenRTDModel`,
`PolynomialRTDModel`, and `PiecewisePolynomialRTDModel`.

## `model_to_portable_definition`

**Introduced in:** rtd-sensor 0.6.0

```python
model_to_portable_definition(
    model: PortableRTDModel,
    *,
    metadata: Mapping[str, object] | None = None,
) -> dict[str, object]
```

Supports `IEC60751RTDModel`, `CallendarVanDusenRTDModel`,
`PolynomialRTDModel`, and `PiecewisePolynomialRTDModel` in format version 1.

## `model_from_portable_definition`

**Introduced in:** rtd-sensor 0.6.0

```python
model_from_portable_definition(
    artifact: Mapping[str, object],
) -> PortableModelDefinition
```

Validates and reconstructs a supported model. Invalid or unsupported artifacts
raise `InvalidPortableModelDefinitionError`.

## `PortableModelDefinition`

**Introduced in:** rtd-sensor 0.6.0

```python
PortableModelDefinition(
    model: PortableRTDModel,
    metadata: dict[str, object],
)
```

See [Portable model definitions](../documentation/custom-models/portable-definitions.md).
