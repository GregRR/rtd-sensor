# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
from dataclasses import FrozenInstanceError

import pytest

from rtd import pt100, pt1000
from rtd.models import CallendarVanDusenRTDModel

IEC_A = 3.9083e-3
IEC_B = -5.775e-7
IEC_C = -4.183e-12


def _standard_model(
    *,
    r0_ohms: float = 100.0,
    minimum_temperature_c: float = -200.0,
    maximum_temperature_c: float = 850.0,
) -> CallendarVanDusenRTDModel:
    return CallendarVanDusenRTDModel(
        r0_ohms=r0_ohms,
        a=IEC_A,
        b=IEC_B,
        c=IEC_C,
        minimum_temperature_c=minimum_temperature_c,
        maximum_temperature_c=maximum_temperature_c,
        coefficient_source="IEC 60751 coefficients for equivalence testing",
    )


@pytest.mark.parametrize(
    "temperature_c",
    [-200.0, -100.0, 0.0, 25.0, 100.0, 850.0],
)
def test_standard_coefficients_match_pt100(temperature_c: float) -> None:
    model = _standard_model(r0_ohms=100.0)

    assert model.celsius_to_resistance(temperature_c) == pytest.approx(
        pt100.celsius_to_resistance(temperature_c),
        abs=1e-12,
    )


@pytest.mark.parametrize(
    "temperature_c",
    [-200.0, -100.0, 0.0, 25.0, 100.0, 850.0],
)
def test_standard_coefficients_match_pt1000(temperature_c: float) -> None:
    model = _standard_model(r0_ohms=1000.0)

    assert model.celsius_to_resistance(temperature_c) == pytest.approx(
        pt1000.celsius_to_resistance(temperature_c),
        abs=1e-11,
    )


def test_custom_coefficients_are_used_for_positive_temperature() -> None:
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.025,
        a=3.91e-3,
        b=-5.80e-7,
        c=None,
        minimum_temperature_c=0.0,
        maximum_temperature_c=250.0,
    )
    temperature_c = 100.0
    expected_ratio = 1.0 + model.a * temperature_c + model.b * temperature_c**2

    assert model.celsius_to_resistance(temperature_c) == pytest.approx(
        model.r0_ohms * expected_ratio,
        abs=1e-12,
    )
    assert model.celsius_to_resistance(temperature_c) != pytest.approx(
        pt100.celsius_to_resistance(temperature_c),
        abs=1e-5,
    )


def test_custom_coefficients_are_used_for_negative_temperature() -> None:
    custom_c = -4.20e-12
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.025,
        a=3.91e-3,
        b=-5.80e-7,
        c=custom_c,
        minimum_temperature_c=-100.0,
        maximum_temperature_c=250.0,
    )
    temperature_c = -50.0
    expected_ratio = (
        1.0
        + model.a * temperature_c
        + model.b * temperature_c**2
        + custom_c * (temperature_c - 100.0) * temperature_c**3
    )

    assert model.celsius_to_resistance(temperature_c) == pytest.approx(
        model.r0_ohms * expected_ratio,
        abs=1e-12,
    )


@pytest.mark.parametrize(
    "temperature_c",
    [-100.0, -50.0, -0.001, 0.0, 25.0, 100.0, 250.0],
)
def test_custom_model_round_trip(temperature_c: float) -> None:
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.025,
        a=3.91e-3,
        b=-5.80e-7,
        c=-4.20e-12,
        minimum_temperature_c=-100.0,
        maximum_temperature_c=250.0,
    )

    resistance = model.celsius_to_resistance(temperature_c)

    assert model.resistance_to_celsius(resistance) == pytest.approx(
        temperature_c,
        abs=1e-9,
    )


def test_positive_only_model_can_omit_c() -> None:
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.025,
        a=3.91e-3,
        b=-5.80e-7,
        minimum_temperature_c=25.0,
        maximum_temperature_c=250.0,
    )

    resistance = model.celsius_to_resistance(125.0)

    assert model.c is None
    assert model.resistance_to_celsius(resistance) == pytest.approx(125.0)


