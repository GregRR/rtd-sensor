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

fit = self_heating.fit_zero_power_resistance(observations)

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

### Estimate fit-parameter uncertainty from residual scatter

For an unweighted 3+ observation fit, residual scatter can also provide the usual
ordinary-least-squares estimate of uncertainty in the fitted zero-power resistance
and slope:

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

If measurement-current uncertainty is material, however, the independent
coordinate itself is uncertain. Ordinary least squares does not account for that.
Likewise, unequal resistance uncertainties, correlation among repeated readings,
or shared bridge/current-source/calibration effects need an explicit statistical
model rather than being inferred from the residuals.

A perfectly fitted finite dataset can produce zero residual-based covariance. That
does **not** prove the experiment has zero physical uncertainty; it only means the
residual-scatter estimator has no scatter from which to estimate a nonzero common
resistance variance.

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

This propagation includes only the residual-scatter covariance estimated from the
unweighted OLS fit. Current coordinates remain fixed/exact, and the RTD model is
treated as fixed. Model-parameter covariance, measurement-current uncertainty,
additional resistance uncertainty, heteroscedasticity, and correlated experimental
effects remain separate.

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

The first uncertainty implementation assumes those four standard uncertainties are
independent. It does **not** infer covariance between readings made with the same
current source, bridge, meter, or calibration chain. If important common-mode or
correlated effects are present, they should not be hidden inside an independence
assumption. Because this is a local first-order propagation, the supplied
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
input dependence and can give the wrong result.

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

- covariance-aware propagation for correlated two-current measurement inputs;
- uncertainty-weighted or covariance-aware multi-observation fitting;
- an automatic experiment-specific residual acceptance threshold;
- a named dissipation/self-heating coefficient or dissipation constant; or
- environmental provenance such as medium, flow, or mounting.

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
