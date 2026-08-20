# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
from dataclasses import FrozenInstanceError

import pytest

from rtd_sensor.exceptions import RTDFitError
from rtd_sensor.fitting import (
    CalibrationObservation,
    FitParameterCovariance,
    IEC60751R0FitEvidence,
    IEC60751R0FitResult,
    PolynomialFitEvidence,
    PolynomialFitResult,
    fit_iec60751_r0,
    fit_polynomial,
)
from rtd_sensor.models import IEC60751RTDModel, PolynomialRTDModel


def _synthetic_resistance(temperature_c: float) -> float:
    return 1000.0 * (
        1.0
        + 5.0e-3 * temperature_c
        + 4.0e-6 * temperature_c**2
        + 1.0e-9 * temperature_c**3
    )


def _iec_observations(
    r0_ohms: float,
    temperatures_c: tuple[float, ...],
) -> tuple[CalibrationObservation, ...]:
    model = IEC60751RTDModel(r0_ohms=r0_ohms)
    return tuple(
        CalibrationObservation(
            temperature_c,
            model.celsius_to_resistance(temperature_c),
        )
        for temperature_c in temperatures_c
    )


def test_fit_iec60751_r0_recovers_exact_characterized_model() -> None:
    observations = _iec_observations(100.037, (-50.0, 0.0, 100.0, 250.0))

    result = fit_iec60751_r0(observations)

    assert isinstance(result, IEC60751R0FitResult)
    assert isinstance(result.model, IEC60751RTDModel)
    assert isinstance(result.evidence, IEC60751R0FitEvidence)
    assert result.model.r0_ohms == pytest.approx(100.037, abs=1e-13)
    assert result.model.minimum_temperature_c == -50.0
    assert result.model.maximum_temperature_c == 250.0
    assert result.evidence.observation_count == 4
    assert result.evidence.fitted_parameter_count == 1
    assert result.evidence.residual_degrees_of_freedom == 3
    assert result.evidence.observation_minimum_temperature_c == -50.0
    assert result.evidence.observation_maximum_temperature_c == 250.0
    assert result.evidence.rms_residual_ohms < 1e-12
    assert result.evidence.max_absolute_residual_ohms < 1e-12
    assert result.evidence.weighting_method == "unweighted"
    assert result.evidence.solver == "closed_form_single_parameter_least_squares"


def test_fit_iec60751_r0_retains_observed_minus_fitted_residuals() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0),
        CalibrationObservation(100.0, 138.6),
        CalibrationObservation(200.0, 175.7),
    )

    result = fit_iec60751_r0(observations)
    expected = tuple(
        observation.resistance_ohms
        - result.model.celsius_to_resistance(observation.temperature_c)
        for observation in observations
    )

    assert result.evidence.residuals_ohms == pytest.approx(expected)
    assert result.evidence.rms_residual_ohms == pytest.approx(
        math.sqrt(math.fsum(value * value for value in expected) / len(expected))
    )


def test_fit_iec60751_r0_supports_relative_weights() -> None:
    base = IEC60751RTDModel(r0_ohms=100.0)
    observations = (
        CalibrationObservation(0.0, 100.0, weight=1.0),
        CalibrationObservation(100.0, base.celsius_to_resistance(100.0), weight=1.0),
        CalibrationObservation(100.0, 150.0, weight=0.0001),
    )

    result = fit_iec60751_r0(observations)

    assert result.evidence.weighting_method == "normalized_explicit_weights"
    assert result.evidence.effective_weights == (1.0, 1.0, 0.0001)
    assert result.evidence.weighted_sum_squared_residual is not None
    assert result.evidence.weighted_rms_residual_ohms is not None
    assert result.model.r0_ohms < 100.01


def test_fit_iec60751_r0_supports_resistance_standard_uncertainty() -> None:
    base = IEC60751RTDModel(r0_ohms=100.0)
    observations = (
        CalibrationObservation(
            0.0,
            100.0,
            standard_uncertainty_ohms=0.01,
        ),
        CalibrationObservation(
            100.0,
            base.celsius_to_resistance(100.0),
            standard_uncertainty_ohms=0.02,
        ),
    )

    result = fit_iec60751_r0(observations)

    assert result.evidence.weighting_method == (
        "normalized_inverse_variance_from_standard_uncertainty"
    )
    assert result.evidence.effective_weights == pytest.approx((1.0, 0.25))
    assert result.model.r0_ohms == pytest.approx(100.0, abs=1e-13)


