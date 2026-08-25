---
title: Self-heating and zero-power resistance
description: Use two current/resistance observations to extrapolate RTD resistance to zero measurement current without mixing acquisition control into the RTD model.
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

print(result.zero_power_resistance_ohms)       # approximately 100.0
print(result.low_current_resistance_rise_ohms) # approximately 0.01
```

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

## What the observation retains

Each `SelfHeatingObservation` keeps the two measured quantities used by the
analysis:

- measurement-current magnitude in amperes; and
- measured RTD resistance in ohms.

It also exposes `current_squared_a2` and the observed electrical power
`dissipated_power_w = I²R` for inspection and later analysis.

The two-current method intentionally uses the documented **resistance versus
current-squared** extrapolation rather than substituting `I²R` as the independent
coordinate. A later 0.8.0 slice may add statistically justified analysis of larger
observation sets.

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

- uncertainty propagation;
- multi-observation fitting and residual diagnostics;
- dissipation/self-heating coefficients; or
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
