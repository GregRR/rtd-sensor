# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Internal RTD model definitions."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._curves import IEC_60751_PT385, RTDCurve

__all__ = [
    "PT100_IEC_60751",
    "PT1000_IEC_60751",
    "RTDModel",
]


@dataclass(frozen=True, slots=True)
class RTDModel:
    """Combine a normalized RTD curve with its resistance at 0 °C."""

    name: str
    r0_ohms: float
    curve: RTDCurve

    def __post_init__(self) -> None:
        r0_ohms = float(self.r0_ohms)
        if not math.isfinite(r0_ohms):
            raise ValueError("R0 must be finite")
        if r0_ohms <= 0.0:
            raise ValueError("R0 must be greater than zero")
        object.__setattr__(self, "r0_ohms", r0_ohms)

    @property
    def minimum_temperature_c(self) -> float:
        """Return the model's minimum supported temperature."""
        return self.curve.minimum_temperature_c

    @property
    def maximum_temperature_c(self) -> float:
        """Return the model's maximum supported temperature."""
        return self.curve.maximum_temperature_c

    def celsius_to_resistance(self, temperature_c: float) -> float:
        """Convert Celsius to ideal RTD resistance in ohms."""
        resistance_ratio = self.curve.resistance_ratio(temperature_c)
        return self.r0_ohms * resistance_ratio

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        """Convert RTD resistance in ohms to Celsius."""
        resistance = float(resistance_ohms)
        self._validate_resistance(resistance)
        resistance_ratio = resistance / self.r0_ohms
        return self.curve.temperature_from_resistance_ratio(
            resistance_ratio
        )

    def resistance_sensitivity_ohms_per_celsius(
        self,
        temperature_c: float,
    ) -> float:
        """Return the exact local resistance sensitivity dR/dT."""
        return self.r0_ohms * self.curve.resistance_ratio_slope(temperature_c)

    def temperature_sensitivity_celsius_per_ohm(
        self,
        temperature_c: float,
    ) -> float:
        """Return the exact local inverse sensitivity dT/dR."""
        resistance_sensitivity = self.resistance_sensitivity_ohms_per_celsius(
            temperature_c
        )
        return 1.0 / resistance_sensitivity

    def _validate_resistance(self, resistance_ohms: float) -> None:
        if not math.isfinite(resistance_ohms):
            raise ValueError("Resistance must be finite")
        if resistance_ohms <= 0.0:
            raise ValueError("Resistance must be greater than zero")

        minimum_resistance = self.celsius_to_resistance(
            self.minimum_temperature_c
        )
        maximum_resistance = self.celsius_to_resistance(
            self.maximum_temperature_c
        )

        if resistance_ohms < minimum_resistance:
            raise ValueError(
                f"Resistance is below the supported {self.name} range"
            )
        if resistance_ohms > maximum_resistance:
            raise ValueError(
                f"Resistance is above the supported {self.name} range"
            )


PT100_IEC_60751 = RTDModel(
    name="Pt100",
    r0_ohms=100.0,
    curve=IEC_60751_PT385,
)


PT1000_IEC_60751 = RTDModel(
    name="Pt1000",
    r0_ohms=1000.0,
    curve=IEC_60751_PT385,
)
