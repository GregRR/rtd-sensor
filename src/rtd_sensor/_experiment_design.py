# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Private numerical foundations for calibration experiment design.

The public experiment-planning API is intentionally not introduced in this slice.
These helpers establish prospective polynomial information/covariance using the
same scaled weighted Householder system as :mod:`rtd_sensor.fitting`, while
expressing every covariance in one caller-specified planning reference basis. They
also construct the deterministic sensitivity-weighted moment matrix used by the
reviewed 0.9 I-optimal criterion.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import Literal

from . import models as _public_models
from ._curves import (
    CallendarVanDusenCurve as _CallendarVanDusenCurve,
)
from ._curves import (
    PiecewisePolynomialRTDCurve as _PiecewisePolynomialRTDCurve,
)
from ._curves import (
    PolynomialRTDCurve as _PolynomialRTDCurve,
)
from ._curves import (
    _polynomial_derivative,
    _polynomial_roots_in_interval,
    _polynomial_value,
    _trim_polynomial,
)
from ._models import RTDModel as _InternalRTDModel
from ._protocols import RTDUncertaintyModel
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
from .uncertainty import _covariance_quadratic_form


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


# Standard 15-point Gauss / 31-point Kronrod pair used by QUADPACK DQK31.
# The odd-index Kronrod abscissae are the seven nonzero Gauss abscissae;
# the center is shared by both rules. See Piessens et al. (1983), QUADPACK.
_GK31_ABSCISSAE = (
    0.998002298693397060285172840152271,
    0.987992518020485428489565718586613,
    0.967739075679139134257347978784337,
    0.937273392400705904307758947710209,
    0.897264532344081900882509656454496,
    0.848206583410427216200648320774217,
    0.790418501442465932967649294817947,
    0.724417731360170047416186054613938,
    0.650996741297416970533735895313275,
    0.570972172608538847537226737253911,
    0.485081863640239680693655740232351,
    0.394151347077563369897207370981045,
    0.299180007153168812166780024266389,
    0.201194093997434522300628303394596,
    0.101142066918717499027074231447392,
    0.0,
)
_GK31_GAUSS_WEIGHTS = (
    0.030753241996117268354628393577204,
    0.070366047488108124709267416450667,
    0.107159220467171935011869546685869,
    0.139570677926154314447804794511028,
    0.166269205816993933553200860481209,
    0.186161000015562211026800561866423,
    0.198431485327111576456118326443839,
    0.202578241925561272880620199967519,
)
_GK31_KRONROD_WEIGHTS = (
    0.005377479872923348987792051430128,
    0.015007947329316122538374763075807,
    0.025460847326715320186874001019653,
    0.035346360791375846222037948478360,
    0.044589751324764876608227299373280,
    0.053481524690928087265343147239430,
    0.062009567800670640285139230960803,
    0.069854121318728258709520077099147,
    0.076849680757720378894432777482659,
    0.083080502823133021038289247286104,
    0.088564443056211770647275443693774,
    0.093126598170825321225486872747346,
    0.096642726983623678505179907627589,
    0.099173598721791959332393173484603,
    0.100769845523875595044946662617570,
    0.101330007014791549017374792767493,
)
_MOMENT_INTEGRATION_METHOD = "adaptive_gauss_kronrod_15_31"
# Numerical integration accuracy only. It is never a scientific-equivalence,
# design-ranking, or tie threshold.
_MOMENT_RELATIVE_ERROR_TARGET = 1.0e-12
# Implementation resource guard, not a scientific threshold. This is deliberately
# private and may be benchmark-adjusted without changing the meaning of a result.
_MAX_MOMENT_INTERVAL_EVALUATIONS = 4096


@dataclass(frozen=True, slots=True)
class _OperatingPriorityInterval:
    """One explicit constant relative-importance density over temperature."""

    minimum_temperature_c: float
    maximum_temperature_c: float
    relative_weight_density: float


@dataclass(frozen=True, slots=True)
class _SensitivityWeightedMomentMatrix:
    """Frozen numerical evidence for the sensitivity-weighted I-optimal moment."""

    moment_matrix: tuple[tuple[float, ...], ...]
    normalized_estimated_error_matrix: tuple[tuple[float, ...], ...]
    parameter_names: tuple[str, ...]
    reference_temperature_c: float
    priority_normalization_c: float
    structural_partition_c: tuple[float, ...]
    accepted_subinterval_count: int
    sensitivity_evaluation_count: int
    adaptive_subdivision_occurred: bool
    integration_method: str
    relative_error_target: float


@dataclass(frozen=True, slots=True)
class _QuadratureEstimate:
    values: tuple[float, ...]
    absolute_integrals: tuple[float, ...]
    errors: tuple[float, ...]
    evaluation_count: int


