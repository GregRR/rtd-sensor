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
    evaluate_two_current_temperatures,
    extrapolate_zero_power_resistance,
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


def test_zero_power_uncertainty_current_sensitivity_is_zero_without_resistance_change() -> (
    None
):
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
