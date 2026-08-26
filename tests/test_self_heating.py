# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
from dataclasses import FrozenInstanceError

import pytest

from rtd_sensor import catalog
from rtd_sensor.self_heating import (
    SelfHeatingObservation,
    TwoCurrentInputStandardUncertainties,
    TwoCurrentSelfHeatingTemperatureResult,
    TwoCurrentSelfHeatingTemperatureUncertaintyResult,
    TwoCurrentZeroPowerEvidence,
    TwoCurrentZeroPowerResult,
    TwoCurrentZeroPowerUncertaintyResult,
    ZeroPowerResistanceFitEvidence,
    ZeroPowerResistanceFitResult,
    ZeroPowerResistanceFitUncertaintyResult,
    estimate_zero_power_fit_uncertainty,
    evaluate_two_current_temperatures,
    extrapolate_zero_power_resistance,
    fit_zero_power_resistance,
    propagate_two_current_temperature_uncertainty,
    propagate_two_current_zero_power_uncertainty,
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
