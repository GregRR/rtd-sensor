# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared structural protocols for public RTD model interfaces."""

from __future__ import annotations

from typing import Protocol


class RTDUncertaintyModel(Protocol):
    """Minimal RTD behavior required for uncertainty propagation.

    This narrower protocol remains separate from :class:`RTDModel` so callers
    that provide only inverse conversion and local ``dT/dR`` sensitivity keep
    satisfying the uncertainty API. No inheritance from an rtd-sensor class is
    required; compatibility is structural.
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


class RTDModel(RTDUncertaintyModel, Protocol):
    """Structural interface for RTD conversion and local sensitivity.

    Built-in sensor modules, configurable rtd-sensor models, and third-party
    model objects can satisfy this interface without inheriting from a package
    base class. The protocol intentionally describes numerical behavior only.
    Valid ranges, model identity, and descriptive metadata are separate discovery
    concerns rather than requirements imposed on every structural model.
    """

    def celsius_to_resistance(self, temperature_c: float) -> float:
        """Convert temperature in Celsius to resistance in ohms."""
        ...

    def resistance_sensitivity_ohms_per_celsius(
        self,
        temperature_c: float,
    ) -> float:
        """Return local resistance sensitivity dR/dT in ohms/°C."""
        ...
