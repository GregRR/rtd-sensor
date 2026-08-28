---
title: self_heating API
description: Quick API reference for rtd_sensor.self_heating observations, zero-power extrapolation, multi-observation fitting, and uncertainty propagation.
---

# `rtd_sensor.self_heating`

The self-heating API is **introduced in rtd-sensor 0.8.0**. It provides the
standard two-current resistance-domain extrapolation to zero measurement current,
a 3+ observation least-squares fit of the same resistance-versus-current-squared
relationship, residual-based parameter covariance for that larger fit, and
model-based temperature/uncertainty analysis for both the two-current and larger-fit
results, optional experiment-context provenance, context-bound self-heating
coefficient/dissipation-constant reporting, and threshold-free extrapolation-support
diagnostics.

## `SelfHeatingObservation`

**Introduced in:** rtd-sensor 0.8.0

```python
SelfHeatingObservation(
    measurement_current_a: float,
    resistance_ohms: float,
)
```

Both values must be finite and greater than zero. Measurement current is the
positive current magnitude in amperes.

Read-only derived properties:

```text
current_squared_a2: float
dissipated_power_w: float  # I²R at the observed resistance
```

`dissipated_power_w` records observation-level electrical power. The two-current
extrapolation itself follows the standard linear model of resistance versus
measurement-current squared.

## `extrapolate_zero_power_resistance`

**Introduced in:** rtd-sensor 0.8.0

```python
extrapolate_zero_power_resistance(
    observation_1: SelfHeatingObservation,
    observation_2: SelfHeatingObservation,
) -> TwoCurrentZeroPowerResult
```

The observations must use distinct current magnitudes and represent the same
stable external thermal condition. The function normalizes them into increasing
current order and extrapolates the resistance-vs-current-squared line to zero
current.

This resistance-domain function deliberately does **not** assess multi-point
linearity or prove that the experimental thermal condition was stable. Use
`propagate_two_current_zero_power_uncertainty(...)` when standard uncertainties for
the measured currents and resistances are available, and use
`evaluate_two_current_temperatures(...)` when model-based temperatures are also
wanted.


## `fit_zero_power_resistance`

**Introduced in:** rtd-sensor 0.8.0

```python
fit_zero_power_resistance(
    observations: Iterable[SelfHeatingObservation],
    *,
    resistance_standard_uncertainties_ohms: Iterable[float] | None = None,
    measurement_current_standard_uncertainties_a: Iterable[float] | None = None,
    current_resistance_error_correlations: Iterable[float] | None = None,
    context: SelfHeatingExperimentContext | None = None,
) -> ZeroPowerResistanceFitResult
```

Fits the same linear self-heating relation used by the two-current method:

```text
R(i) = R0 + k*i²
```

At least three observations and at least two numerically distinct current levels
are required. Repeated measurements at the same current levels are allowed, so a
sequence such as low/high/low/high can retain repeated-cycle scatter while still
providing positive residual degrees of freedom.

The default multi-observation path uses **unweighted ordinary least squares** in
resistance. If every observation has an absolute resistance standard uncertainty,
pass those values with `resistance_standard_uncertainties_ohms`; the same function
then uses inverse-variance weighted least squares with weights proportional to
`1/u²`. The `I²` coordinate remains fixed/exact in those two modes.

If every observation also has a measurement-current standard uncertainty, pass it
with `measurement_current_standard_uncertainties_a`. The fit then uses York
errors-in-variables regression in `(I², R)` coordinates. Current uncertainty is
propagated to the squared-current coordinate with the first-order relation
`u(I²) = 2 I u(I)`. Optional `current_resistance_error_correlations` supply one
within-observation correlation coefficient per current/resistance pair; omitted
coefficients are recorded as zero. The York path does not infer covariance between
separate observations. Optional ``context`` remains non-behavioral provenance and
does not alter any fit.

