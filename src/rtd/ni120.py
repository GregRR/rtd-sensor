# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""North American Ni120 / 6720 ppm/K resistance-temperature conversion.

This module implements Minco's ``NA`` nickel characteristic: 120 ohms at
0 °C with a nominal TCR of 0.00672 ohm/ohm/°C. Minco publishes the
characteristic as twelve cubic intervals rather than one global polynomial:

``R(T) / R0 = A + B*T + C*T**2 + D*T**3``

with interval-specific A/B/C/D coefficients from -80 °C through 260 °C.
The implementation preserves those published coefficients and uses the
piecewise-characteristic continuity machinery only to reconcile the tiny
join mismatches caused by their printed precision. It does not refit or
replace Minco's source curve.

Equation provenance:
    - Minco, *Resistance Thermometry: Principles and Applications of
      Resistance Thermometers and Thermistors*, Nickel section, page 6:
      https://www.minco.com/wp-content/uploads/Resistance-Thermometry.pdf
    - Minco identifies the corresponding table code as ``NA``: nickel,
      120 ohms at 0 °C, TCR 0.00672 ohm/ohm/°C:
      https://www.minco.com/resource-center/rtd-temperature-vs-resistance-table/

Independent resistance-table verification:
    - Pyromation, *120 Ohm Nickel RTD — 0.00672 coefficient, degree Celsius*:
      https://www.pyromation.com/downloads/data/672_c.pdf

The -80 °C through 260 °C bounds are the range of the published piecewise
equation and independent validation table. Product-level operating limits may
be narrower and remain a separate concern.
"""

from __future__ import annotations

from . import _models

__all__ = [
    "MAX_TEMPERATURE_C",
    "MIN_TEMPERATURE_C",
    "R0_OHMS",
    "celsius_to_resistance",
    "resistance_sensitivity_ohms_per_celsius",
    "resistance_to_celsius",
    "temperature_sensitivity_celsius_per_ohm",
]

_MODEL = _models.NI120_6720

R0_OHMS = _MODEL.r0_ohms
MIN_TEMPERATURE_C = _MODEL.minimum_temperature_c
MAX_TEMPERATURE_C = _MODEL.maximum_temperature_c


def celsius_to_resistance(temperature_c: float) -> float:
    """Convert Celsius to ideal North American Ni120 resistance in ohms."""
    return _MODEL.celsius_to_resistance(temperature_c)


def resistance_to_celsius(resistance_ohms: float) -> float:
    """Convert North American Ni120 resistance in ohms to Celsius."""
    return _MODEL.resistance_to_celsius(resistance_ohms)


def resistance_sensitivity_ohms_per_celsius(temperature_c: float) -> float:
    """Return the active Minco segment's analytical dR/dT."""
    return _MODEL.resistance_sensitivity_ohms_per_celsius(temperature_c)


def temperature_sensitivity_celsius_per_ohm(temperature_c: float) -> float:
    """Return the active Minco segment's analytical dT/dR."""
    return _MODEL.temperature_sensitivity_celsius_per_ohm(temperature_c)
