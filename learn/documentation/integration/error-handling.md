---
title: Error handling
description: Handle rtd-sensor package-owned domain errors while preserving the distinction between RTD model failures, invalid inputs, and hardware acquisition failures.
---

# Error handling

A measurement application benefits from knowing **which layer failed**. An ADC
communication error is not the same as a valid resistance that falls outside an
RTD model's range.

`rtd-sensor` therefore keeps its package-owned RTD exceptions small and does not
translate arbitrary acquisition failures into model errors.

**Public exception taxonomy available since:** rtd-sensor 0.5.0. Portable-model
and calibration-fitting exceptions were added in 0.6.0; calibration
experiment-design failures are added in 0.9.0.

## Catch a specific conversion problem

```python
from rtd_sensor import exceptions, pt100

try:
    temperature_c = pt100.resistance_to_celsius(measured_resistance)
except exceptions.RTDOutOfRangeError:
    # Resistance was supplied, but it is outside this RTD model's range.
    ...
```

## Catch package-owned RTD domain failures

```python
from rtd_sensor import exceptions

try:
    ...
except exceptions.RTDError as exc:
    ...
```

Use this when your application wants one branch for package-owned RTD domain
errors without also catching unrelated hardware exceptions.

## Public exception roles

| Exception | Typical meaning |
| --- | --- |
| `RTDOutOfRangeError` | Temperature or resistance lies outside a model's supported range |
| `UnknownRTDModelError` | Unknown canonical built-in model ID |
| `InvalidRTDModelError` | Custom model definition fails scientific/numerical validation |
| `InvalidPortableModelDefinitionError` | Portable artifact is malformed, unsupported, or invalid |
| `RTDFitError` | Calibration fit cannot produce an acceptable model |
| `RTDExperimentDesignError` | Calibration experiment planning cannot produce a valid design |
| `RTDModelSelectionError` | Conflicting or unsupported model-selection declarations |

Several retain compatibility with conventional Python exception families: for
example, package-owned model/range/fitting errors that historically behaved as
value problems remain compatible with `ValueError`, while unknown model IDs are
compatible with `KeyError`.

## Invalid scalar input

Not every bad scalar is an RTD domain exception. Non-finite or wrong-type inputs
may raise `ValueError` or `TypeError` according to the public API. Boolean
physical values are explicitly rejected.

## Acquisition exceptions remain acquisition exceptions

```python
from rtd_sensor import measurement, pt100

# If hardware_reader.read_resistance_ohms() raises a driver-specific SPI error,
# that error propagates. It is not converted into RTDOutOfRangeError.
temperature_c = measurement.read_temperature_celsius(
    hardware_reader,
    model=pt100,
)
```

This allows the application to distinguish “could not acquire resistance” from
“acquired resistance does not fit the selected model.”

## Related features

- [Valid ranges and errors](../using/ranges-errors.md)
- [Hardware/acquisition boundary](../measurement-uncertainty/acquisition-boundary.md)
- [API: exceptions](../../api/exceptions.md)
