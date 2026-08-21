# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Measurement-uncertainty helpers for RTD temperature conversion.

The low-level helpers in this module follow the measurement-uncertainty
conventions in JCGM 100:2008 and NIST Technical Note 1297. Full citations are
maintained in ``docs/REFERENCES.md``.
They operate on already-evaluated uncertainty quantities; they do not decide
which physical effects belong in a particular RTD uncertainty budget.

A tolerance limit is not automatically a standard uncertainty. If a bounded
specification is converted with :func:`standard_uncertainty_from_bound`, the
selected probability distribution is an explicit modeling assumption made by
the caller.

The RTD-specific helpers use exact local sensitivities supplied by the active RTD
model. Inverse temperature transformations use first-order propagation. The
helpers preserve fitted-model, resistance-measurement, and additional
temperature-domain contributions separately so uncertainty analysis remains
inspectable rather than collapsing immediately to one number.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, TypeAlias

from ._protocols import RTDUncertaintyModel
from ._validation import as_float as _as_float
from .fitting import (
    CallendarVanDusenFitResult,
    FitParameterCovariance,
    IEC60751R0FitResult,
    PolynomialFitResult,
)

__all__ = [
    "BoundDistribution",
    "EvaluationMethod",
    "FitCovarianceResistancePropagation",
    "FitCovarianceTemperaturePropagation",
    "RTDUncertaintyModel",
    "ResistanceUncertaintyPropagation",
    "TemperatureUncertaintyBudget",
    "TemperatureUncertaintyComponent",
    "combine_independent_standard_uncertainties",
    "expanded_uncertainty",
    "propagate_fit_covariance_to_resistance",
    "propagate_fit_covariance_to_temperature",
    "propagate_resistance_uncertainty",
    "standard_uncertainty_from_bound",
    "standard_uncertainty_from_expanded",
    "temperature_uncertainty_budget",
]


BoundDistribution: TypeAlias = Literal["rectangular", "triangular"]
EvaluationMethod: TypeAlias = Literal["A", "B"]


@dataclass(frozen=True, slots=True)
class TemperatureUncertaintyComponent:
    """Named standard-uncertainty contribution already expressed in Celsius.

    Args:
        name: Short human-readable name for the contribution.
        standard_uncertainty_c: Non-negative standard uncertainty in °C.
        evaluation_method: Optional ``"A"`` or ``"B"`` label describing how
            the standard uncertainty was evaluated. The label records the
            evaluation method, not a different mathematical combination rule.
        source: Optional provenance such as a calibration certificate,
            manufacturer specification, test report, or calculation source.
        note: Optional free-form explanation of assumptions or context.
    """

    name: str
    standard_uncertainty_c: float
    evaluation_method: EvaluationMethod | None = None
    source: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        name = _validate_nonempty_text(self.name, name="Component name")
        standard_uncertainty_c = _validate_nonnegative_finite(
            self.standard_uncertainty_c,
            name="Component standard uncertainty",
        )

        evaluation_method = self.evaluation_method
        if evaluation_method not in (None, "A", "B"):
            raise ValueError("Evaluation method must be 'A', 'B', or None")

        source = _validate_optional_text(self.source, name="Component source")
        note = _validate_optional_text(self.note, name="Component note")

        object.__setattr__(self, "name", name)
        object.__setattr__(
            self,
            "standard_uncertainty_c",
            standard_uncertainty_c,
        )
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "note", note)


@dataclass(frozen=True, slots=True)
class FitCovarianceResistancePropagation:
    """Fitted-parameter covariance propagated to resistance at one temperature.

    ``parameter_sensitivity_vector`` contains ``dR/dtheta`` values in the same
    order as ``parameter_covariance.parameter_names``. Because fitted parameters
    can have different dimensions, the individual sensitivity entries do not
    necessarily share one physical unit. The propagated variance and standard
    uncertainty are always reported in ``ohm²`` and ``ohm`` respectively.

    This result describes only uncertainty associated with the retained fitted-
    parameter covariance. It does not include measurement-resistance uncertainty,
    calibration reference-temperature uncertainty, drift, self-heating, tolerance,
    or other uncertainty-budget components.
    """

    temperature_c: float
    resistance_ohms: float
    parameter_covariance: FitParameterCovariance
    parameter_sensitivity_vector: tuple[float, ...]
    resistance_variance_ohms_squared: float
    resistance_standard_uncertainty_ohms: float


