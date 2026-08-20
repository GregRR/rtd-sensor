---
title: Polynomial RTD models
description: Represent one global RTD resistance-temperature polynomial with PolynomialRTDModel, validation, inversion, sensitivity, and provenance.
---

# Polynomial RTD models

Use `PolynomialRTDModel` when the authoritative characteristic is expressed as
**one global polynomial** over a declared temperature range.

For

```text
x = T - reference_temperature_c
```

the model evaluates:

```text
R(T) = Rref × (1 + c1*x + c2*x² + ... + cn*xⁿ)
```

The constant term is implicitly `1`, because `reference_resistance_ohms` is by
definition the resistance at the reference temperature.

## Simple example

```python
from rtd_sensor.models import PolynomialRTDModel

example = PolynomialRTDModel(
    reference_resistance_ohms=10.0,
    reference_temperature_c=25.0,
    coefficients=(0.01,),
    minimum_temperature_c=-20.0,
    maximum_temperature_c=80.0,
    name="Illustrative linear RTD",
    coefficient_source="Example only — not a real sensor characteristic",
)

assert example.celsius_to_resistance(25.0) == 10.0
```

Here `coefficients=(0.01,)` means a first-order normalized coefficient `c1` of
0.01 per degree relative to the 25 °C reference point.

## Higher-order example

```python
model = PolynomialRTDModel(
    reference_resistance_ohms=100.0,
    coefficients=(3.9e-3, -5.8e-7),
    minimum_temperature_c=0.0,
    maximum_temperature_c=300.0,
    coefficient_source="Illustrative polynomial source",
)
```

The public API supports polynomial degrees up to the package's validated limit.
High-order fitting is numerically fragile, so a larger degree is not
automatically a better physical model.

## How inverse conversion works

`rtd-sensor` does **not** construct a separate approximate inverse polynomial.
It validates the forward characteristic for strict monotonicity and then uses
bounded bisection to solve the inverse on the validated range.

This keeps forward and inverse behavior tied to the same characteristic.

## Model validation

The polynomial is analytically differentiated. Construction fails if the curve
becomes non-finite, non-positive in resistance, or non-increasing anywhere in
the declared range.

## Don't force the wrong source into a global polynomial

If a manufacturer publishes several interval-specific polynomials, use
[PiecewisePolynomialRTDModel](piecewise-polynomial.md). If the authoritative
source is a table, use [TabulatedRTDModel](tabulated.md).

## Related features

- [Calibration fitting](calibration-fitting.md)
- [Piecewise polynomial models](piecewise-polynomial.md)
- [Tabulated models](tabulated.md)
- [Portable model definitions](portable-definitions.md)
