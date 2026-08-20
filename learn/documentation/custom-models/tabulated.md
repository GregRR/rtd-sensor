---
title: Tabulated RTD models
description: Preserve an authoritative resistance-temperature table with TabulatedRTDModel and monotonic piecewise-linear interpolation.
---

# Tabulated RTD models

Use `TabulatedRTDModel` when the authoritative RTD source is a
**resistance-temperature table** and you want to preserve those source points
rather than fit a new equation through them.

**Available since:** rtd-sensor 0.5.0.

## Example

```python
from rtd_sensor.models import TabulatedRTDModel, TabulatedRTDPoint

example = TabulatedRTDModel(
    points=(
        TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
        TabulatedRTDPoint(temperature_c=50.0, resistance_ohms=119.4),
        TabulatedRTDPoint(temperature_c=100.0, resistance_ohms=138.5),
    ),
    name="Illustrative table-backed RTD",
    table_source="Example only — not a real sensor table",
    source_precision="temperature 0.1 °C; resistance 0.1 Ω",
)

assert example.celsius_to_resistance(75.0) == 128.95
```

## Interpolation behavior

The model uses **piecewise-linear interpolation** between adjacent source rows.
That choice is deliberate:

- every supplied source point is retained exactly;
- a strictly monotonic table cannot overshoot between rows;
- no fitted curvature is invented; and
- each interval has an exact linear inverse.

## Source requirements

Points must be ordered with strictly increasing temperature and strictly
increasing resistance. A non-monotonic table cannot provide one unambiguous
resistance-to-temperature inverse and is rejected.

## No extrapolation

The first and last source rows define the complete model range. Temperatures or
resistances outside that table raise `RTDOutOfRangeError`.

## Sensitivity at a source point

Inside an interval, sensitivity is simply that interval's slope. At an interior
source point, the model uses the interval on the point's right; at the final
point it uses the last interval. This deterministic one-sided rule matters when
adjacent intervals have different slopes.

## Source precision

`source_precision` is optional provenance text. If a table was printed to
0.1 Ω, interpolation may numerically produce more digits, but those extra digits
do not create extra scientific precision.

## Portability status

Version 1 of the portable model-definition format does **not** yet serialize
`TabulatedRTDModel`. Keep the source table itself as the authoritative portable
record for now.

## Related features

- [Polynomial models](polynomial.md)
- [Piecewise polynomial models](piecewise-polynomial.md)
- [Choosing a model](../using/choosing-model.md)
