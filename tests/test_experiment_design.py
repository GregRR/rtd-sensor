# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import math
from decimal import Decimal, localcontext

import pytest

from rtd_sensor import pt100
from rtd_sensor._experiment_design import (
    _OperatingPriorityInterval,
    _prospective_polynomial_covariance,
    _sensitivity_weighted_moment_matrix,
)
from rtd_sensor.exceptions import RTDExperimentDesignError
from rtd_sensor.fitting import CalibrationObservation, fit_polynomial
from rtd_sensor.models import TabulatedRTDModel, TabulatedRTDPoint


def _power_series_variance(
    covariance: tuple[tuple[float, ...], ...],
    *,
    temperature_c: float,
    reference_temperature_c: float,
) -> float:
    x = temperature_c - reference_temperature_c
    basis = [1.0]
    for _ in range(len(covariance) - 1):
        basis.append(basis[-1] * x)
    return math.fsum(
        covariance[row][column] * basis[row] * basis[column]
        for row in range(len(covariance))
        for column in range(len(covariance))
    )


def test_prospective_covariance_matches_fitter_when_reference_basis_matches() -> None:
    temperatures = (-50.0, 0.0, 40.0, 100.0, 180.0)
    uncertainties = (0.01, 0.02, 0.015, 0.03, 0.018)

    def resistance(temperature_c: float) -> float:
        return (
            100.0
            + 0.39 * temperature_c
            + 1.0e-4 * temperature_c**2
            - 2.0e-7 * temperature_c**3
        )

    fit = fit_polynomial(
        tuple(
            CalibrationObservation(
                temperature_c,
                resistance(temperature_c),
                standard_uncertainty_ohms=uncertainty,
            )
            for temperature_c, uncertainty in zip(
                temperatures,
                uncertainties,
                strict=True,
            )
        ),
        degree=3,
    )
    fit_covariance = fit.evidence.parameter_covariance
    assert fit_covariance is not None

    prospective = _prospective_polynomial_covariance(
        temperatures,
        uncertainties,
        degree=3,
        planning_reference_temperature_c=65.0,
    )

    # Prospective planning uses no response values, but when the fixed planning
    # basis matches fit_polynomial()'s declared-range basis, it must reproduce the
    # same absolute-uncertainty information covariance exactly.
    assert prospective.covariance_matrix == fit_covariance.covariance_matrix
    assert prospective.reference_temperature_c == fit.model.reference_temperature_c
    assert (
        prospective.scaled_system_condition_number
        == fit.evidence.scaled_system_condition_number
    )
    assert prospective.conditioning_method == fit.evidence.conditioning_method
    assert prospective.solver == fit.evidence.solver


def test_prospective_covariance_can_use_fixed_basis_before_design_spans_range() -> None:
    temperatures = (0.0, 20.0, 40.0)
    uncertainties = (0.01, 0.015, 0.02)

    fixed_basis = _prospective_polynomial_covariance(
        temperatures,
        uncertainties,
        degree=2,
        planning_reference_temperature_c=50.0,
    )
    candidate_midpoint_basis = _prospective_polynomial_covariance(
        temperatures,
        uncertainties,
        degree=2,
        planning_reference_temperature_c=20.0,
    )

    assert fixed_basis.reference_temperature_c == 50.0
    assert fixed_basis.scaled_temperature_center_c == 20.0

    for temperature_c in (-10.0, 0.0, 25.0, 50.0, 80.0):
        fixed_variance = _power_series_variance(
            fixed_basis.covariance_matrix,
            temperature_c=temperature_c,
            reference_temperature_c=fixed_basis.reference_temperature_c,
        )
        midpoint_variance = _power_series_variance(
            candidate_midpoint_basis.covariance_matrix,
            temperature_c=temperature_c,
            reference_temperature_c=candidate_midpoint_basis.reference_temperature_c,
        )
        assert fixed_variance == pytest.approx(midpoint_variance, rel=2.0e-13)


def test_prospective_covariance_canonicalizes_run_order_before_qr() -> None:
    temperatures = (-80.0, -20.0, 0.0, 40.0, 40.0, 100.0, 160.0)
    uncertainties = (0.012, 0.02, 0.01, 0.024, 0.018, 0.015, 0.025)

    forward = _prospective_polynomial_covariance(
        temperatures,
        uncertainties,
        degree=3,
        planning_reference_temperature_c=40.0,
    )
    reverse = _prospective_polynomial_covariance(
        tuple(reversed(temperatures)),
        tuple(reversed(uncertainties)),
        degree=3,
        planning_reference_temperature_c=40.0,
    )

    assert reverse == forward