```python
weighted_fit = self_heating.fit_zero_power_resistance(
    observations,
    resistance_standard_uncertainties_ohms=(0.002, 0.002, 0.005, 0.005),
)

print(weighted_fit.evidence.effective_weights)
print(weighted_fit.evidence.chi_squared)
print(weighted_fit.evidence.reduced_chi_squared)
```

The uncertainty sequences must be finite, positive, and match the observation
count. Errors-in-variables fitting requires both current and resistance standard
uncertainties. Correlation coefficients must lie from `-1` through `1`. These values
are supplied measurement evidence; `rtd-sensor` does not infer them from replicate
scatter or shared instrumentation and does not define a universal acceptable
reduced-chi-square threshold.

```python
eiv_fit = self_heating.fit_zero_power_resistance(
    observations,
    resistance_standard_uncertainties_ohms=(0.002, 0.002, 0.005, 0.005),
    measurement_current_standard_uncertainties_a=(2e-7, 2e-7, 5e-7, 5e-7),
    current_resistance_error_correlations=(0.0, 0.0, 0.2, 0.2),
)

print(eiv_fit.evidence.current_squared_standard_uncertainties_a2)
print(eiv_fit.evidence.errors_in_variables_effective_weights)
print(eiv_fit.evidence.chi_squared)
```

## `assess_zero_power_extrapolation`

**Introduced in:** rtd-sensor 0.8.0

```python
assess_zero_power_extrapolation(
    result: TwoCurrentZeroPowerResult | ZeroPowerResistanceFitResult,
) -> ZeroPowerExtrapolationAssessment
```

Returns a threshold-free assessment of what the retained observations can and
cannot support. The function does not emit Python runtime warnings and does not
label an experiment as globally stable or unstable. Instead, the assessment exposes
structured `ZeroPowerExtrapolationWarning` objects with stable codes when the
evidence has an objective limitation:

```text
two_current_exact_line_no_residual_test
only_two_distinct_current_levels
no_repeated_current_levels
nonpositive_resistance_slope
```

The assessment also reports:

```text
observation_count
distinct_current_count
repeated_current_level_count
residual_degrees_of_freedom
minimum_measurement_current_a
maximum_measurement_current_a
minimum_to_maximum_current_ratio
zero_power_extrapolation_distance_in_current_squared_spans
resistance_slope_direction
supports_residual_consistency_assessment
supports_linearity_assessment
supports_repeated_level_assessment
warning_codes
warnings
has_warnings
```

`zero_power_extrapolation_distance_in_current_squared_spans` is
`min(I²) / (max(I²) - min(I²))`: the distance from the lowest sampled `I²` point
to zero expressed in units of the observed `I²` span. It is a descriptive
geometry/conditioning metric, not a pass/fail score. Likewise, the API deliberately
defines no universal acceptable current ratio or residual magnitude.

A warning means that the retained data lack a particular internal check; it does
**not** prove that the physical experiment failed. Conversely, an assessment with
no structural warnings does not prove stable external temperature. The experimental
requirement for constant external temperature and steady readings remains outside
what current/resistance values alone can establish.

## `ZeroPowerExtrapolationAssessment` and `ZeroPowerExtrapolationWarning`

`ZeroPowerExtrapolationAssessment` retains the source zero-power result and derives
all counts, geometry metrics, support flags, and warnings from that retained state.
`ZeroPowerExtrapolationWarning` retains only its stable `code`; its human-readable
`message` is derived from that code so the two cannot disagree.

## `SelfHeatingExperimentContext`

**Introduced in:** rtd-sensor 0.8.0

```python
SelfHeatingExperimentContext(
    medium: str | None = None,
    flow_condition: str | None = None,
    mounting: str | None = None,
    setup: str | None = None,
    notes: str | None = None,
)
```

The context records thermal-environment provenance for a 3+ observation fit. At
least one of ``medium``, ``flow_condition``, ``mounting``, or ``setup`` must be
supplied. Text is stripped of surrounding whitespace; blank strings are rejected.
The fields do not change fitting or RTD conversion.

## `ZeroPowerResistanceFitResult`

**Introduced in:** rtd-sensor 0.8.0

Fields and read-only diagnostics:

