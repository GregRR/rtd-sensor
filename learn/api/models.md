---
title: models API
description: Quick API reference for rtd_sensor.models structural RTDModel and configurable RTD model classes.
---

# `rtd_sensor.models`

Some configurable model classes predate the 0.4.0 rename from `pt100-core` /
`rtd` to `rtd-sensor` / `rtd_sensor`. Those entries show both dates.

## `RTDModel`

**Introduced in:** rtd-sensor 0.5.0

Structural protocol requiring:

```text
celsius_to_resistance(temperature_c) -> float
resistance_to_celsius(resistance_ohms) -> float
resistance_sensitivity_ohms_per_celsius(temperature_c) -> float
temperature_sensitivity_celsius_per_ohm(temperature_c) -> float
```

## `IEC60751RTDModel`

**Introduced in:** project release 0.3.0 (`pt100-core`); available as
`rtd_sensor.models.IEC60751RTDModel` since rtd-sensor 0.4.0.

```python
IEC60751RTDModel(
    r0_ohms: float,
    name: str = "IEC 60751 RTD",
    minimum_temperature_c: float = -200.0,
    maximum_temperature_c: float = 850.0,
)
```

## `CallendarVanDusenRTDModel`

**Introduced in:** project release 0.3.0 (`pt100-core`); available as
`rtd_sensor.models.CallendarVanDusenRTDModel` since rtd-sensor 0.4.0.

```python
CallendarVanDusenRTDModel(
    *,
    r0_ohms: float,
    a: float,
    b: float,
    minimum_temperature_c: float,
    maximum_temperature_c: float,
    c: float | None = None,
    name: str = "Custom Callendar-Van Dusen RTD",
    coefficient_source: str | None = None,
)
```

## `PolynomialRTDModel`

**Introduced in:** rtd-sensor 0.4.0

```python
PolynomialRTDModel(
    *,
    reference_resistance_ohms: float,
    coefficients: Sequence[float],
    minimum_temperature_c: float,
    maximum_temperature_c: float,
    reference_temperature_c: float = 0.0,
    name: str = "Polynomial RTD",
    coefficient_source: str | None = None,
)
```

## `PiecewisePolynomialSegment`

**Introduced in:** rtd-sensor 0.4.0

```python
PiecewisePolynomialSegment(
    *,
    minimum_temperature_c: float,
    maximum_temperature_c: float,
    coefficients: Sequence[float],
    temperature_origin_c: float = 0.0,
)
```

## `PiecewisePolynomialRTDModel`

**Introduced in:** rtd-sensor 0.4.0

```python
PiecewisePolynomialRTDModel(
    *,
    reference_resistance_ohms: float,
    segments: Sequence[PiecewisePolynomialSegment],
    reference_temperature_c: float = 0.0,
    name: str = "Piecewise polynomial RTD",
    coefficient_source: str | None = None,
    maximum_continuity_adjustment_ratio: float = 0.0,
)
```

## `TabulatedRTDPoint`

**Introduced in:** rtd-sensor 0.5.0

```python
TabulatedRTDPoint(*, temperature_c: float, resistance_ohms: float)
```

## `TabulatedRTDModel`

**Introduced in:** rtd-sensor 0.5.0

```python
TabulatedRTDModel(
    *,
    points: Sequence[TabulatedRTDPoint],
    name: str = "Tabulated RTD",
    table_source: str | None = None,
    source_precision: str | None = None,
)
```

All concrete model classes provide the four `RTDModel` numerical methods.

See [Custom & calibrated models](../documentation/custom-models/index.md).
