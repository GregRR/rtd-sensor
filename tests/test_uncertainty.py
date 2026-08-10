# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from rtd_sensor import pt100, pt1000, uncertainty
from rtd_sensor.models import CallendarVanDusenRTDModel, IEC60751RTDModel


def test_rectangular_bound_converts_to_standard_uncertainty() -> None:
    result = uncertainty.standard_uncertainty_from_bound(
        3.0,
        distribution="rectangular",
    )
    assert result == pytest.approx(math.sqrt(3.0))


def test_triangular_bound_converts_to_standard_uncertainty() -> None:
    result = uncertainty.standard_uncertainty_from_bound(
        6.0,
        distribution="triangular",
    )
    assert result == pytest.approx(math.sqrt(6.0))


def test_zero_bound_has_zero_standard_uncertainty() -> None:
    assert (
        uncertainty.standard_uncertainty_from_bound(
            0.0,
            distribution="rectangular",
        )
        == 0.0
    )


@pytest.mark.parametrize("value", [-1.0, math.inf, -math.inf, math.nan])
def test_bound_conversion_rejects_invalid_half_width(value: float) -> None:
    with pytest.raises(ValueError):
        uncertainty.standard_uncertainty_from_bound(
            value,
            distribution="rectangular",
        )


def test_bound_conversion_rejects_unknown_distribution() -> None:
    with pytest.raises(ValueError):
        uncertainty.standard_uncertainty_from_bound(
            1.0,
            distribution="normal",  # type: ignore[arg-type]
        )


def test_expanded_uncertainty_converts_back_to_standard_uncertainty() -> None:
    result = uncertainty.standard_uncertainty_from_expanded(
        0.20,
        coverage_factor=2.0,
    )
    assert result == pytest.approx(0.10)


@pytest.mark.parametrize("value", [-1.0, math.inf, -math.inf, math.nan])
def test_expanded_to_standard_rejects_invalid_uncertainty(value: float) -> None:
    with pytest.raises(ValueError):
        uncertainty.standard_uncertainty_from_expanded(
            value,
            coverage_factor=2.0,
        )


@pytest.mark.parametrize("coverage_factor", [0.0, -1.0, math.inf, math.nan])
def test_expanded_to_standard_rejects_invalid_coverage_factor(
    coverage_factor: float,
) -> None:
    with pytest.raises(ValueError):
        uncertainty.standard_uncertainty_from_expanded(
            0.20,
            coverage_factor=coverage_factor,
        )


def test_independent_uncertainties_combine_by_root_sum_square() -> None:
    result = uncertainty.combine_independent_standard_uncertainties(3.0, 4.0)
    assert result == pytest.approx(5.0)


def test_combination_supports_zero_and_single_components() -> None:
    assert uncertainty.combine_independent_standard_uncertainties(0.0) == 0.0
    assert uncertainty.combine_independent_standard_uncertainties(2.5) == 2.5


def test_combination_requires_at_least_one_component() -> None:
    with pytest.raises(ValueError):
        uncertainty.combine_independent_standard_uncertainties()


@pytest.mark.parametrize("value", [-1.0, math.inf, -math.inf, math.nan])
def test_combination_rejects_invalid_components(value: float) -> None:
    with pytest.raises(ValueError):
        uncertainty.combine_independent_standard_uncertainties(0.1, value)


def test_expanded_uncertainty_multiplies_by_coverage_factor() -> None:
    result = uncertainty.expanded_uncertainty(
        0.12,
        coverage_factor=2.0,
    )
    assert result == pytest.approx(0.24)


@pytest.mark.parametrize("value", [-1.0, math.inf, -math.inf, math.nan])
def test_expanded_uncertainty_rejects_invalid_standard_uncertainty(
    value: float,
) -> None:
    with pytest.raises(ValueError):
        uncertainty.expanded_uncertainty(value, coverage_factor=2.0)


@pytest.mark.parametrize("coverage_factor", [0.0, -1.0, math.inf, math.nan])
def test_expanded_uncertainty_rejects_invalid_coverage_factor(
    coverage_factor: float,
) -> None:
    with pytest.raises(ValueError):
        uncertainty.expanded_uncertainty(0.1, coverage_factor=coverage_factor)


