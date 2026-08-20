---
title: IEC 60751 tolerance classes
description: Calculate IEC 60751:2022 platinum thermometer and bare-resistor tolerance limits with rtd-sensor and understand what those limits mean.
---

# IEC 60751 tolerance classes

IEC 60751 defines temperature-dependent tolerance classes for platinum RTDs.
`rtd_sensor.tolerance` calculates the numerical **maximum permitted temperature
deviation** for those classes and enforces the class validity ranges.

Tolerance is a conformity limit, not automatically a standard uncertainty.

## Complete thermometer

For an assembled thermometer or probe:

```python
from rtd_sensor import tolerance

maximum_error_c = tolerance.thermometer_tolerance_c(
    100.0,
    tolerance_class="A",
    construction="wire_wound",
)

print(maximum_error_c)  # 0.35
```

A result of `0.35` means a nominal tolerance band of **±0.35 °C** at 100 °C. It
does not predict that the sensor will actually be off by 0.35 °C.

Thermometer classes are `AA`, `A`, `B`, and `C`. Construction is either
`"wire_wound"` or `"film"`, because the standard validity range depends on
construction.

## Bare platinum resistor

For a bare sensing resistor:

```python
maximum_error_c = tolerance.platinum_resistor_tolerance_c(
    100.0,
    tolerance_class="F0.15",
)
```

The ASCII class designation includes construction: `W` for wire-wound and `F`
for film. Supported designations are `W0.1`, `W0.15`, `W0.3`, `W0.6`, `F0.1`,
`F0.15`, `F0.3`, and `F0.6`.

## Range enforcement

The same formula cannot be extended indefinitely and still carry the same IEC
class designation. If the requested temperature is outside that class's
standard validity range, the function raises `ValueError`.

## What this function does not prove

Calculating a class limit does not establish that a physical device satisfies
all IEC 60751 construction, qualification, and testing requirements. The API
provides the numerical tolerance rule and its valid range.

## Tolerance versus uncertainty

If you choose to use a tolerance bound as an input to an uncertainty budget,
you must also choose and justify a probability model. For example, treating a
bound as rectangular is a **user modeling assumption**, not something IEC 60751
states automatically.

See [Uncertainty fundamentals](uncertainty.md).