```text
zero_power_resistance_ohms: float
resistance_slope_ohms_per_a2: float
evidence: ZeroPowerResistanceFitEvidence
resistance_slope_direction: "positive" | "zero" | "negative"
```

A positive slope is the direction expected for ordinary self-heating under the
linear model. Zero and negative slopes are retained as evidence instead of being
rejected or silently relabeled as valid self-heating.

## `ZeroPowerResistanceFitEvidence`

**Introduced in:** rtd-sensor 0.8.0

The evidence preserves the observations in caller-supplied order and retains one
residual for each observation. Derived diagnostics include:

```text
observation_count: int
fitted_parameter_count: int                # always 2
residual_degrees_of_freedom: int           # observation_count - 2
distinct_current_count: int
minimum_measurement_current_a: float
maximum_measurement_current_a: float
current_squared_span_a2: float
rms_residual_ohms: float
max_absolute_residual_ohms: float
residual_standard_deviation_ohms: float
fitted_resistances_ohms: tuple[float, ...]
context: SelfHeatingExperimentContext | None
resistance_standard_uncertainties_ohms: tuple[float, ...] | None
measurement_current_standard_uncertainties_a: tuple[float, ...] | None
current_resistance_error_correlations: tuple[float, ...] | None
current_squared_standard_uncertainties_a2: tuple[float, ...] | None
effective_weights: tuple[float, ...] | None
errors_in_variables_effective_weights: tuple[float, ...] | None
errors_in_variables_iteration_count: int | None
chi_squared: float | None
reduced_chi_squared: float | None
weighted_rms_residual_ohms: float | None
method: (
    "ordinary_least_squares_resistance_vs_current_squared"
    | "inverse_variance_weighted_least_squares_resistance_vs_current_squared"
    | "york_errors_in_variables_resistance_vs_current_squared"
)
```

Residuals are `observed resistance - fitted resistance`. RMS residual is the
descriptive `sqrt(SSE / observation_count)` quantity; residual standard deviation
uses `sqrt(SSE / residual_degrees_of_freedom)`.

These diagnostics provide evidence about scatter and departures from the fitted
line, but they do not prove that the external temperature was stable. Interpreting
a residual magnitude as acceptable still requires an experiment-specific basis.

## `estimate_zero_power_fit_uncertainty`

**Introduced in:** rtd-sensor 0.8.0

```python
estimate_zero_power_fit_uncertainty(
    result: ZeroPowerResistanceFitResult,
) -> ZeroPowerResistanceFitUncertaintyResult
```

Estimates fitted-parameter covariance using the statistical model retained by the
fit. For an unweighted fit, the calculation uses residual variance
`SSE / residual_degrees_of_freedom` and ordinary-least-squares covariance. For an
inverse-variance weighted fit, covariance comes directly from the supplied absolute
resistance standard uncertainties. For a York errors-in-variables fit, covariance
comes from the York adjusted coordinates and the supplied current/resistance
coordinate uncertainty model. Neither absolute-uncertainty path is rescaled by
residual scatter or reduced chi-square.

The York path can represent correlation between current and resistance errors
within each observation. Correlation between separate observations still requires a
larger covariance model. Fitted RTD-model covariance also remains separate.

## `ZeroPowerResistanceFitUncertaintyResult`

**Introduced in:** rtd-sensor 0.8.0

Fields and read-only derived properties:

```text
fit_result: ZeroPowerResistanceFitResult
residual_variance_ohms_squared: float | None
parameter_names: tuple[str, str]
parameter_covariance_matrix: tuple[tuple[float, float], tuple[float, float]]
zero_power_resistance_variance_ohms_squared: float
zero_power_resistance_standard_uncertainty_ohms: float
resistance_slope_variance_ohms_squared_per_a4: float
resistance_slope_standard_uncertainty_ohms_per_a2: float
zero_power_resistance_slope_covariance_ohms_squared_per_a2: float
method: "residual_variance_scaled_least_squares" | "resistance_standard_uncertainties"
```

