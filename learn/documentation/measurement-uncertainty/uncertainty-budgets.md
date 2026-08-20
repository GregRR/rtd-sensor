---
title: Temperature uncertainty budgets
description: Build inspectable RTD temperature uncertainty budgets from resistance propagation and named independent temperature-domain components.
---

# Temperature uncertainty budgets

`temperature_uncertainty_budget()` combines the propagated resistance
contribution with additional independent components that are **already expressed
as standard uncertainties in °C**.

The result remains inspectable rather than collapsing every contribution into
one unexplained number.

## Example with a named sensor contribution

```python
from rtd_sensor import pt100, tolerance, uncertainty

class_a_limit = tolerance.thermometer_tolerance_c(
    100.0,
    tolerance_class="A",
    construction="wire_wound",
)

# This rectangular distribution is an explicit user assumption.
sensor_u = uncertainty.standard_uncertainty_from_bound(
    class_a_limit,
    distribution="rectangular",
)

sensor_component = uncertainty.TemperatureUncertaintyComponent(
    name="Sensor class limit",
    standard_uncertainty_c=sensor_u,
    evaluation_method="B",
    source="IEC 60751 Class A limit modeled as rectangular",
)

budget = uncertainty.temperature_uncertainty_budget(
    pt100.celsius_to_resistance(100.0),
    0.01,
    model=pt100,
    additional_components=(sensor_component,),
    coverage_factor=2.0,
)

print(budget.combined_standard_uncertainty_c)
print(budget.expanded_uncertainty_c)
```

## What a component contains

`TemperatureUncertaintyComponent` stores:

- a human-readable `name`;
- `standard_uncertainty_c`;
- optional Type A/Type B evaluation method;
- optional source; and
- optional note.

The optional fields provide provenance only. All supplied numerical components
must already be standard uncertainties in °C.

## What the budget contains

`TemperatureUncertaintyBudget` retains the resistance propagation result,
additional named components, combined standard uncertainty, and—if requested—the
coverage factor and expanded uncertainty.

Its `temperature_c` property reports the nominal converted temperature from the
resistance contribution.

## Independence assumption

The current budget combines components as uncorrelated terms. It does not
support covariance matrices, coefficient covariance, effective degrees of
freedom, or Monte Carlo analysis.

If two uncertainty sources are materially correlated, do not treat this helper
as if it had modeled that covariance.

## Related features

- [IEC tolerance](tolerance.md)
- [Uncertainty fundamentals](uncertainty.md)
- [Resistance propagation](resistance-propagation.md)
