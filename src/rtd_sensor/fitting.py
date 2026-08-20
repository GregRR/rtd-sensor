# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Calibration fitting for traceable RTD models.

The fitting API intentionally keeps the fitted numerical model separate from the
observations and diagnostics that justify it. Successful fits return a validated
model together with immutable fit evidence.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from . import _curves
from ._curves import _MAX_POLYNOMIAL_DEGREE
from .exceptions import InvalidRTDModelError, RTDFitError
from .models import IEC60751RTDModel, PolynomialRTDModel

__all__ = [
    "CalibrationObservation",
    "IEC60751R0FitEvidence",
    "IEC60751R0FitResult",
    "FitParameterCovariance",
    "PolynomialFitEvidence",
    "PolynomialFitResult",
    "fit_iec60751_r0",
    "fit_polynomial",
]

_MAX_SCALED_SYSTEM_CONDITION_NUMBER = 1.0e10
_CONDITIONING_METHOD = "infinity_norm_of_householder_r"
_SOLVER = "householder_qr_least_squares"
_WeightingMethod = Literal[
    "unweighted",
    "normalized_explicit_weights",
    "normalized_inverse_variance_from_standard_uncertainty",
]
_CovarianceEstimationMethod = Literal[
    "residual_variance_scaled_least_squares",
    "resistance_standard_uncertainties",
]
_CovarianceParameterization = Literal[
    "r0_ohms",
    "resistance_power_series_at_model_reference_temperature",
]
_CovarianceUnavailableReason = Literal[
    "residual_variance_requires_positive_degrees_of_freedom",
    "covariance_not_finitely_representable",
]


def _as_float(value: float, *, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a real number, not bool")
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise TypeError(f"{name} must be a real number") from error


@dataclass(frozen=True, slots=True)
class CalibrationObservation:
    """One measured calibration point used by a fitting operation.

    Exactly one weighting convention may be used for a weighted fit. ``weight`` is
    a caller-supplied positive relative least-squares weight.
    ``standard_uncertainty_ohms`` is a positive standard uncertainty in resistance;
    it is converted to an inverse-variance weight ``1 / u**2``.
    """

    temperature_c: float
    resistance_ohms: float
    weight: float | None = None
    standard_uncertainty_ohms: float | None = None

    def __post_init__(self) -> None:
        temperature_c = _as_float(self.temperature_c, name="Temperature")
        resistance_ohms = _as_float(self.resistance_ohms, name="Resistance")
        weight = None if self.weight is None else _as_float(self.weight, name="Weight")
        uncertainty = (
            None
            if self.standard_uncertainty_ohms is None
            else _as_float(
                self.standard_uncertainty_ohms,
                name="Standard uncertainty",
            )
        )

        if not math.isfinite(temperature_c):
            raise ValueError("Temperature must be finite")
        if not math.isfinite(resistance_ohms):
            raise ValueError("Resistance must be finite")
        if resistance_ohms <= 0.0:
            raise ValueError("Resistance must be greater than zero")
        if weight is not None:
            if not math.isfinite(weight):
                raise ValueError("Weight must be finite")
            if weight <= 0.0:
                raise ValueError("Weight must be greater than zero")
        if uncertainty is not None:
            if not math.isfinite(uncertainty):
                raise ValueError("Standard uncertainty must be finite")
            if uncertainty <= 0.0:
                raise ValueError("Standard uncertainty must be greater than zero")
        if weight is not None and uncertainty is not None:
            raise ValueError("Specify either weight or standard uncertainty, not both")

        object.__setattr__(self, "temperature_c", temperature_c)
        object.__setattr__(self, "resistance_ohms", resistance_ohms)
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "standard_uncertainty_ohms", uncertainty)


@dataclass(frozen=True, slots=True)
class FitParameterCovariance:
    """Covariance matrix for parameters estimated by one fitting operation.

    ``covariance_matrix`` follows ``parameter_names`` in both dimensions. For
    polynomial fits the parameterization is the unnormalized resistance power
    series at the returned model's reference temperature,
    ``R(T) = a0 + a1*x + ...``. This is intentionally fit evidence rather than
    part of the deployable model definition.

    ``residual_variance_scaled_least_squares`` means the unknown common residual
    variance scale was estimated from the fit residuals and residual degrees of
    freedom. ``resistance_standard_uncertainties`` means absolute, independent
    resistance standard uncertainties supplied on every observation defined the
    covariance directly; residual scatter does not rescale that covariance.
    """

    parameter_names: tuple[str, ...]
    covariance_matrix: tuple[tuple[float, ...], ...]
    estimation_method: _CovarianceEstimationMethod
    parameterization: _CovarianceParameterization


