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
from dataclasses import dataclass, field
from typing import Literal

from ._protocols import RTDModel as _RTDModel
from ._validation import as_float as _as_float

__all__ = [
    "SelfHeatingObservation",
    "TwoCurrentZeroPowerEvidence",
    "TwoCurrentSelfHeatingTemperatureResult",
    "TwoCurrentZeroPowerResult",
    "evaluate_two_current_temperatures",
    "extrapolate_zero_power_resistance",
]

_TwoCurrentMethod = Literal["linear_resistance_vs_current_squared"]


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
    extrapolation. It does not infer temperature, assess multi-point linearity,
    propagate uncertainty, or establish that the experimental thermal condition was
    stable; those are separate 0.8.0 capabilities.

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
    if evidence.current_squared_change_a2 <= 0.0:
        raise ValueError(
            "Two-current extrapolation requires numerically distinct "
            "current-squared levels"
        )
    slope = evidence.resistance_slope_ohms_per_a2
    zero_power_resistance = low.resistance_ohms - slope * low.current_squared_a2

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
