# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
import random
from dataclasses import FrozenInstanceError

import pytest

from rtd import uncertainty
from rtd.models import PiecewisePolynomialRTDModel, PiecewisePolynomialSegment


def _continuous_model() -> PiecewisePolynomialRTDModel:
    return PiecewisePolynomialRTDModel(
        reference_resistance_ohms=100.0,
        reference_temperature_c=0.0,
        segments=(
            PiecewisePolynomialSegment(
                minimum_temperature_c=-10.0,
                maximum_temperature_c=0.0,
                coefficients=(1.0, 0.01),
            ),
            PiecewisePolynomialSegment(
                minimum_temperature_c=0.0,
                maximum_temperature_c=10.0,
                coefficients=(1.0, 0.02),
            ),
        ),
        name="Synthetic piecewise RTD",
        coefficient_source="Synthetic independent segment equations",
    )


def test_piecewise_forward_uses_full_segment_polynomials() -> None:
    model = _continuous_model()

    assert model.celsius_to_resistance(-5.0) == pytest.approx(95.0)
    assert model.celsius_to_resistance(0.0) == 100.0
    assert model.celsius_to_resistance(5.0) == pytest.approx(110.0)


@pytest.mark.parametrize(
    "temperature_c",
    [-10.0, -7.25, -0.001, 0.0, 0.001, 4.5, 9.999, 10.0],
)
def test_piecewise_temperature_round_trip(temperature_c: float) -> None:
    model = _continuous_model()
    resistance = model.celsius_to_resistance(temperature_c)

    assert model.resistance_to_celsius(resistance) == pytest.approx(
        temperature_c,
        abs=1e-11,
    )


def test_piecewise_resistance_round_trip() -> None:
    model = _continuous_model()
    resistance = 106.25
    temperature_c = model.resistance_to_celsius(resistance)

    assert model.celsius_to_resistance(temperature_c) == pytest.approx(
        resistance,
        abs=1e-11,
    )


def test_piecewise_segment_can_use_local_temperature_origin() -> None:
    model = PiecewisePolynomialRTDModel(
        reference_resistance_ohms=10.0,
        reference_temperature_c=25.0,
        segments=(
            PiecewisePolynomialSegment(
                minimum_temperature_c=20.0,
                maximum_temperature_c=30.0,
                temperature_origin_c=25.0,
                coefficients=(1.0, 0.01),
            ),
        ),
    )

    assert model.celsius_to_resistance(25.0) == 10.0
    assert model.celsius_to_resistance(30.0) == pytest.approx(10.5)
    assert model.resistance_to_celsius(9.5) == pytest.approx(20.0, abs=1e-12)


def test_piecewise_sensitivity_uses_active_segment() -> None:
    model = _continuous_model()

    assert model.resistance_sensitivity_ohms_per_celsius(-1.0) == pytest.approx(1.0)
    assert model.resistance_sensitivity_ohms_per_celsius(1.0) == pytest.approx(2.0)


def test_piecewise_boundary_sensitivity_uses_right_hand_segment() -> None:
    model = _continuous_model()

    # Interior joins belong to the segment on their right. Published piecewise
    # fits need not be exactly C1-continuous, so the one-sided convention makes
    # the sensitivity result deterministic rather than pretending both slopes
    # are mathematically identical.
    assert model.resistance_sensitivity_ohms_per_celsius(0.0) == pytest.approx(2.0)


def test_piecewise_final_endpoint_sensitivity_uses_last_segment() -> None:
    model = _continuous_model()

    assert model.resistance_sensitivity_ohms_per_celsius(10.0) == pytest.approx(2.0)


def test_piecewise_preserves_source_segments_and_metadata() -> None:
    model = _continuous_model()

    assert model.name == "Synthetic piecewise RTD"
    assert model.coefficient_source == "Synthetic independent segment equations"
    assert model.minimum_temperature_c == -10.0
    assert model.maximum_temperature_c == 10.0
    assert model.continuity_adjustments == (0.0, 0.0)
    assert model.segments[0].coefficients == (1.0, 0.01)

    with pytest.raises(FrozenInstanceError):
        model.reference_resistance_ohms = 99.0  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        model.segments[0].coefficients = (1.0, 0.02)  # type: ignore[misc]


