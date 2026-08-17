# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from rtd_sensor import pt100

# Independent reference values
# ----------------------------
#
# Validation source:
#   Fluke Calibration, "PT100 Resistance Table Generator"
#   https://www.fluke.com/en-us/learn/tools-calculators/
#   pt100-table-generator
#
# Accessed:
#   2026-08-04
#
# Generator settings:
#   Temperature unit: Celsius
#   Thermometer type: PT-385
#   Nominal resistance R0: 100.0000 ohms
#   Temperature range: -200 °C through 650 °C
#
# These values are rounded to two decimal places, matching the
# independently generated table. They are deliberately not generated
# by rtd_sensor.pt100 and therefore provide an external check on the
# implementation.
#
# Fluke identifies IEC 60751 among the source standards and publishes
# the PT-385 coefficients:
#
#   A = 3.9083e-3
#   B = -5.775e-7
#   C = -4.183e-12 below 0 °C
#
# The rounded value 18.52 ohms is suitable for checking the forward
# conversion at -200 °C. It is not used as an inverse-conversion input
# because it is slightly below the exact equation-defined minimum
# resistance after rounding to two decimal places.


@pytest.mark.parametrize(
    ("temperature_c", "expected_resistance_ohms"),
    [
        (-200.0, 18.52),
        (-100.0, 60.26),
        (-50.0, 80.31),
        (0.0, 100.00),
        (25.0, 109.73),
        (50.0, 119.40),
        (100.0, 138.51),
        (200.0, 175.86),
        (400.0, 247.09),
        (650.0, 329.64),
    ],
)
def test_celsius_to_resistance_matches_fluke_reference_table(
    temperature_c: float,
    expected_resistance_ohms: float,
) -> None:
    resistance = pt100.celsius_to_resistance(temperature_c)

    assert resistance == pytest.approx(
        expected_resistance_ohms,
        abs=0.005,
    )


@pytest.mark.parametrize(
    ("resistance_ohms", "expected_temperature_c"),
    [
        (60.26, -100.0),
        (80.31, -50.0),
        (100.00, 0.0),
        (109.73, 25.0),
        (119.40, 50.0),
        (138.51, 100.0),
        (175.86, 200.0),
        (247.09, 400.0),
        (329.64, 650.0),
    ],
)
def test_resistance_to_celsius_matches_fluke_reference_table(
    resistance_ohms: float,
    expected_temperature_c: float,
) -> None:
    temperature = pt100.resistance_to_celsius(resistance_ohms)

    assert temperature == pytest.approx(
        expected_temperature_c,
        abs=0.02,
    )


@pytest.mark.parametrize(
    "temperature_c",
    [
        -200.0,
        -175.5,
        -100.0,
        -0.001,
        0.0,
        25.0,
        100.0,
        419.75,
        850.0,
    ],
)
def test_temperature_round_trip(temperature_c: float) -> None:
    resistance = pt100.celsius_to_resistance(temperature_c)
    converted_temperature = pt100.resistance_to_celsius(resistance)

    assert converted_temperature == pytest.approx(
        temperature_c,
        abs=1e-9,
    )


@pytest.mark.parametrize(
    "temperature_c",
    [
        -200.0,
        -150.0,
        -100.0,
        -50.0,
        0.0,
        100.0,
        300.0,
        600.0,
    ],
)
def test_resistance_increases_with_temperature(
    temperature_c: float,
) -> None:
    first = pt100.celsius_to_resistance(temperature_c)
    second = pt100.celsius_to_resistance(temperature_c + 0.001)

    assert second > first


@pytest.mark.parametrize(
    "temperature_c",
    [
        -201.0,
        851.0,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_celsius_to_resistance_rejects_invalid_temperature(
    temperature_c: float,
) -> None:
    with pytest.raises(ValueError):
        pt100.celsius_to_resistance(temperature_c)


@pytest.mark.parametrize(
    "resistance_ohms",
    [
        -1.0,
        0.0,
        18.0,
        391.0,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_resistance_to_celsius_rejects_invalid_resistance(
    resistance_ohms: float,
) -> None:
    with pytest.raises(ValueError):
        pt100.resistance_to_celsius(resistance_ohms)


def test_minimum_temperature_boundary_round_trip() -> None:
    resistance = pt100.celsius_to_resistance(pt100.MIN_TEMPERATURE_C)

    temperature = pt100.resistance_to_celsius(resistance)

    assert temperature == pytest.approx(
        pt100.MIN_TEMPERATURE_C,
        abs=1e-9,
    )


def test_maximum_temperature_boundary_round_trip() -> None:
    resistance = pt100.celsius_to_resistance(pt100.MAX_TEMPERATURE_C)

    temperature = pt100.resistance_to_celsius(resistance)

    assert temperature == pytest.approx(
        pt100.MAX_TEMPERATURE_C,
        abs=1e-9,
    )


def test_zero_celsius_is_exactly_100_ohms() -> None:
    assert pt100.celsius_to_resistance(0.0) == 100.0


def test_100_ohms_is_zero_celsius() -> None:
    assert pt100.resistance_to_celsius(100.0) == 0.0
