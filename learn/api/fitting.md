---
title: fitting API
description: Quick API reference for rtd_sensor.fitting polynomial calibration observations, evidence, results, and fit_polynomial.
---

# `rtd_sensor.fitting`

The public fitting API was **introduced in rtd-sensor 0.6.0**.

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
fit range, RMS/max residuals, weighting diagnostics, condition number, solver,
and scaling information.

See [Calibration fitting](../documentation/custom-models/calibration-fitting.md).