def test_negative_only_declared_range_is_supported() -> None:
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.025,
        a=3.91e-3,
        b=-5.80e-7,
        c=-4.20e-12,
        minimum_temperature_c=-100.0,
        maximum_temperature_c=-10.0,
    )

    resistance = model.celsius_to_resistance(-40.0)

    assert model.resistance_to_celsius(resistance) == pytest.approx(-40.0)


def test_positive_only_model_validates_only_declared_range() -> None:
    # This synthetic quadratic decreases near 0 °C but is strictly increasing
    # over 50..100 °C. R0 is still the equation's 0 °C reference; it must not
    # silently expand a calibration's declared validity interval.
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.0,
        a=-5.0e-4,
        b=1.0e-5,
        minimum_temperature_c=50.0,
        maximum_temperature_c=100.0,
    )

    for temperature_c in (50.0, 75.0, 100.0):
        resistance = model.celsius_to_resistance(temperature_c)
        assert model.resistance_to_celsius(resistance) == pytest.approx(
            temperature_c,
            abs=1e-9,
        )

    with pytest.raises(ValueError, match="strictly increasing"):
        CallendarVanDusenRTDModel(
            r0_ohms=100.0,
            a=-5.0e-4,
            b=1.0e-5,
            minimum_temperature_c=0.0,
            maximum_temperature_c=100.0,
        )


def test_negative_only_model_validates_only_declared_range() -> None:
    # This synthetic quadratic is strictly increasing over -100..-50 °C but
    # turns downward before 0 °C. Inversion must remain bounded to the declared
    # negative interval even when R/R0 is greater than 1 there.
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.0,
        a=-8.0e-4,
        b=-1.0e-5,
        c=0.0,
        minimum_temperature_c=-100.0,
        maximum_temperature_c=-50.0,
    )

    temperature_c = -75.0
    resistance = model.celsius_to_resistance(temperature_c)

    assert resistance > model.r0_ohms
    assert model.resistance_to_celsius(resistance) == pytest.approx(
        temperature_c,
        abs=1e-9,
    )

    with pytest.raises(ValueError, match="strictly increasing"):
        CallendarVanDusenRTDModel(
            r0_ohms=100.0,
            a=-8.0e-4,
            b=-1.0e-5,
            c=0.0,
            minimum_temperature_c=-100.0,
            maximum_temperature_c=0.0,
        )


@pytest.mark.parametrize("r0_ohms", [0.0, -1.0])
def test_custom_model_rejects_nonpositive_r0(r0_ohms: float) -> None:
    with pytest.raises(ValueError):
        CallendarVanDusenRTDModel(
            r0_ohms=r0_ohms,
            a=IEC_A,
            b=IEC_B,
            c=None,
            minimum_temperature_c=0.0,
            maximum_temperature_c=250.0,
        )


def test_negative_temperature_range_requires_c() -> None:
    with pytest.raises(ValueError, match="C coefficient is required"):
        CallendarVanDusenRTDModel(
            r0_ohms=100.0,
            a=IEC_A,
            b=IEC_B,
            minimum_temperature_c=-50.0,
            maximum_temperature_c=200.0,
        )


@pytest.mark.parametrize(
    (
        "r0_ohms",
        "a",
        "b",
        "c",
        "minimum_temperature_c",
        "maximum_temperature_c",
    ),
    [
        (math.nan, IEC_A, IEC_B, IEC_C, -100.0, 250.0),
        (math.inf, IEC_A, IEC_B, IEC_C, -100.0, 250.0),
        (100.0, math.nan, IEC_B, IEC_C, -100.0, 250.0),
        (100.0, math.inf, IEC_B, IEC_C, -100.0, 250.0),
        (100.0, IEC_A, math.nan, IEC_C, -100.0, 250.0),
        (100.0, IEC_A, -math.inf, IEC_C, -100.0, 250.0),
        (100.0, IEC_A, IEC_B, math.nan, -100.0, 250.0),
        (100.0, IEC_A, IEC_B, -math.inf, -100.0, 250.0),
        (100.0, IEC_A, IEC_B, IEC_C, math.nan, 250.0),
        (100.0, IEC_A, IEC_B, IEC_C, -100.0, math.inf),
    ],
)
def test_custom_model_rejects_nonfinite_inputs(
    r0_ohms: float,
    a: float,
    b: float,
    c: float,
    minimum_temperature_c: float,
    maximum_temperature_c: float,
) -> None:
    with pytest.raises(ValueError):
        CallendarVanDusenRTDModel(
            r0_ohms=r0_ohms,
            a=a,
            b=b,
            c=c,
            minimum_temperature_c=minimum_temperature_c,
            maximum_temperature_c=maximum_temperature_c,
        )