@dataclass(frozen=True, slots=True)
class FitCovarianceTemperaturePropagation:
    """Fitted-parameter covariance propagated to inferred temperature.

    ``resistance_parameter_sensitivity_vector`` retains ``dR/dtheta`` and
    ``parameter_sensitivity_vector`` contains the derived ``dT/dtheta`` values,
    both in the same order as ``parameter_covariance.parameter_names``. The
    temperature sensitivities come from implicit differentiation of the fitted
    RTD relationship at the converted temperature::

        dT/dtheta = -(dR/dtheta) * (dT/dR)

    The resulting covariance propagation is first-order/local because inferred
    temperature is generally nonlinear in the fitted parameters. The measured
    resistance is treated as fixed; its own uncertainty is not included.

    This result describes only uncertainty associated with the retained fitted-
    parameter covariance. It does not include measurement-resistance uncertainty,
    calibration reference-temperature uncertainty, drift, self-heating, tolerance,
    or other uncertainty-budget components.
    """

    resistance_ohms: float
    temperature_c: float
    parameter_covariance: FitParameterCovariance
    resistance_parameter_sensitivity_vector: tuple[float, ...]
    temperature_sensitivity_celsius_per_ohm: float
    parameter_sensitivity_vector: tuple[float, ...]
    temperature_variance_celsius_squared: float
    temperature_standard_uncertainty_c: float


@dataclass(frozen=True, slots=True)
class ResistanceUncertaintyPropagation:
    """First-order propagation of resistance uncertainty into temperature."""

    resistance_ohms: float
    temperature_c: float
    resistance_standard_uncertainty_ohms: float
    temperature_sensitivity_celsius_per_ohm: float
    temperature_standard_uncertainty_c: float


@dataclass(frozen=True, slots=True)
class TemperatureUncertaintyBudget:
    """Structured RTD temperature uncertainty budget.

    ``resistance`` retains the resistance-domain input and its propagated
    temperature contribution. ``additional_components`` contains independent
    standard-uncertainty contributions that the caller has already expressed
    in °C. The current budget combines those contributions as uncorrelated.

    ``coverage_factor`` and ``expanded_uncertainty_c`` are both ``None`` when
    expanded uncertainty was not requested. No confidence level is inferred
    from a supplied coverage factor.
    """

    resistance: ResistanceUncertaintyPropagation
    additional_components: tuple[TemperatureUncertaintyComponent, ...]
    combined_standard_uncertainty_c: float
    coverage_factor: float | None
    expanded_uncertainty_c: float | None

    @property
    def temperature_c(self) -> float:
        """Return the converted temperature associated with this budget."""
        return self.resistance.temperature_c


# Source: JCGM (2008), JCGM 100:2008, and Taylor & Kuyatt (1994);
# see docs/REFERENCES.md.
def standard_uncertainty_from_bound(
    half_width: float,
    *,
    distribution: BoundDistribution,
) -> float:
    """Convert a symmetric bound half-width to standard uncertainty.

    Args:
        half_width: Positive magnitude ``a`` of a symmetric interval
            ``estimate ± a``.
        distribution: Probability model assigned to values inside the
            interval. ``rectangular`` gives ``a / sqrt(3)`` and
            ``triangular`` gives ``a / sqrt(6)``.

    Returns:
        Standard uncertainty in the same units as ``half_width``.

    Raises:
        ValueError: If the half-width is negative or non-finite, or if the
            distribution is unsupported.

    Notes:
        Choosing a distribution is part of the uncertainty model. This
        function must not be read as asserting that an IEC tolerance band,
        manufacturer limit, or other specification has a particular
        probability distribution.
    """
    bound = _validate_nonnegative_finite(half_width, name="Half-width")

    if distribution == "rectangular":
        divisor = math.sqrt(3.0)
    elif distribution == "triangular":
        divisor = math.sqrt(6.0)
    else:
        raise ValueError("Distribution must be 'rectangular' or 'triangular'")

    return bound / divisor


# Source: JCGM (2008), JCGM 100:2008; see docs/REFERENCES.md.
def standard_uncertainty_from_expanded(
    expanded_uncertainty_value: float,
    *,
    coverage_factor: float,
) -> float:
    """Convert expanded uncertainty ``U`` to standard uncertainty ``u``.

    This performs the inverse of ``U = k * u`` and therefore requires the
    coverage factor from the certificate or other source that reported the
    expanded uncertainty.
    """
    expanded = _validate_nonnegative_finite(
        expanded_uncertainty_value,
        name="Expanded uncertainty",
    )
    factor = _validate_positive_finite(
        coverage_factor,
        name="Coverage factor",
    )
    standard = expanded / factor
    if not math.isfinite(standard):
        raise ValueError("Standard uncertainty result must remain finite")
    return standard


