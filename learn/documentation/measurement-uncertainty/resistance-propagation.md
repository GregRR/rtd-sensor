---
title: Resistance uncertainty propagation
description: Propagate resistance standard uncertainty to temperature using an RTD model's exact local dT/dR sensitivity.
---

# Resistance uncertainty propagation

A resistance measurement uncertainty becomes a temperature uncertainty through
the local slope of the RTD's inverse characteristic.

For small uncertainties, first-order propagation is:

```text
u(T) ≈ |dT/dR| × u(R)
```

`rtd-sensor` gets `dT/dR` from the same active model used for the nominal
conversion.

## Example

```python
from rtd_sensor import pt100, uncertainty

propagated = uncertainty.propagate_resistance_uncertainty(
    100.0,
    0.01,
    model=pt100,
)

print(propagated.temperature_c)
print(propagated.temperature_sensitivity_celsius_per_ohm)
print(propagated.temperature_standard_uncertainty_c)
```

This helper propagates uncertainty in a **resistance measurement**. Uncertainty
associated with parameters estimated during calibration is a different contribution;
see [Fitted-model covariance propagation](fitted-model-propagation.md).

The returned `ResistanceUncertaintyPropagation` retains:

- resistance in ohms;
- converted temperature in °C;
- resistance standard uncertainty in ohms;
- local `dT/dR` sensitivity; and
- resulting temperature standard uncertainty.

## Use a calibrated model

```python
from rtd_sensor import uncertainty
from rtd_sensor.models import IEC60751RTDModel

probe = IEC60751RTDModel(r0_ohms=100.017)

result = uncertainty.propagate_resistance_uncertainty(
    119.42,
    0.02,
    model=probe,
)
```

This is why the uncertainty interface accepts structural models rather than
hard-coding Pt100.

## First-order limitation

This is a local linearization. If uncertainty is large enough that the curve's
nonlinearity across the uncertainty interval matters, a higher-order or Monte
Carlo method may be more appropriate. The current helper does not claim to solve
that case.

## Related features

- [Sensitivity](../using/sensitivity.md)
- [Uncertainty fundamentals](uncertainty.md)
- [Temperature uncertainty budgets](uncertainty-budgets.md)
