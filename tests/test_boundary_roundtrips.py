# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
import random

import pytest

from rtd._curves import IEC_60751_PT385
from rtd._models import RTDModel
from rtd.models import CallendarVanDusenRTDModel, IEC60751RTDModel

IEC_A = 3.9083e-3
IEC_B = -5.775e-7
IEC_C = -4.183e-12


def _generic_iec_model(r0_ohms: float) -> RTDModel:
    return RTDModel(
        name="boundary test RTD",
        reference_resistance_ohms=r0_ohms,
        curve=IEC_60751_PT385,
    )


@pytest.mark.parametrize(
    ("r0_ohms", "temperature_c"),
    [
        (768.7896875216958, -200.0),
        (755.0950204485852, 850.0),
    ],
)
def test_regression_characterized_r0_exact_boundary_round_trip(
    r0_ohms: float,
    temperature_c: float,
) -> None:
    """Regression for R0 values that previously rounded outside the curve."""
    model = IEC60751RTDModel(r0_ohms=r0_ohms)

    resistance = model.celsius_to_resistance(temperature_c)

    assert model.resistance_to_celsius(resistance) == temperature_c


def test_iec_boundaries_round_trip_across_seeded_r0_sample() -> None:
    """Exercise endpoint round trips over many deterministic R0 scalings."""
    random_generator = random.Random(20260809)

    for _ in range(1024):
        # Span well beyond normal Pt100/Pt1000 R0 values so the test exercises
        # floating-point scaling rather than a few fortunate decimal values.
        r0_ohms = 10.0 ** random_generator.uniform(-3.0, 6.0)
        model = _generic_iec_model(r0_ohms)

        for temperature_c in (
            model.minimum_temperature_c,
            model.maximum_temperature_c,
        ):
            resistance = model.celsius_to_resistance(temperature_c)
            converted = model.resistance_to_celsius(resistance)
            assert converted == pytest.approx(temperature_c, abs=1e-12)


@pytest.mark.parametrize(
    ("temperature_c", "direction"),
    [
        (-200.0, -math.inf),
        (850.0, math.inf),
    ],
)
def test_curve_accepts_only_one_outward_ulp_at_ratio_boundary(
    temperature_c: float,
    direction: float,
) -> None:
    """The normalization margin is exactly one representable float."""
    boundary_ratio = IEC_60751_PT385.resistance_ratio(temperature_c)
    one_ulp_outside = math.nextafter(boundary_ratio, direction)
    two_ulps_outside = math.nextafter(one_ulp_outside, direction)

    assert (
        IEC_60751_PT385.temperature_from_resistance_ratio(one_ulp_outside)
        == temperature_c
    )

    with pytest.raises(ValueError, match="supported range"):
        IEC_60751_PT385.temperature_from_resistance_ratio(two_ulps_outside)


@pytest.mark.parametrize(
    ("temperature_c", "direction"),
    [
        (-200.0, -math.inf),
        (850.0, math.inf),
    ],
)
def test_public_model_still_rejects_resistance_beyond_boundary(
    temperature_c: float,
    direction: float,
) -> None:
    """Ratio normalization must not widen the public resistance range."""
    model = _generic_iec_model(755.0950204485852)
    boundary_resistance = model.celsius_to_resistance(temperature_c)
    outside_resistance = math.nextafter(boundary_resistance, direction)

    with pytest.raises(ValueError, match="supported .* range"):
        model.resistance_to_celsius(outside_resistance)


def test_custom_cvd_boundaries_round_trip_across_seeded_parameter_space() -> None:
    """Stress declared boundaries across varied valid custom CVD models."""
    random_generator = random.Random(60751)

    for index in range(300):
        r0_ohms = 10.0 ** random_generator.uniform(-3.0, 6.0)
        a = IEC_A * random_generator.uniform(0.97, 1.03)
        b = IEC_B * random_generator.uniform(0.90, 1.10)
        c = IEC_C * random_generator.uniform(0.90, 1.10)

        range_kind = index % 3
        if range_kind == 0:
            minimum_temperature_c = random_generator.uniform(-200.0, -1.0)
            maximum_temperature_c = random_generator.uniform(1.0, 850.0)
            model_c: float | None = c
        elif range_kind == 1:
            minimum_temperature_c = random_generator.uniform(0.0, 100.0)
            maximum_temperature_c = random_generator.uniform(101.0, 850.0)
            model_c = None
        else:
            minimum_temperature_c = random_generator.uniform(-200.0, -101.0)
            maximum_temperature_c = random_generator.uniform(-100.0, -0.001)
            model_c = c

        model = CallendarVanDusenRTDModel(
            r0_ohms=r0_ohms,
            a=a,
            b=b,
            c=model_c,
            minimum_temperature_c=minimum_temperature_c,
            maximum_temperature_c=maximum_temperature_c,
        )

        for temperature_c in (
            minimum_temperature_c,
            maximum_temperature_c,
        ):
            resistance = model.celsius_to_resistance(temperature_c)
            converted = model.resistance_to_celsius(resistance)
            assert converted == pytest.approx(temperature_c, abs=1e-9)