# Source: JCGM (2008), JCGM 100:2008, law of propagation for
# uncorrelated inputs; see docs/REFERENCES.md.
def combine_independent_standard_uncertainties(
    *standard_uncertainties: float,
) -> float:
    """Combine independent standard uncertainties by root-sum-square.

    Args:
        *standard_uncertainties: One or more non-negative standard
            uncertainties expressed in the same output units.

    Returns:
        Combined standard uncertainty in those same units.

    Raises:
        ValueError: If no components are supplied or if any component is
            negative or non-finite.

    Notes:
        This helper assumes the supplied components are uncorrelated. It
        intentionally does not accept covariance or correlation terms; those
        require a covariance-aware propagation model.
    """
    if not standard_uncertainties:
        raise ValueError("At least one standard uncertainty is required")

    validated = [
        _validate_nonnegative_finite(value, name="Standard uncertainty")
        for value in standard_uncertainties
    ]

    # math.hypot performs the root-sum-square calculation without the
    # avoidable overflow/underflow risk of explicitly squaring every input.
    combined = math.hypot(*validated)
    if not math.isfinite(combined):
        raise ValueError("Combined standard uncertainty must remain finite")
    return combined


# Source: JCGM (2008), JCGM 100:2008; see docs/REFERENCES.md.
def expanded_uncertainty(
    combined_standard_uncertainty: float,
    *,
    coverage_factor: float,
) -> float:
    """Return expanded uncertainty ``U = k * u_c``.

    No confidence level is inferred from the coverage factor. A coverage
    factor such as ``k=2`` only has a probability interpretation when that
    interpretation is justified by the underlying uncertainty analysis.
    """
    combined = _validate_nonnegative_finite(
        combined_standard_uncertainty,
        name="Combined standard uncertainty",
    )
    factor = _validate_positive_finite(
        coverage_factor,
        name="Coverage factor",
    )
    expanded = factor * combined
    if not math.isfinite(expanded):
        raise ValueError("Expanded uncertainty result must remain finite")
    return expanded