def test_piecewise_opt_in_stitches_small_published_join_rounding() -> None:
    model = PiecewisePolynomialRTDModel(
        reference_resistance_ohms=100.0,
        segments=(
            PiecewisePolynomialSegment(
                minimum_temperature_c=-10.0,
                maximum_temperature_c=0.0,
                coefficients=(1.0, 0.01),
            ),
            PiecewisePolynomialSegment(
                minimum_temperature_c=0.0,
                maximum_temperature_c=10.0,
                coefficients=(1.0, 0.01),
            ),
            PiecewisePolynomialSegment(
                minimum_temperature_c=10.0,
                maximum_temperature_c=20.0,
                # At 10 °C this printed source fit is 1e-6 below the
                # preceding segment. The explicit allowance authorizes only
                # the constant offset needed to restore an invertible join.
                coefficients=(0.999999, 0.01),
            ),
        ),
        maximum_continuity_adjustment_ratio=2e-6,
    )

    assert model.segments[2].coefficients == (0.999999, 0.01)
    assert model.continuity_adjustments == pytest.approx((0.0, 0.0, 1e-6))
    assert model.celsius_to_resistance(10.0) == pytest.approx(110.0)
    assert model.celsius_to_resistance(10.000001) > 110.0
    assert model.resistance_to_celsius(110.0) == pytest.approx(10.0, abs=1e-12)


def test_piecewise_stitching_is_anchored_at_reference_segment() -> None:
    model = PiecewisePolynomialRTDModel(
        reference_resistance_ohms=100.0,
        segments=(
            PiecewisePolynomialSegment(
                minimum_temperature_c=-10.0,
                maximum_temperature_c=0.0,
                coefficients=(1.000001, 0.01),
            ),
            PiecewisePolynomialSegment(
                minimum_temperature_c=0.0,
                maximum_temperature_c=10.0,
                coefficients=(1.0, 0.02),
            ),
        ),
        maximum_continuity_adjustment_ratio=2e-6,
    )

    # The 0 °C segment is the reference anchor and is not shifted. The older
    # segment is shifted toward it, preserving the declared 100 Ω at 0 °C.
    assert model.continuity_adjustments == pytest.approx((-1e-6, 0.0))
    assert model.celsius_to_resistance(0.0) == 100.0


def test_piecewise_default_rejects_source_level_join_discontinuity() -> None:
    with pytest.raises(ValueError, match="requires normalized-ratio adjustment"):
        PiecewisePolynomialRTDModel(
            reference_resistance_ohms=100.0,
            segments=(
                PiecewisePolynomialSegment(
                    minimum_temperature_c=-10.0,
                    maximum_temperature_c=0.0,
                    coefficients=(1.0, 0.01),
                ),
                PiecewisePolynomialSegment(
                    minimum_temperature_c=0.0,
                    maximum_temperature_c=10.0,
                    coefficients=(1.0, 0.01),
                ),
                PiecewisePolynomialSegment(
                    minimum_temperature_c=10.0,
                    maximum_temperature_c=20.0,
                    coefficients=(0.999999, 0.01),
                ),
            ),
        )


def test_piecewise_rejects_join_larger_than_explicit_allowance() -> None:
    with pytest.raises(ValueError, match="exceeding the declared maximum"):
        PiecewisePolynomialRTDModel(
            reference_resistance_ohms=100.0,
            segments=(
                PiecewisePolynomialSegment(
                    minimum_temperature_c=-10.0,
                    maximum_temperature_c=0.0,
                    coefficients=(1.0, 0.01),
                ),
                PiecewisePolynomialSegment(
                    minimum_temperature_c=0.0,
                    maximum_temperature_c=10.0,
                    coefficients=(1.0, 0.01),
                ),
                PiecewisePolynomialSegment(
                    minimum_temperature_c=10.0,
                    maximum_temperature_c=20.0,
                    coefficients=(0.999, 0.01),
                ),
            ),
            maximum_continuity_adjustment_ratio=1e-5,
        )


def test_piecewise_rejects_reference_segment_that_does_not_define_rref() -> None:
    with pytest.raises(ValueError, match="normalized resistance ratio of 1"):
        PiecewisePolynomialRTDModel(
            reference_resistance_ohms=100.0,
            segments=(
                PiecewisePolynomialSegment(
                    minimum_temperature_c=-10.0,
                    maximum_temperature_c=10.0,
                    coefficients=(1.0001, 0.01),
                ),
            ),
            maximum_continuity_adjustment_ratio=1.0,
        )


