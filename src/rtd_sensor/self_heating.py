# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""RTD self-heating analysis and two-current zero-power extrapolation.

The two-current method implemented here follows resistance-thermometry guidance
that models measured resistance as linear in measurement-current squared under a
stable thermal condition. It analyzes caller-supplied current/resistance evidence
and can interpret the result through an explicitly supplied RTD model; it does not
control excitation current or acquisition hardware.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from ._protocols import RTDModel as _RTDModel
from ._validation import as_float as _as_float

__all__ = [
    "SelfHeatingCoefficientResult",
    "SelfHeatingCoefficientUncertaintyResult",
    "SelfHeatingExperimentContext",
    "SelfHeatingObservation",
    "ZeroPowerExtrapolationAssessment",
    "ZeroPowerExtrapolationWarning",
    "ZeroPowerResistanceFitEvidence",
    "ZeroPowerResistanceFitResult",
    "ZeroPowerResistanceFitTemperatureResult",
    "ZeroPowerResistanceFitTemperatureUncertaintyResult",
    "ZeroPowerResistanceFitUncertaintyResult",
    "TwoCurrentInputCorrelationMatrix",
    "TwoCurrentInputStandardUncertainties",
    "TwoCurrentSelfHeatingTemperatureResult",
    "TwoCurrentSelfHeatingTemperatureUncertaintyResult",
    "TwoCurrentZeroPowerEvidence",
    "TwoCurrentZeroPowerResult",
    "TwoCurrentZeroPowerUncertaintyResult",
    "assess_zero_power_extrapolation",
    "estimate_zero_power_fit_uncertainty",
    "evaluate_self_heating_coefficient",
    "evaluate_two_current_temperatures",
    "evaluate_zero_power_fit_temperatures",
    "fit_zero_power_resistance",
    "extrapolate_zero_power_resistance",
    "propagate_self_heating_coefficient_uncertainty",
    "propagate_two_current_temperature_uncertainty",
    "propagate_two_current_zero_power_uncertainty",
    "propagate_zero_power_fit_temperature_uncertainty",
]

_TwoCurrentMethod = Literal["linear_resistance_vs_current_squared"]
_ZeroPowerFitMethod = Literal[
    "ordinary_least_squares_resistance_vs_current_squared",
    "inverse_variance_weighted_least_squares_resistance_vs_current_squared",
]
_ZeroPowerFitUncertaintyMethod = Literal[
    "residual_variance_scaled_least_squares",
    "resistance_standard_uncertainties",
]
_ZeroPowerFitTemperatureUncertaintyMethod = Literal[
    "first_order_fit_parameter_covariance"
]
_SelfHeatingCoefficientMethod = Literal[
    "least_squares_temperature_rise_vs_fitted_power_through_origin"
]
_SelfHeatingCoefficientUncertaintyMethod = Literal[
    "first_order_fit_parameter_covariance"
]
_TwoCurrentUncertaintyMethod = Literal[
    "first_order_independent_inputs",
    "first_order_correlated_inputs",
]
_ZeroPowerExtrapolationWarningCode = Literal[
    "two_current_exact_line_no_residual_test",
    "only_two_distinct_current_levels",
    "no_repeated_current_levels",
    "nonpositive_resistance_slope",
]
_ZERO_POWER_EXTRAPOLATION_WARNING_MESSAGES: dict[
    _ZeroPowerExtrapolationWarningCode, str
] = {
    "two_current_exact_line_no_residual_test": (
        "Two observations exactly determine the zero-power line, so residual scatter "
        "or departures from linearity cannot be assessed from this result alone."
    ),
    "only_two_distinct_current_levels": (
        "The fit contains only two distinct current levels. Repeated observations can "
        "show scatter at those levels, but cannot test departure from a straight line "
        "across three or more current levels."
    ),
    "no_repeated_current_levels": (
        "No current level is repeated, so the retained observations cannot assess "
        "within-level repeatability. Repeated cycles are particularly useful when "
        "thermal drift is suspected."
    ),
    "nonpositive_resistance_slope": (
        "The retained resistance-versus-current-squared slope is zero or negative, "
        "so the observations do not show the positive resistance rise expected for "
        "ordinary self-heating."
    ),
}
_TWO_CURRENT_INPUT_PARAMETER_NAMES = (
    "low_current_a",
    "low_resistance_ohms",
    "high_current_a",
    "high_resistance_ohms",
)


@dataclass(frozen=True, slots=True)
class SelfHeatingObservation:
    """One steady-state current/resistance observation for self-heating analysis.

    ``measurement_current_a`` is the positive magnitude of the measurement
    current in amperes. ``resistance_ohms`` is the corresponding measured RTD
    resistance under the same thermal condition.

    The derived ``dissipated_power_w`` value is the observation-level electrical
    power ``I**2 * R``. The two-current extrapolation itself follows the standard
    linear model in ``I**2`` rather than fitting against this derived power value.
    """

    measurement_current_a: float
    resistance_ohms: float

    def __post_init__(self) -> None:
        current = _as_float(self.measurement_current_a, name="Measurement current")
        resistance = _as_float(self.resistance_ohms, name="Resistance")

        if not math.isfinite(current):
            raise ValueError("Measurement current must be finite")
        if current <= 0.0:
            raise ValueError("Measurement current must be greater than zero")
        if not math.isfinite(resistance):
            raise ValueError("Resistance must be finite")
        if resistance <= 0.0:
            raise ValueError("Resistance must be greater than zero")

        current_squared = current * current
        if not math.isfinite(current_squared):
            raise ValueError("Measurement current squared must be finite")
        if current_squared <= 0.0:
            raise ValueError("Measurement current squared must be greater than zero")
        dissipated_power = current_squared * resistance
        if not math.isfinite(dissipated_power):
            raise ValueError("Dissipated power must be finite")
        if dissipated_power <= 0.0:
            raise ValueError("Dissipated power must be greater than zero")

        object.__setattr__(self, "measurement_current_a", current)
        object.__setattr__(self, "resistance_ohms", resistance)

    @property
    def current_squared_a2(self) -> float:
        """Return measurement-current squared in A²."""
        return self.measurement_current_a * self.measurement_current_a

    @property
    def dissipated_power_w(self) -> float:
        """Return observation-level electrical power ``I²R`` in watts."""
        return self.current_squared_a2 * self.resistance_ohms


@dataclass(frozen=True, slots=True)
class SelfHeatingExperimentContext:
    """Non-behavioral thermal-environment provenance for self-heating evidence.

    The fields describe the conditions under which current/resistance observations
    were made. They do not alter the resistance fit or RTD model. At least one of
    ``medium``, ``flow_condition``, ``mounting``, or ``setup`` must be supplied so
    the context identifies a meaningful thermal environment rather than an empty
    metadata shell.
    """

    medium: str | None = None
    flow_condition: str | None = None
    mounting: str | None = None
    setup: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        for field_name, display_name in (
            ("medium", "Medium"),
            ("flow_condition", "Flow condition"),
            ("mounting", "Mounting"),
            ("setup", "Setup"),
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

        if not any(
            (
                self.medium,
                self.flow_condition,
                self.mounting,
                self.setup,
            )
        ):
            raise ValueError(
                "Self-heating context requires medium, flow condition, mounting, "
                "or setup"
            )


@dataclass(frozen=True, slots=True)
class TwoCurrentZeroPowerEvidence:
    """Immutable evidence supporting one two-current zero-power extrapolation.

    The observations are normalized into increasing-current order regardless of
    the order supplied to :func:`extrapolate_zero_power_resistance`. With only two
    current levels there are no residual degrees of freedom, so this evidence does
    not by itself establish that the external thermal condition was stable.
    """

    low_current_observation: SelfHeatingObservation
    high_current_observation: SelfHeatingObservation
    method: _TwoCurrentMethod = field(
        init=False,
        default="linear_resistance_vs_current_squared",
    )

    def __post_init__(self) -> None:
        if not isinstance(self.low_current_observation, SelfHeatingObservation):
            raise TypeError("low_current_observation must be a SelfHeatingObservation")
        if not isinstance(self.high_current_observation, SelfHeatingObservation):
            raise TypeError("high_current_observation must be a SelfHeatingObservation")
        if (
            self.high_current_observation.measurement_current_a
            <= self.low_current_observation.measurement_current_a
        ):
            raise ValueError(
                "Two-current evidence requires high current to be greater "
                "than low current"
            )
        if self.current_squared_change_a2 <= 0.0:
            raise ValueError(
                "Two-current evidence requires numerically distinct "
                "current-squared levels"
            )
        if not math.isfinite(self.resistance_slope_ohms_per_a2):
            raise ValueError("Two-current evidence requires a finite resistance slope")

    @property
    def current_ratio(self) -> float:
        """Return high-current magnitude divided by low-current magnitude."""
        return (
            self.high_current_observation.measurement_current_a
            / self.low_current_observation.measurement_current_a
        )

    @property
    def current_squared_change_a2(self) -> float:
        """Return ``I_high² - I_low²`` in A²."""
        return (
            self.high_current_observation.current_squared_a2
            - self.low_current_observation.current_squared_a2
        )

    @property
    def resistance_change_ohms(self) -> float:
        """Return ``R_high - R_low`` in ohms."""
        return (
            self.high_current_observation.resistance_ohms
            - self.low_current_observation.resistance_ohms
        )

    @property
    def resistance_slope_ohms_per_a2(self) -> float:
        """Return the two-point slope ``dR/d(I²)`` in ohms/A²."""
        return self.resistance_change_ohms / self.current_squared_change_a2

    @property
    def residual_degrees_of_freedom(self) -> int:
        """Return zero because two observations exactly define a two-parameter line."""
        return 0


@dataclass(frozen=True, slots=True)
class TwoCurrentZeroPowerResult:
    """Two-current zero-power resistance result with retained input evidence."""

    zero_power_resistance_ohms: float
    evidence: TwoCurrentZeroPowerEvidence

    def __post_init__(self) -> None:
        resistance = _as_float(
            self.zero_power_resistance_ohms,
            name="Zero-power resistance",
        )
        if not math.isfinite(resistance):
            raise ValueError("Zero-power resistance must be finite")
        if resistance <= 0.0:
            raise ValueError("Zero-power resistance must be greater than zero")
        if not isinstance(self.evidence, TwoCurrentZeroPowerEvidence):
            raise TypeError("evidence must be a TwoCurrentZeroPowerEvidence")

        expected = _zero_power_resistance_from_evidence(self.evidence)
        tolerance = 8.0 * max(math.ulp(resistance), math.ulp(expected))
        if not math.isclose(resistance, expected, rel_tol=0.0, abs_tol=tolerance):
            raise ValueError(
                "Zero-power resistance must be consistent with retained evidence"
            )
        object.__setattr__(self, "zero_power_resistance_ohms", resistance)

    @property
    def low_current_resistance_rise_ohms(self) -> float:
        """Return observed low-current resistance minus zero-power resistance."""
        return (
            self.evidence.low_current_observation.resistance_ohms
            - self.zero_power_resistance_ohms
        )

    @property
    def high_current_resistance_rise_ohms(self) -> float:
        """Return observed high-current resistance minus zero-power resistance."""
        return (
            self.evidence.high_current_observation.resistance_ohms
            - self.zero_power_resistance_ohms
        )


@dataclass(frozen=True, slots=True)
class ZeroPowerResistanceFitEvidence:
    """Observations and residual diagnostics for a 3+ point zero-power fit.

    Observations remain in caller-supplied order so repeated current cycles and
    residual sequences remain inspectable. At least three observations and two
    numerically distinct current-squared levels are required. Residuals are
    ``observed resistance - fitted resistance`` in ohms.

    Optional absolute resistance standard uncertainties select inverse-variance
    weighted least squares and are retained with the evidence. Residual diagnostics
    can reveal scatter or departures from the fitted linear ``R``-versus-``I²``
    relationship, but they do not by themselves prove that the external temperature
    was stable or that a physical self-heating correction is valid.
    """

    observations: tuple[SelfHeatingObservation, ...]
    residuals_ohms: tuple[float, ...]
    context: SelfHeatingExperimentContext | None = None
    resistance_standard_uncertainties_ohms: tuple[float, ...] | None = None
    method: _ZeroPowerFitMethod = field(init=False)

    def __post_init__(self) -> None:
        observations = tuple(self.observations)
        if len(observations) < 3:
            raise ValueError("Zero-power fitting requires at least three observations")
        if not all(
            isinstance(observation, SelfHeatingObservation)
            for observation in observations
        ):
            raise TypeError("Observations must be SelfHeatingObservation values")

        residuals = tuple(
            _as_float(residual, name="Fit residual") for residual in self.residuals_ohms
        )
        if len(residuals) != len(observations):
            raise ValueError("Fit residual count must match observation count")
        if not all(math.isfinite(residual) for residual in residuals):
            raise ValueError("Fit residuals must be finite")
        if self.context is not None and not isinstance(
            self.context, SelfHeatingExperimentContext
        ):
            raise TypeError("context must be a SelfHeatingExperimentContext or None")

        resistance_uncertainties = _validated_fit_resistance_uncertainties(
            self.resistance_standard_uncertainties_ohms,
            observation_count=len(observations),
        )
        method: _ZeroPowerFitMethod = (
            "ordinary_least_squares_resistance_vs_current_squared"
            if resistance_uncertainties is None
            else "inverse_variance_weighted_least_squares_resistance_vs_current_squared"
        )

        distinct_current_squared = {
            observation.current_squared_a2 for observation in observations
        }
        if len(distinct_current_squared) < 2:
            raise ValueError(
                "Zero-power fitting requires at least two distinct current levels"
            )

        _, _, expected_residuals = _fit_zero_power_line(
            observations,
            resistance_standard_uncertainties_ohms=resistance_uncertainties,
        )
        for residual, expected_residual in zip(
            residuals,
            expected_residuals,
            strict=True,
        ):
            tolerance = 16.0 * max(
                math.ulp(residual),
                math.ulp(expected_residual),
            )
            if not math.isclose(
                residual,
                expected_residual,
                rel_tol=0.0,
                abs_tol=tolerance,
            ):
                raise ValueError(
                    "Fit residuals must be consistent with retained observations"
                )

        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "residuals_ohms", residuals)
        object.__setattr__(
            self,
            "resistance_standard_uncertainties_ohms",
            resistance_uncertainties,
        )
        object.__setattr__(self, "method", method)

    @property
    def effective_weights(self) -> tuple[float, ...] | None:
        """Return normalized inverse-variance weights when uncertainties exist."""
        uncertainties = self.resistance_standard_uncertainties_ohms
        if uncertainties is None:
            return None
        minimum_uncertainty = min(uncertainties)
        weights = tuple(
            (minimum_uncertainty / uncertainty) ** 2 for uncertainty in uncertainties
        )
        if not all(math.isfinite(weight) and weight > 0.0 for weight in weights):
            raise ValueError(
                "Resistance standard uncertainties have an unrepresentable "
                "inverse-variance weighting range"
            )
        return weights

    @property
    def chi_squared(self) -> float | None:
        """Return resistance-domain chi-square for absolute uncertainty weighting."""
        uncertainties = self.resistance_standard_uncertainties_ohms
        if uncertainties is None:
            return None
        value = math.fsum(
            (residual / uncertainty) ** 2
            for residual, uncertainty in zip(
                self.residuals_ohms,
                uncertainties,
                strict=True,
            )
        )
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("Zero-power fit chi-square must remain finite")
        return value

    @property
    def reduced_chi_squared(self) -> float | None:
        """Return chi-square divided by positive residual degrees of freedom."""
        chi_squared = self.chi_squared
        if chi_squared is None:
            return None
        return chi_squared / self.residual_degrees_of_freedom

    @property
    def weighted_rms_residual_ohms(self) -> float | None:
        """Return normalized-weight RMS residual when uncertainty weights exist."""
        weights = self.effective_weights
        if weights is None:
            return None
        weighted_sum = math.fsum(
            weight * residual * residual
            for weight, residual in zip(weights, self.residuals_ohms, strict=True)
        )
        total_weight = math.fsum(weights)
        value = math.sqrt(weighted_sum / total_weight)
        if not math.isfinite(value):
            raise ValueError("Weighted RMS residual must remain finite")
        return value

    @property
    def observation_count(self) -> int:
        """Return the number of retained observations."""
        return len(self.observations)

    @property
    def fitted_parameter_count(self) -> int:
        """Return two for the fitted zero-power intercept and current-squared slope."""
        return 2

    @property
    def residual_degrees_of_freedom(self) -> int:
        """Return observation count minus the two fitted line parameters."""
        return self.observation_count - self.fitted_parameter_count

    @property
    def distinct_current_count(self) -> int:
        """Return the number of numerically distinct current-squared levels."""
        return len(
            {observation.current_squared_a2 for observation in self.observations}
        )

    @property
    def minimum_measurement_current_a(self) -> float:
        """Return the smallest retained measurement-current magnitude."""
        return min(
            observation.measurement_current_a for observation in self.observations
        )

    @property
    def maximum_measurement_current_a(self) -> float:
        """Return the largest retained measurement-current magnitude."""
        return max(
            observation.measurement_current_a for observation in self.observations
        )

    @property
    def current_squared_span_a2(self) -> float:
        """Return the retained maximum minus minimum current squared."""
        values = tuple(
            observation.current_squared_a2 for observation in self.observations
        )
        return max(values) - min(values)

    @property
    def rms_residual_ohms(self) -> float:
        """Return descriptive RMS residual using the observation count denominator."""
        return math.hypot(*self.residuals_ohms) / math.sqrt(self.observation_count)

    @property
    def max_absolute_residual_ohms(self) -> float:
        """Return the largest absolute retained residual in ohms."""
        return max(abs(residual) for residual in self.residuals_ohms)

    @property
    def residual_standard_deviation_ohms(self) -> float:
        """Return ``sqrt(SSE / residual_degrees_of_freedom)`` in ohms."""
        return math.hypot(*self.residuals_ohms) / math.sqrt(
            self.residual_degrees_of_freedom
        )

    @property
    def fitted_resistances_ohms(self) -> tuple[float, ...]:
        """Return fitted resistance corresponding to each retained observation."""
        return tuple(
            observation.resistance_ohms - residual
            for observation, residual in zip(
                self.observations,
                self.residuals_ohms,
                strict=True,
            )
        )