@dataclass(frozen=True, slots=True)
class IEC60751R0FitEvidence:
    """Immutable observations and diagnostics supporting an IEC R0 fit.

    The fitted parameter is only ``R0``. The IEC 60751 PT-385 normalized
    characteristic remains fixed. Residuals are ``observed resistance - fitted
    resistance`` in ohms. ``rms_residual_ohms`` is the descriptive root mean
    square ``sqrt(sum(residual**2) / observation_count)``, not a
    degrees-of-freedom-adjusted estimate of residual standard deviation. When
    ``residual_degrees_of_freedom`` is zero, the residual metrics are
    approximately zero by construction and do not measure fit quality.

    The observation span is retained separately from the model's declared
    validity range because a caller may have independent justification for an
    applicability interval that is broader, narrower, or disjoint from the
    temperatures used to characterize ``R0``. Parameter covariance is retained
    when its statistical scale is defined. Unweighted and relative-weighted
    zero-DOF fits record why covariance is unavailable; absolute resistance
    standard uncertainties can define covariance even at zero residual DOF.
    """

    observations: tuple[CalibrationObservation, ...]
    residuals_ohms: tuple[float, ...]
    observation_count: int
    fitted_parameter_count: int
    residual_degrees_of_freedom: int
    observation_minimum_temperature_c: float
    observation_maximum_temperature_c: float
    minimum_temperature_c: float
    maximum_temperature_c: float
    rms_residual_ohms: float
    max_absolute_residual_ohms: float
    weighting_method: _WeightingMethod
    effective_weights: tuple[float, ...] | None
    weighted_sum_squared_residual: float | None
    weighted_rms_residual_ohms: float | None
    parameter_covariance: FitParameterCovariance | None
    parameter_covariance_unavailable_reason: _CovarianceUnavailableReason | None
    solver: str


@dataclass(frozen=True, slots=True)
class IEC60751R0FitResult:
    """Fitted IEC 60751 model and the evidence supporting the R0 estimate."""

    model: IEC60751RTDModel
    evidence: IEC60751R0FitEvidence


@dataclass(frozen=True, slots=True)
class PolynomialFitEvidence:
    """Immutable observations and diagnostics supporting a polynomial fit.

    Residuals are ``observed resistance - fitted resistance`` in ohms. RMS and
    maximum absolute residuals are always unweighted. ``rms_residual_ohms`` is the
    descriptive root mean square ``sqrt(sum(residual**2) / observation_count)``, not
    a degrees-of-freedom-adjusted estimate of residual standard deviation. The
    explicit observation, fitted-parameter, and residual-degrees-of-freedom counts
    make saturated or nearly saturated fits visible to callers. Weighted diagnostics
    are populated only when the observations use an explicit weighting convention.
    Effective weights are normalized so the largest weight is 1.0; this preserves
    the least-squares objective while avoiding arbitrary overall weight scale.
    Parameter covariance is retained in the unnormalized resistance power-series
    basis at the returned model's reference temperature. Unweighted and relative-
    weighted fits estimate the common variance scale from residuals and therefore
    require positive residual degrees of freedom; absolute resistance standard
    uncertainties define covariance directly.
    """

    observations: tuple[CalibrationObservation, ...]
    residuals_ohms: tuple[float, ...]
    degree: int
    observation_count: int
    fitted_parameter_count: int
    residual_degrees_of_freedom: int
    minimum_temperature_c: float
    maximum_temperature_c: float
    rms_residual_ohms: float
    max_absolute_residual_ohms: float
    weighting_method: _WeightingMethod
    effective_weights: tuple[float, ...] | None
    weighted_sum_squared_residual: float | None
    weighted_rms_residual_ohms: float | None
    parameter_covariance: FitParameterCovariance | None
    parameter_covariance_unavailable_reason: _CovarianceUnavailableReason | None
    scaled_system_condition_number: float
    scaled_system_condition_limit: float
    conditioning_method: str
    solver: str
    scaled_temperature_center_c: float
    scaled_temperature_half_range_c: float


@dataclass(frozen=True, slots=True)
class PolynomialFitResult:
    """Validated fitted polynomial model and the evidence supporting the fit."""

    model: PolynomialRTDModel
    evidence: PolynomialFitEvidence


def _validate_degree(degree: int) -> int:
    if isinstance(degree, bool) or not isinstance(degree, int):
        raise TypeError("Polynomial degree must be an integer")
    if degree < 1:
        raise ValueError("Polynomial degree must be at least 1")
    if degree > _MAX_POLYNOMIAL_DEGREE:
        raise ValueError(f"Polynomial degree must not exceed {_MAX_POLYNOMIAL_DEGREE}")
    return degree