@pytest.mark.parametrize(
    ("segments", "message"),
    [
        ((), "At least one piecewise polynomial segment"),
        (
            (
                PiecewisePolynomialSegment(
                    minimum_temperature_c=-10.0,
                    maximum_temperature_c=-1.0,
                    coefficients=(1.0, 0.01),
                ),
                PiecewisePolynomialSegment(
                    minimum_temperature_c=0.0,
                    maximum_temperature_c=10.0,
                    coefficients=(1.0, 0.01),
                ),
            ),
            "temperature gaps",
        ),
        (
            (
                PiecewisePolynomialSegment(
                    minimum_temperature_c=-10.0,
                    maximum_temperature_c=1.0,
                    coefficients=(1.0, 0.01),
                ),
                PiecewisePolynomialSegment(
                    minimum_temperature_c=0.0,
                    maximum_temperature_c=10.0,
                    coefficients=(1.0, 0.01),
                ),
            ),
            "overlap",
        ),
    ],
)
def test_piecewise_rejects_invalid_segment_partition(
    segments: tuple[PiecewisePolynomialSegment, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        PiecewisePolynomialRTDModel(
            reference_resistance_ohms=100.0,
            segments=segments,
        )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"minimum_temperature_c": 0.0, "maximum_temperature_c": 0.0}, "below"),
        ({"coefficients": ()}, "At least one segment coefficient"),
        ({"coefficients": (math.nan, 0.01)}, "coefficients must be finite"),
        ({"coefficients": (math.inf, 0.01)}, "coefficients must be finite"),
        ({"coefficients": (1.0,) + (0.01,) * 13}, "degree must not exceed 12"),
        ({"temperature_origin_c": math.nan}, "temperature origin must be finite"),
    ],
)
def test_piecewise_segment_rejects_invalid_definition(
    kwargs: dict[str, object],
    message: str,
) -> None:
    defaults: dict[str, object] = {
        "minimum_temperature_c": -10.0,
        "maximum_temperature_c": 10.0,
        "coefficients": (1.0, 0.01),
    }
    defaults.update(kwargs)

    with pytest.raises((TypeError, ValueError), match=message):
        PiecewisePolynomialSegment(**defaults)  # type: ignore[arg-type]


def test_piecewise_segment_rejects_nonpositive_ratio() -> None:
    with pytest.raises(ValueError, match="resistance ratio must remain positive"):
        PiecewisePolynomialSegment(
            minimum_temperature_c=-2.0,
            maximum_temperature_c=1.0,
            coefficients=(1.0, 0.6),
        )


def test_piecewise_segment_rejects_decreasing_curve() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        PiecewisePolynomialSegment(
            minimum_temperature_c=-10.0,
            maximum_temperature_c=10.0,
            coefficients=(1.0, -0.01),
        )


def test_piecewise_segment_rejects_hidden_negative_slope() -> None:
    # Full ratio polynomial with s(T) = T**2 - 0.6*T + 0.08. Its slope is
    # positive at both endpoints of [-1, 1] but negative around T=0.3.
    with pytest.raises(ValueError, match="strictly increasing"):
        PiecewisePolynomialSegment(
            minimum_temperature_c=-1.0,
            maximum_temperature_c=1.0,
            coefficients=(1.0, 0.08, -0.3, 1.0 / 3.0),
        )


@pytest.mark.parametrize(
    "temperature_c",
    [-10.000001, 10.000001, math.inf, -math.inf, math.nan],
)
def test_piecewise_rejects_out_of_range_temperature(temperature_c: float) -> None:
    model = _continuous_model()

    with pytest.raises(ValueError):
        model.celsius_to_resistance(temperature_c)


def test_piecewise_rejects_resistance_below_and_above_range() -> None:
    model = _continuous_model()
    minimum = model.celsius_to_resistance(-10.0)
    maximum = model.celsius_to_resistance(10.0)

    with pytest.raises(ValueError):
        model.resistance_to_celsius(math.nextafter(minimum, -math.inf))
    with pytest.raises(ValueError):
        model.resistance_to_celsius(math.nextafter(maximum, math.inf))


def test_piecewise_exact_boundary_round_trips_survive_reference_scaling() -> None:
    model = PiecewisePolynomialRTDModel(
        reference_resistance_ohms=755.0950204485852,
        segments=(
            PiecewisePolynomialSegment(
                minimum_temperature_c=-10.0,
                maximum_temperature_c=0.0,
                coefficients=(1.0, 0.01),
            ),
            PiecewisePolynomialSegment(
                minimum_temperature_c=0.0,
                maximum_temperature_c=10.0,
                coefficients=(1.0, 0.02),
            ),
        ),
    )

    for temperature_c in (-10.0, 0.0, 10.0):
        resistance = model.celsius_to_resistance(temperature_c)
        assert model.resistance_to_celsius(resistance) == pytest.approx(
            temperature_c,
            abs=1e-12,
        )


