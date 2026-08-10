# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
import random
from dataclasses import FrozenInstanceError

import pytest

from rtd.models import PolynomialRTDModel


def _cubic_model() -> PolynomialRTDModel:
    return PolynomialRTDModel(
        reference_resistance_ohms=1000.0,
        reference_temperature_c=0.0,
        coefficients=(5.0e-3, 4.0e-6, 1.0e-9),
        minimum_temperature_c=-60.0,
        maximum_temperature_c=200.0,
        name="Synthetic cubic RTD",
        coefficient_source="Independent synthetic test characteristic",
    )


def test_reference_temperature_equals_reference_resistance() -> None:
    model = PolynomialRTDModel(
        reference_resistance_ohms=10.0,
        reference_temperature_c=25.0,
        coefficients=(0.01,),
        minimum_temperature_c=-20.0,
        maximum_temperature_c=80.0,
    )

    assert model.celsius_to_resistance(25.0) == 10.0
    assert model.resistance_to_celsius(10.0) == 25.0


def test_reference_temperature_need_not_be_zero() -> None:
    model = PolynomialRTDModel(
        reference_resistance_ohms=10.0,
        reference_temperature_c=25.0,
        coefficients=(0.01,),
        minimum_temperature_c=-20.0,
        maximum_temperature_c=80.0,
    )

    assert model.celsius_to_resistance(30.0) == pytest.approx(10.5)
    assert model.resistance_to_celsius(10.5) == pytest.approx(30.0, abs=1e-12)


def test_polynomial_forward_equation_matches_direct_evaluation() -> None:
    model = _cubic_model()
    temperature_c = 87.25
    expected_ratio = (
        1.0
        + 5.0e-3 * temperature_c
        + 4.0e-6 * temperature_c**2
        + 1.0e-9 * temperature_c**3
    )

    assert model.celsius_to_resistance(temperature_c) == pytest.approx(
        1000.0 * expected_ratio,
        rel=0.0,
        abs=1e-12,
    )


@pytest.mark.parametrize(
    "temperature_c",
    [-60.0, -40.5, -0.001, 0.0, 23.75, 100.0, 199.999, 200.0],
)
def test_polynomial_model_temperature_round_trip(temperature_c: float) -> None:
    model = _cubic_model()
    resistance = model.celsius_to_resistance(temperature_c)

    assert model.resistance_to_celsius(resistance) == pytest.approx(
        temperature_c,
        abs=1e-11,
    )


def test_polynomial_model_resistance_round_trip() -> None:
    model = _cubic_model()
    resistance = 1423.75
    temperature_c = model.resistance_to_celsius(resistance)

    assert model.celsius_to_resistance(temperature_c) == pytest.approx(
        resistance,
        abs=1e-10,
    )


def test_polynomial_model_analytical_sensitivity() -> None:
    model = _cubic_model()
    temperature_c = 75.0
    expected_ratio_slope = (
        5.0e-3 + 2.0 * 4.0e-6 * temperature_c + 3.0 * 1.0e-9 * temperature_c**2
    )
    expected_ohms_per_celsius = 1000.0 * expected_ratio_slope

    assert model.resistance_sensitivity_ohms_per_celsius(
        temperature_c
    ) == pytest.approx(expected_ohms_per_celsius, rel=0.0, abs=1e-14)
    assert model.temperature_sensitivity_celsius_per_ohm(
        temperature_c
    ) == pytest.approx(1.0 / expected_ohms_per_celsius, rel=0.0, abs=1e-14)


def test_polynomial_sensitivity_matches_central_difference() -> None:
    model = _cubic_model()
    temperature_c = 63.125
    delta_c = 1e-4
    numerical_slope = (
        model.celsius_to_resistance(temperature_c + delta_c)
        - model.celsius_to_resistance(temperature_c - delta_c)
    ) / (2.0 * delta_c)

    assert model.resistance_sensitivity_ohms_per_celsius(
        temperature_c
    ) == pytest.approx(numerical_slope, rel=2e-10)


def test_polynomial_model_preserves_metadata_and_is_immutable() -> None:
    model = _cubic_model()

    assert model.name == "Synthetic cubic RTD"
    assert model.coefficient_source == "Independent synthetic test characteristic"
    assert model.coefficients == (5.0e-3, 4.0e-6, 1.0e-9)

    with pytest.raises(FrozenInstanceError):
        model.reference_resistance_ohms = 999.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"reference_resistance_ohms": 0.0}, "Reference resistance"),
        ({"reference_resistance_ohms": -1.0}, "Reference resistance"),
        ({"reference_resistance_ohms": math.inf}, "Reference resistance"),
        ({"reference_temperature_c": math.nan}, "Reference temperature"),
        ({"minimum_temperature_c": math.nan}, "Minimum temperature"),
        ({"maximum_temperature_c": math.inf}, "Maximum temperature"),
        (
            {"minimum_temperature_c": 10.0, "maximum_temperature_c": 10.0},
            "Minimum temperature",
        ),
        ({"coefficients": ()}, "At least one polynomial coefficient"),
        ({"coefficients": (math.nan,)}, "Polynomial coefficients"),
        ({"coefficients": (math.inf,)}, "Polynomial coefficients"),
        ({"coefficients": (0.01,) * 13}, "degree must not exceed 12"),
        ({"coefficient_source": "   "}, "Coefficient source"),
    ],
)
def test_polynomial_model_rejects_invalid_definition(
    kwargs: dict[str, object],
    message: str,
) -> None:
    defaults: dict[str, object] = {
        "reference_resistance_ohms": 100.0,
        "reference_temperature_c": 0.0,
        "coefficients": (0.01,),
        "minimum_temperature_c": -20.0,
        "maximum_temperature_c": 50.0,
    }
    defaults.update(kwargs)

    with pytest.raises((TypeError, ValueError), match=message):
        PolynomialRTDModel(**defaults)  # type: ignore[arg-type]


