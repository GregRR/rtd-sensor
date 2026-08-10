# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""IEC 60751 Pt500 resistance and temperature conversion.

The implementation uses the IEC 60751 PT-385 Callendar–Van Dusen
resistance-temperature relationship with a nominal resistance of
500 ohms at 0 °C. Pt500 shares the same normalized IEC platinum
characteristic as Pt100 and Pt1000; only ``R0`` changes.

Normative reference:
    IEC 60751:2022, Industrial platinum resistance thermometers and
    platinum temperature sensors.

Publicly accessible verification references:
    - UST Umweltsensortechnik GmbH, ``Pt500 - Basic resistance values``,
      values calculated according to DIN EN 60751.
    - Fluke, PT100 Resistance Table Generator, which explicitly supports
      Pt500 using the PT-385 coefficients.

The model represents the standardized ideal curve. It does not include
individual probe calibration, lead-wire resistance, self-heating, or
measurement-circuit errors.
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

_MODEL = _models.PT500_IEC_60751

R0_OHMS = _MODEL.r0_ohms
MIN_TEMPERATURE_C = _MODEL.minimum_temperature_c
MAX_TEMPERATURE_C = _MODEL.maximum_temperature_c


def celsius_to_resistance(temperature_c: float) -> float:
    """Convert temperature in Celsius to ideal Pt500 resistance in ohms.

    Args:
        temperature_c: Temperature in degrees Celsius.

    Returns:
        Ideal Pt500 resistance in ohms.

    Raises:
        ValueError: If the temperature is non-finite or outside the
            supported IEC 60751 range of -200 °C through 850 °C.
    """
    return _MODEL.celsius_to_resistance(temperature_c)


def resistance_to_celsius(resistance_ohms: float) -> float:
    """Convert Pt500 resistance in ohms to temperature in Celsius.

    Args:
        resistance_ohms: Measured, compensated Pt500 resistance in ohms.

    Returns:
        Temperature in degrees Celsius.

    Raises:
        ValueError: If the resistance is non-finite, non-positive, or
            outside the resistance range represented by -200 °C through
            850 °C.
    """
    return _MODEL.resistance_to_celsius(resistance_ohms)


def resistance_sensitivity_ohms_per_celsius(temperature_c: float) -> float:
    """Return the exact local resistance sensitivity dR/dT.

    The result is expressed in ohms per degree Celsius and is evaluated
    analytically from the configured Callendar-Van Dusen curve.
    """
    return _MODEL.resistance_sensitivity_ohms_per_celsius(temperature_c)


def temperature_sensitivity_celsius_per_ohm(temperature_c: float) -> float:
    """Return the exact local inverse sensitivity dT/dR.

    The result is expressed in degrees Celsius per ohm and is the reciprocal
    of the local resistance sensitivity.
    """
    return _MODEL.temperature_sensitivity_celsius_per_ohm(temperature_c)
