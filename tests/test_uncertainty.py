# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from rtd_sensor import pt100, pt1000, uncertainty
from rtd_sensor.exceptions import RTDOutOfRangeError
from rtd_sensor.fitting import (
    CalibrationObservation,
    CallendarVanDusenFitResult,
    fit_callendar_van_dusen,
    fit_iec60751_r0,
    fit_polynomial,
)
from rtd_sensor.models import (
    CallendarVanDusenRTDModel,
    IEC60751RTDModel,
    PolynomialRTDModel,
)


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


def test_fit_covariance_propagates_iec_r0_variance_to_resistance() -> None:
    fit = fit_iec60751_r0(
        (
            CalibrationObservation(
                0.0,
                100.0,
                standard_uncertainty_ohms=0.01,
            ),
        ),
        minimum_temperature_c=-50.0,
        maximum_temperature_c=150.0,
    )

    propagated = uncertainty.propagate_fit_covariance_to_resistance(
        100.0,
        fit_result=fit,
    )

    ratio = IEC60751RTDModel(r0_ohms=1.0).celsius_to_resistance(100.0)
    assert propagated.temperature_c == 100.0
    assert propagated.resistance_ohms == pytest.approx(100.0 * ratio)
    assert propagated.parameter_sensitivity_vector == pytest.approx((ratio,))
    assert propagated.resistance_variance_ohms_squared == pytest.approx(
        (ratio * 0.01) ** 2
    )
    assert propagated.resistance_standard_uncertainty_ohms == pytest.approx(
        ratio * 0.01
    )
    assert propagated.parameter_covariance is fit.evidence.parameter_covariance


def test_fit_covariance_propagates_polynomial_covariance_with_correlation() -> None:
    fit = fit_polynomial(
        (
            CalibrationObservation(
                0.0,
                100.0,
                standard_uncertainty_ohms=1.0,
            ),
            CalibrationObservation(
                10.0,
                120.0,
                standard_uncertainty_ohms=1.0,
            ),
        ),
        degree=1,
        minimum_temperature_c=0.0,
        maximum_temperature_c=8.0,
    )

    propagated = uncertainty.propagate_fit_covariance_to_resistance(
        8.0,
        fit_result=fit,
    )

    assert fit.model.reference_temperature_c == 4.0
    assert propagated.resistance_ohms == pytest.approx(116.0)
    assert propagated.parameter_sensitivity_vector == pytest.approx((1.0, 4.0))
    # With independent 1-ohm standard uncertainties at 0 and 10 C, the fitted
    # line predicts R(8 C) as 0.2*R(0 C) + 0.8*R(10 C), so the variance is
    # 0.2**2 + 0.8**2 = 0.68 ohm^2. This includes the fitted-parameter
    # covariance term rather than treating a0 and a1 as independent.
    assert propagated.resistance_variance_ohms_squared == pytest.approx(0.68)
    assert propagated.resistance_standard_uncertainty_ohms == pytest.approx(
        math.sqrt(0.68)
    )

    at_reference = uncertainty.propagate_fit_covariance_to_resistance(
        fit.model.reference_temperature_c,
        fit_result=fit,
    )
    covariance = fit.evidence.parameter_covariance
    assert covariance is not None
    assert at_reference.parameter_sensitivity_vector == pytest.approx((1.0, 0.0))
    assert at_reference.resistance_variance_ohms_squared == pytest.approx(
        covariance.covariance_matrix[0][0]
    )


def test_fit_covariance_propagation_requires_available_covariance() -> None:
    fit = fit_iec60751_r0(
        (CalibrationObservation(0.0, 100.0),),
        minimum_temperature_c=-50.0,
        maximum_temperature_c=150.0,
    )

    with pytest.raises(
        ValueError,
        match=(
            "residual_variance_requires_positive_degrees_of_freedom.*"
            "fitted model itself remains valid"
        ),
    ):
        uncertainty.propagate_fit_covariance_to_resistance(0.0, fit_result=fit)


