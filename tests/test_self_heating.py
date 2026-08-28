# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
from dataclasses import FrozenInstanceError

import pytest

from rtd_sensor import catalog
from rtd_sensor.self_heating import (
    SelfHeatingCoefficientResult,
    SelfHeatingCoefficientUncertaintyResult,
    SelfHeatingExperimentContext,
    SelfHeatingObservation,
    TwoCurrentInputCorrelationMatrix,
    TwoCurrentInputStandardUncertainties,
    TwoCurrentSelfHeatingTemperatureResult,
    TwoCurrentSelfHeatingTemperatureUncertaintyResult,
    TwoCurrentZeroPowerEvidence,
    TwoCurrentZeroPowerResult,
    TwoCurrentZeroPowerUncertaintyResult,
    ZeroPowerExtrapolationAssessment,
    ZeroPowerExtrapolationWarning,
    ZeroPowerResistanceFitEvidence,
    ZeroPowerResistanceFitResult,
    ZeroPowerResistanceFitTemperatureResult,
    ZeroPowerResistanceFitTemperatureUncertaintyResult,
    ZeroPowerResistanceFitUncertaintyResult,
    assess_zero_power_extrapolation,
    estimate_zero_power_fit_uncertainty,
    evaluate_self_heating_coefficient,
    evaluate_two_current_temperatures,
    evaluate_zero_power_fit_temperatures,
    extrapolate_zero_power_resistance,
    fit_zero_power_resistance,
    propagate_self_heating_coefficient_uncertainty,
    propagate_two_current_temperature_uncertainty,
    propagate_two_current_zero_power_uncertainty,
    propagate_zero_power_fit_temperature_uncertainty,
)


def test_self_heating_observation_normalizes_numeric_values() -> None:
    observation = SelfHeatingObservation(1, 100)

    assert observation.measurement_current_a == 1.0
    assert observation.resistance_ohms == 100.0
    assert isinstance(observation.measurement_current_a, float)
    assert isinstance(observation.resistance_ohms, float)


def test_self_heating_observation_is_immutable() -> None:
    observation = SelfHeatingObservation(0.001, 100.0)

    with pytest.raises(FrozenInstanceError):
        observation.resistance_ohms = 101.0  # type: ignore[misc]


@pytest.mark.parametrize("field", ["measurement_current_a", "resistance_ohms"])
def test_self_heating_observation_rejects_bool(field: str) -> None:
    kwargs: dict[str, object] = {
        "measurement_current_a": 0.001,
        "resistance_ohms": 100.0,
    }
    kwargs[field] = True

    with pytest.raises(TypeError):
        SelfHeatingObservation(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("current", [0.0, -0.001, math.inf, -math.inf, math.nan])
def test_self_heating_observation_rejects_invalid_current(current: float) -> None:
    with pytest.raises(ValueError):
        SelfHeatingObservation(current, 100.0)


@pytest.mark.parametrize("resistance", [0.0, -1.0, math.inf, -math.inf, math.nan])
def test_self_heating_observation_rejects_invalid_resistance(resistance: float) -> None:
    with pytest.raises(ValueError):
        SelfHeatingObservation(0.001, resistance)


def test_self_heating_observation_rejects_nonfinite_squared_current() -> None:
    with pytest.raises(ValueError, match="current squared"):
        SelfHeatingObservation(1.0e200, 100.0)


def test_self_heating_observation_rejects_underflowed_squared_current() -> None:
    with pytest.raises(ValueError, match="current squared"):
        SelfHeatingObservation(1.0e-200, 100.0)


def test_self_heating_observation_rejects_nonfinite_power() -> None:
    with pytest.raises(ValueError, match="Dissipated power"):
        SelfHeatingObservation(1.0e100, 1.0e200)


def test_self_heating_observation_reports_current_squared_and_power() -> None:
    observation = SelfHeatingObservation(0.001, 100.02)

    assert observation.current_squared_a2 == pytest.approx(1.0e-6)
    assert observation.dissipated_power_w == pytest.approx(100.02e-6)


def test_self_heating_experiment_context_normalizes_optional_text() -> None:
    context = SelfHeatingExperimentContext(
        medium="  flowing water  ",
        flow_condition="  approximately 0.4 m/s  ",
        notes="  calibration bath  ",
    )

    assert context.medium == "flowing water"
    assert context.flow_condition == "approximately 0.4 m/s"
    assert context.notes == "calibration bath"
    assert context.mounting is None
    assert context.setup is None


def test_self_heating_experiment_context_is_immutable() -> None:
    context = SelfHeatingExperimentContext(medium="stirred water")

    with pytest.raises(FrozenInstanceError):
        context.medium = "air"  # type: ignore[misc]


def test_self_heating_experiment_context_requires_environment_descriptor() -> None:
    with pytest.raises(ValueError, match="requires medium"):
        SelfHeatingExperimentContext(notes="notes alone are not environment context")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"medium": "   "},
        {"setup": 123},
    ],
)
def test_self_heating_experiment_context_rejects_invalid_text(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        SelfHeatingExperimentContext(**kwargs)  # type: ignore[arg-type]


def test_two_current_evidence_rejects_reversed_current_order() -> None:
    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(0.002, 100.04)

    with pytest.raises(ValueError, match="high current"):
        TwoCurrentZeroPowerEvidence(
            low_current_observation=high,
            high_current_observation=low,
        )


def test_two_current_result_rejects_resistance_inconsistent_with_evidence() -> None:
    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(0.002, 100.04)
    evidence = TwoCurrentZeroPowerEvidence(
        low_current_observation=low,
        high_current_observation=high,
    )

    with pytest.raises(ValueError, match="consistent with retained evidence"):
        TwoCurrentZeroPowerResult(
            zero_power_resistance_ohms=99.0,
            evidence=evidence,
        )


def test_two_current_extrapolation_matches_sqrt2_current_case() -> None:
    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02)

    result = extrapolate_zero_power_resistance(low, high)

    assert isinstance(result, TwoCurrentZeroPowerResult)
    assert isinstance(result.evidence, TwoCurrentZeroPowerEvidence)
    assert result.zero_power_resistance_ohms == pytest.approx(100.0, abs=1e-12)
    assert result.low_current_resistance_rise_ohms == pytest.approx(0.01, abs=1e-12)
    assert result.high_current_resistance_rise_ohms == pytest.approx(0.02, abs=1e-12)


def test_two_current_extrapolation_matches_general_closed_form() -> None:
    low = SelfHeatingObservation(0.0008, 119.413)
    high = SelfHeatingObservation(0.0017, 119.451)

    result = extrapolate_zero_power_resistance(low, high)
    i1_squared = low.measurement_current_a**2
    i2_squared = high.measurement_current_a**2
    expected = (
        low.resistance_ohms * i2_squared - high.resistance_ohms * i1_squared
    ) / (i2_squared - i1_squared)

    assert result.zero_power_resistance_ohms == pytest.approx(expected, rel=1e-14)


def test_two_current_extrapolation_normalizes_observation_order() -> None:
    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(0.002, 100.04)

    forward = extrapolate_zero_power_resistance(low, high)
    reverse = extrapolate_zero_power_resistance(high, low)

    assert forward == reverse
    assert forward.evidence.low_current_observation is low
    assert forward.evidence.high_current_observation is high


def test_two_current_evidence_reports_auditable_derived_quantities() -> None:
    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(0.002, 100.04)

    evidence = extrapolate_zero_power_resistance(low, high).evidence

    assert evidence.method == "linear_resistance_vs_current_squared"
    assert evidence.current_ratio == pytest.approx(2.0)
    assert evidence.current_squared_change_a2 == pytest.approx(3.0e-6)
    assert evidence.resistance_change_ohms == pytest.approx(0.03)
    assert evidence.resistance_slope_ohms_per_a2 == pytest.approx(10000.0)
    assert evidence.residual_degrees_of_freedom == 0


def test_two_current_extrapolation_allows_zero_observed_resistance_change() -> None:
    low = SelfHeatingObservation(0.001, 100.0)
    high = SelfHeatingObservation(0.002, 100.0)

    result = extrapolate_zero_power_resistance(low, high)

    assert result.zero_power_resistance_ohms == 100.0
    assert result.low_current_resistance_rise_ohms == 0.0
    assert result.high_current_resistance_rise_ohms == 0.0


def test_two_current_extrapolation_retains_negative_observed_change_as_evidence() -> (
    None
):
    low = SelfHeatingObservation(0.001, 100.02)
    high = SelfHeatingObservation(0.002, 100.01)

    result = extrapolate_zero_power_resistance(low, high)

    assert result.evidence.resistance_change_ohms < 0.0
    assert result.low_current_resistance_rise_ohms < 0.0
    assert result.zero_power_resistance_ohms > low.resistance_ohms


def test_two_current_extrapolation_rejects_equal_current_levels() -> None:
    observation_1 = SelfHeatingObservation(0.001, 100.0)
    observation_2 = SelfHeatingObservation(0.001, 100.01)

    with pytest.raises(ValueError, match="distinct current levels"):
        extrapolate_zero_power_resistance(observation_1, observation_2)


@pytest.mark.parametrize("position", [1, 2])
def test_two_current_extrapolation_rejects_non_observation_arguments(
    position: int,
) -> None:
    observation = SelfHeatingObservation(0.001, 100.0)

    with pytest.raises(TypeError, match=f"observation_{position}"):
        if position == 1:
            extrapolate_zero_power_resistance(
                100.0,  # type: ignore[arg-type]
                observation,
            )
        else:
            extrapolate_zero_power_resistance(
                observation,
                100.0,  # type: ignore[arg-type]
            )


def test_two_current_extrapolation_rejects_nonpositive_intercept() -> None:
    low = SelfHeatingObservation(0.001, 1.0)
    high = SelfHeatingObservation(0.002, 5.0)

    with pytest.raises(ValueError, match="greater than zero"):
        extrapolate_zero_power_resistance(low, high)


def test_two_current_temperature_evaluation_uses_supplied_model() -> None:
    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02)
    zero_power = extrapolate_zero_power_resistance(low, high)
    model = catalog.get_model("pt100")

    result = evaluate_two_current_temperatures(zero_power, model=model)

    assert isinstance(result, TwoCurrentSelfHeatingTemperatureResult)
    assert result.zero_power_result is zero_power
    assert result.model is model
    assert result.zero_power_temperature_c == pytest.approx(0.0, abs=1e-12)
    assert result.low_current_temperature_c == pytest.approx(
        model.resistance_to_celsius(100.01),
    )
    assert result.high_current_temperature_c == pytest.approx(
        model.resistance_to_celsius(100.02),
    )
    assert result.low_current_temperature_rise_c == pytest.approx(
        result.low_current_temperature_c - result.zero_power_temperature_c
    )
    assert result.high_current_temperature_rise_c == pytest.approx(
        result.high_current_temperature_c - result.zero_power_temperature_c
    )


