---
title: Calibration fitting
description: Fit characterized IEC 60751 R0 values or validated polynomial RTD models from calibration observations with auditable residuals, diagnostics, and optional weighting.
---

# Calibration fitting

`rtd_sensor.fitting` fits RTD models from measured **temperature/resistance
calibration observations** without requiring NumPy. The 0.6.0 API introduced
polynomial fitting; 0.7.0 adds fitting of a characterized IEC 60751 PT-385
reference resistance while keeping the standard characteristic fixed.

The API deliberately returns two things together:

1. the numerical model you can use for conversion; and
2. immutable evidence describing how that fit was obtained and how well it
   matched the observations.

**Available since:** rtd-sensor 0.6.0.

## Fit a characterized IEC 60751 `R0`

**Planned for:** rtd-sensor 0.7.0.

When the probe is assumed to retain the standard IEC 60751 PT-385 curve and you
only want to estimate its individual reference resistance, fit `R0` directly:

```python
from rtd_sensor import fitting

observations = (
    fitting.CalibrationObservation(0.0, 100.037),
    fitting.CalibrationObservation(100.0, 138.556),
)

fit = fitting.fit_iec60751_r0(observations)
print(fit.model.r0_ohms)
```

The returned numerical model is an ordinary `IEC60751RTDModel`; the calibration
process does not create a second model kind. The evidence retains the observations
and residuals separately.

With two or more distinct temperatures, the model range defaults to the observed
span. A single-temperature observation can identify `R0`, but you must then
declare a nonzero applicability range explicitly:

```python
fit = fitting.fit_iec60751_r0(
    (fitting.CalibrationObservation(0.0, 100.037),),
    minimum_temperature_c=-50.0,
    maximum_temperature_c=250.0,
)
```

An explicitly declared range describes where you intend to use the fitted model,
not where calibration observations were collected. With an independent basis it
may be broader, narrower, or even disjoint from the observation span. The fit
evidence keeps those two ranges separate so the applicability declaration is not
mistaken for calibration evidence. Fitting `R0` does not by itself establish IEC
tolerance-class conformance or prove physical accuracy away from the calibration
points.

## Polynomial fit

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
- fitted-parameter covariance when the statistical basis supports it;
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

## Fitted-parameter covariance

In 0.7.0, both IEC `R0` and polynomial fitting retain parameter covariance when
the regression assumptions provide enough information to estimate it:

```python
covariance = fit.evidence.parameter_covariance
if covariance is not None:
    print(covariance.parameter_names)
    print(covariance.covariance_matrix)
```

For an unweighted fit, or one using only relative weights, the overall residual
variance is not supplied externally. The fitter estimates that scale from residual
scatter and residual degrees of freedom. A saturated fit therefore cannot report
parameter covariance from those data alone; the evidence records the reason instead
of returning a zero matrix just because the fitted curve passes through every point.

When every observation supplies `standard_uncertainty_ohms`, those values have an
absolute physical scale. Under the fit assumptions they define the parameter
covariance directly, so covariance can remain available even when residual degrees
of freedom are zero. The observed residuals remain a separate diagnostic and do not
silently rescale the supplied uncertainties.

Polynomial covariance is reported for the resistance-space power series at the
returned model's reference temperature: `R(T) = a0 + a1*x + a2*x² + ...`. This is
fit evidence, not additional state embedded into the portable model. Covariance
propagation into predicted resistance/temperature uncertainty is a later 0.7.0
step.

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
