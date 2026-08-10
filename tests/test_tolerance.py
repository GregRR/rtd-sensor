# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
from typing import cast

import pytest

from rtd_sensor import tolerance

# Normative reference
# -------------------
# IEC 60751:2022, section 5.2:
#   Table 1 — tolerance classes of platinum resistors
#   Table 2 — tolerance classes of thermometers
#
# The standard defines the tolerance magnitude as an offset plus a
# coefficient times |t| and gives construction-dependent validity ranges.
# These requirements apply for any value of R0.


@pytest.mark.parametrize(
    ("tolerance_class", "temperature_c", "expected_error_c"),
    [
        ("AA", 0.0, 0.1),
        ("AA", 100.0, 0.27),
        ("A", 0.0, 0.15),
        ("A", 100.0, 0.35),
        ("A", -100.0, 0.35),
        ("B", 0.0, 0.3),
        ("B", 100.0, 0.8),
        ("C", 0.0, 0.6),
        ("C", 100.0, 1.6),
    ],
)
def test_thermometer_tolerance_formula(
    tolerance_class: tolerance.ThermometerToleranceClass,
    temperature_c: float,
    expected_error_c: float,
) -> None:
    result = tolerance.thermometer_tolerance_c(
        temperature_c,
        tolerance_class=tolerance_class,
        construction="wire_wound",
    )

    assert result == pytest.approx(expected_error_c)


@pytest.mark.parametrize(
    ("tolerance_class", "construction", "lower_c", "upper_c"),
    [
        ("AA", "wire_wound", -50.0, 250.0),
        ("AA", "film", 0.0, 150.0),
        ("A", "wire_wound", -100.0, 450.0),
        ("A", "film", -30.0, 300.0),
        ("B", "wire_wound", -196.0, 600.0),
        ("B", "film", -50.0, 500.0),
        ("C", "wire_wound", -196.0, 600.0),
        ("C", "film", -50.0, 600.0),
    ],
)
def test_thermometer_class_boundaries_are_inclusive(
    tolerance_class: tolerance.ThermometerToleranceClass,
    construction: tolerance.RTDConstruction,
    lower_c: float,
    upper_c: float,
) -> None:
    lower = tolerance.thermometer_tolerance_c(
        lower_c,
        tolerance_class=tolerance_class,
        construction=construction,
    )
    upper = tolerance.thermometer_tolerance_c(
        upper_c,
        tolerance_class=tolerance_class,
        construction=construction,
    )

    assert lower > 0.0
    assert upper > 0.0


@pytest.mark.parametrize(
    ("tolerance_class", "construction", "temperature_c"),
    [
        ("AA", "wire_wound", -50.001),
        ("AA", "film", -0.001),
        ("A", "wire_wound", 450.001),
        ("A", "film", 300.001),
        ("B", "wire_wound", -196.001),
        ("B", "film", 500.001),
        ("C", "wire_wound", 600.001),
        ("C", "film", -50.001),
    ],
)
def test_thermometer_rejects_temperature_outside_class_range(
    tolerance_class: tolerance.ThermometerToleranceClass,
    construction: tolerance.RTDConstruction,
    temperature_c: float,
) -> None:
    with pytest.raises(ValueError, match="Temperature must be between"):
        tolerance.thermometer_tolerance_c(
            temperature_c,
            tolerance_class=tolerance_class,
            construction=construction,
        )


@pytest.mark.parametrize(
    ("tolerance_class", "temperature_c", "expected_error_c"),
    [
        ("W0.1", -100.0, 0.27),
        ("W0.15", 100.0, 0.35),
        ("W0.3", 200.0, 1.3),
        ("W0.6", 300.0, 3.6),
        ("F0.1", 100.0, 0.27),
        ("F0.15", -30.0, 0.21),
        ("F0.3", 200.0, 1.3),
        ("F0.6", 300.0, 3.6),
    ],
)
def test_platinum_resistor_tolerance_formula(
    tolerance_class: tolerance.PlatinumResistorToleranceClass,
    temperature_c: float,
    expected_error_c: float,
) -> None:
    result = tolerance.platinum_resistor_tolerance_c(
        temperature_c,
        tolerance_class=tolerance_class,
    )

    assert result == pytest.approx(expected_error_c)


@pytest.mark.parametrize(
    ("tolerance_class", "lower_c", "upper_c"),
    [
        ("W0.1", -100.0, 350.0),
        ("W0.15", -100.0, 450.0),
        ("W0.3", -196.0, 660.0),
        ("W0.6", -196.0, 660.0),
        ("F0.1", 0.0, 150.0),
        ("F0.15", -30.0, 300.0),
        ("F0.3", -50.0, 500.0),
        ("F0.6", -50.0, 600.0),
    ],
)
def test_platinum_resistor_class_boundaries_are_inclusive(
    tolerance_class: tolerance.PlatinumResistorToleranceClass,
    lower_c: float,
    upper_c: float,
) -> None:
    lower = tolerance.platinum_resistor_tolerance_c(
        lower_c,
        tolerance_class=tolerance_class,
    )
    upper = tolerance.platinum_resistor_tolerance_c(
        upper_c,
        tolerance_class=tolerance_class,
    )

    assert lower > 0.0
    assert upper > 0.0


@pytest.mark.parametrize("temperature_c", [math.inf, -math.inf, math.nan])
def test_tolerance_rejects_nonfinite_temperature(
    temperature_c: float,
) -> None:
    with pytest.raises(ValueError, match="Temperature must be finite"):
        tolerance.thermometer_tolerance_c(
            temperature_c,
            tolerance_class="A",
            construction="wire_wound",
        )

    with pytest.raises(ValueError, match="Temperature must be finite"):
        tolerance.platinum_resistor_tolerance_c(
            temperature_c,
            tolerance_class="W0.15",
        )


def test_thermometer_rejects_unsupported_class() -> None:
    invalid_class = cast(tolerance.ThermometerToleranceClass, "D")

    with pytest.raises(ValueError, match="Unsupported IEC 60751 thermometer"):
        tolerance.thermometer_tolerance_c(
            0.0,
            tolerance_class=invalid_class,
            construction="wire_wound",
        )


def test_thermometer_rejects_unsupported_construction() -> None:
    invalid_construction = cast(tolerance.RTDConstruction, "ceramic")

    with pytest.raises(ValueError, match="Unsupported IEC 60751 thermometer"):
        tolerance.thermometer_tolerance_c(
            0.0,
            tolerance_class="A",
            construction=invalid_construction,
        )


def test_platinum_resistor_rejects_unsupported_class() -> None:
    invalid_class = cast(tolerance.PlatinumResistorToleranceClass, "W0.2")

    with pytest.raises(ValueError, match="Unsupported IEC 60751 platinum"):
        tolerance.platinum_resistor_tolerance_c(
            0.0,
            tolerance_class=invalid_class,
        )