def test_fit_iec60751_r0_estimates_covariance_from_residual_variance() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0),
        CalibrationObservation(100.0, 138.6),
        CalibrationObservation(200.0, 175.7),
    )

    result = fit_iec60751_r0(observations)
    covariance = result.evidence.parameter_covariance

    assert isinstance(covariance, FitParameterCovariance)
    assert covariance.parameter_names == ("r0_ohms",)
    assert covariance.parameterization == "r0_ohms"
    assert covariance.estimation_method == "residual_variance_scaled_least_squares"
    ratios = tuple(
        IEC60751RTDModel(r0_ohms=1.0).celsius_to_resistance(observation.temperature_c)
        for observation in observations
    )
    residual_variance = (
        math.fsum(residual * residual for residual in result.evidence.residuals_ohms)
        / result.evidence.residual_degrees_of_freedom
    )
    expected_variance = residual_variance / math.fsum(ratio * ratio for ratio in ratios)
    assert covariance.covariance_matrix[0][0] == pytest.approx(expected_variance)
    assert result.evidence.parameter_covariance_unavailable_reason is None


def test_fit_iec60751_r0_covariance_from_residual_variance_uses_relative_weights() -> (
    None
):
    raw_weights = (1.0, 4.0, 1.0)
    observations = (
        CalibrationObservation(0.0, 100.0, weight=raw_weights[0]),
        CalibrationObservation(100.0, 138.4, weight=raw_weights[1]),
        CalibrationObservation(200.0, 175.9, weight=raw_weights[2]),
    )

    result = fit_iec60751_r0(observations)
    covariance = result.evidence.parameter_covariance

    assert isinstance(covariance, FitParameterCovariance)
    assert result.evidence.weighting_method == "normalized_explicit_weights"
    assert covariance.estimation_method == "residual_variance_scaled_least_squares"
    ratios = tuple(
        IEC60751RTDModel(r0_ohms=1.0).celsius_to_resistance(observation.temperature_c)
        for observation in observations
    )
    weighted_residual_variance = (
        math.fsum(
            weight * residual * residual
            for weight, residual in zip(
                raw_weights, result.evidence.residuals_ohms, strict=True
            )
        )
        / result.evidence.residual_degrees_of_freedom
    )
    expected_variance = weighted_residual_variance / math.fsum(
        weight * ratio * ratio
        for weight, ratio in zip(raw_weights, ratios, strict=True)
    )
    assert covariance.covariance_matrix[0][0] == pytest.approx(expected_variance)


def test_fit_iec60751_r0_covariance_uses_absolute_standard_uncertainties() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0, standard_uncertainty_ohms=0.01),
        CalibrationObservation(100.0, 138.5055, standard_uncertainty_ohms=0.02),
    )

    result = fit_iec60751_r0(observations)
    covariance = result.evidence.parameter_covariance

    assert isinstance(covariance, FitParameterCovariance)
    assert covariance.estimation_method == "resistance_standard_uncertainties"
    ratios = tuple(
        IEC60751RTDModel(r0_ohms=1.0).celsius_to_resistance(observation.temperature_c)
        for observation in observations
    )
    expected_variance = 1.0 / ((ratios[0] / 0.01) ** 2 + (ratios[1] / 0.02) ** 2)
    assert covariance.covariance_matrix[0][0] == pytest.approx(expected_variance)


def test_fit_iec60751_r0_zero_dof_covariance_depends_on_uncertainty_basis() -> None:
    unweighted = fit_iec60751_r0(
        (CalibrationObservation(0.0, 100.0),),
        minimum_temperature_c=-50.0,
        maximum_temperature_c=250.0,
    )
    uncertainty_weighted = fit_iec60751_r0(
        (
            CalibrationObservation(
                0.0,
                100.0,
                standard_uncertainty_ohms=0.02,
            ),
        ),
        minimum_temperature_c=-50.0,
        maximum_temperature_c=250.0,
    )

    assert unweighted.evidence.parameter_covariance is None
    assert unweighted.evidence.parameter_covariance_unavailable_reason == (
        "residual_variance_requires_positive_degrees_of_freedom"
    )
    covariance = uncertainty_weighted.evidence.parameter_covariance
    assert isinstance(covariance, FitParameterCovariance)
    assert covariance.estimation_method == "resistance_standard_uncertainties"
    assert covariance.covariance_matrix[0][0] == pytest.approx(0.02**2)
    assert uncertainty_weighted.evidence.parameter_covariance_unavailable_reason is None


