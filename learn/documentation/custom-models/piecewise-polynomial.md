---
title: Piecewise polynomial RTD models
description: Represent RTD characteristics published as separate polynomial intervals with PiecewisePolynomialRTDModel and explicit continuity handling.
---

# Piecewise polynomial RTD models

Some RTD sources publish one polynomial for each temperature interval rather
than one equation for the complete range. `PiecewisePolynomialRTDModel`
preserves that structure.

Each `PiecewisePolynomialSegment` stores a complete normalized polynomial:

```text
R(T) / Rref = c0 + c1*x + c2*x² + ... + cn*xⁿ
x = T - temperature_origin_c
```

Unlike `PolynomialRTDModel`, the segment's coefficient tuple **includes its
constant term** `c0`.

## Example

```python
from rtd_sensor.models import (
    PiecewisePolynomialRTDModel,
    PiecewisePolynomialSegment,
)

example = PiecewisePolynomialRTDModel(
    reference_resistance_ohms=100.0,
    segments=(
        PiecewisePolynomialSegment(
            minimum_temperature_c=-10.0,
            maximum_temperature_c=0.0,
            coefficients=(1.0, 0.01),
        ),
        PiecewisePolynomialSegment(
            minimum_temperature_c=0.0,
            maximum_temperature_c=10.0,
            coefficients=(1.0, 0.02),
        ),
    ),
    coefficient_source="Example only — not a real sensor characteristic",
)
```

## Required segment behavior

Segments must form a contiguous characteristic and must remain positive in
resistance and strictly increasing. The complete model then provides one
bounded inverse across the full range.

At an interior boundary, the temperature belongs to the segment on its right.
Sensitivity at that boundary therefore also uses the right-hand segment slope.

## Small published join mismatches

Printed source coefficients may be independently rounded, causing adjacent
segments to miss exact continuity by a tiny amount. The default is strict: the
model does not silently hide such a mismatch.

If the source justifies it, you can explicitly authorize a maximum normalized
constant-term correction:

```python
model = PiecewisePolynomialRTDModel(
    reference_resistance_ohms=120.0,
    segments=segments,
    maximum_continuity_adjustment_ratio=1e-5,
)
```

Only bounded additive corrections to segment constants are allowed. Derivatives
and higher-order shape are unchanged, and applied adjustments remain exposed on
the model for auditability.

This mechanism is intended for source-rounding effects, not for making
incompatible curves appear continuous.

## Real built-in example

The [Ni120 6720](../built-in-rtds/ni120.md) built-in uses the generic piecewise
machinery because its authoritative characteristic is published as multiple
cubic intervals.

## Related features

- [Polynomial models](polynomial.md)
- [Tabulated models](tabulated.md)
- [Portable model definitions](portable-definitions.md)