def test_prospective_covariance_rejects_insufficient_distinct_temperatures() -> None:
    with pytest.raises(
        RTDExperimentDesignError,
        match="requires at least 3 distinct prospective calibration temperatures",
    ):
        _prospective_polynomial_covariance(
            (0.0, 0.0, 100.0),
            (0.01, 0.01, 0.02),
            degree=2,
            planning_reference_temperature_c=50.0,
        )


def test_prospective_covariance_rejects_unrepresentable_uncertainty_range() -> None:
    with pytest.raises(
        RTDExperimentDesignError,
        match="unrepresentable inverse-variance weighting range",
    ):
        _prospective_polynomial_covariance(
            (0.0, 50.0, 100.0),
            (1.0e-200, 1.0, 1.0),
            degree=2,
            planning_reference_temperature_c=50.0,
        )


def test_prospective_covariance_rejects_unrepresentable_common_scale() -> None:
    with pytest.raises(
        RTDExperimentDesignError,
        match="unrepresentable covariance scale",
    ):
        _prospective_polynomial_covariance(
            (0.0, 50.0, 100.0),
            (1.0e-200, 1.0e-200, 1.0e-200),
            degree=2,
            planning_reference_temperature_c=50.0,
        )


def _decimal_inverse(matrix: list[list[Decimal]]) -> list[list[Decimal]]:
    """Invert a small matrix independently with high-precision Gauss-Jordan."""

    size = len(matrix)
    augmented = [
        row[:]
        + [Decimal(1) if row_index == column else Decimal(0) for column in range(size)]
        for row_index, row in enumerate(matrix)
    ]

    for column in range(size):
        pivot = max(
            range(column, size),
            key=lambda row_index: abs(augmented[row_index][column]),
        )
        if pivot != column:
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]

        pivot_value = augmented[column][column]
        assert pivot_value != 0
        for entry in range(2 * size):
            augmented[column][entry] /= pivot_value

        for row_index in range(size):
            if row_index == column:
                continue
            factor = augmented[row_index][column]
            if factor == 0:
                continue
            for entry in range(2 * size):
                augmented[row_index][entry] -= factor * augmented[column][entry]

    return [row[size:] for row in augmented]


def _decimal_power(base: Decimal, exponent: int) -> Decimal:
    """Raise a Decimal to a nonnegative integer power, including ``0**0``."""

    return Decimal(1) if exponent == 0 else base**exponent