def _effective_weights(
    observations: tuple[CalibrationObservation, ...],
) -> tuple[_WeightingMethod, tuple[float, ...] | None]:
    has_weights = [observation.weight is not None for observation in observations]
    has_uncertainties = [
        observation.standard_uncertainty_ohms is not None
        for observation in observations
    ]

    if any(has_weights) and any(has_uncertainties):
        raise RTDFitError(
            "A fit must use one weighting convention: explicit weights or "
            "standard uncertainties"
        )
    if any(has_weights):
        if not all(has_weights):
            raise RTDFitError(
                "Every observation must provide a weight for a weighted fit"
            )
        raw_weights: list[float] = []
        for observation in observations:
            weight = observation.weight
            assert weight is not None
            raw_weights.append(weight)
        maximum_weight = max(raw_weights)
        effective_weights = tuple(weight / maximum_weight for weight in raw_weights)
        if not all(weight > 0.0 for weight in effective_weights):
            raise RTDFitError(
                "Calibration weights have an unrepresentable dynamic range"
            )
        return "normalized_explicit_weights", effective_weights
    if any(has_uncertainties):
        if not all(has_uncertainties):
            raise RTDFitError(
                "Every observation must provide a standard uncertainty for an "
                "uncertainty-weighted fit"
            )
        uncertainties: list[float] = []
        for observation in observations:
            uncertainty = observation.standard_uncertainty_ohms
            assert uncertainty is not None
            uncertainties.append(uncertainty)
        minimum_uncertainty = min(uncertainties)
        effective_weights = tuple(
            (minimum_uncertainty / uncertainty) ** 2 for uncertainty in uncertainties
        )
        if not all(
            math.isfinite(weight) and weight > 0.0 for weight in effective_weights
        ):
            raise RTDFitError(
                "Standard uncertainties have an unrepresentable inverse-variance "
                "weighting range"
            )
        return (
            "normalized_inverse_variance_from_standard_uncertainty",
            effective_weights,
        )
    return "unweighted", None


def _householder_least_squares(
    matrix: list[list[float]],
    vector: list[float],
) -> tuple[tuple[float, ...], float, tuple[tuple[float, ...], ...]]:
    row_count = len(matrix)
    column_count = len(matrix[0])
    transformed = [row[:] for row in matrix]
    rhs = vector[:]

    for column in range(column_count):
        norm = 0.0
        for row in range(column, row_count):
            norm = math.hypot(norm, transformed[row][column])
        if norm == 0.0 or not math.isfinite(norm):
            raise RTDFitError("Calibration observations are rank deficient")

        leading = transformed[column][column]
        alpha = -math.copysign(norm, leading if leading != 0.0 else 1.0)
        reflector = [transformed[row][column] for row in range(column, row_count)]
        reflector[0] -= alpha
        reflector_norm_squared = math.fsum(value * value for value in reflector)
        if reflector_norm_squared == 0.0 or not math.isfinite(reflector_norm_squared):
            raise RTDFitError("Calibration observations are rank deficient")
        beta = 2.0 / reflector_norm_squared

        for target_column in range(column, column_count):
            projection = beta * math.fsum(
                reflector[offset] * transformed[column + offset][target_column]
                for offset in range(len(reflector))
            )
            for offset, value in enumerate(reflector):
                transformed[column + offset][target_column] -= projection * value

        rhs_projection = beta * math.fsum(
            reflector[offset] * rhs[column + offset] for offset in range(len(reflector))
        )
        for offset, value in enumerate(reflector):
            rhs[column + offset] -= rhs_projection * value

        transformed[column][column] = alpha
        for row in range(column + 1, row_count):
            transformed[row][column] = 0.0

    upper = [row[:column_count] for row in transformed[:column_count]]
    condition_number = _upper_triangular_condition_inf(upper)
    if not math.isfinite(condition_number):
        raise RTDFitError("Calibration observations are rank deficient")
    if condition_number > _MAX_SCALED_SYSTEM_CONDITION_NUMBER:
        raise RTDFitError(
            "Scaled calibration system is severely ill-conditioned "
            f"(condition diagnostic {condition_number:.6g} exceeds "
            f"{_MAX_SCALED_SYSTEM_CONDITION_NUMBER:.6g})"
        )

    coefficients = _back_substitute(upper, rhs[:column_count])
    if not all(math.isfinite(value) for value in coefficients):
        raise RTDFitError("Polynomial fit produced non-finite coefficients")
    return (
        tuple(coefficients),
        condition_number,
        tuple(tuple(value for value in row) for row in upper),
    )


