# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from rtd._curves import IEC_60751_PT385
from rtd._models import RTDModel


def _model(r0_ohms: float) -> RTDModel:
    return RTDModel(
        name="test RTD",
        r0_ohms=r0_ohms,
        curve=IEC_60751_PT385,
    )


def test_zero_celsius_equals_r0() -> None:
    model = _model(250.0)
    assert model.celsius_to_resistance(0.0) == 250.0


@pytest.mark.parametrize(
    "temperature_c",
    [-200.0, -100.0, -0.001, 0.0, 25.0, 100.0, 850.0],
)
def test_models_on_same_curve_have_same_resistance_ratio(
    temperature_c: float,
) -> None:
    pt100_model = _model(100.0)
    pt500_model = _model(500.0)
    pt1000_model = _model(1000.0)

    pt100_ratio = pt100_model.celsius_to_resistance(temperature_c) / 100.0
    pt500_ratio = pt500_model.celsius_to_resistance(temperature_c) / 500.0
    pt1000_ratio = pt1000_model.celsius_to_resistance(temperature_c) / 1000.0

    assert pt500_ratio == pytest.approx(pt100_ratio, abs=1e-15)
    assert pt1000_ratio == pytest.approx(pt100_ratio, abs=1e-15)


@pytest.mark.parametrize(
    "temperature_c",
    [-200.0, -175.5, -100.0, -0.001, 0.0, 25.0, 419.75, 850.0],
)
def test_generic_model_temperature_round_trip(
    temperature_c: float,
) -> None:
    model = _model(250.0)
    resistance = model.celsius_to_resistance(temperature_c)
    converted = model.resistance_to_celsius(resistance)

    assert converted == pytest.approx(temperature_c, abs=1e-9)


def test_generic_model_resistance_round_trip() -> None:
    model = _model(250.0)
    resistance = 250.0 * 1.234
    temperature = model.resistance_to_celsius(resistance)
    converted = model.celsius_to_resistance(temperature)

    assert converted == pytest.approx(resistance, abs=1e-12)


def test_generic_model_boundaries_are_supported() -> None:
    model = _model(250.0)

    for temperature_c in (
        model.minimum_temperature_c,
        model.maximum_temperature_c,
    ):
        resistance = model.celsius_to_resistance(temperature_c)
        converted = model.resistance_to_celsius(resistance)
        assert converted == pytest.approx(temperature_c, abs=1e-9)


@pytest.mark.parametrize(
    "r0_ohms",
    [0.0, -1.0, math.inf, -math.inf, math.nan],
)
def test_generic_model_rejects_invalid_r0(r0_ohms: float) -> None:
    with pytest.raises(ValueError):
        _model(r0_ohms)


@pytest.mark.parametrize(
    "temperature_c",
    [-201.0, 851.0, math.inf, -math.inf, math.nan],
)
def test_generic_model_rejects_invalid_temperature(
    temperature_c: float,
) -> None:
    model = _model(250.0)
    with pytest.raises(ValueError):
        model.celsius_to_resistance(temperature_c)


@pytest.mark.parametrize(
    "resistance_ohms",
    [0.0, -1.0, math.inf, -math.inf, math.nan],
)
def test_generic_model_rejects_invalid_resistance(
    resistance_ohms: float,
) -> None:
    model = _model(250.0)
    with pytest.raises(ValueError):
        model.resistance_to_celsius(resistance_ohms)