def _decimal_degree_12_reference(
    temperatures: tuple[float, ...],
    uncertainties: tuple[float, ...],
    *,
    reference_temperature_c: float,
    operating_half_range_c: float,
) -> tuple[list[list[Decimal]], Decimal]:
    """Return an independent high-precision covariance and closed-form ``J_T``.

    This reference intentionally does not use the production QR, triangular inverse,
    covariance transform, or trace helper. It starts from the exact binary64 inputs,
    builds the absolute inverse-variance information matrix directly in high
    precision, inverts it with Gauss-Jordan, applies the analytical affine basis
    transform with ``Decimal``, and evaluates a closed-form
    uniform/constant-sensitivity I-optimal moment matrix.
    """

    degree = 12
    size = degree + 1
    decimal_temperatures = tuple(Decimal.from_float(value) for value in temperatures)
    decimal_uncertainties = tuple(Decimal.from_float(value) for value in uncertainties)
    observed_minimum = min(decimal_temperatures)
    observed_maximum = max(decimal_temperatures)
    scaled_center = (observed_minimum + observed_maximum) / Decimal(2)
    scaled_half_range = (observed_maximum - observed_minimum) / Decimal(2)
    scaled_temperatures = tuple(
        (temperature - scaled_center) / scaled_half_range
        for temperature in decimal_temperatures
    )

    information = [
        [
            sum(
                (
                    _decimal_power(scaled_temperature, row + column)
                    / (uncertainty * uncertainty)
                    for scaled_temperature, uncertainty in zip(
                        scaled_temperatures,
                        decimal_uncertainties,
                        strict=True,
                    )
                ),
                Decimal(0),
            )
            for column in range(size)
        ]
        for row in range(size)
    ]
    scaled_covariance = _decimal_inverse(information)

    reference = Decimal.from_float(reference_temperature_c)
    alpha = (reference - scaled_center) / scaled_half_range
    beta = Decimal(1) / scaled_half_range
    transform = [[Decimal(0) for _ in range(size)] for _ in range(size)]
    for scaled_power in range(size):
        for shifted_power in range(scaled_power + 1):
            transform[shifted_power][scaled_power] = (
                Decimal(math.comb(scaled_power, shifted_power))
                * _decimal_power(alpha, scaled_power - shifted_power)
                * _decimal_power(beta, shifted_power)
            )

    left_product = [
        [
            sum(
                (
                    transform[row][inner] * scaled_covariance[inner][column]
                    for inner in range(size)
                ),
                Decimal(0),
            )
            for column in range(size)
        ]
        for row in range(size)
    ]
    covariance = [
        [
            sum(
                (
                    left_product[row][inner] * transform[column][inner]
                    for inner in range(size)
                ),
                Decimal(0),
            )
            for column in range(size)
        ]
        for row in range(size)
    ]

    # For uniform priority and constant s(T)=1 over a range centered on the
    # planning reference, M_ij is the normalized even power moment:
    #     M_ij = H^(i+j)/(i+j+1) for even i+j, otherwise 0.
    # This is the closed-form version of DESIGN.md's sensitivity-weighted moment
    # matrix and avoids using the not-yet-implemented quadrature path in this test.
    half_range = Decimal.from_float(operating_half_range_c)
    moment = [[Decimal(0) for _ in range(size)] for _ in range(size)]
    for row in range(size):
        for column in range(size):
            power = row + column
            if power % 2 == 0:
                moment[row][column] = _decimal_power(half_range, power) / Decimal(
                    power + 1
                )

    objective = sum(
        (
            covariance[row][column] * moment[column][row]
            for row in range(size)
            for column in range(size)
        ),
        Decimal(0),
    )
    return covariance, objective


def _uniform_constant_sensitivity_moment_matrix(
    *,
    size: int,
    operating_half_range_c: float,
) -> tuple[tuple[float, ...], ...]:
    return tuple(
        tuple(
            (
                operating_half_range_c ** (row + column) / (row + column + 1)
                if (row + column) % 2 == 0
                else 0.0
            )
            for column in range(size)
        )
        for row in range(size)
    )


def _uniform_objective(
    covariance: tuple[tuple[float, ...], ...],
    *,
    operating_half_range_c: float,
) -> float:
    moment_matrix = _uniform_constant_sensitivity_moment_matrix(
        size=len(covariance),
        operating_half_range_c=operating_half_range_c,
    )
    return math.fsum(
        covariance[row][column] * moment_matrix[column][row]
        for row in range(len(covariance))
        for column in range(len(covariance))
    )


def _maximum_relative_covariance_error(
    actual: tuple[tuple[float, ...], ...],
    expected: list[list[Decimal]],
) -> float:
    maximum_relative_error = 0.0
    for row in range(len(actual)):
        for column in range(len(actual)):
            expected_value = expected[row][column]
            actual_value = Decimal.from_float(actual[row][column])
            assert expected_value != 0
            maximum_relative_error = max(
                maximum_relative_error,
                float(abs((actual_value - expected_value) / expected_value)),
            )
    return maximum_relative_error


def _relative_objective_error(actual: float, expected: Decimal) -> float:
    return float(abs((Decimal.from_float(actual) - expected) / expected))


def _near_guardrail_temperatures(close_temperature_c: float) -> tuple[float, ...]:
    return (
        -1.0,
        -0.8,
        -0.6,
        -0.4,
        -0.2,
        0.0,
        close_temperature_c,
        0.2,
        0.4,
        0.6,
        0.8,
        0.9,
        1.0,
    )


