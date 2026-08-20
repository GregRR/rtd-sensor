---
title: Built-in sensor modules API
description: Quick API reference for rtd_sensor.pt100, pt500, pt1000, ni1000, ni1000_tk5000, and ni120.
---

# Built-in sensor modules

Public built-in modules:

```python
from rtd_sensor import ni1000, ni1000_tk5000, ni120, pt100, pt500, pt1000
```

Each exposes:

```text
R0_OHMS
MIN_TEMPERATURE_C
MAX_TEMPERATURE_C
celsius_to_resistance(temperature_c: float) -> float
resistance_to_celsius(resistance_ohms: float) -> float
resistance_sensitivity_ohms_per_celsius(temperature_c: float) -> float
temperature_sensitivity_celsius_per_ohm(temperature_c: float) -> float
```

## Version history

The Pt100 and Pt1000 APIs predate the 0.4.0 project/package rename. The table
therefore distinguishes original project availability from the current
`rtd_sensor` import path.

| Module | Conversion/constants introduced | Sensitivity API introduced | Current `rtd_sensor` module since |
| --- | --- | --- | --- |
| `pt100` | 0.1.0 (`pt100-core`) | 0.3.0 (`pt100-core`) | 0.4.0 |
| `pt1000` | 0.2.0 (`pt100-core`) | 0.3.0 (`pt100-core`) | 0.4.0 |
| `pt500` | 0.4.0 | 0.4.0 | 0.4.0 |
| `ni1000` | 0.4.0 | 0.4.0 | 0.4.0 |
| `ni1000_tk5000` | 0.4.0 | 0.4.0 | 0.4.0 |
| `ni120` | 0.4.0 | 0.4.0 | 0.4.0 |

The conversion/constants column covers `R0_OHMS`, the minimum/maximum
constants, `celsius_to_resistance()`, and `resistance_to_celsius()`. The
sensitivity column covers both local sensitivity functions.

## Built-in ranges

| Module | R0 | Range |
| --- | ---: | ---: |
| `pt100` | 100 Ω | -200..850 °C |
| `pt500` | 500 Ω | -200..850 °C |
| `pt1000` | 1000 Ω | -200..850 °C |
| `ni1000` | 1000 Ω | -60..250 °C |
| `ni1000_tk5000` | 1000 Ω | -60..250 °C |
| `ni120` | 120 Ω | -80..260 °C |

Minimal example:

```python
from rtd_sensor import pt100

t = pt100.resistance_to_celsius(119.3971)
r = pt100.celsius_to_resistance(50.0)
```

Out-of-range conversions raise `RTDOutOfRangeError`. Non-finite or invalid
scalar values may raise `ValueError` or `TypeError`.

See [Built-in RTDs](../documentation/built-in-rtds/index.md) for full details.
