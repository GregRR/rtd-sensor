---
title: Batch conversion
description: Convert iterables of RTD temperatures or resistances with rtd_sensor.batch while preserving scalar behavior and exceptions.
---

# Batch conversion

`rtd_sensor.batch` applies an RTD model's scalar conversion method to each value
in an ordered iterable and returns an ordinary Python list.

It adds **no NumPy dependency** and accepts one-pass iterables such as
generators.

**Available since:** rtd-sensor 0.6.0.

## Convert several temperatures

```python
from rtd_sensor import batch, pt100

temperatures_c = [0.0, 25.0, 50.0, 100.0]
resistances_ohms = batch.celsius_to_resistance(pt100, temperatures_c)
```

## Convert the values back

```python
round_trip_c = batch.resistance_to_celsius(pt100, resistances_ohms)
```

## Use a generator

The iterable is consumed once and in order:

```python
from rtd_sensor import batch, pt1000

temperatures = (value for value in range(0, 101, 10))
resistances = batch.celsius_to_resistance(pt1000, temperatures)
```

The result is still a normal list.

## Use a custom model

The helpers work with any object satisfying the structural RTD model interface:

```python
from rtd_sensor import batch
from rtd_sensor.models import IEC60751RTDModel

probe = IEC60751RTDModel(r0_ohms=100.017)
values = batch.celsius_to_resistance(probe, [0.0, 50.0, 100.0])
```

## Fail-fast behavior

Scalar conversion remains authoritative. If one element raises an exception,
the same exception propagates from the batch call and **no partial result list
is returned**.

That matters when you want batch behavior to match the exact range and
validation semantics of a model rather than silently skipping bad values.

## When not to use it

`rtd_sensor.batch` is intentionally small. It does not provide array broadcasting,
masking, vectorized error reporting, or DataFrame integration. If you already
work in NumPy or pandas, you can still call the scalar API in whatever vectorized
or table workflow fits your application.

## Related features

- [Temperature ↔ resistance](conversion.md)
- [RTDModel interface](../integration/rtdmodel-interface.md)
- [API: batch](../../api/batch.md)