def test_two_current_temperature_evaluation_preserves_negative_rise() -> None:
    low = SelfHeatingObservation(0.001, 100.02)
    high = SelfHeatingObservation(0.002, 100.01)
    zero_power = extrapolate_zero_power_resistance(low, high)

    result = evaluate_two_current_temperatures(
        zero_power,
        model=catalog.get_model("pt100"),
    )

    assert result.low_current_temperature_rise_c < 0.0
    assert result.high_current_temperature_rise_c < 0.0


def test_two_current_temperature_evaluation_rejects_non_result() -> None:
    with pytest.raises(TypeError, match="TwoCurrentZeroPowerResult"):
        evaluate_two_current_temperatures(
            100.0,  # type: ignore[arg-type]
            model=catalog.get_model("pt100"),
        )


def test_two_current_temperature_evaluation_propagates_model_error() -> None:
    class FailingModel:
        def resistance_to_celsius(self, resistance_ohms: float) -> float:
            raise RuntimeError("model conversion failed")

        def celsius_to_resistance(self, temperature_c: float) -> float:
            return 100.0

        def resistance_sensitivity_ohms_per_celsius(
            self, temperature_c: float
        ) -> float:
            return 1.0

        def temperature_sensitivity_celsius_per_ohm(
            self, temperature_c: float
        ) -> float:
            return 1.0

    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02)
    zero_power = extrapolate_zero_power_resistance(low, high)

    with pytest.raises(RuntimeError, match="model conversion failed"):
        evaluate_two_current_temperatures(zero_power, model=FailingModel())


def test_two_current_temperature_evaluation_rejects_nonfinite_model_result() -> None:
    class NonFiniteModel:
        def resistance_to_celsius(self, resistance_ohms: float) -> float:
            return math.nan

        def celsius_to_resistance(self, temperature_c: float) -> float:
            return 100.0

        def resistance_sensitivity_ohms_per_celsius(
            self, temperature_c: float
        ) -> float:
            return 1.0

        def temperature_sensitivity_celsius_per_ohm(
            self, temperature_c: float
        ) -> float:
            return 1.0

    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02)
    zero_power = extrapolate_zero_power_resistance(low, high)

    with pytest.raises(ValueError, match="Zero-power temperature must be finite"):
        evaluate_two_current_temperatures(zero_power, model=NonFiniteModel())


def test_zero_power_fit_matches_exact_three_point_line() -> None:
    observations = (
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02),
        SelfHeatingObservation(0.002, 100.04),
    )

    result = fit_zero_power_resistance(observations)

    assert isinstance(result, ZeroPowerResistanceFitResult)
    assert isinstance(result.evidence, ZeroPowerResistanceFitEvidence)
    assert result.zero_power_resistance_ohms == pytest.approx(100.0)
    assert result.resistance_slope_ohms_per_a2 == pytest.approx(10000.0)
    assert result.resistance_slope_direction == "positive"
    assert result.evidence.observations == observations
    assert result.evidence.observation_count == 3
    assert result.evidence.fitted_parameter_count == 2
    assert result.evidence.residual_degrees_of_freedom == 1
    assert result.evidence.distinct_current_count == 3
    assert result.evidence.current_squared_span_a2 == pytest.approx(3.0e-6)
    assert result.evidence.rms_residual_ohms == pytest.approx(0.0, abs=1e-12)
    assert result.evidence.max_absolute_residual_ohms == pytest.approx(0.0, abs=1e-12)
    assert result.evidence.residual_standard_deviation_ohms == pytest.approx(
        0.0, abs=1e-12
    )


def test_zero_power_fit_allows_repeated_two_current_cycles() -> None:
    low_current = 0.001
    high_current = math.sqrt(2.0) * 0.001
    observations = (
        SelfHeatingObservation(low_current, 100.009),
        SelfHeatingObservation(high_current, 100.019),
        SelfHeatingObservation(low_current, 100.011),
        SelfHeatingObservation(high_current, 100.021),
    )

    result = fit_zero_power_resistance(observations)

    assert result.zero_power_resistance_ohms == pytest.approx(100.0)
    assert result.resistance_slope_ohms_per_a2 == pytest.approx(10000.0)
    assert result.evidence.distinct_current_count == 2
    assert result.evidence.residual_degrees_of_freedom == 2
    assert result.evidence.observations == observations
    assert result.evidence.residuals_ohms == pytest.approx(
        (-0.001, -0.001, 0.001, 0.001)
    )
    assert result.evidence.rms_residual_ohms == pytest.approx(0.001)
    assert result.evidence.residual_standard_deviation_ohms == pytest.approx(
        math.sqrt(2.0) * 0.001
    )


def test_zero_power_fit_inverse_variance_weighting_uses_resistance_uncertainties() -> (
    None
):
    observations = (
        SelfHeatingObservation(1.0, 101.0),
        SelfHeatingObservation(2.0, 104.0),
        SelfHeatingObservation(3.0, 120.0),
    )

    unweighted = fit_zero_power_resistance(observations)
    weighted = fit_zero_power_resistance(
        observations,
        resistance_standard_uncertainties_ohms=(1.0, 1.0, 100.0),
    )

    assert weighted.evidence.method == (
        "inverse_variance_weighted_least_squares_resistance_vs_current_squared"
    )
    assert weighted.evidence.resistance_standard_uncertainties_ohms == (
        1.0,
        1.0,
        100.0,
    )
    assert weighted.evidence.effective_weights == pytest.approx((1.0, 1.0, 0.0001))
    assert weighted.zero_power_resistance_ohms == pytest.approx(99.99658115863201)
    assert weighted.resistance_slope_ohms_per_a2 == pytest.approx(1.0015873192065634)
    assert abs(weighted.zero_power_resistance_ohms - 100.0) < abs(
        unweighted.zero_power_resistance_ohms - 100.0
    )
    assert weighted.evidence.chi_squared == pytest.approx(0.012088046265359842)
    assert weighted.evidence.reduced_chi_squared == pytest.approx(
        weighted.evidence.chi_squared
    )
    assert weighted.evidence.weighted_rms_residual_ohms == pytest.approx(
        0.07774137216844444
    )


def test_zero_power_fit_equal_resistance_uncertainties_preserve_ols_estimates() -> None:
    observations = (
        SelfHeatingObservation(1.0, 102.0),
        SelfHeatingObservation(2.0, 108.0),
        SelfHeatingObservation(3.0, 119.0),
    )

    unweighted = fit_zero_power_resistance(observations)
    weighted = fit_zero_power_resistance(
        observations,
        resistance_standard_uncertainties_ohms=(0.5, 0.5, 0.5),
    )

    assert weighted.zero_power_resistance_ohms == pytest.approx(
        unweighted.zero_power_resistance_ohms
    )
    assert weighted.resistance_slope_ohms_per_a2 == pytest.approx(
        unweighted.resistance_slope_ohms_per_a2
    )
    assert weighted.evidence.residuals_ohms == pytest.approx(
        unweighted.evidence.residuals_ohms
    )


def test_zero_power_weighted_fit_uncertainty_uses_absolute_input_uncertainties() -> (
    None
):
    fit = fit_zero_power_resistance(
        (
            SelfHeatingObservation(1.0, 101.0),
            SelfHeatingObservation(2.0, 104.0),
            SelfHeatingObservation(3.0, 109.0),
        ),
        resistance_standard_uncertainties_ohms=(0.5, 0.5, 0.5),
    )

    uncertainty = estimate_zero_power_fit_uncertainty(fit)

    assert fit.evidence.chi_squared == pytest.approx(0.0, abs=1e-20)
    assert uncertainty.method == "resistance_standard_uncertainties"
    assert uncertainty.residual_variance_ohms_squared is None
    assert uncertainty.parameter_covariance_matrix[0] == pytest.approx(
        (0.25, -1.0 / 28.0)
    )
    assert uncertainty.parameter_covariance_matrix[1] == pytest.approx(
        (-1.0 / 28.0, 3.0 / 392.0)
    )
    assert uncertainty.zero_power_resistance_standard_uncertainty_ohms == pytest.approx(
        0.5
    )


@pytest.mark.parametrize(
    "uncertainties, match",
    [
        ((0.1, 0.1), "count must match"),
        ((0.1, 0.0, 0.1), "greater than zero"),
        ((0.1, math.inf, 0.1), "must be finite"),
    ],
)
def test_zero_power_fit_rejects_invalid_resistance_uncertainties(
    uncertainties: tuple[float, ...],
    match: str,
) -> None:
    observations = (
        SelfHeatingObservation(1.0, 101.0),
        SelfHeatingObservation(2.0, 104.0),
        SelfHeatingObservation(3.0, 109.0),
    )

    with pytest.raises(ValueError, match=match):
        fit_zero_power_resistance(
            observations,
            resistance_standard_uncertainties_ohms=uncertainties,
        )


def _york_reference_case() -> tuple[
    tuple[SelfHeatingObservation, ...],
    tuple[float, ...],
    tuple[float, ...],
]:
    x_values = (0.0, 0.9, 1.8, 2.6, 3.3, 4.4, 5.2, 6.1, 6.5, 7.4)
    resistances = (5.9, 5.4, 4.4, 4.6, 3.5, 3.7, 2.8, 2.8, 2.4, 1.5)
    x_weights = (1000.0, 1000.0, 500.0, 800.0, 200.0, 80.0, 60.0, 20.0, 1.8, 1.0)
    resistance_weights = (1.0, 1.8, 4.0, 8.0, 20.0, 20.0, 70.0, 70.0, 100.0, 500.0)
    x_scale = 1.0e-6
    current_squared = tuple((value + 1.0) * x_scale for value in x_values)
    observations = tuple(
        SelfHeatingObservation(math.sqrt(x_value), resistance)
        for x_value, resistance in zip(current_squared, resistances, strict=True)
    )
    x_uncertainties = tuple(x_scale / math.sqrt(weight) for weight in x_weights)
    current_uncertainties = tuple(
        x_uncertainty / (2.0 * observation.measurement_current_a)
        for x_uncertainty, observation in zip(
            x_uncertainties, observations, strict=True
        )
    )
    resistance_uncertainties = tuple(
        1.0 / math.sqrt(weight) for weight in resistance_weights
    )
    return observations, current_uncertainties, resistance_uncertainties


def test_zero_power_fit_york_errors_in_variables_matches_reference_case() -> None:
    observations, current_uncertainties, resistance_uncertainties = (
        _york_reference_case()
    )

    result = fit_zero_power_resistance(
        observations,
        resistance_standard_uncertainties_ohms=resistance_uncertainties,
        measurement_current_standard_uncertainties_a=current_uncertainties,
    )
    uncertainty = estimate_zero_power_fit_uncertainty(result)

    assert result.evidence.method == (
        "york_errors_in_variables_resistance_vs_current_squared"
    )
    assert result.zero_power_resistance_ohms == pytest.approx(5.96044363147907)
    assert result.resistance_slope_ohms_per_a2 == pytest.approx(-480533.4074462)
    assert result.evidence.chi_squared == pytest.approx(11.86635319406145)
    assert result.evidence.reduced_chi_squared == pytest.approx(1.483294149257681)
    assert result.evidence.errors_in_variables_iteration_count == 8
    assert result.evidence.effective_weights is None
    assert result.evidence.weighted_rms_residual_ohms is None
    assert uncertainty.method == "york_coordinate_standard_uncertainties"
    assert uncertainty.residual_variance_ohms_squared is None
    assert uncertainty.zero_power_resistance_standard_uncertainty_ohms == pytest.approx(
        0.35116247718456
    )
    assert uncertainty.resistance_slope_standard_uncertainty_ohms_per_a2 == (
        pytest.approx(57985.0090007744)
    )
    assert (
        uncertainty.zero_power_resistance_slope_covariance_ohms_squared_per_a2
        == pytest.approx(-19834.8059269357)
    )


