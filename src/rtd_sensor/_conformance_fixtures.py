# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Language-neutral custom-model fixture definitions for conformance v1.

These fixtures are synthetic interoperability cases, not additional built-in
RTD models or scientific reference data.  They exercise configurable-model
behavior that cannot be represented by the nominal built-in model catalog.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import (
    CallendarVanDusenRTDModel,
    IEC60751RTDModel,
    PiecewisePolynomialRTDModel,
    PiecewisePolynomialSegment,
    PolynomialRTDModel,
)

type FixtureStatus = Literal["ok", "invalid_model"]


@dataclass(frozen=True, slots=True)
class FixtureAnchor:
    """One explicit valid-domain temperature anchor for a model fixture."""

    temperature_c: float
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CharacteristicModelFixture:
    """Fixture that composes a published characteristic with model-specific Rref."""

    fixture_id: str
    display_name: str
    fixture_purpose: str
    expected_status: FixtureStatus
    characteristic_id: str
    reference_resistance_ohms: float
    minimum_temperature_c: float
    maximum_temperature_c: float
    anchors: tuple[FixtureAnchor, ...] = ()


@dataclass(frozen=True, slots=True)
class CallendarVanDusenFixture:
    """Fixture for a configurable Callendar-Van Dusen model definition."""

    fixture_id: str
    display_name: str
    fixture_purpose: str
    expected_status: FixtureStatus
    reference_resistance_ohms: float
    a: float
    b: float
    c: float | None
    minimum_temperature_c: float
    maximum_temperature_c: float
    anchors: tuple[FixtureAnchor, ...] = ()


@dataclass(frozen=True, slots=True)
class PolynomialFixture:
    """Fixture for a configurable normalized polynomial model definition."""

    fixture_id: str
    display_name: str
    fixture_purpose: str
    expected_status: FixtureStatus
    reference_resistance_ohms: float
    reference_temperature_c: float
    coefficients: tuple[float, ...]
    minimum_temperature_c: float
    maximum_temperature_c: float
    anchors: tuple[FixtureAnchor, ...] = ()


@dataclass(frozen=True, slots=True)
class PiecewiseSegmentFixture:
    """One source interval in a piecewise-polynomial conformance fixture."""

    minimum_temperature_c: float
    maximum_temperature_c: float
    coefficients: tuple[float, ...]
    temperature_origin_c: float = 0.0


@dataclass(frozen=True, slots=True)
class PiecewisePolynomialFixture:
    """Fixture for a configurable piecewise-polynomial model definition."""

    fixture_id: str
    display_name: str
    fixture_purpose: str
    expected_status: FixtureStatus
    reference_resistance_ohms: float
    reference_temperature_c: float
    segments: tuple[PiecewiseSegmentFixture, ...]
    maximum_continuity_adjustment_ratio: float = 0.0
    anchors: tuple[FixtureAnchor, ...] = ()


type ModelFixture = (
    CharacteristicModelFixture
    | CallendarVanDusenFixture
    | PolynomialFixture
    | PiecewisePolynomialFixture
)
type ConfigurableFixtureModel = (
    IEC60751RTDModel
    | CallendarVanDusenRTDModel
    | PolynomialRTDModel
    | PiecewisePolynomialRTDModel
)