def test_nonstandard_coefficient_sign_is_allowed_when_curve_is_valid() -> None:
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.0,
        a=3.8e-3,
        b=1.0e-8,
        c=None,
        minimum_temperature_c=0.0,
        maximum_temperature_c=100.0,
    )

    resistance = model.celsius_to_resistance(50.0)

    assert model.resistance_to_celsius(resistance) == pytest.approx(50.0)


def test_custom_model_rejects_interior_nonmonotonic_negative_curve() -> None:
    # End-point slopes are positive for this synthetic curve, but the
    # derivative becomes negative inside the declared range. This guards
    # against validating monotonicity from end points alone.
    with pytest.raises(ValueError, match="strictly increasing"):
        CallendarVanDusenRTDModel(
            r0_ohms=100.0,
            a=0.002203392490416668,
            b=4.231872370200682e-05,
            c=-6.197378914483429e-10,
            minimum_temperature_c=-200.0,
            maximum_temperature_c=0.0,
        )


def test_custom_model_rejects_nonincreasing_positive_range() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        CallendarVanDusenRTDModel(
            r0_ohms=100.0,
            a=1.0e-3,
            b=-1.0e-5,
            c=None,
            minimum_temperature_c=0.0,
            maximum_temperature_c=100.0,
        )


def test_custom_model_rejects_nonpositive_resistance_ratio() -> None:
    with pytest.raises(ValueError, match="resistance ratio must remain positive"):
        CallendarVanDusenRTDModel(
            r0_ohms=100.0,
            a=1.0e-2,
            b=0.0,
            c=0.0,
            minimum_temperature_c=-200.0,
            maximum_temperature_c=-100.0,
        )


@pytest.mark.parametrize(
    ("minimum_temperature_c", "maximum_temperature_c"),
    [
        (100.0, 100.0),
        (101.0, 100.0),
    ],
)
def test_custom_model_rejects_invalid_range(
    minimum_temperature_c: float,
    maximum_temperature_c: float,
) -> None:
    with pytest.raises(ValueError):
        CallendarVanDusenRTDModel(
            r0_ohms=100.0,
            a=IEC_A,
            b=IEC_B,
            c=None,
            minimum_temperature_c=minimum_temperature_c,
            maximum_temperature_c=maximum_temperature_c,
        )


def test_custom_model_enforces_declared_range() -> None:
    model = _standard_model(
        minimum_temperature_c=20.0,
        maximum_temperature_c=120.0,
    )

    with pytest.raises(ValueError):
        model.celsius_to_resistance(19.999)
    with pytest.raises(ValueError):
        model.celsius_to_resistance(120.001)

    below = pt100.celsius_to_resistance(19.999)
    above = pt100.celsius_to_resistance(120.001)
    with pytest.raises(ValueError):
        model.resistance_to_celsius(below)
    with pytest.raises(ValueError):
        model.resistance_to_celsius(above)


def test_coefficient_source_is_retained_and_trimmed() -> None:
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.025,
        a=3.91e-3,
        b=-5.80e-7,
        c=None,
        minimum_temperature_c=0.0,
        maximum_temperature_c=250.0,
        coefficient_source="  Calibration certificate SN-123  ",
    )

    assert model.coefficient_source == "Calibration certificate SN-123"


def test_empty_coefficient_source_is_rejected() -> None:
    with pytest.raises(ValueError, match="Coefficient source must not be empty"):
        CallendarVanDusenRTDModel(
            r0_ohms=100.0,
            a=IEC_A,
            b=IEC_B,
            c=None,
            minimum_temperature_c=0.0,
            maximum_temperature_c=250.0,
            coefficient_source="   ",
        )


def test_custom_model_is_immutable() -> None:
    model = _standard_model()

    with pytest.raises(FrozenInstanceError):
        model.a = 4.0e-3  # type: ignore[misc]
