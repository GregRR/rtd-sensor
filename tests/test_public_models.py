# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
from dataclasses import FrozenInstanceError

import pytest

from rtd_sensor import pt100, pt1000
from rtd_sensor.models import IEC60751RTDModel


@pytest.mark.parametrize(
    "temperature_c",
    [-200.0, -100.0, 0.0, 25.0, 100.0, 850.0],
)
def test_nominal_100_ohm_model_matches_pt100(
    temperature_c: float,
) -> None:
    model = IEC60751RTDModel(r0_ohms=100.0)

    assert model.celsius_to_resistance(temperature_c) == pytest.approx(
        pt100.celsius_to_resistance(temperature_c)
    )


@pytest.mark.parametrize(
    "temperature_c",
    [-200.0, -100.0, 0.0, 25.0, 100.0, 850.0],
)
def test_nominal_1000_ohm_model_matches_pt1000(
    temperature_c: float,
) -> None:
    model = IEC60751RTDModel(r0_ohms=1000.0)

    assert model.celsius_to_resistance(temperature_c) == pytest.approx(
        pt1000.celsius_to_resistance(temperature_c)
    )


def test_characterized_r0_is_exact_at_zero_celsius() -> None:
    model = IEC60751RTDModel(r0_ohms=100.017)

    assert model.celsius_to_resistance(0.0) == 100.017
    assert model.resistance_to_celsius(100.017) == 0.0


def test_characterized_r0_scales_standard_curve() -> None:
    model = IEC60751RTDModel(r0_ohms=100.017)
    nominal_ratio = pt100.celsius_to_resistance(100.0) / 100.0

    assert model.celsius_to_resistance(100.0) == pytest.approx(
        100.017 * nominal_ratio,
        abs=1e-12,
    )


def test_declared_range_can_be_narrower_than_standard_curve() -> None:
    model = IEC60751RTDModel(
        r0_ohms=100.017,
        minimum_temperature_c=20.0,
        maximum_temperature_c=120.0,
    )

    assert model.resistance_to_celsius(
        model.celsius_to_resistance(20.0)
    ) == pytest.approx(20.0, abs=1e-9)
    assert model.resistance_to_celsius(
        model.celsius_to_resistance(120.0)
    ) == pytest.approx(120.0, abs=1e-9)

    with pytest.raises(ValueError):
        model.celsius_to_resistance(19.999)
    with pytest.raises(ValueError):
        model.celsius_to_resistance(120.001)


def test_declared_range_rejects_resistance_outside_range() -> None:
    model = IEC60751RTDModel(
        r0_ohms=100.0,
        minimum_temperature_c=-50.0,
        maximum_temperature_c=250.0,
    )

    below = pt100.celsius_to_resistance(-50.001)
    above = pt100.celsius_to_resistance(250.001)

    with pytest.raises(ValueError):
        model.resistance_to_celsius(below)
    with pytest.raises(ValueError):
        model.resistance_to_celsius(above)


@pytest.mark.parametrize(
    "r0_ohms",
    [0.0, -1.0, math.inf, -math.inf, math.nan],
)
def test_model_rejects_invalid_r0(r0_ohms: float) -> None:
    with pytest.raises(ValueError):
        IEC60751RTDModel(r0_ohms=r0_ohms)


@pytest.mark.parametrize(
    ("minimum_temperature_c", "maximum_temperature_c"),
    [
        (-201.0, 100.0),
        (-100.0, 851.0),
        (100.0, 100.0),
        (101.0, 100.0),
        (math.nan, 100.0),
        (-100.0, math.inf),
    ],
)
def test_model_rejects_invalid_declared_range(
    minimum_temperature_c: float,
    maximum_temperature_c: float,
) -> None:
    with pytest.raises(ValueError):
        IEC60751RTDModel(
            r0_ohms=100.0,
            minimum_temperature_c=minimum_temperature_c,
            maximum_temperature_c=maximum_temperature_c,
        )


def test_model_is_immutable() -> None:
    model = IEC60751RTDModel(r0_ohms=100.0)

    with pytest.raises(FrozenInstanceError):
        model.r0_ohms = 101.0  # type: ignore[misc]
