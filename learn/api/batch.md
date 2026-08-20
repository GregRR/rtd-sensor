---
title: batch API
description: Quick API reference for rtd_sensor.batch iterable temperature/resistance conversion helpers.
---

# `rtd_sensor.batch`

The public batch API was **introduced in rtd-sensor 0.6.0**.

## `celsius_to_resistance`

**Introduced in:** rtd-sensor 0.6.0

```python
celsius_to_resistance(
    model: RTDModel,
    temperatures_c: Iterable[float],
) -> list[float]
```

Applies `model.celsius_to_resistance()` once to each input, in order. Returns an
eager list. The first scalar exception propagates unchanged; no partial list is
returned.

## `resistance_to_celsius`

**Introduced in:** rtd-sensor 0.6.0

```python
resistance_to_celsius(
    model: RTDModel,
    resistances_ohms: Iterable[float],
) -> list[float]
```

Equivalent behavior using `model.resistance_to_celsius()`.

Example:

```python
from rtd_sensor import batch, pt100

values = batch.celsius_to_resistance(pt100, [0.0, 50.0, 100.0])
```

See [Batch conversion](../documentation/using/batch.md).