def test_zero_power_fit_york_transforms_current_uncertainty_to_current_squared() -> (
    None
):
    observations = (
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(0.002, 100.04),
        SelfHeatingObservation(0.003, 100.09),
    )
    current_uncertainties = (1.0e-6, 2.0e-6, 3.0e-6)

    result = fit_zero_power_resistance(
        observations,
        resistance_standard_uncertainties_ohms=(0.01, 0.01, 0.01),
        measurement_current_standard_uncertainties_a=current_uncertainties,
    )

    assert result.evidence.measurement_current_standard_uncertainties_a == (
        current_uncertainties
    )
    assert result.evidence.current_squared_standard_uncertainties_a2 == pytest.approx(
        (2.0e-9, 8.0e-9, 18.0e-9)
    )
    assert result.evidence.current_resistance_error_correlations == (0.0, 0.0, 0.0)
    assert result.evidence.errors_in_variables_effective_weights is not None


def test_zero_power_fit_york_uses_within_observation_error_correlations() -> None:
    observations, current_uncertainties, resistance_uncertainties = (
        _york_reference_case()
    )
    correlations = (0.5, -0.25, 0.7, 0.1, -0.4, 0.3, 0.2, -0.5, 0.6, -0.2)

    result = fit_zero_power_resistance(
        observations,
        resistance_standard_uncertainties_ohms=resistance_uncertainties,
        measurement_current_standard_uncertainties_a=current_uncertainties,
        current_resistance_error_correlations=correlations,
    )
    uncertainty = estimate_zero_power_fit_uncertainty(result)

    assert result.evidence.current_resistance_error_correlations == correlations
    assert result.zero_power_resistance_ohms == pytest.approx(5.83181898739891)
    assert result.resistance_slope_ohms_per_a2 == pytest.approx(-451537.03055443)
    assert result.evidence.chi_squared == pytest.approx(13.43120450718031)
    assert uncertainty.parameter_covariance_matrix[0] == pytest.approx(
        (0.107009194986145, -16566.818300761)
    )
    assert uncertainty.parameter_covariance_matrix[1] == pytest.approx(
        (-16566.818300761, 2694617559.07278)
    )


def test_zero_power_fit_york_rejects_incomplete_or_invalid_uncertainty_model() -> None:
    observations = (
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(0.002, 100.04),
        SelfHeatingObservation(0.003, 100.09),
    )

    with pytest.raises(ValueError, match="requires resistance standard uncertainties"):
        fit_zero_power_resistance(
            observations,
            measurement_current_standard_uncertainties_a=(1.0e-6,) * 3,
        )
    with pytest.raises(ValueError, match="count must match"):
        fit_zero_power_resistance(
            observations,
            resistance_standard_uncertainties_ohms=(0.01,) * 3,
            measurement_current_standard_uncertainties_a=(1.0e-6,) * 2,
        )
    with pytest.raises(ValueError, match="greater than zero"):
        fit_zero_power_resistance(
            observations,
            resistance_standard_uncertainties_ohms=(0.01,) * 3,
            measurement_current_standard_uncertainties_a=(1.0e-6, 0.0, 1.0e-6),
        )
    with pytest.raises(ValueError, match="between -1 and 1"):
        fit_zero_power_resistance(
            observations,
            resistance_standard_uncertainties_ohms=(0.01,) * 3,
            measurement_current_standard_uncertainties_a=(1.0e-6,) * 3,
            current_resistance_error_correlations=(0.0, 1.1, 0.0),
        )
    with pytest.raises(ValueError, match="require measurement-current"):
        fit_zero_power_resistance(
            observations,
            resistance_standard_uncertainties_ohms=(0.01,) * 3,
            current_resistance_error_correlations=(0.0,) * 3,
        )


def test_zero_power_fit_york_rejects_unrepresentable_weighting_range() -> None:
    observations = (
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(0.002, 100.04),
        SelfHeatingObservation(0.003, 100.09),
    )

    with pytest.raises(ValueError, match="unrepresentable weighting range"):
        fit_zero_power_resistance(
            observations,
            resistance_standard_uncertainties_ohms=(1.0e-13,) * 3,
            measurement_current_standard_uncertainties_a=(
                1.0e-20,
                5.0e147,
                1.0e-20,
            ),
        )


def test_self_heating_coefficient_rejects_errors_in_variables_fit() -> None:
    fit = fit_zero_power_resistance(
        (
            SelfHeatingObservation(0.001, 100.01),
            SelfHeatingObservation(0.002, 100.04),
            SelfHeatingObservation(0.003, 100.09),
        ),
        resistance_standard_uncertainties_ohms=(0.001, 0.001, 0.001),
        measurement_current_standard_uncertainties_a=(1.0e-7, 1.0e-7, 1.0e-7),
        context=SelfHeatingExperimentContext(medium="air"),
    )
    temperatures = evaluate_zero_power_fit_temperatures(
        fit,
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    with pytest.raises(ValueError, match="does not yet support errors-in-variables"):
        evaluate_self_heating_coefficient(temperatures)


def test_zero_power_fit_york_evidence_direct_construction_recomputes_fit() -> None:
    observations, current_uncertainties, resistance_uncertainties = (
        _york_reference_case()
    )
    produced = fit_zero_power_resistance(
        observations,
        resistance_standard_uncertainties_ohms=resistance_uncertainties,
        measurement_current_standard_uncertainties_a=current_uncertainties,
    )

    direct = ZeroPowerResistanceFitEvidence(
        observations=observations,
        residuals_ohms=produced.evidence.residuals_ohms,
        resistance_standard_uncertainties_ohms=resistance_uncertainties,
        measurement_current_standard_uncertainties_a=current_uncertainties,
    )

    assert direct.method == "york_errors_in_variables_resistance_vs_current_squared"
    assert direct.chi_squared == pytest.approx(produced.evidence.chi_squared)
    assert direct.current_resistance_error_correlations == (0.0,) * len(observations)


def test_zero_power_fit_uncertainty_matches_repeated_two_current_case() -> None:
    low_current = 0.001
    high_current = math.sqrt(2.0) * 0.001
    fit = fit_zero_power_resistance(
        (
            SelfHeatingObservation(low_current, 100.009),
            SelfHeatingObservation(high_current, 100.019),
            SelfHeatingObservation(low_current, 100.011),
            SelfHeatingObservation(high_current, 100.021),
        )
    )

    uncertainty = estimate_zero_power_fit_uncertainty(fit)

    assert isinstance(uncertainty, ZeroPowerResistanceFitUncertaintyResult)
    assert uncertainty.fit_result is fit
    assert uncertainty.method == "residual_variance_scaled_least_squares"
    assert uncertainty.parameter_names == (
        "zero_power_resistance_ohms",
        "resistance_slope_ohms_per_a2",
    )
    assert uncertainty.residual_variance_ohms_squared == pytest.approx(2.0e-6)
    assert uncertainty.zero_power_resistance_variance_ohms_squared == pytest.approx(
        5.0e-6
    )
    assert uncertainty.zero_power_resistance_standard_uncertainty_ohms == pytest.approx(
        math.sqrt(5.0e-6)
    )
    assert uncertainty.resistance_slope_variance_ohms_squared_per_a4 == pytest.approx(
        2.0e6
    )
    assert (
        uncertainty.resistance_slope_standard_uncertainty_ohms_per_a2
        == pytest.approx(math.sqrt(2.0e6))
    )
    assert (
        uncertainty.zero_power_resistance_slope_covariance_ohms_squared_per_a2
        == pytest.approx(-3.0)
    )
    assert uncertainty.parameter_covariance_matrix[0] == pytest.approx((5.0e-6, -3.0))
    assert uncertainty.parameter_covariance_matrix[1] == pytest.approx((-3.0, 2.0e6))


def test_zero_power_fit_uncertainty_matches_three_distinct_current_levels() -> None:
    fit = fit_zero_power_resistance(
        (
            SelfHeatingObservation(1.0, 102.0),
            SelfHeatingObservation(2.0, 108.0),
            SelfHeatingObservation(3.0, 119.0),
        )
    )

    uncertainty = estimate_zero_power_fit_uncertainty(fit)

    assert uncertainty.residual_variance_ohms_squared == pytest.approx(9.0 / 98.0)
    assert uncertainty.zero_power_resistance_variance_ohms_squared == pytest.approx(
        9.0 / 98.0
    )
    assert uncertainty.resistance_slope_variance_ohms_squared_per_a4 == pytest.approx(
        27.0 / 9604.0
    )
    assert (
        uncertainty.zero_power_resistance_slope_covariance_ohms_squared_per_a2
        == pytest.approx(-9.0 / 686.0)
    )


def test_zero_power_fit_uncertainty_is_zero_for_exact_line() -> None:
    fit = fit_zero_power_resistance(
        (
            SelfHeatingObservation(1.0, 101.0),
            SelfHeatingObservation(2.0, 104.0),
            SelfHeatingObservation(3.0, 109.0),
        )
    )

    uncertainty = estimate_zero_power_fit_uncertainty(fit)

    assert uncertainty.residual_variance_ohms_squared == pytest.approx(0.0, abs=1e-20)
    assert uncertainty.parameter_covariance_matrix[0] == pytest.approx(
        (0.0, 0.0), abs=1e-20
    )
    assert uncertainty.parameter_covariance_matrix[1] == pytest.approx(
        (0.0, 0.0), abs=1e-20
    )


def test_zero_power_fit_uncertainty_rejects_wrong_result_type() -> None:
    with pytest.raises(TypeError, match="ZeroPowerResistanceFitResult"):
        estimate_zero_power_fit_uncertainty(object())  # type: ignore[arg-type]


def _repeated_two_current_fit(
    *,
    context: SelfHeatingExperimentContext | None = None,
) -> ZeroPowerResistanceFitResult:
    low_current = 0.001
    high_current = math.sqrt(2.0) * 0.001
    return fit_zero_power_resistance(
        (
            SelfHeatingObservation(low_current, 100.009),
            SelfHeatingObservation(high_current, 100.019),
            SelfHeatingObservation(low_current, 100.011),
            SelfHeatingObservation(high_current, 100.021),
        ),
        context=context,
    )


def test_zero_power_fit_retains_nonbehavioral_experiment_context() -> None:
    context = SelfHeatingExperimentContext(
        medium="flowing water",
        flow_condition="approximately 0.4 m/s",
    )

    fit = _repeated_two_current_fit(context=context)

    assert fit.evidence.context is context
    assert fit.zero_power_resistance_ohms == pytest.approx(100.0)
    assert fit.resistance_slope_ohms_per_a2 == pytest.approx(10000.0)


def test_zero_power_fit_rejects_wrong_context_type() -> None:
    with pytest.raises(TypeError, match="SelfHeatingExperimentContext"):
        fit_zero_power_resistance(
            (
                SelfHeatingObservation(0.001, 100.01),
                SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02),
                SelfHeatingObservation(0.002, 100.04),
            ),
            context=object(),  # type: ignore[arg-type]
        )