# Source: JCGM (2008), JCGM 100:2008, sections 5.1-5.2, and
# Taylor & Kuyatt (1994), Appendix A; see docs/REFERENCES.md.
def propagate_fit_covariance_to_resistance(
    temperature_c: float,
    *,
    fit_result: CallendarVanDusenFitResult | IEC60751R0FitResult | PolynomialFitResult,
) -> FitCovarianceResistancePropagation:
    """Propagate fitted-parameter covariance into resistance uncertainty.

    The calculation applies the covariance form of the law of propagation of
    uncertainty using the full retained parameter covariance matrix::

        u²(R) = J Cov(theta) J.T

    where ``J`` is the resistance sensitivity vector with respect to the fitted
    parameters at ``temperature_c``. Correlation terms in the fitted-parameter
    covariance are therefore retained rather than combined as if the parameters
    were independent. For IEC-R0 and resistance-space polynomial parameterizations,
    resistance is linear in the retained fitted parameters and the covariance
    transformation is exact at fixed temperature. Custom CVD results use the public
    ``R0, A, B, C`` parameter basis; when ``R0`` and shape coefficients are jointly
    fitted, forward propagation is first-order/local because those parameters enter
    the CVD equation multiplicatively.

    Supported fit results are ``CallendarVanDusenFitResult``,
    ``IEC60751R0FitResult``, and ``PolynomialFitResult``. The fit must contain
    available parameter covariance.

    This is fitted-model uncertainty only. It does not include uncertainty in a
    subsequently measured resistance, calibration reference-temperature
    uncertainty, sensor drift, tolerance, self-heating, or other effects.
    """
    if not isinstance(
        fit_result,
        (CallendarVanDusenFitResult, IEC60751R0FitResult, PolynomialFitResult),
    ):
        raise TypeError(
            "fit_result must be CallendarVanDusenFitResult, IEC60751R0FitResult, "
            "or PolynomialFitResult"
        )

    temperature = _as_float(temperature_c, name="Temperature")
    if not math.isfinite(temperature):
        raise ValueError("Temperature must be finite")

    covariance = fit_result.evidence.parameter_covariance
    if covariance is None:
        reason = fit_result.evidence.parameter_covariance_unavailable_reason
        detail = "unknown reason" if reason is None else reason
        raise ValueError(
            "Fit parameter covariance is unavailable "
            f"({detail}); the fitted model itself remains valid for temperature "
            "conversion, but its uncertainty cannot be propagated."
        )

    sensitivities: tuple[float, ...]
    if isinstance(fit_result, IEC60751R0FitResult):
        if covariance.parameterization != "r0_ohms" or covariance.parameter_names != (
            "r0_ohms",
        ):
            raise ValueError("IEC R0 fit covariance has an unexpected parameterization")
        resistance = _as_float(
            fit_result.model.celsius_to_resistance(temperature),
            name="Fitted resistance",
        )
        sensitivities = (resistance / fit_result.model.r0_ohms,)
    elif isinstance(fit_result, CallendarVanDusenFitResult):
        if (
            covariance.parameterization != "callendar_van_dusen_parameters"
            or covariance.parameter_names != fit_result.evidence.fitted_parameter_names
        ):
            raise ValueError(
                "Callendar-Van Dusen fit covariance has an unexpected parameterization"
            )
        resistance = _as_float(
            fit_result.model.celsius_to_resistance(temperature),
            name="Fitted resistance",
        )
        sensitivity_values: list[float] = []
        for parameter in covariance.parameter_names:
            if parameter == "r0_ohms":
                sensitivity_values.append(resistance / fit_result.model.r0_ohms)
            elif parameter == "a":
                sensitivity_values.append(fit_result.model.r0_ohms * temperature)
            elif parameter == "b":
                sensitivity_values.append(
                    fit_result.model.r0_ohms * temperature * temperature
                )
            elif parameter == "c":
                c_basis = (
                    (temperature - 100.0) * temperature**3 if temperature < 0.0 else 0.0
                )
                sensitivity_values.append(fit_result.model.r0_ohms * c_basis)
            else:
                raise ValueError(
                    "Callendar-Van Dusen fit covariance has an unknown parameter name"
                )
        sensitivities = tuple(sensitivity_values)
    else:
        expected_parameter_names = tuple(
            f"a{power}" for power in range(len(fit_result.model.coefficients) + 1)
        )
        if (
            covariance.parameterization
            != "resistance_power_series_at_model_reference_temperature"
            or covariance.parameter_names != expected_parameter_names
        ):
            raise ValueError(
                "Polynomial fit covariance has an unexpected parameterization"
            )
        resistance = _as_float(
            fit_result.model.celsius_to_resistance(temperature),
            name="Fitted resistance",
        )
        x = temperature - fit_result.model.reference_temperature_c
        sensitivity_values = [1.0]
        for _ in range(len(fit_result.model.coefficients)):
            sensitivity_values.append(sensitivity_values[-1] * x)
        sensitivities = tuple(sensitivity_values)

    variance = _covariance_quadratic_form(
        sensitivities,
        covariance.covariance_matrix,
    )
    standard_uncertainty = math.sqrt(variance)
    if not math.isfinite(standard_uncertainty):
        raise ValueError(
            "Propagated fitted-model resistance uncertainty must remain finite"
        )

    return FitCovarianceResistancePropagation(
        temperature_c=temperature,
        resistance_ohms=resistance,
        parameter_covariance=covariance,
        parameter_sensitivity_vector=sensitivities,
        resistance_variance_ohms_squared=variance,
        resistance_standard_uncertainty_ohms=standard_uncertainty,
    )