def _validated_priority_partition(
    priority_intervals: tuple[_OperatingPriorityInterval, ...],
    *,
    fitted_minimum_temperature_c: float,
    fitted_maximum_temperature_c: float,
) -> tuple[_OperatingPriorityInterval, ...]:
    if not priority_intervals:
        raise RTDExperimentDesignError(
            "At least one operating-priority interval is required"
        )

    validated: list[_OperatingPriorityInterval] = []
    for interval in priority_intervals:
        if not isinstance(interval, _OperatingPriorityInterval):
            raise TypeError(
                "Operating priorities must be _OperatingPriorityInterval values"
            )
        lower = _as_planning_float(
            interval.minimum_temperature_c,
            name="Operating-priority minimum temperature",
        )
        upper = _as_planning_float(
            interval.maximum_temperature_c,
            name="Operating-priority maximum temperature",
        )
        weight = _as_planning_float(
            interval.relative_weight_density,
            name="Operating-priority relative weight density",
        )
        if upper <= lower:
            raise ValueError("Operating-priority intervals must have positive width")
        if weight < 0.0:
            raise ValueError(
                "Operating-priority relative weight density must be nonnegative"
            )
        validated.append(
            _OperatingPriorityInterval(
                minimum_temperature_c=lower,
                maximum_temperature_c=upper,
                relative_weight_density=weight,
            )
        )

    if validated[0].minimum_temperature_c != fitted_minimum_temperature_c:
        raise RTDExperimentDesignError(
            "Operating priorities must begin at the fitted-range minimum"
        )
    if validated[-1].maximum_temperature_c != fitted_maximum_temperature_c:
        raise RTDExperimentDesignError(
            "Operating priorities must end at the fitted-range maximum"
        )
    for previous, current in zip(validated, validated[1:], strict=False):
        if previous.maximum_temperature_c != current.minimum_temperature_c:
            raise RTDExperimentDesignError(
                "Operating priorities must form a complete non-overlapping partition"
            )
    if not any(interval.relative_weight_density > 0.0 for interval in validated):
        raise RTDExperimentDesignError(
            "At least one operating-priority interval must have positive weight"
        )
    return tuple(validated)


def _validated_sensitivity_breakpoints(
    breakpoints_c: tuple[float, ...],
    *,
    nominal_minimum_temperature_c: float,
    nominal_maximum_temperature_c: float,
) -> tuple[float, ...]:
    converted = tuple(
        _as_planning_float(value, name="Nominal-sensitivity breakpoint")
        for value in breakpoints_c
    )
    if converted != tuple(sorted(set(converted))):
        raise ValueError(
            "Nominal-sensitivity breakpoints must be unique and strictly increasing"
        )
    if any(
        value <= nominal_minimum_temperature_c or value >= nominal_maximum_temperature_c
        for value in converted
    ):
        raise ValueError(
            "Nominal-sensitivity breakpoints must lie inside the declared "
            "nominal domain"
        )
    return converted


def _moment_integrand_upper_triangle(
    model: RTDUncertaintyModel,
    temperature_c: float,
    *,
    degree: int,
    reference_temperature_c: float,
    relative_weight_density: float,
) -> tuple[float, ...]:
    sensitivity = model.temperature_sensitivity_celsius_per_ohm(temperature_c)
    if isinstance(sensitivity, bool):
        raise RTDExperimentDesignError(
            "Nominal temperature sensitivity must be a finite positive real number"
        )
    try:
        sensitivity = float(sensitivity)
    except (TypeError, ValueError) as error:
        raise RTDExperimentDesignError(
            "Nominal temperature sensitivity must be a finite positive real number"
        ) from error
    if not math.isfinite(sensitivity) or sensitivity <= 0.0:
        raise RTDExperimentDesignError(
            "Nominal temperature sensitivity must remain finite and strictly positive"
        )

    x = temperature_c - reference_temperature_c
    basis = [1.0]
    for _ in range(degree):
        basis.append(basis[-1] * x)
    if not all(math.isfinite(value) for value in basis):
        raise RTDExperimentDesignError(
            "Polynomial planning basis is not finitely representable over the "
            "fitted range"
        )

    scale = relative_weight_density * sensitivity * sensitivity
    if not math.isfinite(scale):
        raise RTDExperimentDesignError(
            "Sensitivity-weighted moment integrand is not finitely representable"
        )
    values = tuple(
        scale * basis[row] * basis[column]
        for row in range(degree + 1)
        for column in range(row, degree + 1)
    )
    if not all(math.isfinite(value) for value in values):
        raise RTDExperimentDesignError(
            "Sensitivity-weighted moment integrand is not finitely representable"
        )
    return values


