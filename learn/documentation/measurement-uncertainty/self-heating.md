---
title: Self-heating and zero-power resistance
description: Extrapolate RTD resistance to zero measurement current from two or more current/resistance observations without mixing acquisition control into the RTD model.
---

# Self-heating and zero-power resistance

**Available since:** rtd-sensor 0.8.0.

Measuring an RTD requires current. That current dissipates electrical power in
the sensing element and can raise the element temperature above its surroundings.
The size of the effect depends on the thermometer construction and on the thermal
environment, so self-heating is not an immutable property of a Pt100 or another
RTD characteristic.

`rtd_sensor.self_heating` analyzes current/resistance observations supplied by the
caller. It does not control current sources, bridges, ADCs, MAX31865 devices, or
other acquisition hardware.

## Two-current zero-power extrapolation

The first 0.8.0 API follows the resistance-thermometry method documented by the
BIPM: under a stable external thermal condition, measured resistance is treated as
linear in measurement-current squared over the two current levels. Extrapolating
that line to zero current gives the zero-power resistance estimate.

For two observations `(i1, R1)` and `(i2, R2)`, the relation is equivalent to:

```text
R0 = (R1*i2² - R2*i1²) / (i2² - i1²)
```

The BIPM industrial PRT guide also describes the common 1 mA and √2 mA case. When
the higher-current power is approximately doubled, the resistance increase between
the two measurements equals the low-current self-heating resistance rise under the
linear model.

```python
import math

from rtd_sensor import self_heating

low = self_heating.SelfHeatingObservation(
    measurement_current_a=0.001,
    resistance_ohms=100.01,
)
high = self_heating.SelfHeatingObservation(
    measurement_current_a=math.sqrt(2.0) * 0.001,
    resistance_ohms=100.02,
)

result = self_heating.extrapolate_zero_power_resistance(low, high)

print(result.zero_power_resistance_ohms)  # approximately 100.0
print(result.low_current_resistance_rise_ohms)  # approximately 0.01
```

## Fit three or more observations

With three or more observations, `rtd-sensor` can fit the same
resistance-versus-current-squared relationship instead of forcing an exact line
through only two points:

```python
observations = [
    self_heating.SelfHeatingObservation(0.001, 100.010),
    self_heating.SelfHeatingObservation(2**0.5 * 0.001, 100.019),
    self_heating.SelfHeatingObservation(0.001, 100.011),
    self_heating.SelfHeatingObservation(2**0.5 * 0.001, 100.021),
]

context = self_heating.SelfHeatingExperimentContext(
    medium="flowing water",
    flow_condition="approximately 0.4 m/s",
    mounting="fully immersed probe",
)

fit = self_heating.fit_zero_power_resistance(
    observations,
    context=context,
)

print(fit.zero_power_resistance_ohms)
print(fit.resistance_slope_ohms_per_a2)
print(fit.evidence.residuals_ohms)
print(fit.evidence.residual_standard_deviation_ohms)
```

The fit is:

```text
R(i) = R0 + k*i²
```

and uses ordinary least squares in resistance. The observation-level `I²R` power
remains available for inspection, but it is **not** substituted as the independent
fit coordinate. That keeps the larger-observation analysis on the same model as
the documented two-current extrapolation and avoids putting measured resistance
on both sides of the regression.

### Repeated current cycles are allowed

Three observations do not require three different current levels. Repeated
low/high cycles are useful evidence when the experiment needs multiple readings to
estimate a stable difference. For example:

```text
low → high → low → high
```

provides four observations at two current levels and two residual degrees of
freedom. `rtd-sensor` preserves the observations and residuals in the order the
caller supplied them so the sequence remains inspectable.

### What the residuals tell you

The returned evidence reports:

- every resistance residual (`observed - fitted`);
- descriptive RMS residual;
- maximum absolute residual;
- residual standard deviation using the positive residual degrees of freedom;
- the number of observations and distinct current levels; and
- the sampled current and current-squared span.

A larger observation set can therefore expose scatter or departures from the
assumed linear relation that two points cannot reveal. It still cannot prove that
the external temperature was stable. Drift, incomplete settling, acquisition
error, and genuine nonlinearity can all appear in the residuals.