def test_degree_12_covariance_and_objective_against_high_precision_reference() -> None:
    temperatures = (
        -120.0,
        -105.0,
        -90.0,
        -72.0,
        -55.0,
        -37.0,
        -18.0,
        0.0,
        19.0,
        39.0,
        60.0,
        82.0,
        105.0,
        129.0,
        154.0,
        180.0,
        207.0,
    )
    uncertainties = (
        0.008,
        0.011,
        0.009,
        0.014,
        0.010,
        0.016,
        0.012,
        0.018,
        0.013,
        0.021,
        0.015,
        0.024,
        0.017,
        0.027,
        0.019,
        0.030,
        0.022,
    )
    planning_reference_temperature_c = 40.0
    operating_half_range_c = 140.0

    prospective = _prospective_polynomial_covariance(
        temperatures,
        uncertainties,
        degree=12,
        planning_reference_temperature_c=planning_reference_temperature_c,
    )

    with localcontext() as context:
        context.prec = 110
        reference_covariance, reference_objective = _decimal_degree_12_reference(
            temperatures,
            uncertainties,
            reference_temperature_c=planning_reference_temperature_c,
            operating_half_range_c=operating_half_range_c,
        )

    maximum_relative_covariance_error = _maximum_relative_covariance_error(
        prospective.covariance_matrix,
        reference_covariance,
    )
    computed_objective = _uniform_objective(
        prospective.covariance_matrix,
        operating_half_range_c=operating_half_range_c,
    )
    relative_objective_error = _relative_objective_error(
        computed_objective,
        reference_objective,
    )

    # This well-conditioned fixture establishes the ordinary degree-12 empirical
    # envelope required by the 0.9 design review. On the reviewed fixture the
    # current binary64 path is about 2.3e-11 relative in covariance and 2.9e-11 in
    # J_T. A 5e-10 regression ceiling preserves substantial margin over those
    # measured values while still detecting errors on the scale of the previously
    # observed ~1.9e-10 point-coefficient recentering result. It is a numerical
    # regression envelope, never an optimization tie/equivalence threshold.
    assert maximum_relative_covariance_error < 5.0e-10
    assert relative_objective_error < 5.0e-10


def test_degree_12_covariance_and_objective_near_conditioning_guardrail() -> None:
    temperatures = _near_guardrail_temperatures(2.5e-6)
    uncertainties = (0.01,) * 13
    planning_reference_temperature_c = 5.0
    operating_half_range_c = 6.0

    prospective = _prospective_polynomial_covariance(
        temperatures,
        uncertainties,
        degree=12,
        planning_reference_temperature_c=planning_reference_temperature_c,
    )

    # The candidate QR basis is centered near zero, while the fixed planning basis
    # is centered far outside the candidate span. The design is also deliberately
    # close to the existing 1e10 Householder-R conditioning guardrail.
    assert (
        0.9 * prospective.scaled_system_condition_limit
        < prospective.scaled_system_condition_number
        < prospective.scaled_system_condition_limit
    )

    with localcontext() as context:
        context.prec = 160
        reference_covariance, reference_objective = _decimal_degree_12_reference(
            temperatures,
            uncertainties,
            reference_temperature_c=planning_reference_temperature_c,
            operating_half_range_c=operating_half_range_c,
        )

    maximum_relative_covariance_error = _maximum_relative_covariance_error(
        prospective.covariance_matrix,
        reference_covariance,
    )
    computed_objective = _uniform_objective(
        prospective.covariance_matrix,
        operating_half_range_c=operating_half_range_c,
    )
    relative_objective_error = _relative_objective_error(
        computed_objective,
        reference_objective,
    )

    # On this reviewed near-guardrail fixture the current path is about 4.1e-8
    # relative in both covariance and J_T. The 5e-7 regression ceiling keeps
    # more than an order of magnitude of margin. This is empirical implementation
    # validation, not a scientific equivalence or optimization-tie threshold.
    assert maximum_relative_covariance_error < 5.0e-7
    assert relative_objective_error < 5.0e-7