def test_fit_covariance_propagation_rejects_unsupported_result_type() -> None:
    with pytest.raises(TypeError, match="fit_result"):
        uncertainty.propagate_fit_covariance_to_resistance(
            0.0,
            fit_result=object(),  # type: ignore[arg-type]
        )


def test_fit_covariance_propagation_uses_model_temperature_range() -> None:
    fit = fit_iec60751_r0(
        (
            CalibrationObservation(
                0.0,
                100.0,
                standard_uncertainty_ohms=0.01,
            ),
        ),
        minimum_temperature_c=-10.0,
        maximum_temperature_c=10.0,
    )

    with pytest.raises(RTDOutOfRangeError, match="between -10.*10"):
        uncertainty.propagate_fit_covariance_to_resistance(20.0, fit_result=fit)


def test_fit_covariance_propagates_quadratic_polynomial_sensitivities() -> None:
    fit = fit_polynomial(
        (
            CalibrationObservation(
                0.0,
                100.0,
                standard_uncertainty_ohms=1.0,
            ),
            CalibrationObservation(
                5.0,
                112.5,
                standard_uncertainty_ohms=1.0,
            ),
            CalibrationObservation(
                10.0,
                130.0,
                standard_uncertainty_ohms=1.0,
            ),
        ),
        degree=2,
        minimum_temperature_c=0.0,
        maximum_temperature_c=8.0,
    )

    propagated = uncertainty.propagate_fit_covariance_to_resistance(
        8.0,
        fit_result=fit,
    )

    assert fit.model.reference_temperature_c == 4.0
    assert propagated.resistance_ohms == pytest.approx(122.4)
    assert propagated.parameter_sensitivity_vector == pytest.approx((1.0, 4.0, 16.0))
    # Quadratic interpolation at 8 C from independent observations at 0, 5,
    # and 10 C has Lagrange weights (-0.12, 0.64, 0.48). With 1-ohm standard
    # uncertainty on each observation, the prediction variance is the sum of
    # their squared weights.
    assert propagated.resistance_variance_ohms_squared == pytest.approx(0.6544)


def test_fit_covariance_propagates_iec_r0_variance_to_temperature() -> None:
    fit = fit_iec60751_r0(
        (
            CalibrationObservation(
                0.0,
                100.0,
                standard_uncertainty_ohms=0.01,
            ),
        ),
        minimum_temperature_c=-50.0,
        maximum_temperature_c=150.0,
    )
    resistance = fit.model.celsius_to_resistance(100.0)

    propagated = uncertainty.propagate_fit_covariance_to_temperature(
        resistance,
        fit_result=fit,
    )

    ratio = IEC60751RTDModel(r0_ohms=1.0).celsius_to_resistance(100.0)
    inverse_sensitivity = fit.model.temperature_sensitivity_celsius_per_ohm(100.0)
    expected_parameter_sensitivity = -inverse_sensitivity * ratio
    expected_variance = (expected_parameter_sensitivity * 0.01) ** 2

    assert propagated.resistance_ohms == pytest.approx(resistance)
    assert propagated.temperature_c == pytest.approx(100.0)
    assert propagated.resistance_parameter_sensitivity_vector == pytest.approx((ratio,))
    assert propagated.temperature_sensitivity_celsius_per_ohm == pytest.approx(
        inverse_sensitivity
    )
    assert propagated.parameter_sensitivity_vector == pytest.approx(
        (expected_parameter_sensitivity,)
    )
    assert propagated.temperature_variance_celsius_squared == pytest.approx(
        expected_variance
    )
    assert propagated.temperature_standard_uncertainty_c == pytest.approx(
        math.sqrt(expected_variance)
    )


