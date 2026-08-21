---
title: Fitted-model covariance propagation
description: Propagate calibration-fit parameter covariance into predicted RTD resistance or inferred temperature uncertainty without mixing it automatically into the rest of the measurement budget.
---

# Fitted-model covariance propagation

**Planned for:** rtd-sensor 0.7.0.

A fitted RTD model does not have perfectly known parameters. When a supported
calibration fit retains parameter covariance, `rtd-sensor` can propagate that
covariance into either the resistance predicted by the fitted curve at a selected
temperature or the temperature inferred from a fixed resistance.

For a model prediction `R(T, θ)`, covariance propagation is:

```text
u²_fit(R) = J Cov(θ) Jᵀ
```

`J` is the vector of resistance sensitivities with respect to the fitted
parameters. The full covariance matrix is used, including off-diagonal terms.
Those terms matter because fitted parameters are generally correlated. For the
currently supported IEC-R0 and polynomial fit-space parameterizations, resistance
is linear in the retained fitted parameters, so this resistance covariance
transformation is exact at fixed temperature under the fit model.

## IEC 60751 R0 example

```python
from rtd_sensor import fitting, uncertainty

fit = fitting.fit_iec60751_r0(
    (
        fitting.CalibrationObservation(
            0.0,
            100.037,
            standard_uncertainty_ohms=0.01,
        ),
    ),
    minimum_temperature_c=-50.0,
    maximum_temperature_c=250.0,
)

propagated = uncertainty.propagate_fit_covariance_to_resistance(
    100.0,
    fit_result=fit,
)

print(propagated.resistance_ohms)
print(propagated.resistance_standard_uncertainty_ohms)
```

For the fixed IEC characteristic, `R(T) = R0 × rho(T)`, so the parameter
sensitivity is simply `dR/dR0 = rho(T)`.

## Polynomial example

Polynomial covariance is retained in the resistance-space basis

```text
R(T) = a0 + a1*x + a2*x² + ...
x = T - reference_temperature_c
```

so the sensitivity vector is directly:

```text
J = (1, x, x², ...)
```

That is why the covariance milestone retained this basis instead of pretending
that the normalized deployable polynomial coefficients were independently fitted.

```python
fit = fitting.fit_polynomial(
    (
        fitting.CalibrationObservation(0.0, 100.0, standard_uncertainty_ohms=0.02),
        fitting.CalibrationObservation(50.0, 119.4, standard_uncertainty_ohms=0.02),
        fitting.CalibrationObservation(100.0, 138.5, standard_uncertainty_ohms=0.02),
    ),
    degree=1,
)

propagated = uncertainty.propagate_fit_covariance_to_resistance(
    25.0,
    fit_result=fit,
)

print(propagated.parameter_sensitivity_vector)
print(propagated.resistance_variance_ohms_squared)
```

## Propagate into inferred temperature

For an inverse conversion, the measured resistance is held fixed while the
fitted parameters vary. If the model satisfies

```text
R_model(T, θ) = R_measured
```

implicit differentiation gives the fitted-parameter temperature sensitivity:

```text
dT/dθ = -(dR/dθ) * (dT/dR)
```

The full covariance is then propagated with

```text
u²_fit(T) = J_T Cov(θ) J_Tᵀ
```

```python
resistance = fit.model.celsius_to_resistance(25.0)

temperature_propagated = uncertainty.propagate_fit_covariance_to_temperature(
    resistance,
    fit_result=fit,
)

print(temperature_propagated.temperature_c)
print(temperature_propagated.temperature_standard_uncertainty_c)
print(temperature_propagated.parameter_sensitivity_vector)
```

Unlike the forward resistance transformation above, this inverse result is a
**first-order local linearization** because inferred temperature is generally
nonlinear in the fitted parameters. The result retains both the resistance-side
parameter sensitivity vector and the derived temperature-side vector so the
calculation can be inspected.

## What this uncertainty means

This result describes the uncertainty associated with the **fitted parameters
under the regression assumptions**. It is not a complete uncertainty budget.
It does not automatically include:

- uncertainty in a later resistance measurement;
- uncertainty in the reference temperatures used for calibration;
- sensor drift;
- self-heating;
- lead-wire effects;
- IEC tolerance assumptions; or
- other acquisition/systematic effects.

Neither propagation function automatically inserts this contribution into
`temperature_uncertainty_budget()`. Whether two contributions are independent
is a property of the actual measurement/calibration process, not something the
package can infer safely from two numbers.

## Covariance must be available

A successful fit does not always have estimable parameter covariance. For
example, an unweighted saturated fit has no residual degrees of freedom from
which to estimate the unknown residual variance scale. If covariance is
unavailable, propagation fails explicitly and reports the reason retained by
the fit evidence rather than returning zero uncertainty.

## Forward exactness and inverse local linearization

The forward resistance covariance transformation is exact for the currently
supported linear-in-parameter fit representations at fixed temperature. The
inverse temperature propagation is first-order/local because it uses the local
implicit sensitivity at the converted temperature. Monte Carlo or other methods
may eventually be appropriate when parameter uncertainty is large enough that
inverse-model nonlinearity matters.

## Related pages

- [Calibration fitting](../custom-models/calibration-fitting.md)
- [Resistance uncertainty propagation](resistance-propagation.md)
- [Temperature uncertainty budgets](uncertainty-budgets.md)
