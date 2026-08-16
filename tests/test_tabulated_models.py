# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
from dataclasses import FrozenInstanceError

import pytest

from rtd_sensor import measurement, uncertainty
from rtd_sensor.exceptions import InvalidRTDModelError, RTDOutOfRangeError
from rtd_sensor.models import TabulatedRTDModel, TabulatedRTDPoint


def _model() -> TabulatedRTDModel:
    return TabulatedRTDModel(
        points=(
            TabulatedRTDPoint(temperature_c=-50.0, resistance_ohms=80.0),
            TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
            TabulatedRTDPoint(temperature_c=100.0, resistance_ohms=150.0),
            TabulatedRTDPoint(temperature_c=200.0, resistance_ohms=220.0),
        ),
        name="Synthetic tabulated RTD",
        table_source="  Synthetic source table  ",
        source_precision="  temperatures 1 °C; resistance 0.1 ohm  ",
    )


def test_tabulated_model_preserves_source_points_and_metadata() -> None:
    model = _model()

    assert model.points == (
        TabulatedRTDPoint(temperature_c=-50.0, resistance_ohms=80.0),
        TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
        TabulatedRTDPoint(temperature_c=100.0, resistance_ohms=150.0),
        TabulatedRTDPoint(temperature_c=200.0, resistance_ohms=220.0),
    )
    assert model.name == "Synthetic tabulated RTD"
    assert model.table_source == "Synthetic source table"
    assert model.source_precision == "temperatures 1 °C; resistance 0.1 ohm"
    assert model.interpolation_method == "linear"
    assert model.minimum_temperature_c == -50.0
    assert model.maximum_temperature_c == 200.0


def test_tabulated_model_snapshots_mutable_point_sequence() -> None:
    points = [
        TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
        TabulatedRTDPoint(temperature_c=100.0, resistance_ohms=150.0),
    ]
    model = TabulatedRTDModel(points=points)
    points.append(TabulatedRTDPoint(temperature_c=200.0, resistance_ohms=220.0))

    assert len(model.points) == 2
    assert isinstance(model.points, tuple)


def test_tabulated_point_and_model_are_immutable() -> None:
    model = _model()

    with pytest.raises(FrozenInstanceError):
        model.points[0].resistance_ohms = 81.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        model.name = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("temperature_c", "expected_resistance"),
    [
        (-50.0, 80.0),
        (0.0, 100.0),
        (100.0, 150.0),
        (200.0, 220.0),
    ],
)
def test_tabulated_forward_preserves_source_points_exactly(
    temperature_c: float,
    expected_resistance: float,
) -> None:
    assert _model().celsius_to_resistance(temperature_c) == expected_resistance


@pytest.mark.parametrize(
    ("temperature_c", "expected_resistance"),
    [
        (-25.0, 90.0),
        (50.0, 125.0),
        (150.0, 185.0),
    ],
)
def test_tabulated_forward_interpolates_linearly(
    temperature_c: float,
    expected_resistance: float,
) -> None:
    assert _model().celsius_to_resistance(temperature_c) == pytest.approx(
        expected_resistance
    )


@pytest.mark.parametrize(
    ("resistance_ohms", "expected_temperature"),
    [
        (80.0, -50.0),
        (100.0, 0.0),
        (150.0, 100.0),
        (220.0, 200.0),
    ],
)
def test_tabulated_inverse_preserves_source_points_exactly(
    resistance_ohms: float,
    expected_temperature: float,
) -> None:
    assert _model().resistance_to_celsius(resistance_ohms) == expected_temperature


@pytest.mark.parametrize(
    ("resistance_ohms", "expected_temperature"),
    [
        (90.0, -25.0),
        (125.0, 50.0),
        (185.0, 150.0),
    ],
)
def test_tabulated_inverse_inverts_intervals(
    resistance_ohms: float,
    expected_temperature: float,
) -> None:
    assert _model().resistance_to_celsius(resistance_ohms) == pytest.approx(
        expected_temperature
    )


@pytest.mark.parametrize(
    "temperature_c",
    [-50.0, -7.25, 0.0, 36.5, 100.0, 199.9, 200.0],
)
def test_tabulated_round_trip(temperature_c: float) -> None:
    model = _model()
    resistance = model.celsius_to_resistance(temperature_c)
    assert model.resistance_to_celsius(resistance) == pytest.approx(
        temperature_c,
        abs=1e-12,
    )


def test_tabulated_sensitivity_uses_active_interval() -> None:
    model = _model()

    assert model.resistance_sensitivity_ohms_per_celsius(-25.0) == pytest.approx(0.4)
    assert model.resistance_sensitivity_ohms_per_celsius(50.0) == pytest.approx(0.5)
    assert model.resistance_sensitivity_ohms_per_celsius(150.0) == pytest.approx(0.7)
    assert model.temperature_sensitivity_celsius_per_ohm(150.0) == pytest.approx(
        1.0 / 0.7
    )


