---
title: Calibration fitting
description: Fit characterized IEC 60751 R0 values, selected custom CVD parameters, or validated polynomial RTD models from calibration observations with auditable covariance and diagnostics.
---

# Calibration fitting

`rtd_sensor.fitting` fits RTD models from measured **temperature/resistance
calibration observations** without requiring NumPy. The 0.6.0 API introduced
polynomial fitting; 0.7.0 adds fitting of a characterized IEC 60751 PT-385
reference resistance and selected custom Callendar–Van Dusen parameters.

The API deliberately returns two things together:

1. the numerical model you can use for conversion; and
2. immutable evidence describing how that fit was obtained and how well it
   matched the observations.

**Available since:** rtd-sensor 0.6.0.

## Planned 0.9 calibration experiment design

The current fitting API analyzes calibration observations that already exist. The
0.9 roadmap separately plans a **prospective calibration experiment designer** that
will help choose calibration temperatures before or during an experiment. That
planner is still under design review and is **not part of the current public API**.

The provisional criterion is prediction-oriented: it minimizes a weighted integral
of predicted fitted-curve variance over the declared operating range, after
translating resistance-domain fit uncertainty into first-order
temperature-equivalent uncertainty through a nominal RTD model. The engineering
design document records the full equations, assumptions, candidate-set semantics,
repeat policy, numerical integration, conditioning, and evidence requirements.

### I-optimal versus V-optimal terminology

