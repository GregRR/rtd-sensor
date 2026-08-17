# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from rtd_sensor import ni1000

# Independent reference table
# ---------------------------
# Validation sources: TE Connectivity / HL-Planartechnik and Honeywell;
# see docs/REFERENCES.md.
#
# TE Connectivity / HL-Planartechnik, "Ni1000SOT Temperature Sensor",
# publishes a 1 °C resistance table for the former DIN 43760 6178 ppm/K
# characteristic.  The table is rounded to 0.1 ohm, so tests use an absolute
# tolerance of 0.05 ohm.  Honeywell's MERLIN NX installation guide reproduces
# the same table independently of this implementation.
_TE_REFERENCE_VALUES = [
    (-60.0, 695.2),
    (-40.0, 791.3),
    (-20.0, 893.0),
    (0.0, 1000.0),
    (20.0, 1112.4),
    (50.0, 1291.1),
    (100.0, 1617.8),
    (150.0, 1986.3),
    (160.0, 2065.9),
]


def test_constants_match_former_din_ni1000_characteristic() -> None:
    assert ni1000.R0_OHMS == 1000.0
    assert ni1000.MIN_TEMPERATURE_C == -60.0
    assert ni1000.MAX_TEMPERATURE_C == 250.0


@pytest.mark.parametrize(("temperature_c", "expected_ohms"), _TE_REFERENCE_VALUES)
def test_celsius_to_resistance_matches_independent_te_table(
    temperature_c: float,
    expected_ohms: float,
) -> None:
    assert ni1000.celsius_to_resistance(temperature_c) == pytest.approx(
        expected_ohms,
        abs=0.05,
    )


@pytest.mark.parametrize(
    ("temperature_c", "reference_ohms"),
    _TE_REFERENCE_VALUES[1:],
)
def test_reference_resistance_to_celsius_matches_te_table(
    temperature_c: float,
    reference_ohms: float,
) -> None:
    # The source table is rounded to 0.1 ohm, so inverse checks use a
    # temperature tolerance wide enough to cover that source precision. The
    # rounded -60 °C entry (695.2 ohm) lies slightly below the exact model
    # boundary (695.20259488 ohm), so it is intentionally tested only in the
    # forward direction; resistance-domain validation must remain strict.
    assert ni1000.resistance_to_celsius(reference_ohms) == pytest.approx(
        temperature_c,
        abs=0.011,
    )


@pytest.mark.parametrize(
    "temperature_c",
    [-60.0, -55.5, -1.0, 0.0, 0.001, 65.0, 160.0, 200.0, 250.0],
)
def test_temperature_round_trip(temperature_c: float) -> None:
    resistance = ni1000.celsius_to_resistance(temperature_c)
    assert ni1000.resistance_to_celsius(resistance) == pytest.approx(
        temperature_c,
        abs=1e-9,
    )


def test_boundaries_round_trip_exactly_enough_for_public_api() -> None:
    for temperature_c in (
        ni1000.MIN_TEMPERATURE_C,
        ni1000.MAX_TEMPERATURE_C,
    ):
        resistance = ni1000.celsius_to_resistance(temperature_c)
        converted = ni1000.resistance_to_celsius(resistance)
        assert converted == pytest.approx(temperature_c, abs=1e-12)


def test_forward_polynomial_at_upper_boundary() -> None:
    assert ni1000.celsius_to_resistance(250.0) == pytest.approx(
        2891.5625,
        abs=1e-12,
    )


@pytest.mark.parametrize(
    "temperature_c",
    [-60.001, 250.001, math.inf, -math.inf, math.nan],
)
def test_celsius_to_resistance_rejects_out_of_range_temperature(
    temperature_c: float,
) -> None:
    with pytest.raises(ValueError):
        ni1000.celsius_to_resistance(temperature_c)


def test_resistance_to_celsius_rejects_out_of_range_resistance() -> None:
    minimum = ni1000.celsius_to_resistance(ni1000.MIN_TEMPERATURE_C)
    maximum = ni1000.celsius_to_resistance(ni1000.MAX_TEMPERATURE_C)

    with pytest.raises(ValueError):
        ni1000.resistance_to_celsius(math.nextafter(minimum, -math.inf))
    with pytest.raises(ValueError):
        ni1000.resistance_to_celsius(math.nextafter(maximum, math.inf))


@pytest.mark.parametrize("resistance_ohms", [0.0, -1.0, math.inf, -math.inf, math.nan])
def test_resistance_to_celsius_rejects_invalid_resistance(
    resistance_ohms: float,
) -> None:
    with pytest.raises(ValueError):
        ni1000.resistance_to_celsius(resistance_ohms)


@pytest.mark.parametrize("temperature_c", [-60.0, 0.0, 100.0, 250.0])
def test_resistance_sensitivity_matches_published_polynomial_derivative(
    temperature_c: float,
) -> None:
    a = 5.485e-3
    b = 6.650e-6
    d = 2.805e-11
    f = -2.000e-17
    expected = ni1000.R0_OHMS * (
        a
        + 2.0 * b * temperature_c
        + 4.0 * d * temperature_c**3
        + 6.0 * f * temperature_c**5
    )

    actual = ni1000.resistance_sensitivity_ohms_per_celsius(temperature_c)
    assert actual == pytest.approx(expected, abs=1e-12)
    assert ni1000.temperature_sensitivity_celsius_per_ohm(
        temperature_c
    ) == pytest.approx(1.0 / expected, abs=1e-15)


def test_characteristic_is_monotonic_across_one_degree_grid() -> None:
    resistances = [
        ni1000.celsius_to_resistance(float(temperature_c))
        for temperature_c in range(-60, 251)
    ]
    assert all(
        earlier < later
        for earlier, later in zip(resistances, resistances[1:], strict=False)
    )