def test_polynomial_model_rejects_nonpositive_resistance_ratio() -> None:
    with pytest.raises(ValueError, match="resistance ratio must remain positive"):
        PolynomialRTDModel(
            reference_resistance_ohms=100.0,
            reference_temperature_c=0.0,
            coefficients=(0.6,),
            minimum_temperature_c=-2.0,
            maximum_temperature_c=1.0,
        )


def test_polynomial_model_rejects_decreasing_curve() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        PolynomialRTDModel(
            reference_resistance_ohms=100.0,
            coefficients=(-0.01,),
            minimum_temperature_c=-10.0,
            maximum_temperature_c=10.0,
        )


def test_polynomial_model_rejects_hidden_negative_slope_between_endpoints() -> None:
    # This ratio polynomial has slope
    #   s(T) = T**2 - 0.6*T + 0.08,
    # whose minimum at T=0.3 is negative even though the endpoint slopes over
    # [-1, 1] are both positive. A coarse endpoint-only or sparse-grid check
    # could therefore accept a curve that is not invertible everywhere.
    with pytest.raises(ValueError, match="strictly increasing"):
        PolynomialRTDModel(
            reference_resistance_ohms=100.0,
            coefficients=(0.08, -0.3, 1.0 / 3.0),
            minimum_temperature_c=-1.0,
            maximum_temperature_c=1.0,
        )


def test_polynomial_model_rejects_slope_that_touches_zero() -> None:
    # s(T) = (T - 0.3)**2 reaches exactly zero at an interior extremum.
    with pytest.raises(ValueError, match="strictly increasing"):
        PolynomialRTDModel(
            reference_resistance_ohms=100.0,
            coefficients=(0.09, -0.3, 1.0 / 3.0),
            minimum_temperature_c=-1.0,
            maximum_temperature_c=1.0,
        )


@pytest.mark.parametrize(
    "temperature_c",
    [-20.000001, 50.000001, math.inf, -math.inf, math.nan],
)
def test_polynomial_model_rejects_out_of_range_temperature(
    temperature_c: float,
) -> None:
    model = PolynomialRTDModel(
        reference_resistance_ohms=100.0,
        coefficients=(0.01,),
        minimum_temperature_c=-20.0,
        maximum_temperature_c=50.0,
    )

    with pytest.raises(ValueError):
        model.celsius_to_resistance(temperature_c)


def test_polynomial_model_rejects_resistance_outside_range() -> None:
    model = PolynomialRTDModel(
        reference_resistance_ohms=100.0,
        coefficients=(0.01,),
        minimum_temperature_c=-20.0,
        maximum_temperature_c=50.0,
    )
    minimum = model.celsius_to_resistance(-20.0)
    maximum = model.celsius_to_resistance(50.0)

    with pytest.raises(ValueError, match="below"):
        model.resistance_to_celsius(math.nextafter(minimum, -math.inf))
    with pytest.raises(ValueError, match="above"):
        model.resistance_to_celsius(math.nextafter(maximum, math.inf))


def test_polynomial_boundary_round_trips_across_varied_reference_models() -> None:
    random_generator = random.Random(20260810)

    for _ in range(500):
        reference_resistance = 10.0 ** random_generator.uniform(0.0, 4.0)
        reference_temperature = random_generator.uniform(-10.0, 40.0)
        half_range = random_generator.uniform(5.0, 40.0)
        minimum_temperature = reference_temperature - half_range
        maximum_temperature = reference_temperature + half_range

        # A + B*x^3 has derivative A + 3*B*x^2, so choosing positive A/B
        # guarantees a strictly increasing characteristic. Keep the terms small
        # enough that the normalized resistance remains positive at both ends.
        a = random_generator.uniform(5e-4, 5e-3)
        b = random_generator.uniform(0.0, 2e-7)
        model = PolynomialRTDModel(
            reference_resistance_ohms=reference_resistance,
            reference_temperature_c=reference_temperature,
            coefficients=(a, 0.0, b),
            minimum_temperature_c=minimum_temperature,
            maximum_temperature_c=maximum_temperature,
        )

        for boundary_c in (minimum_temperature, maximum_temperature):
            resistance = model.celsius_to_resistance(boundary_c)
            converted = model.resistance_to_celsius(resistance)
            assert converted == pytest.approx(boundary_c, abs=1e-10)