MODEL_FIXTURES: tuple[ModelFixture, ...] = (
    CharacteristicModelFixture(
        fixture_id="calibrated_pt385_r0_99p5",
        display_name="Characterized PT-385 model with R0 = 99.5 ohm",
        fixture_purpose=(
            "Verify characterized reference resistance below 100 ohm across the "
            "full PT-385 characteristic range."
        ),
        expected_status="ok",
        characteristic_id="iec60751_pt385",
        reference_resistance_ohms=99.5,
        minimum_temperature_c=-200.0,
        maximum_temperature_c=850.0,
        anchors=(
            FixtureAnchor(-200.0, ("minimum_boundary", "negative_temperature")),
            FixtureAnchor(-100.0, ("negative_temperature",)),
            FixtureAnchor(0.0, ("reference_temperature", "branch_boundary")),
            FixtureAnchor(100.0, ("positive_temperature",)),
            FixtureAnchor(850.0, ("maximum_boundary", "positive_temperature")),
        ),
    ),
    CharacteristicModelFixture(
        fixture_id="calibrated_pt385_nonnominal_r0",
        display_name="Calibrated PT-385 model with non-nominal R0",
        fixture_purpose=(
            "Verify composition of the published PT-385 characteristic with a "
            "characterized reference resistance and narrowed model range."
        ),
        expected_status="ok",
        characteristic_id="iec60751_pt385",
        reference_resistance_ohms=100.123,
        minimum_temperature_c=-50.0,
        maximum_temperature_c=200.0,
        anchors=(
            FixtureAnchor(-50.0, ("minimum_boundary", "negative_temperature")),
            FixtureAnchor(0.0, ("reference_temperature", "branch_boundary")),
            FixtureAnchor(100.0, ("positive_temperature",)),
            FixtureAnchor(200.0, ("maximum_boundary", "positive_temperature")),
        ),
    ),
    CharacteristicModelFixture(
        fixture_id="calibrated_pt385_r0_502p5",
        display_name="Characterized PT-385 model with R0 = 502.5 ohm",
        fixture_purpose=(
            "Verify characterized reference resistance near the Pt500 scale with "
            "a deliberately narrowed validity range."
        ),
        expected_status="ok",
        characteristic_id="iec60751_pt385",
        reference_resistance_ohms=502.5,
        minimum_temperature_c=-100.0,
        maximum_temperature_c=500.0,
        anchors=(
            FixtureAnchor(-100.0, ("minimum_boundary", "negative_temperature")),
            FixtureAnchor(-50.0, ("negative_temperature",)),
            FixtureAnchor(0.0, ("reference_temperature", "branch_boundary")),
            FixtureAnchor(100.0, ("positive_temperature",)),
            FixtureAnchor(500.0, ("maximum_boundary", "positive_temperature")),
        ),
    ),
    CharacteristicModelFixture(
        fixture_id="calibrated_pt385_r0_995",
        display_name="Characterized PT-385 model with R0 = 995 ohm",
        fixture_purpose=(
            "Verify characterized reference resistance near the Pt1000 scale across "
            "the full PT-385 characteristic range."
        ),
        expected_status="ok",
        characteristic_id="iec60751_pt385",
        reference_resistance_ohms=995.0,
        minimum_temperature_c=-200.0,
        maximum_temperature_c=850.0,
        anchors=(
            FixtureAnchor(-200.0, ("minimum_boundary", "negative_temperature")),
            FixtureAnchor(-100.0, ("negative_temperature",)),
            FixtureAnchor(0.0, ("reference_temperature", "branch_boundary")),
            FixtureAnchor(100.0, ("positive_temperature",)),
            FixtureAnchor(850.0, ("maximum_boundary", "positive_temperature")),
        ),
    ),
    CallendarVanDusenFixture(
        fixture_id="custom_cvd_two_sided",
        display_name="Two-sided custom Callendar-Van Dusen model",
        fixture_purpose=(
            "Verify custom A/B/C coefficients across both negative and positive "
            "temperature branches."
        ),
        expected_status="ok",
        reference_resistance_ohms=100.025,
        a=3.91e-3,
        b=-5.80e-7,
        c=-4.20e-12,
        minimum_temperature_c=-100.0,
        maximum_temperature_c=250.0,
        anchors=(
            FixtureAnchor(-100.0, ("minimum_boundary", "negative_temperature")),
            FixtureAnchor(-50.0, ("negative_temperature",)),
            FixtureAnchor(0.0, ("reference_temperature", "branch_boundary")),
            FixtureAnchor(100.0, ("positive_temperature",)),
            FixtureAnchor(250.0, ("maximum_boundary", "positive_temperature")),
        ),
    ),
    CallendarVanDusenFixture(
        fixture_id="custom_cvd_positive_ratio_crossing",
        display_name="Positive-only CVD model with off-zero R/R0 crossing",
        fixture_purpose=(
            "Verify a positive-only validity interval whose monotonic curve crosses "
            "R/R0 = 1 at 60 °C rather than at the excluded 0 °C reference point."
        ),
        expected_status="ok",
        reference_resistance_ohms=100.0,
        a=-6.0e-4,
        b=1.0e-5,
        c=None,
        minimum_temperature_c=50.0,
        maximum_temperature_c=100.0,
        anchors=(
            FixtureAnchor(50.0, ("minimum_boundary", "positive_temperature")),
            FixtureAnchor(60.0, ("ratio_crossing", "positive_temperature")),
            FixtureAnchor(75.0, ("representative", "positive_temperature")),
            FixtureAnchor(100.0, ("maximum_boundary", "positive_temperature")),
        ),
    ),
    CallendarVanDusenFixture(
        fixture_id="custom_cvd_negative_only",
        display_name="Negative-only custom CVD model",
        fixture_purpose=(
            "Verify that inversion remains bounded to a declared negative-only "
            "interval even when resistance exceeds R0 throughout part of that range."
        ),
        expected_status="ok",
        reference_resistance_ohms=100.0,
        a=-8.0e-4,
        b=-1.0e-5,
        c=0.0,
        minimum_temperature_c=-100.0,
        maximum_temperature_c=-50.0,
        anchors=(
            FixtureAnchor(-100.0, ("minimum_boundary", "negative_temperature")),
            FixtureAnchor(-80.0, ("ratio_crossing", "negative_temperature")),
            FixtureAnchor(-75.0, ("representative", "negative_temperature")),
            FixtureAnchor(-50.0, ("maximum_boundary", "negative_temperature")),
        ),
    ),
    PolynomialFixture(
        fixture_id="custom_polynomial_nonzero_reference",
        display_name="Polynomial model with a non-zero reference temperature",
        fixture_purpose=(
            "Verify normalized polynomial coefficients referenced to 25 °C rather "
            "than assuming a universal 0 °C reference."
        ),
        expected_status="ok",
        reference_resistance_ohms=1000.0,
        reference_temperature_c=25.0,
        coefficients=(4.0e-3, 1.0e-6),
        minimum_temperature_c=-20.0,
        maximum_temperature_c=120.0,
        anchors=(
            FixtureAnchor(-20.0, ("minimum_boundary", "negative_temperature")),
            FixtureAnchor(0.0, ("representative",)),
            FixtureAnchor(25.0, ("reference_temperature",)),
            FixtureAnchor(75.0, ("representative", "positive_temperature")),
            FixtureAnchor(120.0, ("maximum_boundary", "positive_temperature")),
        ),
    ),
    PiecewisePolynomialFixture(
        fixture_id="custom_piecewise_local_origins",
        display_name="Piecewise polynomial model with local segment origins",
        fixture_purpose=(
            "Verify full per-segment polynomials, local temperature origins, and "
            "deterministic routing at an interior join."
        ),
        expected_status="ok",
        reference_resistance_ohms=100.0,
        reference_temperature_c=0.0,
        segments=(
            PiecewiseSegmentFixture(
                minimum_temperature_c=-10.0,
                maximum_temperature_c=0.0,
                coefficients=(0.9, 0.01),
                temperature_origin_c=-10.0,
            ),
            PiecewiseSegmentFixture(
                minimum_temperature_c=0.0,
                maximum_temperature_c=10.0,
                coefficients=(1.0, 0.02),
                temperature_origin_c=0.0,
            ),
        ),
        anchors=(
            FixtureAnchor(-10.0, ("minimum_boundary", "negative_temperature")),
            FixtureAnchor(-5.0, ("piecewise_segment", "negative_temperature")),
            FixtureAnchor(0.0, ("reference_temperature", "piecewise_join")),
            FixtureAnchor(5.0, ("piecewise_segment", "positive_temperature")),
            FixtureAnchor(10.0, ("maximum_boundary", "positive_temperature")),
        ),
    ),
    PiecewisePolynomialFixture(
        fixture_id="custom_piecewise_stitched_join",
        display_name="Piecewise polynomial model with bounded join stitching",
        fixture_purpose=(
            "Verify that source coefficients remain unchanged while a small, "
            "explicitly authorized constant ratio offset restores continuity."
        ),
        expected_status="ok",
        reference_resistance_ohms=100.0,
        reference_temperature_c=0.0,
        segments=(
            PiecewiseSegmentFixture(
                minimum_temperature_c=0.0,
                maximum_temperature_c=10.0,
                coefficients=(1.0, 0.01),
            ),
            PiecewiseSegmentFixture(
                minimum_temperature_c=10.0,
                maximum_temperature_c=20.0,
                coefficients=(0.999999, 0.01),
            ),
        ),
        maximum_continuity_adjustment_ratio=2.0e-6,
        anchors=(
            FixtureAnchor(0.0, ("minimum_boundary", "reference_temperature")),
            FixtureAnchor(5.0, ("piecewise_segment", "positive_temperature")),
            FixtureAnchor(10.0, ("piecewise_join", "positive_temperature")),
            FixtureAnchor(15.0, ("piecewise_segment", "positive_temperature")),
            FixtureAnchor(20.0, ("maximum_boundary", "positive_temperature")),
        ),
    ),
    CharacteristicModelFixture(
        fixture_id="invalid_calibrated_r0_nonpositive",
        display_name="Invalid calibrated model with non-positive R0",
        fixture_purpose="Verify invalid_model for a non-positive reference resistance.",
        expected_status="invalid_model",
        characteristic_id="iec60751_pt385",
        reference_resistance_ohms=0.0,
        minimum_temperature_c=-50.0,
        maximum_temperature_c=200.0,
    ),
    CallendarVanDusenFixture(
        fixture_id="invalid_cvd_missing_c_negative_range",
        display_name="Invalid CVD model missing C for a negative range",
        fixture_purpose=(
            "Verify invalid_model when a negative-temperature CVD interval omits C."
        ),
        expected_status="invalid_model",
        reference_resistance_ohms=100.0,
        a=3.9083e-3,
        b=-5.775e-7,
        c=None,
        minimum_temperature_c=-50.0,
        maximum_temperature_c=100.0,
    ),
    CallendarVanDusenFixture(
        fixture_id="invalid_cvd_nonmonotonic",
        display_name="Invalid non-monotonic CVD model",
        fixture_purpose=(
            "Verify invalid_model when the declared coefficient set does not remain "
            "strictly increasing across its validity interval."
        ),
        expected_status="invalid_model",
        reference_resistance_ohms=100.0,
        a=1.0e-3,
        b=-1.0e-5,
        c=None,
        minimum_temperature_c=0.0,
        maximum_temperature_c=100.0,
    ),
    PolynomialFixture(
        fixture_id="invalid_polynomial_decreasing",
        display_name="Invalid decreasing polynomial model",
        fixture_purpose=(
            "Verify invalid_model for a polynomial characteristic with negative slope."
        ),
        expected_status="invalid_model",
        reference_resistance_ohms=100.0,
        reference_temperature_c=0.0,
        coefficients=(-0.01,),
        minimum_temperature_c=-10.0,
        maximum_temperature_c=10.0,
    ),
    PiecewisePolynomialFixture(
        fixture_id="invalid_piecewise_gap",
        display_name="Invalid piecewise model with a temperature gap",
        fixture_purpose=(
            "Verify invalid_model when adjacent source intervals are not contiguous."
        ),
        expected_status="invalid_model",
        reference_resistance_ohms=100.0,
        reference_temperature_c=0.0,
        segments=(
            PiecewiseSegmentFixture(-10.0, -1.0, (1.0, 0.01)),
            PiecewiseSegmentFixture(0.0, 10.0, (1.0, 0.01)),
        ),
    ),
    PiecewisePolynomialFixture(
        fixture_id="invalid_piecewise_unapproved_discontinuity",
        display_name="Invalid piecewise model with an unapproved discontinuity",
        fixture_purpose=(
            "Verify invalid_model when a source-level join requires more than the "
            "declared continuity adjustment allowance."
        ),
        expected_status="invalid_model",
        reference_resistance_ohms=100.0,
        reference_temperature_c=0.0,
        segments=(
            PiecewiseSegmentFixture(0.0, 10.0, (1.0, 0.01)),
            PiecewiseSegmentFixture(10.0, 20.0, (0.999, 0.01)),
        ),
        maximum_continuity_adjustment_ratio=1.0e-5,
    ),
)


