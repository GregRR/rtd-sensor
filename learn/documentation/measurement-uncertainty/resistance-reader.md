---
title: ResistanceReader composition
description: Compose any hardware-neutral resistance source with a built-in, calibrated, or third-party RTD model using rtd_sensor.measurement.
---

# ResistanceReader composition

`ResistanceReader` is a tiny structural protocol for anything that can return
one RTD resistance value in ohms:

```python
from rtd_sensor.measurement import ResistanceReader


def read_resistance(reader: ResistanceReader) -> float:
    return reader.read_resistance_ohms()
```

An implementation does **not** need to inherit from an `rtd-sensor` base class.
It simply needs a compatible `read_resistance_ohms()` method.

**Hardware-neutral measurement API available since:** rtd-sensor 0.5.0.

## Compose a neutral reader with a model

```python
from rtd_sensor import measurement, pt100


class MyReader:
    def read_resistance_ohms(self) -> float:
        return 119.3971


reader = MyReader()
temperature_c = measurement.read_temperature_celsius(reader, model=pt100)
```

This is the preferred path for new hardware and application code because the
explicit model can be a built-in, characterized model, fitted model, or
third-party structural model.

## Built-in ID convenience

You may select a verified built-in by canonical ID:

```python
temperature_c = measurement.read_temperature_celsius(
    reader,
    rtd_type="pt1000",
)
```

A neutral reader defaults to Pt100 if neither `model` nor `rtd_type` is
provided, preserving historical simulation behavior. For new production code,
an explicit model selection is usually clearer.

## Model-aware readers

The built-in simulation readers declare an `rtd_type`. If no explicit selection
is supplied, that declared built-in type is honored.

Conflicting declarations are rejected. For example, a reader declaring
`pt1000` cannot be explicitly interpreted as `pt100`.

An explicit model object cannot be combined with a reader-declared `rtd_type`,
because the structural model protocol deliberately does not carry identity
metadata that would prove those two declarations agree.

## Exception behavior

Acquisition exceptions from `reader.read_resistance_ohms()` propagate unchanged.
Conversion exceptions from the model also propagate unchanged. The measurement
composition layer does not disguise a hardware failure as a model failure.

## Related features

- [Hardware/acquisition boundary](acquisition-boundary.md)
- [Simulation](../simulation-testing/simulation.md)
- [RTDModel interface](../integration/rtdmodel-interface.md)