@dataclass(frozen=True, slots=True)
class ZeroPowerResistanceFitResult:
    """3+ observation zero-power resistance fit and retained evidence."""

    zero_power_resistance_ohms: float
    resistance_slope_ohms_per_a2: float
    evidence: ZeroPowerResistanceFitEvidence

    def __post_init__(self) -> None:
        resistance = _as_float(
            self.zero_power_resistance_ohms,
            name="Zero-power resistance",
        )
        slope = _as_float(
            self.resistance_slope_ohms_per_a2,
            name="Resistance slope",
        )
        if not math.isfinite(resistance):
            raise ValueError("Zero-power resistance must be finite")
        if resistance <= 0.0:
            raise ValueError("Zero-power resistance must be greater than zero")
        if not math.isfinite(slope):
            raise ValueError("Resistance slope must be finite")
        if not isinstance(self.evidence, ZeroPowerResistanceFitEvidence):
            raise TypeError("evidence must be a ZeroPowerResistanceFitEvidence")

        expected_resistance, expected_slope, expected_residuals = _fit_zero_power_line(
            self.evidence.observations,
            resistance_standard_uncertainties_ohms=(
                self.evidence.resistance_standard_uncertainties_ohms
            ),
        )
        resistance_tolerance = 16.0 * max(
            math.ulp(resistance),
            math.ulp(expected_resistance),
        )
        slope_tolerance = 16.0 * max(math.ulp(slope), math.ulp(expected_slope))
        if not math.isclose(
            resistance,
            expected_resistance,
            rel_tol=0.0,
            abs_tol=resistance_tolerance,
        ):
            raise ValueError(
                "Zero-power resistance must be consistent with retained fit evidence"
            )
        if not math.isclose(
            slope,
            expected_slope,
            rel_tol=0.0,
            abs_tol=slope_tolerance,
        ):
            raise ValueError(
                "Resistance slope must be consistent with retained fit evidence"
            )
        for residual, expected_residual in zip(
            self.evidence.residuals_ohms,
            expected_residuals,
            strict=True,
        ):
            tolerance = 16.0 * max(
                math.ulp(residual),
                math.ulp(expected_residual),
            )
            if not math.isclose(
                residual,
                expected_residual,
                rel_tol=0.0,
                abs_tol=tolerance,
            ):
                raise ValueError(
                    "Fit residuals must be consistent with retained observations"
                )

        object.__setattr__(self, "zero_power_resistance_ohms", resistance)
        object.__setattr__(self, "resistance_slope_ohms_per_a2", slope)

    @property
    def resistance_slope_direction(self) -> Literal["positive", "zero", "negative"]:
        """Return the sign of the fitted resistance-versus-current-squared slope."""
        if self.resistance_slope_ohms_per_a2 > 0.0:
            return "positive"
        if self.resistance_slope_ohms_per_a2 < 0.0:
            return "negative"
        return "zero"


@dataclass(frozen=True, slots=True)
class ZeroPowerExtrapolationWarning:
    """One structured warning about support for a zero-power extrapolation.

    Warning codes describe objective limitations of the supplied evidence. They do
    not apply experiment-independent residual or conditioning thresholds.
    """

    code: _ZeroPowerExtrapolationWarningCode

    def __post_init__(self) -> None:
        if self.code not in _ZERO_POWER_EXTRAPOLATION_WARNING_MESSAGES:
            raise ValueError(
                f"Unknown zero-power extrapolation warning code: {self.code!r}"
            )

    @property
    def message(self) -> str:
        """Return the human-readable explanation for this warning code."""
        return _ZERO_POWER_EXTRAPOLATION_WARNING_MESSAGES[self.code]


@dataclass(frozen=True, slots=True)
class ZeroPowerExtrapolationAssessment:
    """Threshold-free evidence assessment for one zero-power extrapolation.

    The assessment reports structural evidence limitations and useful current-geometry
    metrics. It does not prove that the external temperature was stable, infer thermal
    drift, or apply universal residual/conditioning acceptance thresholds.
    """

    result: TwoCurrentZeroPowerResult | ZeroPowerResistanceFitResult

    def __post_init__(self) -> None:
        if not isinstance(
            self.result,
            (TwoCurrentZeroPowerResult, ZeroPowerResistanceFitResult),
        ):
            raise TypeError(
                "result must be a TwoCurrentZeroPowerResult or "
                "ZeroPowerResistanceFitResult"
            )

    @property
    def observations(self) -> tuple[SelfHeatingObservation, ...]:
        """Return the retained observations in their evidence order."""
        if isinstance(self.result, TwoCurrentZeroPowerResult):
            return (
                self.result.evidence.low_current_observation,
                self.result.evidence.high_current_observation,
            )
        return self.result.evidence.observations

    @property
    def observation_count(self) -> int:
        """Return the number of retained current/resistance observations."""
        return len(self.observations)

    @property
    def distinct_current_count(self) -> int:
        """Return the number of numerically distinct current-squared levels."""
        return len(
            {observation.current_squared_a2 for observation in self.observations}
        )

    @property
    def repeated_current_level_count(self) -> int:
        """Return how many distinct current levels occur more than once."""
        counts: dict[float, int] = {}
        for observation in self.observations:
            current_squared = observation.current_squared_a2
            counts[current_squared] = counts.get(current_squared, 0) + 1
        return sum(count > 1 for count in counts.values())

    @property
    def residual_degrees_of_freedom(self) -> int:
        """Return residual degrees of freedom available to the retained fit."""
        if isinstance(self.result, TwoCurrentZeroPowerResult):
            return self.result.evidence.residual_degrees_of_freedom
        return self.result.evidence.residual_degrees_of_freedom

    @property
    def minimum_measurement_current_a(self) -> float:
        """Return the smallest retained measurement-current magnitude."""
        return min(
            observation.measurement_current_a for observation in self.observations
        )

    @property
    def maximum_measurement_current_a(self) -> float:
        """Return the largest retained measurement-current magnitude."""
        return max(
            observation.measurement_current_a for observation in self.observations
        )

    @property
    def minimum_to_maximum_current_ratio(self) -> float:
        """Return minimum divided by maximum retained measurement current."""
        return self.minimum_measurement_current_a / self.maximum_measurement_current_a

    @property
    def zero_power_extrapolation_distance_in_current_squared_spans(self) -> float:
        """Return zero-current extrapolation distance in observed I²-span units.

        The value is ``min(I²) / (max(I²) - min(I²))``. It is a descriptive
        geometry/conditioning metric only; the API intentionally defines no universal
        acceptable maximum.
        """
        current_squared_values = tuple(
            observation.current_squared_a2 for observation in self.observations
        )
        minimum = min(current_squared_values)
        span = max(current_squared_values) - minimum
        return minimum / span

    @property
    def resistance_slope_direction(self) -> Literal["positive", "zero", "negative"]:
        """Return the sign of the retained R-versus-I² slope."""
        if isinstance(self.result, TwoCurrentZeroPowerResult):
            slope = self.result.evidence.resistance_slope_ohms_per_a2
        else:
            slope = self.result.resistance_slope_ohms_per_a2
        if slope > 0.0:
            return "positive"
        if slope < 0.0:
            return "negative"
        return "zero"

    @property
    def supports_residual_consistency_assessment(self) -> bool:
        """Return whether residual scatter is available for inspection."""
        return self.residual_degrees_of_freedom > 0

    @property
    def supports_linearity_assessment(self) -> bool:
        """Return whether at least three distinct current levels test line shape."""
        return self.distinct_current_count >= 3

    @property
    def supports_repeated_level_assessment(self) -> bool:
        """Return whether at least one current level has repeated observations."""
        return self.repeated_current_level_count > 0

    @property
    def warnings(self) -> tuple[ZeroPowerExtrapolationWarning, ...]:
        """Return structured evidence-limit warnings in deterministic order."""
        warning_codes: list[_ZeroPowerExtrapolationWarningCode] = []
        if isinstance(self.result, TwoCurrentZeroPowerResult):
            warning_codes.append("two_current_exact_line_no_residual_test")
        elif self.distinct_current_count == 2:
            warning_codes.append("only_two_distinct_current_levels")
        elif self.repeated_current_level_count == 0:
            warning_codes.append("no_repeated_current_levels")

        if self.resistance_slope_direction != "positive":
            warning_codes.append("nonpositive_resistance_slope")

        return tuple(ZeroPowerExtrapolationWarning(code) for code in warning_codes)

    @property
    def warning_codes(self) -> tuple[_ZeroPowerExtrapolationWarningCode, ...]:
        """Return stable warning codes without the explanatory text."""
        return tuple(warning.code for warning in self.warnings)

    @property
    def has_warnings(self) -> bool:
        """Return whether this assessment contains any structural warning."""
        return bool(self.warnings)


