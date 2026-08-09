# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""IEC 60751 temperature-tolerance calculations.

IEC 60751:2022 distinguishes the tolerance classes of bare platinum
resistors from the tolerance classes of assembled thermometers. The
published tolerance formulas apply for any value of R0, but their
permitted temperature ranges depend on construction and device type.

The values returned here are maximum permitted temperature deviations
from the nominal resistance-temperature relationship. They are tolerance
limits, not probability distributions or standard uncertainties. Numerical
tolerance calculation alone does not establish full IEC 60751 conformity;
the standard contains additional construction and test requirements.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "PlatinumResistorToleranceClass",
    "RTDConstruction",
    "ThermometerToleranceClass",
    "platinum_resistor_tolerance_c",
    "thermometer_tolerance_c",
]


type RTDConstruction = Literal["wire_wound", "film"]
type ThermometerToleranceClass = Literal["AA", "A", "B", "C"]
type PlatinumResistorToleranceClass = Literal[
    "W0.1",
    "W0.15",
    "W0.3",
    "W0.6",
    "F0.1",
    "F0.15",
    "F0.3",
    "F0.6",
]


@dataclass(frozen=True, slots=True)
class _ToleranceSpec:
    """Numerical IEC tolerance rule plus the range where its class is valid.

    The standard's tolerance equations all have the form
    ``offset + slope * abs(t)``.  The validity range is stored separately
    because construction-specific class ranges are not generally symmetric
    about 0 °C and must not be inferred from the equation alone.
    """

    offset_c: float
    slope_c_per_c: float
    minimum_temperature_c: float
    maximum_temperature_c: float


# IEC 60751:2022, Table 2 — tolerance classes of thermometers.
#
# These ranges are part of the class definition, not merely recommended
# operating ranges. Keeping them beside the equation coefficients prevents a
# caller from accidentally extending a standard class beyond its defined range.
_THERMOMETER_SPECS: dict[
    tuple[ThermometerToleranceClass, RTDConstruction],
    _ToleranceSpec,
] = {
    ("AA", "wire_wound"): _ToleranceSpec(0.1, 0.0017, -50.0, 250.0),
    ("AA", "film"): _ToleranceSpec(0.1, 0.0017, 0.0, 150.0),
    ("A", "wire_wound"): _ToleranceSpec(0.15, 0.002, -100.0, 450.0),
    ("A", "film"): _ToleranceSpec(0.15, 0.002, -30.0, 300.0),
    ("B", "wire_wound"): _ToleranceSpec(0.3, 0.005, -196.0, 600.0),
    ("B", "film"): _ToleranceSpec(0.3, 0.005, -50.0, 500.0),
    ("C", "wire_wound"): _ToleranceSpec(0.6, 0.01, -196.0, 600.0),
    ("C", "film"): _ToleranceSpec(0.6, 0.01, -50.0, 600.0),
}


# IEC 60751:2022, Table 1 — tolerance classes of platinum resistors.
# The public ASCII designations combine the standard W/F construction
# prefix with the decimal tolerance-class value. W and F are retained in the
# public designation because construction is already part of the bare-resistor
# class identity, unlike the assembled-thermometer API where it is a separate
# argument.
_PLATINUM_RESISTOR_SPECS: dict[
    PlatinumResistorToleranceClass,
    _ToleranceSpec,
] = {
    "W0.1": _ToleranceSpec(0.1, 0.0017, -100.0, 350.0),
    "W0.15": _ToleranceSpec(0.15, 0.002, -100.0, 450.0),
    "W0.3": _ToleranceSpec(0.3, 0.005, -196.0, 660.0),
    "W0.6": _ToleranceSpec(0.6, 0.01, -196.0, 660.0),
    "F0.1": _ToleranceSpec(0.1, 0.0017, 0.0, 150.0),
    "F0.15": _ToleranceSpec(0.15, 0.002, -30.0, 300.0),
    "F0.3": _ToleranceSpec(0.3, 0.005, -50.0, 500.0),
    "F0.6": _ToleranceSpec(0.6, 0.01, -50.0, 600.0),
}


def thermometer_tolerance_c(
    temperature_c: float,
    *,
    tolerance_class: ThermometerToleranceClass,
    construction: RTDConstruction,
) -> float:
    """Return the IEC 60751 thermometer tolerance in degrees Celsius.

    Args:
        temperature_c: Nominal temperature in degrees Celsius.
        tolerance_class: Standard thermometer class ``AA``, ``A``, ``B``,
            or ``C``.
        construction: Whether the thermometer uses a ``wire_wound`` or
            ``film`` platinum resistor. Construction affects the standard
            temperature range over which the class designation is valid.

    Returns:
        Positive maximum permitted absolute temperature deviation in degrees
        Celsius at the specified reference temperature.

    Raises:
        ValueError: If the temperature is non-finite, the class or
            construction is unsupported, or the temperature is outside the
            IEC 60751 validity range for that class and construction.
    """
    try:
        spec = _THERMOMETER_SPECS[(tolerance_class, construction)]
    except KeyError as exc:
        raise ValueError(
            "Unsupported IEC 60751 thermometer tolerance class or construction"
        ) from exc

    return _temperature_tolerance_c(
        temperature_c,
        spec,
        designation=f"thermometer class {tolerance_class} ({construction})",
    )


def platinum_resistor_tolerance_c(
    temperature_c: float,
    *,
    tolerance_class: PlatinumResistorToleranceClass,
) -> float:
    """Return the IEC 60751 platinum-resistor tolerance in degrees Celsius.

    The class designation includes construction: ``W`` denotes wire wound
    and ``F`` denotes film. For example, ``W0.15`` corresponds to IEC class
    W 0.15 and ``F0.3`` corresponds to IEC class F 0.3.

    Args:
        temperature_c: Nominal temperature in degrees Celsius.
        tolerance_class: Standard platinum-resistor class designation.

    Returns:
        Positive maximum permitted absolute temperature deviation in degrees
        Celsius at the specified reference temperature.

    Raises:
        ValueError: If the temperature is non-finite, the class is
            unsupported, or the temperature is outside the IEC 60751 validity
            range for that platinum-resistor class.
    """
    try:
        spec = _PLATINUM_RESISTOR_SPECS[tolerance_class]
    except KeyError as exc:
        raise ValueError(
            "Unsupported IEC 60751 platinum-resistor tolerance class"
        ) from exc

    return _temperature_tolerance_c(
        temperature_c,
        spec,
        designation=f"platinum-resistor class {tolerance_class}",
    )


def _temperature_tolerance_c(
    temperature_c: float,
    spec: _ToleranceSpec,
    *,
    designation: str,
) -> float:
    """Evaluate one validated IEC tolerance specification.

    The returned value is the positive magnitude of the permitted deviation;
    callers that need a nominal tolerance interval can interpret it as
    ``temperature ± returned_value``. This helper intentionally does not turn
    that bounded limit into a statistical uncertainty.
    """

    temperature = float(temperature_c)
    if not math.isfinite(temperature):
        raise ValueError("Temperature must be finite")
    if not (
        spec.minimum_temperature_c
        <= temperature
        <= spec.maximum_temperature_c
    ):
        raise ValueError(
            f"Temperature must be between {spec.minimum_temperature_c:g} °C "
            f"and {spec.maximum_temperature_c:g} °C for IEC 60751 "
            f"{designation}"
        )

    # IEC 60751 expresses the temperature-dependent term using |t|, so the
    # allowed deviation grows with distance from 0 °C regardless of sign.
    return spec.offset_c + spec.slope_c_per_c * abs(temperature)
