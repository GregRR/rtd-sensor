# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public configurable RTD models.

The built-in :mod:`rtd.pt100` and :mod:`rtd.pt1000` modules remain the
simplest interfaces for nominal IEC 60751 sensors. This module provides
advanced models for individually characterized RTDs and for platinum
RTDs with user-supplied Callendar-Van Dusen coefficient sets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ._curves import IEC_60751_PT385
from ._curves import CallendarVanDusenCurve as _CallendarVanDusenCurve
from ._models import RTDModel as _RTDModel

__all__ = [
    "CallendarVanDusenRTDModel",
    "IEC60751RTDModel",
]


@dataclass(frozen=True, slots=True)
class IEC60751RTDModel:
    """Configurable RTD using the IEC 60751 PT-385 curve.

    This model is useful when an individual sensor has a characterized
    or calibrated R0 value but still uses the standard IEC 60751 curve.
    The optional temperature limits can restrict the model to a probe's
    declared or calibrated operating range without changing the
    underlying standardized curve.

    Args:
        r0_ohms: Sensor resistance at 0 °C in ohms.
        name: Human-readable model or probe name.
        minimum_temperature_c: Lowest temperature at which this model
            should be used.
        maximum_temperature_c: Highest temperature at which this model
            should be used.

    Raises:
        ValueError: If R0 or either temperature limit is invalid, if the
            limits are reversed, or if the declared range extends beyond
            the IEC 60751 PT-385 curve implemented by this package.
    """

    r0_ohms: float
    name: str = "IEC 60751 RTD"
    minimum_temperature_c: float = IEC_60751_PT385.minimum_temperature_c
    maximum_temperature_c: float = IEC_60751_PT385.maximum_temperature_c
    _model: _RTDModel = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        minimum_temperature_c = float(self.minimum_temperature_c)
        maximum_temperature_c = float(self.maximum_temperature_c)

        if not math.isfinite(minimum_temperature_c):
            raise ValueError("Minimum temperature must be finite")
        if not math.isfinite(maximum_temperature_c):
            raise ValueError("Maximum temperature must be finite")
        if minimum_temperature_c >= maximum_temperature_c:
            raise ValueError(
                "Minimum temperature must be below maximum temperature"
            )
        if minimum_temperature_c < IEC_60751_PT385.minimum_temperature_c:
            raise ValueError(
                "Minimum temperature is below the IEC 60751 PT-385 range"
            )
        if maximum_temperature_c > IEC_60751_PT385.maximum_temperature_c:
            raise ValueError(
                "Maximum temperature is above the IEC 60751 PT-385 range"
            )

        model = _RTDModel(
            name=self.name,
            r0_ohms=self.r0_ohms,
            curve=IEC_60751_PT385,
        )

        object.__setattr__(self, "r0_ohms", model.r0_ohms)
        object.__setattr__(
            self,
            "minimum_temperature_c",
            minimum_temperature_c,
        )
        object.__setattr__(
            self,
            "maximum_temperature_c",
            maximum_temperature_c,
        )
        object.__setattr__(self, "_model", model)

    def celsius_to_resistance(self, temperature_c: float) -> float:
        """Convert Celsius to resistance using this RTD model."""
        temperature = float(temperature_c)
        self._validate_temperature(temperature)
        return self._model.celsius_to_resistance(temperature)

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        """Convert resistance in ohms to Celsius using this RTD model."""
        resistance = float(resistance_ohms)
        self._validate_resistance(resistance)
        return self._model.resistance_to_celsius(resistance)

    def _validate_temperature(self, temperature_c: float) -> None:
        if not math.isfinite(temperature_c):
            raise ValueError("Temperature must be finite")
        if not (
            self.minimum_temperature_c
            <= temperature_c
            <= self.maximum_temperature_c
        ):
            raise ValueError(
                "Temperature must be between "
                f"{self.minimum_temperature_c:g} °C and "
                f"{self.maximum_temperature_c:g} °C"
            )

    def _validate_resistance(self, resistance_ohms: float) -> None:
        if not math.isfinite(resistance_ohms):
            raise ValueError("Resistance must be finite")
        if resistance_ohms <= 0.0:
            raise ValueError("Resistance must be greater than zero")

        minimum_resistance = self._model.celsius_to_resistance(
            self.minimum_temperature_c
        )
        maximum_resistance = self._model.celsius_to_resistance(
            self.maximum_temperature_c
        )

        if resistance_ohms < minimum_resistance:
            raise ValueError("Resistance is below the declared model range")
        if resistance_ohms > maximum_resistance:
            raise ValueError("Resistance is above the declared model range")