def test_fit_iec60751_r0_records_unrepresentable_covariance() -> None:
    result = fit_iec60751_r0(
        (
            CalibrationObservation(
                0.0,
                100.0,
                standard_uncertainty_ohms=1.0e-200,
            ),
        ),
        minimum_temperature_c=-50.0,
        maximum_temperature_c=250.0,
    )

    assert result.model.r0_ohms == 100.0
    assert result.evidence.parameter_covariance is None
    assert result.evidence.parameter_covariance_unavailable_reason == (
        "covariance_not_finitely_representable"
    )


def test_fit_iec60751_r0_single_temperature_requires_explicit_range() -> None:
    observation = CalibrationObservation(0.0, 100.037)

    with pytest.raises(RTDFitError, match="single-temperature R0 fit"):
        fit_iec60751_r0((observation,))

    result = fit_iec60751_r0(
        (observation,),
        minimum_temperature_c=-50.0,
        maximum_temperature_c=250.0,
    )

    assert result.model.r0_ohms == pytest.approx(100.037)
    assert result.model.minimum_temperature_c == -50.0
    assert result.model.maximum_temperature_c == 250.0
    assert result.evidence.residual_degrees_of_freedom == 0
    assert result.evidence.observation_minimum_temperature_c == 0.0
    assert result.evidence.observation_maximum_temperature_c == 0.0


def test_fit_iec60751_r0_explicit_range_is_separate_from_observation_span() -> None:
    observations = _iec_observations(100.037, (0.0, 100.0))

    result = fit_iec60751_r0(
        observations,
        minimum_temperature_c=-100.0,
        maximum_temperature_c=400.0,
    )

    assert result.evidence.observation_minimum_temperature_c == 0.0
    assert result.evidence.observation_maximum_temperature_c == 100.0
    assert result.evidence.minimum_temperature_c == -100.0
    assert result.evidence.maximum_temperature_c == 400.0


def test_fit_iec60751_r0_explicit_range_may_be_disjoint_from_observations() -> None:
    observations = _iec_observations(100.037, (0.0, 20.0))

    result = fit_iec60751_r0(
        observations,
        minimum_temperature_c=500.0,
        maximum_temperature_c=600.0,
    )

    assert result.model.minimum_temperature_c == 500.0
    assert result.model.maximum_temperature_c == 600.0
    assert result.evidence.observation_minimum_temperature_c == 0.0
    assert result.evidence.observation_maximum_temperature_c == 20.0
    assert result.evidence.minimum_temperature_c == 500.0
    assert result.evidence.maximum_temperature_c == 600.0


def test_fit_iec60751_r0_requires_both_explicit_range_limits() -> None:
    observations = _iec_observations(100.0, (0.0, 100.0))

    with pytest.raises(ValueError, match="must be supplied together"):
        fit_iec60751_r0(observations, minimum_temperature_c=-50.0)

    with pytest.raises(ValueError, match="must be supplied together"):
        fit_iec60751_r0(observations, maximum_temperature_c=250.0)


def test_fit_iec60751_r0_rejects_range_outside_iec_characteristic() -> None:
    observations = _iec_observations(100.0, (0.0, 100.0))

    with pytest.raises(RTDFitError, match="not valid"):
        fit_iec60751_r0(
            observations,
            minimum_temperature_c=-201.0,
            maximum_temperature_c=100.0,
        )


def test_fit_iec60751_r0_rejects_observations_outside_iec_characteristic() -> None:
    observations = (
        CalibrationObservation(-201.0, 18.0),
        CalibrationObservation(0.0, 100.0),
    )

    with pytest.raises(RTDFitError, match="IEC 60751 PT-385 range"):
        fit_iec60751_r0(observations)


def test_fit_iec60751_r0_accepts_one_pass_iterable() -> None:
    observations = (
        observation for observation in _iec_observations(100.037, (-25.0, 0.0, 100.0))
    )

    result = fit_iec60751_r0(observations)

    assert result.model.r0_ohms == pytest.approx(100.037, abs=1e-13)
    assert len(result.evidence.observations) == 3


def test_fit_iec60751_r0_rejects_empty_and_non_observation_inputs() -> None:
    with pytest.raises(RTDFitError, match="At least one calibration observation"):
        fit_iec60751_r0(())

    with pytest.raises(TypeError, match="CalibrationObservation"):
        fit_iec60751_r0([(0.0, 100.0), (100.0, 138.5)])  # type: ignore[list-item]