def test_fit_covariance_temperature_sensitivity_matches_finite_difference() -> None:
    fit = fit_iec60751_r0(
        (
            CalibrationObservation(
                0.0,
                100.0,
                standard_uncertainty_ohms=0.01,
            ),
        ),
        minimum_temperature_c=-50.0,
        maximum_temperature_c=150.0,
    )
    resistance = fit.model.celsius_to_resistance(100.0)
    propagated = uncertainty.propagate_fit_covariance_to_temperature(
        resistance,
        fit_result=fit,
    )

    step_ohms = 1.0e-4
    lower_model = IEC60751RTDModel(
        r0_ohms=fit.model.r0_ohms - step_ohms,
        minimum_temperature_c=fit.model.minimum_temperature_c,
        maximum_temperature_c=fit.model.maximum_temperature_c,
    )
    upper_model = IEC60751RTDModel(
        r0_ohms=fit.model.r0_ohms + step_ohms,
        minimum_temperature_c=fit.model.minimum_temperature_c,
        maximum_temperature_c=fit.model.maximum_temperature_c,
    )
    numerical_sensitivity = (
        upper_model.resistance_to_celsius(resistance)
        - lower_model.resistance_to_celsius(resistance)
    ) / (2.0 * step_ohms)

    assert propagated.parameter_sensitivity_vector[0] == pytest.approx(
        numerical_sensitivity,
        rel=1e-8,
        abs=1e-10,
    )


def test_fit_covariance_propagates_polynomial_variance_to_temperature() -> None:
    fit = fit_polynomial(
        (
            CalibrationObservation(
                0.0,
                100.0,
                standard_uncertainty_ohms=1.0,
            ),
            CalibrationObservation(
                10.0,
                120.0,
                standard_uncertainty_ohms=1.0,
            ),
        ),
        degree=1,
        minimum_temperature_c=0.0,
        maximum_temperature_c=8.0,
    )
    resistance = fit.model.celsius_to_resistance(8.0)

    propagated = uncertainty.propagate_fit_covariance_to_temperature(
        resistance,
        fit_result=fit,
    )
    resistance_propagated = uncertainty.propagate_fit_covariance_to_resistance(
        8.0,
        fit_result=fit,
    )
    inverse_sensitivity = fit.model.temperature_sensitivity_celsius_per_ohm(8.0)

    assert propagated.temperature_c == pytest.approx(8.0)
    assert propagated.resistance_parameter_sensitivity_vector == pytest.approx(
        (1.0, 4.0)
    )
    assert propagated.parameter_sensitivity_vector == pytest.approx(
        (-inverse_sensitivity, -4.0 * inverse_sensitivity)
    )
    assert propagated.temperature_variance_celsius_squared == pytest.approx(
        resistance_propagated.resistance_variance_ohms_squared * inverse_sensitivity**2
    )


def test_polynomial_temperature_parameter_sensitivity_matches_finite_difference() -> (
    None
):
    fit = fit_polynomial(
        (
            CalibrationObservation(
                0.0,
                100.0,
                standard_uncertainty_ohms=0.2,
            ),
            CalibrationObservation(
                10.0,
                120.0,
                standard_uncertainty_ohms=0.3,
            ),
            CalibrationObservation(
                20.0,
                142.0,
                standard_uncertainty_ohms=0.4,
            ),
        ),
        degree=2,
        minimum_temperature_c=0.0,
        maximum_temperature_c=20.0,
    )
    resistance = fit.model.celsius_to_resistance(8.0)
    propagated = uncertainty.propagate_fit_covariance_to_temperature(
        resistance,
        fit_result=fit,
    )

    a0 = fit.model.reference_resistance_ohms
    a1 = a0 * fit.model.coefficients[0]
    a2 = a0 * fit.model.coefficients[1]
    step = 1.0e-6
    perturbed_temperatures: list[float] = []
    for offset in (-step, step):
        model = PolynomialRTDModel(
            reference_resistance_ohms=a0,
            reference_temperature_c=fit.model.reference_temperature_c,
            coefficients=(a1 / a0, (a2 + offset) / a0),
            minimum_temperature_c=fit.model.minimum_temperature_c,
            maximum_temperature_c=fit.model.maximum_temperature_c,
        )
        perturbed_temperatures.append(model.resistance_to_celsius(resistance))

    numerical_sensitivity = (perturbed_temperatures[1] - perturbed_temperatures[0]) / (
        2.0 * step
    )
    assert propagated.parameter_sensitivity_vector[2] == pytest.approx(
        numerical_sensitivity,
        rel=1e-8,
        abs=1e-9,
    )


