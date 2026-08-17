# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

import rtd_sensor._curves as _curves
from rtd_sensor import ni120

# Independent reference table
# ---------------------------
# Pyromation publishes a 1 °C table for a "120 Ohm Nickel RTD — 0.00672
# coefficient" from -80 °C through 260 °C. These values are deliberately
# independent of Minco's polynomial coefficient source, so they can detect a
# transcription, segment-routing, or stitching error in the implementation.
#
# Validation source: Pyromation; see docs/REFERENCES.md.
# https://www.pyromation.com/downloads/data/672_c.pdf
_PYROMATION_REFERENCE_VALUES = [
    (-80.0, 66.60),
    (-70.0, 73.10),
    (-60.0, 79.62),
    (-50.0, 86.16),
    (-40.0, 92.76),
    (-30.0, 99.41),
    (-20.0, 106.15),
    (-10.0, 113.00),
    (0.0, 120.00),
    (10.0, 127.17),
    (20.0, 134.52),
    (30.0, 142.06),
    (40.0, 149.80),
    (50.0, 157.75),
    (60.0, 165.90),
    (70.0, 174.27),
    (80.0, 182.85),
    (90.0, 191.64),
    (100.0, 200.64),
    (110.0, 209.85),
    (120.0, 219.29),
    (130.0, 228.95),
    (140.0, 238.84),
    (150.0, 248.95),
    (160.0, 259.30),
    (170.0, 269.89),
    (180.0, 280.77),
    (190.0, 291.95),
    (200.0, 303.45),
    (210.0, 315.31),
    (220.0, 327.54),
    (230.0, 340.14),
    (240.0, 353.14),
    (250.0, 366.53),
    (260.0, 380.31),
]


def test_constants_match_north_american_ni120_characteristic() -> None:
    assert ni120.R0_OHMS == 120.0
    assert ni120.MIN_TEMPERATURE_C == -80.0
    assert ni120.MAX_TEMPERATURE_C == 260.0


@pytest.mark.parametrize(
    ("temperature_c", "expected_ohms"),
    _PYROMATION_REFERENCE_VALUES,
)
def test_celsius_to_resistance_matches_independent_pyromation_table(
    temperature_c: float,
    expected_ohms: float,
) -> None:
    # Pyromation prints resistance to 0.01 ohm. Minco's printed segment
    # coefficients also require less than 0.001 ohm of explicit continuity
    # stitching. A 0.006-ohm absolute tolerance therefore reflects the source
    # precision without hiding a meaningful curve-selection error.
    assert ni120.celsius_to_resistance(temperature_c) == pytest.approx(
        expected_ohms,
        abs=0.006,
    )


@pytest.mark.parametrize(
    ("temperature_c", "reference_ohms"),
    _PYROMATION_REFERENCE_VALUES[1:-1],
)
def test_reference_resistance_to_celsius_matches_pyromation_table(
    temperature_c: float,
    reference_ohms: float,
) -> None:
    # Exclude the rounded endpoints because 66.60 ohm lies a few nanohms below
    # the exact stitched -80 °C boundary and 380.31 ohm lies slightly above the
    # exact 260 °C boundary. Strict model-domain validation should not be
    # widened merely to accept rounded publication endpoints.
    assert ni120.resistance_to_celsius(reference_ohms) == pytest.approx(
        temperature_c,
        abs=0.01,
    )


@pytest.mark.parametrize(
    "temperature_c",
    [
        -80.0,
        -60.0,
        -30.0,
        0.0,
        30.0,
        60.0,
        90.0,
        120.0,
        150.0,
        180.0,
        210.0,
        240.0,
        260.0,
    ],
)
def test_all_piecewise_boundaries_round_trip(temperature_c: float) -> None:
    resistance = ni120.celsius_to_resistance(temperature_c)
    assert ni120.resistance_to_celsius(resistance) == pytest.approx(
        temperature_c,
        abs=1e-10,
    )