def test_calibration_observation_normalizes_values_and_is_immutable() -> None:
    observation = CalibrationObservation(25, 109.73, weight=2)

    assert observation.temperature_c == 25.0
    assert observation.resistance_ohms == 109.73
    assert observation.weight == 2.0

    with pytest.raises(FrozenInstanceError):
        observation.temperature_c = 30.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "exception", "message"),
    [
        ({"temperature_c": True}, TypeError, "Temperature"),
        ({"temperature_c": math.nan}, ValueError, "Temperature must be finite"),
        ({"resistance_ohms": 0.0}, ValueError, "greater than zero"),
        ({"resistance_ohms": math.inf}, ValueError, "Resistance must be finite"),
        ({"weight": 0.0}, ValueError, "Weight must be greater than zero"),
        ({"weight": math.inf}, ValueError, "Weight must be finite"),
        (
            {"standard_uncertainty_ohms": 0.0},
            ValueError,
            "Standard uncertainty must be greater than zero",
        ),
        (
            {"weight": 1.0, "standard_uncertainty_ohms": 0.1},
            ValueError,
            "either weight or standard uncertainty",
        ),
    ],
)
def test_calibration_observation_rejects_invalid_values(
    kwargs: dict[str, object],
    exception: type[Exception],
    message: str,
) -> None:
    values: dict[str, object] = {
        "temperature_c": 0.0,
        "resistance_ohms": 100.0,
    }
    values.update(kwargs)

    with pytest.raises(exception, match=message):
        CalibrationObservation(**values)  # type: ignore[arg-type]


def test_fit_polynomial_recovers_exact_cubic_model() -> None:
    observations = [
        CalibrationObservation(temperature_c, _synthetic_resistance(temperature_c))
        for temperature_c in (-60.0, -20.0, 0.0, 50.0, 100.0, 150.0, 200.0)
    ]

    result = fit_polynomial(
        observations,
        degree=3,
        name="Fitted synthetic cubic",
        coefficient_source="Synthetic calibration fixture",
    )

    assert isinstance(result, PolynomialFitResult)
    assert isinstance(result.model, PolynomialRTDModel)
    assert result.model.name == "Fitted synthetic cubic"
    assert result.model.coefficient_source == "Synthetic calibration fixture"
    assert result.evidence.degree == 3
    assert result.evidence.observation_count == 7
    assert result.evidence.fitted_parameter_count == 4
    assert result.evidence.residual_degrees_of_freedom == 3
    assert result.evidence.observations == tuple(observations)
    assert result.evidence.weighting_method == "unweighted"
    assert result.evidence.effective_weights is None
    assert result.evidence.rms_residual_ohms < 1e-11
    assert result.evidence.max_absolute_residual_ohms < 2e-11
    assert (
        result.evidence.scaled_system_condition_number
        < result.evidence.scaled_system_condition_limit
    )
    assert result.evidence.conditioning_method == "infinity_norm_of_householder_r"
    assert result.evidence.solver == "householder_qr_least_squares"

    for temperature_c in (-60.0, -12.5, 0.0, 80.0, 143.25, 200.0):
        assert result.model.celsius_to_resistance(temperature_c) == pytest.approx(
            _synthetic_resistance(temperature_c),
            rel=0.0,
            abs=2e-11,
        )


def test_fit_polynomial_retains_residuals_in_observed_minus_fitted_order() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0),
        CalibrationObservation(50.0, 120.5),
        CalibrationObservation(100.0, 140.0),
    )

    result = fit_polynomial(observations, degree=1)
    expected_residuals = tuple(
        observation.resistance_ohms
        - result.model.celsius_to_resistance(observation.temperature_c)
        for observation in observations
    )

    assert result.evidence.residuals_ohms == pytest.approx(expected_residuals)
    assert result.evidence.rms_residual_ohms == pytest.approx(
        math.sqrt(math.fsum(value * value for value in expected_residuals) / 3.0)
    )
    assert result.evidence.max_absolute_residual_ohms == pytest.approx(
        max(abs(value) for value in expected_residuals)
    )


def test_fit_polynomial_allows_repeated_temperature_measurements() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0),
        CalibrationObservation(50.0, 120.0),
        CalibrationObservation(50.0, 120.2),
        CalibrationObservation(100.0, 140.0),
    )

    result = fit_polynomial(observations, degree=1)

    assert len(result.evidence.observations) == 4
    assert result.evidence.observations[1].temperature_c == 50.0
    assert result.evidence.observations[2].temperature_c == 50.0


