---
title: tolerance API
description: Quick API reference for IEC 60751 thermometer and platinum-resistor tolerance calculations.
---

# `rtd_sensor.tolerance`

All public tolerance symbols were **introduced in project release 0.3.0** under
`pt100-core` / `rtd`. The current `rtd_sensor.tolerance` import path began with
rtd-sensor 0.4.0.

## Type aliases

**Introduced in:** project release 0.3.0 (`pt100-core`); current import path
since rtd-sensor 0.4.0.

```text
RTDConstruction = Literal["wire_wound", "film"]
ThermometerToleranceClass = Literal["AA", "A", "B", "C"]
PlatinumResistorToleranceClass = Literal[
    "W0.1", "W0.15", "W0.3", "W0.6",
    "F0.1", "F0.15", "F0.3", "F0.6",
]
```

## `thermometer_tolerance_c`

**Introduced in:** project release 0.3.0 (`pt100-core`); current import path
since rtd-sensor 0.4.0.

```python
thermometer_tolerance_c(
    temperature_c: float,
    *,
    tolerance_class: ThermometerToleranceClass,
    construction: RTDConstruction,
) -> float
```

Returns the positive magnitude of the maximum permitted temperature deviation
in °C. Raises `ValueError` outside the class/construction validity range or for
unsupported selections.

## `platinum_resistor_tolerance_c`

**Introduced in:** project release 0.3.0 (`pt100-core`); current import path
since rtd-sensor 0.4.0.

```python
platinum_resistor_tolerance_c(
    temperature_c: float,
    *,
    tolerance_class: PlatinumResistorToleranceClass,
) -> float
```

See [IEC 60751 tolerance classes](../documentation/measurement-uncertainty/tolerance.md).