The covariance-matrix parameter order is:

```text
zero_power_resistance_ohms
resistance_slope_ohms_per_a2
```

For an unweighted exact finite fit, zero residual-based covariance is not a
statement that the physical experiment has zero uncertainty; it only means the
residual-scatter estimator observed no scatter from which to estimate a nonzero
common resistance variance. In contrast, an exact inverse-variance weighted fit can
have zero chi-square residual and still retain nonzero parameter covariance because
the supplied absolute resistance uncertainties define that covariance directly.

## `evaluate_zero_power_fit_temperatures`

**Introduced in:** rtd-sensor 0.8.0

```python
evaluate_zero_power_fit_temperatures(
    result: ZeroPowerResistanceFitResult,
    *,
    model: RTDModel,
) -> ZeroPowerResistanceFitTemperatureResult
```

Applies one explicitly supplied RTD model to the fitted zero-power resistance,
every observed resistance, and every fitted resistance at the sampled current
coordinates. Model conversion and range failures propagate unchanged.

## `ZeroPowerResistanceFitTemperatureResult`

**Introduced in:** rtd-sensor 0.8.0

Fields and read-only derived properties:

```text
fit_result: ZeroPowerResistanceFitResult
model: RTDModel
zero_power_temperature_c: float
observed_temperatures_c: tuple[float, ...]
fitted_temperatures_c: tuple[float, ...]
observed_temperature_rises_c: tuple[float, ...]
fitted_temperature_rises_c: tuple[float, ...]
temperature_residuals_c: tuple[float, ...]
observed_dissipated_powers_w: tuple[float, ...]
fitted_dissipated_powers_w: tuple[float, ...]
```

Caller observation order is preserved. Observed powers use ``I²R_observed``; fitted
powers use the fitted resistance at the same sampled current coordinate. These
temperature-rise/power pairs remain experimental evidence and are not automatically
reported as a transferable self-heating coefficient or dissipation constant.

## `propagate_zero_power_fit_temperature_uncertainty`

**Introduced in:** rtd-sensor 0.8.0

```python
propagate_zero_power_fit_temperature_uncertainty(
    result: ZeroPowerResistanceFitTemperatureResult,
) -> ZeroPowerResistanceFitTemperatureUncertaintyResult
```

Propagates the full retained covariance of the fitted zero-power resistance and
``dR/d(I²)`` slope through the supplied RTD model. The covariance may come from
residual-scatter OLS, supplied absolute resistance uncertainties in the weighted
fit, or a York errors-in-variables coordinate-uncertainty model. The result reports
fit-parameter-covariance uncertainty for the zero-power temperature, each fitted
temperature, and each fitted temperature rise.

At sampled ``x = I²``, fitted resistance depends on the retained parameters as
``R0 + k*x``. The fitted-temperature sensitivity vector is the local ``dT/dR``
times ``(1, x)``. Temperature-rise sensitivities subtract the zero-power
temperature sensitivity first, preserving the shared fitted intercept and the
intercept/slope covariance.

This is first-order/local propagation. For a York fit, measurement-current
uncertainty has already influenced the fitted-parameter covariance, but no separate
direct uncertainty term is added for the nominal sampled current coordinate used to
report each fitted point. The RTD model is treated as fixed and no additional
resistance uncertainty, model-parameter covariance, or cross-observation correlated
experiment effects are inserted automatically.

## `ZeroPowerResistanceFitTemperatureUncertaintyResult`

**Introduced in:** rtd-sensor 0.8.0

The result retains:

```text
temperature_result: ZeroPowerResistanceFitTemperatureResult
fit_uncertainty: ZeroPowerResistanceFitUncertaintyResult
parameter_names: tuple[str, str]
zero_power_temperature_parameter_sensitivity_vector: tuple[float, float]
fitted_temperature_parameter_sensitivity_vectors: tuple[tuple[float, float], ...]
fitted_temperature_rise_parameter_sensitivity_vectors: tuple[tuple[float, float], ...]
zero_power_temperature_variance_celsius_squared: float
zero_power_temperature_standard_uncertainty_c: float
fitted_temperature_variances_celsius_squared: tuple[float, ...]
fitted_temperature_standard_uncertainties_c: tuple[float, ...]
fitted_temperature_rise_variances_celsius_squared: tuple[float, ...]
fitted_temperature_rise_standard_uncertainties_c: tuple[float, ...]
propagation_method: "first_order_fit_parameter_covariance"
```