def test_fit_polynomial_supports_explicit_relative_weights() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0, weight=1.0),
        CalibrationObservation(100.0, 200.0, weight=1.0),
        CalibrationObservation(100.0, 220.0, weight=0.0001),
    )

    result = fit_polynomial(observations, degree=1)

    assert result.evidence.weighting_method == "normalized_explicit_weights"
    assert result.evidence.effective_weights == (1.0, 1.0, 0.0001)
    assert result.evidence.weighted_sum_squared_residual is not None
    assert result.evidence.weighted_rms_residual_ohms is not None
    assert result.model.celsius_to_resistance(100.0) == pytest.approx(
        200.00199980002,
        abs=1e-9,
    )


def test_fit_polynomial_converts_standard_uncertainty_to_inverse_variance() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0, standard_uncertainty_ohms=1.0),
        CalibrationObservation(100.0, 200.0, standard_uncertainty_ohms=2.0),
    )

    result = fit_polynomial(observations, degree=1)

    assert result.evidence.weighting_method == (
        "normalized_inverse_variance_from_standard_uncertainty"
    )
    assert result.evidence.effective_weights == pytest.approx((1.0, 0.25))
    assert result.evidence.weighted_sum_squared_residual is not None
    assert result.evidence.weighted_rms_residual_ohms is not None


def test_fit_polynomial_estimates_covariance_in_model_reference_basis() -> None:
    observations = (
        CalibrationObservation(-1.0, 98.4),
        CalibrationObservation(0.0, 100.1),
        CalibrationObservation(1.0, 101.5),
    )

    result = fit_polynomial(observations, degree=1)
    covariance = result.evidence.parameter_covariance

    assert isinstance(covariance, FitParameterCovariance)
    assert covariance.parameter_names == ("a0", "a1")
    assert covariance.parameterization == (
        "resistance_power_series_at_model_reference_temperature"
    )
    assert covariance.estimation_method == "residual_variance_scaled_least_squares"
    residual_variance = (
        math.fsum(residual * residual for residual in result.evidence.residuals_ohms)
        / result.evidence.residual_degrees_of_freedom
    )
    assert covariance.covariance_matrix[0][0] == pytest.approx(residual_variance / 3.0)
    assert covariance.covariance_matrix[0][1] == pytest.approx(0.0, abs=1e-15)
    assert covariance.covariance_matrix[1][0] == pytest.approx(0.0, abs=1e-15)
    assert covariance.covariance_matrix[1][1] == pytest.approx(residual_variance / 2.0)


def test_fit_polynomial_covariance_from_residual_variance_uses_relative_weights() -> (
    None
):
    raw_weights = (1.0, 4.0, 2.0, 1.0)
    observations = (
        CalibrationObservation(0.0, 100.0, weight=raw_weights[0]),
        CalibrationObservation(50.0, 120.4, weight=raw_weights[1]),
        CalibrationObservation(100.0, 139.7, weight=raw_weights[2]),
        CalibrationObservation(150.0, 160.2, weight=raw_weights[3]),
    )

    result = fit_polynomial(observations, degree=1)
    covariance = result.evidence.parameter_covariance

    assert isinstance(covariance, FitParameterCovariance)
    assert result.evidence.weighting_method == "normalized_explicit_weights"
    assert covariance.estimation_method == "residual_variance_scaled_least_squares"
    reference_temperature_c = result.model.reference_temperature_c
    offsets = tuple(
        observation.temperature_c - reference_temperature_c
        for observation in observations
    )
    weighted_residual_variance = (
        math.fsum(
            weight * residual * residual
            for weight, residual in zip(
                raw_weights, result.evidence.residuals_ohms, strict=True
            )
        )
        / result.evidence.residual_degrees_of_freedom
    )
    sum_w = math.fsum(raw_weights)
    sum_wx = math.fsum(
        weight * offset for weight, offset in zip(raw_weights, offsets, strict=True)
    )
    sum_wxx = math.fsum(
        weight * offset * offset
        for weight, offset in zip(raw_weights, offsets, strict=True)
    )
    determinant = sum_w * sum_wxx - sum_wx * sum_wx
    expected = (
        (
            weighted_residual_variance * sum_wxx / determinant,
            -weighted_residual_variance * sum_wx / determinant,
        ),
        (
            -weighted_residual_variance * sum_wx / determinant,
            weighted_residual_variance * sum_w / determinant,
        ),
    )
    for actual_row, expected_row in zip(
        covariance.covariance_matrix, expected, strict=True
    ):
        assert actual_row == pytest.approx(expected_row)