@dataclass(frozen=True, slots=True)
class ZeroPowerResistanceFitUncertaintyResult:
    """Parameter uncertainty for one 3+ observation zero-power fit.

    For an unweighted fit, current-squared coordinates are treated as fixed/exact
    and resistance-domain errors are assumed independent, zero-mean, and to share
    an unknown common variance estimated from residual scatter. For an
    inverse-variance weighted fit, every retained resistance standard uncertainty
    is treated as an absolute independent response uncertainty, so parameter
    covariance comes directly from those supplied uncertainties and is not rescaled
    by the observed residual scatter.

    Measurement-current uncertainty, correlated observation errors, and fitted
    RTD-model covariance remain outside this result.
    """

    fit_result: ZeroPowerResistanceFitResult
    residual_variance_ohms_squared: float | None = field(init=False)
    parameter_covariance_matrix: tuple[
        tuple[float, float],
        tuple[float, float],
    ] = field(init=False)
    method: _ZeroPowerFitUncertaintyMethod = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.fit_result, ZeroPowerResistanceFitResult):
            raise TypeError("fit_result must be a ZeroPowerResistanceFitResult")

        residual_variance, covariance, method = _zero_power_fit_parameter_covariance(
            self.fit_result
        )
        object.__setattr__(
            self,
            "residual_variance_ohms_squared",
            residual_variance,
        )
        object.__setattr__(self, "parameter_covariance_matrix", covariance)
        object.__setattr__(self, "method", method)

    @property
    def parameter_names(self) -> tuple[str, str]:
        """Return covariance-matrix parameter order."""
        return (
            "zero_power_resistance_ohms",
            "resistance_slope_ohms_per_a2",
        )

    @property
    def zero_power_resistance_variance_ohms_squared(self) -> float:
        """Return fitted zero-power-resistance variance."""
        return self.parameter_covariance_matrix[0][0]

    @property
    def zero_power_resistance_standard_uncertainty_ohms(self) -> float:
        """Return fitted zero-power-resistance standard uncertainty."""
        return math.sqrt(self.zero_power_resistance_variance_ohms_squared)

    @property
    def resistance_slope_variance_ohms_squared_per_a4(self) -> float:
        """Return fitted ``dR/d(I²)`` slope variance."""
        return self.parameter_covariance_matrix[1][1]

    @property
    def resistance_slope_standard_uncertainty_ohms_per_a2(self) -> float:
        """Return fitted ``dR/d(I²)`` slope standard uncertainty."""
        return math.sqrt(self.resistance_slope_variance_ohms_squared_per_a4)

    @property
    def zero_power_resistance_slope_covariance_ohms_squared_per_a2(self) -> float:
        """Return covariance between fitted intercept and slope."""
        return self.parameter_covariance_matrix[0][1]


@dataclass(frozen=True, slots=True)
class ZeroPowerResistanceFitTemperatureResult:
    """Model-based temperatures and powers for one multi-observation zero-power fit.

    The exact supplied RTD model is applied to the fitted zero-power resistance,
    every observed resistance, and every resistance predicted by the retained
    ``R = R0 + k*I²`` fit at the sampled current levels. Caller observation order is
    preserved throughout.

    Observed and fitted dissipated powers are reported separately. The observed
    values use the measured resistance in ``I²R``; fitted values use the fitted
    resistance at the same current coordinate. These quantities remain evidence
    about the experiment and are not, by themselves, a setup-independent
    self-heating coefficient or dissipation constant.
    """

    fit_result: ZeroPowerResistanceFitResult
    model: _RTDModel = field(repr=False, compare=False)
    zero_power_temperature_c: float = field(init=False)
    observed_temperatures_c: tuple[float, ...] = field(init=False)
    fitted_temperatures_c: tuple[float, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.fit_result, ZeroPowerResistanceFitResult):
            raise TypeError("fit_result must be a ZeroPowerResistanceFitResult")

        evidence = self.fit_result.evidence
        zero_power_temperature = _converted_temperature_c(
            self.model,
            self.fit_result.zero_power_resistance_ohms,
            name="Zero-power fit temperature",
        )
        observed_temperatures = tuple(
            _converted_temperature_c(
                self.model,
                observation.resistance_ohms,
                name="Observed fit temperature",
            )
            for observation in evidence.observations
        )
        fitted_temperatures = tuple(
            _converted_temperature_c(
                self.model,
                resistance,
                name="Fitted self-heating temperature",
            )
            for resistance in evidence.fitted_resistances_ohms
        )

        object.__setattr__(self, "zero_power_temperature_c", zero_power_temperature)
        object.__setattr__(self, "observed_temperatures_c", observed_temperatures)
        object.__setattr__(self, "fitted_temperatures_c", fitted_temperatures)

    @property
    def observed_temperature_rises_c(self) -> tuple[float, ...]:
        """Return observed temperatures minus fitted zero-power temperature."""
        return tuple(
            temperature - self.zero_power_temperature_c
            for temperature in self.observed_temperatures_c
        )

    @property
    def fitted_temperature_rises_c(self) -> tuple[float, ...]:
        """Return fitted temperatures minus fitted zero-power temperature."""
        return tuple(
            temperature - self.zero_power_temperature_c
            for temperature in self.fitted_temperatures_c
        )

    @property
    def temperature_residuals_c(self) -> tuple[float, ...]:
        """Return observed minus fitted temperatures in caller observation order."""
        return tuple(
            observed - fitted
            for observed, fitted in zip(
                self.observed_temperatures_c,
                self.fitted_temperatures_c,
                strict=True,
            )
        )

    @property
    def observed_dissipated_powers_w(self) -> tuple[float, ...]:
        """Return measured observation powers ``I²R_observed`` in watts."""
        return tuple(
            observation.dissipated_power_w
            for observation in self.fit_result.evidence.observations
        )

    @property
    def fitted_dissipated_powers_w(self) -> tuple[float, ...]:
        """Return fitted powers ``I²R_fitted`` at each sampled current."""
        powers = tuple(
            observation.current_squared_a2 * resistance
            for observation, resistance in zip(
                self.fit_result.evidence.observations,
                self.fit_result.evidence.fitted_resistances_ohms,
                strict=True,
            )
        )
        if not all(math.isfinite(power) and power > 0.0 for power in powers):
            raise ValueError("Fitted dissipated powers must be positive and finite")
        return powers


@dataclass(frozen=True, slots=True)
class ZeroPowerResistanceFitTemperatureUncertaintyResult:
    """Fit-covariance uncertainty for multi-observation temperatures and rises.

    The propagation uses the fitted-parameter order
    ``(zero_power_resistance_ohms, resistance_slope_ohms_per_a2)`` and the full
    retained 2x2 covariance matrix. Current-squared coordinates are treated as
    fixed/exact, matching the underlying ordinary-least-squares covariance model.

    Only uncertainty from the residual-scatter fit covariance is included. The
    supplied RTD model is treated as fixed; model-parameter covariance, current
    uncertainty, resistance measurement uncertainty beyond the residual model, and
    correlated experimental effects remain separate.
    """

    temperature_result: ZeroPowerResistanceFitTemperatureResult
    fit_uncertainty: ZeroPowerResistanceFitUncertaintyResult
    zero_power_temperature_parameter_sensitivity_vector: tuple[float, float] = field(
        init=False
    )
    fitted_temperature_parameter_sensitivity_vectors: tuple[
        tuple[float, float], ...
    ] = field(init=False)
    fitted_temperature_rise_parameter_sensitivity_vectors: tuple[
        tuple[float, float], ...
    ] = field(init=False)
    zero_power_temperature_variance_celsius_squared: float = field(init=False)
    zero_power_temperature_standard_uncertainty_c: float = field(init=False)
    fitted_temperature_variances_celsius_squared: tuple[float, ...] = field(init=False)
    fitted_temperature_standard_uncertainties_c: tuple[float, ...] = field(init=False)
    fitted_temperature_rise_variances_celsius_squared: tuple[float, ...] = field(
        init=False
    )
    fitted_temperature_rise_standard_uncertainties_c: tuple[float, ...] = field(
        init=False
    )
    propagation_method: _ZeroPowerFitTemperatureUncertaintyMethod = field(
        init=False,
        default="first_order_fit_parameter_covariance",
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.temperature_result,
            ZeroPowerResistanceFitTemperatureResult,
        ):
            raise TypeError(
                "temperature_result must be a ZeroPowerResistanceFitTemperatureResult"
            )
        if not isinstance(
            self.fit_uncertainty,
            ZeroPowerResistanceFitUncertaintyResult,
        ):
            raise TypeError(
                "fit_uncertainty must be a ZeroPowerResistanceFitUncertaintyResult"
            )
        if self.fit_uncertainty.fit_result != self.temperature_result.fit_result:
            raise ValueError(
                "fit_uncertainty must describe the retained zero-power fit"
            )

        covariance = self.fit_uncertainty.parameter_covariance_matrix
        zero_sensitivity = _temperature_sensitivity_celsius_per_ohm(
            self.temperature_result.model,
            self.temperature_result.zero_power_temperature_c,
            name="Zero-power fit temperature sensitivity",
        )
        zero_vector = (zero_sensitivity, 0.0)
        zero_variance = _two_parameter_covariance_variance(
            zero_vector,
            covariance,
            quantity_name="Zero-power fit temperature uncertainty",
        )

        fitted_vectors: list[tuple[float, float]] = []
        rise_vectors: list[tuple[float, float]] = []
        fitted_variances: list[float] = []
        rise_variances: list[float] = []

        for observation, temperature in zip(
            self.temperature_result.fit_result.evidence.observations,
            self.temperature_result.fitted_temperatures_c,
            strict=True,
        ):
            local_sensitivity = _temperature_sensitivity_celsius_per_ohm(
                self.temperature_result.model,
                temperature,
                name="Fitted self-heating temperature sensitivity",
            )
            fitted_vector = (
                local_sensitivity,
                observation.current_squared_a2 * local_sensitivity,
            )
            rise_vector = (
                fitted_vector[0] - zero_vector[0],
                fitted_vector[1],
            )
            fitted_vectors.append(fitted_vector)
            rise_vectors.append(rise_vector)
            fitted_variances.append(
                _two_parameter_covariance_variance(
                    fitted_vector,
                    covariance,
                    quantity_name="Fitted self-heating temperature uncertainty",
                )
            )
            rise_variances.append(
                _two_parameter_covariance_variance(
                    rise_vector,
                    covariance,
                    quantity_name=("Fitted self-heating temperature-rise uncertainty"),
                )
            )

        object.__setattr__(
            self,
            "zero_power_temperature_parameter_sensitivity_vector",
            zero_vector,
        )
        object.__setattr__(
            self,
            "fitted_temperature_parameter_sensitivity_vectors",
            tuple(fitted_vectors),
        )
        object.__setattr__(
            self,
            "fitted_temperature_rise_parameter_sensitivity_vectors",
            tuple(rise_vectors),
        )
        object.__setattr__(
            self,
            "zero_power_temperature_variance_celsius_squared",
            zero_variance,
        )
        object.__setattr__(
            self,
            "zero_power_temperature_standard_uncertainty_c",
            math.sqrt(zero_variance),
        )
        object.__setattr__(
            self,
            "fitted_temperature_variances_celsius_squared",
            tuple(fitted_variances),
        )
        object.__setattr__(
            self,
            "fitted_temperature_standard_uncertainties_c",
            tuple(math.sqrt(value) for value in fitted_variances),
        )
        object.__setattr__(
            self,
            "fitted_temperature_rise_variances_celsius_squared",
            tuple(rise_variances),
        )
        object.__setattr__(
            self,
            "fitted_temperature_rise_standard_uncertainties_c",
            tuple(math.sqrt(value) for value in rise_variances),
        )

    @property
    def parameter_names(self) -> tuple[str, str]:
        """Return the fitted-parameter order used by all sensitivity vectors."""
        return self.fit_uncertainty.parameter_names