def test_zero_power_fit_temperature_evaluation_reports_observed_and_fitted_values() -> (
    None
):
    fit = _repeated_two_current_fit()
    model = _LinearTwoOhmPerCelsiusModel()

    result = evaluate_zero_power_fit_temperatures(fit, model=model)

    assert isinstance(result, ZeroPowerResistanceFitTemperatureResult)
    assert result.fit_result is fit
    assert result.model is model
    assert result.zero_power_temperature_c == pytest.approx(0.0)
    assert result.observed_temperatures_c == pytest.approx(
        (0.0045, 0.0095, 0.0055, 0.0105)
    )
    assert result.fitted_temperatures_c == pytest.approx((0.005, 0.01, 0.005, 0.01))
    assert result.observed_temperature_rises_c == pytest.approx(
        result.observed_temperatures_c
    )
    assert result.fitted_temperature_rises_c == pytest.approx(
        result.fitted_temperatures_c
    )
    assert result.temperature_residuals_c == pytest.approx(
        (-0.0005, -0.0005, 0.0005, 0.0005)
    )
    assert result.observed_dissipated_powers_w == pytest.approx(
        (100.009e-6, 200.038e-6, 100.011e-6, 200.042e-6)
    )
    assert result.fitted_dissipated_powers_w == pytest.approx(
        (100.01e-6, 200.04e-6, 100.01e-6, 200.04e-6)
    )