def _gauss_kronrod_15_31_vector(
    evaluate: Callable[[float], tuple[float, ...]],
    lower: float,
    upper: float,
) -> _QuadratureEstimate:
    """Integrate a finite vector on one interval with QUADPACK-style DQK31.

    ``evaluate`` is intentionally kept internal and is called at exactly the
    31 Kronrod nodes. The embedded 15-point Gauss rule supplies the raw error
    difference, which is adjusted using QUADPACK's ``resasc`` formulation and
    roundoff floor. All vector components share exactly the same nodes.
    """

    # This helper is private and always receives the closure constructed by
    # _sensitivity_weighted_moment_matrix. Avoid exporting a callable-based API.
    center = 0.5 * (lower + upper)
    half_length = 0.5 * (upper - lower)
    absolute_half_length = abs(half_length)

    center_values = evaluate(center)
    component_count = len(center_values)
    # The explicit comprehensions below are clearer than broadcasting and keep the
    # package dependency-free.
    gauss = [
        _GK31_GAUSS_WEIGHTS[7] * center_values[index]
        for index in range(component_count)
    ]
    kronrod = [
        _GK31_KRONROD_WEIGHTS[15] * center_values[index]
        for index in range(component_count)
    ]
    absolute = [
        _GK31_KRONROD_WEIGHTS[15] * abs(center_values[index])
        for index in range(component_count)
    ]
    sampled_pairs: list[tuple[int, tuple[float, ...], tuple[float, ...]]] = []
    evaluation_count = 1

    for index in range(15):
        abscissa = half_length * _GK31_ABSCISSAE[index]
        left_values = evaluate(center - abscissa)
        right_values = evaluate(center + abscissa)
        evaluation_count += 2
        sampled_pairs.append((index, left_values, right_values))
        for component in range(component_count):
            pair_sum = left_values[component] + right_values[component]
            kronrod[component] += _GK31_KRONROD_WEIGHTS[index] * pair_sum
            absolute[component] += _GK31_KRONROD_WEIGHTS[index] * (
                abs(left_values[component]) + abs(right_values[component])
            )
        if index % 2 == 1:
            gauss_weight = _GK31_GAUSS_WEIGHTS[(index - 1) // 2]
            for component in range(component_count):
                gauss[component] += gauss_weight * (
                    left_values[component] + right_values[component]
                )

    means = [0.5 * value for value in kronrod]
    ascending = [
        _GK31_KRONROD_WEIGHTS[15] * abs(center_values[component] - means[component])
        for component in range(component_count)
    ]
    for index, left_values, right_values in sampled_pairs:
        weight = _GK31_KRONROD_WEIGHTS[index]
        for component in range(component_count):
            ascending[component] += weight * (
                abs(left_values[component] - means[component])
                + abs(right_values[component] - means[component])
            )

    values = tuple(value * half_length for value in kronrod)
    absolute_integrals = tuple(value * absolute_half_length for value in absolute)
    ascending_integrals = tuple(value * absolute_half_length for value in ascending)
    raw_errors = tuple(
        abs((kronrod[index] - gauss[index]) * half_length)
        for index in range(component_count)
    )
    errors: list[float] = []
    epsilon = sys.float_info.epsilon
    minimum_normal = sys.float_info.min
    for raw_error, resasc, resabs in zip(
        raw_errors,
        ascending_integrals,
        absolute_integrals,
        strict=True,
    ):
        adjusted = raw_error
        if resasc != 0.0 and adjusted != 0.0:
            adjusted = resasc * min(1.0, (200.0 * adjusted / resasc) ** 1.5)
        if resabs > minimum_normal / (50.0 * epsilon):
            adjusted = max(50.0 * epsilon * resabs, adjusted)
        errors.append(adjusted)

    return _QuadratureEstimate(
        values=values,
        absolute_integrals=absolute_integrals,
        errors=tuple(errors),
        evaluation_count=evaluation_count,
    )


def _quadrature_estimate_meets_target(estimate: _QuadratureEstimate) -> bool:
    return all(
        (
            error == 0.0
            if absolute_integral == 0.0
            else error <= _MOMENT_RELATIVE_ERROR_TARGET * absolute_integral
        )
        for error, absolute_integral in zip(
            estimate.errors,
            estimate.absolute_integrals,
            strict=True,
        )
    )


def _sensitivity_weighted_moment_matrix(
    model: RTDUncertaintyModel,
    *,
    degree: int,
    planning_reference_temperature_c: float,
    fitted_minimum_temperature_c: float,
    fitted_maximum_temperature_c: float,
    nominal_minimum_temperature_c: float,
    nominal_maximum_temperature_c: float,
    priority_intervals: tuple[_OperatingPriorityInterval, ...],
    sensitivity_breakpoints_c: tuple[float, ...] = (),
) -> _SensitivityWeightedMomentMatrix:
    """Construct the frozen sensitivity-weighted I-optimal moment matrix.

    For ``phi(T) = (1, x, ..., x**degree)`` with
    ``x = T - planning_reference_temperature_c``, relative priority density
    ``w(T)``, and nominal inverse sensitivity ``s(T) = dT/dR``, DESIGN.md defines

    ``M_T = integral w(T) s(T)^2 phi(T) phi(T).T dT / W``

    where ``W = integral w(T) dT``. This helper evaluates the complete upper
    triangle together with the dependency-free adaptive 15/31 Gauss-Kronrod
    procedure, then mirrors it exactly. With the package degree cap of 12,
    ``phi_i * phi_j`` has degree at most 24; on tabulated constant-sensitivity
    pieces the embedded Gauss-15 rule is already exact through degree 29 in
    exact arithmetic. Analytical CVD/polynomial sensitivity pieces instead rely
    on the adaptive error estimate. Breakpoints and priority boundaries are
    structural partitions, so quadrature never knowingly crosses them.
    """

    degree = _validate_degree(degree)
    reference = _as_planning_float(
        planning_reference_temperature_c,
        name="Planning reference temperature",
    )
    fitted_minimum = _as_planning_float(
        fitted_minimum_temperature_c,
        name="Fitted-range minimum temperature",
    )
    fitted_maximum = _as_planning_float(
        fitted_maximum_temperature_c,
        name="Fitted-range maximum temperature",
    )
    nominal_minimum = _as_planning_float(
        nominal_minimum_temperature_c,
        name="Nominal-sensitivity domain minimum temperature",
    )
    nominal_maximum = _as_planning_float(
        nominal_maximum_temperature_c,
        name="Nominal-sensitivity domain maximum temperature",
    )
    if fitted_maximum <= fitted_minimum:
        raise ValueError("Fitted range must have positive width")
    if nominal_maximum <= nominal_minimum:
        raise ValueError("Nominal-sensitivity domain must have positive width")
    if fitted_minimum < nominal_minimum or fitted_maximum > nominal_maximum:
        raise RTDExperimentDesignError(
            "The complete fitted range must lie inside the nominal-sensitivity domain"
        )

    priorities = _validated_priority_partition(
        priority_intervals,
        fitted_minimum_temperature_c=fitted_minimum,
        fitted_maximum_temperature_c=fitted_maximum,
    )
    breakpoints = _validated_sensitivity_breakpoints(
        sensitivity_breakpoints_c,
        nominal_minimum_temperature_c=nominal_minimum,
        nominal_maximum_temperature_c=nominal_maximum,
    )
    relevant_breakpoints = tuple(
        value for value in breakpoints if fitted_minimum < value < fitted_maximum
    )
    structural_partition = tuple(
        sorted(
            {
                fitted_minimum,
                fitted_maximum,
                *(interval.minimum_temperature_c for interval in priorities),
                *(interval.maximum_temperature_c for interval in priorities),
                *relevant_breakpoints,
            }
        )
    )

    normalization = math.fsum(
        interval.relative_weight_density
        * (interval.maximum_temperature_c - interval.minimum_temperature_c)
        for interval in priorities
    )
    if not math.isfinite(normalization) or normalization <= 0.0:
        raise RTDExperimentDesignError(
            "Operating-priority normalization is not finitely representable"
        )

    dimension = degree + 1
    component_count = dimension * (dimension + 1) // 2
    value_terms: list[list[float]] = [[] for _ in range(component_count)]
    error_terms: list[list[float]] = [[] for _ in range(component_count)]
    sensitivity_evaluation_count = 0
    accepted_subinterval_count = 0
    interval_evaluation_count = 0
    adaptive_subdivision_occurred = False

    priority_index = 0
    initial_pieces: list[tuple[float, float, float]] = []
    for lower, upper in zip(
        structural_partition,
        structural_partition[1:],
        strict=False,
    ):
        while (
            priority_index + 1 < len(priorities)
            and lower >= priorities[priority_index].maximum_temperature_c
        ):
            priority_index += 1
        priority = priorities[priority_index]
        if not (
            priority.minimum_temperature_c <= lower
            and upper <= priority.maximum_temperature_c
        ):
            raise AssertionError("Structural partition escaped its priority interval")
        initial_pieces.append((lower, upper, priority.relative_weight_density))

    for initial_lower, initial_upper, weight in initial_pieces:
        if weight == 0.0:
            continue

        def evaluate(
            temperature_c: float,
            piece_weight: float = weight,
        ) -> tuple[float, ...]:
            return _moment_integrand_upper_triangle(
                model,
                temperature_c,
                degree=degree,
                reference_temperature_c=reference,
                relative_weight_density=piece_weight,
            )

        stack = [(initial_lower, initial_upper, False)]
        while stack:
            lower, upper, subdivided = stack.pop()
            if interval_evaluation_count >= _MAX_MOMENT_INTERVAL_EVALUATIONS:
                raise RTDExperimentDesignError(
                    "Sensitivity-weighted moment integration exceeded its "
                    "deterministic resource limit before meeting the fixed error target"
                )
            estimate = _gauss_kronrod_15_31_vector(evaluate, lower, upper)
            interval_evaluation_count += 1
            sensitivity_evaluation_count += estimate.evaluation_count
            if _quadrature_estimate_meets_target(estimate):
                accepted_subinterval_count += 1
                adaptive_subdivision_occurred = (
                    adaptive_subdivision_occurred or subdivided
                )
                for component in range(component_count):
                    value_terms[component].append(estimate.values[component])
                    error_terms[component].append(estimate.errors[component])
                continue

            midpoint = 0.5 * (lower + upper)
            if midpoint in (lower, upper):
                raise RTDExperimentDesignError(
                    "Sensitivity-weighted moment integration cannot subdivide the "
                    "interval further while meeting the fixed error target"
                )
            adaptive_subdivision_occurred = True
            # LIFO stack: push right first so traversal remains deterministic
            # left-before-right, as specified in DESIGN.md.
            stack.append((midpoint, upper, True))
            stack.append((lower, midpoint, True))

    upper_values = tuple(math.fsum(terms) / normalization for terms in value_terms)
    upper_errors = tuple(math.fsum(terms) / normalization for terms in error_terms)
    if not all(math.isfinite(value) for value in (*upper_values, *upper_errors)):
        raise RTDExperimentDesignError(
            "Sensitivity-weighted moment matrix is not finitely representable"
        )

    moment_rows = [[0.0] * dimension for _ in range(dimension)]
    error_rows = [[0.0] * dimension for _ in range(dimension)]
    component = 0
    for row in range(dimension):
        for column in range(row, dimension):
            moment_rows[row][column] = upper_values[component]
            moment_rows[column][row] = upper_values[component]
            error_rows[row][column] = upper_errors[component]
            error_rows[column][row] = upper_errors[component]
            component += 1

    return _SensitivityWeightedMomentMatrix(
        moment_matrix=tuple(tuple(row) for row in moment_rows),
        normalized_estimated_error_matrix=tuple(tuple(row) for row in error_rows),
        parameter_names=tuple(f"a{power}" for power in range(dimension)),
        reference_temperature_c=reference,
        priority_normalization_c=normalization,
        structural_partition_c=structural_partition,
        accepted_subinterval_count=accepted_subinterval_count,
        sensitivity_evaluation_count=sensitivity_evaluation_count,
        adaptive_subdivision_occurred=adaptive_subdivision_occurred,
        integration_method=_MOMENT_INTEGRATION_METHOD,
        relative_error_target=_MOMENT_RELATIVE_ERROR_TARGET,
    )


_MAXIMUM_UNCERTAINTY_METHOD = "analytical_sensitivity_stationary_polynomial"
_MAX_STATIONARY_POLYNOMIAL_DEGREE = 34


@dataclass(frozen=True, slots=True)
class _ResistanceSensitivityPiece:
    """One package-owned analytical dR/dT polynomial over a closed interval."""

    minimum_temperature_c: float
    maximum_temperature_c: float
    local_origin_temperature_c: float
    coefficients_ohms_per_celsius: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class _MaximumUncertaintyLocation:
    """One exact computed maximizer or one-sided limiting location."""

    temperature_c: float
    side: Literal["point", "left_limit", "right_limit"]


@dataclass(frozen=True, slots=True)
class _MaximumPredictedTemperatureUncertainty:
    """Frozen result of the package-model full-range maximum diagnostic."""

    status: Literal["established", "not_established"]
    maximum_standard_uncertainty_c: float | None
    maximum_variance_c2: float | None
    locations: tuple[_MaximumUncertaintyLocation, ...]
    method: str | None
    reason: str | None
    analytical_piece_count: int
    stationary_root_count: int
    maximum_stationary_polynomial_degree: int | None


def _translate_polynomial_coefficients(
    coefficients: Sequence[float],
    *,
    source_origin_temperature_c: float,
    target_origin_temperature_c: float,
) -> tuple[float, ...]:
    """Translate an ascending-power polynomial into a new local coordinate."""

    shift = target_origin_temperature_c - source_origin_temperature_c
    translated_terms: list[list[float]] = [[] for _ in range(len(coefficients))]
    try:
        for source_power, coefficient in enumerate(coefficients):
            for target_power in range(source_power + 1):
                translated_terms[target_power].append(
                    coefficient
                    * math.comb(source_power, target_power)
                    * shift ** (source_power - target_power)
                )
        translated = tuple(math.fsum(terms) for terms in translated_terms)
    except OverflowError as error:
        raise RTDExperimentDesignError(
            "Analytical sensitivity polynomial is not finitely representable"
        ) from error
    if not all(math.isfinite(value) for value in translated):
        raise RTDExperimentDesignError(
            "Analytical sensitivity polynomial is not finitely representable"
        )
    return _trim_polynomial(translated)


def _localized_sensitivity_piece(
    *,
    minimum_temperature_c: float,
    maximum_temperature_c: float,
    source_origin_temperature_c: float,
    source_coefficients_ohms_per_celsius: Sequence[float],
) -> _ResistanceSensitivityPiece:
    local_origin = minimum_temperature_c + 0.5 * (
        maximum_temperature_c - minimum_temperature_c
    )
    coefficients = _translate_polynomial_coefficients(
        source_coefficients_ohms_per_celsius,
        source_origin_temperature_c=source_origin_temperature_c,
        target_origin_temperature_c=local_origin,
    )
    return _ResistanceSensitivityPiece(
        minimum_temperature_c=minimum_temperature_c,
        maximum_temperature_c=maximum_temperature_c,
        local_origin_temperature_c=local_origin,
        coefficients_ohms_per_celsius=coefficients,
    )


def _package_internal_model(model: object) -> _InternalRTDModel | None:
    """Return the package-owned internal model behind a supported public object."""

    if isinstance(model, _InternalRTDModel):
        return model

    if isinstance(model, _public_models.IEC60751RTDModel):
        return model._model
    if isinstance(model, _public_models.CallendarVanDusenRTDModel):
        return model._model
    if isinstance(model, _public_models.PolynomialRTDModel):
        return model._model
    if isinstance(model, _public_models.PiecewisePolynomialRTDModel):
        return model._model

    # Built-in convenience modules such as ``rtd_sensor.pt100`` are package-owned
    # model façades. Do not recognize arbitrary third-party modules merely because
    # they happen to expose an attribute named ``_MODEL``.
    if isinstance(model, ModuleType) and model.__name__.startswith("rtd_sensor."):
        internal = getattr(model, "_MODEL", None)
        if isinstance(internal, _InternalRTDModel):
            return internal

    return None


def _package_sensitivity_pieces(
    model: object,
    *,
    fitted_minimum_temperature_c: float,
    fitted_maximum_temperature_c: float,
) -> tuple[_ResistanceSensitivityPiece, ...] | None:
    """Freeze package analytical dR/dT pieces, or return ``None`` for black boxes."""

    pieces: list[_ResistanceSensitivityPiece] = []
    if isinstance(model, _public_models.TabulatedRTDModel):
        if (
            fitted_minimum_temperature_c < model.minimum_temperature_c
            or fitted_maximum_temperature_c > model.maximum_temperature_c
        ):
            raise RTDExperimentDesignError(
                "The complete fitted range must lie inside the nominal-model range"
            )

        temperatures = model._temperatures_c
        slopes = model._slopes_ohms_per_celsius
        for index, slope in enumerate(slopes):
            lower = max(fitted_minimum_temperature_c, temperatures[index])
            upper = min(fitted_maximum_temperature_c, temperatures[index + 1])
            if lower >= upper:
                continue
            pieces.append(
                _localized_sensitivity_piece(
                    minimum_temperature_c=lower,
                    maximum_temperature_c=upper,
                    source_origin_temperature_c=lower,
                    source_coefficients_ohms_per_celsius=(slope,),
                )
            )
        return tuple(pieces)

    internal = _package_internal_model(model)
    if internal is None:
        return None

    declared_minimum = internal.minimum_temperature_c
    declared_maximum = internal.maximum_temperature_c
    if isinstance(
        model,
        (
            _public_models.IEC60751RTDModel,
            _public_models.CallendarVanDusenRTDModel,
            _public_models.PolynomialRTDModel,
            _public_models.PiecewisePolynomialRTDModel,
        ),
    ):
        declared_minimum = model.minimum_temperature_c
        declared_maximum = model.maximum_temperature_c
    if (
        fitted_minimum_temperature_c < declared_minimum
        or fitted_maximum_temperature_c > declared_maximum
    ):
        raise RTDExperimentDesignError(
            "The complete fitted range must lie inside the nominal-model range"
        )

    curve = internal.curve
    resistance_scale = internal.reference_resistance_ohms
    pieces = []

    if isinstance(curve, _CallendarVanDusenCurve):
        source_pieces: list[tuple[float, float, tuple[float, ...]]] = []
        negative_upper = min(fitted_maximum_temperature_c, 0.0)
        if fitted_minimum_temperature_c < negative_upper:
            source_pieces.append(
                (
                    fitted_minimum_temperature_c,
                    negative_upper,
                    (
                        resistance_scale * curve.a,
                        resistance_scale * 2.0 * curve.b,
                        resistance_scale * -300.0 * curve.c,
                        resistance_scale * 4.0 * curve.c,
                    ),
                )
            )
        positive_lower = max(fitted_minimum_temperature_c, 0.0)
        if positive_lower < fitted_maximum_temperature_c:
            source_pieces.append(
                (
                    positive_lower,
                    fitted_maximum_temperature_c,
                    (
                        resistance_scale * curve.a,
                        resistance_scale * 2.0 * curve.b,
                    ),
                )
            )
        # A range ending or beginning exactly at 0 °C still needs one analytical
        # piece. The applicable derivative is the side present inside the range.
        if not source_pieces:
            fallback_coefficients: tuple[float, ...] = (
                resistance_scale * curve.a,
                resistance_scale * 2.0 * curve.b,
            )
            source_pieces.append(
                (
                    fitted_minimum_temperature_c,
                    fitted_maximum_temperature_c,
                    fallback_coefficients,
                )
            )
        for lower, upper, coefficients in source_pieces:
            pieces.append(
                _localized_sensitivity_piece(
                    minimum_temperature_c=lower,
                    maximum_temperature_c=upper,
                    source_origin_temperature_c=0.0,
                    source_coefficients_ohms_per_celsius=coefficients,
                )
            )
        return tuple(pieces)

    if isinstance(curve, _PolynomialRTDCurve):
        source_coefficients = tuple(
            resistance_scale * power * coefficient
            for power, coefficient in enumerate(curve.coefficients, start=1)
        )
        return (
            _localized_sensitivity_piece(
                minimum_temperature_c=fitted_minimum_temperature_c,
                maximum_temperature_c=fitted_maximum_temperature_c,
                source_origin_temperature_c=curve.reference_temperature_c,
                source_coefficients_ohms_per_celsius=source_coefficients,
            ),
        )

    if isinstance(curve, _PiecewisePolynomialRTDCurve):
        for segment in curve.segments:
            lower = max(fitted_minimum_temperature_c, segment.minimum_temperature_c)
            upper = min(fitted_maximum_temperature_c, segment.maximum_temperature_c)
            if lower >= upper:
                continue
            source_coefficients = tuple(
                resistance_scale * power * coefficient
                for power, coefficient in enumerate(segment.coefficients[1:], start=1)
            )
            pieces.append(
                _localized_sensitivity_piece(
                    minimum_temperature_c=lower,
                    maximum_temperature_c=upper,
                    source_origin_temperature_c=segment.temperature_origin_c,
                    source_coefficients_ohms_per_celsius=source_coefficients,
                )
            )
        return tuple(pieces)

    # A future package model family does not silently inherit an analytical
    # maximum claim. It must explicitly define the exact piece semantics first.
    return None


def _variance_polynomial_in_local_coordinate(
    covariance_matrix: tuple[tuple[float, ...], ...],
    *,
    planning_reference_temperature_c: float,
    local_origin_temperature_c: float,
) -> tuple[float, ...]:
    """Return q(T)=phi(T).T C phi(T) in one local temperature coordinate."""

    dimension = len(covariance_matrix)
    maximum_power = 2 * (dimension - 1)
    coefficient_terms: list[list[float]] = [[] for _ in range(maximum_power + 1)]
    shift = local_origin_temperature_c - planning_reference_temperature_c
    try:
        for row in range(dimension):
            for column in range(dimension):
                source_power = row + column
                covariance = covariance_matrix[row][column]
                for target_power in range(source_power + 1):
                    coefficient_terms[target_power].append(
                        covariance
                        * math.comb(source_power, target_power)
                        * shift ** (source_power - target_power)
                    )
        coefficients = tuple(math.fsum(terms) for terms in coefficient_terms)
    except OverflowError as error:
        raise RTDExperimentDesignError(
            "Predicted fitted-curve variance polynomial is not finitely representable"
        ) from error
    if not all(math.isfinite(value) for value in coefficients):
        raise RTDExperimentDesignError(
            "Predicted fitted-curve variance polynomial is not finitely representable"
        )
    return _trim_polynomial(coefficients)


def _multiply_polynomials(
    left: Sequence[float],
    right: Sequence[float],
) -> tuple[float, ...]:
    if not left or not right:
        return (0.0,)
    terms: list[list[float]] = [[] for _ in range(len(left) + len(right) - 1)]
    try:
        for left_power, left_coefficient in enumerate(left):
            for right_power, right_coefficient in enumerate(right):
                terms[left_power + right_power].append(
                    left_coefficient * right_coefficient
                )
        result = tuple(math.fsum(component_terms) for component_terms in terms)
    except OverflowError as error:
        raise RTDExperimentDesignError(
            "Stationary-point polynomial is not finitely representable"
        ) from error
    if not all(math.isfinite(value) for value in result):
        raise RTDExperimentDesignError(
            "Stationary-point polynomial is not finitely representable"
        )
    return _trim_polynomial(result)


def _stationary_polynomial(
    variance_coefficients: Sequence[float],
    sensitivity_coefficients: Sequence[float],
) -> tuple[float, ...]:
    """Build h=q'r-2qr', whose interior roots locate extrema of q/r^2."""

    first = _multiply_polynomials(
        _polynomial_derivative(variance_coefficients),
        sensitivity_coefficients,
    )
    second = _multiply_polynomials(
        variance_coefficients,
        _polynomial_derivative(sensitivity_coefficients),
    )
    size = max(len(first), len(second))
    result = tuple(
        math.fsum(
            (
                first[power] if power < len(first) else 0.0,
                -2.0 * second[power] if power < len(second) else 0.0,
            )
        )
        for power in range(size)
    )
    if not all(math.isfinite(value) for value in result):
        raise RTDExperimentDesignError(
            "Stationary-point polynomial is not finitely representable"
        )
    return _trim_polynomial(result)


def _stationary_roots_in_interval(
    coefficients: Sequence[float],
    lower: float,
    upper: float,
) -> tuple[float, ...]:
    """Locate roots of a validated degree-at-most-34 stationary polynomial."""

    polynomial = _trim_polynomial(coefficients)
    degree = len(polynomial) - 1
    if degree > _MAX_STATIONARY_POLYNOMIAL_DEGREE:
        raise RTDExperimentDesignError(
            "Stationary-point polynomial exceeds the validated degree limit"
        )
    try:
        roots = tuple(_polynomial_roots_in_interval(polynomial, lower, upper))
    except (OverflowError, ValueError) as error:
        raise RTDExperimentDesignError(
            "Stationary-point root calculation did not remain finite"
        ) from error
    if not all(math.isfinite(root) and lower < root < upper for root in roots):
        raise RTDExperimentDesignError(
            "Stationary-point root calculation produced an invalid root"
        )
    return roots


def _predicted_temperature_variance_at_piece_temperature(
    covariance: _ProspectivePolynomialCovariance,
    piece: _ResistanceSensitivityPiece,
    temperature_c: float,
) -> float:
    x = temperature_c - covariance.reference_temperature_c
    basis = [1.0]
    for _ in range(len(covariance.covariance_matrix) - 1):
        basis.append(basis[-1] * x)
    try:
        resistance_variance = _covariance_quadratic_form(
            tuple(basis),
            covariance.covariance_matrix,
        )
        local_temperature = temperature_c - piece.local_origin_temperature_c
        resistance_sensitivity = _polynomial_value(
            piece.coefficients_ohms_per_celsius,
            local_temperature,
        )
    except (OverflowError, ValueError) as error:
        raise RTDExperimentDesignError(
            "Predicted fitted-curve temperature variance is not finitely representable"
        ) from error
    if not math.isfinite(resistance_sensitivity) or resistance_sensitivity <= 0.0:
        raise RTDExperimentDesignError(
            "Package analytical resistance sensitivity must remain finite and "
            "strictly positive"
        )
    try:
        inverse_sensitivity = 1.0 / resistance_sensitivity
        variance = resistance_variance * inverse_sensitivity * inverse_sensitivity
    except OverflowError as error:
        raise RTDExperimentDesignError(
            "Predicted fitted-curve temperature variance is not finitely representable"
        ) from error
    if not math.isfinite(variance) or variance < 0.0:
        raise RTDExperimentDesignError(
            "Predicted fitted-curve temperature variance is not finitely representable"
        )
    return variance


def _full_range_maximum_predicted_temperature_uncertainty(
    model: object,
    covariance: _ProspectivePolynomialCovariance,
    *,
    fitted_minimum_temperature_c: float,
    fitted_maximum_temperature_c: float,
) -> _MaximumPredictedTemperatureUncertainty:
    """Establish the full-range maximum fitted-curve uncertainty when possible.

    Package-owned CVD, polynomial, piecewise-polynomial, and tabulated models expose
    exact analytical dR/dT pieces internally. On each piece, with resistance-domain
    fitted-curve variance ``q(T)`` and resistance sensitivity ``r(T)=dR/dT``, the
    temperature-domain variance is ``v_T=q/r**2``. Its interior stationary points
    are the real roots of ``h=q' r - 2 q r'``. For degree-12 fits and degree-12
    nominal polynomial pieces, ``h`` has degree at most 34.

    Arbitrary structural third-party models are deliberately not sampled in search
    of a pseudo-maximum. Their integrated I-optimal criterion may still use dT/dR,
    but this diagnostic returns ``not_established`` unless the package owns the
    analytical piece semantics.
    """

    fitted_minimum = _as_planning_float(
        fitted_minimum_temperature_c,
        name="Fitted-range minimum temperature",
    )
    fitted_maximum = _as_planning_float(
        fitted_maximum_temperature_c,
        name="Fitted-range maximum temperature",
    )
    if fitted_maximum <= fitted_minimum:
        raise ValueError("Fitted range must have positive width")
    planning_midpoint = fitted_minimum + 0.5 * (fitted_maximum - fitted_minimum)
    if covariance.reference_temperature_c != planning_midpoint:
        raise RTDExperimentDesignError(
            "Full-range maximum uncertainty requires the fixed planning basis "
            "at the midpoint of the complete fitted range"
        )

    pieces = _package_sensitivity_pieces(
        model,
        fitted_minimum_temperature_c=fitted_minimum,
        fitted_maximum_temperature_c=fitted_maximum,
    )
    if pieces is None:
        return _MaximumPredictedTemperatureUncertainty(
            status="not_established",
            maximum_standard_uncertainty_c=None,
            maximum_variance_c2=None,
            locations=(),
            method=None,
            reason=(
                "The nominal model does not expose package-owned analytical "
                "sensitivity pieces for a proof-oriented full-range maximum"
            ),
            analytical_piece_count=0,
            stationary_root_count=0,
            maximum_stationary_polynomial_degree=None,
        )
    if not pieces:
        raise RTDExperimentDesignError(
            "No analytical nominal-model sensitivity piece covers the fitted range"
        )

    evaluations: list[tuple[float, _MaximumUncertaintyLocation]] = []
    stationary_root_count = 0
    maximum_stationary_degree = 0

    for piece_index, piece in enumerate(pieces):
        variance_coefficients = _variance_polynomial_in_local_coordinate(
            covariance.covariance_matrix,
            planning_reference_temperature_c=covariance.reference_temperature_c,
            local_origin_temperature_c=piece.local_origin_temperature_c,
        )
        stationary = _stationary_polynomial(
            variance_coefficients,
            piece.coefficients_ohms_per_celsius,
        )
        stationary_degree = len(stationary) - 1
        maximum_stationary_degree = max(maximum_stationary_degree, stationary_degree)
        lower_local = piece.minimum_temperature_c - piece.local_origin_temperature_c
        upper_local = piece.maximum_temperature_c - piece.local_origin_temperature_c
        roots = _stationary_roots_in_interval(
            stationary,
            lower_local,
            upper_local,
        )
        stationary_root_count += len(roots)

        lower_side: Literal["point", "right_limit"] = (
            "point" if piece_index == 0 else "right_limit"
        )
        upper_side: Literal["point", "left_limit"] = (
            "point" if piece_index == len(pieces) - 1 else "left_limit"
        )
        for temperature_c, side in (
            (piece.minimum_temperature_c, lower_side),
            (piece.maximum_temperature_c, upper_side),
        ):
            evaluations.append(
                (
                    _predicted_temperature_variance_at_piece_temperature(
                        covariance,
                        piece,
                        temperature_c,
                    ),
                    _MaximumUncertaintyLocation(temperature_c, side),
                )
            )

        for root in roots:
            temperature_c = piece.local_origin_temperature_c + root
            evaluations.append(
                (
                    _predicted_temperature_variance_at_piece_temperature(
                        covariance,
                        piece,
                        temperature_c,
                    ),
                    _MaximumUncertaintyLocation(temperature_c, "point"),
                )
            )

    maximum_variance = max(value for value, _ in evaluations)
    locations = tuple(
        location for value, location in evaluations if value == maximum_variance
    )
    return _MaximumPredictedTemperatureUncertainty(
        status="established",
        maximum_standard_uncertainty_c=math.sqrt(maximum_variance),
        maximum_variance_c2=maximum_variance,
        locations=locations,
        method=_MAXIMUM_UNCERTAINTY_METHOD,
        reason=None,
        analytical_piece_count=len(pieces),
        stationary_root_count=stationary_root_count,
        maximum_stationary_polynomial_degree=maximum_stationary_degree,
    )