def test_tabulated_knot_sensitivity_uses_right_hand_interval() -> None:
    model = _model()

    assert model.resistance_sensitivity_ohms_per_celsius(0.0) == pytest.approx(0.5)
    assert model.resistance_sensitivity_ohms_per_celsius(100.0) == pytest.approx(0.7)


def test_tabulated_final_endpoint_sensitivity_uses_last_interval() -> None:
    assert _model().resistance_sensitivity_ohms_per_celsius(200.0) == pytest.approx(0.7)


@pytest.mark.parametrize("temperature_c", [-50.000001, 200.000001])
def test_tabulated_model_does_not_extrapolate_temperature(temperature_c: float) -> None:
    with pytest.raises(RTDOutOfRangeError):
        _model().celsius_to_resistance(temperature_c)


@pytest.mark.parametrize("resistance_ohms", [79.999999, 220.000001])
def test_tabulated_model_does_not_extrapolate_resistance(
    resistance_ohms: float,
) -> None:
    with pytest.raises(RTDOutOfRangeError):
        _model().resistance_to_celsius(resistance_ohms)


@pytest.mark.parametrize("temperature_c", [math.nan, math.inf, -math.inf])
def test_tabulated_nonfinite_temperature_remains_plain_value_error(
    temperature_c: float,
) -> None:
    with pytest.raises(ValueError) as caught:
        _model().celsius_to_resistance(temperature_c)
    assert not isinstance(caught.value, RTDOutOfRangeError)


@pytest.mark.parametrize("resistance_ohms", [math.nan, math.inf, -math.inf, 0.0, -1.0])
def test_tabulated_invalid_resistance_remains_plain_value_error(
    resistance_ohms: float,
) -> None:
    with pytest.raises(ValueError) as caught:
        _model().resistance_to_celsius(resistance_ohms)
    assert not isinstance(caught.value, RTDOutOfRangeError)


@pytest.mark.parametrize(
    ("points", "message"),
    [
        ((), "At least two"),
        (
            (TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),),
            "At least two",
        ),
        (
            (
                TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
                TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=101.0),
            ),
            "temperatures must be strictly increasing",
        ),
        (
            (
                TabulatedRTDPoint(temperature_c=10.0, resistance_ohms=101.0),
                TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=102.0),
            ),
            "temperatures must be strictly increasing",
        ),
        (
            (
                TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
                TabulatedRTDPoint(temperature_c=10.0, resistance_ohms=100.0),
            ),
            "resistances must be strictly increasing",
        ),
        (
            (
                TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
                TabulatedRTDPoint(temperature_c=10.0, resistance_ohms=99.0),
            ),
            "resistances must be strictly increasing",
        ),
    ],
)
def test_tabulated_model_rejects_noninvertible_tables(
    points: tuple[TabulatedRTDPoint, ...],
    message: str,
) -> None:
    with pytest.raises(InvalidRTDModelError, match=message):
        TabulatedRTDModel(points=points)


@pytest.mark.parametrize(
    ("temperature_c", "resistance_ohms", "message"),
    [
        (math.nan, 100.0, "temperature must be finite"),
        (0.0, math.inf, "resistance must be finite"),
        (0.0, 0.0, "resistance must be greater than zero"),
    ],
)
def test_tabulated_point_rejects_invalid_source_values(
    temperature_c: float,
    resistance_ohms: float,
    message: str,
) -> None:
    with pytest.raises(InvalidRTDModelError, match=message):
        TabulatedRTDPoint(
            temperature_c=temperature_c,
            resistance_ohms=resistance_ohms,
        )


def test_tabulated_model_rejects_nonpoint_entries() -> None:
    invalid_points: object = ((0.0, 100.0), (100.0, 150.0))
    with pytest.raises(TypeError, match="TabulatedRTDPoint"):
        TabulatedRTDModel(points=invalid_points)  # type: ignore[arg-type]


def test_tabulated_model_rejects_empty_table_source() -> None:
    points = (
        TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
        TabulatedRTDPoint(temperature_c=100.0, resistance_ohms=150.0),
    )
    with pytest.raises(InvalidRTDModelError, match="Table source must not be empty"):
        TabulatedRTDModel(points=points, table_source="   ")


def test_tabulated_model_rejects_empty_source_precision() -> None:
    points = (
        TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
        TabulatedRTDPoint(temperature_c=100.0, resistance_ohms=150.0),
    )
    with pytest.raises(
        InvalidRTDModelError, match="Source precision must not be empty"
    ):
        TabulatedRTDModel(points=points, source_precision="   ")


def test_measurement_composes_with_tabulated_model() -> None:
    class Reader:
        def read_resistance_ohms(self) -> float:
            return 125.0

    temperature_c = measurement.read_temperature_celsius(Reader(), model=_model())
    assert temperature_c == pytest.approx(50.0)


def test_uncertainty_uses_tabulated_local_sensitivity() -> None:
    result = uncertainty.propagate_resistance_uncertainty(
        125.0,
        0.05,
        model=_model(),
    )

    assert result.temperature_c == pytest.approx(50.0)
    assert result.temperature_standard_uncertainty_c == pytest.approx(0.1)