def test_zero_power_fit_temperature_evaluation_retains_negative_fitted_rises() -> None:
    fit = fit_zero_power_resistance(
        (
            SelfHeatingObservation(0.001, 100.03),
            SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02),
            SelfHeatingObservation(0.002, 100.00),
        )
    )

    result = evaluate_zero_power_fit_temperatures(
        fit,
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    assert fit.resistance_slope_direction == "negative"
    assert all(rise < 0.0 for rise in result.fitted_temperature_rises_c)


def test_zero_power_fit_temperature_uncertainty_preserves_fit_covariance() -> None:
    temperatures = evaluate_zero_power_fit_temperatures(
        _repeated_two_current_fit(),
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    result = propagate_zero_power_fit_temperature_uncertainty(temperatures)

    assert isinstance(result, ZeroPowerResistanceFitTemperatureUncertaintyResult)
    assert result.temperature_result is temperatures
    assert result.fit_uncertainty.fit_result is temperatures.fit_result
    assert result.propagation_method == "first_order_fit_parameter_covariance"
    assert result.parameter_names == (
        "zero_power_resistance_ohms",
        "resistance_slope_ohms_per_a2",
    )
    assert result.zero_power_temperature_parameter_sensitivity_vector == pytest.approx(
        (0.5, 0.0)
    )
    assert result.zero_power_temperature_variance_celsius_squared == pytest.approx(
        1.25e-6
    )
    assert result.zero_power_temperature_standard_uncertainty_c == pytest.approx(
        math.sqrt(1.25e-6)
    )
    expected_vectors = (
        (0.5, 0.5e-6),
        (0.5, 1.0e-6),
        (0.5, 0.5e-6),
        (0.5, 1.0e-6),
    )
    for actual, expected in zip(
        result.fitted_temperature_parameter_sensitivity_vectors,
        expected_vectors,
        strict=True,
    ):
        assert actual == pytest.approx(expected)
    assert result.fitted_temperature_variances_celsius_squared == pytest.approx(
        (2.5e-7, 2.5e-7, 2.5e-7, 2.5e-7)
    )
    assert result.fitted_temperature_rise_variances_celsius_squared == pytest.approx(
        (5.0e-7, 2.0e-6, 5.0e-7, 2.0e-6)
    )
    assert result.fitted_temperature_rise_standard_uncertainties_c == pytest.approx(
        (math.sqrt(5.0e-7), math.sqrt(2.0e-6)) * 2
    )


def test_zero_power_fit_temperature_uncertainty_uses_weighted_fit_covariance() -> None:
    fit = fit_zero_power_resistance(
        (
            SelfHeatingObservation(1.0, 101.0),
            SelfHeatingObservation(2.0, 104.0),
            SelfHeatingObservation(3.0, 109.0),
        ),
        resistance_standard_uncertainties_ohms=(0.5, 0.5, 0.5),
    )
    temperatures = evaluate_zero_power_fit_temperatures(
        fit,
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    result = propagate_zero_power_fit_temperature_uncertainty(temperatures)

    assert result.fit_uncertainty.method == "resistance_standard_uncertainties"
    assert result.zero_power_temperature_standard_uncertainty_c == pytest.approx(0.25)
    assert all(
        uncertainty > 0.0
        for uncertainty in result.fitted_temperature_rise_standard_uncertainties_c
    )


def test_zero_power_fit_temperature_uncertainty_is_zero_for_exact_fit() -> None:
    fit = fit_zero_power_resistance(
        (
            SelfHeatingObservation(1.0, 101.0),
            SelfHeatingObservation(2.0, 104.0),
            SelfHeatingObservation(3.0, 109.0),
        )
    )
    temperatures = evaluate_zero_power_fit_temperatures(
        fit,
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    result = propagate_zero_power_fit_temperature_uncertainty(temperatures)

    assert result.zero_power_temperature_standard_uncertainty_c == pytest.approx(
        0.0, abs=1e-20
    )
    assert result.fitted_temperature_standard_uncertainties_c == pytest.approx(
        (0.0, 0.0, 0.0), abs=1e-20
    )
    assert result.fitted_temperature_rise_standard_uncertainties_c == pytest.approx(
        (0.0, 0.0, 0.0), abs=1e-20
    )


def test_zero_power_fit_temperature_evaluation_rejects_wrong_result_type() -> None:
    with pytest.raises(TypeError, match="ZeroPowerResistanceFitResult"):
        evaluate_zero_power_fit_temperatures(
            object(),  # type: ignore[arg-type]
            model=_LinearTwoOhmPerCelsiusModel(),
        )


def test_zero_power_fit_temperature_uncertainty_rejects_wrong_result_type() -> None:
    with pytest.raises(TypeError, match="ZeroPowerResistanceFitTemperatureResult"):
        propagate_zero_power_fit_temperature_uncertainty(
            object(),  # type: ignore[arg-type]
        )


def test_zero_power_fit_temperature_result_rejects_nonfinite_model_output() -> None:
    class NonFiniteTemperatureModel(_LinearTwoOhmPerCelsiusModel):
        def resistance_to_celsius(self, resistance_ohms: float) -> float:
            return math.inf

    with pytest.raises(ValueError, match="temperature must be finite"):
        evaluate_zero_power_fit_temperatures(
            _repeated_two_current_fit(),
            model=NonFiniteTemperatureModel(),
        )


def test_zero_power_fit_temperature_uncertainty_rejects_mismatched_fit() -> None:
    temperatures = evaluate_zero_power_fit_temperatures(
        _repeated_two_current_fit(),
        model=_LinearTwoOhmPerCelsiusModel(),
    )
    other_fit = fit_zero_power_resistance(
        (
            SelfHeatingObservation(1.0, 101.0),
            SelfHeatingObservation(2.0, 104.0),
            SelfHeatingObservation(3.0, 109.0),
        )
    )

    with pytest.raises(ValueError, match="retained zero-power fit"):
        ZeroPowerResistanceFitTemperatureUncertaintyResult(
            temperature_result=temperatures,
            fit_uncertainty=estimate_zero_power_fit_uncertainty(other_fit),
        )


def test_zero_power_fit_temperature_uncertainty_rejects_nonfinite_sensitivity() -> None:
    class NonFiniteSensitivityModel(_LinearTwoOhmPerCelsiusModel):
        def temperature_sensitivity_celsius_per_ohm(
            self, temperature_c: float
        ) -> float:
            return math.inf

    temperatures = evaluate_zero_power_fit_temperatures(
        _repeated_two_current_fit(),
        model=NonFiniteSensitivityModel(),
    )

    with pytest.raises(ValueError, match="sensitivity must be finite"):
        propagate_zero_power_fit_temperature_uncertainty(temperatures)


def _context_bound_temperature_fit() -> ZeroPowerResistanceFitTemperatureResult:
    fit = _repeated_two_current_fit(
        context=SelfHeatingExperimentContext(
            medium="flowing water",
            flow_condition="approximately 0.4 m/s",
            mounting="fully immersed probe",
        )
    )
    return evaluate_zero_power_fit_temperatures(
        fit,
        model=_LinearTwoOhmPerCelsiusModel(),
    )


def test_self_heating_coefficient_reports_context_bound_power_relationship() -> None:
    temperatures = _context_bound_temperature_fit()

    result = evaluate_self_heating_coefficient(temperatures)

    assert isinstance(result, SelfHeatingCoefficientResult)
    assert result.temperature_result is temperatures
    assert result.context is temperatures.fit_result.evidence.context
    assert result.method == (
        "least_squares_temperature_rise_vs_fitted_power_through_origin"
    )
    assert result.distinct_current_count == 2
    assert result.current_squared_levels_a2 == pytest.approx((1.0e-6, 2.0e-6))
    assert result.fitted_temperature_rises_c == pytest.approx((0.005, 0.01))
    assert result.fitted_dissipated_powers_w == pytest.approx((100.01e-6, 200.04e-6))
    pointwise = result.pointwise_self_heating_coefficients_c_per_w
    assert pointwise == pytest.approx((0.005 / 100.01e-6, 0.01 / 200.04e-6))
    assert min(pointwise) < result.self_heating_coefficient_c_per_w < max(pointwise)
    assert result.self_heating_coefficient_c_per_mw == pytest.approx(
        result.self_heating_coefficient_c_per_w / 1000.0
    )
    assert result.dissipation_constant_w_per_c == pytest.approx(
        1.0 / result.self_heating_coefficient_c_per_w
    )
    assert result.dissipation_constant_mw_per_c == pytest.approx(
        1000.0 / result.self_heating_coefficient_c_per_w
    )
    assert len(result.coefficient_fit_residuals_c) == 2
    assert result.coefficient_rms_residual_c > 0.0
    assert result.coefficient_max_absolute_residual_c > 0.0


def test_self_heating_coefficient_uses_distinct_current_levels_once() -> None:
    context = SelfHeatingExperimentContext(setup="dry-block calibrator")
    observations = (
        SelfHeatingObservation(0.001, 100.009),
        SelfHeatingObservation(0.001, 100.010),
        SelfHeatingObservation(0.001, 100.011),
        SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.019),
        SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.021),
    )
    temperatures = evaluate_zero_power_fit_temperatures(
        fit_zero_power_resistance(observations, context=context),
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    result = evaluate_self_heating_coefficient(temperatures)

    assert result.distinct_current_count == 2
    assert len(result.fitted_dissipated_powers_w) == 2
    assert len(result.fitted_temperature_rises_c) == 2


def test_self_heating_coefficient_requires_retained_context() -> None:
    temperatures = evaluate_zero_power_fit_temperatures(
        _repeated_two_current_fit(),
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    with pytest.raises(ValueError, match="experiment context"):
        evaluate_self_heating_coefficient(temperatures)


def test_self_heating_coefficient_rejects_nonpositive_slope() -> None:
    context = SelfHeatingExperimentContext(medium="still air")
    fit = fit_zero_power_resistance(
        (
            SelfHeatingObservation(0.001, 100.03),
            SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02),
            SelfHeatingObservation(0.002, 100.00),
        ),
        context=context,
    )
    temperatures = evaluate_zero_power_fit_temperatures(
        fit,
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    with pytest.raises(ValueError, match="positive resistance slope"):
        evaluate_self_heating_coefficient(temperatures)


def test_self_heating_coefficient_rejects_wrong_result_type() -> None:
    with pytest.raises(TypeError, match="ZeroPowerResistanceFitTemperatureResult"):
        evaluate_self_heating_coefficient(object())  # type: ignore[arg-type]


def test_self_heating_coefficient_uncertainty_propagates_fit_covariance() -> None:
    coefficient = evaluate_self_heating_coefficient(_context_bound_temperature_fit())

    result = propagate_self_heating_coefficient_uncertainty(coefficient)

    assert isinstance(result, SelfHeatingCoefficientUncertaintyResult)
    assert result.coefficient_result is coefficient
    assert (
        result.fit_uncertainty.fit_result is coefficient.temperature_result.fit_result
    )
    assert result.parameter_names == (
        "zero_power_resistance_ohms",
        "resistance_slope_ohms_per_a2",
    )
    assert result.propagation_method == "first_order_fit_parameter_covariance"
    assert all(
        math.isfinite(value)
        for value in result.self_heating_coefficient_parameter_sensitivity_vector
    )
    assert result.self_heating_coefficient_standard_uncertainty_c_per_w > 0.0
    assert result.self_heating_coefficient_standard_uncertainty_c_per_mw == (
        pytest.approx(
            result.self_heating_coefficient_standard_uncertainty_c_per_w / 1000.0
        )
    )
    expected_dissipation_uncertainty = (
        result.self_heating_coefficient_standard_uncertainty_c_per_w
        / coefficient.self_heating_coefficient_c_per_w**2
    )
    assert result.dissipation_constant_standard_uncertainty_w_per_c == pytest.approx(
        expected_dissipation_uncertainty
    )
    assert result.dissipation_constant_standard_uncertainty_mw_per_c == pytest.approx(
        1000.0 * expected_dissipation_uncertainty
    )


def test_self_heating_coefficient_sensitivity_matches_finite_difference() -> None:
    context = SelfHeatingExperimentContext(setup="oil bath")
    current_squared = (1.0, 4.0, 9.0)

    def coefficient_for(r0: float, slope: float) -> float:
        observations = tuple(
            SelfHeatingObservation(
                math.sqrt(value),
                r0 + slope * value,
            )
            for value in current_squared
        )
        temperatures = evaluate_zero_power_fit_temperatures(
            fit_zero_power_resistance(observations, context=context),
            model=_LinearTwoOhmPerCelsiusModel(),
        )
        return evaluate_self_heating_coefficient(
            temperatures
        ).self_heating_coefficient_c_per_w

    r0 = 100.0
    slope = 1.0
    observations = tuple(
        SelfHeatingObservation(math.sqrt(value), r0 + slope * value)
        for value in current_squared
    )
    temperatures = evaluate_zero_power_fit_temperatures(
        fit_zero_power_resistance(observations, context=context),
        model=_LinearTwoOhmPerCelsiusModel(),
    )
    coefficient = evaluate_self_heating_coefficient(temperatures)
    uncertainty = propagate_self_heating_coefficient_uncertainty(coefficient)

    r0_step = 1.0e-4
    slope_step = 1.0e-6
    expected_r0_sensitivity = (
        coefficient_for(r0 + r0_step, slope) - coefficient_for(r0 - r0_step, slope)
    ) / (2.0 * r0_step)
    expected_slope_sensitivity = (
        coefficient_for(r0, slope + slope_step)
        - coefficient_for(r0, slope - slope_step)
    ) / (2.0 * slope_step)

    sensitivities = uncertainty.self_heating_coefficient_parameter_sensitivity_vector
    assert sensitivities[0] == pytest.approx(expected_r0_sensitivity, rel=1e-6)
    assert sensitivities[1] == pytest.approx(expected_slope_sensitivity, rel=1e-6)


def test_self_heating_coefficient_uncertainty_is_zero_for_exact_fit() -> None:
    context = SelfHeatingExperimentContext(medium="stirred water")
    temperatures = evaluate_zero_power_fit_temperatures(
        fit_zero_power_resistance(
            (
                SelfHeatingObservation(1.0, 101.0),
                SelfHeatingObservation(2.0, 104.0),
                SelfHeatingObservation(3.0, 109.0),
            ),
            context=context,
        ),
        model=_LinearTwoOhmPerCelsiusModel(),
    )
    coefficient = evaluate_self_heating_coefficient(temperatures)

    result = propagate_self_heating_coefficient_uncertainty(coefficient)

    assert (
        result.self_heating_coefficient_standard_uncertainty_c_per_w
        == pytest.approx(0.0, abs=1e-20)
    )
    assert result.dissipation_constant_standard_uncertainty_w_per_c == pytest.approx(
        0.0, abs=1e-20
    )


def test_self_heating_coefficient_uncertainty_rejects_wrong_result_type() -> None:
    with pytest.raises(TypeError, match="SelfHeatingCoefficientResult"):
        propagate_self_heating_coefficient_uncertainty(
            object()  # type: ignore[arg-type]
        )


def test_self_heating_coefficient_uncertainty_rejects_nonfinite_sensitivity() -> None:
    class NonFiniteSensitivityModel(_LinearTwoOhmPerCelsiusModel):
        def temperature_sensitivity_celsius_per_ohm(
            self, temperature_c: float
        ) -> float:
            return math.inf

    context = SelfHeatingExperimentContext(setup="dry-block calibrator")
    temperatures = evaluate_zero_power_fit_temperatures(
        _repeated_two_current_fit(context=context),
        model=NonFiniteSensitivityModel(),
    )
    coefficient = evaluate_self_heating_coefficient(temperatures)

    with pytest.raises(ValueError, match="sensitivity must be finite"):
        propagate_self_heating_coefficient_uncertainty(coefficient)


def test_self_heating_coefficient_pt100_sensitivity_matches_finite_difference() -> None:
    context = SelfHeatingExperimentContext(setup="water bath")
    model = catalog.get_model("pt100")
    current_squared = (1.0e-6, 4.0e-6, 9.0e-6)

    def coefficient_for(r0: float, slope: float) -> float:
        observations = tuple(
            SelfHeatingObservation(math.sqrt(value), r0 + slope * value)
            for value in current_squared
        )
        temperatures = evaluate_zero_power_fit_temperatures(
            fit_zero_power_resistance(observations, context=context),
            model=model,
        )
        return evaluate_self_heating_coefficient(
            temperatures
        ).self_heating_coefficient_c_per_w

    r0 = 100.0
    slope = 10000.0
    observations = tuple(
        SelfHeatingObservation(math.sqrt(value), r0 + slope * value)
        for value in current_squared
    )
    temperatures = evaluate_zero_power_fit_temperatures(
        fit_zero_power_resistance(observations, context=context),
        model=model,
    )
    uncertainty = propagate_self_heating_coefficient_uncertainty(
        evaluate_self_heating_coefficient(temperatures)
    )

    r0_step = 1.0e-4
    slope_step = 1.0
    expected_r0_sensitivity = (
        coefficient_for(r0 + r0_step, slope) - coefficient_for(r0 - r0_step, slope)
    ) / (2.0 * r0_step)
    expected_slope_sensitivity = (
        coefficient_for(r0, slope + slope_step)
        - coefficient_for(r0, slope - slope_step)
    ) / (2.0 * slope_step)

    actual = uncertainty.self_heating_coefficient_parameter_sensitivity_vector
    assert actual[0] == pytest.approx(expected_r0_sensitivity, rel=1.0e-6)
    assert actual[1] == pytest.approx(expected_slope_sensitivity, rel=1.0e-6)


def test_self_heating_coefficient_reports_finite_range_dependence() -> None:
    context = SelfHeatingExperimentContext(medium="stirred water")
    model = _LinearTwoOhmPerCelsiusModel()

    def coefficient_for(currents: tuple[float, ...]) -> SelfHeatingCoefficientResult:
        observations = tuple(
            SelfHeatingObservation(current, 100.0 + 10000.0 * current**2)
            for current in currents
        )
        temperatures = evaluate_zero_power_fit_temperatures(
            fit_zero_power_resistance(observations, context=context),
            model=model,
        )
        return evaluate_self_heating_coefficient(temperatures)

    narrow = coefficient_for((0.001, 0.002, 0.003))
    wide = coefficient_for((0.001, 0.003, 0.005))

    assert (
        wide.self_heating_coefficient_c_per_w < narrow.self_heating_coefficient_c_per_w
    )
    assert wide.coefficient_rms_residual_c > narrow.coefficient_rms_residual_c
    assert max(wide.pointwise_self_heating_coefficients_c_per_w) > min(
        wide.pointwise_self_heating_coefficients_c_per_w
    )


def test_zero_power_fit_uncertainty_handles_difficult_current_geometry() -> None:
    def observations_for(
        currents: tuple[float, float, float],
        residual_offsets: tuple[float, float, float],
    ) -> tuple[SelfHeatingObservation, ...]:
        return tuple(
            SelfHeatingObservation(
                current,
                100.0 + 10000.0 * current**2 + residual,
            )
            for current, residual in zip(currents, residual_offsets, strict=True)
        )

    far = estimate_zero_power_fit_uncertainty(
        fit_zero_power_resistance(
            observations_for((0.001, 0.002, 0.003), (0.0, 1.0e-6, -1.0e-6))
        )
    )
    close = estimate_zero_power_fit_uncertainty(
        fit_zero_power_resistance(
            observations_for(
                (0.001, 0.001001, 0.001002),
                (0.0, 1.0e-6, -1.0e-6),
            )
        )
    )
    assert (
        close.resistance_slope_standard_uncertainty_ohms_per_a2
        > 1000.0 * far.resistance_slope_standard_uncertainty_ohms_per_a2
    )

    asymmetric = estimate_zero_power_fit_uncertainty(
        fit_zero_power_resistance(
            observations_for(
                (0.001, 0.00101, 0.01),
                (1.0e-6, -1.0e-6, 2.0e-6),
            )
        )
    )
    assert all(
        math.isfinite(value)
        for row in asymmetric.parameter_covariance_matrix
        for value in row
    )


def test_zero_power_fit_preserves_caller_observation_order() -> None:
    observations = (
        SelfHeatingObservation(0.002, 100.04),
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02),
    )

    result = fit_zero_power_resistance(observations)

    assert result.evidence.observations == observations
    assert result.evidence.fitted_resistances_ohms == pytest.approx(
        tuple(observation.resistance_ohms for observation in observations)
    )


def test_zero_power_fit_reports_nonzero_residual_diagnostics() -> None:
    observations = (
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.021),
        SelfHeatingObservation(0.002, 100.04),
        SelfHeatingObservation(math.sqrt(5.0) * 0.001, 100.052),
    )

    result = fit_zero_power_resistance(observations)

    assert result.evidence.residual_degrees_of_freedom == 2
    assert result.evidence.rms_residual_ohms > 0.0
    assert result.evidence.max_absolute_residual_ohms > 0.0
    assert result.evidence.residual_standard_deviation_ohms > 0.0
    assert len(result.evidence.residuals_ohms) == len(observations)
    assert math.fsum(result.evidence.residuals_ohms) == pytest.approx(0.0, abs=1e-12)


def test_zero_power_fit_retains_negative_slope_as_evidence() -> None:
    observations = (
        SelfHeatingObservation(0.001, 100.03),
        SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02),
        SelfHeatingObservation(0.002, 100.00),
    )

    result = fit_zero_power_resistance(observations)

    assert result.zero_power_resistance_ohms == pytest.approx(100.04)
    assert result.resistance_slope_ohms_per_a2 < 0.0
    assert result.resistance_slope_direction == "negative"


def test_zero_power_fit_retains_zero_slope_as_evidence() -> None:
    result = fit_zero_power_resistance(
        (
            SelfHeatingObservation(0.001, 100.0),
            SelfHeatingObservation(0.002, 100.0),
            SelfHeatingObservation(0.003, 100.0),
        )
    )

    assert result.zero_power_resistance_ohms == pytest.approx(100.0)
    assert result.resistance_slope_ohms_per_a2 == pytest.approx(0.0)
    assert result.resistance_slope_direction == "zero"


def test_zero_power_fit_handles_large_resistance_scale_without_sum_overflow() -> None:
    result = fit_zero_power_resistance(
        (
            SelfHeatingObservation(1.0e-154, 1.0e308),
            SelfHeatingObservation(1.1e-154, 1.0e308),
            SelfHeatingObservation(1.2e-154, 1.0e308),
        )
    )

    assert result.zero_power_resistance_ohms == 1.0e308
    assert result.resistance_slope_ohms_per_a2 == 0.0
    assert result.evidence.rms_residual_ohms == 0.0


def test_zero_power_fit_accepts_generator() -> None:
    observations = (
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02),
        SelfHeatingObservation(0.002, 100.04),
    )

    result = fit_zero_power_resistance(observation for observation in observations)

    assert result.zero_power_resistance_ohms == pytest.approx(100.0)