The first multi-observation fit deliberately does **not** assign a universal
"good" or "bad" residual threshold. Such a threshold depends on the experiment,
measurement uncertainty, thermometer, and intended use. It also remains unweighted
for now; resistance/current uncertainties and correlated effects are not silently
inserted into the objective.

### Ask what the observations can actually support

**Introduced in rtd-sensor 0.8.0.**

After either a two-current extrapolation or a larger fit, you can ask for a
threshold-free evidence assessment:

```python
assessment = self_heating.assess_zero_power_extrapolation(fit)

print(assessment.warning_codes)
print(assessment.minimum_to_maximum_current_ratio)
print(assessment.zero_power_extrapolation_distance_in_current_squared_spans)
```

This does not turn residuals into an arbitrary green/red score. It reports
structural limitations that can be stated without knowing the experiment's required
uncertainty or acceptance tolerance. For example:

- two observations exactly define a two-parameter line, so they have no residual
  check;
- repeated observations at only two current levels can show scatter at those levels
  but cannot test line shape across a third level;
- three or more distinct current levels without repeats can test line shape but do
  not show within-level repeatability; and
- a zero or negative `R`-versus-`I²` slope does not show the positive resistance
  rise expected for ordinary self-heating.

The assessment also exposes geometry rather than silently choosing a threshold.
`minimum_to_maximum_current_ratio` shows how separated the sampled currents are.
`zero_power_extrapolation_distance_in_current_squared_spans` reports how far zero
current lies beyond the lowest sampled `I²` point relative to the sampled `I²`
span. A larger value means zero lies farther outside the observed span, but
`rtd-sensor` intentionally does not define a universally acceptable maximum.

These diagnostics are evidence checks, not proof of thermal stability. BIPM/CCT
guidance still requires the external temperature to remain constant and readings to
become steady; when drift is present, repeated current cycles may be needed. The
software has no external-temperature or time-history evidence unless the experiment
records it separately.

### Estimate fit-parameter uncertainty from residual scatter

For a 3+ observation fit, the parameter-covariance model depends on how the
resistance observations were fitted. An unweighted fit uses the usual residual-
scatter ordinary-least-squares estimate of uncertainty in the fitted zero-power
resistance and slope:

```python
fit_uncertainty = self_heating.estimate_zero_power_fit_uncertainty(fit)

print(fit_uncertainty.zero_power_resistance_standard_uncertainty_ohms)
print(fit_uncertainty.resistance_slope_standard_uncertainty_ohms_per_a2)
print(fit_uncertainty.parameter_covariance_matrix)
```

The estimate uses the residual variance
`SSE / residual_degrees_of_freedom` and the two-parameter ordinary-least-squares
information matrix. The covariance matrix order is:

```text
zero_power_resistance_ohms
resistance_slope_ohms_per_a2
```

This is a **conditional regression uncertainty estimate**, not a complete
measurement uncertainty budget. It assumes the sampled `I²` values are effectively
known, and that the resistance-domain errors about the fitted line are independent
and zero-mean with a common variance. That unknown variance is estimated from the
retained residuals. This makes the result useful for repeated-current experiments
whose scatter reasonably matches those assumptions.

If every resistance observation instead has a defensible absolute standard
uncertainty, use inverse-variance weighted least squares:

```python
weighted_fit = self_heating.fit_zero_power_resistance(
    observations,
    resistance_standard_uncertainties_ohms=(0.002, 0.002, 0.005, 0.005),
)
weighted_uncertainty = self_heating.estimate_zero_power_fit_uncertainty(weighted_fit)

print(weighted_fit.evidence.effective_weights)
print(weighted_fit.evidence.chi_squared)
print(weighted_fit.evidence.reduced_chi_squared)
print(weighted_uncertainty.parameter_covariance_matrix)
```

The effective fit weights are proportional to `1/u(R)²`. They are normalized for
numerical stability, but the original absolute uncertainties are retained and used
for chi-square and parameter covariance. That covariance is **not** multiplied by
reduced chi-square or otherwise rescaled to make the observed residuals agree with
the supplied uncertainties. An exact weighted line can therefore have zero
chi-square residual while still retaining nonzero parameter uncertainty.

If measurement-current uncertainty is material, however, the independent
coordinate itself is uncertain. Fixed-coordinate least squares does not account for
that; an errors-in-variables model is needed. Correlation among repeated readings or
shared bridge/current-source/calibration effects likewise needs an explicit
covariance model rather than being inferred from residuals or from marginal
resistance standard uncertainties.

