---
title: Uncertainty fundamentals
description: Use rtd-sensor uncertainty primitives for bounded specifications, independent standard uncertainties, expanded uncertainty, and explicit metrology assumptions.
---

# Uncertainty fundamentals

`rtd_sensor.uncertainty` provides numerical building blocks for measurement
uncertainty. It does **not** decide which physical effects belong in your
measurement model or which probability distribution is justified.

That separation is important: software can perform the arithmetic, but the
measurement evidence must justify the assumptions.

## Convert a symmetric bound to standard uncertainty

For a bound of ±`a`, you can explicitly choose a rectangular or triangular
model:

```python
from rtd_sensor import uncertainty

u_rectangular = uncertainty.standard_uncertainty_from_bound(
    0.35,
    distribution="rectangular",
)

u_triangular = uncertainty.standard_uncertainty_from_bound(
    0.35,
    distribution="triangular",
)
```

The numerical formulas are:

```text
rectangular: a / sqrt(3)
triangular:  a / sqrt(6)
```

The choice of distribution is yours to justify.

## Convert expanded uncertainty back to standard uncertainty

If an uncertainty source explicitly provides an expanded uncertainty and
coverage factor:

```python
u_standard = uncertainty.standard_uncertainty_from_expanded(
    0.20,
    coverage_factor=2.0,
)
```

## Combine independent standard uncertainties

```python
combined_u = uncertainty.combine_independent_standard_uncertainties(
    0.04,
    0.07,
    0.02,
)
```

This uses root-sum-square and assumes the supplied components are independent
or uncorrelated for the purpose of this calculation.

## Expanded uncertainty

```python
expanded_u = uncertainty.expanded_uncertainty(
    combined_u,
    coverage_factor=2.0,
)
```

The function does not assign a confidence level to `k=2`. A probability
interpretation requires justification from the complete uncertainty analysis.

## Type A and Type B labels

`TemperatureUncertaintyComponent` can retain an optional `evaluation_method` of
`"A"` or `"B"`, plus source and note text. Those are provenance fields. They do
not change the arithmetic and do not transform an invalid uncertainty quantity
into a valid one.

## Current limits

The simple combination helpers do not yet model covariance between correlated
components, coefficient covariance, effective degrees of freedom, or Monte
Carlo propagation.

For RTD-specific resistance propagation, continue to
[Resistance uncertainty propagation](resistance-propagation.md).