def test_degree_12_close_scores_are_characterized_without_fuzzy_tie() -> None:
    uncertainties = (0.01,) * 13
    planning_reference_temperature_c = 5.0
    operating_half_range_c = 6.0
    first_temperatures = _near_guardrail_temperatures(2.5e-6)
    second_temperatures = _near_guardrail_temperatures(2.5000001e-6)

    first = _prospective_polynomial_covariance(
        first_temperatures,
        uncertainties,
        degree=12,
        planning_reference_temperature_c=planning_reference_temperature_c,
    )
    second = _prospective_polynomial_covariance(
        second_temperatures,
        uncertainties,
        degree=12,
        planning_reference_temperature_c=planning_reference_temperature_c,
    )
    first_objective = _uniform_objective(
        first.covariance_matrix,
        operating_half_range_c=operating_half_range_c,
    )
    second_objective = _uniform_objective(
        second.covariance_matrix,
        operating_half_range_c=operating_half_range_c,
    )

    with localcontext() as context:
        context.prec = 160
        _, first_reference = _decimal_degree_12_reference(
            first_temperatures,
            uncertainties,
            reference_temperature_c=planning_reference_temperature_c,
            operating_half_range_c=operating_half_range_c,
        )
        _, second_reference = _decimal_degree_12_reference(
            second_temperatures,
            uncertainties,
            reference_temperature_c=planning_reference_temperature_c,
            operating_half_range_c=operating_half_range_c,
        )

    first_error = _relative_objective_error(first_objective, first_reference)
    second_error = _relative_objective_error(second_objective, second_reference)
    reference_relative_separation = float(
        abs(second_reference - first_reference) / first_reference
    )

    # The independent objectives differ by only about 8e-8 relative, inside the
    # near-guardrail numerical regression envelope. The production values remain
    # strict binary64 scores; this study deliberately does not turn the measured
    # accuracy envelope into an isclose/fuzzy-tie rule or require that such a close
    # real-arithmetic ordering be resolved scientifically.
    assert 0.0 < reference_relative_separation < 5.0e-7
    assert first_error < 5.0e-7
    assert second_error < 5.0e-7


class _ConstantSensitivityModel:
    def __init__(self, sensitivity_celsius_per_ohm: float) -> None:
        self.sensitivity_celsius_per_ohm = sensitivity_celsius_per_ohm
        self.evaluated_temperatures: list[float] = []

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        return resistance_ohms

    def temperature_sensitivity_celsius_per_ohm(
        self,
        temperature_c: float,
    ) -> float:
        self.evaluated_temperatures.append(temperature_c)
        return self.sensitivity_celsius_per_ohm


class _OscillatorySensitivityModel(_ConstantSensitivityModel):
    def temperature_sensitivity_celsius_per_ohm(
        self,
        temperature_c: float,
    ) -> float:
        self.evaluated_temperatures.append(temperature_c)
        return 1.0 + 0.4 * math.sin(1000.0 * temperature_c)


def _piecewise_constant_sensitivity_moment(
    intervals: tuple[tuple[float, float, float, float], ...],
    *,
    degree: int,
    reference_temperature_c: float,
) -> tuple[tuple[float, ...], ...]:
    normalization = math.fsum(
        weight * (upper - lower) for lower, upper, weight, _ in intervals
    )
    rows: list[tuple[float, ...]] = []
    for row in range(degree + 1):
        values: list[float] = []
        for column in range(degree + 1):
            power = row + column
            numerator = math.fsum(
                weight
                * sensitivity
                * sensitivity
                * (
                    (upper - reference_temperature_c) ** (power + 1)
                    - (lower - reference_temperature_c) ** (power + 1)
                )
                / (power + 1)
                for lower, upper, weight, sensitivity in intervals
            )
            values.append(numerator / normalization)
        rows.append(tuple(values))
    return tuple(rows)


def test_moment_matrix_matches_closed_form_degree_12_constant_sensitivity() -> None:
    model = _ConstantSensitivityModel(0.25)
    result = _sensitivity_weighted_moment_matrix(
        model,
        degree=12,
        planning_reference_temperature_c=0.0,
        fitted_minimum_temperature_c=-2.0,
        fitted_maximum_temperature_c=2.0,
        nominal_minimum_temperature_c=-2.0,
        nominal_maximum_temperature_c=2.0,
        priority_intervals=(_OperatingPriorityInterval(-2.0, 2.0, 3.0),),
    )
    expected = _piecewise_constant_sensitivity_moment(
        ((-2.0, 2.0, 3.0, 0.25),),
        degree=12,
        reference_temperature_c=0.0,
    )

    for actual_row, expected_row in zip(
        result.moment_matrix,
        expected,
        strict=True,
    ):
        assert actual_row == pytest.approx(expected_row, rel=2.0e-14, abs=1.0e-15)

    assert result.integration_method == "adaptive_gauss_kronrod_15_31"
    assert result.relative_error_target == 1.0e-12
    assert result.priority_normalization_c == 12.0
    assert result.structural_partition_c == (-2.0, 2.0)
    assert result.accepted_subinterval_count == 1
    assert result.sensitivity_evaluation_count == 31
    assert result.adaptive_subdivision_occurred is False
    assert result.parameter_names == tuple(f"a{power}" for power in range(13))
    assert result.moment_matrix == tuple(
        tuple(result.moment_matrix[column][row] for column in range(13))
        for row in range(13)
    )