A perfectly fitted **unweighted** finite dataset can produce zero residual-based
covariance. That does **not** prove the experiment has zero physical uncertainty; it
only means the residual-scatter estimator has no scatter from which to estimate a
nonzero common resistance variance.

A positive fitted slope is the direction ordinarily expected for self-heating.
Zero or negative slopes are retained and reported as evidence rather than being
rejected, because software cannot determine from the sign alone whether the cause
was negligible heating, drift, measurement noise, or an invalid experiment.

### Interpret the larger fit as temperature and power

The 3+ observation fit can be converted through an RTD model without replacing its
resistance-domain evidence:

```python
fit_temperatures = self_heating.evaluate_zero_power_fit_temperatures(
    fit,
    model=model,
)

print(fit_temperatures.zero_power_temperature_c)
print(fit_temperatures.fitted_temperature_rises_c)
print(fit_temperatures.observed_dissipated_powers_w)
print(fit_temperatures.fitted_dissipated_powers_w)
```

The same model is used for the fitted zero-power resistance, each observed
resistance, and the fit-predicted resistance at each sampled current. The result
therefore keeps both views:

- **observed** temperatures and ``I²R_observed`` powers show the measured data;
- **fitted** temperatures and ``I²R_fitted`` powers show the retained linear
  resistance-versus-current-squared fit at those same current coordinates.

The difference between observed and fitted temperatures is also retained as a
temperature-domain residual. Negative fitted temperature rises remain visible when
the fitted resistance slope is negative; the API does not relabel such a dataset as
valid physical self-heating.

These temperature-rise-versus-power pairs are useful evidence for later
dissipation analysis, but they are not automatically called a self-heating
coefficient or dissipation constant. The BIPM industrial-PRT guidance notes that
such coefficients depend on the sensor/probe construction and the specific thermal
environment, and manufacturers commonly specify them for a stated medium and flow
condition.

### Propagate the larger fit covariance into temperature rises

The retained intercept/slope covariance can be propagated through the same RTD
model:

```python
fit_temperature_uncertainty = (
    self_heating.propagate_zero_power_fit_temperature_uncertainty(fit_temperatures)
)

print(fit_temperature_uncertainty.zero_power_temperature_standard_uncertainty_c)
print(fit_temperature_uncertainty.fitted_temperature_rise_standard_uncertainties_c)
```

At each sampled current-squared coordinate ``x``, the fitted resistance is
``R0 + k*x``. Its sensitivity to the fitted parameters ``(R0, k)`` is therefore
``(1, x)``. Multiplying by the model's local ``dT/dR`` gives the fitted-temperature
sensitivity vector. The zero-power sensitivity is subtracted before propagating a
temperature rise, so the shared fitted intercept and its covariance with slope are
not discarded.

This propagation uses whichever intercept/slope covariance the retained fit
provides: residual-scatter covariance for unweighted OLS, or covariance defined by
supplied absolute resistance standard uncertainties for inverse-variance weighted
least squares. Current coordinates remain fixed/exact, and the RTD model is treated
as fixed. Model-parameter covariance, measurement-current uncertainty, and
correlated experimental effects remain separate.

## Convert the result to zero-power temperature

Once the resistance extrapolation is complete, the same result can be interpreted
through any supplied RTD model:

```python
from rtd_sensor import catalog, self_heating

model = catalog.get_model("pt100")
temperatures = self_heating.evaluate_two_current_temperatures(
    result,
    model=model,
)

print(temperatures.zero_power_temperature_c)
print(temperatures.low_current_temperature_rise_c)
print(temperatures.high_current_temperature_rise_c)
```

The function converts three resistance values through the **same** model:

- the extrapolated zero-power resistance;
- the low-current observed resistance; and
- the high-current observed resistance.

The reported self-heating temperature rise at each operating point is the
difference between that observed temperature and the extrapolated zero-power
temperature. The result also retains the exact supplied model object so the model
used for those conversions remains inspectable. The calculation does not modify
the RTD model, and model range or conversion errors propagate normally.

The zero-power temperature is the RTD-model interpretation of the extrapolated
zero-current resistance under the experiment's stable-condition assumption. It
should not be described as an independently measured ambient temperature.

## Propagate measurement uncertainty