@dataclass(frozen=True, slots=True)
class SelfHeatingCoefficientResult:
    """Context-bound self-heating coefficient from a multi-observation fit.

    A scalar coefficient is fitted through the origin from fitted temperature rise
    versus fitted ``I²R`` power at each distinct sampled current level. Repeated
    observations at the same current level therefore influence the underlying
    resistance fit but do not receive an additional weight in this secondary
    coefficient calculation. This is a finite-range descriptive coefficient, not
    the zero-power differential ``d(ΔT)/dP``. Because fitted power is
    ``I² * (R0 + k*I²)``, pointwise ``ΔT/P`` and the fitted scalar can depend on
    the sampled power range even when the resistance-versus-current-squared fit is
    exact.

    The retained experiment context is part of the result because self-heating is
    influenced by thermal contact with the environment. The coefficient must not
    be treated as an intrinsic, setup-independent property of the RTD
    characteristic.
    """

    temperature_result: ZeroPowerResistanceFitTemperatureResult
    context: SelfHeatingExperimentContext = field(init=False)
    current_squared_levels_a2: tuple[float, ...] = field(init=False)
    fitted_temperature_rises_c: tuple[float, ...] = field(init=False)
    fitted_dissipated_powers_w: tuple[float, ...] = field(init=False)
    coefficient_fit_residuals_c: tuple[float, ...] = field(init=False)
    self_heating_coefficient_c_per_w: float = field(init=False)
    dissipation_constant_w_per_c: float = field(init=False)
    method: _SelfHeatingCoefficientMethod = field(
        init=False,
        default="least_squares_temperature_rise_vs_fitted_power_through_origin",
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.temperature_result, ZeroPowerResistanceFitTemperatureResult
        ):
            raise TypeError(
                "temperature_result must be a ZeroPowerResistanceFitTemperatureResult"
            )

        fit_result = self.temperature_result.fit_result
        context = fit_result.evidence.context
        if context is None:
            raise ValueError(
                "Self-heating coefficient requires retained experiment context"
            )
        if fit_result.resistance_slope_ohms_per_a2 <= 0.0:
            raise ValueError(
                "Self-heating coefficient requires a positive resistance slope"
            )

        level_data: dict[float, tuple[float, float]] = {}
        for observation, rise, power in zip(
            fit_result.evidence.observations,
            self.temperature_result.fitted_temperature_rises_c,
            self.temperature_result.fitted_dissipated_powers_w,
            strict=True,
        ):
            level_data.setdefault(
                observation.current_squared_a2,
                (rise, power),
            )

        levels = tuple(sorted(level_data))
        rises = tuple(level_data[level][0] for level in levels)
        powers = tuple(level_data[level][1] for level in levels)
        if not all(math.isfinite(rise) and rise > 0.0 for rise in rises):
            raise ValueError(
                "Self-heating coefficient requires positive finite fitted "
                "temperature rises"
            )
        if not all(math.isfinite(power) and power > 0.0 for power in powers):
            raise ValueError(
                "Self-heating coefficient requires positive finite fitted powers"
            )

        coefficient = _through_origin_self_heating_coefficient(
            powers,
            rises,
        )
        dissipation_constant = 1.0 / coefficient
        if not math.isfinite(dissipation_constant) or dissipation_constant <= 0.0:
            raise ValueError("Dissipation constant must be positive and finite")

        residuals = tuple(
            rise - coefficient * power
            for rise, power in zip(rises, powers, strict=True)
        )
        if not all(math.isfinite(residual) for residual in residuals):
            raise ValueError("Self-heating coefficient residuals must be finite")

        object.__setattr__(self, "context", context)
        object.__setattr__(self, "current_squared_levels_a2", levels)
        object.__setattr__(self, "fitted_temperature_rises_c", rises)
        object.__setattr__(self, "fitted_dissipated_powers_w", powers)
        object.__setattr__(self, "coefficient_fit_residuals_c", residuals)
        object.__setattr__(self, "self_heating_coefficient_c_per_w", coefficient)
        object.__setattr__(
            self,
            "dissipation_constant_w_per_c",
            dissipation_constant,
        )

    @property
    def distinct_current_count(self) -> int:
        """Return the number of distinct current levels used for the coefficient."""
        return len(self.current_squared_levels_a2)

    @property
    def coefficient_rms_residual_c(self) -> float:
        """Return descriptive RMS residual of the through-origin coefficient fit."""
        return math.hypot(*self.coefficient_fit_residuals_c) / math.sqrt(
            self.distinct_current_count
        )

    @property
    def coefficient_max_absolute_residual_c(self) -> float:
        """Return the largest absolute descriptive coefficient-fit residual."""
        return max(abs(residual) for residual in self.coefficient_fit_residuals_c)

    @property
    def pointwise_self_heating_coefficients_c_per_w(self) -> tuple[float, ...]:
        """Return fitted temperature rise divided by fitted power at each level."""
        return tuple(
            rise / power
            for rise, power in zip(
                self.fitted_temperature_rises_c,
                self.fitted_dissipated_powers_w,
                strict=True,
            )
        )

    @property
    def self_heating_coefficient_c_per_mw(self) -> float:
        """Return the scalar self-heating coefficient in °C/mW."""
        return self.self_heating_coefficient_c_per_w / 1000.0

    @property
    def dissipation_constant_mw_per_c(self) -> float:
        """Return the reciprocal dissipation constant in mW/°C."""
        return self.dissipation_constant_w_per_c * 1000.0


@dataclass(frozen=True, slots=True)
class SelfHeatingCoefficientUncertaintyResult:
    """Fit-covariance uncertainty for a context-bound self-heating coefficient.

    The scalar coefficient is treated as a deterministic function of the fitted
    zero-power resistance and ``dR/d(I²)`` slope. The full retained 2x2 covariance
    matrix is propagated through the coefficient calculation with first-order
    local sensitivities. The RTD model and experiment context are treated as fixed.
    This uncertainty describes covariance of the retained finite-range coefficient;
    it does not quantify the deterministic difference between that coefficient and
    a zero-power differential coefficient or other coefficient definition.
    """

    coefficient_result: SelfHeatingCoefficientResult
    fit_uncertainty: ZeroPowerResistanceFitUncertaintyResult
    self_heating_coefficient_parameter_sensitivity_vector: tuple[float, float] = field(
        init=False
    )
    self_heating_coefficient_variance_celsius_squared_per_watt_squared: float = field(
        init=False
    )
    self_heating_coefficient_standard_uncertainty_c_per_w: float = field(init=False)
    dissipation_constant_parameter_sensitivity_vector: tuple[float, float] = field(
        init=False
    )
    dissipation_constant_variance_watt_squared_per_celsius_squared: float = field(
        init=False
    )
    dissipation_constant_standard_uncertainty_w_per_c: float = field(init=False)
    propagation_method: _SelfHeatingCoefficientUncertaintyMethod = field(
        init=False,
        default="first_order_fit_parameter_covariance",
    )

    def __post_init__(self) -> None:
        if not isinstance(self.coefficient_result, SelfHeatingCoefficientResult):
            raise TypeError("coefficient_result must be a SelfHeatingCoefficientResult")
        if not isinstance(
            self.fit_uncertainty, ZeroPowerResistanceFitUncertaintyResult
        ):
            raise TypeError(
                "fit_uncertainty must be a ZeroPowerResistanceFitUncertaintyResult"
            )
        if (
            self.fit_uncertainty.fit_result
            != self.coefficient_result.temperature_result.fit_result
        ):
            raise ValueError(
                "fit_uncertainty must describe the retained zero-power fit"
            )

        coefficient_vector = _self_heating_coefficient_parameter_sensitivities(
            self.coefficient_result
        )
        coefficient_variance = _two_parameter_covariance_variance(
            coefficient_vector,
            self.fit_uncertainty.parameter_covariance_matrix,
            quantity_name="Self-heating coefficient uncertainty",
        )
        coefficient = self.coefficient_result.self_heating_coefficient_c_per_w
        dissipation_vector = (
            (-coefficient_vector[0] / coefficient) / coefficient,
            (-coefficient_vector[1] / coefficient) / coefficient,
        )
        if not all(math.isfinite(value) for value in dissipation_vector):
            raise ValueError(
                "Dissipation-constant parameter sensitivities must be finite"
            )
        dissipation_variance = _two_parameter_covariance_variance(
            dissipation_vector,
            self.fit_uncertainty.parameter_covariance_matrix,
            quantity_name="Dissipation constant uncertainty",
        )

        object.__setattr__(
            self,
            "self_heating_coefficient_parameter_sensitivity_vector",
            coefficient_vector,
        )
        object.__setattr__(
            self,
            "self_heating_coefficient_variance_celsius_squared_per_watt_squared",
            coefficient_variance,
        )
        object.__setattr__(
            self,
            "self_heating_coefficient_standard_uncertainty_c_per_w",
            math.sqrt(coefficient_variance),
        )
        object.__setattr__(
            self,
            "dissipation_constant_parameter_sensitivity_vector",
            dissipation_vector,
        )
        object.__setattr__(
            self,
            "dissipation_constant_variance_watt_squared_per_celsius_squared",
            dissipation_variance,
        )
        object.__setattr__(
            self,
            "dissipation_constant_standard_uncertainty_w_per_c",
            math.sqrt(dissipation_variance),
        )

    @property
    def parameter_names(self) -> tuple[str, str]:
        """Return the fitted-parameter order used by both sensitivity vectors."""
        return self.fit_uncertainty.parameter_names

    @property
    def self_heating_coefficient_standard_uncertainty_c_per_mw(self) -> float:
        """Return coefficient standard uncertainty in °C/mW."""
        return self.self_heating_coefficient_standard_uncertainty_c_per_w / 1000.0

    @property
    def dissipation_constant_standard_uncertainty_mw_per_c(self) -> float:
        """Return dissipation-constant standard uncertainty in mW/°C."""
        return self.dissipation_constant_standard_uncertainty_w_per_c * 1000.0


@dataclass(frozen=True, slots=True)
class TwoCurrentInputCorrelationMatrix:
    """Correlation matrix for the four normalized two-current inputs.

    Matrix rows and columns follow :attr:`input_parameter_names`: ``I_low``,
    ``R_low``, ``I_high``, and ``R_high``. The matrix must be finite, symmetric,
    positive semidefinite, and have unit diagonal. Correlations are supplied
    separately from :class:`TwoCurrentInputStandardUncertainties` so the same
    uncertainty magnitudes can be propagated under independent or correlated
    assumptions without changing the retained measurement evidence.
    """

    correlation_matrix: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        matrix = _validate_two_current_correlation_matrix(self.correlation_matrix)
        object.__setattr__(self, "correlation_matrix", matrix)

    @property
    def input_parameter_names(self) -> tuple[str, str, str, str]:
        """Return the fixed row/column order of the correlation matrix."""
        return _TWO_CURRENT_INPUT_PARAMETER_NAMES

    def covariance_matrix(
        self,
        standard_uncertainties: TwoCurrentInputStandardUncertainties,
    ) -> tuple[tuple[float, ...], ...]:
        """Return the covariance matrix for supplied standard uncertainties."""
        if not isinstance(
            standard_uncertainties,
            TwoCurrentInputStandardUncertainties,
        ):
            raise TypeError(
                "standard_uncertainties must be a TwoCurrentInputStandardUncertainties"
            )
        values = standard_uncertainties.standard_uncertainty_vector
        return tuple(
            tuple(
                self.correlation_matrix[row][column] * values[row] * values[column]
                for column in range(4)
            )
            for row in range(4)
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class TwoCurrentInputStandardUncertainties:
    """Standard uncertainty magnitudes for the four two-current inputs.

    Fields correspond to the normalized low- and high-current observations retained
    by :class:`TwoCurrentZeroPowerEvidence`. All values are non-negative standard
    uncertainties. Propagation treats them as mutually independent unless an
    explicit :class:`TwoCurrentInputCorrelationMatrix` is supplied; correlation is
    never inferred from the measurement sequence or shared instrumentation.
    """

    low_current_standard_uncertainty_a: float
    low_resistance_standard_uncertainty_ohms: float
    high_current_standard_uncertainty_a: float
    high_resistance_standard_uncertainty_ohms: float

    def __post_init__(self) -> None:
        for field_name, display_name in (
            (
                "low_current_standard_uncertainty_a",
                "Low-current standard uncertainty",
            ),
            (
                "low_resistance_standard_uncertainty_ohms",
                "Low-resistance standard uncertainty",
            ),
            (
                "high_current_standard_uncertainty_a",
                "High-current standard uncertainty",
            ),
            (
                "high_resistance_standard_uncertainty_ohms",
                "High-resistance standard uncertainty",
            ),
        ):
            value = _as_float(getattr(self, field_name), name=display_name)
            if not math.isfinite(value):
                raise ValueError(f"{display_name} must be finite")
            if value < 0.0:
                raise ValueError(f"{display_name} must be non-negative")
            object.__setattr__(self, field_name, value)

    @property
    def input_parameter_names(self) -> tuple[str, str, str, str]:
        """Return the fixed input order used by uncertainty sensitivity vectors."""
        return _TWO_CURRENT_INPUT_PARAMETER_NAMES

    @property
    def standard_uncertainty_vector(self) -> tuple[float, float, float, float]:
        """Return standard uncertainties in :attr:`input_parameter_names` order."""
        return (
            self.low_current_standard_uncertainty_a,
            self.low_resistance_standard_uncertainty_ohms,
            self.high_current_standard_uncertainty_a,
            self.high_resistance_standard_uncertainty_ohms,
        )


@dataclass(frozen=True, slots=True)
class TwoCurrentZeroPowerUncertaintyResult:
    """First-order uncertainty propagated to two-current zero-power resistance.

    Standard uncertainty magnitudes are retained separately from an optional input
    correlation matrix. When correlations are supplied, :attr:`input_covariance_matrix`
    exposes the full covariance matrix actually used by the propagation.
    """

    zero_power_result: TwoCurrentZeroPowerResult
    input_standard_uncertainties: TwoCurrentInputStandardUncertainties
    input_correlation_matrix: TwoCurrentInputCorrelationMatrix | None = None
    zero_power_resistance_input_sensitivity_vector: tuple[
        float, float, float, float
    ] = field(init=False)
    zero_power_resistance_variance_ohms_squared: float = field(init=False)
    zero_power_resistance_standard_uncertainty_ohms: float = field(init=False)
    propagation_method: _TwoCurrentUncertaintyMethod = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.zero_power_result, TwoCurrentZeroPowerResult):
            raise TypeError("zero_power_result must be a TwoCurrentZeroPowerResult")
        if not isinstance(
            self.input_standard_uncertainties,
            TwoCurrentInputStandardUncertainties,
        ):
            raise TypeError(
                "input_standard_uncertainties must be a "
                "TwoCurrentInputStandardUncertainties"
            )

        if self.input_correlation_matrix is not None and not isinstance(
            self.input_correlation_matrix, TwoCurrentInputCorrelationMatrix
        ):
            raise TypeError(
                "input_correlation_matrix must be a "
                "TwoCurrentInputCorrelationMatrix or None"
            )

        sensitivities = _zero_power_resistance_input_sensitivities(
            self.zero_power_result
        )
        variance, standard_uncertainty = _two_current_uncertainty_propagation(
            sensitivities,
            self.input_standard_uncertainties,
            self.input_correlation_matrix,
            quantity_name="Zero-power resistance uncertainty",
        )
        propagation_method: _TwoCurrentUncertaintyMethod = (
            "first_order_correlated_inputs"
            if self.input_correlation_matrix is not None
            else "first_order_independent_inputs"
        )
        object.__setattr__(
            self,
            "zero_power_resistance_input_sensitivity_vector",
            sensitivities,
        )
        object.__setattr__(
            self,
            "zero_power_resistance_variance_ohms_squared",
            variance,
        )
        object.__setattr__(
            self,
            "zero_power_resistance_standard_uncertainty_ohms",
            standard_uncertainty,
        )
        object.__setattr__(self, "propagation_method", propagation_method)

    @property
    def input_covariance_matrix(
        self,
    ) -> tuple[tuple[float, ...], ...]:
        """Return the 4x4 covariance matrix used for propagation."""
        return _two_current_input_covariance_matrix(
            self.input_standard_uncertainties,
            self.input_correlation_matrix,
        )

    @property
    def input_parameter_names(self) -> tuple[str, str, str, str]:
        """Return the input order used by the retained sensitivity vector."""
        return _TWO_CURRENT_INPUT_PARAMETER_NAMES