def test_zero_power_fit_requires_three_observations() -> None:
    with pytest.raises(ValueError, match="at least three"):
        fit_zero_power_resistance(
            (
                SelfHeatingObservation(0.001, 100.01),
                SelfHeatingObservation(0.002, 100.04),
            )
        )


def test_zero_power_fit_requires_two_distinct_current_levels() -> None:
    with pytest.raises(ValueError, match="distinct current levels"):
        fit_zero_power_resistance(
            (
                SelfHeatingObservation(0.001, 100.00),
                SelfHeatingObservation(0.001, 100.01),
                SelfHeatingObservation(0.001, 100.02),
            )
        )


def test_zero_power_fit_rejects_non_observation() -> None:
    with pytest.raises(TypeError, match="SelfHeatingObservation"):
        fit_zero_power_resistance(
            (
                SelfHeatingObservation(0.001, 100.01),
                SelfHeatingObservation(0.002, 100.04),
                100.0,  # type: ignore[arg-type]
            )
        )


def test_zero_power_fit_rejects_nonpositive_intercept() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        fit_zero_power_resistance(
            (
                SelfHeatingObservation(1.0, 3.0),
                SelfHeatingObservation(2.0, 15.0),
                SelfHeatingObservation(3.0, 35.0),
            )
        )


def test_zero_power_fit_result_rejects_inconsistent_intercept() -> None:
    result = fit_zero_power_resistance(
        (
            SelfHeatingObservation(0.001, 100.01),
            SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02),
            SelfHeatingObservation(0.002, 100.04),
        )
    )

    with pytest.raises(ValueError, match="consistent with retained fit evidence"):
        ZeroPowerResistanceFitResult(
            zero_power_resistance_ohms=99.0,
            resistance_slope_ohms_per_a2=result.resistance_slope_ohms_per_a2,
            evidence=result.evidence,
        )


def test_zero_power_fit_result_rejects_inconsistent_slope() -> None:
    result = fit_zero_power_resistance(
        (
            SelfHeatingObservation(0.001, 100.01),
            SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02),
            SelfHeatingObservation(0.002, 100.04),
        )
    )

    with pytest.raises(ValueError, match="consistent with retained fit evidence"):
        ZeroPowerResistanceFitResult(
            zero_power_resistance_ohms=result.zero_power_resistance_ohms,
            resistance_slope_ohms_per_a2=9999.0,
            evidence=result.evidence,
        )


def test_zero_power_fit_evidence_rejects_residual_count_mismatch() -> None:
    observations = (
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02),
        SelfHeatingObservation(0.002, 100.04),
    )

    with pytest.raises(ValueError, match="residual count"):
        ZeroPowerResistanceFitEvidence(
            observations=observations,
            residuals_ohms=(0.0, 0.0),
        )


def test_zero_power_fit_evidence_rejects_inconsistent_residuals() -> None:
    observations = (
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02),
        SelfHeatingObservation(0.002, 100.04),
    )

    with pytest.raises(ValueError, match="consistent with retained observations"):
        ZeroPowerResistanceFitEvidence(
            observations=observations,
            residuals_ohms=(1.0, 1.0, 1.0),
        )


class _LinearTwoOhmPerCelsiusModel:
    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        return (resistance_ohms - 100.0) / 2.0

    def celsius_to_resistance(self, temperature_c: float) -> float:
        return 100.0 + 2.0 * temperature_c

    def resistance_sensitivity_ohms_per_celsius(self, temperature_c: float) -> float:
        return 2.0

    def temperature_sensitivity_celsius_per_ohm(self, temperature_c: float) -> float:
        return 0.5


def _sqrt2_uncertainty_case() -> tuple[
    TwoCurrentZeroPowerResult,
    TwoCurrentInputStandardUncertainties,
]:
    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02)
    zero_power = extrapolate_zero_power_resistance(low, high)
    inputs = TwoCurrentInputStandardUncertainties(
        low_current_standard_uncertainty_a=0.0,
        low_resistance_standard_uncertainty_ohms=0.001,
        high_current_standard_uncertainty_a=0.0,
        high_resistance_standard_uncertainty_ohms=0.001,
    )
    return zero_power, inputs


def test_two_current_input_uncertainties_normalize_numeric_values() -> None:
    inputs = TwoCurrentInputStandardUncertainties(
        low_current_standard_uncertainty_a=1,
        low_resistance_standard_uncertainty_ohms=2,
        high_current_standard_uncertainty_a=3,
        high_resistance_standard_uncertainty_ohms=4,
    )

    assert inputs.standard_uncertainty_vector == (1.0, 2.0, 3.0, 4.0)
    assert inputs.input_parameter_names == (
        "low_current_a",
        "low_resistance_ohms",
        "high_current_a",
        "high_resistance_ohms",
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "low_current_standard_uncertainty_a",
        "low_resistance_standard_uncertainty_ohms",
        "high_current_standard_uncertainty_a",
        "high_resistance_standard_uncertainty_ohms",
    ],
)
def test_two_current_input_uncertainties_reject_invalid_values(
    field_name: str,
) -> None:
    kwargs: dict[str, object] = {
        "low_current_standard_uncertainty_a": 0.0,
        "low_resistance_standard_uncertainty_ohms": 0.0,
        "high_current_standard_uncertainty_a": 0.0,
        "high_resistance_standard_uncertainty_ohms": 0.0,
    }
    kwargs[field_name] = -1.0
    with pytest.raises(ValueError, match="non-negative"):
        TwoCurrentInputStandardUncertainties(**kwargs)  # type: ignore[arg-type]

    kwargs[field_name] = math.inf
    with pytest.raises(ValueError, match="finite"):
        TwoCurrentInputStandardUncertainties(**kwargs)  # type: ignore[arg-type]

    kwargs[field_name] = True
    with pytest.raises(TypeError):
        TwoCurrentInputStandardUncertainties(**kwargs)  # type: ignore[arg-type]