# Source: JCGM (2008), JCGM 100:2008, sections 5.1-5.2, and
# Taylor & Kuyatt (1994), Appendix A; see docs/REFERENCES.md.
def propagate_fit_covariance_to_temperature(
    resistance_ohms: float,
    *,
    fit_result: CallendarVanDusenFitResult | IEC60751R0FitResult | PolynomialFitResult,
) -> FitCovarianceTemperaturePropagation:
    """Propagate fitted-parameter covariance into inferred temperature.

    The supplied resistance is first converted with the fitted model. At that
    inferred temperature, the retained resistance-parameter sensitivities are
    combined with the model's local inverse sensitivity using implicit
    differentiation::

        dT/dtheta = -(dR/dtheta) * (dT/dR)

    The full fitted-parameter covariance is then propagated as::

        u²(T) = J_T Cov(theta) J_T.T

    Unlike forward resistance propagation for the currently supported fit
    parameterizations, this inverse-temperature propagation is a first-order
    local linearization. The measured resistance is treated as fixed. Its own
    uncertainty, calibration reference-temperature uncertainty, sensor drift,
    tolerance, self-heating, and other effects are not included.
    """
    if not isinstance(
        fit_result,
        (CallendarVanDusenFitResult, IEC60751R0FitResult, PolynomialFitResult),
    ):
        raise TypeError(
            "fit_result must be CallendarVanDusenFitResult, IEC60751R0FitResult, "
            "or PolynomialFitResult"
        )

    resistance = _validate_positive_finite(
        resistance_ohms,
        name="Resistance",
    )
    temperature = _as_float(
        fit_result.model.resistance_to_celsius(resistance),
        name="Converted temperature",
    )
    if not math.isfinite(temperature):
        raise ValueError("Converted temperature must remain finite")

    resistance_propagation = propagate_fit_covariance_to_resistance(
        temperature,
        fit_result=fit_result,
    )
    temperature_sensitivity = _as_float(
        fit_result.model.temperature_sensitivity_celsius_per_ohm(temperature),
        name="Temperature sensitivity",
    )
    if not math.isfinite(temperature_sensitivity):
        raise ValueError("Temperature sensitivity must remain finite")

    parameter_sensitivities = tuple(
        -temperature_sensitivity * sensitivity
        for sensitivity in resistance_propagation.parameter_sensitivity_vector
    )
    if not all(math.isfinite(value) for value in parameter_sensitivities):
        raise ValueError(
            "Fitted-model temperature parameter sensitivities must remain finite"
        )

    variance = _covariance_quadratic_form(
        parameter_sensitivities,
        resistance_propagation.parameter_covariance.covariance_matrix,
    )
    standard_uncertainty = math.sqrt(variance)
    if not math.isfinite(standard_uncertainty):
        raise ValueError(
            "Propagated fitted-model temperature uncertainty must remain finite"
        )

    return FitCovarianceTemperaturePropagation(
        resistance_ohms=resistance,
        temperature_c=temperature,
        parameter_covariance=resistance_propagation.parameter_covariance,
        resistance_parameter_sensitivity_vector=(
            resistance_propagation.parameter_sensitivity_vector
        ),
        temperature_sensitivity_celsius_per_ohm=temperature_sensitivity,
        parameter_sensitivity_vector=parameter_sensitivities,
        temperature_variance_celsius_squared=variance,
        temperature_standard_uncertainty_c=standard_uncertainty,
    )


def _covariance_quadratic_form(
    sensitivity_vector: tuple[float, ...],
    covariance_matrix: tuple[tuple[float, ...], ...],
) -> float:
    size = len(sensitivity_vector)
    if (
        size == 0
        or len(covariance_matrix) != size
        or any(len(row) != size for row in covariance_matrix)
    ):
        raise ValueError("Parameter covariance dimensions do not match sensitivities")

    terms = tuple(
        sensitivity_vector[row]
        * covariance_matrix[row][column]
        * sensitivity_vector[column]
        for row in range(size)
        for column in range(size)
    )
    if not all(math.isfinite(value) for value in terms):
        raise ValueError(
            "Propagated fitted-model resistance variance must remain finite"
        )

    try:
        variance = math.fsum(terms)
    except OverflowError as error:
        raise ValueError(
            "Propagated fitted-model resistance variance must remain finite"
        ) from error
    if not math.isfinite(variance):
        raise ValueError(
            "Propagated fitted-model resistance variance must remain finite"
        )
    if variance < 0.0:
        try:
            absolute_sum = math.fsum(abs(value) for value in terms)
        except OverflowError as error:
            raise ValueError(
                "Propagated fitted-model resistance variance must remain finite"
            ) from error
        rounding_tolerance = (
            8.0 * len(terms) * math.ulp(absolute_sum) if absolute_sum > 0.0 else 0.0
        )
        if variance < -rounding_tolerance:
            raise ValueError(
                "Propagated fitted-model resistance variance must be non-negative"
            )
        variance = 0.0
    return variance