If standard uncertainties are available for the two measurement currents and two
measured resistances, they can be propagated through the extrapolation without
changing the original observations:

```python
inputs = self_heating.TwoCurrentInputStandardUncertainties(
    low_current_standard_uncertainty_a=1e-6,
    low_resistance_standard_uncertainty_ohms=0.002,
    high_current_standard_uncertainty_a=1e-6,
    high_resistance_standard_uncertainty_ohms=0.002,
)

zero_power_uncertainty = self_heating.propagate_two_current_zero_power_uncertainty(
    result,
    input_standard_uncertainties=inputs,
)
print(zero_power_uncertainty.zero_power_resistance_standard_uncertainty_ohms)

temperature_uncertainty = self_heating.propagate_two_current_temperature_uncertainty(
    temperatures,
    input_standard_uncertainties=inputs,
)
print(temperature_uncertainty.zero_power_temperature_standard_uncertainty_c)
print(temperature_uncertainty.low_current_temperature_rise_standard_uncertainty_c)
```

The calculation uses first-order propagation from the original four measured
inputs in this order:

```text
low current, low resistance, high current, high resistance
```

When no additional dependence information is supplied, those four standard
uncertainties are treated as independent. If a defensible correlation model is
available, retain it explicitly instead of hiding it inside an independence
assumption:

```python
correlations = self_heating.TwoCurrentInputCorrelationMatrix(
    correlation_matrix=(
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 1.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 1.0, 0.0, 1.0),
    )
)

correlated = self_heating.propagate_two_current_zero_power_uncertainty(
    result,
    input_standard_uncertainties=inputs,
    input_correlation_matrix=correlations,
)

print(correlated.input_covariance_matrix)
print(correlated.propagation_method)
```

This example represents perfectly correlated low/high resistance errors while the
other cross-correlations are zero. The matrix order is still `I_low`, `R_low`,
`I_high`, `R_high`. `rtd-sensor` requires a finite, symmetric, positive-semidefinite
correlation matrix with unit diagonal and combines it with the supplied standard
uncertainties to form the covariance matrix used in `J Cov(x) Jᵀ`.

Correlation is **not inferred** merely because readings use the same current source,
bridge, meter, calibration chain, or acquisition sequence. A shared instrument can
create dependence, but its sign and magnitude require an actual measurement/error
model. Because this remains a local first-order propagation, the supplied
uncertainties should also be small enough for the local linearization to be
meaningful. A current uncertainty that is large relative to the separation between
the two current levels needs more careful treatment.

For temperature results, the local `dT/dR` sensitivity comes from the same RTD
model used for the temperatures. Fitted-model covariance is not added
automatically; it remains a separate contribution because its dependence on the
measurement inputs cannot be assumed in general.

### Why temperature-rise uncertainty is propagated directly

The low-current temperature and the zero-power temperature are not independent:
the low-current resistance is one of the measurements used to calculate the
zero-power resistance. The same is true at the high-current point.

For that reason, `rtd-sensor` propagates each temperature rise directly from the
original current/resistance inputs. It does not simply combine the uncertainty of
`T_observed` and `T_zero_power` by root-sum-square, which would discard the shared
input dependence and can give the wrong result. When an input correlation matrix is
supplied, the same full covariance matrix is used here as well; common-mode terms
can therefore cancel or reinforce according to the retained sensitivity vectors.

## Report a context-bound self-heating coefficient

A self-heating coefficient is meaningful only with the thermal environment that
produced it. For the 3+ observation fit, retain that information when fitting and
then derive the coefficient from the model-based temperature result:

```python
coefficient = self_heating.evaluate_self_heating_coefficient(fit_temperatures)

print(coefficient.self_heating_coefficient_c_per_mw)
print(coefficient.dissipation_constant_mw_per_c)
print(coefficient.pointwise_self_heating_coefficients_c_per_w)
print(coefficient.coefficient_fit_residuals_c)
```

The scalar is a through-origin fit of **fitted temperature rise versus fitted
``I²R`` power** at the distinct sampled current levels. It is a **finite-range**
coefficient over those levels, not the zero-power differential ``d(ΔT)/dP``.
Repeated measurements at one current level still influence the resistance fit, but
that level appears only once in the coefficient fit so replicate count does not
create an extra secondary weight.

