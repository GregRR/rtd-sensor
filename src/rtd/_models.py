# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Internal RTD model definitions."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ._curves import (
    IEC_60751_PT385,
    NI_5000_TK5000,
    NI_6180_DIN_43760,
    NI_6720_NORTH_AMERICAN,
    RTDCurve,
)
from ._validation import as_float as _as_float

__all__ = [
    "PT100_IEC_60751",
    "PT500_IEC_60751",
    "NI1000_6180",
    "NI1000_TK5000",
    "NI120_6720",
    "PT1000_IEC_60751",
    "RTDModel",
]


@dataclass(frozen=True, slots=True)
class RTDModel:
    """Combine a normalized RTD curve with its reference resistance.

    The curve defines the temperature at which its normalized ratio is 1.
    Keeping that reference temperature in the curve allows the same scaling
    model to represent traditional ``R0`` characteristics referenced at
    0 °C as well as future characteristics referenced at another temperature.
    """

    name: str
    reference_resistance_ohms: float
    curve: RTDCurve
    identity: str | None = None

    def __post_init__(self) -> None:
        reference_resistance_ohms = _as_float(
            self.reference_resistance_ohms,
            name="Reference resistance",
        )
        if not math.isfinite(reference_resistance_ohms):
            raise ValueError("Reference resistance must be finite")
        if reference_resistance_ohms <= 0.0:
            raise ValueError("Reference resistance must be greater than zero")
        object.__setattr__(self, "reference_resistance_ohms", reference_resistance_ohms)

        if self.identity is not None and (
            not self.identity or self.identity != self.identity.strip()
        ):
            raise ValueError("RTD model identity must be a non-empty, trimmed string")

    @property
    def reference_temperature_c(self) -> float:
        """Return the curve temperature associated with the reference resistance."""
        return self.curve.reference_temperature_c

    @property
    def r0_ohms(self) -> float:
        """Return the reference resistance for 0 °C-based characteristics.

        This compatibility property supports the existing Pt100/Pt500/Pt1000
        and configurable CVD APIs, all of which are referenced at 0 °C. New
        generic code should prefer ``reference_resistance_ohms``.
        """
        if self.reference_temperature_c != 0.0:
            raise AttributeError("This RTD model is not referenced at 0 °C")
        return self.reference_resistance_ohms

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
        return self.reference_resistance_ohms * resistance_ratio

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        """Convert RTD resistance in ohms to Celsius."""
        resistance = _as_float(resistance_ohms, name="Resistance")
        self._validate_resistance(resistance)
        resistance_ratio = resistance / self.reference_resistance_ohms
        return self.curve.temperature_from_resistance_ratio(resistance_ratio)

    def resistance_sensitivity_ohms_per_celsius(
        self,
        temperature_c: float,
    ) -> float:
        """Return the exact local resistance sensitivity dR/dT."""
        return self.reference_resistance_ohms * self.curve.resistance_ratio_slope(
            temperature_c
        )

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

        minimum_resistance = self.celsius_to_resistance(self.minimum_temperature_c)
        maximum_resistance = self.celsius_to_resistance(self.maximum_temperature_c)

        if resistance_ohms < minimum_resistance:
            raise ValueError(f"Resistance is below the supported {self.name} range")
        if resistance_ohms > maximum_resistance:
            raise ValueError(f"Resistance is above the supported {self.name} range")


_BUILTIN_RTD_MODELS: dict[str, RTDModel] = {}


def _built_in_model(
    *,
    identity: str,
    name: str,
    reference_resistance_ohms: float,
    curve: RTDCurve,
) -> RTDModel:
    """Create and register one built-in model under its simulation identity.

    Built-in identity belongs with the model definition rather than in the
    simulation module. Keeping registration here gives the package one
    authoritative identity-to-model mapping and prevents a new RTD from being
    added to conversion APIs while simulation silently retains a stale list.
    """
    if identity in _BUILTIN_RTD_MODELS:
        raise RuntimeError(f"Duplicate built-in RTD identity: {identity!r}")

    model = RTDModel(
        name=name,
        reference_resistance_ohms=reference_resistance_ohms,
        curve=curve,
        identity=identity,
    )
    _BUILTIN_RTD_MODELS[identity] = model
    return model


PT100_IEC_60751 = _built_in_model(
    identity="pt100",
    name="Pt100",
    reference_resistance_ohms=100.0,
    curve=IEC_60751_PT385,
)


PT500_IEC_60751 = _built_in_model(
    identity="pt500",
    name="Pt500",
    reference_resistance_ohms=500.0,
    curve=IEC_60751_PT385,
)


PT1000_IEC_60751 = _built_in_model(
    identity="pt1000",
    name="Pt1000",
    reference_resistance_ohms=1000.0,
    curve=IEC_60751_PT385,
)


NI1000_6180 = _built_in_model(
    identity="ni1000",
    name="Ni1000 6180",
    reference_resistance_ohms=1000.0,
    curve=NI_6180_DIN_43760,
)


NI1000_TK5000 = _built_in_model(
    identity="ni1000_tk5000",
    name="Ni1000 TK5000",
    reference_resistance_ohms=1000.0,
    curve=NI_5000_TK5000,
)


NI120_6720 = _built_in_model(
    identity="ni120",
    name="Ni120 North American 6720",
    reference_resistance_ohms=120.0,
    curve=NI_6720_NORTH_AMERICAN,
)


# Expose an immutable internal view so every consumer uses the same registry.
# There is intentionally no public registration API yet: this is a closed set
# of verified built-ins, not a plugin mechanism for arbitrary user models.
BUILTIN_RTD_MODELS: Mapping[str, RTDModel] = MappingProxyType(_BUILTIN_RTD_MODELS)