def test_moment_matrix_tabulated_breakpoint_matches_analytic_piecewise_result() -> None:
    from rtd_sensor._experiment_design import (
        _OperatingPriorityInterval,
        _sensitivity_weighted_moment_matrix,
    )

    model = TabulatedRTDModel(
        points=(
            TabulatedRTDPoint(temperature_c=-10.0, resistance_ohms=90.0),
            TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
            TabulatedRTDPoint(temperature_c=20.0, resistance_ohms=140.0),
        )
    )
    result = _sensitivity_weighted_moment_matrix(
        model,
        degree=3,
        planning_reference_temperature_c=5.0,
        fitted_minimum_temperature_c=-10.0,
        fitted_maximum_temperature_c=20.0,
        nominal_minimum_temperature_c=-10.0,
        nominal_maximum_temperature_c=20.0,
        priority_intervals=(_OperatingPriorityInterval(-10.0, 20.0, 1.0),),
        sensitivity_breakpoints_c=(0.0,),
    )
    expected = _piecewise_constant_sensitivity_moment(
        (
            (-10.0, 0.0, 1.0, 1.0),
            (0.0, 20.0, 1.0, 0.5),
        ),
        degree=3,
        reference_temperature_c=5.0,
    )

    for actual_row, expected_row in zip(
        result.moment_matrix,
        expected,
        strict=True,
    ):
        assert actual_row == pytest.approx(expected_row, rel=2.0e-14, abs=1.0e-13)
    assert result.structural_partition_c == (-10.0, 0.0, 20.0)
    assert result.accepted_subinterval_count == 2
    assert result.sensitivity_evaluation_count == 62
    assert result.adaptive_subdivision_occurred is False


def test_moment_matrix_priority_scale_and_split_are_invariant() -> None:
    model = _ConstantSensitivityModel(0.4)
    unsplit = _sensitivity_weighted_moment_matrix(
        model,
        degree=4,
        planning_reference_temperature_c=0.0,
        fitted_minimum_temperature_c=-5.0,
        fitted_maximum_temperature_c=5.0,
        nominal_minimum_temperature_c=-5.0,
        nominal_maximum_temperature_c=5.0,
        priority_intervals=(_OperatingPriorityInterval(-5.0, 5.0, 2.0),),
    )
    scaled_and_split = _sensitivity_weighted_moment_matrix(
        model,
        degree=4,
        planning_reference_temperature_c=0.0,
        fitted_minimum_temperature_c=-5.0,
        fitted_maximum_temperature_c=5.0,
        nominal_minimum_temperature_c=-5.0,
        nominal_maximum_temperature_c=5.0,
        priority_intervals=(
            _OperatingPriorityInterval(-5.0, -1.0, 34.0),
            _OperatingPriorityInterval(-1.0, 5.0, 34.0),
        ),
    )

    for row in range(5):
        for column in range(5):
            difference = abs(
                scaled_and_split.moment_matrix[row][column]
                - unsplit.moment_matrix[row][column]
            )
            combined_estimated_error = (
                scaled_and_split.normalized_estimated_error_matrix[row][column]
                + unsplit.normalized_estimated_error_matrix[row][column]
            )
            assert difference <= combined_estimated_error