@dataclass(frozen=True, slots=True)
class TwoCurrentSelfHeatingTemperatureResult:
    """Model-based temperatures derived from a two-current zero-power result.

    All three resistance values are converted through the same explicitly supplied
    RTD model. The temperature-rise properties therefore compare each observed
    current point with the extrapolated zero-power temperature without changing
    the underlying RTD model or the retained resistance-domain evidence.
    """

    zero_power_result: TwoCurrentZeroPowerResult
    model: _RTDModel = field(repr=False, compare=False)
    zero_power_temperature_c: float = field(init=False)
    low_current_temperature_c: float = field(init=False)
    high_current_temperature_c: float = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.zero_power_result, TwoCurrentZeroPowerResult):
            raise TypeError("zero_power_result must be a TwoCurrentZeroPowerResult")

        evidence = self.zero_power_result.evidence
        zero_power_temperature = _converted_temperature_c(
            self.model,
            self.zero_power_result.zero_power_resistance_ohms,
            name="Zero-power temperature",
        )
        low_current_temperature = _converted_temperature_c(
            self.model,
            evidence.low_current_observation.resistance_ohms,
            name="Low-current temperature",
        )
        high_current_temperature = _converted_temperature_c(
            self.model,
            evidence.high_current_observation.resistance_ohms,
            name="High-current temperature",
        )
        object.__setattr__(self, "zero_power_temperature_c", zero_power_temperature)
        object.__setattr__(self, "low_current_temperature_c", low_current_temperature)
        object.__setattr__(
            self,
            "high_current_temperature_c",
            high_current_temperature,
        )

    @property
    def low_current_temperature_rise_c(self) -> float:
        """Return low-current temperature minus zero-power temperature."""
        return self.low_current_temperature_c - self.zero_power_temperature_c

    @property
    def high_current_temperature_rise_c(self) -> float:
        """Return high-current temperature minus zero-power temperature."""
        return self.high_current_temperature_c - self.zero_power_temperature_c


@dataclass(frozen=True, slots=True)
class TwoCurrentSelfHeatingTemperatureUncertaintyResult:
    """First-order uncertainty for model-based two-current temperatures and rises.

    Sensitivity vectors use the fixed input order exposed by
    :attr:`input_parameter_names`. Temperature-rise uncertainties are propagated
    directly from the original current/resistance inputs so the shared zero-power
    estimate is not incorrectly treated as independent of each observed resistance.
    Any explicit input correlations retained by the corresponding zero-power
    uncertainty result are propagated through the same sensitivity vectors.
    """

    temperature_result: TwoCurrentSelfHeatingTemperatureResult
    zero_power_uncertainty: TwoCurrentZeroPowerUncertaintyResult
    zero_power_temperature_input_sensitivity_vector: tuple[
        float, float, float, float
    ] = field(init=False)
    low_current_temperature_input_sensitivity_vector: tuple[
        float, float, float, float
    ] = field(init=False)
    high_current_temperature_input_sensitivity_vector: tuple[
        float, float, float, float
    ] = field(init=False)
    low_current_temperature_rise_input_sensitivity_vector: tuple[
        float, float, float, float
    ] = field(init=False)
    high_current_temperature_rise_input_sensitivity_vector: tuple[
        float, float, float, float
    ] = field(init=False)
    zero_power_temperature_variance_celsius_squared: float = field(init=False)
    zero_power_temperature_standard_uncertainty_c: float = field(init=False)
    low_current_temperature_variance_celsius_squared: float = field(init=False)
    low_current_temperature_standard_uncertainty_c: float = field(init=False)
    high_current_temperature_variance_celsius_squared: float = field(init=False)
    high_current_temperature_standard_uncertainty_c: float = field(init=False)
    low_current_temperature_rise_variance_celsius_squared: float = field(init=False)
    low_current_temperature_rise_standard_uncertainty_c: float = field(init=False)
    high_current_temperature_rise_variance_celsius_squared: float = field(init=False)
    high_current_temperature_rise_standard_uncertainty_c: float = field(init=False)
    propagation_method: _TwoCurrentUncertaintyMethod = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(
            self.temperature_result, TwoCurrentSelfHeatingTemperatureResult
        ):
            raise TypeError(
                "temperature_result must be a TwoCurrentSelfHeatingTemperatureResult"
            )
        if not isinstance(
            self.zero_power_uncertainty, TwoCurrentZeroPowerUncertaintyResult
        ):
            raise TypeError(
                "zero_power_uncertainty must be a TwoCurrentZeroPowerUncertaintyResult"
            )
        if (
            self.zero_power_uncertainty.zero_power_result
            != self.temperature_result.zero_power_result
        ):
            raise ValueError(
                "zero_power_uncertainty must describe the retained zero-power result"
            )

        zero_resistance_sensitivities = (
            self.zero_power_uncertainty.zero_power_resistance_input_sensitivity_vector
        )
        model = self.temperature_result.model
        zero_temperature_sensitivity = _temperature_sensitivity_celsius_per_ohm(
            model,
            self.temperature_result.zero_power_temperature_c,
            name="Zero-power temperature sensitivity",
        )
        low_temperature_sensitivity = _temperature_sensitivity_celsius_per_ohm(
            model,
            self.temperature_result.low_current_temperature_c,
            name="Low-current temperature sensitivity",
        )
        high_temperature_sensitivity = _temperature_sensitivity_celsius_per_ohm(
            model,
            self.temperature_result.high_current_temperature_c,
            name="High-current temperature sensitivity",
        )

        zero_temperature_vector = (
            zero_temperature_sensitivity * zero_resistance_sensitivities[0],
            zero_temperature_sensitivity * zero_resistance_sensitivities[1],
            zero_temperature_sensitivity * zero_resistance_sensitivities[2],
            zero_temperature_sensitivity * zero_resistance_sensitivities[3],
        )
        low_temperature_vector = (0.0, low_temperature_sensitivity, 0.0, 0.0)
        high_temperature_vector = (0.0, 0.0, 0.0, high_temperature_sensitivity)
        low_rise_vector = (
            low_temperature_vector[0] - zero_temperature_vector[0],
            low_temperature_vector[1] - zero_temperature_vector[1],
            low_temperature_vector[2] - zero_temperature_vector[2],
            low_temperature_vector[3] - zero_temperature_vector[3],
        )
        high_rise_vector = (
            high_temperature_vector[0] - zero_temperature_vector[0],
            high_temperature_vector[1] - zero_temperature_vector[1],
            high_temperature_vector[2] - zero_temperature_vector[2],
            high_temperature_vector[3] - zero_temperature_vector[3],
        )

        standard_uncertainties = (
            self.zero_power_uncertainty.input_standard_uncertainties
        )
        correlation_matrix = self.zero_power_uncertainty.input_correlation_matrix
        zero_temperature_variance, zero_temperature_uncertainty = (
            _two_current_uncertainty_propagation(
                zero_temperature_vector,
                standard_uncertainties,
                correlation_matrix,
                quantity_name="Zero-power temperature uncertainty",
            )
        )
        low_temperature_variance, low_temperature_uncertainty = (
            _two_current_uncertainty_propagation(
                low_temperature_vector,
                standard_uncertainties,
                correlation_matrix,
                quantity_name="Low-current temperature uncertainty",
            )
        )
        high_temperature_variance, high_temperature_uncertainty = (
            _two_current_uncertainty_propagation(
                high_temperature_vector,
                standard_uncertainties,
                correlation_matrix,
                quantity_name="High-current temperature uncertainty",
            )
        )
        low_rise_variance, low_rise_uncertainty = _two_current_uncertainty_propagation(
            low_rise_vector,
            standard_uncertainties,
            correlation_matrix,
            quantity_name="Low-current temperature-rise uncertainty",
        )
        high_rise_variance, high_rise_uncertainty = (
            _two_current_uncertainty_propagation(
                high_rise_vector,
                standard_uncertainties,
                correlation_matrix,
                quantity_name="High-current temperature-rise uncertainty",
            )
        )

        object.__setattr__(
            self,
            "zero_power_temperature_input_sensitivity_vector",
            zero_temperature_vector,
        )
        object.__setattr__(
            self,
            "low_current_temperature_input_sensitivity_vector",
            low_temperature_vector,
        )
        object.__setattr__(
            self,
            "high_current_temperature_input_sensitivity_vector",
            high_temperature_vector,
        )
        object.__setattr__(
            self,
            "low_current_temperature_rise_input_sensitivity_vector",
            low_rise_vector,
        )
        object.__setattr__(
            self,
            "high_current_temperature_rise_input_sensitivity_vector",
            high_rise_vector,
        )
        object.__setattr__(
            self,
            "zero_power_temperature_variance_celsius_squared",
            zero_temperature_variance,
        )
        object.__setattr__(
            self,
            "zero_power_temperature_standard_uncertainty_c",
            zero_temperature_uncertainty,
        )
        object.__setattr__(
            self,
            "low_current_temperature_variance_celsius_squared",
            low_temperature_variance,
        )
        object.__setattr__(
            self,
            "low_current_temperature_standard_uncertainty_c",
            low_temperature_uncertainty,
        )
        object.__setattr__(
            self,
            "high_current_temperature_variance_celsius_squared",
            high_temperature_variance,
        )
        object.__setattr__(
            self,
            "high_current_temperature_standard_uncertainty_c",
            high_temperature_uncertainty,
        )
        object.__setattr__(
            self,
            "low_current_temperature_rise_variance_celsius_squared",
            low_rise_variance,
        )
        object.__setattr__(
            self,
            "low_current_temperature_rise_standard_uncertainty_c",
            low_rise_uncertainty,
        )
        object.__setattr__(
            self,
            "high_current_temperature_rise_variance_celsius_squared",
            high_rise_variance,
        )
        object.__setattr__(
            self,
            "high_current_temperature_rise_standard_uncertainty_c",
            high_rise_uncertainty,
        )
        object.__setattr__(
            self,
            "propagation_method",
            self.zero_power_uncertainty.propagation_method,
        )

    @property
    def input_parameter_names(self) -> tuple[str, str, str, str]:
        """Return the input order used by all retained sensitivity vectors."""
        return _TWO_CURRENT_INPUT_PARAMETER_NAMES