The finite-range distinction matters even for idealized data. If the resistance fit
is exactly ``R = R0 + kI²``, then fitted power is
``P = I²(R0 + kI²)``. The ``kI⁴`` term means pointwise ``ΔT/P`` can change across
the current range even with no measurement noise and, for a linear RTD model, no
model curvature. The result therefore retains the pointwise ``ΔT/P`` values and
coefficient-fit residuals. Their RMS and maximum absolute residual are descriptive
shape diagnostics of the fitted relationship, not a second statistical error model.
Use those diagnostics to judge whether one scalar describes the sampled range;
`rtd-sensor` does not invent a universal acceptance threshold. A zero or negative
resistance slope is retained by the resistance fit but is not promoted into a named
positive self-heating coefficient. The two-current correction path is intentionally
not used for this named characterization because two points leave no residual
degrees of freedom.

The reciprocal is reported as the **dissipation constant**. The convenient unit
forms follow the metrology guidance:

```text
self-heating coefficient: °C/mW
dissipation constant:     mW/°C
```

Do not transfer a coefficient measured in one medium, flow condition, mounting, or
setup to another without evidence. Treat it as local to the fitted zero-power
temperature and sampled power/current range as well. The BIPM/CCT guidance notes
that self-heating depends on thermal contact with the environment and can also vary
with temperature; manufacturer coefficients are therefore measured under stated
conditions.

### Propagate the fit covariance into the coefficient

```python
coefficient_uncertainty = self_heating.propagate_self_heating_coefficient_uncertainty(
    coefficient
)

print(coefficient_uncertainty.self_heating_coefficient_standard_uncertainty_c_per_mw)
print(coefficient_uncertainty.dissipation_constant_standard_uncertainty_mw_per_c)
```

This propagates the retained covariance of the fitted zero-power resistance and
slope into the finite-range coefficient. That covariance can come from residual-
scatter OLS or from supplied absolute resistance standard uncertainties in a
weighted fit. It does not include
the deterministic difference between that scalar and a zero-power differential
coefficient. It also does not add coefficient-fit residual scatter, model parameter
covariance, current uncertainty, or correlated environmental/acquisition effects.
An exact resistance fit can therefore produce zero covariance-derived coefficient
uncertainty without proving that the physical self-heating behavior is exact or
range-independent.

## What the observation retains

Each `SelfHeatingObservation` keeps the two measured quantities used by the
analysis:

- measurement-current magnitude in amperes; and
- measured RTD resistance in ohms.

It also exposes `current_squared_a2` and the observed electrical power
`dissipated_power_w = I²R` for inspection and later analysis.

Both the two-current extrapolation and the multi-observation fit intentionally use
the documented **resistance versus current-squared** relationship rather than
substituting `I²R` as the independent coordinate. Observation-level power remains
available for later dissipation/self-heating analysis.

## Experimental assumptions matter

The calculation cannot prove that the physical experiment was valid. In
particular, the source guidance requires the external temperature to remain stable
and enough time to be allowed for readings to become steady. When temperature is
drifting, repeated current cycles may be needed to estimate the self-heating change
reliably.

Two observations exactly determine a line, so the first API has zero residual
degrees of freedom. The returned evidence therefore exposes the current ratio,
resistance change, current-squared span, and slope, but it does not label the data
as experimentally stable.

## Deliberately deferred within 0.8.0

The current 0.8.0 implementation does not yet provide:

- errors-in-variables multi-observation fitting when measurement-current
  uncertainty is material;
- covariance-aware multi-observation fitting for defensibly correlated observations;
- an automatic experiment-specific residual acceptance threshold.

Those remaining capabilities stay within the documented 0.8.0 scope and can
build on the retained observation/evidence contract rather than changing nominal
RTD conversion.

## Sources

The implementation basis is the BIPM/CCT guidance already retained in the project
references:

- *Guide to the Realization of the ITS-90 — Platinum Resistance Thermometry*,
  section 5.3.3, especially Equation 34 for two-current zero-current resistance;
- *Guide on Secondary Thermometry — Industrial Platinum Resistance Thermometers*,
  section 4.1 and Equation 4.1.1 for linear extrapolation of resistance versus
  current squared and the requirement for stable external temperature.

See the project [`docs/REFERENCES.md`](https://github.com/GregRR/rtd-sensor/blob/main/docs/REFERENCES.md)
for the retained source record.