def test_moment_matrix_skips_zero_weight_intervals() -> None:
    class PositiveOnlyModel(_ConstantSensitivityModel):
        def temperature_sensitivity_celsius_per_ohm(
            self,
            temperature_c: float,
        ) -> float:
            if temperature_c < 0.0:
                raise AssertionError("zero-weight interval must not be evaluated")
            return super().temperature_sensitivity_celsius_per_ohm(temperature_c)

    model = PositiveOnlyModel(0.5)
    result = _sensitivity_weighted_moment_matrix(
        model,
        degree=2,
        planning_reference_temperature_c=0.0,
        fitted_minimum_temperature_c=-1.0,
        fitted_maximum_temperature_c=1.0,
        nominal_minimum_temperature_c=-1.0,
        nominal_maximum_temperature_c=1.0,
        priority_intervals=(
            _OperatingPriorityInterval(-1.0, 0.0, 0.0),
            _OperatingPriorityInterval(0.0, 1.0, 1.0),
        ),
    )

    assert result.structural_partition_c == (-1.0, 0.0, 1.0)
    assert result.accepted_subinterval_count == 1
    assert all(temperature >= 0.0 for temperature in model.evaluated_temperatures)


def test_moment_matrix_rejects_incomplete_priority_partition() -> None:
    with pytest.raises(
        RTDExperimentDesignError,
        match="complete non-overlapping partition",
    ):
        _sensitivity_weighted_moment_matrix(
            _ConstantSensitivityModel(1.0),
            degree=1,
            planning_reference_temperature_c=0.0,
            fitted_minimum_temperature_c=-1.0,
            fitted_maximum_temperature_c=1.0,
            nominal_minimum_temperature_c=-1.0,
            nominal_maximum_temperature_c=1.0,
            priority_intervals=(
                _OperatingPriorityInterval(-1.0, -0.25, 1.0),
                _OperatingPriorityInterval(0.25, 1.0, 1.0),
            ),
        )


def test_moment_matrix_rejects_fitted_range_outside_nominal_domain() -> None:
    with pytest.raises(
        RTDExperimentDesignError,
        match="must lie inside the nominal-sensitivity domain",
    ):
        _sensitivity_weighted_moment_matrix(
            _ConstantSensitivityModel(1.0),
            degree=1,
            planning_reference_temperature_c=0.0,
            fitted_minimum_temperature_c=-2.0,
            fitted_maximum_temperature_c=2.0,
            nominal_minimum_temperature_c=-1.0,
            nominal_maximum_temperature_c=2.0,
            priority_intervals=(_OperatingPriorityInterval(-2.0, 2.0, 1.0),),
        )


def test_moment_matrix_rejects_nonpositive_nominal_sensitivity() -> None:
    with pytest.raises(
        RTDExperimentDesignError,
        match="finite and strictly positive",
    ):
        _sensitivity_weighted_moment_matrix(
            _ConstantSensitivityModel(0.0),
            degree=1,
            planning_reference_temperature_c=0.0,
            fitted_minimum_temperature_c=-1.0,
            fitted_maximum_temperature_c=1.0,
            nominal_minimum_temperature_c=-1.0,
            nominal_maximum_temperature_c=1.0,
            priority_intervals=(_OperatingPriorityInterval(-1.0, 1.0, 1.0),),
        )


def test_moment_matrix_resource_limit_fails_instead_of_relaxing_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import rtd_sensor._experiment_design as experiment_design

    monkeypatch.setattr(experiment_design, "_MAX_MOMENT_INTERVAL_EVALUATIONS", 1)
    with pytest.raises(
        RTDExperimentDesignError,
        match="resource limit",
    ):
        experiment_design._sensitivity_weighted_moment_matrix(
            _OscillatorySensitivityModel(1.0),
            degree=2,
            planning_reference_temperature_c=0.0,
            fitted_minimum_temperature_c=-1.0,
            fitted_maximum_temperature_c=1.0,
            nominal_minimum_temperature_c=-1.0,
            nominal_maximum_temperature_c=1.0,
            priority_intervals=(
                experiment_design._OperatingPriorityInterval(-1.0, 1.0, 1.0),
            ),
        )