def evaluate_self_heating_coefficient(
    result: ZeroPowerResistanceFitTemperatureResult,
) -> SelfHeatingCoefficientResult:
    """Derive a context-bound self-heating coefficient from a 3+ observation fit.

    The retained experiment context is required, as is a positive fitted
    resistance-versus-current-squared slope. The scalar coefficient is a
    through-origin least-squares description of fitted temperature rise versus
    fitted dissipated power at the distinct sampled current levels. It is therefore
    a finite-range coefficient rather than a zero-power differential coefficient.
    Residuals and pointwise coefficients remain available for judging how well one
    scalar describes the retained range; no universal acceptance threshold is
    imposed.

    Raises:
        TypeError: If ``result`` is not a
            :class:`ZeroPowerResistanceFitTemperatureResult`.
        ValueError: If context is missing, the fitted slope/rises are not positive,
            or the coefficient cannot be represented finitely.
    """
    if not isinstance(result, ZeroPowerResistanceFitTemperatureResult):
        raise TypeError("result must be a ZeroPowerResistanceFitTemperatureResult")
    return SelfHeatingCoefficientResult(temperature_result=result)


def propagate_self_heating_coefficient_uncertainty(
    result: SelfHeatingCoefficientResult,
) -> SelfHeatingCoefficientUncertaintyResult:
    """Propagate retained fit covariance into coefficient and dissipation constant.

    The full fitted intercept/slope covariance is propagated through the
    through-origin coefficient calculation. This remains a first-order/local
    estimate conditional on the same fixed-current assumptions as
    :func:`estimate_zero_power_fit_uncertainty`; covariance may come from residual-
    scatter ordinary least squares or supplied absolute resistance uncertainties.
    The RTD model and thermal-environment context are treated as fixed. It does not
    add uncertainty
    for the deterministic range dependence of this finite-range coefficient or for
    its difference from a zero-power differential coefficient.

    Raises:
        TypeError: If ``result`` is not a :class:`SelfHeatingCoefficientResult`.
        ValueError: If propagated sensitivities or variances are non-finite.
    """
    if not isinstance(result, SelfHeatingCoefficientResult):
        raise TypeError("result must be a SelfHeatingCoefficientResult")
    return SelfHeatingCoefficientUncertaintyResult(
        coefficient_result=result,
        fit_uncertainty=estimate_zero_power_fit_uncertainty(
            result.temperature_result.fit_result
        ),
    )


def evaluate_two_current_temperatures(
    result: TwoCurrentZeroPowerResult,
    *,
    model: _RTDModel,
) -> TwoCurrentSelfHeatingTemperatureResult:
    """Convert a two-current zero-power result into RTD temperatures.

    ``model`` is applied to the extrapolated zero-power resistance and to both
    retained observed resistances. The returned temperature rises are therefore
    model-based differences between each observed operating point and the inferred
    zero-current state under the same experimental assumptions as ``result``.

    Model conversion exceptions propagate unchanged. This function does not add
    uncertainty, prove thermal stability, or infer ambient temperature independently
    of the two-current extrapolation.

    Raises:
        TypeError: If ``result`` is not a :class:`TwoCurrentZeroPowerResult`.
        ValueError: If a model conversion returns a non-finite temperature.
    """
    if not isinstance(result, TwoCurrentZeroPowerResult):
        raise TypeError("result must be a TwoCurrentZeroPowerResult")

    return TwoCurrentSelfHeatingTemperatureResult(
        zero_power_result=result,
        model=model,
    )


def propagate_two_current_zero_power_uncertainty(
    result: TwoCurrentZeroPowerResult,
    *,
    input_standard_uncertainties: TwoCurrentInputStandardUncertainties,
    input_correlation_matrix: TwoCurrentInputCorrelationMatrix | None = None,
) -> TwoCurrentZeroPowerUncertaintyResult:
    """Propagate input uncertainties to zero-power resistance.

    The first-order law of propagation is applied to the original four inputs in
    normalized low/high-current order: ``I_low``, ``R_low``, ``I_high``, and
    ``R_high``. Current and resistance uncertainties may therefore contribute to
    the extrapolated intercept. Inputs are treated as mutually independent when
    ``input_correlation_matrix`` is omitted. When supplied, its correlations are
    combined with the retained standard uncertainties and the full covariance form
    of the first-order law of propagation is used.

    This result contains only measurement-input uncertainty for the two-current
    extrapolation. Correlation must be supplied explicitly; it is not inferred from
    a shared instrument, current source, calibration, or measurement sequence. Model
    uncertainty and thermal-drift effects remain separate.
    """
    if not isinstance(result, TwoCurrentZeroPowerResult):
        raise TypeError("result must be a TwoCurrentZeroPowerResult")
    if not isinstance(
        input_standard_uncertainties,
        TwoCurrentInputStandardUncertainties,
    ):
        raise TypeError(
            "input_standard_uncertainties must be a "
            "TwoCurrentInputStandardUncertainties"
        )
    if input_correlation_matrix is not None and not isinstance(
        input_correlation_matrix, TwoCurrentInputCorrelationMatrix
    ):
        raise TypeError(
            "input_correlation_matrix must be a "
            "TwoCurrentInputCorrelationMatrix or None"
        )

    return TwoCurrentZeroPowerUncertaintyResult(
        zero_power_result=result,
        input_standard_uncertainties=input_standard_uncertainties,
        input_correlation_matrix=input_correlation_matrix,
    )


def propagate_two_current_temperature_uncertainty(
    result: TwoCurrentSelfHeatingTemperatureResult,
    *,
    input_standard_uncertainties: TwoCurrentInputStandardUncertainties,
    input_correlation_matrix: TwoCurrentInputCorrelationMatrix | None = None,
) -> TwoCurrentSelfHeatingTemperatureUncertaintyResult:
    """Propagate two-current input uncertainties into temperatures.

    The calculation uses first-order local RTD sensitivities from the exact model
    retained by ``result``. Zero-power temperature, observed temperatures, and
    observed-minus-zero-power temperature rises are all propagated directly from
    the original four inputs. This preserves the dependence created because the
    zero-power estimate is calculated from the same resistance observations.

    ``input_correlation_matrix`` has the same meaning as in
    :func:`propagate_two_current_zero_power_uncertainty`; when omitted, the four
    inputs are treated as mutually independent. Fitted-model covariance and other
    uncertainty-budget components remain separate and are not combined automatically.
    """
    if not isinstance(result, TwoCurrentSelfHeatingTemperatureResult):
        raise TypeError("result must be a TwoCurrentSelfHeatingTemperatureResult")
    if not isinstance(
        input_standard_uncertainties,
        TwoCurrentInputStandardUncertainties,
    ):
        raise TypeError(
            "input_standard_uncertainties must be a "
            "TwoCurrentInputStandardUncertainties"
        )

    zero_power_uncertainty = propagate_two_current_zero_power_uncertainty(
        result.zero_power_result,
        input_standard_uncertainties=input_standard_uncertainties,
        input_correlation_matrix=input_correlation_matrix,
    )
    return TwoCurrentSelfHeatingTemperatureUncertaintyResult(
        temperature_result=result,
        zero_power_uncertainty=zero_power_uncertainty,
    )


def assess_zero_power_extrapolation(
    result: TwoCurrentZeroPowerResult | ZeroPowerResistanceFitResult,
) -> ZeroPowerExtrapolationAssessment:
    """Assess structural evidence support for one zero-power extrapolation.

    This function does not emit :mod:`warnings` or decide whether an experiment is
    acceptable. It returns stable warning codes for objective evidence limitations
    and descriptive current-geometry metrics so callers can apply criteria justified
    for their own experiment. No result can by itself prove that the external thermal
    environment was constant; that requires experimental control/provenance beyond
    current/resistance values.

    Raises:
        TypeError: If ``result`` is not a supported zero-power result type.
    """
    return ZeroPowerExtrapolationAssessment(result=result)


def estimate_zero_power_fit_uncertainty(
    result: ZeroPowerResistanceFitResult,
) -> ZeroPowerResistanceFitUncertaintyResult:
    """Estimate parameter uncertainty for a retained zero-power resistance fit.

    For an unweighted fit, covariance uses the fitted residual variance and the
    ordinary-least-squares information matrix. For an inverse-variance weighted fit,
    covariance comes directly from the supplied absolute resistance standard
    uncertainties and is not rescaled by residual scatter. Both paths treat the
    current-squared coordinates as fixed/exact. This is not propagation of
    measurement-current uncertainty or a substitute for an errors-in-variables
    model when current uncertainty matters.

    Raises:
        TypeError: If ``result`` is not a :class:`ZeroPowerResistanceFitResult`.
        ValueError: If the resulting covariance cannot be represented finitely.
    """
    if not isinstance(result, ZeroPowerResistanceFitResult):
        raise TypeError("result must be a ZeroPowerResistanceFitResult")
    return ZeroPowerResistanceFitUncertaintyResult(fit_result=result)


def evaluate_zero_power_fit_temperatures(
    result: ZeroPowerResistanceFitResult,
    *,
    model: _RTDModel,
) -> ZeroPowerResistanceFitTemperatureResult:
    """Interpret a multi-observation zero-power fit through one RTD model.

    The same model converts the fitted zero-power resistance, every observed
    resistance, and every fitted resistance at the sampled current coordinates.
    The result therefore exposes observed and fitted temperature rises together
    with measured and fitted ``I²R`` powers without changing the resistance-domain
    fit or claiming that a setup-independent dissipation constant has been
    established.

    Model conversion exceptions and range failures propagate unchanged.

    Raises:
        TypeError: If ``result`` is not a :class:`ZeroPowerResistanceFitResult`.
        ValueError: If a model conversion returns a non-finite temperature.
    """
    if not isinstance(result, ZeroPowerResistanceFitResult):
        raise TypeError("result must be a ZeroPowerResistanceFitResult")
    return ZeroPowerResistanceFitTemperatureResult(
        fit_result=result,
        model=model,
    )


def propagate_zero_power_fit_temperature_uncertainty(
    result: ZeroPowerResistanceFitTemperatureResult,
) -> ZeroPowerResistanceFitTemperatureUncertaintyResult:
    """Propagate multi-observation fit covariance into temperatures and rises.

    The retained covariance of the fitted zero-power resistance and ``dR/d(I²)``
    slope is propagated with the full covariance matrix. At each
    sampled current coordinate ``x = I²``, fitted resistance is ``R0 + k*x``.
    Temperature-rise sensitivities are formed directly as the difference between
    the fitted-temperature and zero-power-temperature sensitivity vectors, so the
    shared fitted intercept is not treated as independent.

    This remains first-order/local because RTD resistance-to-temperature conversion
    is generally nonlinear. The RTD model itself is treated as fixed.

    Raises:
        TypeError: If ``result`` is not a
            :class:`ZeroPowerResistanceFitTemperatureResult`.
        ValueError: If model sensitivities or propagated variances are non-finite.
    """
    if not isinstance(result, ZeroPowerResistanceFitTemperatureResult):
        raise TypeError("result must be a ZeroPowerResistanceFitTemperatureResult")

    return ZeroPowerResistanceFitTemperatureUncertaintyResult(
        temperature_result=result,
        fit_uncertainty=estimate_zero_power_fit_uncertainty(result.fit_result),
    )


def fit_zero_power_resistance(
    observations: Iterable[SelfHeatingObservation],
    *,
    resistance_standard_uncertainties_ohms: Iterable[float] | None = None,
    context: SelfHeatingExperimentContext | None = None,
) -> ZeroPowerResistanceFitResult:
    """Fit ``R = R0 + k*I²`` to at least three current/resistance observations.

    By default the fit uses ordinary least squares in resistance with
    measurement-current squared as the independent coordinate. If every observation
    has a supplied absolute resistance standard uncertainty, inverse-variance
    weighted least squares is used instead with weights proportional to ``1/u²``.
    The current/current-squared coordinates remain fixed and exact in both cases.
    At least three observations provide positive residual degrees of freedom;
    repeated measurements at only two current levels are allowed and can therefore
    retain repeated-cycle scatter.

    Observations remain in caller-supplied order in the returned evidence. The
    residual diagnostics describe consistency with the fitted linear relation but
    do not prove that the external temperature was stable. A zero or negative
    slope is retained rather than converted into a claim of valid self-heating.

    Resistance uncertainties, when supplied, must be finite, positive, and match the
    observation count. They are treated as absolute independent response standard
    uncertainties supplied by the caller;
    parameter covariance is therefore determined from those absolute uncertainties
    rather than rescaled to force the observed residual scatter to agree with them.
    Measurement-current uncertainty requires an errors-in-variables treatment and is
    not included here. Correlated observation errors and automatic pass/fail
    thresholds also remain outside this fit. Optional ``context`` is retained as
    non-behavioral experiment provenance and does not alter the fit.

    Raises:
        TypeError: If any supplied value is not a :class:`SelfHeatingObservation`,
            or ``context`` has the wrong type.
        ValueError: If fewer than three observations are supplied, fewer than two
            distinct current levels are represented, the fit is not finitely
            representable, or the extrapolated zero-power resistance is not
            positive and finite.
    """
    observation_tuple = tuple(observations)
    if len(observation_tuple) < 3:
        raise ValueError("Zero-power fitting requires at least three observations")
    if not all(
        isinstance(observation, SelfHeatingObservation)
        for observation in observation_tuple
    ):
        raise TypeError("Observations must be SelfHeatingObservation values")
    if context is not None and not isinstance(context, SelfHeatingExperimentContext):
        raise TypeError("context must be a SelfHeatingExperimentContext or None")

    resistance_uncertainties = _validated_fit_resistance_uncertainties(
        resistance_standard_uncertainties_ohms,
        observation_count=len(observation_tuple),
    )
    zero_power_resistance, slope, residuals = _fit_zero_power_line(
        observation_tuple,
        resistance_standard_uncertainties_ohms=resistance_uncertainties,
    )
    if not math.isfinite(zero_power_resistance):
        raise ValueError("Zero-power fit must produce finite resistance")
    if zero_power_resistance <= 0.0:
        raise ValueError("Zero-power fit must produce resistance greater than zero")

    evidence = ZeroPowerResistanceFitEvidence(
        observations=observation_tuple,
        residuals_ohms=residuals,
        context=context,
        resistance_standard_uncertainties_ohms=resistance_uncertainties,
    )
    return ZeroPowerResistanceFitResult(
        zero_power_resistance_ohms=zero_power_resistance,
        resistance_slope_ohms_per_a2=slope,
        evidence=evidence,
    )


