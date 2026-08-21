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
from .models import CallendarVanDusenRTDModel, IEC60751RTDModel, PolynomialRTDModel

__all__ = [
    "CalibrationObservation",
    "CalibrationProvenance",
    "CalibrationTemperatureUncertaintyHandling",
    "CallendarVanDusenFitEvidence",
    "CallendarVanDusenFitParameter",
    "CallendarVanDusenFitResult",
    "IEC60751R0FitEvidence",
    "IEC60751R0FitResult",
    "FitParameterCovariance",
    "PolynomialFitEvidence",
    "PolynomialFitResult",
    "fit_callendar_van_dusen",
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
    "callendar_van_dusen_parameters",
    "resistance_power_series_at_model_reference_temperature",
]
CallendarVanDusenFitParameter = Literal["r0_ohms", "a", "b", "c"]
CalibrationTemperatureUncertaintyHandling = Literal["reject", "retain_not_used"]
_TemperatureUncertaintyEvidenceTreatment = Literal["not_supplied", "retained_not_used"]
_CVD_PARAMETER_ORDER: tuple[CallendarVanDusenFitParameter, ...] = (
    "r0_ohms",
    "a",
    "b",
    "c",
)
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


def _normalized_optional_text(value: str | None, *, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string or None")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


@dataclass(frozen=True, slots=True)
class CalibrationProvenance:
    """Application-neutral provenance retained with calibration fit evidence.

    These fields describe the calibration record and reference context. They are
    deliberately non-behavioral: they do not alter fitting, are not copied into
    the fitted numerical model, and are not automatically serialized into a
    portable model definition.
    """

    certificate_identifier: str | None = None
    calibration_date: str | None = None
    laboratory: str | None = None
    reference_standard: str | None = None
    source_document: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        for field_name, display_name in (
            ("certificate_identifier", "Certificate identifier"),
            ("calibration_date", "Calibration date"),
            ("laboratory", "Laboratory"),
            ("reference_standard", "Reference standard"),
            ("source_document", "Source document"),
            ("notes", "Notes"),
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_optional_text(
                    getattr(self, field_name),
                    name=display_name,
                ),
            )


@dataclass(frozen=True, slots=True)
class CalibrationObservation:
    """One measured calibration point used by a fitting operation.

    Exactly one weighting convention may be used for a weighted fit. ``weight`` is
    a caller-supplied positive relative least-squares weight.
    ``standard_uncertainty_ohms`` is a positive standard uncertainty in resistance;
    it is converted to an inverse-variance weight ``1 / u**2``.
    ``standard_uncertainty_temperature_c`` records standard uncertainty in the
    calibration/reference temperature coordinate. Current fitters do not use that
    value as a resistance weight or perform errors-in-variables regression.
    """

    temperature_c: float
    resistance_ohms: float
    weight: float | None = None
    standard_uncertainty_ohms: float | None = None
    standard_uncertainty_temperature_c: float | None = None

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
        temperature_uncertainty = (
            None
            if self.standard_uncertainty_temperature_c is None
            else _as_float(
                self.standard_uncertainty_temperature_c,
                name="Temperature standard uncertainty",
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
        if temperature_uncertainty is not None:
            if not math.isfinite(temperature_uncertainty):
                raise ValueError("Temperature standard uncertainty must be finite")
            if temperature_uncertainty <= 0.0:
                raise ValueError(
                    "Temperature standard uncertainty must be greater than zero"
                )
        if weight is not None and uncertainty is not None:
            raise ValueError("Specify either weight or standard uncertainty, not both")

        object.__setattr__(self, "temperature_c", temperature_c)
        object.__setattr__(self, "resistance_ohms", resistance_ohms)
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "standard_uncertainty_ohms", uncertainty)
        object.__setattr__(
            self,
            "standard_uncertainty_temperature_c",
            temperature_uncertainty,
        )


def _temperature_uncertainty_treatment(
    observations: tuple[CalibrationObservation, ...],
    handling: CalibrationTemperatureUncertaintyHandling,
) -> _TemperatureUncertaintyEvidenceTreatment:
    if handling not in ("reject", "retain_not_used"):
        raise ValueError(
            "Temperature uncertainty handling must be 'reject' or 'retain_not_used'"
        )
    has_temperature_uncertainty = any(
        observation.standard_uncertainty_temperature_c is not None
        for observation in observations
    )
    if not has_temperature_uncertainty:
        return "not_supplied"
    if handling == "reject":
        raise RTDFitError(
            "Calibration observations include temperature standard uncertainty, "
            "but current least-squares fitting treats temperature as exact. Use "
            "temperature_uncertainty_handling='retain_not_used' only when you "
            "intend to retain that uncertainty as evidence without including it "
            "in the fit."
        )
    return "retained_not_used"


def _validate_calibration_provenance(
    provenance: CalibrationProvenance | None,
) -> CalibrationProvenance | None:
    if provenance is not None and not isinstance(provenance, CalibrationProvenance):
        raise TypeError("Provenance must be CalibrationProvenance or None")
    return provenance


@dataclass(frozen=True, slots=True)
class FitParameterCovariance:
    """Covariance matrix for parameters estimated by one fitting operation.

    ``covariance_matrix`` follows ``parameter_names`` in both dimensions. For
    polynomial fits the parameterization is the unnormalized resistance power
    series at the returned model's reference temperature,
    ``R(T) = a0 + a1*x + ...``. This is intentionally fit evidence rather than
    part of the deployable model definition.

    ``parameter_transformation`` records an additional basis transformation when
    covariance is not exposed in the exact linear fit basis.
    ``standard_uncertainties`` and ``correlation_matrix`` are derived diagnostics
    in the same parameter order. ``residual_variance_scaled_least_squares`` means
    the unknown common residual variance scale was estimated from the fit residuals
    and residual degrees of freedom. ``resistance_standard_uncertainties`` means
    absolute, independent resistance standard uncertainties supplied on every
    observation defined the covariance directly; residual scatter does not rescale
    that covariance.
    """

    parameter_names: tuple[str, ...]
    covariance_matrix: tuple[tuple[float, ...], ...]
    estimation_method: _CovarianceEstimationMethod
    parameterization: _CovarianceParameterization
    parameter_transformation: str | None = None

    @property
    def standard_uncertainties(self) -> tuple[float, ...]:
        """Return standard uncertainties derived from covariance diagonal terms."""
        return tuple(
            math.sqrt(self.covariance_matrix[index][index])
            for index in range(len(self.parameter_names))
        )

    @property
    def correlation_matrix(self) -> tuple[tuple[float | None, ...], ...]:
        """Return parameter correlations, using ``None`` when undefined.

        A correlation coefficient is undefined when either parameter has zero
        variance. Those entries are therefore reported as ``None`` rather than
        assigning an arbitrary numerical correlation.
        """
        standard_uncertainties = self.standard_uncertainties
        return tuple(
            tuple(
                (
                    self.covariance_matrix[row][column]
                    / (standard_uncertainties[row] * standard_uncertainties[column])
                    if standard_uncertainties[row] > 0.0
                    and standard_uncertainties[column] > 0.0
                    else None
                )
                for column in range(len(self.parameter_names))
            )
            for row in range(len(self.parameter_names))
        )


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
    standard uncertainties can define covariance even at zero residual DOF. When
    those absolute uncertainties are supplied, chi-square and reduced-chi-square
    residual-consistency diagnostics are retained as well. Calibration/reference
    temperature uncertainty treatment and optional application-neutral calibration
    provenance are retained separately from the numerical model.
    """

    observations: tuple[CalibrationObservation, ...]
    temperature_uncertainty_treatment: _TemperatureUncertaintyEvidenceTreatment
    provenance: CalibrationProvenance | None
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
    chi_squared: float | None
    reduced_chi_squared: float | None
    parameter_covariance: FitParameterCovariance | None
    parameter_covariance_unavailable_reason: _CovarianceUnavailableReason | None
    solver: str


@dataclass(frozen=True, slots=True)
class IEC60751R0FitResult:
    """Fitted IEC 60751 model and the evidence supporting the R0 estimate."""

    model: IEC60751RTDModel
    evidence: IEC60751R0FitEvidence


@dataclass(frozen=True, slots=True)
class CallendarVanDusenFitEvidence:
    """Immutable observations and diagnostics supporting a custom CVD fit.

    ``fitted_parameter_names`` identifies which of ``R0``, ``A``, ``B``, and
    ``C`` were estimated rather than supplied as fixed inputs. The least-squares
    system uses an algebraically linearized CVD parameterization with explicit
    column scaling; covariance is transformed back to the public fitted parameter
    basis before it is exposed. The condition diagnostic therefore reflects the
    scaled estimation problem used to decide whether the requested parameters are
    identifiable from the supplied observations. Absolute-uncertainty fits also
    retain chi-square/reduced-chi-square residual-consistency diagnostics.
    Calibration/reference temperature uncertainty treatment and optional
    application-neutral calibration provenance remain evidence only.
    """

    observations: tuple[CalibrationObservation, ...]
    temperature_uncertainty_treatment: _TemperatureUncertaintyEvidenceTreatment
    provenance: CalibrationProvenance | None
    residuals_ohms: tuple[float, ...]
    fitted_parameter_names: tuple[CallendarVanDusenFitParameter, ...]
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
    chi_squared: float | None
    reduced_chi_squared: float | None
    parameter_covariance: FitParameterCovariance | None
    parameter_covariance_unavailable_reason: _CovarianceUnavailableReason | None
    scaled_system_condition_number: float
    scaled_system_condition_limit: float
    conditioning_method: str
    solver: str
    linearized_parameter_names: tuple[str, ...]
    design_column_scales: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class CallendarVanDusenFitResult:
    """Validated custom CVD model and the evidence supporting the fit."""

    model: CallendarVanDusenRTDModel
    evidence: CallendarVanDusenFitEvidence


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
    uncertainties define covariance directly. Absolute-uncertainty fits also
    retain chi-square and, when residual degrees of freedom are positive,
    reduced-chi-square residual-consistency diagnostics. Calibration/reference
    temperature uncertainty treatment and optional application-neutral calibration
    provenance remain evidence only.
    """

    observations: tuple[CalibrationObservation, ...]
    temperature_uncertainty_treatment: _TemperatureUncertaintyEvidenceTreatment
    provenance: CalibrationProvenance | None
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
    chi_squared: float | None
    reduced_chi_squared: float | None
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
        raise RTDFitError("Least-squares fit produced non-finite coefficients")
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


def _chi_squared_diagnostics(
    observations: tuple[CalibrationObservation, ...],
    residuals_ohms: tuple[float, ...],
    *,
    weighting_method: _WeightingMethod,
    residual_degrees_of_freedom: int,
) -> tuple[float | None, float | None]:
    """Return chi-square diagnostics when absolute resistance uncertainties exist."""
    if weighting_method != "normalized_inverse_variance_from_standard_uncertainty":
        return (None, None)

    uncertainties = tuple(
        observation.standard_uncertainty_ohms for observation in observations
    )
    assert all(uncertainty is not None for uncertainty in uncertainties)
    chi_squared = math.fsum(
        (residual / uncertainty) ** 2
        for residual, uncertainty in zip(residuals_ohms, uncertainties, strict=True)
        if uncertainty is not None
    )
    reduced = (
        chi_squared / residual_degrees_of_freedom
        if residual_degrees_of_freedom > 0
        else None
    )
    return (chi_squared, reduced)


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


def _validate_cvd_fit_parameters(
    fit_parameters: Iterable[CallendarVanDusenFitParameter],
) -> tuple[CallendarVanDusenFitParameter, ...]:
    if isinstance(fit_parameters, (str, bytes)):
        raise TypeError("fit_parameters must be an iterable of parameter names")
    requested = tuple(fit_parameters)
    if not requested:
        raise ValueError("At least one Callendar-Van Dusen parameter must be fitted")
    if not all(isinstance(parameter, str) for parameter in requested):
        raise TypeError("Callendar-Van Dusen fit parameter names must be strings")
    unknown = [
        parameter for parameter in requested if parameter not in _CVD_PARAMETER_ORDER
    ]
    if unknown:
        raise ValueError(f"Unsupported Callendar-Van Dusen fit parameter: {unknown[0]}")
    if len(set(requested)) != len(requested):
        raise ValueError("Callendar-Van Dusen fit parameter names must be unique")
    requested_set = set(requested)
    return tuple(
        parameter for parameter in _CVD_PARAMETER_ORDER if parameter in requested_set
    )


def _cvd_c_basis(temperature_c: float) -> float:
    if temperature_c >= 0.0:
        return 0.0
    return (temperature_c - 100.0) * temperature_c**3


def _cvd_shape_basis(
    parameter: CallendarVanDusenFitParameter,
    temperature_c: float,
) -> float:
    if parameter == "a":
        return temperature_c
    if parameter == "b":
        return temperature_c * temperature_c
    if parameter == "c":
        return _cvd_c_basis(temperature_c)
    raise ValueError(f"No shape basis exists for {parameter}")


def _cvd_resistance_unchecked(
    temperature_c: float,
    *,
    r0_ohms: float,
    a: float,
    b: float,
    c: float | None,
) -> float:
    ratio = 1.0 + a * temperature_c + b * temperature_c**2
    if temperature_c < 0.0:
        ratio += (0.0 if c is None else c) * _cvd_c_basis(temperature_c)
    return r0_ohms * ratio


def _column_scaled_least_squares(
    raw_matrix: list[list[float]],
    vector: list[float],
    *,
    effective_weights: tuple[float, ...] | None,
) -> tuple[
    tuple[float, ...],
    float,
    tuple[tuple[float, ...], ...],
    tuple[float, ...],
]:
    column_count = len(raw_matrix[0])
    column_scales = tuple(
        max(abs(row[column]) for row in raw_matrix) for column in range(column_count)
    )
    if not all(math.isfinite(scale) and scale > 0.0 for scale in column_scales):
        raise RTDFitError(
            "Requested Callendar-Van Dusen parameters are not identifiable from "
            "the supplied calibration temperatures"
        )

    matrix: list[list[float]] = []
    weighted_vector: list[float] = []
    for index, row in enumerate(raw_matrix):
        weight = 1.0 if effective_weights is None else effective_weights[index]
        row_scale = math.sqrt(weight)
        matrix.append(
            [
                row[column] / column_scales[column] * row_scale
                for column in range(column_count)
            ]
        )
        weighted_vector.append(vector[index] * row_scale)

    scaled_coefficients, condition_number, upper = _householder_least_squares(
        matrix,
        weighted_vector,
    )
    coefficients = tuple(
        coefficient / scale
        for coefficient, scale in zip(scaled_coefficients, column_scales, strict=True)
    )
    return coefficients, condition_number, upper, column_scales


def _cvd_covariance_transform(
    fitted_parameter_names: tuple[CallendarVanDusenFitParameter, ...],
    *,
    linearized_parameter_names: tuple[str, ...],
    r0_ohms: float,
    fitted_values: dict[CallendarVanDusenFitParameter, float],
) -> tuple[tuple[float, ...], ...]:
    size = len(fitted_parameter_names)
    if "r0_ohms" not in fitted_parameter_names:
        return tuple(
            tuple(1.0 if row == column else 0.0 for column in range(size))
            for row in range(size)
        )

    r0_column = linearized_parameter_names.index("r0_ohms")
    transform: list[list[float]] = []
    for parameter in fitted_parameter_names:
        row = [0.0] * size
        if parameter == "r0_ohms":
            row[r0_column] = 1.0
        else:
            linearized_name = f"r0_times_{parameter}"
            parameter_column = linearized_parameter_names.index(linearized_name)
            row[r0_column] = -fitted_values[parameter] / r0_ohms
            row[parameter_column] = 1.0 / r0_ohms
        transform.append(row)
    return tuple(tuple(row) for row in transform)


def fit_callendar_van_dusen(
    observations: Iterable[CalibrationObservation],
    *,
    fit_parameters: Iterable[CallendarVanDusenFitParameter],
    r0_ohms: float | None = None,
    a: float | None = None,
    b: float | None = None,
    c: float | None = None,
    minimum_temperature_c: float | None = None,
    maximum_temperature_c: float | None = None,
    name: str = "Fitted Callendar-Van Dusen RTD",
    coefficient_source: str | None = None,
    temperature_uncertainty_handling: CalibrationTemperatureUncertaintyHandling = (
        "reject"
    ),
    provenance: CalibrationProvenance | None = None,
) -> CallendarVanDusenFitResult:
    """Fit selected Callendar-Van Dusen parameters to calibration observations.

    The requested parameters are estimated only when the supplied temperatures
    identify the corresponding CVD basis functions with acceptable conditioning.
    Parameters not listed in ``fit_parameters`` must be supplied as fixed values,
    except ``C`` may be omitted for a wholly non-negative declared model range.

    The modern CVD equation is algebraically linearized for least squares. When
    ``R0`` is fitted, shape coefficients are estimated internally as ``R0*A``,
    ``R0*B``, and ``R0*C`` and transformed back to the public ``R0, A, B, C``
    basis. The coefficient transformation is exact; when ``R0`` and shape
    coefficients are fitted jointly, covariance in the public ratio parameters is
    obtained by first-order Jacobian propagation from the exact linearized-fit
    covariance. This avoids nonlinear optimization while retaining the exact CVD
    model form and making the covariance approximation explicit.

    If any shape coefficient (``A``, ``B``, or ``C``) is fitted, the declared model
    range may be narrowed but not extended beyond the calibration-observation span.
    If only ``R0`` is fitted while all shape coefficients are fixed, an explicitly
    supplied applicability range may be independent of the observation span, just
    as for characterized-standard ``R0`` fitting.

    Temperature remains the independent variable. ``standard_uncertainty_ohms``
    therefore describes resistance uncertainty only. Calibration/reference
    temperature uncertainty is rejected by default. The explicit
    ``retain_not_used`` handling mode retains supplied temperature standard
    uncertainties in the fit evidence while still treating their coordinate values
    as exact; it does not convert them into resistance weights or perform
    errors-in-variables regression.
    """

    # Source: Pearce et al. (2022), Appendix 1, for the modern CVD form
    # R(t) = R0[1 + A*t + B*t^2 + C*(t-100)*t^3] below 0 °C, with C=0 above 0 °C.
    fitted_parameter_names = _validate_cvd_fit_parameters(fit_parameters)
    fitted_parameter_set = set(fitted_parameter_names)

    observation_tuple = tuple(observations)
    if not observation_tuple:
        raise RTDFitError("At least one calibration observation is required")
    if not all(
        isinstance(observation, CalibrationObservation)
        for observation in observation_tuple
    ):
        raise TypeError("Observations must be CalibrationObservation values")

    temperature_uncertainty_treatment = _temperature_uncertainty_treatment(
        observation_tuple,
        temperature_uncertainty_handling,
    )
    provenance = _validate_calibration_provenance(provenance)

    distinct_temperatures = {
        observation.temperature_c for observation in observation_tuple
    }
    if len(distinct_temperatures) < len(fitted_parameter_names):
        raise RTDFitError(
            f"Fitting {len(fitted_parameter_names)} Callendar-Van Dusen parameters "
            f"requires at least {len(fitted_parameter_names)} distinct calibration "
            "temperatures"
        )
    if "c" in fitted_parameter_set and not any(
        temperature < 0.0 for temperature in distinct_temperatures
    ):
        raise RTDFitError(
            "Fitting C requires at least one negative-temperature calibration "
            "observation"
        )

    observed_minimum_c = min(distinct_temperatures)
    observed_maximum_c = max(distinct_temperatures)
    explicit_range = (
        minimum_temperature_c is not None or maximum_temperature_c is not None
    )
    if explicit_range and (
        minimum_temperature_c is None or maximum_temperature_c is None
    ):
        raise ValueError(
            "Minimum and maximum fitted temperatures must be supplied together"
        )
    if explicit_range:
        assert minimum_temperature_c is not None
        assert maximum_temperature_c is not None
        minimum_c = _as_float(minimum_temperature_c, name="Minimum fitted temperature")
        maximum_c = _as_float(maximum_temperature_c, name="Maximum fitted temperature")
    else:
        if observed_minimum_c == observed_maximum_c:
            raise RTDFitError(
                "A single calibration temperature requires an explicit model range"
            )
        minimum_c = observed_minimum_c
        maximum_c = observed_maximum_c

    if not math.isfinite(minimum_c):
        raise ValueError("Minimum fitted temperature must be finite")
    if not math.isfinite(maximum_c):
        raise ValueError("Maximum fitted temperature must be finite")
    if minimum_c >= maximum_c:
        raise ValueError(
            "Minimum fitted temperature must be below maximum fitted temperature"
        )

    shape_parameters_fitted = any(
        parameter in fitted_parameter_set for parameter in ("a", "b", "c")
    )
    if shape_parameters_fitted and (
        minimum_c < observed_minimum_c or maximum_c > observed_maximum_c
    ):
        raise RTDFitError(
            "A CVD fit that estimates A, B, or C may not extend the declared model "
            "range beyond the observed calibration span"
        )

    supplied_values: dict[CallendarVanDusenFitParameter, float | None] = {
        "r0_ohms": r0_ohms,
        "a": a,
        "b": b,
        "c": c,
    }
    fixed_values: dict[CallendarVanDusenFitParameter, float | None] = {}
    for parameter in _CVD_PARAMETER_ORDER:
        supplied = supplied_values[parameter]
        if parameter in fitted_parameter_set:
            if supplied is not None:
                raise ValueError(
                    f"{parameter} cannot be supplied when it is listed in "
                    "fit_parameters"
                )
            fixed_values[parameter] = None
            continue
        if parameter == "c" and supplied is None and minimum_c >= 0.0:
            fixed_values[parameter] = None
            continue
        if supplied is None:
            raise ValueError(
                f"A fixed value for {parameter} is required when it is not fitted"
            )
        value = _as_float(supplied, name=parameter)
        if not math.isfinite(value):
            raise ValueError(f"Fixed {parameter} must be finite")
        if parameter == "r0_ohms" and value <= 0.0:
            raise ValueError("Fixed r0_ohms must be greater than zero")
        fixed_values[parameter] = value

    weighting_method, effective_weights = _effective_weights(observation_tuple)

    raw_matrix: list[list[float]] = []
    vector: list[float] = []
    linearized_parameter_names: list[str] = []
    if "r0_ohms" in fitted_parameter_set:
        linearized_parameter_names.append("r0_ohms")
        linearized_parameter_names.extend(
            f"r0_times_{parameter}"
            for parameter in fitted_parameter_names
            if parameter != "r0_ohms"
        )
        for observation in observation_tuple:
            temperature = observation.temperature_c
            base_ratio = 1.0
            for parameter in ("a", "b", "c"):
                if parameter in fitted_parameter_set:
                    continue
                fixed = fixed_values[parameter]
                if fixed is not None:
                    base_ratio += fixed * _cvd_shape_basis(parameter, temperature)
            row = [base_ratio]
            row.extend(
                _cvd_shape_basis(parameter, temperature)
                for parameter in fitted_parameter_names
                if parameter != "r0_ohms"
            )
            raw_matrix.append(row)
            vector.append(observation.resistance_ohms)
    else:
        fixed_r0 = fixed_values["r0_ohms"]
        assert fixed_r0 is not None
        linearized_parameter_names.extend(fitted_parameter_names)
        for observation in observation_tuple:
            temperature = observation.temperature_c
            fixed_ratio = 1.0
            for parameter in ("a", "b", "c"):
                if parameter in fitted_parameter_set:
                    continue
                fixed = fixed_values[parameter]
                if fixed is not None:
                    fixed_ratio += fixed * _cvd_shape_basis(parameter, temperature)
            raw_matrix.append(
                [
                    fixed_r0 * _cvd_shape_basis(parameter, temperature)
                    for parameter in fitted_parameter_names
                ]
            )
            vector.append(observation.resistance_ohms - fixed_r0 * fixed_ratio)

    try:
        linearized_coefficients, condition_number, upper, column_scales = (
            _column_scaled_least_squares(
                raw_matrix,
                vector,
                effective_weights=effective_weights,
            )
        )
    except RTDFitError as error:
        if "ill-conditioned" in str(error) or "rank deficient" in str(error):
            raise RTDFitError(
                "Requested Callendar-Van Dusen parameters are not identifiable "
                f"from these calibration observations: {error}"
            ) from error
        raise

    fitted_values: dict[CallendarVanDusenFitParameter, float] = {}
    if "r0_ohms" in fitted_parameter_set:
        fitted_r0 = linearized_coefficients[0]
        if not math.isfinite(fitted_r0) or fitted_r0 <= 0.0:
            raise RTDFitError("Fitted R0 must be finite and positive")
        fitted_values["r0_ohms"] = fitted_r0
        coefficient_index = 1
        for parameter in fitted_parameter_names:
            if parameter == "r0_ohms":
                continue
            value = linearized_coefficients[coefficient_index] / fitted_r0
            coefficient_index += 1
            if not math.isfinite(value):
                raise RTDFitError(f"Fitted {parameter} must be finite")
            fitted_values[parameter] = value
    else:
        for parameter, value in zip(
            fitted_parameter_names, linearized_coefficients, strict=True
        ):
            if not math.isfinite(value):
                raise RTDFitError(f"Fitted {parameter} must be finite")
            fitted_values[parameter] = value

    final_values: dict[CallendarVanDusenFitParameter, float | None] = {}
    for parameter in _CVD_PARAMETER_ORDER:
        final_values[parameter] = (
            fitted_values[parameter]
            if parameter in fitted_parameter_set
            else fixed_values[parameter]
        )
    final_r0 = final_values["r0_ohms"]
    final_a = final_values["a"]
    final_b = final_values["b"]
    assert final_r0 is not None and final_a is not None and final_b is not None

    try:
        model = CallendarVanDusenRTDModel(
            r0_ohms=final_r0,
            a=final_a,
            b=final_b,
            c=final_values["c"],
            minimum_temperature_c=minimum_c,
            maximum_temperature_c=maximum_c,
            name=name,
            coefficient_source=coefficient_source,
        )
    except InvalidRTDModelError as error:
        raise RTDFitError(
            "Fitted Callendar-Van Dusen coefficients do not define a valid RTD "
            f"model: {error}"
        ) from error

    residuals = tuple(
        observation.resistance_ohms
        - _cvd_resistance_unchecked(
            observation.temperature_c,
            r0_ohms=model.r0_ohms,
            a=model.a,
            b=model.b,
            c=model.c,
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
        weighted_rms_residual_ohms = math.sqrt(
            weighted_sum_squared_residual / math.fsum(effective_weights)
        )

    residual_degrees_of_freedom = len(observation_tuple) - len(fitted_parameter_names)
    chi_squared, reduced_chi_squared = _chi_squared_diagnostics(
        observation_tuple,
        residuals,
        weighting_method=weighting_method,
        residual_degrees_of_freedom=residual_degrees_of_freedom,
    )
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
            unscale_transform = tuple(
                tuple(
                    1.0 / column_scales[row] if row == column else 0.0
                    for column in range(len(column_scales))
                )
                for row in range(len(column_scales))
            )
            linearized_covariance = _transform_covariance_matrix(
                scaled_covariance, unscale_transform
            )
            parameter_transform = _cvd_covariance_transform(
                fitted_parameter_names,
                linearized_parameter_names=tuple(linearized_parameter_names),
                r0_ohms=model.r0_ohms,
                fitted_values=fitted_values,
            )
            fitted_covariance = _transform_covariance_matrix(
                linearized_covariance, parameter_transform
            )
            fitted_covariance = tuple(
                tuple(
                    0.5 * fitted_covariance[row][column]
                    + 0.5 * fitted_covariance[column][row]
                    for column in range(len(fitted_covariance))
                )
                for row in range(len(fitted_covariance))
            )
        except (OverflowError, ValueError):
            fitted_covariance = ()
        if (
            not fitted_covariance
            or not all(
                math.isfinite(value) for row in fitted_covariance for value in row
            )
            or not all(
                fitted_covariance[index][index] >= 0.0
                for index in range(len(fitted_covariance))
            )
        ):
            covariance_unavailable_reason = "covariance_not_finitely_representable"
        else:
            parameter_covariance = FitParameterCovariance(
                parameter_names=fitted_parameter_names,
                covariance_matrix=fitted_covariance,
                estimation_method=covariance_method,
                parameterization="callendar_van_dusen_parameters",
                parameter_transformation=(
                    "first_order_ratio_transform_from_linearized_cvd"
                    if "r0_ohms" in fitted_parameter_set
                    and any(
                        parameter != "r0_ohms" for parameter in fitted_parameter_names
                    )
                    else None
                ),
            )

    evidence = CallendarVanDusenFitEvidence(
        observations=observation_tuple,
        temperature_uncertainty_treatment=temperature_uncertainty_treatment,
        provenance=provenance,
        residuals_ohms=residuals,
        fitted_parameter_names=fitted_parameter_names,
        observation_count=len(observation_tuple),
        fitted_parameter_count=len(fitted_parameter_names),
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
        chi_squared=chi_squared,
        reduced_chi_squared=reduced_chi_squared,
        parameter_covariance=parameter_covariance,
        parameter_covariance_unavailable_reason=covariance_unavailable_reason,
        scaled_system_condition_number=condition_number,
        scaled_system_condition_limit=_MAX_SCALED_SYSTEM_CONDITION_NUMBER,
        conditioning_method="infinity_norm_of_householder_r_after_column_scaling",
        solver=_SOLVER,
        linearized_parameter_names=tuple(linearized_parameter_names),
        design_column_scales=column_scales,
    )
    return CallendarVanDusenFitResult(model=model, evidence=evidence)


def fit_iec60751_r0(
    observations: Iterable[CalibrationObservation],
    *,
    minimum_temperature_c: float | None = None,
    maximum_temperature_c: float | None = None,
    name: str = "Fitted IEC 60751 RTD",
    temperature_uncertainty_handling: CalibrationTemperatureUncertaintyHandling = (
        "reject"
    ),
    provenance: CalibrationProvenance | None = None,
) -> IEC60751R0FitResult:
    """Fit only ``R0`` while retaining the IEC 60751 PT-385 characteristic.

    For each observation, the normalized IEC characteristic supplies
    ``rho(T) = R(T) / R0`` and the fitter solves the one-parameter linear
    least-squares problem ``R_observed = R0 * rho(T)``. Relative weights and
    resistance standard uncertainties use the same conventions as
    :func:`fit_polynomial`. Temperature is treated as the independent variable.
    Calibration/reference temperature uncertainty is rejected by default; the
    explicit ``retain_not_used`` handling mode preserves it as evidence while
    leaving it outside the least-squares objective.

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

    temperature_uncertainty_treatment = _temperature_uncertainty_treatment(
        observation_tuple,
        temperature_uncertainty_handling,
    )
    provenance = _validate_calibration_provenance(provenance)

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
    chi_squared, reduced_chi_squared = _chi_squared_diagnostics(
        observation_tuple,
        residuals,
        weighting_method=weighting_method,
        residual_degrees_of_freedom=residual_degrees_of_freedom,
    )
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
        temperature_uncertainty_treatment=temperature_uncertainty_treatment,
        provenance=provenance,
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
        chi_squared=chi_squared,
        reduced_chi_squared=reduced_chi_squared,
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
    temperature_uncertainty_handling: CalibrationTemperatureUncertaintyHandling = (
        "reject"
    ),
    provenance: CalibrationProvenance | None = None,
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
    independent variable. Calibration/reference temperature uncertainty is rejected
    by default; the explicit ``retain_not_used`` handling mode preserves it as
    evidence while leaving it outside the least-squares objective. The fitter does
    not implement errors-in-variables regression.

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

    temperature_uncertainty_treatment = _temperature_uncertainty_treatment(
        observation_tuple,
        temperature_uncertainty_handling,
    )
    provenance = _validate_calibration_provenance(provenance)

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
    chi_squared, reduced_chi_squared = _chi_squared_diagnostics(
        observation_tuple,
        residuals,
        weighting_method=weighting_method,
        residual_degrees_of_freedom=residual_degrees_of_freedom,
    )
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
        temperature_uncertainty_treatment=temperature_uncertainty_treatment,
        provenance=provenance,
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
        chi_squared=chi_squared,
        reduced_chi_squared=reduced_chi_squared,
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