def test_moment_matrix_adapts_deterministically_for_smooth_black_box() -> None:
    class SmoothModel(_ConstantSensitivityModel):
        def temperature_sensitivity_celsius_per_ohm(
            self,
            temperature_c: float,
        ) -> float:
            self.evaluated_temperatures.append(temperature_c)
            return 1.0 + 0.2 * math.sin(5.0 * temperature_c)

    first = _sensitivity_weighted_moment_matrix(
        SmoothModel(1.0),
        degree=4,
        planning_reference_temperature_c=0.0,
        fitted_minimum_temperature_c=-1.0,
        fitted_maximum_temperature_c=1.0,
        nominal_minimum_temperature_c=-1.0,
        nominal_maximum_temperature_c=1.0,
        priority_intervals=(_OperatingPriorityInterval(-1.0, 1.0, 1.0),),
    )
    second = _sensitivity_weighted_moment_matrix(
        SmoothModel(1.0),
        degree=4,
        planning_reference_temperature_c=0.0,
        fitted_minimum_temperature_c=-1.0,
        fitted_maximum_temperature_c=1.0,
        nominal_minimum_temperature_c=-1.0,
        nominal_maximum_temperature_c=1.0,
        priority_intervals=(_OperatingPriorityInterval(-1.0, 1.0, 1.0),),
    )

    assert first == second
    assert first.adaptive_subdivision_occurred is True
    assert first.accepted_subinterval_count == 2
    assert first.sensitivity_evaluation_count == 93


def test_trace_objective_matches_direct_piecewise_analytic_integral() -> None:
    model = TabulatedRTDModel(
        points=(
            TabulatedRTDPoint(temperature_c=-10.0, resistance_ohms=90.0),
            TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
            TabulatedRTDPoint(temperature_c=20.0, resistance_ohms=140.0),
        )
    )
    moment = _sensitivity_weighted_moment_matrix(
        model,
        degree=3,
        planning_reference_temperature_c=5.0,
        fitted_minimum_temperature_c=-10.0,
        fitted_maximum_temperature_c=20.0,
        nominal_minimum_temperature_c=-10.0,
        nominal_maximum_temperature_c=20.0,
        priority_intervals=(_OperatingPriorityInterval(-10.0, 20.0, 1.0),),
        sensitivity_breakpoints_c=(0.0,),
    )
    covariance = _prospective_polynomial_covariance(
        (-10.0, -2.0, 8.0, 20.0),
        (0.02, 0.015, 0.025, 0.018),
        degree=3,
        planning_reference_temperature_c=5.0,
    ).covariance_matrix

    trace_objective = math.fsum(
        covariance[row][column] * moment.moment_matrix[column][row]
        for row in range(4)
        for column in range(4)
    )
    exact_piecewise_moment = _piecewise_constant_sensitivity_moment(
        (
            (-10.0, 0.0, 1.0, 1.0),
            (0.0, 20.0, 1.0, 0.5),
        ),
        degree=3,
        reference_temperature_c=5.0,
    )
    direct_analytic_objective = math.fsum(
        covariance[row][column] * exact_piecewise_moment[row][column]
        for row in range(4)
        for column in range(4)
    )
    propagated_integration_error = math.fsum(
        abs(covariance[row][column])
        * moment.normalized_estimated_error_matrix[row][column]
        for row in range(4)
        for column in range(4)
    )

    assert abs(trace_objective - direct_analytic_objective) <= (
        propagated_integration_error + 8.0 * math.ulp(abs(direct_analytic_objective))
    )


def test_moment_matrix_is_deterministic() -> None:
    from rtd_sensor._experiment_design import (
        _OperatingPriorityInterval,
        _sensitivity_weighted_moment_matrix,
    )

    priority_intervals = (
        _OperatingPriorityInterval(-200.0, 0.0, 0.5),
        _OperatingPriorityInterval(0.0, 850.0, 1.0),
    )
    first = _sensitivity_weighted_moment_matrix(
        pt100,
        degree=5,
        planning_reference_temperature_c=325.0,
        fitted_minimum_temperature_c=-200.0,
        fitted_maximum_temperature_c=850.0,
        nominal_minimum_temperature_c=-200.0,
        nominal_maximum_temperature_c=850.0,
        priority_intervals=priority_intervals,
        sensitivity_breakpoints_c=(0.0,),
    )
    second = _sensitivity_weighted_moment_matrix(
        pt100,
        degree=5,
        planning_reference_temperature_c=325.0,
        fitted_minimum_temperature_c=-200.0,
        fitted_maximum_temperature_c=850.0,
        nominal_minimum_temperature_c=-200.0,
        nominal_maximum_temperature_c=850.0,
        priority_intervals=priority_intervals,
        sensitivity_breakpoints_c=(0.0,),
    )

    assert second == first
    assert first.structural_partition_c == (-200.0, 0.0, 850.0)