def test_combination_rejects_nonfinite_result() -> None:
    with pytest.raises(ValueError):
        uncertainty.combine_independent_standard_uncertainties(
            float.fromhex("0x1.fffffffffffffp+1023"),
            float.fromhex("0x1.fffffffffffffp+1023"),
        )


def test_expanded_uncertainty_rejects_nonfinite_result() -> None:
    with pytest.raises(ValueError):
        uncertainty.expanded_uncertainty(
            float.fromhex("0x1.fffffffffffffp+1023"),
            coverage_factor=2.0,
        )


def test_pt100_sensitivity_at_zero_matches_analytical_derivative() -> None:
    assert pt100.resistance_sensitivity_ohms_per_celsius(0.0) == pytest.approx(
        0.39083,
        abs=1e-12,
    )
    assert pt100.temperature_sensitivity_celsius_per_ohm(0.0) == pytest.approx(
        1.0 / 0.39083,
        abs=1e-12,
    )


def test_pt1000_sensitivity_scales_with_r0() -> None:
    pt100_slope = pt100.resistance_sensitivity_ohms_per_celsius(100.0)
    pt1000_slope = pt1000.resistance_sensitivity_ohms_per_celsius(100.0)

    assert pt1000_slope == pytest.approx(10.0 * pt100_slope, abs=1e-12)
    assert pt1000.temperature_sensitivity_celsius_per_ohm(100.0) == pytest.approx(
        pt100.temperature_sensitivity_celsius_per_ohm(100.0) / 10.0,
        abs=1e-12,
    )


@pytest.mark.parametrize("temperature_c", [-150.0, -50.0, 50.0, 500.0])
def test_analytical_sensitivity_matches_central_difference(
    temperature_c: float,
) -> None:
    step_c = 1.0e-4
    numerical_slope = (
        pt100.celsius_to_resistance(temperature_c + step_c)
        - pt100.celsius_to_resistance(temperature_c - step_c)
    ) / (2.0 * step_c)

    assert pt100.resistance_sensitivity_ohms_per_celsius(
        temperature_c
    ) == pytest.approx(numerical_slope, rel=1e-9, abs=1e-10)


def test_negative_temperature_sensitivity_uses_full_cvd_derivative() -> None:
    # At -100 °C the C term contributes to the derivative.  This reference is
    # calculated independently from d(R/R0)/dT = A + 2BT + C*T^2*(4T-300).
    assert pt100.resistance_sensitivity_ohms_per_celsius(-100.0) == pytest.approx(
        0.4053081, abs=1e-12
    )


def test_configurable_iec_model_exposes_same_sensitivity_behavior() -> None:
    model = IEC60751RTDModel(r0_ohms=100.017)
    expected = pt100.resistance_sensitivity_ohms_per_celsius(50.0) * 1.00017
    assert model.resistance_sensitivity_ohms_per_celsius(50.0) == pytest.approx(
        expected,
        abs=1e-12,
    )


def test_custom_cvd_model_uses_supplied_coefficients_for_sensitivity() -> None:
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.0,
        a=4.0e-3,
        b=-5.0e-7,
        c=-4.0e-12,
        minimum_temperature_c=-50.0,
        maximum_temperature_c=250.0,
    )
    expected_slope = 100.0 * (4.0e-3 + 2.0 * -5.0e-7 * 100.0)
    assert model.resistance_sensitivity_ohms_per_celsius(100.0) == pytest.approx(
        expected_slope,
        abs=1e-12,
    )


def test_model_sensitivity_enforces_declared_temperature_range() -> None:
    model = IEC60751RTDModel(
        r0_ohms=100.0,
        minimum_temperature_c=0.0,
        maximum_temperature_c=100.0,
    )
    with pytest.raises(ValueError):
        model.resistance_sensitivity_ohms_per_celsius(-1.0)
    with pytest.raises(ValueError):
        model.temperature_sensitivity_celsius_per_ohm(101.0)
