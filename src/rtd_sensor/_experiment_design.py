# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Private numerical foundations for calibration experiment design.

The public experiment-planning API is intentionally not introduced in this slice.
These helpers establish prospective polynomial information/covariance using the
same scaled weighted Householder system as :mod:`rtd_sensor.fitting`, while
expressing every covariance in one caller-specified planning reference basis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .exceptions import RTDExperimentDesignError, RTDFitError
from .fitting import (
    _CONDITIONING_METHOD,
    _MAX_SCALED_SYSTEM_CONDITION_NUMBER,
    _SOLVER,
    _householder_qr_upper,
    _normalized_inverse_variance_weights,
    _scale_covariance_matrix,
    _shift_scaled_polynomial_transform,
    _transform_covariance_matrix,
    _upper_triangular_information_inverse,
    _validate_degree,
)


@dataclass(frozen=True, slots=True)
class _ProspectivePolynomialCovariance:
    """Prospective polynomial covariance in one fixed planning basis."""

    covariance_matrix: tuple[tuple[float, ...], ...]
    parameter_names: tuple[str, ...]
    reference_temperature_c: float
    scaled_temperature_center_c: float
    scaled_temperature_half_range_c: float
    scaled_system_condition_number: float
    scaled_system_condition_limit: float
    conditioning_method: str
    solver: str


def _as_planning_float(value: float, *, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a real number, not bool")
    try:
        converted = float(value)
    except (TypeError, ValueError) as error:
        raise TypeError(f"{name} must be a real number") from error
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    return converted


def _prospective_polynomial_covariance(
    temperatures_c: tuple[float, ...],
    standard_uncertainties_ohms: tuple[float, ...],
    *,
    degree: int,
    planning_reference_temperature_c: float,
) -> _ProspectivePolynomialCovariance:
    """Construct prospective fitted-polynomial covariance before responses exist.

    The weighted design rows are formed in a candidate-span-scaled coordinate and
    reduced with the same Householder QR and conditioning guardrail used by
    ``fit_polynomial()``. With normalized inverse-variance weights
    ``w_i = (u_min / u_i)^2`` and Householder factor ``R``, the prospective
    covariance in that scaled basis is

    ``C_scaled = u_min^2 * (R.T @ R)^-1``.

    If ``A`` is the affine power-series coefficient transform from the scaled
    candidate coordinate into the fixed planning coordinate, the covariance used
    by the experiment-design criterion is the congruence transform

    ``C_theta = A @ C_scaled @ A.T``.

    This is the covariance that must share a basis with the planned moment matrix
    in ``J_T = trace(C_theta M_T)``. No resistance observations, fitted
    coefficients, or residuals are fabricated.
    """

    degree = _validate_degree(degree)
    reference_temperature_c = _as_planning_float(
        planning_reference_temperature_c,
        name="Planning reference temperature",
    )

    if len(temperatures_c) != len(standard_uncertainties_ohms):
        raise ValueError(
            "Temperatures and resistance standard uncertainties must have the same "
            "length"
        )
    if not temperatures_c:
        raise RTDExperimentDesignError(
            "At least one prospective calibration observation is required"
        )

    runs = tuple(
        sorted(
            (
                _as_planning_float(temperature, name="Temperature"),
                _as_planning_float(
                    uncertainty,
                    name="Resistance standard uncertainty",
                ),
            )
            for temperature, uncertainty in zip(
                temperatures_c,
                standard_uncertainties_ohms,
                strict=True,
            )
        )
    )
    if any(uncertainty <= 0.0 for _, uncertainty in runs):
        raise ValueError("Resistance standard uncertainty must be greater than zero")

    distinct_temperatures = {temperature for temperature, _ in runs}
    if len(distinct_temperatures) < degree + 1:
        raise RTDExperimentDesignError(
            f"Polynomial degree {degree} requires at least {degree + 1} distinct "
            "prospective calibration temperatures"
        )

    observed_minimum_c = min(distinct_temperatures)
    observed_maximum_c = max(distinct_temperatures)
    scaled_half_range_c = (observed_maximum_c - observed_minimum_c) / 2.0
    if scaled_half_range_c <= 0.0 or not math.isfinite(scaled_half_range_c):
        raise RTDExperimentDesignError(
            "Prospective calibration temperatures must span a finite interval"
        )
    scaled_center_c = (observed_minimum_c + observed_maximum_c) / 2.0

    uncertainties = tuple(uncertainty for _, uncertainty in runs)
    try:
        minimum_uncertainty, effective_weights = _normalized_inverse_variance_weights(
            uncertainties
        )
    except ValueError as error:
        raise RTDExperimentDesignError(str(error)) from error
    covariance_scale = minimum_uncertainty * minimum_uncertainty
    if not math.isfinite(covariance_scale) or covariance_scale <= 0.0:
        raise RTDExperimentDesignError(
            "Resistance standard uncertainties have an unrepresentable covariance scale"
        )

    matrix: list[list[float]] = []
    for (temperature_c, _), weight in zip(runs, effective_weights, strict=True):
        scaled_temperature = (temperature_c - scaled_center_c) / scaled_half_range_c
        row = [1.0]
        for _ in range(degree):
            row.append(row[-1] * scaled_temperature)
        row_scale = math.sqrt(weight)
        matrix.append([value * row_scale for value in row])

    try:
        upper, condition_number, transformed_rhs = _householder_qr_upper(matrix)
        assert transformed_rhs is None
        scaled_information_inverse = _upper_triangular_information_inverse(upper)
        scaled_covariance = _scale_covariance_matrix(
            scaled_information_inverse,
            covariance_scale,
        )
        transform = _shift_scaled_polynomial_transform(
            degree + 1,
            scaled_center_c=scaled_center_c,
            scaled_half_range_c=scaled_half_range_c,
            reference_temperature_c=reference_temperature_c,
        )
        transformed_covariance = _transform_covariance_matrix(
            scaled_covariance,
            transform,
        )
    except RTDFitError as error:
        raise RTDExperimentDesignError(
            "Prospective polynomial design is not identifiable or numerically "
            f"admissible: {error}"
        ) from error
    except (OverflowError, ValueError) as error:
        raise RTDExperimentDesignError(
            "Prospective polynomial covariance is not finitely representable"
        ) from error

    covariance_matrix = tuple(
        tuple(
            0.5 * transformed_covariance[row][column]
            + 0.5 * transformed_covariance[column][row]
            for column in range(len(transformed_covariance))
        )
        for row in range(len(transformed_covariance))
    )
    if not all(
        math.isfinite(value) for row in covariance_matrix for value in row
    ) or not all(
        covariance_matrix[index][index] >= 0.0
        for index in range(len(covariance_matrix))
    ):
        raise RTDExperimentDesignError(
            "Prospective polynomial covariance is not finitely representable"
        )

    return _ProspectivePolynomialCovariance(
        covariance_matrix=covariance_matrix,
        parameter_names=tuple(f"a{power}" for power in range(degree + 1)),
        reference_temperature_c=reference_temperature_c,
        scaled_temperature_center_c=scaled_center_c,
        scaled_temperature_half_range_c=scaled_half_range_c,
        scaled_system_condition_number=condition_number,
        scaled_system_condition_limit=_MAX_SCALED_SYSTEM_CONDITION_NUMBER,
        conditioning_method=_CONDITIONING_METHOD,
        solver=_SOLVER,
    )
