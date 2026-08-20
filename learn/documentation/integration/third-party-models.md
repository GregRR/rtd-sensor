---
title: Third-party RTD models
description: Supply third-party structural RTD model objects to rtd-sensor batch, measurement, and uncertainty workflows without registration or inheritance.
---

# Third-party models

A third-party model can participate in many `rtd-sensor` workflows without
being registered in the built-in catalog and without inheriting from a package
class.

The object must provide the structural methods required by the workflow.

## Minimal full-model example

```python
class ExampleModel:
    def celsius_to_resistance(self, temperature_c: float) -> float:
        return 100.0 + 0.4 * temperature_c

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        return (resistance_ohms - 100.0) / 0.4

    def resistance_sensitivity_ohms_per_celsius(
        self, temperature_c: float
    ) -> float:
        return 0.4

    def temperature_sensitivity_celsius_per_ohm(
        self, temperature_c: float
    ) -> float:
        return 2.5
```

This is only an illustrative linear model, not a documented physical RTD.

## Use it with batch conversion

```python
from rtd_sensor import batch

model = ExampleModel()
values = batch.celsius_to_resistance(model, [0.0, 10.0, 20.0])
```

## Use it with a resistance reader

```python
from rtd_sensor import measurement


class Reader:
    def read_resistance_ohms(self) -> float:
        return 110.0


temperature_c = measurement.read_temperature_celsius(
    Reader(),
    model=model,
)
```

## Use it with uncertainty propagation

If it provides `resistance_to_celsius()` and
`temperature_sensitivity_celsius_per_ohm()`, it can satisfy the narrower
uncertainty protocol as well.

## What rtd-sensor does not do for third-party models

The package does not automatically verify the scientific provenance, range,
monotonicity, exception semantics, or numerical accuracy of an arbitrary
third-party object. Its exceptions also propagate unchanged rather than being
wrapped as package-owned model errors.

Use the built-in model classes when you want `rtd-sensor`'s own validation
semantics for CVD, polynomial, piecewise-polynomial, or tabulated definitions.