def _back_substitute(
    upper: list[list[float]],
    rhs: list[float],
) -> list[float]:
    size = len(upper)
    solution = [0.0] * size
    for row in range(size - 1, -1, -1):
        diagonal = upper[row][row]
        if diagonal == 0.0 or not math.isfinite(diagonal):
            raise RTDFitError("Calibration observations are rank deficient")
        remainder = math.fsum(
            upper[row][column] * solution[column] for column in range(row + 1, size)
        )
        solution[row] = (rhs[row] - remainder) / diagonal
    return solution


def _upper_triangular_information_inverse(
    upper: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], ...]:
    """Return ``(R.T @ R)^-1`` for a nonsingular upper-triangular ``R``."""

    upper_lists = [list(row) for row in upper]
    size = len(upper_lists)
    inverse_columns: list[list[float]] = []
    for column in range(size):
        rhs = [0.0] * size
        rhs[column] = 1.0
        inverse_columns.append(_back_substitute(upper_lists, rhs))

    # (R.T R)^-1 = R^-1 R^-T. ``inverse_columns`` stores columns of R^-1.
    return tuple(
        tuple(
            math.fsum(
                inverse_columns[column][row] * inverse_columns[column][other_row]
                for column in range(size)
            )
            for other_row in range(size)
        )
        for row in range(size)
    )


def _scale_covariance_matrix(
    matrix: tuple[tuple[float, ...], ...],
    scale: float,
) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(scale * value for value in row) for row in matrix)


def _transform_covariance_matrix(
    covariance: tuple[tuple[float, ...], ...],
    transform: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], ...]:
    """Return ``transform @ covariance @ transform.T``."""

    size = len(covariance)
    return tuple(
        tuple(
            math.fsum(
                transform[row][left]
                * covariance[left][right]
                * transform[other_row][right]
                for left in range(size)
                for right in range(size)
            )
            for other_row in range(size)
        )
        for row in range(size)
    )


def _covariance_scale_and_method(
    observations: tuple[CalibrationObservation, ...],
    *,
    weighting_method: _WeightingMethod,
    residuals_ohms: tuple[float, ...],
    effective_weights: tuple[float, ...] | None,
    residual_degrees_of_freedom: int,
) -> tuple[
    float | None,
    _CovarianceEstimationMethod | None,
    _CovarianceUnavailableReason | None,
]:
    if weighting_method == "normalized_inverse_variance_from_standard_uncertainty":
        uncertainties = tuple(
            observation.standard_uncertainty_ohms for observation in observations
        )
        assert all(uncertainty is not None for uncertainty in uncertainties)
        minimum_uncertainty = min(
            uncertainty for uncertainty in uncertainties if uncertainty is not None
        )
        covariance_scale = minimum_uncertainty * minimum_uncertainty
        if not math.isfinite(covariance_scale) or covariance_scale <= 0.0:
            return (None, None, "covariance_not_finitely_representable")
        return (
            covariance_scale,
            "resistance_standard_uncertainties",
            None,
        )

    if residual_degrees_of_freedom <= 0:
        return (
            None,
            None,
            "residual_variance_requires_positive_degrees_of_freedom",
        )

    if effective_weights is None:
        sum_squared_residual = math.fsum(
            residual * residual for residual in residuals_ohms
        )
    else:
        sum_squared_residual = math.fsum(
            weight * residual * residual
            for weight, residual in zip(effective_weights, residuals_ohms, strict=True)
        )
    return (
        sum_squared_residual / residual_degrees_of_freedom,
        "residual_variance_scaled_least_squares",
        None,
    )


def _shift_scaled_polynomial_transform(
    coefficient_count: int,
    *,
    scaled_center_c: float,
    scaled_half_range_c: float,
    reference_temperature_c: float,
) -> tuple[tuple[float, ...], ...]:
    alpha = (reference_temperature_c - scaled_center_c) / scaled_half_range_c
    beta = 1.0 / scaled_half_range_c
    return tuple(
        tuple(
            (
                math.comb(scaled_power, shifted_power)
                * alpha ** (scaled_power - shifted_power)
                * beta**shifted_power
                if scaled_power >= shifted_power
                else 0.0
            )
            for scaled_power in range(coefficient_count)
        )
        for shifted_power in range(coefficient_count)
    )


