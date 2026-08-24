# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
from dataclasses import FrozenInstanceError

import pytest

from rtd_sensor.self_heating import (
    SelfHeatingObservation,
    TwoCurrentZeroPowerEvidence,
    TwoCurrentZeroPowerResult,
    extrapolate_zero_power_resistance,
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