def _normalized_optional_text(value: str | None, *, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string or None")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _through_origin_self_heating_coefficient(
    powers_w: tuple[float, ...],
    temperature_rises_c: tuple[float, ...],
) -> float:
    power_scale = max(powers_w)
    rise_scale = max(temperature_rises_c)
    scaled_powers = tuple(power / power_scale for power in powers_w)
    scaled_rises = tuple(rise / rise_scale for rise in temperature_rises_c)
    numerator = math.fsum(
        power * rise for power, rise in zip(scaled_powers, scaled_rises, strict=True)
    )
    denominator = math.fsum(power * power for power in scaled_powers)
    coefficient = (rise_scale / power_scale) * (numerator / denominator)
    if not math.isfinite(coefficient) or coefficient <= 0.0:
        raise ValueError("Self-heating coefficient must be positive and finite")
    return coefficient


def _self_heating_coefficient_parameter_sensitivities(
    result: SelfHeatingCoefficientResult,
) -> tuple[float, float]:
    temperature_result = result.temperature_result
    zero_temperature = temperature_result.zero_power_temperature_c
    zero_sensitivity = _temperature_sensitivity_celsius_per_ohm(
        temperature_result.model,
        zero_temperature,
        name="Self-heating coefficient zero-power temperature sensitivity",
    )

    fit_result = temperature_result.fit_result
    r0 = fit_result.zero_power_resistance_ohms
    slope = fit_result.resistance_slope_ohms_per_a2
    power_scale = max(result.fitted_dissipated_powers_w)
    rise_scale = max(result.fitted_temperature_rises_c)

    scaled_powers: list[float] = []
    scaled_rises: list[float] = []
    scaled_power_vectors: list[tuple[float, float]] = []
    scaled_rise_vectors: list[tuple[float, float]] = []

    for current_squared in result.current_squared_levels_a2:
        fitted_resistance = r0 + slope * current_squared
        fitted_temperature = _converted_temperature_c(
            temperature_result.model,
            fitted_resistance,
            name="Self-heating coefficient fitted temperature",
        )
        fitted_sensitivity = _temperature_sensitivity_celsius_per_ohm(
            temperature_result.model,
            fitted_temperature,
            name="Self-heating coefficient fitted temperature sensitivity",
        )
        power = current_squared * fitted_resistance
        rise = fitted_temperature - zero_temperature
        scaled_powers.append(power / power_scale)
        scaled_rises.append(rise / rise_scale)
        scaled_power_vectors.append(
            (
                current_squared / power_scale,
                current_squared * current_squared / power_scale,
            )
        )
        scaled_rise_vectors.append(
            (
                (fitted_sensitivity - zero_sensitivity) / rise_scale,
                fitted_sensitivity * current_squared / rise_scale,
            )
        )

    numerator = math.fsum(
        power * rise for power, rise in zip(scaled_powers, scaled_rises, strict=True)
    )
    denominator = math.fsum(power * power for power in scaled_powers)
    scale = rise_scale / power_scale

    sensitivities: list[float] = []
    for parameter_index in range(2):
        numerator_derivative = math.fsum(
            power_vector[parameter_index] * rise + power * rise_vector[parameter_index]
            for power, rise, power_vector, rise_vector in zip(
                scaled_powers,
                scaled_rises,
                scaled_power_vectors,
                scaled_rise_vectors,
                strict=True,
            )
        )
        denominator_derivative = 2.0 * math.fsum(
            power * power_vector[parameter_index]
            for power, power_vector in zip(
                scaled_powers,
                scaled_power_vectors,
                strict=True,
            )
        )
        sensitivity = (
            scale
            * (numerator_derivative * denominator - numerator * denominator_derivative)
            / (denominator * denominator)
        )
        if not math.isfinite(sensitivity):
            raise ValueError(
                "Self-heating coefficient parameter sensitivities must be finite"
            )
        sensitivities.append(sensitivity)

    return (sensitivities[0], sensitivities[1])


def _validated_fit_resistance_uncertainties(
    values: Iterable[float] | None,
    *,
    observation_count: int,
) -> tuple[float, ...] | None:
    if values is None:
        return None
    uncertainties = tuple(
        _as_float(value, name="Resistance standard uncertainty") for value in values
    )
    if len(uncertainties) != observation_count:
        raise ValueError(
            "Resistance standard uncertainty count must match observation count"
        )
    for uncertainty in uncertainties:
        if not math.isfinite(uncertainty):
            raise ValueError("Resistance standard uncertainties must be finite")
        if uncertainty <= 0.0:
            raise ValueError(
                "Resistance standard uncertainties must be greater than zero"
            )
    return uncertainties


def _fit_zero_power_line(
    observations: tuple[SelfHeatingObservation, ...],
    *,
    resistance_standard_uncertainties_ohms: tuple[float, ...] | None = None,
) -> tuple[float, float, tuple[float, ...]]:
    if len(observations) < 3:
        raise ValueError("Zero-power fitting requires at least three observations")

    current_squared = tuple(
        observation.current_squared_a2 for observation in observations
    )
    x_min = min(current_squared)
    x_max = max(current_squared)
    x_span = x_max - x_min
    if not math.isfinite(x_span) or x_span <= 0.0:
        raise ValueError(
            "Zero-power fitting requires at least two distinct current levels"
        )

    scaled_x = tuple((value - x_min) / x_span for value in current_squared)
    if not all(math.isfinite(value) for value in scaled_x):
        raise ValueError("Scaled current-squared coordinates must remain finite")

    resistance_scale = max(observation.resistance_ohms for observation in observations)
    scaled_resistance = tuple(
        observation.resistance_ohms / resistance_scale for observation in observations
    )

    if resistance_standard_uncertainties_ohms is None:
        weights = (1.0,) * len(observations)
    else:
        minimum_uncertainty = min(resistance_standard_uncertainties_ohms)
        weights = tuple(
            (minimum_uncertainty / uncertainty) ** 2
            for uncertainty in resistance_standard_uncertainties_ohms
        )
        if not all(math.isfinite(weight) and weight > 0.0 for weight in weights):
            raise ValueError(
                "Resistance standard uncertainties have an unrepresentable "
                "inverse-variance weighting range"
            )

    total_weight = math.fsum(weights)
    if not math.isfinite(total_weight) or total_weight <= 0.0:
        raise ValueError("Zero-power fit weights must remain positive and finite")
    mean_x = (
        math.fsum(
            weight * value for weight, value in zip(weights, scaled_x, strict=True)
        )
        / total_weight
    )
    mean_scaled_resistance = (
        math.fsum(
            weight * value
            for weight, value in zip(weights, scaled_resistance, strict=True)
        )
        / total_weight
    )
    centered_x = tuple(value - mean_x for value in scaled_x)
    centered_resistance = tuple(
        value - mean_scaled_resistance for value in scaled_resistance
    )
    denominator = math.fsum(
        weight * value * value
        for weight, value in zip(weights, centered_x, strict=True)
    )
    numerator = math.fsum(
        weight * x_value * resistance_value
        for weight, x_value, resistance_value in zip(
            weights,
            centered_x,
            centered_resistance,
            strict=True,
        )
    )
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("Zero-power fit is rank deficient")
    if not math.isfinite(numerator):
        raise ValueError("Zero-power fit produced a non-finite least-squares system")

    scaled_slope = numerator / denominator
    scaled_resistance_at_minimum_current_squared = (
        mean_scaled_resistance - scaled_slope * mean_x
    )
    slope = (scaled_slope / x_span) * resistance_scale
    scaled_zero_power_resistance = (
        scaled_resistance_at_minimum_current_squared - scaled_slope * (x_min / x_span)
    )
    zero_power_resistance = scaled_zero_power_resistance * resistance_scale
    if not math.isfinite(scaled_slope) or not math.isfinite(slope):
        raise ValueError("Zero-power fit must produce a finite resistance slope")
    if not math.isfinite(zero_power_resistance):
        raise ValueError("Zero-power fit must produce finite resistance")

    fitted_resistances = tuple(
        (scaled_resistance_at_minimum_current_squared + scaled_slope * value)
        * resistance_scale
        for value in scaled_x
    )
    residuals = tuple(
        observation.resistance_ohms - fitted
        for observation, fitted in zip(
            observations,
            fitted_resistances,
            strict=True,
        )
    )
    if not all(math.isfinite(value) for value in (*fitted_resistances, *residuals)):
        raise ValueError("Zero-power fit diagnostics must remain finite")
    return zero_power_resistance, slope, residuals