Optimal-design terminology is not perfectly uniform. [Atkinson
(2015)](https://doi.org/10.1002/9781118445112.stat04090.pub2) explicitly notes that
designs minimizing **average prediction variance over a region** are variously
called **I-optimal** or **V-optimal**. [NIST's Engineering Statistics
Handbook](https://www.itl.nist.gov/div898/handbook/pri/section5/pri52.htm) uses
**V-optimal** for an average-prediction-variance criterion over a specified set of
points.

`rtd-sensor` will use **I-optimal** consistently for the planned continuous
integral over the fitted operating range. This is a documentation choice intended
to distinguish that continuous region-of-interest formulation from NIST's discrete
V-optimal wording. It does **not** mean that V-optimal is wrong terminology in the
broader experimental-design literature.

The planned `rtd-sensor` criterion is more specifically **sensitivity-weighted
I-optimal** because it adds the local RTD `dT/dR` sensitivity needed to express
predicted fitted-curve uncertainty in temperature-equivalent units. That
RTD-specific weighting is a project design decision built on the classical
I/V-optimal average-prediction-variance framework.

### Initial complete-design search scope

The provisional 0.9 complete-design operation is intentionally an **exact search over
a small, explicit candidate set**. It is aimed at curated candidate temperatures in
the low tens with run budgets in the single digits to low teens, not at silently
searching every 1–5 °C grid point across a very wide range. A range/spacing helper
may materialize a denser list, but that does not guarantee that the resulting joint
design problem fits inside the implementation's exhaustive-search limit.

If a complete-design request is too large, the planner will report the calculated
search size and fail explicitly rather than thinning the candidate set or switching
to an unannounced heuristic. The one-step/next-observation operation remains a
different case: it evaluates each supplied candidate once and can therefore remain
useful with substantially denser candidate lists. Exact tested candidate/run
envelopes will be published with the implementation after benchmarking rather than
being guessed before code exists.

## Fit a characterized IEC 60751 `R0`

**Introduced in:** rtd-sensor 0.7.0.

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

## Fit selected Callendar–Van Dusen parameters

**Introduced in:** rtd-sensor 0.7.0.

When calibration observations are intended to define a custom platinum CVD curve,
select exactly which parameters should be estimated and supply the others as fixed
inputs:

```python
from rtd_sensor import fitting

observations = (
    fitting.CalibrationObservation(-50.0, 80.31),
    fitting.CalibrationObservation(0.0, 100.025),
    fitting.CalibrationObservation(100.0, 138.56),
    fitting.CalibrationObservation(200.0, 175.90),
)

fit = fitting.fit_callendar_van_dusen(
    observations,
    fit_parameters=("r0_ohms", "a", "b", "c"),
)
```

The API does not guess which parameters are identifiable. `fit_parameters` is
explicit, and the scaled least-squares system must be full-rank and below the
project's severe-conditioning limit. `C` cannot be fitted without at least one
negative-temperature observation because its basis term is zero at and above
0 °C. You can also fit a subset while holding other values fixed—for example,
fit `A` and `B` while using a previously characterized `R0`.

Internally, a joint `R0/A/B/C` fit uses the exact algebraic linearization
`(R0, R0*A, R0*B, R0*C)` and then transforms the coefficient estimates back into the public CVD parameter
basis. When `R0` and shape coefficients are fitted jointly, the public
coefficient covariance uses a first-order Jacobian/delta-method transformation from
the exact linearized-fit covariance, and that transformation is recorded in the
covariance evidence. No generic nonlinear
optimizer is introduced for this model. The evidence records the linearized
parameter names, design-column scales, and scaled-system condition diagnostic so
identifiability remains inspectable.

If any shape coefficient (`A`, `B`, or `C`) is estimated, the model range may be
narrowed but not extended beyond the observation span. An `R0`-only fit with all
shape coefficients fixed follows the characterized-model rule instead and may use
an independently justified explicit applicability interval.

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

All three fit families retain immutable observations, residuals, weighting and
uncertainty treatment, optional calibration provenance, and fit diagnostics.
Model-specific evidence adds the parameterization details needed to audit that fit.
For example, `PolynomialFitEvidence` retains information including:

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
- covariance-derived parameter standard uncertainties and correlations;
- chi-square and reduced-chi-square diagnostics when absolute resistance standard uncertainties are supplied;
- scaled-system conditioning/identifiability diagnostics where applicable;
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

These values are converted to normalized inverse-variance weights. Temperature is
treated as the independent variable. If a calibration/reference temperature also
has a standard uncertainty, record it separately with
`standard_uncertainty_temperature_c`. Current fitters reject that field by default
rather than silently translating it into resistance uncertainty.

If you intentionally need to preserve that information while still performing the
existing exact-temperature least-squares fit, opt in explicitly:

```python
fit = fitting.fit_polynomial(
    observations,
    degree=2,
    temperature_uncertainty_handling="retain_not_used",
)
```

The returned observations retain the temperature uncertainties and the evidence
reports `temperature_uncertainty_treatment == "retained_not_used"`, but those
uncertainties did **not** affect the coefficients, weighting, chi-square, or
parameter covariance. This is not errors-in-variables regression. It is an explicit
record that the independent-variable uncertainty is known but not modeled. NIST
calibration literature uses errors-in-variables methods when uncertainty in the
applied/reference independent variable cannot reasonably be ignored.

## Calibration provenance

Calibration context can be retained with the fit without changing the numerical
model:

```python
provenance = fitting.CalibrationProvenance(
    certificate_identifier="CERT-42",
    calibration_date="2026-08-20",
    laboratory="Example Calibration Lab",
    reference_standard="PRT-17",
)

fit = fitting.fit_iec60751_r0(
    observations,
    provenance=provenance,
)
```

This provenance belongs to the fit evidence. It is not automatically copied into
`coefficient_source` or portable-model metadata, so a calibration record cannot
silently change model behavior or acquire a downstream deployment meaning.

## Fitted-parameter covariance

In 0.7.0, IEC `R0`, selected custom CVD, and polynomial fitting retain parameter
covariance when the regression assumptions provide enough information to estimate
it:

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

Custom CVD covariance is reported in the fitted subset of the public `R0`, `A`,
`B`, `C` basis. Polynomial covariance is reported for the resistance-space power
series at the returned model's reference temperature:
`R(T) = a0 + a1*x + a2*x² + ...`. This is fit evidence, not additional state
embedded into the portable model. In 0.7.0, supported fitted covariance can be
propagated into predicted resistance uncertainty with
`uncertainty.propagate_fit_covariance_to_resistance()` or into first-order inferred
temperature uncertainty with
`uncertainty.propagate_fit_covariance_to_temperature()`.

See [Fitted-model covariance propagation](../measurement-uncertainty/fitted-model-propagation.md).

## Fit range

Range semantics depend on what the calibration observations actually determine.
Polynomial fits and CVD fits that estimate any shape coefficient (`A`, `B`, or `C`)
may not extend the deployable model beyond the observed calibration span. You may
narrow them inside that span:

```python
fit = fitting.fit_polynomial(
    observations,
    degree=2,
    minimum_temperature_c=10.0,
    maximum_temperature_c=90.0,
)
```

IEC `R0` fitting, and CVD `R0`-only fitting with independently fixed shape
coefficients, are different: the standard/fixed curve shape is not inferred from
the observations, so an explicitly justified applicability range may be broader,
narrower, or disjoint from the observation span within the underlying model's
supported domain. Fit evidence retains the observation span separately so that an
applicability declaration is not mistaken for calibration evidence.

## When fitting fails

`RTDFitError` is raised rather than returning an unsafe model for conditions
such as rank-deficient observations, severe ill-conditioning, or a fitted curve
that becomes non-positive or non-monotonic over its declared range.

This is an important distinction: a least-squares solver producing coefficients
does not automatically mean those coefficients define a usable invertible RTD
model.

## Save the fitted model

The numerical model returned by any supported IEC `R0`, custom CVD, or polynomial
fit can be passed directly to [portable model definitions](portable-definitions.md)
so another process or language can reconstruct the deployable model without
rerunning the fit. Fit evidence, covariance, and calibration provenance remain
separate from that portable numerical definition.

## Related features

- [Characterized IEC 60751 models](characterized-iec60751.md)
- [Callendar–Van Dusen models](callendar-van-dusen.md)
- [Polynomial models](polynomial.md)
- [Portable model definitions](portable-definitions.md)
- [Fitted-model covariance propagation](../measurement-uncertainty/fitted-model-propagation.md)