# Source: JCGM (2008), JCGM 100:2008, first-order sensitivity
# propagation; see docs/REFERENCES.md.
def propagate_resistance_uncertainty(
    resistance_ohms: float,
    resistance_standard_uncertainty_ohms: float,
    *,
    model: RTDUncertaintyModel,
) -> ResistanceUncertaintyPropagation:
    """Propagate resistance standard uncertainty into temperature.

    The measured resistance is first converted to temperature with ``model``.
    The standard uncertainty is then propagated with the first-order law of
    propagation using the exact local inverse sensitivity ``dT/dR`` provided
    by that same model::

        u(T) = |dT/dR| * u(R)

    This is a local linearization. For uncertainty intervals large enough that
    RTD nonlinearity is material, a higher-order or distribution-propagation
    method such as Monte Carlo analysis may be more appropriate.
    """
    resistance = _validate_positive_finite(
        resistance_ohms,
        name="Resistance",
    )
    resistance_standard_uncertainty = _validate_nonnegative_finite(
        resistance_standard_uncertainty_ohms,
        name="Resistance standard uncertainty",
    )

    temperature_c = _as_float(
        model.resistance_to_celsius(resistance),
        name="Converted temperature",
    )
    if not math.isfinite(temperature_c):
        raise ValueError("Converted temperature must remain finite")

    sensitivity = _as_float(
        model.temperature_sensitivity_celsius_per_ohm(temperature_c),
        name="Temperature sensitivity",
    )
    if not math.isfinite(sensitivity):
        raise ValueError("Temperature sensitivity must remain finite")

    temperature_standard_uncertainty = (
        abs(sensitivity) * resistance_standard_uncertainty
    )
    if not math.isfinite(temperature_standard_uncertainty):
        raise ValueError(
            "Propagated temperature standard uncertainty must remain finite"
        )

    return ResistanceUncertaintyPropagation(
        resistance_ohms=resistance,
        temperature_c=temperature_c,
        resistance_standard_uncertainty_ohms=(resistance_standard_uncertainty),
        temperature_sensitivity_celsius_per_ohm=sensitivity,
        temperature_standard_uncertainty_c=temperature_standard_uncertainty,
    )


def temperature_uncertainty_budget(
    resistance_ohms: float,
    resistance_standard_uncertainty_ohms: float,
    *,
    model: RTDUncertaintyModel,
    additional_components: Iterable[TemperatureUncertaintyComponent] = (),
    coverage_factor: float | None = None,
) -> TemperatureUncertaintyBudget:
    """Build an RTD temperature uncertainty budget from independent inputs.

    Args:
        resistance_ohms: Compensated RTD resistance in ohms.
        resistance_standard_uncertainty_ohms: Standard uncertainty associated
            with that resistance estimate, in ohms.
        model: RTD conversion model used for both the nominal temperature and
            the local ``dT/dR`` sensitivity.
        additional_components: Independent standard-uncertainty contributions
            already expressed in °C. The caller is responsible for evaluating
            each physical effect and for avoiding double counting.
        coverage_factor: Optional factor ``k`` used to report expanded
            uncertainty. If omitted, expanded uncertainty is not calculated.

    Returns:
        An immutable, inspectable uncertainty budget.

    Notes:
        The current implementation assumes the resistance contribution and all
        additional components are uncorrelated. It does not accept covariance
        terms, coefficient covariance, or an effective-degrees-of-freedom
        model. A tolerance limit may be included only after the caller has
        explicitly converted it to a standard uncertainty under a justified
        probability-distribution assumption.
    """
    resistance = propagate_resistance_uncertainty(
        resistance_ohms,
        resistance_standard_uncertainty_ohms,
        model=model,
    )

    components = tuple(additional_components)
    for component in components:
        if not isinstance(component, TemperatureUncertaintyComponent):
            raise TypeError(
                "Additional components must be TemperatureUncertaintyComponent "
                "instances"
            )

    combined = combine_independent_standard_uncertainties(
        resistance.temperature_standard_uncertainty_c,
        *(component.standard_uncertainty_c for component in components),
    )

    if coverage_factor is None:
        validated_coverage_factor = None
        expanded = None
    else:
        validated_coverage_factor = _validate_positive_finite(
            coverage_factor,
            name="Coverage factor",
        )
        expanded = expanded_uncertainty(
            combined,
            coverage_factor=validated_coverage_factor,
        )

    return TemperatureUncertaintyBudget(
        resistance=resistance,
        additional_components=components,
        combined_standard_uncertainty_c=combined,
        coverage_factor=validated_coverage_factor,
        expanded_uncertainty_c=expanded,
    )


def _validate_nonnegative_finite(value: float, *, name: str) -> float:
    number = _as_float(value, name=name)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if number < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return number


def _validate_positive_finite(value: float, *, name: str) -> float:
    number = _as_float(value, name=name)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if number <= 0.0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def _validate_nonempty_text(value: str, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must not be empty")
    return text


def _validate_optional_text(value: str | None, *, name: str) -> str | None:
    if value is None:
        return None
    return _validate_nonempty_text(value, name=name)
