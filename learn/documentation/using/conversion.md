---
title: Temperature and resistance conversion
description: Convert RTD temperature to resistance and resistance to temperature with rtd-sensor built-in and custom models.
---

# Temperature ↔ resistance

Every supported RTD model provides the same two core operations:

- `celsius_to_resistance()` converts temperature in °C to resistance in Ω.
- `resistance_to_celsius()` converts resistance in Ω to temperature in °C.

## Built-in Pt100 example

```python
from rtd_sensor import pt100

resistance_ohms = pt100.celsius_to_resistance(100.0)
temperature_c = pt100.resistance_to_celsius(resistance_ohms)

print(resistance_ohms)
print(temperature_c)
```

The first call calculates what an ideal built-in Pt100 model predicts at
100 °C. The second converts that model resistance back to temperature.

## Converting a measured resistance

Suppose a hardware layer has already produced a compensated Pt100 resistance of
119.3971 Ω:

```python
from rtd_sensor import pt100

measured_resistance_ohms = 119.3971
temperature_c = pt100.resistance_to_celsius(measured_resistance_ohms)
```

`rtd-sensor` does not know how the resistance was acquired. It may have come from
a MAX31865, a laboratory bridge, a DAQ, or a simulated reader. The conversion
layer only needs the resistance value and the correct RTD model.

## The same API works with other built-ins

```python
from rtd_sensor import ni1000_tk5000, pt1000

pt1000_r = pt1000.celsius_to_resistance(50.0)
ni1000_r = ni1000_tk5000.celsius_to_resistance(50.0)
```

The function names are intentionally identical. What changes is the model
characteristic behind them.

## Configurable models use methods

A configurable model object exposes the same operations as methods:

```python
from rtd_sensor.models import IEC60751RTDModel

probe = IEC60751RTDModel(
    r0_ohms=100.017,
    minimum_temperature_c=-50.0,
    maximum_temperature_c=250.0,
)

temperature_c = probe.resistance_to_celsius(119.42)
```

This lets code work with a built-in module, a calibrated model object, or a
third-party structural model through the same conceptual interface.

## Common mistakes

### Using resistance from the wrong RTD type

A 1000 Ω nickel RTD is not automatically interchangeable with a Pt1000. The
nominal resistance alone does not identify the resistance-temperature curve.
Use [model discovery](catalog.md) or the sensor's documentation to identify the
correct characteristic.

### Treating hardware output as element resistance when it is not

The value passed to `rtd-sensor` should represent the best available estimate of
the **RTD sensing element's resistance**. Lead resistance and acquisition-system
corrections belong to the hardware/acquisition layer.

### Ignoring model range

Models reject temperatures or resistances outside their declared range instead
of silently extrapolating. See [Valid ranges and errors](ranges-errors.md).

## Related features

- [Batch conversion](batch.md)
- [Sensitivity](sensitivity.md)
- [Built-in RTDs](../built-in-rtds/index.md)
- [Custom & calibrated models](../custom-models/index.md)
- [Hardware/acquisition boundary](../measurement-uncertainty/acquisition-boundary.md)