def test_two_current_input_correlation_matrix_normalizes_and_exposes_order() -> None:
    correlations = TwoCurrentInputCorrelationMatrix(
        correlation_matrix=(
            (1, 0, 0, 0),
            (0, 1, 0, 0.25),
            (0, 0, 1, 0),
            (0, 0.25, 0, 1),
        )
    )

    assert correlations.input_parameter_names == (
        "low_current_a",
        "low_resistance_ohms",
        "high_current_a",
        "high_resistance_ohms",
    )
    assert correlations.correlation_matrix[1][3] == pytest.approx(0.25)
    assert correlations.correlation_matrix[3][1] == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("matrix", "message"),
    [
        (
            (
                (1.0, 0.2, 0.0, 0.0),
                (0.1, 1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            ),
            "symmetric",
        ),
        (
            (
                (0.9, 0.0, 0.0, 0.0),
                (0.0, 1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            ),
            "diagonal",
        ),
        (
            (
                (1.0, 1.1, 0.0, 0.0),
                (1.1, 1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            ),
            "between -1 and 1",
        ),
        (
            (
                (1.0, 0.9, 0.9, 0.0),
                (0.9, 1.0, -0.9, 0.0),
                (0.9, -0.9, 1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            ),
            "positive semidefinite",
        ),
    ],
)
def test_two_current_input_correlation_matrix_rejects_invalid_matrices(
    matrix: tuple[tuple[float, ...], ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        TwoCurrentInputCorrelationMatrix(correlation_matrix=matrix)


def test_two_current_input_correlation_matrix_accepts_valid_low_rank_matrix() -> None:
    correlations = TwoCurrentInputCorrelationMatrix(
        correlation_matrix=(
            (1.0, -0.9999791765107585, 0.5626028914348433, -0.530474000927361),
            (-0.9999791765107585, 1.0, -0.5679263889742487, 0.5359335209517727),
            (0.5626028914348433, -0.5679263889742489, 1.0, -0.999263914301841),
            (-0.530474000927361, 0.5359335209517727, -0.9992639143018411, 1.0),
        )
    )

    assert correlations.correlation_matrix[0][0] == 1.0


def test_two_current_input_correlation_matrix_tolerates_float_roundoff_at_bounds() -> (
    None
):
    correlations = TwoCurrentInputCorrelationMatrix(
        correlation_matrix=(
            (1.0000000000000002, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, -1.0000000000000002),
            (0.0, 0.0, -1.0000000000000002, 1.0),
        )
    )

    assert correlations.correlation_matrix[0][0] == 1.0
    assert correlations.correlation_matrix[2][3] == -1.0
    assert correlations.correlation_matrix[3][2] == -1.0


def test_correlated_zero_power_uncertainty_uses_full_covariance() -> None:
    zero_power, inputs = _sqrt2_uncertainty_case()
    correlations = TwoCurrentInputCorrelationMatrix(
        correlation_matrix=(
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 1.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 1.0, 0.0, 1.0),
        )
    )

    result = propagate_two_current_zero_power_uncertainty(
        zero_power,
        input_standard_uncertainties=inputs,
        input_correlation_matrix=correlations,
    )

    assert result.propagation_method == "first_order_correlated_inputs"
    assert result.input_correlation_matrix is correlations
    assert result.input_covariance_matrix[1][3] == pytest.approx(1.0e-6)
    assert result.zero_power_resistance_variance_ohms_squared == pytest.approx(1.0e-6)
    assert result.zero_power_resistance_standard_uncertainty_ohms == pytest.approx(
        0.001
    )


def test_correlated_current_uncertainty_uses_current_sensitivities() -> None:
    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02)
    zero_power = extrapolate_zero_power_resistance(low, high)
    inputs = TwoCurrentInputStandardUncertainties(
        low_current_standard_uncertainty_a=1.0e-6,
        low_resistance_standard_uncertainty_ohms=0.0,
        high_current_standard_uncertainty_a=1.0e-6,
        high_resistance_standard_uncertainty_ohms=0.0,
    )
    correlations = TwoCurrentInputCorrelationMatrix(
        correlation_matrix=(
            (1.0, 0.0, 1.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (1.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    )

    result = propagate_two_current_zero_power_uncertainty(
        zero_power,
        input_standard_uncertainties=inputs,
        input_correlation_matrix=correlations,
    )

    expected = (-40.0 + 20.0 * math.sqrt(2.0)) * 1.0e-6
    assert result.zero_power_resistance_standard_uncertainty_ohms == pytest.approx(
        abs(expected)
    )


def test_identity_correlation_reproduces_independent_propagation() -> None:
    zero_power, inputs = _sqrt2_uncertainty_case()
    identity = TwoCurrentInputCorrelationMatrix(
        correlation_matrix=(
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    )

    independent = propagate_two_current_zero_power_uncertainty(
        zero_power,
        input_standard_uncertainties=inputs,
    )
    correlated = propagate_two_current_zero_power_uncertainty(
        zero_power,
        input_standard_uncertainties=inputs,
        input_correlation_matrix=identity,
    )

    assert correlated.zero_power_resistance_variance_ohms_squared == pytest.approx(
        independent.zero_power_resistance_variance_ohms_squared
    )
    for correlated_row, independent_row in zip(
        correlated.input_covariance_matrix,
        independent.input_covariance_matrix,
        strict=True,
    ):
        assert correlated_row == pytest.approx(independent_row)


def test_correlated_resistance_error_cancels_from_temperature_rises() -> None:
    zero_power, inputs = _sqrt2_uncertainty_case()
    temperatures = evaluate_two_current_temperatures(
        zero_power,
        model=_LinearTwoOhmPerCelsiusModel(),
    )
    correlations = TwoCurrentInputCorrelationMatrix(
        correlation_matrix=(
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 1.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 1.0, 0.0, 1.0),
        )
    )

    result = propagate_two_current_temperature_uncertainty(
        temperatures,
        input_standard_uncertainties=inputs,
        input_correlation_matrix=correlations,
    )

    assert result.propagation_method == "first_order_correlated_inputs"
    assert result.zero_power_temperature_standard_uncertainty_c == pytest.approx(0.0005)
    assert result.low_current_temperature_rise_standard_uncertainty_c == pytest.approx(
        0.0,
        abs=1.0e-15,
    )
    assert result.high_current_temperature_rise_standard_uncertainty_c == pytest.approx(
        0.0,
        abs=1.0e-15,
    )


def test_zero_power_uncertainty_matches_sqrt2_resistance_only_case() -> None:
    zero_power, inputs = _sqrt2_uncertainty_case()

    result = propagate_two_current_zero_power_uncertainty(
        zero_power,
        input_standard_uncertainties=inputs,
    )

    assert isinstance(result, TwoCurrentZeroPowerUncertaintyResult)
    assert result.zero_power_result is zero_power
    assert result.input_standard_uncertainties is inputs
    assert result.propagation_method == "first_order_independent_inputs"
    assert result.input_parameter_names == inputs.input_parameter_names
    assert result.zero_power_resistance_input_sensitivity_vector[1] == pytest.approx(
        2.0
    )
    assert result.zero_power_resistance_input_sensitivity_vector[3] == pytest.approx(
        -1.0
    )
    assert result.zero_power_resistance_standard_uncertainty_ohms == pytest.approx(
        math.sqrt(5.0) * 0.001
    )
    assert result.zero_power_resistance_variance_ohms_squared == pytest.approx(5.0e-6)


def test_zero_power_uncertainty_includes_current_uncertainty() -> None:
    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(math.sqrt(2.0) * 0.001, 100.02)
    zero_power = extrapolate_zero_power_resistance(low, high)
    inputs = TwoCurrentInputStandardUncertainties(
        low_current_standard_uncertainty_a=1.0e-6,
        low_resistance_standard_uncertainty_ohms=0.0,
        high_current_standard_uncertainty_a=1.0e-6,
        high_resistance_standard_uncertainty_ohms=0.0,
    )

    result = propagate_two_current_zero_power_uncertainty(
        zero_power,
        input_standard_uncertainties=inputs,
    )

    sensitivities = result.zero_power_resistance_input_sensitivity_vector
    assert sensitivities[0] == pytest.approx(-40.0)
    assert sensitivities[2] == pytest.approx(20.0 * math.sqrt(2.0))
    assert result.zero_power_resistance_standard_uncertainty_ohms == pytest.approx(
        math.sqrt(2400.0) * 1.0e-6
    )


def test_zero_power_current_sensitivity_is_zero_without_resistance_change() -> None:
    low = SelfHeatingObservation(0.001, 100.0)
    high = SelfHeatingObservation(0.002, 100.0)
    zero_power = extrapolate_zero_power_resistance(low, high)
    inputs = TwoCurrentInputStandardUncertainties(
        low_current_standard_uncertainty_a=1.0e-6,
        low_resistance_standard_uncertainty_ohms=0.0,
        high_current_standard_uncertainty_a=1.0e-6,
        high_resistance_standard_uncertainty_ohms=0.0,
    )

    result = propagate_two_current_zero_power_uncertainty(
        zero_power,
        input_standard_uncertainties=inputs,
    )

    assert result.zero_power_resistance_input_sensitivity_vector[0] == 0.0
    assert result.zero_power_resistance_input_sensitivity_vector[2] == 0.0
    assert result.zero_power_resistance_standard_uncertainty_ohms == 0.0


def test_temperature_uncertainty_propagates_shared_inputs_directly() -> None:
    zero_power, inputs = _sqrt2_uncertainty_case()
    temperatures = evaluate_two_current_temperatures(
        zero_power,
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    result = propagate_two_current_temperature_uncertainty(
        temperatures,
        input_standard_uncertainties=inputs,
    )

    assert isinstance(result, TwoCurrentSelfHeatingTemperatureUncertaintyResult)
    assert result.temperature_result is temperatures
    assert result.zero_power_uncertainty.zero_power_result is zero_power
    assert result.propagation_method == "first_order_independent_inputs"
    assert result.input_parameter_names == inputs.input_parameter_names
    assert result.zero_power_temperature_standard_uncertainty_c == pytest.approx(
        0.5 * math.sqrt(5.0) * 0.001
    )
    assert result.low_current_temperature_standard_uncertainty_c == pytest.approx(
        0.0005
    )
    assert result.high_current_temperature_standard_uncertainty_c == pytest.approx(
        0.0005
    )
    assert result.low_current_temperature_rise_standard_uncertainty_c == pytest.approx(
        math.sqrt(0.5) * 0.001
    )
    assert result.high_current_temperature_rise_standard_uncertainty_c == pytest.approx(
        math.sqrt(2.0) * 0.001
    )


def test_temperature_rise_uncertainty_is_not_naive_rss_of_derived_temperatures() -> (
    None
):
    zero_power, inputs = _sqrt2_uncertainty_case()
    temperatures = evaluate_two_current_temperatures(
        zero_power,
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    result = propagate_two_current_temperature_uncertainty(
        temperatures,
        input_standard_uncertainties=inputs,
    )
    naive = math.hypot(
        result.low_current_temperature_standard_uncertainty_c,
        result.zero_power_temperature_standard_uncertainty_c,
    )

    assert result.low_current_temperature_rise_standard_uncertainty_c < naive
    assert (
        result.low_current_temperature_rise_input_sensitivity_vector
        == pytest.approx((20.0, -0.5, -10.0 * math.sqrt(2.0), 0.5))
    )


def test_two_current_uncertainty_allows_zero_standard_uncertainties() -> None:
    low = SelfHeatingObservation(0.001, 100.01)
    high = SelfHeatingObservation(0.002, 100.04)
    zero_power = extrapolate_zero_power_resistance(low, high)
    inputs = TwoCurrentInputStandardUncertainties(
        low_current_standard_uncertainty_a=0.0,
        low_resistance_standard_uncertainty_ohms=0.0,
        high_current_standard_uncertainty_a=0.0,
        high_resistance_standard_uncertainty_ohms=0.0,
    )
    temperatures = evaluate_two_current_temperatures(
        zero_power,
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    resistance_result = propagate_two_current_zero_power_uncertainty(
        zero_power,
        input_standard_uncertainties=inputs,
    )
    temperature_result = propagate_two_current_temperature_uncertainty(
        temperatures,
        input_standard_uncertainties=inputs,
    )

    assert resistance_result.zero_power_resistance_standard_uncertainty_ohms == 0.0
    assert temperature_result.zero_power_temperature_standard_uncertainty_c == 0.0
    assert temperature_result.low_current_temperature_rise_standard_uncertainty_c == 0.0
    assert (
        temperature_result.high_current_temperature_rise_standard_uncertainty_c == 0.0
    )


def test_zero_power_uncertainty_grows_as_current_levels_get_close() -> None:
    low = SelfHeatingObservation(0.001, 100.01)
    far_high = SelfHeatingObservation(0.002, 100.04)
    close_current = 0.001001
    close_high = SelfHeatingObservation(
        close_current,
        100.0 + 10000.0 * close_current**2,
    )
    inputs = TwoCurrentInputStandardUncertainties(
        low_current_standard_uncertainty_a=0.0,
        low_resistance_standard_uncertainty_ohms=1.0e-4,
        high_current_standard_uncertainty_a=0.0,
        high_resistance_standard_uncertainty_ohms=1.0e-4,
    )

    far = propagate_two_current_zero_power_uncertainty(
        extrapolate_zero_power_resistance(low, far_high),
        input_standard_uncertainties=inputs,
    )
    close = propagate_two_current_zero_power_uncertainty(
        extrapolate_zero_power_resistance(low, close_high),
        input_standard_uncertainties=inputs,
    )

    assert (
        close.zero_power_resistance_standard_uncertainty_ohms
        > 100.0 * far.zero_power_resistance_standard_uncertainty_ohms
    )


def test_two_current_zero_power_uncertainty_result_derives_internal_state() -> None:
    zero_power = extrapolate_zero_power_resistance(
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(0.002, 100.04),
    )
    inputs = TwoCurrentInputStandardUncertainties(
        low_current_standard_uncertainty_a=1.0e-7,
        low_resistance_standard_uncertainty_ohms=1.0e-4,
        high_current_standard_uncertainty_a=1.0e-7,
        high_resistance_standard_uncertainty_ohms=1.0e-4,
    )

    direct = TwoCurrentZeroPowerUncertaintyResult(
        zero_power_result=zero_power,
        input_standard_uncertainties=inputs,
    )
    produced = propagate_two_current_zero_power_uncertainty(
        zero_power,
        input_standard_uncertainties=inputs,
    )

    assert direct.zero_power_resistance_input_sensitivity_vector == pytest.approx(
        produced.zero_power_resistance_input_sensitivity_vector
    )
    assert direct.zero_power_resistance_variance_ohms_squared == pytest.approx(
        produced.zero_power_resistance_variance_ohms_squared
    )


def test_two_current_temperature_result_derives_temperatures_from_retained_state() -> (
    None
):
    zero_power = extrapolate_zero_power_resistance(
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(0.002, 100.04),
    )
    model = _LinearTwoOhmPerCelsiusModel()

    direct = TwoCurrentSelfHeatingTemperatureResult(
        zero_power_result=zero_power,
        model=model,
    )

    assert direct.zero_power_temperature_c == pytest.approx(0.0)
    assert direct.low_current_temperature_c == pytest.approx(0.005)
    assert direct.high_current_temperature_c == pytest.approx(0.02)


def test_two_current_temperature_uncertainty_rejects_mismatched_zero_power_result() -> (
    None
):
    first_zero_power = extrapolate_zero_power_resistance(
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(0.002, 100.04),
    )
    second_zero_power = extrapolate_zero_power_resistance(
        SelfHeatingObservation(0.001, 100.02),
        SelfHeatingObservation(0.002, 100.08),
    )
    inputs = TwoCurrentInputStandardUncertainties(
        low_current_standard_uncertainty_a=0.0,
        low_resistance_standard_uncertainty_ohms=1.0e-4,
        high_current_standard_uncertainty_a=0.0,
        high_resistance_standard_uncertainty_ohms=1.0e-4,
    )
    temperatures = TwoCurrentSelfHeatingTemperatureResult(
        zero_power_result=first_zero_power,
        model=_LinearTwoOhmPerCelsiusModel(),
    )
    mismatched = TwoCurrentZeroPowerUncertaintyResult(
        zero_power_result=second_zero_power,
        input_standard_uncertainties=inputs,
    )

    with pytest.raises(ValueError, match="retained zero-power result"):
        TwoCurrentSelfHeatingTemperatureUncertaintyResult(
            temperature_result=temperatures,
            zero_power_uncertainty=mismatched,
        )


def test_two_current_uncertainty_rejects_wrong_argument_types() -> None:
    zero_power, inputs = _sqrt2_uncertainty_case()
    temperatures = evaluate_two_current_temperatures(
        zero_power,
        model=_LinearTwoOhmPerCelsiusModel(),
    )

    with pytest.raises(TypeError, match="TwoCurrentZeroPowerResult"):
        propagate_two_current_zero_power_uncertainty(
            100.0,  # type: ignore[arg-type]
            input_standard_uncertainties=inputs,
        )
    with pytest.raises(TypeError, match="TwoCurrentInputStandardUncertainties"):
        propagate_two_current_zero_power_uncertainty(
            zero_power,
            input_standard_uncertainties=100.0,  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="TwoCurrentInputCorrelationMatrix"):
        propagate_two_current_zero_power_uncertainty(
            zero_power,
            input_standard_uncertainties=inputs,
            input_correlation_matrix=100.0,  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="TwoCurrentSelfHeatingTemperatureResult"):
        propagate_two_current_temperature_uncertainty(
            zero_power,  # type: ignore[arg-type]
            input_standard_uncertainties=inputs,
        )
    with pytest.raises(TypeError, match="TwoCurrentInputStandardUncertainties"):
        propagate_two_current_temperature_uncertainty(
            temperatures,
            input_standard_uncertainties=100.0,  # type: ignore[arg-type]
        )


def test_temperature_uncertainty_propagates_model_sensitivity_error() -> None:
    class FailingSensitivityModel(_LinearTwoOhmPerCelsiusModel):
        def temperature_sensitivity_celsius_per_ohm(
            self, temperature_c: float
        ) -> float:
            raise RuntimeError("sensitivity failed")

    zero_power, inputs = _sqrt2_uncertainty_case()
    temperatures = evaluate_two_current_temperatures(
        zero_power,
        model=FailingSensitivityModel(),
    )

    with pytest.raises(RuntimeError, match="sensitivity failed"):
        propagate_two_current_temperature_uncertainty(
            temperatures,
            input_standard_uncertainties=inputs,
        )


def test_temperature_uncertainty_rejects_nonfinite_model_sensitivity() -> None:
    class NonFiniteSensitivityModel(_LinearTwoOhmPerCelsiusModel):
        def temperature_sensitivity_celsius_per_ohm(
            self, temperature_c: float
        ) -> float:
            return math.inf

    zero_power, inputs = _sqrt2_uncertainty_case()
    temperatures = evaluate_two_current_temperatures(
        zero_power,
        model=NonFiniteSensitivityModel(),
    )

    with pytest.raises(ValueError, match="sensitivity must be finite"):
        propagate_two_current_temperature_uncertainty(
            temperatures,
            input_standard_uncertainties=inputs,
        )


def test_zero_power_extrapolation_assessment_reports_two_current_limitations() -> None:
    result = extrapolate_zero_power_resistance(
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(0.002, 100.04),
    )

    assessment = assess_zero_power_extrapolation(result)

    assert isinstance(assessment, ZeroPowerExtrapolationAssessment)
    assert assessment.observation_count == 2
    assert assessment.distinct_current_count == 2
    assert assessment.repeated_current_level_count == 0
    assert assessment.residual_degrees_of_freedom == 0
    assert assessment.minimum_measurement_current_a == pytest.approx(0.001)
    assert assessment.maximum_measurement_current_a == pytest.approx(0.002)
    assert assessment.minimum_to_maximum_current_ratio == pytest.approx(0.5)
    assert assessment.zero_power_extrapolation_distance_in_current_squared_spans == (
        pytest.approx(1.0 / 3.0)
    )
    assert assessment.resistance_slope_direction == "positive"
    assert not assessment.supports_residual_consistency_assessment
    assert not assessment.supports_linearity_assessment
    assert not assessment.supports_repeated_level_assessment
    assert assessment.warning_codes == ("two_current_exact_line_no_residual_test",)
    assert assessment.has_warnings
    assert "exactly determine" in assessment.warnings[0].message


def test_zero_power_extrapolation_assessment_reports_two_level_fit_limit() -> None:
    result = fit_zero_power_resistance(
        [
            SelfHeatingObservation(0.001, 100.01),
            SelfHeatingObservation(0.002, 100.04),
            SelfHeatingObservation(0.001, 100.011),
            SelfHeatingObservation(0.002, 100.039),
        ]
    )

    assessment = assess_zero_power_extrapolation(result)

    assert assessment.observation_count == 4
    assert assessment.distinct_current_count == 2
    assert assessment.repeated_current_level_count == 2
    assert assessment.residual_degrees_of_freedom == 2
    assert assessment.supports_residual_consistency_assessment
    assert not assessment.supports_linearity_assessment
    assert assessment.supports_repeated_level_assessment
    assert assessment.warning_codes == ("only_two_distinct_current_levels",)


def test_zero_power_extrapolation_assessment_reports_missing_repeats() -> None:
    result = fit_zero_power_resistance(
        [
            SelfHeatingObservation(0.001, 100.01),
            SelfHeatingObservation(0.002, 100.04),
            SelfHeatingObservation(0.003, 100.09),
        ]
    )

    assessment = assess_zero_power_extrapolation(result)

    assert assessment.supports_residual_consistency_assessment
    assert assessment.supports_linearity_assessment
    assert not assessment.supports_repeated_level_assessment
    assert assessment.warning_codes == ("no_repeated_current_levels",)


def test_zero_power_extrapolation_assessment_can_have_no_structural_warnings() -> None:
    result = fit_zero_power_resistance(
        [
            SelfHeatingObservation(0.001, 100.01),
            SelfHeatingObservation(0.002, 100.04),
            SelfHeatingObservation(0.003, 100.09),
            SelfHeatingObservation(0.001, 100.01),
        ]
    )

    assessment = assess_zero_power_extrapolation(result)

    assert assessment.distinct_current_count == 3
    assert assessment.repeated_current_level_count == 1
    assert assessment.supports_linearity_assessment
    assert assessment.supports_repeated_level_assessment
    assert assessment.warning_codes == ()
    assert assessment.warnings == ()
    assert not assessment.has_warnings


def test_zero_power_extrapolation_assessment_warns_on_nonpositive_slope() -> None:
    result = extrapolate_zero_power_resistance(
        SelfHeatingObservation(0.001, 100.02),
        SelfHeatingObservation(0.002, 100.01),
    )

    assessment = assess_zero_power_extrapolation(result)

    assert assessment.resistance_slope_direction == "negative"
    assert assessment.warning_codes == (
        "two_current_exact_line_no_residual_test",
        "nonpositive_resistance_slope",
    )


def test_zero_power_extrapolation_assessment_exposes_close_current_geometry() -> None:
    result = extrapolate_zero_power_resistance(
        SelfHeatingObservation(0.001, 100.01),
        SelfHeatingObservation(0.001001, 100.01002001),
    )

    assessment = assess_zero_power_extrapolation(result)

    assert assessment.minimum_to_maximum_current_ratio == pytest.approx(1.0 / 1.001)
    assert assessment.zero_power_extrapolation_distance_in_current_squared_spans > 499.0
    assert assessment.warning_codes == ("two_current_exact_line_no_residual_test",)


def test_zero_power_extrapolation_assessment_rejects_wrong_result_type() -> None:
    with pytest.raises(TypeError, match="TwoCurrentZeroPowerResult"):
        ZeroPowerExtrapolationAssessment(result=object())  # type: ignore[arg-type]


def test_zero_power_extrapolation_warning_rejects_unknown_code() -> None:
    with pytest.raises(ValueError, match="Unknown zero-power extrapolation warning"):
        ZeroPowerExtrapolationWarning("unknown")  # type: ignore[arg-type]
