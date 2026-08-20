---
title: RTD sensitivity
description: Use rtd-sensor to calculate dR/dT and dT/dR and understand why sensitivity matters for resolution and uncertainty.
---

# Sensitivity

**Sensitivity** describes how strongly one quantity changes when another
quantity changes. For RTDs, two forms are useful:

- **resistance sensitivity**, `dR/dT`, in ohms per degree Celsius (Ω/°C);
- **temperature sensitivity**, `dT/dR`, in degrees Celsius per ohm (°C/Ω).

They are local values: the sensitivity can change with temperature because an
RTD characteristic is not necessarily perfectly linear.

## Resistance sensitivity

```python
from rtd_sensor import pt100

d_r_d_t = pt100.resistance_sensitivity_ohms_per_celsius(100.0)
print(d_r_d_t)
```

This answers: **near 100 °C, how many ohms does this Pt100 model change for a
one-degree change in temperature?**

## Temperature sensitivity

```python
from rtd_sensor import pt100

d_t_d_r = pt100.temperature_sensitivity_celsius_per_ohm(100.0)
print(d_t_d_r)
```

This answers the inverse question: **near 100 °C, how much temperature change
does one ohm represent?**

## Why this matters

Suppose two measurement systems each have a resistance uncertainty of 0.01 Ω.
The corresponding temperature contribution depends on the RTD model's local
`dT/dR`. That is why `rtd-sensor` uses exact model sensitivity in its
[resistance uncertainty propagation](../measurement-uncertainty/resistance-propagation.md).

Sensitivity also helps explain why a Pt1000 gives a larger absolute resistance
change per degree than a Pt100 while sharing the same normalized platinum
characteristic.

## Compare Pt100 and Pt1000

```python
from rtd_sensor import pt100, pt1000

pt100_sensitivity = pt100.resistance_sensitivity_ohms_per_celsius(25.0)
pt1000_sensitivity = pt1000.resistance_sensitivity_ohms_per_celsius(25.0)
```

Because the Pt1000 has ten times the reference resistance, its absolute
resistance sensitivity is also roughly ten times larger for the same normalized
characteristic.

## How rtd-sensor calculates it

Built-in platinum and custom Callendar–Van Dusen models use the analytical
derivative of their active characteristic. Polynomial and piecewise polynomial
models differentiate their supplied polynomials analytically. Tabulated models
use the slope of the active linear-interpolation interval.

The package does not estimate these values by taking arbitrary finite
differences around the requested temperature.

## Common mistake: treating sensitivity as constant

A quick rule of thumb may use one nominal sensitivity value, but professional
uncertainty or resolution work should use sensitivity at the relevant operating
temperature when the model provides it.

## Related features

- [Pt100](../built-in-rtds/pt100.md)
- [Pt1000](../built-in-rtds/pt1000.md)
- [Resistance uncertainty propagation](../measurement-uncertainty/resistance-propagation.md)
- [Uncertainty budgets](../measurement-uncertainty/uncertainty-budgets.md)