## `evaluate_self_heating_coefficient`

**Introduced in:** rtd-sensor 0.8.0

```python
evaluate_self_heating_coefficient(
    result: ZeroPowerResistanceFitTemperatureResult,
) -> SelfHeatingCoefficientResult
```

A named coefficient is produced only when the underlying 3+ observation fit retained
a ``SelfHeatingExperimentContext`` and has a positive resistance-versus-current-
squared slope. The calculation uses fitted temperature rise and fitted ``I²R`` power
at each **distinct** sampled current level and fits the proportional relationship
``ΔT = C_self * P`` through the origin. The returned scalar is a **finite-range**
coefficient over those sampled levels, not the zero-power differential
``d(ΔT)/dP``. Repeated observations at one current level affect the underlying
resistance fit but do not receive a second weight merely by being repeated in the
coefficient calculation.

No universal coefficient-fit residual threshold is imposed. A zero or negative
resistance slope remains available as fit evidence but is rejected for named
positive coefficient reporting.

The two-current correction path is intentionally not accepted here. Its two points
exactly determine the resistance line, so the named context-bound characterization
remains on the larger-observation path with residual diagnostics and fit covariance.

The current coefficient calculation also rejects York errors-in-variables fits.
When measurement-current uncertainty is material, fitted ``I²R`` power depends
directly on an uncertain current coordinate; propagating only the fitted intercept/
slope covariance would omit that dependence. The EIV fit can still be used for the
zero-power extrapolation and its temperature interpretation, but coefficient
characterization remains on the fixed-current OLS/WLS paths until that downstream
uncertainty model is defined.

## `SelfHeatingCoefficientResult`

**Introduced in:** rtd-sensor 0.8.0

The result retains:

```text
temperature_result: ZeroPowerResistanceFitTemperatureResult
context: SelfHeatingExperimentContext
current_squared_levels_a2: tuple[float, ...]
fitted_temperature_rises_c: tuple[float, ...]
fitted_dissipated_powers_w: tuple[float, ...]
pointwise_self_heating_coefficients_c_per_w: tuple[float, ...]
coefficient_fit_residuals_c: tuple[float, ...]
distinct_current_count: int
coefficient_rms_residual_c: float
coefficient_max_absolute_residual_c: float
self_heating_coefficient_c_per_w: float
self_heating_coefficient_c_per_mw: float
dissipation_constant_w_per_c: float
dissipation_constant_mw_per_c: float
method: "least_squares_temperature_rise_vs_fitted_power_through_origin"
```

The coefficient is tied to the retained experiment context and to the fitted
zero-power temperature and sampled power/current range. It must not be treated as
an intrinsic property of the RTD characteristic or assumed to transfer unchanged
to another medium, flow condition, mounting, setup, temperature, or substantially
different power range. Even for an exact linear ``R``-versus-``I²`` fit,
``P = I²(R0 + kI²)`` contains a ``kI⁴`` term, so pointwise ``ΔT/P`` and the fitted
finite-range scalar can vary with sampled power without measurement noise or RTD
model curvature. The retained coefficient-fit residuals, RMS residual, and maximum
absolute residual expose that finite-range shape behavior; they are descriptive
diagnostics, not an additional statistical residual variance or uncertainty
estimate.

## `propagate_self_heating_coefficient_uncertainty`

**Introduced in:** rtd-sensor 0.8.0

```python
propagate_self_heating_coefficient_uncertainty(
    result: SelfHeatingCoefficientResult,
) -> SelfHeatingCoefficientUncertaintyResult
```

