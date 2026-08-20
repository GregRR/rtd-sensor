---
title: fitting API
description: Quick API reference for rtd_sensor.fitting calibration observations, IEC 60751 R0 fitting, polynomial fitting, evidence, and results.
---

# `rtd_sensor.fitting`

The public fitting API was **introduced in rtd-sensor 0.6.0**. IEC 60751 `R0` fitting is being added for rtd-sensor 0.7.0.

## `CalibrationObservation`

**Introduced in:** rtd-sensor 0.6.0

```python
CalibrationObservation(
    temperature_c: float,
    resistance_ohms: float,
    weight: float | None = None,
    standard_uncertainty_ohms: float | None = None,
)
```

`weight` and `standard_uncertainty_ohms` are mutually exclusive on one
observation.

## `fit_iec60751_r0`

**Planned for:** rtd-sensor 0.7.0

```python
fit_iec60751_r0(
    observations: Iterable[CalibrationObservation],
    *,
    minimum_temperature_c: float | None = None,
    maximum_temperature_c: float | None = None,
    name: str = "Fitted IEC 60751 RTD",
) -> IEC60751R0FitResult
```

Fits only the reference resistance `R0` while retaining the package's verified
IEC 60751 PT-385 characteristic. With two or more distinct temperatures, an
omitted model range defaults to the observation span. A single-temperature fit
requires an explicit minimum and maximum model temperature.

Explicit range limits describe intended model applicability, not the span of
calibration evidence. With an independent basis they may be broader, narrower,
or disjoint from the observation span, but they must remain within the supported
IEC characteristic range. The evidence retains the observation span separately
so this assumption remains visible.

## `IEC60751R0FitResult`

**Planned for:** rtd-sensor 0.7.0

Fields:

```text
model: IEC60751RTDModel
evidence: IEC60751R0FitEvidence
```

## `IEC60751R0FitEvidence`

**Planned for:** rtd-sensor 0.7.0

Key fields include observations, resistance residuals, counts/degrees of freedom,
observation span, declared model range, RMS/max residuals, weighting diagnostics,
fitted-parameter covariance when available, and the fitting method.

## `FitParameterCovariance`

**Planned for:** rtd-sensor 0.7.0

Immutable fit evidence describing a fitted-parameter covariance matrix. Key fields:

```text
parameter_names: tuple[str, ...]
covariance_matrix: tuple[tuple[float, ...], ...]
estimation_method: str
parameterization: str
```

For an IEC `R0` fit the single parameter is `r0_ohms`. For polynomial fits the
parameterization is the unnormalized resistance power series at the returned
model's reference temperature, with parameter names `a0`, `a1`, and so on. `a0`
equals the model reference resistance; higher `a` values are the corresponding
resistance-space coefficients rather than the model's normalized coefficients.

Unweighted and relative-weighted fits require positive residual degrees of freedom
to estimate the common residual-variance scale. When covariance cannot be estimated
for that reason, `parameter_covariance` is `None` and the fit evidence records
`parameter_covariance_unavailable_reason`. The same field reports the rare case
where covariance arithmetic is numerically invalid, including non-finite values or
a negative diagonal variance produced by floating-point error. When every
observation supplies an absolute resistance standard uncertainty, covariance comes
directly from those uncertainties and can be available even for a saturated fit.

## `fit_polynomial`

**Introduced in:** rtd-sensor 0.6.0

```python
fit_polynomial(
    observations: Iterable[CalibrationObservation],
    *,
    degree: int,
    minimum_temperature_c: float | None = None,
    maximum_temperature_c: float | None = None,
    name: str = "Fitted polynomial RTD",
    coefficient_source: str | None = None,
) -> PolynomialFitResult
```

Returns a validated polynomial model plus immutable evidence. Raises
`RTDFitError` when observations cannot produce an acceptable deployable model.

## `PolynomialFitResult`

**Introduced in:** rtd-sensor 0.6.0

Fields:

```text
model: PolynomialRTDModel
evidence: PolynomialFitEvidence
```

## `PolynomialFitEvidence`

**Introduced in:** rtd-sensor 0.6.0

Key fields include observations, residuals, degree, counts/degrees of freedom,
fit range, RMS/max residuals, weighting diagnostics, fitted-parameter covariance
when available, condition number, solver, and scaling information.

See [Calibration fitting](../documentation/custom-models/calibration-fitting.md).
