---
title: self_heating API
description: Quick API reference for rtd_sensor.self_heating observations, two-current evidence, and zero-power resistance extrapolation.
---

# `rtd_sensor.self_heating`

The self-heating API is **introduced in rtd-sensor 0.8.0**. It provides the
standard two-current resistance-domain extrapolation to zero measurement current
and can then convert the zero-power and observed resistances through an explicitly
supplied RTD model.

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
linearity, propagate uncertainty, or prove that the experimental thermal condition
was stable. Use `evaluate_two_current_temperatures(...)` when model-based
temperatures are also wanted.


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