def test_fit_polynomial_covariance_transforms_to_narrowed_model_reference() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0, standard_uncertainty_ohms=1.0),
        CalibrationObservation(50.0, 150.0, standard_uncertainty_ohms=1.0),
        CalibrationObservation(100.0, 200.0, standard_uncertainty_ohms=1.0),
    )

    result = fit_polynomial(
        observations,
        degree=1,
        minimum_temperature_c=20.0,
        maximum_temperature_c=60.0,
    )
    covariance = result.evidence.parameter_covariance

    assert isinstance(covariance, FitParameterCovariance)
    assert result.model.reference_temperature_c == 40.0
    # For x = T - 40, X.T @ X = [[3, 30], [30, 5300]].
    assert covariance.covariance_matrix[0][0] == pytest.approx(5300.0 / 15000.0)
    assert covariance.covariance_matrix[0][1] == pytest.approx(-30.0 / 15000.0)
    assert covariance.covariance_matrix[1][0] == pytest.approx(-30.0 / 15000.0)
    assert covariance.covariance_matrix[1][1] == pytest.approx(3.0 / 15000.0)


def test_fit_polynomial_degree_two_covariance_transforms_to_narrowed_reference() -> (
    None
):
    observations = (
        CalibrationObservation(0.0, 100.0, standard_uncertainty_ohms=1.0),
        CalibrationObservation(50.0, 121.25, standard_uncertainty_ohms=1.0),
        CalibrationObservation(100.0, 145.0, standard_uncertainty_ohms=1.0),
        CalibrationObservation(150.0, 171.25, standard_uncertainty_ohms=1.0),
    )

    result = fit_polynomial(
        observations,
        degree=2,
        minimum_temperature_c=20.0,
        maximum_temperature_c=80.0,
    )
    covariance = result.evidence.parameter_covariance

    assert isinstance(covariance, FitParameterCovariance)
    assert covariance.parameter_names == ("a0", "a1", "a2")
    assert result.model.reference_temperature_c == 50.0
    expected = (
        (0.55, 0.003, -0.0001),
        (0.003, 0.00018, -0.000002),
        (-0.0001, -0.000002, 0.00000004),
    )
    for actual_row, expected_row in zip(
        covariance.covariance_matrix, expected, strict=True
    ):
        assert actual_row == pytest.approx(expected_row)


def test_fit_polynomial_saturated_covariance_requires_absolute_uncertainties() -> None:
    unweighted = fit_polynomial(
        (
            CalibrationObservation(0.0, 100.0),
            CalibrationObservation(100.0, 200.0),
        ),
        degree=1,
    )
    uncertainty_weighted = fit_polynomial(
        (
            CalibrationObservation(0.0, 100.0, standard_uncertainty_ohms=1.0),
            CalibrationObservation(100.0, 200.0, standard_uncertainty_ohms=2.0),
        ),
        degree=1,
    )

    assert unweighted.evidence.parameter_covariance is None
    assert unweighted.evidence.parameter_covariance_unavailable_reason == (
        "residual_variance_requires_positive_degrees_of_freedom"
    )
    covariance = uncertainty_weighted.evidence.parameter_covariance
    assert isinstance(covariance, FitParameterCovariance)
    assert covariance.estimation_method == "resistance_standard_uncertainties"
    # For x = T - 50 and u = (1, 2) ohm,
    # X.T @ W @ X = [[1.25, -37.5], [-37.5, 3125]].
    assert covariance.covariance_matrix[0][0] == pytest.approx(1.25)
    assert covariance.covariance_matrix[0][1] == pytest.approx(0.015)
    assert covariance.covariance_matrix[1][0] == pytest.approx(0.015)
    assert covariance.covariance_matrix[1][1] == pytest.approx(0.0005)
    assert uncertainty_weighted.evidence.parameter_covariance_unavailable_reason is None


def test_fit_polynomial_requires_one_consistent_weighting_convention() -> None:
    with pytest.raises(RTDFitError, match="Every observation must provide a weight"):
        fit_polynomial(
            (
                CalibrationObservation(0.0, 100.0, weight=1.0),
                CalibrationObservation(100.0, 200.0),
            ),
            degree=1,
        )

    with pytest.raises(RTDFitError, match="one weighting convention"):
        fit_polynomial(
            (
                CalibrationObservation(0.0, 100.0, weight=1.0),
                CalibrationObservation(
                    100.0,
                    200.0,
                    standard_uncertainty_ohms=1.0,
                ),
            ),
            degree=1,
        )

    with pytest.raises(
        RTDFitError,
        match="Every observation must provide a standard uncertainty",
    ):
        fit_polynomial(
            (
                CalibrationObservation(
                    0.0,
                    100.0,
                    standard_uncertainty_ohms=1.0,
                ),
                CalibrationObservation(100.0, 200.0),
            ),
            degree=1,
        )


