# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Ni1000 6178/6180 ppm/K resistance and temperature conversion.

This module implements the nickel characteristic historically specified by
DIN 43760 and commonly identified as Ni1000 6178/6180 ppm/K.  It uses a
nominal resistance of 1000 ohms at 0 °C and the normalized polynomial

``R(T) / R0 = 1 + A*T + B*T**2 + D*T**4 + F*T**6``

with ``A = 5.485e-3``, ``B = 6.650e-6``, ``D = 2.805e-11``, and
``F = -2.000e-17``.  The supported characteristic range is -60 °C through
250 °C.

The former DIN characteristic is distinct from Ni1000 TK5000.  A sensor
identified only as ``Ni1000`` must therefore be matched to the correct
characteristic before its resistance is interpreted.

Primary equation/range references:
    - ABB, *Industrial temperature measurement: Basics and practice*,
      nickel measurement characteristics according to DIN 43760.
    - Innovative Sensor Technology (IST AG), *RTD Nickel Sensor* application
      note, Nickel ND (6180 ppm/K) coefficient table.

Independent resistance-table verification:
    - TE Connectivity / HL-Planartechnik, *Ni1000SOT Temperature Sensor*.
    - Honeywell, *MERLIN NX IP and MS/TP VAV Controller Installation Guide*.

The model represents the ideal published characteristic.  Physical product
operating ranges and conformity/tolerance ranges can be narrower and must not
be inferred from this mathematical range.
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

_MODEL = _models.NI1000_6180

R0_OHMS = _MODEL.r0_ohms
MIN_TEMPERATURE_C = _MODEL.minimum_temperature_c
MAX_TEMPERATURE_C = _MODEL.maximum_temperature_c


def celsius_to_resistance(temperature_c: float) -> float:
    """Convert Celsius to ideal former-DIN Ni1000 resistance in ohms."""
    return _MODEL.celsius_to_resistance(temperature_c)


def resistance_to_celsius(resistance_ohms: float) -> float:
    """Convert former-DIN Ni1000 resistance in ohms to Celsius."""
    return _MODEL.resistance_to_celsius(resistance_ohms)


def resistance_sensitivity_ohms_per_celsius(temperature_c: float) -> float:
    """Return the exact local resistance sensitivity dR/dT."""
    return _MODEL.resistance_sensitivity_ohms_per_celsius(temperature_c)


def temperature_sensitivity_celsius_per_ohm(temperature_c: float) -> float:
    """Return the exact local inverse sensitivity dT/dR."""
    return _MODEL.temperature_sensitivity_celsius_per_ohm(temperature_c)
