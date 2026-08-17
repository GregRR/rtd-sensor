# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
from dataclasses import FrozenInstanceError

import pytest

from rtd_sensor.exceptions import RTDFitError
from rtd_sensor.fitting import (
    CalibrationObservation,
    PolynomialFitEvidence,
    PolynomialFitResult,
    fit_polynomial,
)
from rtd_sensor.models import PolynomialRTDModel


def _synthetic_resistance(temperature_c: float) -> float:
    return 1000.0 * (
        1.0
        + 5.0e-3 * temperature_c
        + 4.0e-6 * temperature_c**2
        + 1.0e-9 * temperature_c**3
    )


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
