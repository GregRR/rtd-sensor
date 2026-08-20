---
title: Simulation readers
description: Simulate fixed, sequenced, temperature-derived, or noisy RTD resistance readings with rtd_sensor.simulation.
---

# Simulation readers

All simulation readers ultimately expose **resistance in ohms**. That mirrors
the hardware-neutral acquisition boundary and makes them useful for application
tests before real hardware is available.

Pt100 is the default for backward compatibility. Use `rtd_type` to select a
different verified built-in.

## Fixed resistance

```python
from rtd_sensor import simulation

reader = simulation.FixedResistanceReader(119.3971, rtd_type="pt100")

print(reader.read_resistance_ohms())
print(simulation.read_temperature_celsius(reader))
```

Every call returns the same resistance.

## Resistance sequence

```python
reader = simulation.ResistanceSequenceReader(
    [100.0, 109.73, 119.3971],
    rtd_type="pt100",
)

first = reader.read_resistance_ohms()
second = reader.read_resistance_ohms()
```

A non-repeating reader raises `StopIteration` when the sequence is exhausted.
Use `repeat=True` to cycle back to the beginning.

## Temperature sequence

Sometimes it is easier to describe a test in temperatures and let the simulator
create the model resistance:

```python
reader = simulation.TemperatureSequenceReader(
    [20.0, 40.0, 60.0],
    rtd_type="pt1000",
)

for _ in range(3):
    print(simulation.read_temperature_celsius(reader))
```

The reader converts each configured temperature through the selected built-in
RTD model and exposes the resulting resistance.

## Reproducibly noisy temperature

```python
reader = simulation.NoisyTemperatureReader(
    temperature_c=25.0,
    noise_standard_deviation_c=0.05,
    seed=42,
    rtd_type="pt100",
)

samples = [reader.read_resistance_ohms() for _ in range(5)]
```

Gaussian noise is applied in the **temperature domain first**, then that
simulated temperature is converted to ideal model resistance. Supplying the same
seed produces the same pseudo-random sequence.

The simulator does not claim this is a complete physical sensor-noise model. It
is a convenient, controlled source for software tests.

## Supported RTD identities

```python
from rtd_sensor import simulation

print(simulation.SUPPORTED_RTD_TYPES)
```

The tuple is derived from the same built-in registry as the package models.
Unsupported strings are rejected at runtime.

## Reader identity is fixed

A built-in simulation reader resolves its RTD type when constructed. Its
`rtd_type` cannot later be changed to a different characteristic while retaining
the old cached model.

## Preferred composition for new code

`simulation.read_temperature_celsius` is a compatibility re-export of
`measurement.read_temperature_celsius`. For new application or hardware code,
prefer the neutral measurement API when selecting an explicit model object:

```python
from rtd_sensor import measurement, pt1000


class NeutralReader:
    def read_resistance_ohms(self) -> float:
        return 1097.3


temperature_c = measurement.read_temperature_celsius(
    NeutralReader(),
    model=pt1000,
)
```

Use a **neutral** reader with an explicit model. A simulation reader that already
declares `rtd_type` cannot be combined with an explicit model object because the
measurement layer cannot prove the two identities agree.

## Related features

- [ResistanceReader composition](../measurement-uncertainty/resistance-reader.md)
- [Hardware/acquisition boundary](../measurement-uncertainty/acquisition-boundary.md)
- [API: simulation](../../api/simulation.md)
