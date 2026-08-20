---
title: Valid ranges and errors
description: Understand rtd-sensor model ranges, boundary behavior, invalid inputs, and public exceptions.
---

# Valid ranges and errors

An RTD model is only valid over the temperature range it declares. `rtd-sensor`
enforces that range rather than silently extrapolating a curve into territory
where the model has not been verified.

## Example: Pt100 range

The built-in Pt100 characteristic is supported from -200 °C through 850 °C.
The endpoints are valid:

```python
from rtd_sensor import pt100

low_r = pt100.celsius_to_resistance(-200.0)
high_r = pt100.celsius_to_resistance(850.0)
```

A temperature below or above the supported range raises
`RTDOutOfRangeError`:

```python
from rtd_sensor import exceptions, pt100

try:
    pt100.celsius_to_resistance(900.0)
except exceptions.RTDOutOfRangeError as exc:
    print(exc)
```

Resistance-to-temperature conversion applies the equivalent model limits in
resistance space.

## Range is a model property, not a package guess

A configurable model can intentionally declare a narrower range:

```python
from rtd_sensor.models import IEC60751RTDModel

probe = IEC60751RTDModel(
    r0_ohms=100.017,
    minimum_temperature_c=0.0,
    maximum_temperature_c=150.0,
)
```

Even though the IEC PT-385 characteristic itself extends beyond that interval,
this model says that **this particular definition** is intended only from
0 °C to 150 °C.

## Characteristic range versus physical sensor limits

The built-in range describes the mathematical characteristic represented by the
package. A real probe, cable, sheath, connector, or transmitter may have a
narrower operating or conformity range. Always apply the physical device limits
from the sensor manufacturer as a separate constraint.

## Invalid numeric input

Physical numeric inputs must be finite where the API requires a physical
quantity. Boolean values are deliberately rejected even though Python normally
treats `bool` as a subclass of `int`.

This prevents mistakes such as:

```python
from rtd_sensor import pt100

# Rejected rather than silently treating True as 1.0 °C.
pt100.celsius_to_resistance(True)
```

## Package-owned exception hierarchy

For stable branching on RTD domain failures, import `rtd_sensor.exceptions`.
Important public exceptions include:

- `RTDOutOfRangeError` — conversion is outside a model's valid range.
- `UnknownRTDModelError` — an unknown built-in model ID was requested.
- `InvalidRTDModelError` — a custom model definition is scientifically invalid.
- `InvalidPortableModelDefinitionError` — a portable artifact is malformed, unsupported, or scientifically invalid.
- `RTDFitError` — calibration fitting cannot produce an acceptable model.
- `RTDModelSelectionError` — model selection declarations conflict or are incomplete.

All package-owned RTD domain exceptions derive from `RTDError`. Acquisition
exceptions from hardware readers and arbitrary exceptions from third-party
models are not automatically wrapped.

## Why fail instead of extrapolate?

Returning a plausible-looking temperature is not always safer than raising an
error. A value outside a supported characteristic can mean a bad measurement,
open or short circuit, wrong RTD type, or a real temperature beyond the model's
scope. `rtd-sensor` leaves that decision visible to the application.

## Related features

- [Error handling in applications](../integration/error-handling.md)
- [Choosing the right model](choosing-model.md)
- [Built-in RTDs](../built-in-rtds/index.md)