Propagates the full retained covariance of the fitted zero-power resistance and
``dR/d(I²)`` slope through the context-bound coefficient calculation. That
covariance may come from residual-scatter OLS or supplied absolute resistance
standard uncertainties in an inverse-variance weighted fit. The
through-origin coefficient depends on both fitted temperature rise and fitted power,
so both dependencies are included in the parameter sensitivities before the 2x2
covariance matrix is applied. The dissipation-constant uncertainty is propagated
from the reciprocal relationship.

This remains first-order/local. The supplied RTD model and experiment context are
treated as fixed. The reported standard uncertainty describes covariance of this
finite-range coefficient under the retained resistance-fit covariance model; it
does **not** include the
deterministic difference between the finite-range scalar and a zero-power
differential coefficient. Coefficient-fit residual scatter, RTD-model covariance,
current-coordinate uncertainty, and correlated experiment effects are not added
automatically.

## `SelfHeatingCoefficientUncertaintyResult`

**Introduced in:** rtd-sensor 0.8.0

The result retains:

```text
coefficient_result: SelfHeatingCoefficientResult
fit_uncertainty: ZeroPowerResistanceFitUncertaintyResult
parameter_names: tuple[str, str]
self_heating_coefficient_parameter_sensitivity_vector: tuple[float, float]
self_heating_coefficient_variance_celsius_squared_per_watt_squared: float
self_heating_coefficient_standard_uncertainty_c_per_w: float
self_heating_coefficient_standard_uncertainty_c_per_mw: float
dissipation_constant_parameter_sensitivity_vector: tuple[float, float]
dissipation_constant_variance_watt_squared_per_celsius_squared: float
dissipation_constant_standard_uncertainty_w_per_c: float
dissipation_constant_standard_uncertainty_mw_per_c: float
propagation_method: "first_order_fit_parameter_covariance"
```

## `evaluate_two_current_temperatures`

**Introduced in:** rtd-sensor 0.8.0

```python
evaluate_two_current_temperatures(
    result: TwoCurrentZeroPowerResult,
    *,
    model: RTDModel,
) -> TwoCurrentSelfHeatingTemperatureResult
```

The supplied model converts the extrapolated zero-power resistance and both
observed resistances to Celsius. Model conversion errors and range failures
propagate unchanged.

## `TwoCurrentSelfHeatingTemperatureResult`

**Introduced in:** rtd-sensor 0.8.0

Fields and read-only derived properties:

```text
zero_power_result: TwoCurrentZeroPowerResult
model: RTDModel
zero_power_temperature_c: float
low_current_temperature_c: float
high_current_temperature_c: float
low_current_temperature_rise_c: float
high_current_temperature_rise_c: float
```

The exact model object supplied to `evaluate_two_current_temperatures(...)` is
retained as `model` so the model used for the temperature interpretation remains
inspectable with the result. The temperature rises are each observed temperature
minus the extrapolated zero-power temperature. They do not independently establish
ambient temperature or prove that the experiment was thermally stable.

## `TwoCurrentInputStandardUncertainties`

**Introduced in:** rtd-sensor 0.8.0

```python
TwoCurrentInputStandardUncertainties(
    *,
    low_current_standard_uncertainty_a: float,
    low_resistance_standard_uncertainty_ohms: float,
    high_current_standard_uncertainty_a: float,
    high_resistance_standard_uncertainty_ohms: float,
)
```

All four values must be finite and non-negative. The fields correspond to the
normalized low- and high-current observations retained by the zero-power result.
They are treated as independent when no correlation matrix is supplied. Because
the propagation is a local first-order approximation, the supplied uncertainties
should also be small enough for that local linearization to be meaningful. In
particular, a current uncertainty that is large relative to the separation between
the two current levels needs more careful treatment.

The fixed sensitivity-vector order is:

```text
low_current_a
low_resistance_ohms
high_current_a
high_resistance_ohms
```

## `TwoCurrentInputCorrelationMatrix`

**Introduced in:** rtd-sensor 0.8.0