def test_piecewise_randomized_continuous_models_round_trip_across_joins() -> None:
    rng = random.Random(0x50494543)

    for _ in range(200):
        left_slope = rng.uniform(0.001, 0.005)
        middle_slope = rng.uniform(0.001, 0.005)
        right_slope = rng.uniform(0.001, 0.005)

        # The middle segment contains the 0 °C reference. Choose neighboring
        # constants from the shared-boundary values so the independently
        # sloped segments form one continuous, strictly increasing curve.
        left_boundary = -10.0
        right_boundary = 20.0
        middle_left_ratio = 1.0 + middle_slope * left_boundary
        middle_right_ratio = 1.0 + middle_slope * right_boundary
        left_constant = middle_left_ratio - left_slope * left_boundary
        right_constant = middle_right_ratio - right_slope * right_boundary

        model = PiecewisePolynomialRTDModel(
            reference_resistance_ohms=rng.uniform(10.0, 2000.0),
            segments=(
                PiecewisePolynomialSegment(
                    minimum_temperature_c=-50.0,
                    maximum_temperature_c=left_boundary,
                    coefficients=(left_constant, left_slope),
                ),
                PiecewisePolynomialSegment(
                    minimum_temperature_c=left_boundary,
                    maximum_temperature_c=right_boundary,
                    coefficients=(1.0, middle_slope),
                ),
                PiecewisePolynomialSegment(
                    minimum_temperature_c=right_boundary,
                    maximum_temperature_c=80.0,
                    coefficients=(right_constant, right_slope),
                ),
            ),
        )

        for temperature_c in (
            -50.0,
            left_boundary,
            rng.uniform(-49.0, 79.0),
            0.0,
            right_boundary,
            80.0,
        ):
            resistance = model.celsius_to_resistance(temperature_c)
            assert model.resistance_to_celsius(resistance) == pytest.approx(
                temperature_c,
                abs=1e-10,
            )


def test_piecewise_model_integrates_with_uncertainty_protocol() -> None:
    model = _continuous_model()
    resistance = model.celsius_to_resistance(5.0)

    result = uncertainty.propagate_resistance_uncertainty(
        resistance,
        0.2,
        model=model,
    )

    assert result.temperature_c == pytest.approx(5.0, abs=1e-11)
    assert result.temperature_standard_uncertainty_c == pytest.approx(0.1)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reference_resistance_ohms", True),
        ("reference_temperature_c", False),
        ("maximum_continuity_adjustment_ratio", True),
    ],
)
def test_piecewise_model_rejects_boolean_numeric_inputs(
    field: str,
    value: bool,
) -> None:
    kwargs: dict[str, object] = {
        "reference_resistance_ohms": 100.0,
        "reference_temperature_c": 0.0,
        "maximum_continuity_adjustment_ratio": 0.0,
        "segments": (
            PiecewisePolynomialSegment(
                minimum_temperature_c=-10.0,
                maximum_temperature_c=10.0,
                coefficients=(1.0, 0.01),
            ),
        ),
    }
    kwargs[field] = value

    with pytest.raises(TypeError):
        PiecewisePolynomialRTDModel(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("minimum_temperature_c", True),
        ("maximum_temperature_c", False),
        ("temperature_origin_c", True),
        ("coefficients", (1.0, False)),
    ],
)
def test_piecewise_segment_rejects_boolean_numeric_inputs(
    field: str,
    value: object,
) -> None:
    kwargs: dict[str, object] = {
        "minimum_temperature_c": -10.0,
        "maximum_temperature_c": 10.0,
        "temperature_origin_c": 0.0,
        "coefficients": (1.0, 0.01),
    }
    kwargs[field] = value

    with pytest.raises(TypeError):
        PiecewisePolynomialSegment(**kwargs)  # type: ignore[arg-type]


def test_piecewise_rejects_invalid_public_model_metadata() -> None:
    segment = PiecewisePolynomialSegment(
        minimum_temperature_c=-10.0,
        maximum_temperature_c=10.0,
        coefficients=(1.0, 0.01),
    )

    with pytest.raises(ValueError, match="Coefficient source"):
        PiecewisePolynomialRTDModel(
            reference_resistance_ohms=100.0,
            segments=(segment,),
            coefficient_source="   ",
        )
    with pytest.raises(ValueError, match="must not be negative"):
        PiecewisePolynomialRTDModel(
            reference_resistance_ohms=100.0,
            segments=(segment,),
            maximum_continuity_adjustment_ratio=-1e-6,
        )
    with pytest.raises(ValueError, match="within the piecewise range"):
        PiecewisePolynomialRTDModel(
            reference_resistance_ohms=100.0,
            segments=(segment,),
            reference_temperature_c=20.0,
        )
    with pytest.raises(TypeError, match="PiecewisePolynomialSegment"):
        PiecewisePolynomialRTDModel(
            reference_resistance_ohms=100.0,
            segments=(object(),),  # type: ignore[arg-type]
        )
