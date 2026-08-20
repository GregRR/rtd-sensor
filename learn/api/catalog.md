---
title: catalog API
description: Quick API reference for built-in rtd-sensor model discovery and immutable metadata.
---

# `rtd_sensor.catalog`

The public catalog API was **introduced in rtd-sensor 0.5.0**.

## Functions

### `supported_models`

**Introduced in:** rtd-sensor 0.5.0

```python
supported_models() -> tuple[str, ...]
```

Returns canonical IDs for all verified built-ins.

### `get_model`

**Introduced in:** rtd-sensor 0.5.0

```python
get_model(model_id: str) -> RTDModel
```

Returns the cached built-in model adapter. Raises `TypeError` for a non-string
ID and `UnknownRTDModelError` for an unsupported ID.

### `model_info`

**Introduced in:** rtd-sensor 0.5.0

```python
model_info(model_id: str) -> BuiltinRTDModelInfo
```

Returns immutable metadata for the built-in ID.

## `RTDSourceReference`

**Introduced in:** rtd-sensor 0.5.0

```python
RTDSourceReference(*, citation: str, url: str | None = None)
```

## `BuiltinRTDModelInfo`

**Introduced in:** rtd-sensor 0.5.0

```python
BuiltinRTDModelInfo(
    *,
    model_id: str,
    display_name: str,
    characteristic_id: str,
    characteristic_display_name: str,
    material: Literal["platinum", "nickel"],
    curve_kind: Literal[
        "callendar_van_dusen",
        "polynomial",
        "piecewise_polynomial",
    ],
    reference_resistance_ohms: float,
    reference_temperature_c: float,
    minimum_temperature_c: float,
    maximum_temperature_c: float,
    source_references: tuple[RTDSourceReference, ...],
)
```

See [Discovering built-in models](../documentation/using/catalog.md).