@dataclass(frozen=True, slots=True, kw_only=True)
class CallendarVanDusenRTDModel:
    """Platinum RTD model with user-supplied CVD coefficients.

    This model is intended for coefficient sets supplied by a calibration
    certificate, manufacturer, or another traceable technical source. It
    uses the IEC-style ``R0, A, B, C`` form of the Callendar-Van Dusen
    equation, but a model created with custom coefficients is *not*
    automatically an IEC 60751 compliant model.

    ``C`` is used only below 0 °C. It may therefore be omitted when the
    declared valid range is entirely at or above 0 °C. A negative-temperature
    range requires an explicit ``C`` value.

    The supplied coefficients must produce a finite, positive-resistance,
    strictly increasing curve over the interval needed to invert the declared
    model range. This validates the mathematical behavior actually required by
    the converter rather than assuming that custom coefficients have the same
    signs as the standard IEC coefficient set.

    Args:
        r0_ohms: Sensor resistance at 0 °C in ohms.
        a: Callendar-Van Dusen A coefficient in °C⁻¹.
        b: Callendar-Van Dusen B coefficient in °C⁻².
        c: Callendar-Van Dusen C coefficient in °C⁻⁴. May be ``None`` only
            when ``minimum_temperature_c`` is at or above 0 °C.
        minimum_temperature_c: Lowest temperature for which the supplied
            coefficient set is declared valid.
        maximum_temperature_c: Highest temperature for which the supplied
            coefficient set is declared valid.
        name: Human-readable model or probe name.
        coefficient_source: Optional free-form provenance such as a
            calibration-certificate identifier, manufacturer document, or
            other source of the coefficient set. It is retained as metadata
            and does not affect calculations.

    Raises:
        ValueError: If any numerical input is invalid, if the range is
            reversed, if ``C`` is missing for a negative-temperature range,
            or if the coefficients do not define a finite, positive, strictly
            increasing RTD curve over the required inversion interval.
    """

    r0_ohms: float
    a: float
    b: float
    minimum_temperature_c: float
    maximum_temperature_c: float
    c: float | None = None
    name: str = "Custom Callendar-Van Dusen RTD"
    coefficient_source: str | None = None
    _model: _RTDModel = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        r0_ohms = float(self.r0_ohms)
        a = float(self.a)
        b = float(self.b)
        minimum_temperature_c = float(self.minimum_temperature_c)
        maximum_temperature_c = float(self.maximum_temperature_c)
        c = None if self.c is None else float(self.c)

        if not math.isfinite(r0_ohms):
            raise ValueError("R0 must be finite")
        if r0_ohms <= 0.0:
            raise ValueError("R0 must be greater than zero")
        if not math.isfinite(a):
            raise ValueError("A coefficient must be finite")
        if not math.isfinite(b):
            raise ValueError("B coefficient must be finite")
        if c is not None and not math.isfinite(c):
            raise ValueError("C coefficient must be finite")
        if not math.isfinite(minimum_temperature_c):
            raise ValueError("Minimum temperature must be finite")
        if not math.isfinite(maximum_temperature_c):
            raise ValueError("Maximum temperature must be finite")
        if minimum_temperature_c >= maximum_temperature_c:
            raise ValueError(
                "Minimum temperature must be below maximum temperature"
            )

        if minimum_temperature_c < 0.0 and c is None:
            raise ValueError(
                "C coefficient is required for a negative-temperature range"
            )

        effective_c = 0.0 if c is None else c
        curve_minimum_c = min(minimum_temperature_c, 0.0)
        curve_maximum_c = max(maximum_temperature_c, 0.0)

        curve = _CallendarVanDusenCurve(
            name=f"{self.name} Callendar-Van Dusen curve",
            a=a,
            b=b,
            c=effective_c,
            minimum_temperature_c=curve_minimum_c,
            maximum_temperature_c=curve_maximum_c,
        )

        coefficient_source = self.coefficient_source
        if coefficient_source is not None:
            coefficient_source = coefficient_source.strip()
            if not coefficient_source:
                raise ValueError("Coefficient source must not be empty")

        model = _RTDModel(
            name=self.name,
            r0_ohms=r0_ohms,
            curve=curve,
        )

        object.__setattr__(self, "r0_ohms", model.r0_ohms)
        object.__setattr__(self, "a", a)
        object.__setattr__(self, "b", b)
        object.__setattr__(self, "c", c)
        object.__setattr__(
            self,
            "minimum_temperature_c",
            minimum_temperature_c,
        )
        object.__setattr__(
            self,
            "maximum_temperature_c",
            maximum_temperature_c,
        )
        object.__setattr__(self, "coefficient_source", coefficient_source)
        object.__setattr__(self, "_model", model)

    def celsius_to_resistance(self, temperature_c: float) -> float:
        """Convert Celsius to resistance using this coefficient set."""
        temperature = float(temperature_c)
        self._validate_temperature(temperature)
        return self._model.celsius_to_resistance(temperature)

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        """Convert resistance in ohms to Celsius using this coefficient set."""
        resistance = float(resistance_ohms)
        self._validate_resistance(resistance)
        return self._model.resistance_to_celsius(resistance)

    def _validate_temperature(self, temperature_c: float) -> None:
        if not math.isfinite(temperature_c):
            raise ValueError("Temperature must be finite")
        if not (
            self.minimum_temperature_c
            <= temperature_c
            <= self.maximum_temperature_c
        ):
            raise ValueError(
                "Temperature must be between "
                f"{self.minimum_temperature_c:g} °C and "
                f"{self.maximum_temperature_c:g} °C"
            )

    def _validate_resistance(self, resistance_ohms: float) -> None:
        if not math.isfinite(resistance_ohms):
            raise ValueError("Resistance must be finite")
        if resistance_ohms <= 0.0:
            raise ValueError("Resistance must be greater than zero")

        minimum_resistance = self._model.celsius_to_resistance(
            self.minimum_temperature_c
        )
        maximum_resistance = self._model.celsius_to_resistance(
            self.maximum_temperature_c
        )

        if resistance_ohms < minimum_resistance:
            raise ValueError("Resistance is below the declared model range")
        if resistance_ohms > maximum_resistance:
            raise ValueError("Resistance is above the declared model range")
