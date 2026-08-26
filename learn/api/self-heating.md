---
title: self_heating API
description: Quick API reference for rtd_sensor.self_heating observations, zero-power extrapolation, multi-observation fitting, and uncertainty propagation.
---

# `rtd_sensor.self_heating`

The self-heating API is **introduced in rtd-sensor 0.8.0**. It provides the
standard two-current resistance-domain extrapolation to zero measurement current,
a 3+ observation least-squares fit of the same resistance-versus-current-squared
relationship, residual-based parameter covariance for that larger fit, and
model-based temperature/uncertainty analysis for the two-current result.

## `SelfHeatingObservation`

**Introduced in:** rtd-sensor 0.8.0

```python
SelfHeatingObservation(
    measurement_current_a: float,
    resistance_ohms: float,
)
```

Both values must be finite and greater than zero. Measurement current is the
positive current magnitude in amperes.

Read-only derived properties:

```text
current_squared_a2: float
dissipated_power_w: float  # I²R at the observed resistance
```

`dissipated_power_w` records observation-level electrical power. The two-current
extrapolation itself follows the standard linear model of resistance versus
measurement-current squared.

## `extrapolate_zero_power_resistance`

**Introduced in:** rtd-sensor 0.8.0

```python
extrapolate_zero_power_resistance(
    observation_1: SelfHeatingObservation,
    observation_2: SelfHeatingObservation,
) -> TwoCurrentZeroPowerResult
```

The observations must use distinct current magnitudes and represent the same
stable external thermal condition. The function normalizes them into increasing
current order and extrapolates the resistance-vs-current-squared line to zero
current.

This resistance-domain function deliberately does **not** assess multi-point
linearity or prove that the experimental thermal condition was stable. Use
`propagate_two_current_zero_power_uncertainty(...)` when standard uncertainties for
the measured currents and resistances are available, and use
`evaluate_two_current_temperatures(...)` when model-based temperatures are also
wanted.


## `fit_zero_power_resistance`

**Introduced in:** rtd-sensor 0.8.0

```python
fit_zero_power_resistance(
    observations: Iterable[SelfHeatingObservation],
) -> ZeroPowerResistanceFitResult
```

Fits the same linear self-heating relation used by the two-current method:

```text
R(i) = R0 + k*i²
```

At least three observations and at least two numerically distinct current levels
are required. Repeated measurements at the same current levels are allowed, so a
sequence such as low/high/low/high can retain repeated-cycle scatter while still
providing positive residual degrees of freedom.

The first multi-observation implementation uses **unweighted ordinary least
squares** in resistance. It does not use `I²R` as the fit coordinate and does not
yet incorporate current uncertainty, resistance uncertainty, covariance, or an
automatic residual pass/fail threshold.

## `ZeroPowerResistanceFitResult`

**Introduced in:** rtd-sensor 0.8.0

Fields and read-only diagnostics:

```text
zero_power_resistance_ohms: float
resistance_slope_ohms_per_a2: float
evidence: ZeroPowerResistanceFitEvidence
resistance_slope_direction: "positive" | "zero" | "negative"
```

A positive slope is the direction expected for ordinary self-heating under the
linear model. Zero and negative slopes are retained as evidence instead of being
rejected or silently relabeled as valid self-heating.

## `ZeroPowerResistanceFitEvidence`

**Introduced in:** rtd-sensor 0.8.0

The evidence preserves the observations in caller-supplied order and retains one
residual for each observation. Derived diagnostics include:

```text
observation_count: int
fitted_parameter_count: int                # always 2
residual_degrees_of_freedom: int           # observation_count - 2
distinct_current_count: int
minimum_measurement_current_a: float
maximum_measurement_current_a: float
current_squared_span_a2: float
rms_residual_ohms: float
max_absolute_residual_ohms: float
residual_standard_deviation_ohms: float
fitted_resistances_ohms: tuple[float, ...]
method: "ordinary_least_squares_resistance_vs_current_squared"
```

Residuals are `observed resistance - fitted resistance`. RMS residual is the
descriptive `sqrt(SSE / observation_count)` quantity; residual standard deviation
uses `sqrt(SSE / residual_degrees_of_freedom)`.

These diagnostics provide evidence about scatter and departures from the fitted
line, but they do not prove that the external temperature was stable. Interpreting
a residual magnitude as acceptable still requires an experiment-specific basis.

## `estimate_zero_power_fit_uncertainty`

**Introduced in:** rtd-sensor 0.8.0

```python
estimate_zero_power_fit_uncertainty(
    result: ZeroPowerResistanceFitResult,
) -> ZeroPowerResistanceFitUncertaintyResult
```

Estimates the fitted-parameter covariance from the unweighted fit's retained
residual scatter. The calculation uses the residual variance
`SSE / residual_degrees_of_freedom` and ordinary-least-squares parameter covariance.
It treats measurement-current-squared coordinates as fixed/exact and assumes the
resistance-domain errors about the linear model are independent and zero-mean with
a common variance. That unknown variance is estimated from the retained residuals.

It does not incorporate measurement-current uncertainty, supplied resistance
standard uncertainties, heteroscedasticity, correlated repeated observations, or
fitted RTD-model covariance. Those require a different or larger statistical model.

## `ZeroPowerResistanceFitUncertaintyResult`

**Introduced in:** rtd-sensor 0.8.0

Fields and read-only derived properties:

```text
fit_result: ZeroPowerResistanceFitResult
residual_variance_ohms_squared: float
parameter_names: tuple[str, str]
parameter_covariance_matrix: tuple[tuple[float, float], tuple[float, float]]
zero_power_resistance_variance_ohms_squared: float
zero_power_resistance_standard_uncertainty_ohms: float
resistance_slope_variance_ohms_squared_per_a4: float
resistance_slope_standard_uncertainty_ohms_per_a2: float
zero_power_resistance_slope_covariance_ohms_squared_per_a2: float
method: "residual_variance_scaled_least_squares"
```

The covariance-matrix parameter order is:

```text
zero_power_resistance_ohms
resistance_slope_ohms_per_a2
```

A zero residual-based covariance from an exact finite fit is not a statement that
the physical experiment has zero uncertainty. It only means this residual-scatter
estimator observed no scatter from which to estimate a nonzero common resistance
variance.


## `evaluate_two_current_temperatures`

**Introduced in:** rtd-sensor 0.8.0

```python
evaluate_two_current_temperatures(
    result: TwoCurrentZeroPowerResult,
    *,
    model: RTDModel,
) -> TwoCurrentSelfHeatingTemperatureResult
```

The supplied model converts the extrapolated zero-power resistance and both
observed resistances to Celsius. Model conversion errors and range failures
propagate unchanged.

## `TwoCurrentSelfHeatingTemperatureResult`

**Introduced in:** rtd-sensor 0.8.0

Fields and read-only derived properties:

```text
zero_power_result: TwoCurrentZeroPowerResult
model: RTDModel
zero_power_temperature_c: float
low_current_temperature_c: float
high_current_temperature_c: float
low_current_temperature_rise_c: float
high_current_temperature_rise_c: float
```

The exact model object supplied to `evaluate_two_current_temperatures(...)` is
retained as `model` so the model used for the temperature interpretation remains
inspectable with the result. The temperature rises are each observed temperature
minus the extrapolated zero-power temperature. They do not independently establish
ambient temperature or prove that the experiment was thermally stable.

## `TwoCurrentInputStandardUncertainties`

**Introduced in:** rtd-sensor 0.8.0

```python
TwoCurrentInputStandardUncertainties(
    *,
    low_current_standard_uncertainty_a: float,
    low_resistance_standard_uncertainty_ohms: float,
    high_current_standard_uncertainty_a: float,
    high_resistance_standard_uncertainty_ohms: float,
)
```

All four values must be finite and non-negative. The fields correspond to the
normalized low- and high-current observations retained by the zero-power result.
This first uncertainty model treats the four input quantities as independent.
Because the propagation is a local first-order approximation, the supplied
uncertainties should also be small enough for that local linearization to be
meaningful. In particular, a current uncertainty that is large relative to the
separation between the two current levels needs more careful treatment.

The fixed sensitivity-vector order is:

```text
low_current_a
low_resistance_ohms
high_current_a
high_resistance_ohms
```

## `propagate_two_current_zero_power_uncertainty`

**Introduced in:** rtd-sensor 0.8.0

```python
propagate_two_current_zero_power_uncertainty(
    result: TwoCurrentZeroPowerResult,
    *,
    input_standard_uncertainties: TwoCurrentInputStandardUncertainties,
) -> TwoCurrentZeroPowerUncertaintyResult
```

Applies first-order propagation directly to the two measured currents and two
measured resistances. Both current uncertainty and resistance uncertainty can
therefore contribute to the zero-power resistance uncertainty.

`TwoCurrentZeroPowerUncertaintyResult` retains the input uncertainties, the
zero-power-resistance sensitivity vector, propagated variance, standard
uncertainty, and the method label `first_order_independent_inputs`.

## `propagate_two_current_temperature_uncertainty`

**Introduced in:** rtd-sensor 0.8.0

```python
propagate_two_current_temperature_uncertainty(
    result: TwoCurrentSelfHeatingTemperatureResult,
    *,
    input_standard_uncertainties: TwoCurrentInputStandardUncertainties,
) -> TwoCurrentSelfHeatingTemperatureUncertaintyResult
```

Uses the local `dT/dR` sensitivity supplied by the exact RTD model retained in the
temperature result. It reports standard uncertainty for:

- zero-power temperature;
- low- and high-current observed temperatures; and
- low- and high-current self-heating temperature rises.

The temperature-rise uncertainties are propagated from the original four measured
inputs. They are **not** calculated by root-sum-squaring an observed-temperature
uncertainty with the zero-power-temperature uncertainty, because those derived
quantities share the same resistance observations and are therefore not
independent.

`TwoCurrentSelfHeatingTemperatureUncertaintyResult` retains the input sensitivity
vectors, variances, standard uncertainties, the corresponding zero-power
resistance-uncertainty result, and the method label
`first_order_independent_inputs`. Fitted-model covariance and other uncertainty
budget components remain separate.

## `TwoCurrentZeroPowerResult`

**Introduced in:** rtd-sensor 0.8.0

Fields and read-only derived properties:

```text
zero_power_resistance_ohms: float
evidence: TwoCurrentZeroPowerEvidence
low_current_resistance_rise_ohms: float
high_current_resistance_rise_ohms: float
```

## `TwoCurrentZeroPowerEvidence`

**Introduced in:** rtd-sensor 0.8.0

The immutable evidence retains the low- and high-current observations. Derived
properties expose:

```text
current_ratio: float
current_squared_change_a2: float
resistance_change_ohms: float
resistance_slope_ohms_per_a2: float
residual_degrees_of_freedom: int  # always 0 for the two-point method
method: "linear_resistance_vs_current_squared"
```

With only two observations, there is no residual redundancy. The result is an
extrapolation under the caller's stable-condition assumption, not an independent
stability test.

See [Self-heating and zero-power resistance](../documentation/measurement-uncertainty/self-heating.md)
for the scientific assumptions and an example.
