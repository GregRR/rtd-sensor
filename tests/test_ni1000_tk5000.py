# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from rtd import ni1000, ni1000_tk5000

# Independent reference table
# ---------------------------
# E+E Elektronik publishes a 1 °C resistance table for "Ni1000 TK5000 DIN B"
# from -60 °C through 250 °C.  These expected values are deliberately taken
# from that table rather than recomputed from IST's coefficient source, so the
# test can detect a coefficient transcription or characteristic-selection bug.
#
# Source:
# https://www.epluse.com/fileadmin/data/product/r-t_characteristics/R_T_Characteristics_Ni1000_TK5000.pdf
_EE_REFERENCE_VALUES = [
    (-60.0, 751.79),
    (-50.0, 790.88),
    (-40.0, 830.84),
    (-20.0, 913.48),
    (0.0, 1000.00),
    (20.0, 1090.65),
    (50.0, 1234.98),
    (100.0, 1500.00),
    (150.0, 1799.27),
    (200.0, 2136.96),
    (250.0, 2517.27),
]


def test_constants_match_tk5000_characteristic() -> None:
    assert ni1000_tk5000.R0_OHMS == 1000.0
    assert ni1000_tk5000.MIN_TEMPERATURE_C == -60.0
    assert ni1000_tk5000.MAX_TEMPERATURE_C == 250.0


@pytest.mark.parametrize(("temperature_c", "expected_ohms"), _EE_REFERENCE_VALUES)
def test_celsius_to_resistance_matches_independent_ee_table(
    temperature_c: float,
    expected_ohms: float,
) -> None:
    # The source table is published to 0.01 ohm.  The 100 °C polynomial value
    # is 1500.005 ohm while the table prints 1500.00 ohm, so 0.01 ohm safely
    # reflects source precision without pretending the table is exact.
    assert ni1000_tk5000.celsius_to_resistance(temperature_c) == pytest.approx(
        expected_ohms,
        abs=0.01,
    )


@pytest.mark.parametrize(
    ("temperature_c", "reference_ohms"),
    _EE_REFERENCE_VALUES[1:-1],
)
def test_reference_resistance_to_celsius_matches_ee_table(
    temperature_c: float,
    reference_ohms: float,
) -> None:
    # Rounded endpoint values fall just outside the exact model domain:
    # 751.79 < R(-60 °C) and 2517.27 > R(250 °C).  Excluding those two inverse
    # checks preserves strict resistance-domain validation instead of widening
    # the characteristic merely to accommodate publication rounding.
    assert ni1000_tk5000.resistance_to_celsius(reference_ohms) == pytest.approx(
        temperature_c,
        abs=0.003,
    )


@pytest.mark.parametrize(
    "temperature_c",
    [-60.0, -55.5, -1.0, 0.0, 0.001, 65.0, 150.0, 200.0, 250.0],
)
def test_temperature_round_trip(temperature_c: float) -> None:
    resistance = ni1000_tk5000.celsius_to_resistance(temperature_c)
    assert ni1000_tk5000.resistance_to_celsius(resistance) == pytest.approx(
        temperature_c,
        abs=1e-9,
    )


def test_boundaries_round_trip_exactly_enough_for_public_api() -> None:
    for temperature_c in (
        ni1000_tk5000.MIN_TEMPERATURE_C,
        ni1000_tk5000.MAX_TEMPERATURE_C,
    ):
        resistance = ni1000_tk5000.celsius_to_resistance(temperature_c)
        converted = ni1000_tk5000.resistance_to_celsius(resistance)
        assert converted == pytest.approx(temperature_c, abs=1e-12)


def test_forward_polynomial_at_upper_boundary() -> None:
    assert ni1000_tk5000.celsius_to_resistance(250.0) == pytest.approx(
        2517.265625,
        abs=1e-12,
    )


def test_tk5000_is_not_interchangeable_with_6180_characteristic() -> None:
    # Both characteristics are called Ni1000 because R(0 °C) = 1000 ohm, but
    # their nonlinear R/T behavior is materially different.  Keep this
    # distinction executable so a future refactor cannot alias the models.
    assert ni1000_tk5000.celsius_to_resistance(100.0) == pytest.approx(
        1500.005,
        abs=1e-12,
    )
    assert ni1000.celsius_to_resistance(100.0) == pytest.approx(
        1617.785,
        abs=1e-12,
    )
    assert ni1000_tk5000.celsius_to_resistance(100.0) != pytest.approx(
        ni1000.celsius_to_resistance(100.0),
        abs=1.0,
    )


@pytest.mark.parametrize(
    "temperature_c",
    [-60.001, 250.001, math.inf, -math.inf, math.nan],
)
def test_celsius_to_resistance_rejects_out_of_range_temperature(
    temperature_c: float,
) -> None:
    with pytest.raises(ValueError):
        ni1000_tk5000.celsius_to_resistance(temperature_c)


def test_resistance_to_celsius_rejects_out_of_range_resistance() -> None:
    minimum = ni1000_tk5000.celsius_to_resistance(ni1000_tk5000.MIN_TEMPERATURE_C)
    maximum = ni1000_tk5000.celsius_to_resistance(ni1000_tk5000.MAX_TEMPERATURE_C)

    with pytest.raises(ValueError):
        ni1000_tk5000.resistance_to_celsius(math.nextafter(minimum, -math.inf))
    with pytest.raises(ValueError):
        ni1000_tk5000.resistance_to_celsius(math.nextafter(maximum, math.inf))


@pytest.mark.parametrize("resistance_ohms", [0.0, -1.0, math.inf, -math.inf, math.nan])
def test_resistance_to_celsius_rejects_invalid_resistance(
    resistance_ohms: float,
) -> None:
    with pytest.raises(ValueError):
        ni1000_tk5000.resistance_to_celsius(resistance_ohms)


@pytest.mark.parametrize("temperature_c", [-60.0, 0.0, 100.0, 250.0])
def test_resistance_sensitivity_matches_published_polynomial_derivative(
    temperature_c: float,
) -> None:
    # IST's Nickel NL characteristic is cubic, so differentiating the
    # published forward equation gives this exact local sensitivity.
    a = 4.427e-3
    b = 5.172e-6
    c = 5.585e-9
    expected = ni1000_tk5000.R0_OHMS * (
        a + 2.0 * b * temperature_c + 3.0 * c * temperature_c**2
    )

    actual = ni1000_tk5000.resistance_sensitivity_ohms_per_celsius(temperature_c)
    assert actual == pytest.approx(expected, abs=1e-12)
    assert ni1000_tk5000.temperature_sensitivity_celsius_per_ohm(
        temperature_c
    ) == pytest.approx(1.0 / expected, abs=1e-15)


def test_characteristic_is_monotonic_across_one_degree_grid() -> None:
    resistances = [
        ni1000_tk5000.celsius_to_resistance(float(temperature_c))
        for temperature_c in range(-60, 251)
    ]
    assert all(
        earlier < later
        for earlier, later in zip(resistances, resistances[1:], strict=False)
    )