def test_fit_polynomial_may_narrow_but_not_extend_fitted_range() -> None:
    observations = (
        CalibrationObservation(-50.0, 80.0),
        CalibrationObservation(0.0, 100.0),
        CalibrationObservation(50.0, 120.0),
        CalibrationObservation(100.0, 140.0),
    )

    result = fit_polynomial(
        observations,
        degree=1,
        minimum_temperature_c=-20.0,
        maximum_temperature_c=80.0,
    )

    assert result.model.minimum_temperature_c == -20.0
    assert result.model.maximum_temperature_c == 80.0
    assert result.model.reference_temperature_c == 30.0
    assert result.evidence.minimum_temperature_c == -20.0
    assert result.evidence.maximum_temperature_c == 80.0

    with pytest.raises(RTDFitError, match="may not extend beyond"):
        fit_polynomial(
            observations,
            degree=1,
            minimum_temperature_c=-50.1,
        )

    with pytest.raises(RTDFitError, match="may not extend beyond"):
        fit_polynomial(
            observations,
            degree=1,
            maximum_temperature_c=100.1,
        )


@pytest.mark.parametrize(
    ("minimum_temperature_c", "maximum_temperature_c", "message"),
    [
        (math.nan, None, "Minimum fitted temperature must be finite"),
        (None, math.inf, "Maximum fitted temperature must be finite"),
        (
            50.0,
            50.0,
            "Minimum fitted temperature must be below maximum fitted temperature",
        ),
        (
            60.0,
            50.0,
            "Minimum fitted temperature must be below maximum fitted temperature",
        ),
    ],
)
def test_fit_polynomial_rejects_invalid_fitted_range_arguments(
    minimum_temperature_c: float | None,
    maximum_temperature_c: float | None,
    message: str,
) -> None:
    observations = (
        CalibrationObservation(0.0, 100.0),
        CalibrationObservation(100.0, 140.0),
    )

    with pytest.raises(ValueError, match=message):
        fit_polynomial(
            observations,
            degree=1,
            minimum_temperature_c=minimum_temperature_c,
            maximum_temperature_c=maximum_temperature_c,
        )


def test_fit_polynomial_rejects_empty_observation_set() -> None:
    with pytest.raises(RTDFitError, match="At least one calibration observation"):
        fit_polynomial((), degree=1)


def test_fit_polynomial_rejects_nonfinite_temperature_span() -> None:
    observations = (
        CalibrationObservation(-1e308, 100.0),
        CalibrationObservation(1e308, 140.0),
    )

    with pytest.raises(RTDFitError, match="must span a finite interval"):
        fit_polynomial(observations, degree=1)


def test_fit_polynomial_rejects_insufficient_distinct_temperatures() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0),
        CalibrationObservation(0.0, 100.1),
        CalibrationObservation(100.0, 140.0),
    )

    with pytest.raises(RTDFitError, match="at least 3 distinct"):
        fit_polynomial(observations, degree=2)


@pytest.mark.parametrize("degree", [True, 1.5, "2"])
def test_fit_polynomial_rejects_noninteger_degree(degree: object) -> None:
    observations = (
        CalibrationObservation(0.0, 100.0),
        CalibrationObservation(100.0, 140.0),
    )

    with pytest.raises(TypeError, match="degree must be an integer"):
        fit_polynomial(observations, degree=degree)  # type: ignore[arg-type]


@pytest.mark.parametrize("degree", [0, 13])
def test_fit_polynomial_rejects_degree_outside_supported_range(degree: int) -> None:
    observations = (
        CalibrationObservation(0.0, 100.0),
        CalibrationObservation(100.0, 140.0),
    )

    with pytest.raises(ValueError, match="Polynomial degree"):
        fit_polynomial(observations, degree=degree)


def test_fit_polynomial_accepts_one_pass_iterable() -> None:
    observations = (
        CalibrationObservation(temperature_c, resistance_ohms)
        for temperature_c, resistance_ohms in ((0.0, 100.0), (100.0, 140.0))
    )

    result = fit_polynomial(observations, degree=1)

    assert len(result.evidence.observations) == 2
    assert result.model.celsius_to_resistance(50.0) == pytest.approx(120.0)


def test_fit_polynomial_rejects_non_observation_values() -> None:
    values = [(0.0, 100.0), (100.0, 140.0)]
    with pytest.raises(TypeError, match="CalibrationObservation"):
        fit_polynomial(values, degree=1)  # type: ignore[arg-type]


