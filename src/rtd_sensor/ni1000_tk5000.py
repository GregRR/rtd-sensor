# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Ni1000 TK5000 / 5000 ppm/K resistance and temperature conversion.

This module implements the distinct Ni1000 TK5000 characteristic used in
building automation.  Innovative Sensor Technology (IST AG) identifies the
same polynomial as ``Nickel NL (5000 ppm/K)``.  It uses a nominal resistance
of 1000 ohms at 0 °C and the normalized cubic

``R(T) / R0 = 1 + A*T + B*T**2 + C*T**3``

with ``A = 4.427e-3``, ``B = 5.172e-6``, and ``C = 5.585e-9``.  The supported
characteristic range is -60 °C through 250 °C.

This characteristic is intentionally separate from :mod:`rtd_sensor.ni1000`, which
implements the former-DIN 6178/6180 ppm/K Ni1000 curve.  Nominal resistance
alone is therefore not sufficient to choose between the two modules.

Equation provenance:
    - Innovative Sensor Technology (IST AG), *RTD Nickel Sensor* application
      note, ``Nickel NL (5000 ppm/K)`` coefficient table:
      https://www.mouser.com/datasheet/2/1426/nl1k0_520_2fw_b_007-2950467.pdf

Independent resistance-table verification:
    - E+E Elektronik, *R-T Characteristics: Ni1000 TK5000 DIN B*:
      https://www.epluse.com/fileadmin/data/product/r-t_characteristics/R_T_Characteristics_Ni1000_TK5000.pdf

The model represents the published resistance-temperature characteristic,
not the packaging limits of a particular sensor.  A physical product may
specify a narrower operating or conformity range.
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

_MODEL = _models.NI1000_TK5000

R0_OHMS = _MODEL.r0_ohms
MIN_TEMPERATURE_C = _MODEL.minimum_temperature_c
MAX_TEMPERATURE_C = _MODEL.maximum_temperature_c


def celsius_to_resistance(temperature_c: float) -> float:
    """Convert Celsius to ideal Ni1000 TK5000 resistance in ohms."""
    return _MODEL.celsius_to_resistance(temperature_c)


def resistance_to_celsius(resistance_ohms: float) -> float:
    """Convert Ni1000 TK5000 resistance in ohms to Celsius."""
    return _MODEL.resistance_to_celsius(resistance_ohms)


def resistance_sensitivity_ohms_per_celsius(temperature_c: float) -> float:
    """Return the exact local resistance sensitivity dR/dT."""
    return _MODEL.resistance_sensitivity_ohms_per_celsius(temperature_c)


def temperature_sensitivity_celsius_per_ohm(temperature_c: float) -> float:
    """Return the exact local inverse sensitivity dT/dR."""
    return _MODEL.temperature_sensitivity_celsius_per_ohm(temperature_c)
