---
title: simulation API
description: Quick API reference for rtd_sensor.simulation readers, built-in RTD identity selection, compatibility imports, and version history.
---

# `rtd_sensor.simulation`

The simulation API began in project release 0.1.0 under `pt100-core` / `rtd`.
The current `rtd_sensor.simulation` import path began with rtd-sensor 0.4.0.

## `RTDType`

**Introduced in:** project release 0.2.0 (`pt100-core`); current
`rtd_sensor.simulation` path since 0.4.0.

**Changed in:** rtd-sensor 0.4.0 — generalized from a closed `Literal[...]`
union to a string alias backed by runtime built-in-model validation.

RTD model identity is spelled as a string alias:

```text
RTDType = str
```

## `SUPPORTED_RTD_TYPES`

**Introduced in:** rtd-sensor 0.4.0

Public built-in identities are available from:

```text
SUPPORTED_RTD_TYPES: tuple[RTDType, ...]
```

Pt100 is the default `rtd_type` for simulation readers.

## `FixedResistanceReader`

**Introduced in:** project release 0.1.0 (`pt100-core`); current
`rtd_sensor.simulation` path since 0.4.0.

```python
FixedResistanceReader(
    resistance_ohms: float,
    rtd_type: str = "pt100",
)
```

## `ResistanceSequenceReader`

**Introduced in:** project release 0.1.0 (`pt100-core`); current
`rtd_sensor.simulation` path since 0.4.0.

```python
ResistanceSequenceReader(
    readings_ohms: Sequence[float],
    repeat: bool = False,
    rtd_type: str = "pt100",
)
```

`read_resistance_ohms()` raises `StopIteration` when a non-repeating sequence is
exhausted.

## `TemperatureSequenceReader`

**Introduced in:** project release 0.1.0 (`pt100-core`); current
`rtd_sensor.simulation` path since 0.4.0.

```python
TemperatureSequenceReader(
    temperatures_c: Sequence[float],
    repeat: bool = False,
    rtd_type: str = "pt100",
)
```

## `NoisyTemperatureReader`

**Introduced in:** project release 0.1.0 (`pt100-core`); current
`rtd_sensor.simulation` path since 0.4.0.

```python
NoisyTemperatureReader(
    temperature_c: float,
    noise_standard_deviation_c: float = 0.05,
    seed: int | None = None,
    rtd_type: str = "pt100",
)
```

Gaussian noise is applied in the temperature domain before conversion to ideal
RTD resistance.

## Compatibility re-exports

`ResistanceReader` and `read_temperature_celsius` originated in the simulation
API in project release 0.1.0. Since rtd-sensor 0.5.0, the canonical
hardware-neutral definitions live in `rtd_sensor.measurement`, and
`rtd_sensor.simulation` preserves them as compatibility re-exports.

See [Simulation readers](../documentation/simulation-testing/simulation.md).
