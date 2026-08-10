# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Measurement-uncertainty helpers for RTD temperature conversion.

The low-level helpers in this module follow the measurement-uncertainty
conventions used by the GUM/JCGM framework and NIST Technical Note 1297.
They operate on already-evaluated uncertainty quantities; they do not decide
which physical effects belong in a particular RTD uncertainty budget.

A tolerance limit is not automatically a standard uncertainty. If a bounded
specification is converted with :func:`standard_uncertainty_from_bound`, the
selected probability distribution is an explicit modeling assumption made by
the caller.

The RTD-specific helpers use first-order propagation through the exact local
Callendar-Van Dusen sensitivity. They preserve the resistance contribution and
additional temperature-domain components separately so an uncertainty budget
remains inspectable rather than collapsing immediately to one number.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, Protocol

from ._validation import as_float as _as_float

__all__ = [
    "BoundDistribution",
    "EvaluationMethod",
    "RTDUncertaintyModel",
    "ResistanceUncertaintyPropagation",
    "TemperatureUncertaintyBudget",
    "TemperatureUncertaintyComponent",
    "combine_independent_standard_uncertainties",
    "expanded_uncertainty",
    "propagate_resistance_uncertainty",
    "standard_uncertainty_from_bound",
    "standard_uncertainty_from_expanded",
    "temperature_uncertainty_budget",
]


type BoundDistribution = Literal["rectangular", "triangular"]
type EvaluationMethod = Literal["A", "B"]


class RTDUncertaintyModel(Protocol):
    """Structural interface required for RTD uncertainty propagation.

    The built-in :mod:`rtd.pt100` and :mod:`rtd.pt1000` modules and the public
    configurable model classes all satisfy this protocol. Third-party models
    can participate without inheriting from a package-specific base class if
    they provide the same conversion and local-sensitivity operations.
    """

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        """Convert resistance in ohms to temperature in Celsius."""
        ...

    def temperature_sensitivity_celsius_per_ohm(
        self,
        temperature_c: float,
    ) -> float:
        """Return local inverse sensitivity dT/dR in °C/ohm."""
        ...


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
        raise ValueError(
            "Distribution must be 'rectangular' or 'triangular'"
        )

    return bound / divisor


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
        resistance_standard_uncertainty_ohms=(
            resistance_standard_uncertainty
        ),
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