CHARACTERIZED_R0_BINARY32_FIXTURE_IDS: tuple[str, ...] = (
    "calibrated_pt385_r0_99p5",
    "calibrated_pt385_nonnominal_r0",
    "calibrated_pt385_r0_502p5",
    "calibrated_pt385_r0_995",
)


def fixture_by_id(fixture_id: str) -> ModelFixture:
    """Return one conformance fixture by canonical local fixture ID."""
    for fixture in MODEL_FIXTURES:
        if fixture.fixture_id == fixture_id:
            return fixture
    raise KeyError(fixture_id)


def build_fixture_model(fixture: ModelFixture) -> ConfigurableFixtureModel:
    """Construct the Python reference model for one fixture definition."""
    if isinstance(fixture, CharacteristicModelFixture):
        if fixture.characteristic_id != "iec60751_pt385":
            raise ValueError(
                "Unsupported characteristic-model fixture characteristic: "
                f"{fixture.characteristic_id!r}"
            )
        return IEC60751RTDModel(
            r0_ohms=fixture.reference_resistance_ohms,
            name=fixture.display_name,
            minimum_temperature_c=fixture.minimum_temperature_c,
            maximum_temperature_c=fixture.maximum_temperature_c,
        )

    if isinstance(fixture, CallendarVanDusenFixture):
        return CallendarVanDusenRTDModel(
            r0_ohms=fixture.reference_resistance_ohms,
            a=fixture.a,
            b=fixture.b,
            c=fixture.c,
            minimum_temperature_c=fixture.minimum_temperature_c,
            maximum_temperature_c=fixture.maximum_temperature_c,
            name=fixture.display_name,
            coefficient_source="Synthetic conformance fixture",
        )

    if isinstance(fixture, PolynomialFixture):
        return PolynomialRTDModel(
            reference_resistance_ohms=fixture.reference_resistance_ohms,
            reference_temperature_c=fixture.reference_temperature_c,
            coefficients=fixture.coefficients,
            minimum_temperature_c=fixture.minimum_temperature_c,
            maximum_temperature_c=fixture.maximum_temperature_c,
            name=fixture.display_name,
            coefficient_source="Synthetic conformance fixture",
        )

    if isinstance(fixture, PiecewisePolynomialFixture):
        return PiecewisePolynomialRTDModel(
            reference_resistance_ohms=fixture.reference_resistance_ohms,
            reference_temperature_c=fixture.reference_temperature_c,
            segments=tuple(
                PiecewisePolynomialSegment(
                    minimum_temperature_c=segment.minimum_temperature_c,
                    maximum_temperature_c=segment.maximum_temperature_c,
                    coefficients=segment.coefficients,
                    temperature_origin_c=segment.temperature_origin_c,
                )
                for segment in fixture.segments
            ),
            maximum_continuity_adjustment_ratio=(
                fixture.maximum_continuity_adjustment_ratio
            ),
            name=fixture.display_name,
            coefficient_source="Synthetic conformance fixture",
        )

    raise TypeError(f"Unsupported conformance model fixture: {type(fixture)!r}")