def test_fit_polynomial_normalizes_extreme_common_uncertainty_scale() -> None:
    observations = (
        CalibrationObservation(
            0.0,
            100.0,
            standard_uncertainty_ohms=1e-200,
        ),
        CalibrationObservation(
            100.0,
            140.0,
            standard_uncertainty_ohms=1e-200,
        ),
    )

    result = fit_polynomial(observations, degree=1)

    assert result.evidence.effective_weights == (1.0, 1.0)


def test_fit_polynomial_rejects_unrepresentable_weight_dynamic_range() -> None:
    observations = (
        CalibrationObservation(
            0.0,
            100.0,
            standard_uncertainty_ohms=5e-324,
        ),
        CalibrationObservation(
            100.0,
            140.0,
            standard_uncertainty_ohms=1.0,
        ),
    )

    with pytest.raises(RTDFitError, match="unrepresentable inverse-variance"):
        fit_polynomial(observations, degree=1)


def test_fit_polynomial_rejects_unrepresentable_explicit_weight_dynamic_range() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0, weight=1e-300),
        CalibrationObservation(100.0, 140.0, weight=1e50),
    )

    with pytest.raises(
        RTDFitError,
        match="weights have an unrepresentable dynamic range",
    ):
        fit_polynomial(observations, degree=1)


def test_fit_polynomial_accepts_well_spaced_degree_twelve_system() -> None:
    temperatures = tuple(-100.0 + 25.0 * index for index in range(13))
    observations = tuple(
        CalibrationObservation(temperature_c, 100.0 + 0.4 * temperature_c)
        for temperature_c in temperatures
    )

    result = fit_polynomial(observations, degree=12)

    assert (
        result.evidence.scaled_system_condition_number
        < result.evidence.scaled_system_condition_limit
    )
    assert result.evidence.observation_count == 13
    assert result.evidence.fitted_parameter_count == 13
    assert result.evidence.residual_degrees_of_freedom == 0
    assert result.evidence.max_absolute_residual_ohms < 1e-10


def test_fit_polynomial_rejects_severely_ill_conditioned_scaled_system() -> None:
    observations = tuple(
        CalibrationObservation(temperature_c, 100.0 + temperature_c)
        for temperature_c in (0.0, 1e-12, 2e-12, 100.0)
    )

    with pytest.raises(RTDFitError, match="severely ill-conditioned"):
        fit_polynomial(observations, degree=2)


def test_fit_polynomial_rejects_weight_induced_ill_conditioning() -> None:
    observations = tuple(
        CalibrationObservation(
            temperature_c,
            100.0 + 0.4 * temperature_c,
            weight=1.0 if temperature_c == 0.0 else 1e-24,
        )
        for temperature_c in (-100.0, -50.0, 0.0, 50.0, 100.0, 150.0)
    )

    with pytest.raises(RTDFitError, match="severely ill-conditioned"):
        fit_polynomial(observations, degree=2)


def test_fit_polynomial_rejects_unrepresentable_coefficient_shift() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0),
        CalibrationObservation(5e-200, 110.0),
        CalibrationObservation(1e-199, 120.0),
    )

    with pytest.raises(RTDFitError, match="cannot be represented with finite"):
        fit_polynomial(observations, degree=2)


def test_fit_polynomial_rejects_nonpositive_fitted_reference_resistance() -> None:
    observations = tuple(
        CalibrationObservation(temperature_c, resistance_ohms)
        for temperature_c, resistance_ohms in (
            (-1.0, 100.0),
            (-0.5, 1.0),
            (0.5, 1.0),
            (1.0, 100.0),
        )
    )

    with pytest.raises(
        RTDFitError,
        match="reference resistance must be finite and positive",
    ):
        fit_polynomial(observations, degree=2)


def test_fit_polynomial_rejects_scientifically_invalid_fitted_curve() -> None:
    observations = (
        CalibrationObservation(0.0, 100.0),
        CalibrationObservation(50.0, 90.0),
        CalibrationObservation(100.0, 80.0),
    )

    with pytest.raises(RTDFitError, match="not a valid RTD model"):
        fit_polynomial(observations, degree=1)


def test_fit_polynomial_result_and_evidence_are_immutable() -> None:
    result = fit_polynomial(
        (
            CalibrationObservation(0.0, 100.0),
            CalibrationObservation(100.0, 140.0),
        ),
        degree=1,
    )

    assert isinstance(result.evidence, PolynomialFitEvidence)
    with pytest.raises(FrozenInstanceError):
        result.evidence.degree = 2  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.model = result.model  # type: ignore[misc]