def test_reference_resistance_is_exact_at_zero_celsius() -> None:
    assert ni120.celsius_to_resistance(0.0) == 120.0
    assert ni120.resistance_to_celsius(120.0) == 0.0


def test_minco_stitching_is_explicit_and_tightly_bounded() -> None:
    # Minco publishes twelve independently rounded cubic fits. The generic
    # piecewise model exposes every additive ratio offset rather than silently
    # modifying the source coefficients. For this characteristic the largest
    # applied offset is about 7.2e-6 ratio = 0.000864 ohm at R0=120 ohm.
    adjustments = _curves.NI_6720_NORTH_AMERICAN.continuity_adjustments

    assert len(adjustments) == 12
    assert max(abs(value) for value in adjustments) == pytest.approx(
        7.2e-6,
        rel=0.0,
        abs=1e-10,
    )
    assert max(abs(value) for value in adjustments) <= 1.0e-5
    assert max(abs(value) * ni120.R0_OHMS for value in adjustments) < 0.001


@pytest.mark.parametrize(
    "temperature_c",
    [-80.001, 260.001, math.inf, -math.inf, math.nan],
)
def test_celsius_to_resistance_rejects_out_of_range_temperature(
    temperature_c: float,
) -> None:
    with pytest.raises(ValueError):
        ni120.celsius_to_resistance(temperature_c)


def test_resistance_to_celsius_rejects_out_of_range_resistance() -> None:
    minimum = ni120.celsius_to_resistance(ni120.MIN_TEMPERATURE_C)
    maximum = ni120.celsius_to_resistance(ni120.MAX_TEMPERATURE_C)

    with pytest.raises(ValueError):
        ni120.resistance_to_celsius(math.nextafter(minimum, -math.inf))
    with pytest.raises(ValueError):
        ni120.resistance_to_celsius(math.nextafter(maximum, math.inf))


@pytest.mark.parametrize("resistance_ohms", [0.0, -1.0, math.inf, -math.inf, math.nan])
def test_resistance_to_celsius_rejects_invalid_resistance(
    resistance_ohms: float,
) -> None:
    with pytest.raises(ValueError):
        ni120.resistance_to_celsius(resistance_ohms)


@pytest.mark.parametrize(
    ("temperature_c", "b", "c", "d"),
    [
        (-70.0, 5.779005438e-3, 4.519218356e-6, 1.883007648e-8),
        (-45.0, 5.854808892e-3, 5.782609262e-6, 2.584891485e-8),
        (15.0, 5.899358312e-3, 7.267589932e-6, 1.154640832e-8),
        (75.0, 5.776959768e-3, 9.505643490e-6, -3.088087226e-9),
        (135.0, 5.728761999e-3, 9.138994624e-6, 7.759260700e-10),
        (195.0, 7.795943744e-3, -4.904541625e-6, 3.246957072e-8),
        (250.0, 8.017164189e-4, 2.591705610e-5, -1.300325764e-8),
    ],
)
def test_sensitivity_matches_active_minco_segment_derivative(
    temperature_c: float,
    b: float,
    c: float,
    d: float,
) -> None:
    # Constant stitching offsets deliberately leave derivatives untouched, so
    # dR/dT must remain the derivative of Minco's published active segment.
    expected = ni120.R0_OHMS * (
        b + 2.0 * c * temperature_c + 3.0 * d * temperature_c**2
    )

    assert ni120.resistance_sensitivity_ohms_per_celsius(
        temperature_c
    ) == pytest.approx(expected, abs=1e-12)
    assert ni120.temperature_sensitivity_celsius_per_ohm(
        temperature_c
    ) == pytest.approx(1.0 / expected, abs=1e-15)


def test_characteristic_is_monotonic_across_one_degree_grid() -> None:
    resistances = [
        ni120.celsius_to_resistance(float(temperature_c))
        for temperature_c in range(-80, 261)
    ]
    assert all(
        earlier < later
        for earlier, later in zip(resistances, resistances[1:], strict=False)
    )
