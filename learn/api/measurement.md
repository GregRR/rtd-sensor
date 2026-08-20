---
title: measurement API
description: Quick API reference for rtd_sensor.measurement ResistanceReader and read_temperature_celsius composition.
---

# `rtd_sensor.measurement`

The hardware-neutral measurement API was **introduced in rtd-sensor 0.5.0**.
The older `simulation` compatibility imports remain available.

## `ResistanceReader`

**Introduced in:** rtd-sensor 0.5.0 in the hardware-neutral
`rtd_sensor.measurement` module. The earlier simulation-specific protocol dates
to project release 0.1.0.

Structural protocol:

```python
class ResistanceReader(Protocol):
    def read_resistance_ohms(self) -> float: ...
```

No inheritance is required for compatible implementations.

## `read_temperature_celsius`

**Introduced in:** rtd-sensor 0.5.0 in the hardware-neutral
`rtd_sensor.measurement` module. A simulation-focused predecessor existed from
project release 0.1.0.

```python
read_temperature_celsius(
    reader: ResistanceReader,
    *,
    model: RTDModel | None = None,
    rtd_type: str | None = None,
) -> float
```

Selection rules:

- `model` is preferred for new code and accepts any structural RTD model.
- `rtd_type` selects a canonical built-in ID.
- A neutral reader defaults to Pt100 when neither is supplied.
- `model` and `rtd_type` cannot both be supplied.
- An explicit model cannot be combined with a reader that itself declares
  `rtd_type`.
- A reader-declared `rtd_type` must agree with an explicit `rtd_type`.

Selection conflicts raise `RTDModelSelectionError`. Reader and model exceptions
otherwise propagate unchanged.

See [ResistanceReader composition](../documentation/measurement-uncertainty/resistance-reader.md).