```python
TwoCurrentInputCorrelationMatrix(
    correlation_matrix: tuple[tuple[float, float, float, float], ...],
)
```

The matrix uses the same four-input order shown above. It must be finite,
symmetric, positive semidefinite, and have unit diagonal. Supply it only when the
input dependence is known from the measurement model or supporting evidence;
`rtd-sensor` does not infer correlation from shared hardware or from the order in
which readings were collected.

`covariance_matrix(standard_uncertainties)` combines the dimensionless
correlations with a `TwoCurrentInputStandardUncertainties` object and returns the
4 x 4 covariance matrix used by first-order propagation.

## `propagate_two_current_zero_power_uncertainty`

**Introduced in:** rtd-sensor 0.8.0

```python
propagate_two_current_zero_power_uncertainty(
    result: TwoCurrentZeroPowerResult,
    *,
    input_standard_uncertainties: TwoCurrentInputStandardUncertainties,
    input_correlation_matrix: TwoCurrentInputCorrelationMatrix | None = None,
) -> TwoCurrentZeroPowerUncertaintyResult
```

Applies first-order propagation directly to the two measured currents and two
measured resistances. Both current uncertainty and resistance uncertainty can
therefore contribute to the zero-power resistance uncertainty. Omitting
`input_correlation_matrix` preserves the independent-input calculation. Supplying
one uses the full covariance form of the propagation law.

`TwoCurrentZeroPowerUncertaintyResult` retains the input uncertainties, optional
correlation matrix, covariance matrix actually used, zero-power-resistance
sensitivity vector, propagated variance, standard uncertainty, and a method label
of either `first_order_independent_inputs` or `first_order_correlated_inputs`.

## `propagate_two_current_temperature_uncertainty`

**Introduced in:** rtd-sensor 0.8.0

```python
propagate_two_current_temperature_uncertainty(
    result: TwoCurrentSelfHeatingTemperatureResult,
    *,
    input_standard_uncertainties: TwoCurrentInputStandardUncertainties,
    input_correlation_matrix: TwoCurrentInputCorrelationMatrix | None = None,
) -> TwoCurrentSelfHeatingTemperatureUncertaintyResult
```

Uses the local `dT/dR` sensitivity supplied by the exact RTD model retained in the
temperature result. It reports standard uncertainty for:

- zero-power temperature;
- low- and high-current observed temperatures; and
- low- and high-current self-heating temperature rises.

The temperature-rise uncertainties are propagated from the original four measured
inputs. They are **not** calculated by root-sum-squaring an observed-temperature
uncertainty with the zero-power-temperature uncertainty, because those derived
quantities share the same resistance observations and are therefore not
independent.

`TwoCurrentSelfHeatingTemperatureUncertaintyResult` retains the input sensitivity
vectors, variances, standard uncertainties, the corresponding zero-power
resistance-uncertainty result, and the same independent/correlated propagation
method label. Known correlations therefore propagate directly into temperatures
and temperature rises instead of being discarded. Fitted-model covariance and
other uncertainty-budget components remain separate.

## `TwoCurrentZeroPowerResult`

**Introduced in:** rtd-sensor 0.8.0

Fields and read-only derived properties:

```text
zero_power_resistance_ohms: float
evidence: TwoCurrentZeroPowerEvidence
low_current_resistance_rise_ohms: float
high_current_resistance_rise_ohms: float
```

## `TwoCurrentZeroPowerEvidence`

**Introduced in:** rtd-sensor 0.8.0

The immutable evidence retains the low- and high-current observations. Derived
properties expose:

```text
current_ratio: float
current_squared_change_a2: float
resistance_change_ohms: float
resistance_slope_ohms_per_a2: float
residual_degrees_of_freedom: int  # always 0 for the two-point method
method: "linear_resistance_vs_current_squared"
```

With only two observations, there is no residual redundancy. The result is an
extrapolation under the caller's stable-condition assumption, not an independent
stability test.

See [Self-heating and zero-power resistance](../documentation/measurement-uncertainty/self-heating.md)
for the scientific assumptions and an example.
