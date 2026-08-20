---
title: Characterized IEC 60751 models
description: Use IEC60751RTDModel when an IEC PT-385 platinum RTD has a characterized R0 rather than only its nominal Pt100/Pt500/Pt1000 value.
---

# Characterized IEC 60751 models

Use `IEC60751RTDModel` when you have an IEC 60751 PT-385 platinum RTD whose
reference resistance at 0 °C has been individually characterized.

A nominal Pt100 uses `R0 = 100 Ω`. A particular probe might instead have a
measured or certified value such as `100.017 Ω`. Keeping that real `R0` can make
the model represent the individual probe more closely while retaining the
standard PT-385 curve shape.

## Example: characterized Pt100

```python
from rtd_sensor.models import IEC60751RTDModel

probe = IEC60751RTDModel(
    r0_ohms=100.017,
    name="Calibrated probe A",
    minimum_temperature_c=-50.0,
    maximum_temperature_c=250.0,
)

temperature_c = probe.resistance_to_celsius(119.42)
```

## Example: characterized Pt1000

The class is not limited to nominal 100 Ω sensors:

```python
from rtd_sensor.models import IEC60751RTDModel

probe = IEC60751RTDModel(
    r0_ohms=1000.24,
    name="Characterized Pt1000",
    minimum_temperature_c=0.0,
    maximum_temperature_c=180.0,
)
```

The curve is still IEC 60751 PT-385; only the reference resistance and declared
range differ.

## Why declare a range?

A calibration or application may justify a narrower interval than the complete
IEC characteristic. The model enforces the range you declare so downstream
code does not silently use the characterization outside its intended scope.

Defaults are available for the full IEC range, but for an individually
characterized sensor it is usually better to record the range actually supported
by the source or calibration.

## What this model does not mean

Providing a characterized `R0` does not by itself prove that a physical probe
conforms to every IEC 60751 construction, tolerance, or test requirement. It is
a numerical model of the PT-385 characteristic with your selected reference
resistance.

## Fit `R0` from calibration observations

For rtd-sensor 0.7.0, `rtd_sensor.fitting.fit_iec60751_r0()` estimates `R0`
from one or more temperature/resistance calibration observations while holding
the PT-385 characteristic fixed. It returns an `IEC60751RTDModel` plus separate
immutable fit evidence. An explicitly declared model range describes intended
applicability and need not contain the observation temperatures; the evidence
retains the actual observation span independently.

This is different from fitting arbitrary Callendar–Van Dusen coefficients: the
standard curve shape is assumed, and only its reference-resistance scale is
estimated.

## Portable deployment

`IEC60751RTDModel` is supported by the versioned
[portable model-definition format](portable-definitions.md), so a characterized
model can be serialized and reconstructed without repeating the characterization
process.

## Related features

- [Pt100](../built-in-rtds/pt100.md)
- [Callendar–Van Dusen models](callendar-van-dusen.md)
- [IEC 60751 tolerance classes](../measurement-uncertainty/tolerance.md)
