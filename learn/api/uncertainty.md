---
title: uncertainty API
description: Quick API reference for rtd_sensor.uncertainty standard uncertainty helpers, propagation records, protocols, and temperature budgets.
---

# `rtd_sensor.uncertainty`

All public uncertainty symbols were **introduced in project release 0.3.0**
under `pt100-core` / `rtd`. The current `rtd_sensor.uncertainty` import path
began with rtd-sensor 0.4.0.

## Type aliases

**Introduced in:** project release 0.3.0 (`pt100-core`); current import path
since rtd-sensor 0.4.0.

```text
BoundDistribution = Literal["rectangular", "triangular"]
EvaluationMethod = Literal["A", "B"]
```

## `RTDUncertaintyModel`

**Introduced in:** project release 0.3.0 (`pt100-core`); current import path
since rtd-sensor 0.4.0.

A structural protocol requiring resistance-to-temperature conversion and local
`dT/dR` sensitivity. Full `RTDModel` objects satisfy this narrower uncertainty
interface.

## Scalar helpers

All four scalar helpers were **introduced in project release 0.3.0**; current
`rtd_sensor.uncertainty` paths date to rtd-sensor 0.4.0.

```python
standard_uncertainty_from_bound(
    half_width: float,
    *,
    distribution: BoundDistribution,
) -> float
```

```python
standard_uncertainty_from_expanded(
    expanded_uncertainty_value: float,
    *,
    coverage_factor: float,
) -> float
```

```python
combine_independent_standard_uncertainties(
    *standard_uncertainties: float,
) -> float
```

```python
expanded_uncertainty(
    combined_standard_uncertainty: float,
    *,
    coverage_factor: float,
) -> float
```

## `TemperatureUncertaintyComponent`

**Introduced in:** project release 0.3.0 (`pt100-core`); current import path
since rtd-sensor 0.4.0.

```python
TemperatureUncertaintyComponent(
    name: str,
    standard_uncertainty_c: float,
    evaluation_method: Literal["A", "B"] | None = None,
    source: str | None = None,
    note: str | None = None,
)
```

## `ResistanceUncertaintyPropagation`

**Introduced in:** project release 0.3.0 (`pt100-core`); current import path
since rtd-sensor 0.4.0.

Result fields:

```text
resistance_ohms: float
temperature_c: float
resistance_standard_uncertainty_ohms: float
temperature_sensitivity_celsius_per_ohm: float
temperature_standard_uncertainty_c: float
```

## `propagate_resistance_uncertainty`

**Introduced in:** project release 0.3.0 (`pt100-core`); current import path
since rtd-sensor 0.4.0.

```python
propagate_resistance_uncertainty(
    resistance_ohms: float,
    resistance_standard_uncertainty_ohms: float,
    *,
    model: RTDUncertaintyModel,
) -> ResistanceUncertaintyPropagation
```

## `TemperatureUncertaintyBudget`

**Introduced in:** project release 0.3.0 (`pt100-core`); current import path
since rtd-sensor 0.4.0.

Result fields:

```text
resistance: ResistanceUncertaintyPropagation
additional_components: tuple[TemperatureUncertaintyComponent, ...]
combined_standard_uncertainty_c: float
coverage_factor: float | None
expanded_uncertainty_c: float | None
temperature_c: float  # read-only property
```

## `temperature_uncertainty_budget`

**Introduced in:** project release 0.3.0 (`pt100-core`); current import path
since rtd-sensor 0.4.0.

```python
temperature_uncertainty_budget(
    resistance_ohms: float,
    resistance_standard_uncertainty_ohms: float,
    *,
    model: RTDUncertaintyModel,
    additional_components: Iterable[TemperatureUncertaintyComponent] = (),
    coverage_factor: float | None = None,
) -> TemperatureUncertaintyBudget
```

## `FitCovarianceResistancePropagation`

**Planned for:** rtd-sensor 0.7.0.

Result fields:

```text
temperature_c: float
resistance_ohms: float
parameter_covariance: FitParameterCovariance
parameter_sensitivity_vector: tuple[float, ...]
resistance_variance_ohms_squared: float
resistance_standard_uncertainty_ohms: float
```

The sensitivity vector follows the covariance parameter order and represents
``dR/dtheta`` for the fitted parameters. Individual sensitivity entries may have
different physical dimensions because the parameters themselves can have
different dimensions.

## `propagate_fit_covariance_to_resistance`

**Planned for:** rtd-sensor 0.7.0.

```python
propagate_fit_covariance_to_resistance(
    temperature_c: float,
    *,
    fit_result: IEC60751R0FitResult | PolynomialFitResult,
) -> FitCovarianceResistancePropagation
```

Applies covariance propagation ``J Cov(theta) J.T`` to the parameter covariance
retained by a supported fit. For the currently supported IEC-R0 and polynomial
fit-space parameterizations, resistance is linear in those retained parameters,
so the resistance covariance transformation is exact at fixed temperature. The fit must have available
parameter covariance. This result covers fitted-model uncertainty only; it does
not automatically combine acquisition uncertainty, reference-temperature
uncertainty, drift, tolerance, or other budget components.

See [Measurement & uncertainty](../documentation/measurement-uncertainty/index.md).
