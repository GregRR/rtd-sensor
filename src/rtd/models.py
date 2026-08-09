# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public configurable RTD models.

The built-in :mod:`rtd.pt100` and :mod:`rtd.pt1000` modules remain the
simplest interfaces for nominal IEC 60751 sensors. This module provides
an advanced model for an RTD whose resistance at 0 °C (R0) has been
individually characterized while retaining the standard IEC 60751
PT-385 resistance-temperature curve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ._curves import IEC_60751_PT385
from ._models import RTDModel as _RTDModel

__all__ = ["IEC60751RTDModel"]


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