def _upper_triangular_condition_inf(upper: list[list[float]]) -> float:
    size = len(upper)
    norm = max(
        math.fsum(abs(upper[row][column]) for column in range(row, size))
        for row in range(size)
    )
    if norm == 0.0 or not math.isfinite(norm):
        return math.inf

    inverse_row_sums = [0.0] * size
    for column in range(size):
        rhs = [0.0] * size
        rhs[column] = 1.0
        inverse_column = _back_substitute(upper, rhs)
        for row, value in enumerate(inverse_column):
            inverse_row_sums[row] += abs(value)
    inverse_norm = max(inverse_row_sums)
    return norm * inverse_norm


def _shift_scaled_polynomial(
    scaled_coefficients: tuple[float, ...],
    *,
    scaled_center_c: float,
    scaled_half_range_c: float,
    reference_temperature_c: float,
) -> tuple[float, ...]:
    alpha = (reference_temperature_c - scaled_center_c) / scaled_half_range_c
    beta = 1.0 / scaled_half_range_c
    shifted = [0.0] * len(scaled_coefficients)

    for power, coefficient in enumerate(scaled_coefficients):
        for shifted_power in range(power + 1):
            shifted[shifted_power] += (
                coefficient
                * math.comb(power, shifted_power)
                * alpha ** (power - shifted_power)
                * beta**shifted_power
            )
    return tuple(shifted)


def _power_series_value(coefficients: tuple[float, ...], x: float) -> float:
    result = 0.0
    for coefficient in reversed(coefficients):
        result = result * x + coefficient
    return result


