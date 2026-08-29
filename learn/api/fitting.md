---
title: fitting API
description: Quick API reference for rtd_sensor.fitting calibration observations, IEC 60751 R0 fitting, custom CVD fitting, polynomial fitting, covariance, diagnostics, and results.
---

# `rtd_sensor.fitting`

The public fitting API was **introduced in rtd-sensor 0.6.0**. rtd-sensor 0.7.0
adds characterized IEC 60751 `R0` fitting, selected custom Callendar–Van Dusen
parameter fitting, fitted-parameter covariance/diagnostics, calibration provenance,
and explicit reference-temperature uncertainty handling.

!!! note "Planned 0.9 experiment-design terminology"
    The prospective calibration experiment planner described in the 0.9 roadmap is
    still under design review and is **not part of this public API yet**. Its
    provisional continuous average-prediction-variance criterion is documented as
    **I-optimal**. Some optimal-design literature also calls this kind of criterion
    **V-optimal**; Atkinson (2015) explicitly uses both names. `rtd-sensor` uses
    I-optimal for the continuous operating-range integral to distinguish it from
    NIST's discrete V-optimal wording, not because V-optimal is considered
    incorrect. The provisional complete-design operation is exhaustive and intended
    for small curated candidate sets; dense grids may exceed its explicit search
    limit, while one-step planning remains linear in candidate count. See
    [Calibration fitting](../documentation/custom-models/calibration-fitting.md#i-optimal-versus-v-optimal-terminology).

## `CalibrationObservation`

**Introduced in:** rtd-sensor 0.6.0

```python
CalibrationObservation(
    temperature_c: float,
    resistance_ohms: float,
    weight: float | None = None,
    standard_uncertainty_ohms: float | None = None,
    standard_uncertainty_temperature_c: float | None = None,
)
```

`weight` and `standard_uncertainty_ohms` are mutually exclusive on one
observation. `standard_uncertainty_temperature_c` records uncertainty in the
calibration/reference temperature coordinate; current fitters do not use it as a
weight. Fits reject it by default unless the caller explicitly chooses
`temperature_uncertainty_handling="retain_not_used"`. The
`standard_uncertainty_temperature_c` field was added in rtd-sensor 0.7.0.

## Type aliases added in rtd-sensor 0.7.0

```text
CalibrationTemperatureUncertaintyHandling = Literal["reject", "retain_not_used"]
CallendarVanDusenFitParameter = Literal["r0_ohms", "a", "b", "c"]
```

## `CalibrationProvenance`

**Introduced in:** rtd-sensor 0.7.0

Immutable application-neutral calibration context retained only with fit evidence.
Optional fields are `certificate_identifier`, `calibration_date`, `laboratory`,
`reference_standard`, `source_document`, and `notes`. These values do not alter the
fit or numerical model and are not automatically copied into portable-model
metadata.

## `fit_iec60751_r0`

**Introduced in:** rtd-sensor 0.7.0

```python
fit_iec60751_r0(
    observations: Iterable[CalibrationObservation],
    *,
    minimum_temperature_c: float | None = None,
    maximum_temperature_c: float | None = None,
    name: str = "Fitted IEC 60751 RTD",
    temperature_uncertainty_handling: Literal["reject", "retain_not_used"] = "reject",
    provenance: CalibrationProvenance | None = None,
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


## `fit_callendar_van_dusen`

**Introduced in:** rtd-sensor 0.7.0

```python
fit_callendar_van_dusen(
    observations: Iterable[CalibrationObservation],
    *,
    fit_parameters: Iterable[CallendarVanDusenFitParameter],
    r0_ohms: float | None = None,
    a: float | None = None,
    b: float | None = None,
    c: float | None = None,
    minimum_temperature_c: float | None = None,
    maximum_temperature_c: float | None = None,
    name: str = "Fitted Callendar-Van Dusen RTD",
    coefficient_source: str | None = None,
    temperature_uncertainty_handling: Literal["reject", "retain_not_used"] = "reject",
    provenance: CalibrationProvenance | None = None,
) -> CallendarVanDusenFitResult
```

Fits an explicitly requested subset of `r0_ohms`, `a`, `b`, and `c`. Any
parameter not fitted must be supplied as a fixed value, except `c` may be omitted
for a wholly non-negative model range. The fitting system is algebraically
linearized and column-scaled before Householder QR. Rank deficiency and severe
scaled-system ill-conditioning are rejected as non-identifiable parameter fits.

Fitting `c` requires at least one negative-temperature observation because the CVD
`C` term is zero at and above 0 °C. When any shape coefficient (`a`, `b`, or `c`)
is fitted, the declared model range may be narrowed but not extended beyond the
calibration-observation span. An `R0`-only CVD fit with fixed shape coefficients
may use an independently justified explicit applicability range.

## `CallendarVanDusenFitResult` / `CallendarVanDusenFitEvidence`

**Introduced in:** rtd-sensor 0.7.0

The result contains a validated `CallendarVanDusenRTDModel` plus immutable fit
evidence. Evidence identifies the fitted parameters, residuals, observation span
separately from the declared model range, weighting method, chi-square diagnostics
when absolute resistance uncertainties are supplied, parameter covariance,
scaled-system condition diagnostic, linearized parameter names, and design-column
scales used for identifiability/stability.

## `IEC60751R0FitResult`

**Introduced in:** rtd-sensor 0.7.0

Fields:

```text
model: IEC60751RTDModel
evidence: IEC60751R0FitEvidence
```

## `IEC60751R0FitEvidence`

**Introduced in:** rtd-sensor 0.7.0

Key fields include observations, calibration/reference-temperature uncertainty
treatment, optional `CalibrationProvenance`, resistance residuals, counts/degrees of
freedom, observation span, declared model range, RMS/max residuals, weighting
diagnostics, fitted-parameter covariance when available, and the fitting method.

## `FitParameterCovariance`

**Introduced in:** rtd-sensor 0.7.0

Immutable fit evidence describing a fitted-parameter covariance matrix. Key fields:

```text
parameter_names: tuple[str, ...]
covariance_matrix: tuple[tuple[float, ...], ...]
estimation_method: str
parameterization: str
parameter_transformation: str | None
```

`standard_uncertainties` and `correlation_matrix` are derived read-only
properties. The correlation matrix is particularly useful for spotting strongly
coupled fitted CVD or polynomial parameters; entries involving a zero-variance
parameter are `None` because the correlation coefficient is undefined.

For fits that supply an absolute `standard_uncertainty_ohms` on every observation,
fit evidence also reports `chi_squared`; `reduced_chi_squared` is reported when
residual degrees of freedom are positive. These are residual-consistency
diagnostics under the stated resistance-uncertainty model, not automatic
acceptance criteria.

For an IEC `R0` fit the single parameter is `r0_ohms`. Custom CVD fits expose covariance in the actual fitted subset of the public
`r0_ohms`, `a`, `b`, `c` parameter basis after transforming out of the internal
linearized product basis. When `R0` and a shape coefficient are fitted jointly,
`parameter_transformation` records that this public-parameter covariance uses a
first-order ratio/Jacobian transformation from the exact linearized-fit covariance.
For polynomial fits the parameterization is the unnormalized resistance power
series at the returned model's reference temperature, with parameter names `a0`,
`a1`, and so on. `a0`
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

**Introduced in:** rtd-sensor 0.6.0. The `temperature_uncertainty_handling` and
`provenance` arguments were added in rtd-sensor 0.7.0.

```python
fit_polynomial(
    observations: Iterable[CalibrationObservation],
    *,
    degree: int,
    minimum_temperature_c: float | None = None,
    maximum_temperature_c: float | None = None,
    name: str = "Fitted polynomial RTD",
    coefficient_source: str | None = None,
    temperature_uncertainty_handling: Literal["reject", "retain_not_used"] = "reject",
    provenance: CalibrationProvenance | None = None,
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

**Introduced in:** rtd-sensor 0.6.0; covariance, chi-square diagnostics,
reference-temperature uncertainty treatment, and calibration provenance were added
in rtd-sensor 0.7.0.

Key fields include observations, calibration/reference-temperature uncertainty
treatment, optional `CalibrationProvenance`, residuals, degree, counts/degrees of
freedom, fit range, RMS/max residuals, weighting diagnostics, chi-square diagnostics
when absolute resistance uncertainties are supplied, fitted-parameter covariance
when available, condition number, solver, and scaling information.

See [Calibration fitting](../documentation/custom-models/calibration-fitting.md).
