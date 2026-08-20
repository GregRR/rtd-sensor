---
title: Calibration fitting
description: Fit validated polynomial RTD models from calibration observations with auditable residuals, diagnostics, optional weighting, and explicit failure semantics.
---

# Calibration fitting

`rtd_sensor.fitting` fits a validated `PolynomialRTDModel` from measured
**temperature/resistance calibration observations** without requiring NumPy.

The API deliberately returns two things together:

1. the numerical model you can use for conversion; and
2. immutable evidence describing how that fit was obtained and how well it
   matched the observations.

**Available since:** rtd-sensor 0.6.0.

## Basic fit

```python
from rtd_sensor import fitting

observations = (
    fitting.CalibrationObservation(temperature_c=0.0, resistance_ohms=100.02),
    fitting.CalibrationObservation(temperature_c=50.0, resistance_ohms=119.43),
    fitting.CalibrationObservation(temperature_c=100.0, resistance_ohms=138.56),
)

fit = fitting.fit_polynomial(observations, degree=2)
model = fit.model

print(fit.evidence.rms_residual_ohms)
print(fit.evidence.max_absolute_residual_ohms)
```

## What the evidence contains

`PolynomialFitEvidence` retains information including:

- the original observations;
- per-point resistance residuals;
- polynomial degree;
- observation and fitted-parameter counts;
- residual degrees of freedom;
- fitting temperature range;
- unweighted RMS and maximum absolute residual;
- weighting method and normalized effective weights when used;
- weighted residual diagnostics when applicable;
- scaled-system conditioning diagnostic;
- solver and scaling information.

Residuals are **observed resistance minus fitted resistance**.

The reported RMS is descriptive `sqrt(sum(residual²) / observation_count)`. It
is not a degrees-of-freedom-adjusted uncertainty estimate. A nearly saturated
fit can therefore have very small residuals without proving good predictive
performance.

## Weighted fits with explicit weights

Every observation must use the same weighting convention:

```python
observations = (
    fitting.CalibrationObservation(0.0, 100.02, weight=1.0),
    fitting.CalibrationObservation(50.0, 119.43, weight=2.0),
    fitting.CalibrationObservation(100.0, 138.56, weight=1.0),
)

fit = fitting.fit_polynomial(observations, degree=2)
```

Weights must be positive. The package normalizes them so the largest effective
weight is 1.0; the overall scale of a relative least-squares weight set does not
change the fitted objective.

## Weighted fits from resistance uncertainty

Instead of relative weights, every observation may provide a positive
`standard_uncertainty_ohms`:

```python
observations = (
    fitting.CalibrationObservation(0.0, 100.02, standard_uncertainty_ohms=0.01),
    fitting.CalibrationObservation(50.0, 119.43, standard_uncertainty_ohms=0.02),
    fitting.CalibrationObservation(100.0, 138.56, standard_uncertainty_ohms=0.01),
)
```

These values are converted to normalized inverse-variance weights. Temperature
is treated as the independent variable; this fitter does not model uncertainty
in the temperature coordinate.

## Fit range

By default, the fitted model uses the observed calibration span. You may narrow
it inside that span:

```python
fit = fitting.fit_polynomial(
    observations,
    degree=2,
    minimum_temperature_c=10.0,
    maximum_temperature_c=90.0,
)
```

The fitting API does not silently extrapolate the deployable model beyond the
observed calibration span.

## When fitting fails

`RTDFitError` is raised rather than returning an unsafe model for conditions
such as rank-deficient observations, severe ill-conditioning, or a fitted curve
that becomes non-positive or non-monotonic over its declared range.

This is an important distinction: a least-squares solver producing coefficients
does not automatically mean those coefficients define a usable invertible RTD
model.

## Save the fitted model

A fitted polynomial can be passed directly to
[portable model definitions](portable-definitions.md) so another process or
language can reconstruct the numerical model without rerunning the fit.

## Related features

- [Polynomial models](polynomial.md)
- [Portable model definitions](portable-definitions.md)
- [Uncertainty fundamentals](../measurement-uncertainty/uncertainty.md)