def _zero_power_fit_parameter_covariance(
    result: ZeroPowerResistanceFitResult,
) -> tuple[
    float | None,
    tuple[tuple[float, float], tuple[float, float]],
    _ZeroPowerFitUncertaintyMethod,
]:
    evidence = result.evidence
    uncertainties = evidence.resistance_standard_uncertainties_ohms
    if uncertainties is not None:
        weighted_covariance = _zero_power_weighted_fit_parameter_covariance(evidence)
        return (None, weighted_covariance, "resistance_standard_uncertainties")

    residual_standard_deviation = evidence.residual_standard_deviation_ohms
    if residual_standard_deviation == 0.0:
        return (
            0.0,
            ((0.0, 0.0), (0.0, 0.0)),
            "residual_variance_scaled_least_squares",
        )
    residual_variance = residual_standard_deviation * residual_standard_deviation
    if not math.isfinite(residual_variance) or residual_variance <= 0.0:
        raise ValueError(
            "Zero-power fit residual variance is not finitely representable"
        )

    current_squared = tuple(
        observation.current_squared_a2 for observation in evidence.observations
    )
    x_min = min(current_squared)
    x_span = max(current_squared) - x_min
    if not math.isfinite(x_span) or x_span <= 0.0:
        raise ValueError("Zero-power fit current-squared span must be positive")

    scaled_x = tuple((value - x_min) / x_span for value in current_squared)
    mean_scaled_x = math.fsum(scaled_x) / evidence.observation_count
    centered_sum_squares = math.fsum((value - mean_scaled_x) ** 2 for value in scaled_x)
    if not math.isfinite(centered_sum_squares) or centered_sum_squares <= 0.0:
        raise ValueError("Zero-power fit information matrix must be finite")

    residual_sd = residual_standard_deviation
    slope_sd_scaled = residual_sd / math.sqrt(centered_sum_squares)
    slope_sd = slope_sd_scaled / x_span
    zero_coordinate_scaled = x_min / x_span + mean_scaled_x
    intercept_sd = residual_sd * math.hypot(
        1.0 / math.sqrt(evidence.observation_count),
        zero_coordinate_scaled / math.sqrt(centered_sum_squares),
    )

    if (
        not math.isfinite(intercept_sd)
        or not math.isfinite(slope_sd)
        or intercept_sd <= 0.0
        or slope_sd <= 0.0
    ):
        raise ValueError(
            "Zero-power fit parameter standard uncertainties are not finitely "
            "representable"
        )

    intercept_variance = intercept_sd * intercept_sd
    slope_variance = slope_sd * slope_sd
    correlation_denominator = math.hypot(
        zero_coordinate_scaled,
        math.sqrt(centered_sum_squares / evidence.observation_count),
    )
    if correlation_denominator == 0.0 or not math.isfinite(correlation_denominator):
        raise ValueError("Zero-power fit covariance correlation must remain finite")
    correlation = -zero_coordinate_scaled / correlation_denominator
    covariance = correlation * intercept_sd * slope_sd
    values = (
        intercept_variance,
        slope_variance,
        covariance,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Zero-power fit parameter covariance must remain finite")
    if intercept_variance <= 0.0 or slope_variance <= 0.0:
        raise ValueError(
            "Zero-power fit parameter variances are not finitely representable"
        )
    if correlation != 0.0 and covariance == 0.0:
        raise ValueError(
            "Zero-power fit parameter covariance is not finitely representable"
        )

    return (
        residual_variance,
        (
            (intercept_variance, covariance),
            (covariance, slope_variance),
        ),
        "residual_variance_scaled_least_squares",
    )


def _zero_power_weighted_fit_parameter_covariance(
    evidence: ZeroPowerResistanceFitEvidence,
) -> tuple[tuple[float, float], tuple[float, float]]:
    uncertainties = evidence.resistance_standard_uncertainties_ohms
    if uncertainties is None:
        raise ValueError("Weighted fit covariance requires resistance uncertainties")

    current_squared = tuple(
        observation.current_squared_a2 for observation in evidence.observations
    )
    x_min = min(current_squared)
    x_span = max(current_squared) - x_min
    if not math.isfinite(x_span) or x_span <= 0.0:
        raise ValueError("Zero-power fit current-squared span must be positive")
    scaled_x = tuple((value - x_min) / x_span for value in current_squared)

    minimum_uncertainty = min(uncertainties)
    weights = evidence.effective_weights
    assert weights is not None
    total_weight = math.fsum(weights)
    mean_scaled_x = (
        math.fsum(
            weight * value for weight, value in zip(weights, scaled_x, strict=True)
        )
        / total_weight
    )
    centered_sum_squares = math.fsum(
        weight * (value - mean_scaled_x) ** 2
        for weight, value in zip(weights, scaled_x, strict=True)
    )
    if (
        not math.isfinite(total_weight)
        or total_weight <= 0.0
        or not math.isfinite(centered_sum_squares)
        or centered_sum_squares <= 0.0
    ):
        raise ValueError("Zero-power weighted-fit information matrix must be finite")

    zero_coordinate_scaled = -(x_min / x_span)
    offset_from_weighted_mean = zero_coordinate_scaled - mean_scaled_x
    scale_squared = minimum_uncertainty * minimum_uncertainty
    intercept_variance = scale_squared * (
        1.0 / total_weight
        + offset_from_weighted_mean * offset_from_weighted_mean / centered_sum_squares
    )
    slope_variance = scale_squared / (x_span * x_span * centered_sum_squares)
    covariance = (
        scale_squared * offset_from_weighted_mean / (x_span * centered_sum_squares)
    )
    values = (intercept_variance, slope_variance, covariance)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Zero-power weighted-fit covariance must remain finite")
    if intercept_variance <= 0.0 or slope_variance <= 0.0:
        raise ValueError(
            "Zero-power weighted-fit parameter variances must be greater than zero"
        )
    return (
        (intercept_variance, covariance),
        (covariance, slope_variance),
    )


def _two_parameter_covariance_variance(
    sensitivities: tuple[float, float],
    covariance: tuple[tuple[float, float], tuple[float, float]],
    *,
    quantity_name: str,
) -> float:
    first, second = sensitivities
    terms = (
        first * first * covariance[0][0],
        2.0 * first * second * covariance[0][1],
        second * second * covariance[1][1],
    )
    if not all(math.isfinite(term) for term in terms):
        raise ValueError(f"{quantity_name} variance must remain finite")
    variance = math.fsum(terms)
    if not math.isfinite(variance):
        raise ValueError(f"{quantity_name} variance must remain finite")

    # Small negative values can arise from roundoff in an otherwise
    # positive-semidefinite covariance quadratic form. Do not hide material
    # negative variance.
    scale = math.fsum(abs(term) for term in terms)
    tolerance = 32.0 * math.ulp(scale) if scale > 0.0 else 0.0
    if variance < -tolerance:
        raise ValueError(f"{quantity_name} variance must be non-negative")
    return max(0.0, variance)


def _zero_power_resistance_input_sensitivities(
    result: TwoCurrentZeroPowerResult,
) -> tuple[float, float, float, float]:
    evidence = result.evidence
    low = evidence.low_current_observation
    high = evidence.high_current_observation
    low_i2 = low.current_squared_a2
    high_i2 = high.current_squared_a2
    delta_i2 = evidence.current_squared_change_a2
    delta_i2_squared = delta_i2 * delta_i2
    if not math.isfinite(delta_i2_squared) or delta_i2_squared <= 0.0:
        raise ValueError(
            "Current-squared span is too small or too large for uncertainty propagation"
        )

    sensitivities = (
        (
            2.0
            * low.measurement_current_a
            * high_i2
            * (low.resistance_ohms - high.resistance_ohms)
            / delta_i2_squared
        ),
        high_i2 / delta_i2,
        (
            2.0
            * high.measurement_current_a
            * low_i2
            * (high.resistance_ohms - low.resistance_ohms)
            / delta_i2_squared
        ),
        -low_i2 / delta_i2,
    )
    if not all(math.isfinite(value) for value in sensitivities):
        raise ValueError("Zero-power resistance sensitivities must remain finite")
    return sensitivities


def _temperature_sensitivity_celsius_per_ohm(
    model: _RTDModel,
    temperature_c: float,
    *,
    name: str,
) -> float:
    sensitivity = _as_float(
        model.temperature_sensitivity_celsius_per_ohm(temperature_c),
        name=name,
    )
    if not math.isfinite(sensitivity):
        raise ValueError(f"{name} must be finite")
    return sensitivity


def _validate_two_current_correlation_matrix(
    matrix: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], ...]:
    try:
        rows = tuple(tuple(row) for row in matrix)
    except TypeError as error:
        raise TypeError("Correlation matrix must be an iterable of rows") from error
    if len(rows) != 4 or any(len(row) != 4 for row in rows):
        raise ValueError("Correlation matrix must be 4x4")

    tolerance = 1.0e-12
    normalized: list[list[float]] = []
    for row_index, row in enumerate(rows):
        normalized_row: list[float] = []
        for column_index, value in enumerate(row):
            correlation = _as_float(
                value,
                name=f"Correlation[{row_index},{column_index}]",
            )
            if not math.isfinite(correlation):
                raise ValueError("Correlation matrix entries must be finite")
            if correlation < -1.0 - tolerance or correlation > 1.0 + tolerance:
                raise ValueError("Correlation matrix entries must be between -1 and 1")
            normalized_row.append(min(1.0, max(-1.0, correlation)))
        normalized.append(normalized_row)

    for index in range(4):
        if not math.isclose(
            normalized[index][index],
            1.0,
            rel_tol=0.0,
            abs_tol=tolerance,
        ):
            raise ValueError("Correlation matrix diagonal entries must equal 1")
        normalized[index][index] = 1.0
        for other in range(index):
            left = normalized[index][other]
            right = normalized[other][index]
            if not math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance):
                raise ValueError("Correlation matrix must be symmetric")
            symmetric = (left + right) / 2.0
            normalized[index][other] = symmetric
            normalized[other][index] = symmetric

    _validate_positive_semidefinite_correlation_matrix(normalized)
    return (
        tuple(normalized[0]),
        tuple(normalized[1]),
        tuple(normalized[2]),
        tuple(normalized[3]),
    )


def _validate_positive_semidefinite_correlation_matrix(
    matrix: list[list[float]],
) -> None:
    """Validate a small correlation matrix with pivoted semidefinite elimination."""
    size = len(matrix)
    work = [row.copy() for row in matrix]
    tolerance = 1.0e-12

    for pivot_index in range(size):
        selected_index = max(
            range(pivot_index, size),
            key=lambda index: work[index][index],
        )
        selected_pivot = work[selected_index][selected_index]
        if selected_pivot < -tolerance:
            raise ValueError("Correlation matrix must be positive semidefinite")
        if selected_pivot <= tolerance:
            remainder_scale = max(
                abs(work[row][column])
                for row in range(pivot_index, size)
                for column in range(pivot_index, size)
            )
            if remainder_scale > tolerance:
                raise ValueError("Correlation matrix must be positive semidefinite")
            return

        if selected_index != pivot_index:
            work[pivot_index], work[selected_index] = (
                work[selected_index],
                work[pivot_index],
            )
            for work_row in work:
                work_row[pivot_index], work_row[selected_index] = (
                    work_row[selected_index],
                    work_row[pivot_index],
                )

        pivot = work[pivot_index][pivot_index]
        for row in range(pivot_index + 1, size):
            for column in range(row, size):
                updated = work[row][column] - (
                    work[row][pivot_index] * work[column][pivot_index] / pivot
                )
                work[row][column] = updated
                work[column][row] = updated


def _two_current_input_covariance_matrix(
    standard_uncertainties: TwoCurrentInputStandardUncertainties,
    correlation_matrix: TwoCurrentInputCorrelationMatrix | None,
) -> tuple[tuple[float, ...], ...]:
    values = standard_uncertainties.standard_uncertainty_vector
    if correlation_matrix is None:
        return tuple(
            tuple(
                values[row] * values[row] if row == column else 0.0
                for column in range(4)
            )
            for row in range(4)
        )
    return correlation_matrix.covariance_matrix(standard_uncertainties)


def _two_current_uncertainty_propagation(
    sensitivities: tuple[float, float, float, float],
    standard_uncertainties: TwoCurrentInputStandardUncertainties,
    correlation_matrix: TwoCurrentInputCorrelationMatrix | None,
    *,
    quantity_name: str,
) -> tuple[float, float]:
    if correlation_matrix is None:
        return _independent_propagation(
            sensitivities,
            standard_uncertainties.standard_uncertainty_vector,
            quantity_name=quantity_name,
        )
    return _covariance_propagation(
        sensitivities,
        correlation_matrix.covariance_matrix(standard_uncertainties),
        quantity_name=quantity_name,
    )


def _covariance_propagation(
    sensitivities: tuple[float, float, float, float],
    covariance_matrix: tuple[tuple[float, ...], ...],
    *,
    quantity_name: str,
) -> tuple[float, float]:
    variance = math.fsum(
        sensitivities[row] * covariance_matrix[row][column] * sensitivities[column]
        for row in range(4)
        for column in range(4)
    )
    scale = math.fsum(
        abs(sensitivities[row] * covariance_matrix[row][column] * sensitivities[column])
        for row in range(4)
        for column in range(4)
    )
    tolerance = 64.0 * math.ulp(scale) if math.isfinite(scale) else 0.0
    if variance < 0.0 and abs(variance) <= tolerance:
        variance = 0.0
    if not math.isfinite(variance) or variance < 0.0:
        raise ValueError(f"{quantity_name} variance must be finite and non-negative")
    standard_uncertainty = math.sqrt(variance)
    if not math.isfinite(standard_uncertainty):
        raise ValueError(f"{quantity_name} must remain finite")
    return variance, standard_uncertainty


def _independent_propagation(
    sensitivities: tuple[float, float, float, float],
    standard_uncertainties: tuple[float, float, float, float],
    *,
    quantity_name: str,
) -> tuple[float, float]:
    contributions = tuple(
        sensitivity * standard_uncertainty
        for sensitivity, standard_uncertainty in zip(
            sensitivities,
            standard_uncertainties,
            strict=True,
        )
    )
    standard_uncertainty = math.hypot(*contributions)
    if not math.isfinite(standard_uncertainty):
        raise ValueError(f"{quantity_name} must remain finite")
    variance = standard_uncertainty * standard_uncertainty
    if not math.isfinite(variance):
        raise ValueError(f"{quantity_name} variance must remain finite")
    return variance, standard_uncertainty


def _converted_temperature_c(
    model: _RTDModel,
    resistance_ohms: float,
    *,
    name: str,
) -> float:
    temperature = _as_float(
        model.resistance_to_celsius(resistance_ohms),
        name=name,
    )
    if not math.isfinite(temperature):
        raise ValueError(f"{name} must be finite")
    return temperature


def _zero_power_resistance_from_evidence(
    evidence: TwoCurrentZeroPowerEvidence,
) -> float:
    low = evidence.low_current_observation
    slope = evidence.resistance_slope_ohms_per_a2
    return low.resistance_ohms - slope * low.current_squared_a2


def extrapolate_zero_power_resistance(
    observation_1: SelfHeatingObservation,
    observation_2: SelfHeatingObservation,
) -> TwoCurrentZeroPowerResult:
    """Extrapolate RTD resistance to zero measurement current from two observations.

    The method assumes both observations describe the same stable external thermal
    condition and that resistance is linear in measurement-current squared over the
    two supplied current levels. The observations must therefore use distinct
    positive current magnitudes.

    This function intentionally performs only the two-current resistance-domain
    extrapolation. It does not infer temperature, assess multi-point linearity, or
    establish that the experimental thermal condition was stable. Uncertainty can
    be propagated separately with
    :func:`propagate_two_current_zero_power_uncertainty`.

    Raises:
        TypeError: If either argument is not a :class:`SelfHeatingObservation`.
        ValueError: If both observations use the same current magnitude or the
            extrapolated zero-power resistance is not finite and positive.
    """
    if not isinstance(observation_1, SelfHeatingObservation):
        raise TypeError("observation_1 must be a SelfHeatingObservation")
    if not isinstance(observation_2, SelfHeatingObservation):
        raise TypeError("observation_2 must be a SelfHeatingObservation")

    if observation_1.measurement_current_a < observation_2.measurement_current_a:
        low = observation_1
        high = observation_2
    elif observation_2.measurement_current_a < observation_1.measurement_current_a:
        low = observation_2
        high = observation_1
    else:
        raise ValueError("Two-current extrapolation requires distinct current levels")

    evidence = TwoCurrentZeroPowerEvidence(
        low_current_observation=low,
        high_current_observation=high,
    )
    zero_power_resistance = _zero_power_resistance_from_evidence(evidence)

    if not math.isfinite(zero_power_resistance):
        raise ValueError("Zero-power extrapolation must produce finite resistance")
    if zero_power_resistance <= 0.0:
        raise ValueError(
            "Zero-power extrapolation must produce resistance greater than zero"
        )

    return TwoCurrentZeroPowerResult(
        zero_power_resistance_ohms=zero_power_resistance,
        evidence=evidence,
    )
