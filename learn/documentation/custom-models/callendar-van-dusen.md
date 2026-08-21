---
title: Callendar–Van Dusen models
description: Build custom RTD models from documented Callendar–Van Dusen coefficients with validation, range enforcement, sensitivity, and provenance.
---

# Callendar–Van Dusen models

The **Callendar–Van Dusen (CVD) equation** is a mathematical form commonly used
to describe platinum RTD resistance as a function of temperature. Use
`CallendarVanDusenRTDModel` when a calibration certificate, manufacturer, or
other authoritative source gives you an explicit coefficient set.

## Example

```python
from rtd_sensor.models import CallendarVanDusenRTDModel

calibrated_probe = CallendarVanDusenRTDModel(
    r0_ohms=100.025,
    a=3.91e-3,
    b=-5.80e-7,
    c=-4.20e-12,
    minimum_temperature_c=-50.0,
    maximum_temperature_c=250.0,
    name="Probe SN-123",
    coefficient_source="Calibration certificate SN-123",
)
```

Then use it like any other RTD model:

```python
resistance_ohms = calibrated_probe.celsius_to_resistance(100.0)
temperature_c = calibrated_probe.resistance_to_celsius(resistance_ohms)
```

## The `C` coefficient and negative temperatures

The negative-temperature CVD form uses the `C` coefficient. `rtd-sensor` permits
`c=None` only when the model's complete declared range is at or above 0 °C. A
model that includes negative temperatures must provide the coefficient needed
to define that behavior.

## Model validation

Construction validates the supplied curve across the declared range. The curve
must remain:

- finite;
- positive in resistance; and
- strictly increasing so the inverse conversion is well defined.

Invalid definitions raise `InvalidRTDModelError` rather than creating a model
that may later return ambiguous temperatures.

## Coefficients do not imply IEC conformity

A custom coefficient set is not automatically described as IEC 60751 compliant.
Record where the numbers came from with `coefficient_source`, and make only the
conformity claim supported by that source.

## Example: positive-only model without C

```python
from rtd_sensor.models import CallendarVanDusenRTDModel

positive_range = CallendarVanDusenRTDModel(
    r0_ohms=100.0,
    a=3.9083e-3,
    b=-5.775e-7,
    minimum_temperature_c=0.0,
    maximum_temperature_c=200.0,
    coefficient_source="Documented coefficient set",
)
```

## Fit CVD parameters from calibration observations

**Introduced in:** rtd-sensor 0.7.0.

If you have calibration observations rather than a coefficient set, use
`rtd_sensor.fitting.fit_callendar_van_dusen()` and state which parameters should
be estimated:

```python
from rtd_sensor import fitting

fit = fitting.fit_callendar_van_dusen(
    (
        fitting.CalibrationObservation(-50.0, 80.31),
        fitting.CalibrationObservation(0.0, 100.025),
        fitting.CalibrationObservation(100.0, 138.56),
        fitting.CalibrationObservation(200.0, 175.90),
    ),
    fit_parameters=("r0_ohms", "a", "b", "c"),
)

model = fit.model
```

Parameters omitted from `fit_parameters` are fixed inputs and must be supplied
explicitly, except `C` may remain absent for a wholly non-negative model range.
Fitting `C` requires negative-temperature data. The fitter checks rank and scaled
conditioning before returning a model, and its covariance is reported in the
public `R0`, `A`, `B`, `C` parameter basis.

A fitted custom CVD curve is still not automatically IEC 60751 compliant. The
fit evidence says how the coefficients were estimated; standards or manufacturer
provenance must come from the actual calibration/source record.

## Related features

- [Characterized IEC 60751 models](characterized-iec60751.md)
- [Portable model definitions](portable-definitions.md)
- [Choosing a model](../using/choosing-model.md)