def fit_iec60751_r0(
    observations: Iterable[CalibrationObservation],
    *,
    minimum_temperature_c: float | None = None,
    maximum_temperature_c: float | None = None,
    name: str = "Fitted IEC 60751 RTD",
) -> IEC60751R0FitResult:
    """Fit only ``R0`` while retaining the IEC 60751 PT-385 characteristic.

    For each observation, the normalized IEC characteristic supplies
    ``rho(T) = R(T) / R0`` and the fitter solves the one-parameter linear
    least-squares problem ``R_observed = R0 * rho(T)``. Relative weights and
    resistance standard uncertainties use the same conventions as
    :func:`fit_polynomial`. Temperature is treated as the independent variable.

    If no model range is supplied, at least two distinct temperatures are
    required and the returned model uses the observed temperature span. If a
    range is supplied, both limits must be supplied together. That explicit
    applicability range is independent of the observation span: it may be
    broader, narrower, or disjoint, but it must remain inside the IEC 60751
    PT-385 characteristic range. The range is a caller-declared applicability
    assumption; it is not evidence that the calibration observations validated
    performance throughout that interval.

    A single observation can therefore identify ``R0`` only when the caller
    explicitly declares the model range. Fitting ``R0`` does not establish IEC
    tolerance-class conformance or physical probe accuracy away from the
    calibration observations.

    Raises:
        TypeError: If observations use an invalid value category.
        ValueError: If scalar range arguments are malformed.
        RTDFitError: If observations are absent, weighting is inconsistent, a
            default validity span cannot be inferred, or the fit cannot produce
            a finite positive ``R0``.
    """

    observation_tuple = tuple(observations)
    if not observation_tuple:
        raise RTDFitError("At least one calibration observation is required")
    if not all(
        isinstance(observation, CalibrationObservation)
        for observation in observation_tuple
    ):
        raise TypeError("Observations must be CalibrationObservation values")

    distinct_temperatures = {
        observation.temperature_c for observation in observation_tuple
    }
    observed_minimum_c = min(distinct_temperatures)
    observed_maximum_c = max(distinct_temperatures)
    if (
        observed_minimum_c < _curves.IEC_60751_PT385.minimum_temperature_c
        or observed_maximum_c > _curves.IEC_60751_PT385.maximum_temperature_c
    ):
        raise RTDFitError(
            "Calibration temperatures must lie within the IEC 60751 PT-385 range"
        )

    has_minimum = minimum_temperature_c is not None
    has_maximum = maximum_temperature_c is not None
    if has_minimum != has_maximum:
        raise ValueError(
            "Minimum and maximum fitted temperatures must be supplied together"
        )

    if not has_minimum:
        if observed_minimum_c == observed_maximum_c:
            raise RTDFitError(
                "A single-temperature R0 fit requires an explicit model range"
            )
        minimum_c = observed_minimum_c
        maximum_c = observed_maximum_c
    else:
        assert minimum_temperature_c is not None
        assert maximum_temperature_c is not None
        minimum_c = _as_float(
            minimum_temperature_c,
            name="Minimum fitted temperature",
        )
        maximum_c = _as_float(
            maximum_temperature_c,
            name="Maximum fitted temperature",
        )
        if not math.isfinite(minimum_c):
            raise ValueError("Minimum fitted temperature must be finite")
        if not math.isfinite(maximum_c):
            raise ValueError("Maximum fitted temperature must be finite")
        if minimum_c >= maximum_c:
            raise ValueError(
                "Minimum fitted temperature must be below maximum fitted temperature"
            )

    weighting_method, effective_weights = _effective_weights(observation_tuple)

    numerator_terms: list[float] = []
    denominator_terms: list[float] = []
    for index, observation in enumerate(observation_tuple):
        ratio = _curves.IEC_60751_PT385.resistance_ratio(observation.temperature_c)
        weight = 1.0 if effective_weights is None else effective_weights[index]
        numerator_terms.append(weight * ratio * observation.resistance_ohms)
        denominator_terms.append(weight * ratio * ratio)

    numerator = math.fsum(numerator_terms)
    denominator = math.fsum(denominator_terms)
    if (
        not math.isfinite(numerator)
        or not math.isfinite(denominator)
        or denominator <= 0.0
    ):
        raise RTDFitError("R0 fit produced a non-finite least-squares system")

    r0_ohms = numerator / denominator
    if not math.isfinite(r0_ohms) or r0_ohms <= 0.0:
        raise RTDFitError("Fitted R0 must be finite and positive")

    try:
        model = IEC60751RTDModel(
            r0_ohms=r0_ohms,
            name=name,
            minimum_temperature_c=minimum_c,
            maximum_temperature_c=maximum_c,
        )
    except InvalidRTDModelError as error:
        raise RTDFitError(f"Fitted IEC 60751 model is not valid: {error}") from error

    residuals = tuple(
        observation.resistance_ohms
        - r0_ohms * _curves.IEC_60751_PT385.resistance_ratio(observation.temperature_c)
        for observation in observation_tuple
    )
    rms_residual_ohms = math.sqrt(
        math.fsum(residual * residual for residual in residuals) / len(residuals)
    )
    max_absolute_residual_ohms = max(abs(residual) for residual in residuals)

    weighted_sum_squared_residual: float | None = None
    weighted_rms_residual_ohms: float | None = None
    if effective_weights is not None:
        weighted_sum_squared_residual = math.fsum(
            weight * residual * residual
            for weight, residual in zip(effective_weights, residuals, strict=True)
        )
        total_weight = math.fsum(effective_weights)
        weighted_rms_residual_ohms = math.sqrt(
            weighted_sum_squared_residual / total_weight
        )

    residual_degrees_of_freedom = len(observation_tuple) - 1
    covariance_scale, covariance_method, covariance_unavailable_reason = (
        _covariance_scale_and_method(
            observation_tuple,
            weighting_method=weighting_method,
            residuals_ohms=residuals,
            effective_weights=effective_weights,
            residual_degrees_of_freedom=residual_degrees_of_freedom,
        )
    )
    parameter_covariance: FitParameterCovariance | None = None
    if covariance_scale is not None:
        assert covariance_method is not None
        variance_r0 = covariance_scale / denominator
        if not math.isfinite(variance_r0) or variance_r0 < 0.0:
            covariance_unavailable_reason = "covariance_not_finitely_representable"
        else:
            parameter_covariance = FitParameterCovariance(
                parameter_names=("r0_ohms",),
                covariance_matrix=((variance_r0,),),
                estimation_method=covariance_method,
                parameterization="r0_ohms",
            )

    evidence = IEC60751R0FitEvidence(
        observations=observation_tuple,
        residuals_ohms=residuals,
        observation_count=len(observation_tuple),
        fitted_parameter_count=1,
        residual_degrees_of_freedom=residual_degrees_of_freedom,
        observation_minimum_temperature_c=observed_minimum_c,
        observation_maximum_temperature_c=observed_maximum_c,
        minimum_temperature_c=minimum_c,
        maximum_temperature_c=maximum_c,
        rms_residual_ohms=rms_residual_ohms,
        max_absolute_residual_ohms=max_absolute_residual_ohms,
        weighting_method=weighting_method,
        effective_weights=effective_weights,
        weighted_sum_squared_residual=weighted_sum_squared_residual,
        weighted_rms_residual_ohms=weighted_rms_residual_ohms,
        parameter_covariance=parameter_covariance,
        parameter_covariance_unavailable_reason=covariance_unavailable_reason,
        solver="closed_form_single_parameter_least_squares",
    )
    return IEC60751R0FitResult(model=model, evidence=evidence)


