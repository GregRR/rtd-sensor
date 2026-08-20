---
title: RTDModel interface
description: Write application code against rtd-sensor's structural RTDModel protocol instead of one concrete RTD class.
---

# RTDModel interface

Application code that works with more than one RTD characteristic can type
against `rtd_sensor.models.RTDModel` instead of depending on a specific built-in
module or model class.

`RTDModel` is a **structural protocol**. An object qualifies by providing the
required behavior; it does not need to inherit from an `rtd-sensor` base class.

**Public `RTDModel` protocol available since:** rtd-sensor 0.5.0.

## Required operations

A full RTD model provides:

```text
celsius_to_resistance(temperature_c) -> resistance_ohms
resistance_to_celsius(resistance_ohms) -> temperature_c
resistance_sensitivity_ohms_per_celsius(temperature_c) -> dR/dT
temperature_sensitivity_celsius_per_ohm(temperature_c) -> dT/dR
```

## Example function accepting any model

```python
from rtd_sensor import pt100
from rtd_sensor.models import IEC60751RTDModel, RTDModel


def convert_temperature(model: RTDModel, resistance_ohms: float) -> float:
    return model.resistance_to_celsius(resistance_ohms)


nominal = convert_temperature(pt100, 119.3971)

probe = IEC60751RTDModel(r0_ohms=100.017)
characterized = convert_temperature(probe, 119.42)
```

The same application function accepts the built-in module and the configurable
object because both satisfy the structural interface.

## Why identity is not part of RTDModel

The protocol describes **numerical behavior**, not model identity or provenance.
Built-in identity lives in the [catalog](../using/catalog.md). A third-party or
calibrated object may be perfectly usable without being globally registered.

That separation also prevents application code from assuming that every
numerical model has a canonical built-in ID.

## Narrower uncertainty interface

`rtd_sensor.uncertainty.RTDUncertaintyModel` is a narrower structural interface
for operations that need only resistance-to-temperature conversion and `dT/dR`.
Every full `RTDModel` satisfies that narrower requirement.

## Related features

- [Third-party models](third-party-models.md)
- [ResistanceReader](../measurement-uncertainty/resistance-reader.md)
- [Batch conversion](../using/batch.md)