def test_fit_covariance_temperature_propagation_requires_available_covariance() -> None:
    fit = fit_iec60751_r0(
        (CalibrationObservation(0.0, 100.0),),
        minimum_temperature_c=-50.0,
        maximum_temperature_c=150.0,
    )

    with pytest.raises(ValueError, match="fitted model itself remains valid"):
        uncertainty.propagate_fit_covariance_to_temperature(
            100.0,
            fit_result=fit,
        )


def test_fit_covariance_temperature_propagation_uses_model_resistance_range() -> None:
    fit = fit_iec60751_r0(
        (
            CalibrationObservation(
                0.0,
                100.0,
                standard_uncertainty_ohms=0.01,
            ),
        ),
        minimum_temperature_c=-10.0,
        maximum_temperature_c=10.0,
    )
    out_of_range_resistance = IEC60751RTDModel(r0_ohms=100.0).celsius_to_resistance(
        20.0
    )

    with pytest.raises(RTDOutOfRangeError, match="declared model range"):
        uncertainty.propagate_fit_covariance_to_temperature(
            out_of_range_resistance,
            fit_result=fit,
        )


def test_fit_covariance_temperature_propagation_rejects_unsupported_result() -> None:
    with pytest.raises(TypeError, match="fit_result"):
        uncertainty.propagate_fit_covariance_to_temperature(
            100.0,
            fit_result=object(),  # type: ignore[arg-type]
        )


def _fitted_cvd_with_covariance() -> CallendarVanDusenFitResult:
    source = CallendarVanDusenRTDModel(
        r0_ohms=100.025,
        a=3.91e-3,
        b=-5.8e-7,
        c=-4.1e-12,
        minimum_temperature_c=-100.0,
        maximum_temperature_c=200.0,
    )
    observations = tuple(
        CalibrationObservation(
            temperature_c,
            source.celsius_to_resistance(temperature_c),
            standard_uncertainty_ohms=0.01,
        )
        for temperature_c in (-100.0, -50.0, 0.0, 50.0, 100.0, 200.0)
    )
    return fit_callendar_van_dusen(
        observations,
        fit_parameters=("r0_ohms", "a", "b", "c"),
    )


def test_fit_covariance_propagates_cvd_parameter_sensitivities_to_resistance() -> None:
    fit = _fitted_cvd_with_covariance()
    temperature_c = -25.0

    propagated = uncertainty.propagate_fit_covariance_to_resistance(
        temperature_c,
        fit_result=fit,
    )

    resistance = fit.model.celsius_to_resistance(temperature_c)
    c_basis = (temperature_c - 100.0) * temperature_c**3
    expected = (
        resistance / fit.model.r0_ohms,
        fit.model.r0_ohms * temperature_c,
        fit.model.r0_ohms * temperature_c**2,
        fit.model.r0_ohms * c_basis,
    )
    assert propagated.parameter_sensitivity_vector == pytest.approx(expected)
    assert propagated.resistance_variance_ohms_squared >= 0.0
    assert propagated.resistance_standard_uncertainty_ohms >= 0.0


def test_fit_covariance_propagates_cvd_covariance_to_temperature() -> None:
    fit = _fitted_cvd_with_covariance()
    temperature_c = 75.0
    resistance = fit.model.celsius_to_resistance(temperature_c)

    propagated = uncertainty.propagate_fit_covariance_to_temperature(
        resistance,
        fit_result=fit,
    )
    resistance_propagated = uncertainty.propagate_fit_covariance_to_resistance(
        temperature_c,
        fit_result=fit,
    )
    inverse_sensitivity = fit.model.temperature_sensitivity_celsius_per_ohm(
        temperature_c
    )

    assert propagated.temperature_c == pytest.approx(temperature_c)
    assert propagated.temperature_variance_celsius_squared == pytest.approx(
        resistance_propagated.resistance_variance_ohms_squared * inverse_sensitivity**2
    )
    assert propagated.parameter_sensitivity_vector == pytest.approx(
        tuple(
            -inverse_sensitivity * value
            for value in resistance_propagated.parameter_sensitivity_vector
        )
    )