def fit_polynomial(
    observations: Iterable[CalibrationObservation],
    *,
    degree: int,
    minimum_temperature_c: float | None = None,
    maximum_temperature_c: float | None = None,
    name: str = "Fitted polynomial RTD",
    coefficient_source: str | None = None,
) -> PolynomialFitResult:
    """Fit a validated polynomial RTD model to calibration observations.

    The least-squares system is solved with Householder QR after linearly scaling
    the observed temperature span to ``[-1, 1]``. The returned model is referenced
    at the midpoint of its declared fitted range. The valid range defaults to the
    complete observed temperature span and may be narrowed, but never extended,
    by the caller.

    Weighted fits must use one convention consistently across every observation:
    either positive relative ``weight`` values or positive resistance standard
    uncertainties. Standard uncertainties are converted to inverse-variance
    weights proportional to ``1 / u**2``. Effective weights are normalized so the
    largest is 1.0 and are retained in the evidence. Temperature is treated as the
    independent variable; this initial fitter does not implement errors-in-variables
    regression for temperature uncertainty.

    Raises:
        TypeError: If the degree or observations use an invalid value category.
        ValueError: If a scalar degree or range argument is malformed.
        RTDFitError: If the observations are insufficient, the weighting contract
            is inconsistent, the scaled system is severely ill-conditioned, or
            the fitted curve is not a valid monotonic RTD model over its declared
            range.
    """

    degree = _validate_degree(degree)
    observation_tuple = tuple(observations)
    if not observation_tuple:
        raise RTDFitError("At least one calibration observation is required")
    if not all(
        isinstance(observation, CalibrationObservation)
        for observation in observation_tuple
    ):
        raise TypeError("Observations must be CalibrationObservation values")

    distinct_temperatures = {
        observation.temperature_c for observation in observation_tuple
    }
    if len(distinct_temperatures) < degree + 1:
        raise RTDFitError(
            f"Polynomial degree {degree} requires at least {degree + 1} distinct "
            "temperature observations"
        )

    observed_minimum_c = min(distinct_temperatures)
    observed_maximum_c = max(distinct_temperatures)
    scaled_half_range_c = (observed_maximum_c - observed_minimum_c) / 2.0
    if scaled_half_range_c <= 0.0 or not math.isfinite(scaled_half_range_c):
        raise RTDFitError("Calibration temperatures must span a finite interval")
    scaled_center_c = (observed_minimum_c + observed_maximum_c) / 2.0

    minimum_c = (
        observed_minimum_c
        if minimum_temperature_c is None
        else _as_float(minimum_temperature_c, name="Minimum fitted temperature")
    )
    maximum_c = (
        observed_maximum_c
        if maximum_temperature_c is None
        else _as_float(maximum_temperature_c, name="Maximum fitted temperature")
    )
    if not math.isfinite(minimum_c):
        raise ValueError("Minimum fitted temperature must be finite")
    if not math.isfinite(maximum_c):
        raise ValueError("Maximum fitted temperature must be finite")
    if minimum_c >= maximum_c:
        raise ValueError(
            "Minimum fitted temperature must be below maximum fitted temperature"
        )
    if minimum_c < observed_minimum_c or maximum_c > observed_maximum_c:
        raise RTDFitError(
            "Fitted temperature range may not extend beyond the observed "
            "calibration span"
        )

    weighting_method, effective_weights = _effective_weights(observation_tuple)
    matrix: list[list[float]] = []
    vector: list[float] = []
    for index, observation in enumerate(observation_tuple):
        scaled_temperature = (
            observation.temperature_c - scaled_center_c
        ) / scaled_half_range_c
        row = [1.0]
        for _ in range(degree):
            row.append(row[-1] * scaled_temperature)

        weight = 1.0 if effective_weights is None else effective_weights[index]
        row_scale = math.sqrt(weight)
        matrix.append([value * row_scale for value in row])
        vector.append(observation.resistance_ohms * row_scale)

    scaled_coefficients, condition_number, upper = _householder_least_squares(
        matrix,
        vector,
    )

    reference_temperature_c = (minimum_c + maximum_c) / 2.0
    try:
        shifted_coefficients = _shift_scaled_polynomial(
            scaled_coefficients,
            scaled_center_c=scaled_center_c,
            scaled_half_range_c=scaled_half_range_c,
            reference_temperature_c=reference_temperature_c,
        )
    except OverflowError as error:
        raise RTDFitError(
            "Polynomial fit cannot be represented with finite model coefficients"
        ) from error
    reference_resistance_ohms = shifted_coefficients[0]
    if not math.isfinite(reference_resistance_ohms) or reference_resistance_ohms <= 0.0:
        raise RTDFitError("Fitted reference resistance must be finite and positive")
    normalized_coefficients = tuple(
        coefficient / reference_resistance_ohms
        for coefficient in shifted_coefficients[1:]
    )

    try:
        model = PolynomialRTDModel(
            reference_resistance_ohms=reference_resistance_ohms,
            coefficients=normalized_coefficients,
            minimum_temperature_c=minimum_c,
            maximum_temperature_c=maximum_c,
            reference_temperature_c=reference_temperature_c,
            name=name,
            coefficient_source=coefficient_source,
        )
    except InvalidRTDModelError as error:
        raise RTDFitError(
            f"Fitted polynomial is not a valid RTD model: {error}"
        ) from error

    residuals = tuple(
        observation.resistance_ohms
        - _power_series_value(
            scaled_coefficients,
            (observation.temperature_c - scaled_center_c) / scaled_half_range_c,
        )
        for observation in observation_tuple
    )
    rms_residual_ohms = math.sqrt(
        math.fsum(residual * residual for residual in residuals) / len(residuals)
    )
    max_absolute_residual_ohms = max(abs(residual) for residual in residuals)

    weighted_sum_squared_residual: float | None = None
    weighted_rms_residual_ohms: float | None = None
    if effective_weights is not None:
        weighted_sum_squared_residual = math.fsum(
            weight * residual * residual
            for weight, residual in zip(effective_weights, residuals, strict=True)
        )
        total_weight = math.fsum(effective_weights)
        weighted_rms_residual_ohms = math.sqrt(
            weighted_sum_squared_residual / total_weight
        )

    residual_degrees_of_freedom = len(observation_tuple) - (degree + 1)
    covariance_scale, covariance_method, covariance_unavailable_reason = (
        _covariance_scale_and_method(
            observation_tuple,
            weighting_method=weighting_method,
            residuals_ohms=residuals,
            effective_weights=effective_weights,
            residual_degrees_of_freedom=residual_degrees_of_freedom,
        )
    )
    parameter_covariance: FitParameterCovariance | None = None
    if covariance_scale is not None:
        assert covariance_method is not None
        try:
            scaled_information_inverse = _upper_triangular_information_inverse(upper)
            scaled_covariance = _scale_covariance_matrix(
                scaled_information_inverse, covariance_scale
            )
            transform = _shift_scaled_polynomial_transform(
                len(scaled_coefficients),
                scaled_center_c=scaled_center_c,
                scaled_half_range_c=scaled_half_range_c,
                reference_temperature_c=reference_temperature_c,
            )
            transformed_covariance = _transform_covariance_matrix(
                scaled_covariance, transform
            )
            model_basis_covariance = tuple(
                tuple(
                    0.5 * transformed_covariance[row][column]
                    + 0.5 * transformed_covariance[column][row]
                    for column in range(len(transformed_covariance))
                )
                for row in range(len(transformed_covariance))
            )
        except (OverflowError, ValueError):
            model_basis_covariance = ()
        if (
            not model_basis_covariance
            or not all(
                math.isfinite(value) for row in model_basis_covariance for value in row
            )
            or not all(
                model_basis_covariance[index][index] >= 0.0
                for index in range(len(model_basis_covariance))
            )
        ):
            covariance_unavailable_reason = "covariance_not_finitely_representable"
        else:
            parameter_covariance = FitParameterCovariance(
                parameter_names=tuple(
                    f"a{power}" for power in range(len(scaled_coefficients))
                ),
                covariance_matrix=model_basis_covariance,
                estimation_method=covariance_method,
                parameterization=(
                    "resistance_power_series_at_model_reference_temperature"
                ),
            )

    evidence = PolynomialFitEvidence(
        observations=observation_tuple,
        residuals_ohms=residuals,
        degree=degree,
        observation_count=len(observation_tuple),
        fitted_parameter_count=degree + 1,
        residual_degrees_of_freedom=residual_degrees_of_freedom,
        minimum_temperature_c=minimum_c,
        maximum_temperature_c=maximum_c,
        rms_residual_ohms=rms_residual_ohms,
        max_absolute_residual_ohms=max_absolute_residual_ohms,
        weighting_method=weighting_method,
        effective_weights=effective_weights,
        weighted_sum_squared_residual=weighted_sum_squared_residual,
        weighted_rms_residual_ohms=weighted_rms_residual_ohms,
        parameter_covariance=parameter_covariance,
        parameter_covariance_unavailable_reason=covariance_unavailable_reason,
        scaled_system_condition_number=condition_number,
        scaled_system_condition_limit=_MAX_SCALED_SYSTEM_CONDITION_NUMBER,
        conditioning_method=_CONDITIONING_METHOD,
        solver=_SOLVER,
        scaled_temperature_center_c=scaled_center_c,
        scaled_temperature_half_range_c=scaled_half_range_c,
    )
    return PolynomialFitResult(model=model, evidence=evidence)
