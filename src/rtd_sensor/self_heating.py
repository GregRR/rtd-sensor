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
    "SelfHeatingObservation",
    "ZeroPowerResistanceFitEvidence",
    "ZeroPowerResistanceFitResult",
    "TwoCurrentInputStandardUncertainties",
    "TwoCurrentSelfHeatingTemperatureResult",
    "TwoCurrentSelfHeatingTemperatureUncertaintyResult",
    "TwoCurrentZeroPowerEvidence",
    "TwoCurrentZeroPowerResult",
    "TwoCurrentZeroPowerUncertaintyResult",
    "evaluate_two_current_temperatures",
    "fit_zero_power_resistance",
    "extrapolate_zero_power_resistance",
    "propagate_two_current_temperature_uncertainty",
    "propagate_two_current_zero_power_uncertainty",
]

_TwoCurrentMethod = Literal["linear_resistance_vs_current_squared"]
_ZeroPowerFitMethod = Literal["ordinary_least_squares_resistance_vs_current_squared"]
_TwoCurrentUncertaintyMethod = Literal["first_order_independent_inputs"]
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

    Residual diagnostics can reveal scatter or departures from the fitted linear
    ``R``-versus-``I²`` relationship, but they do not by themselves prove that the
    external temperature was stable or that a physical self-heating correction is
    valid.
    """

    observations: tuple[SelfHeatingObservation, ...]
    residuals_ohms: tuple[float, ...]
    method: _ZeroPowerFitMethod = field(
        init=False,
        default="ordinary_least_squares_resistance_vs_current_squared",
    )

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

        distinct_current_squared = {
            observation.current_squared_a2 for observation in observations
        }
        if len(distinct_current_squared) < 2:
            raise ValueError(
                "Zero-power fitting requires at least two distinct current levels"
            )

        _, _, expected_residuals = _fit_zero_power_line(observations)
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
    """Unweighted 3+ observation zero-power resistance fit and evidence."""

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
            self.evidence.observations
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


@dataclass(frozen=True, slots=True, kw_only=True)
class TwoCurrentInputStandardUncertainties:
    """Independent standard uncertainties for the four two-current inputs.

    Fields correspond to the normalized low- and high-current observations retained
    by :class:`TwoCurrentZeroPowerEvidence`. All values are non-negative standard
    uncertainties. This first uncertainty model assumes the four inputs are
    mutually independent; covariance between repeated current or resistance
    measurements is not inferred.
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
    """First-order uncertainty propagated to two-current zero-power resistance."""

    zero_power_result: TwoCurrentZeroPowerResult
    input_standard_uncertainties: TwoCurrentInputStandardUncertainties
    zero_power_resistance_input_sensitivity_vector: tuple[float, float, float, float]
    zero_power_resistance_variance_ohms_squared: float
    zero_power_resistance_standard_uncertainty_ohms: float
    propagation_method: _TwoCurrentUncertaintyMethod = field(
        init=False,
        default="first_order_independent_inputs",
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
    zero_power_temperature_c: float
    low_current_temperature_c: float
    high_current_temperature_c: float

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
    directly from the original current/resistance inputs so the shared
    zero-power estimate is not incorrectly treated as independent of each
    observed resistance.
    """

    temperature_result: TwoCurrentSelfHeatingTemperatureResult
    zero_power_uncertainty: TwoCurrentZeroPowerUncertaintyResult
    zero_power_temperature_input_sensitivity_vector: tuple[float, float, float, float]
    low_current_temperature_input_sensitivity_vector: tuple[float, float, float, float]
    high_current_temperature_input_sensitivity_vector: tuple[float, float, float, float]
    low_current_temperature_rise_input_sensitivity_vector: tuple[
        float, float, float, float
    ]
    high_current_temperature_rise_input_sensitivity_vector: tuple[
        float, float, float, float
    ]
    zero_power_temperature_variance_celsius_squared: float
    zero_power_temperature_standard_uncertainty_c: float
    low_current_temperature_variance_celsius_squared: float
    low_current_temperature_standard_uncertainty_c: float
    high_current_temperature_variance_celsius_squared: float
    high_current_temperature_standard_uncertainty_c: float
    low_current_temperature_rise_variance_celsius_squared: float
    low_current_temperature_rise_standard_uncertainty_c: float
    high_current_temperature_rise_variance_celsius_squared: float
    high_current_temperature_rise_standard_uncertainty_c: float
    propagation_method: _TwoCurrentUncertaintyMethod = field(
        init=False,
        default="first_order_independent_inputs",
    )

    @property
    def input_parameter_names(self) -> tuple[str, str, str, str]:
        """Return the input order used by all retained sensitivity vectors."""
        return _TWO_CURRENT_INPUT_PARAMETER_NAMES


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

    evidence = result.evidence
    zero_power_temperature = _converted_temperature_c(
        model,
        result.zero_power_resistance_ohms,
        name="Zero-power temperature",
    )
    low_current_temperature = _converted_temperature_c(
        model,
        evidence.low_current_observation.resistance_ohms,
        name="Low-current temperature",
    )
    high_current_temperature = _converted_temperature_c(
        model,
        evidence.high_current_observation.resistance_ohms,
        name="High-current temperature",
    )

    return TwoCurrentSelfHeatingTemperatureResult(
        zero_power_result=result,
        model=model,
        zero_power_temperature_c=zero_power_temperature,
        low_current_temperature_c=low_current_temperature,
        high_current_temperature_c=high_current_temperature,
    )


def propagate_two_current_zero_power_uncertainty(
    result: TwoCurrentZeroPowerResult,
    *,
    input_standard_uncertainties: TwoCurrentInputStandardUncertainties,
) -> TwoCurrentZeroPowerUncertaintyResult:
    """Propagate independent input uncertainties to zero-power resistance.

    The first-order law of propagation is applied to the original four inputs in
    normalized low/high-current order: ``I_low``, ``R_low``, ``I_high``, and
    ``R_high``. Current and resistance uncertainties may therefore contribute to
    the extrapolated intercept. The four supplied input standard uncertainties are
    assumed mutually independent.

    This result contains only measurement-input uncertainty for the two-current
    extrapolation. It does not add model uncertainty, thermal-drift effects, or
    covariance between the supplied measurements.
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

    sensitivities = _zero_power_resistance_input_sensitivities(result)
    variance, standard_uncertainty = _independent_propagation(
        sensitivities,
        input_standard_uncertainties.standard_uncertainty_vector,
        quantity_name="Zero-power resistance uncertainty",
    )

    return TwoCurrentZeroPowerUncertaintyResult(
        zero_power_result=result,
        input_standard_uncertainties=input_standard_uncertainties,
        zero_power_resistance_input_sensitivity_vector=sensitivities,
        zero_power_resistance_variance_ohms_squared=variance,
        zero_power_resistance_standard_uncertainty_ohms=standard_uncertainty,
    )


def propagate_two_current_temperature_uncertainty(
    result: TwoCurrentSelfHeatingTemperatureResult,
    *,
    input_standard_uncertainties: TwoCurrentInputStandardUncertainties,
) -> TwoCurrentSelfHeatingTemperatureUncertaintyResult:
    """Propagate independent two-current input uncertainties into temperatures.

    The calculation uses first-order local RTD sensitivities from the exact model
    retained by ``result``. Zero-power temperature, observed temperatures, and
    observed-minus-zero-power temperature rises are all propagated directly from
    the original four inputs. This preserves the dependence created because the
    zero-power estimate is calculated from the same resistance observations.

    Fitted-model covariance and other uncertainty-budget components remain
    separate and are not combined automatically.
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
    )
    zero_resistance_sensitivities = (
        zero_power_uncertainty.zero_power_resistance_input_sensitivity_vector
    )

    zero_temperature_sensitivity = _temperature_sensitivity_celsius_per_ohm(
        result.model,
        result.zero_power_temperature_c,
        name="Zero-power temperature sensitivity",
    )
    low_temperature_sensitivity = _temperature_sensitivity_celsius_per_ohm(
        result.model,
        result.low_current_temperature_c,
        name="Low-current temperature sensitivity",
    )
    high_temperature_sensitivity = _temperature_sensitivity_celsius_per_ohm(
        result.model,
        result.high_current_temperature_c,
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

    standard_uncertainties = input_standard_uncertainties.standard_uncertainty_vector
    zero_temperature_variance, zero_temperature_uncertainty = _independent_propagation(
        zero_temperature_vector,
        standard_uncertainties,
        quantity_name="Zero-power temperature uncertainty",
    )
    low_temperature_variance, low_temperature_uncertainty = _independent_propagation(
        low_temperature_vector,
        standard_uncertainties,
        quantity_name="Low-current temperature uncertainty",
    )
    high_temperature_variance, high_temperature_uncertainty = _independent_propagation(
        high_temperature_vector,
        standard_uncertainties,
        quantity_name="High-current temperature uncertainty",
    )
    low_rise_variance, low_rise_uncertainty = _independent_propagation(
        low_rise_vector,
        standard_uncertainties,
        quantity_name="Low-current temperature-rise uncertainty",
    )
    high_rise_variance, high_rise_uncertainty = _independent_propagation(
        high_rise_vector,
        standard_uncertainties,
        quantity_name="High-current temperature-rise uncertainty",
    )

    return TwoCurrentSelfHeatingTemperatureUncertaintyResult(
        temperature_result=result,
        zero_power_uncertainty=zero_power_uncertainty,
        zero_power_temperature_input_sensitivity_vector=zero_temperature_vector,
        low_current_temperature_input_sensitivity_vector=low_temperature_vector,
        high_current_temperature_input_sensitivity_vector=high_temperature_vector,
        low_current_temperature_rise_input_sensitivity_vector=low_rise_vector,
        high_current_temperature_rise_input_sensitivity_vector=high_rise_vector,
        zero_power_temperature_variance_celsius_squared=zero_temperature_variance,
        zero_power_temperature_standard_uncertainty_c=zero_temperature_uncertainty,
        low_current_temperature_variance_celsius_squared=low_temperature_variance,
        low_current_temperature_standard_uncertainty_c=low_temperature_uncertainty,
        high_current_temperature_variance_celsius_squared=high_temperature_variance,
        high_current_temperature_standard_uncertainty_c=high_temperature_uncertainty,
        low_current_temperature_rise_variance_celsius_squared=low_rise_variance,
        low_current_temperature_rise_standard_uncertainty_c=low_rise_uncertainty,
        high_current_temperature_rise_variance_celsius_squared=high_rise_variance,
        high_current_temperature_rise_standard_uncertainty_c=high_rise_uncertainty,
    )


def fit_zero_power_resistance(
    observations: Iterable[SelfHeatingObservation],
) -> ZeroPowerResistanceFitResult:
    """Fit ``R = R0 + k*I²`` to at least three current/resistance observations.

    The fit uses ordinary least squares in resistance with measurement-current
    squared as the independent coordinate. At least three observations provide
    positive residual degrees of freedom; repeated measurements at only two
    current levels are allowed and can therefore retain repeated-cycle scatter.

    Observations remain in caller-supplied order in the returned evidence. The
    residual diagnostics describe consistency with the fitted linear relation but
    do not prove that the external temperature was stable. A zero or negative
    slope is retained rather than converted into a claim of valid self-heating.

    This first multi-observation fit is unweighted. Measurement-current uncertainty,
    resistance uncertainty, correlated effects, and automatic pass/fail thresholds
    are not included in the least-squares objective.

    Raises:
        TypeError: If any supplied value is not a :class:`SelfHeatingObservation`.
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

    zero_power_resistance, slope, residuals = _fit_zero_power_line(observation_tuple)
    if not math.isfinite(zero_power_resistance):
        raise ValueError("Zero-power fit must produce finite resistance")
    if zero_power_resistance <= 0.0:
        raise ValueError("Zero-power fit must produce resistance greater than zero")

    evidence = ZeroPowerResistanceFitEvidence(
        observations=observation_tuple,
        residuals_ohms=residuals,
    )
    return ZeroPowerResistanceFitResult(
        zero_power_resistance_ohms=zero_power_resistance,
        resistance_slope_ohms_per_a2=slope,
        evidence=evidence,
    )


def _fit_zero_power_line(
    observations: tuple[SelfHeatingObservation, ...],
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

    count = len(observations)
    mean_x = math.fsum(scaled_x) / count
    mean_scaled_resistance = math.fsum(scaled_resistance) / count
    centered_x = tuple(value - mean_x for value in scaled_x)
    centered_resistance = tuple(
        value - mean_scaled_resistance for value in scaled_resistance
    )
    denominator = math.fsum(value * value for value in centered_x)
    numerator = math.fsum(
        x_value * resistance_value
        for x_value, resistance_value in zip(
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
