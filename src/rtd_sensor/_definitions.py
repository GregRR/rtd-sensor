# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Authoritative built-in RTD characteristic and model definitions.

This module contains immutable source data for the verified built-in RTD
characteristics and models. Runtime curve/model objects are constructed from
these definitions so conversion behavior, conformance artifacts, and public
discovery metadata do not maintain independent copies of scientific parameters.

The definitions deliberately preserve source coefficients separately from
runtime-derived values such as piecewise continuity adjustments.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

type Material = Literal["platinum", "nickel"]


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Traceable source metadata for one built-in characteristic definition."""

    citation: str
    url: str | None = None

    def __post_init__(self) -> None:
        _validate_nonempty_trimmed(self.citation, name="Source citation")
        if self.url is not None:
            _validate_nonempty_trimmed(self.url, name="Source URL")


@dataclass(frozen=True, slots=True)
class CallendarVanDusenCharacteristicDefinition:
    """Immutable source definition for a Callendar-Van Dusen characteristic."""

    characteristic_id: str
    display_name: str
    material: Material
    a: float
    b: float
    c: float
    minimum_temperature_c: float
    maximum_temperature_c: float
    source_references: tuple[SourceReference, ...]
    curve_kind: Literal["callendar_van_dusen"] = field(
        init=False,
        default="callendar_van_dusen",
    )
    reference_temperature_c: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_references", tuple(self.source_references))
        _validate_characteristic_identity(self)


@dataclass(frozen=True, slots=True)
class PolynomialCharacteristicDefinition:
    """Immutable source definition for a normalized polynomial characteristic."""

    characteristic_id: str
    display_name: str
    material: Material
    coefficients: tuple[float, ...]
    reference_temperature_c: float
    minimum_temperature_c: float
    maximum_temperature_c: float
    source_references: tuple[SourceReference, ...]
    curve_kind: Literal["polynomial"] = field(init=False, default="polynomial")

    def __post_init__(self) -> None:
        object.__setattr__(self, "coefficients", tuple(self.coefficients))
        object.__setattr__(self, "source_references", tuple(self.source_references))
        _validate_characteristic_identity(self)


@dataclass(frozen=True, slots=True)
class PolynomialSegmentDefinition:
    """Immutable source coefficients for one piecewise-polynomial interval."""

    minimum_temperature_c: float
    maximum_temperature_c: float
    coefficients: tuple[float, ...]
    temperature_origin_c: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "coefficients", tuple(self.coefficients))


@dataclass(frozen=True, slots=True)
class PiecewisePolynomialCharacteristicDefinition:
    """Immutable source definition for a piecewise-polynomial characteristic."""

    characteristic_id: str
    display_name: str
    material: Material
    segments: tuple[PolynomialSegmentDefinition, ...]
    reference_temperature_c: float
    maximum_continuity_adjustment_ratio: float
    continuity_adjustment_reason: str
    source_references: tuple[SourceReference, ...]
    curve_kind: Literal["piecewise_polynomial"] = field(
        init=False,
        default="piecewise_polynomial",
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "segments", tuple(self.segments))
        object.__setattr__(self, "source_references", tuple(self.source_references))
        _validate_characteristic_identity(self)
        _validate_nonempty_trimmed(
            self.continuity_adjustment_reason,
            name="Continuity-adjustment reason",
        )

    @property
    def minimum_temperature_c(self) -> float:
        """Return the first source segment's lower temperature bound."""
        return self.segments[0].minimum_temperature_c

    @property
    def maximum_temperature_c(self) -> float:
        """Return the final source segment's upper temperature bound."""
        return self.segments[-1].maximum_temperature_c


type CharacteristicDefinition = (
    CallendarVanDusenCharacteristicDefinition
    | PolynomialCharacteristicDefinition
    | PiecewisePolynomialCharacteristicDefinition
)


@dataclass(frozen=True, slots=True)
class BuiltinRTDModelDefinition:
    """Immutable identity and scaling metadata for one verified built-in model."""

    model_id: str
    display_name: str
    characteristic_id: str
    reference_resistance_ohms: float

    def __post_init__(self) -> None:
        _validate_nonempty_trimmed(self.model_id, name="Model ID")
        _validate_nonempty_trimmed(self.display_name, name="Model display name")
        _validate_nonempty_trimmed(
            self.characteristic_id,
            name="Characteristic ID",
        )


def _validate_characteristic_identity(
    definition: CharacteristicDefinition,
) -> None:
    _validate_nonempty_trimmed(
        definition.characteristic_id,
        name="Characteristic ID",
    )
    _validate_nonempty_trimmed(definition.display_name, name="Characteristic name")
    if not definition.source_references:
        raise ValueError(
            "Built-in characteristics require at least one source reference"
        )


def _validate_nonempty_trimmed(value: str, *, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty, trimmed string")


_IEC_60751 = SourceReference(
    citation=(
        "IEC 60751:2022, Industrial platinum resistance thermometers and "
        "platinum temperature sensors"
    ),
    url="https://webstore.iec.ch/en/publication/63753",
)

_IST_NICKEL_ND = SourceReference(
    citation=(
        "Innovative Sensor Technology (IST AG), RTD Nickel Sensors application "
        "note, Nickel ND (6180 ppm/K) coefficient table"
    ),
    url="https://www.ist-ag.com/sites/default/files/downloads/ATN_E.pdf",
)

_ABB_DIN_NICKEL = SourceReference(
    citation=(
        "ABB, Industrial temperature measurement: Basics and practice, nickel "
        "measurement characteristics according to DIN 43760"
    )
)

_IST_NICKEL_NL = SourceReference(
    citation=(
        "Innovative Sensor Technology (IST AG), RTD Nickel Sensors application "
        "note, Nickel NL (5000 ppm/K) coefficient table"
    ),
    url="https://www.ist-ag.com/sites/default/files/downloads/ATN_E.pdf",
)

_MINCO_NA = SourceReference(
    citation=(
        "Minco, Resistance Thermometry: Principles and Applications of "
        "Resistance Thermometers and Thermistors, Nickel section, page 6"
    ),
    url="https://www.minco.com/wp-content/uploads/Resistance-Thermometry.pdf",
)


# IEC 60751 defines the PT-385 Callendar-Van Dusen coefficients used by the
# built-in Pt100, Pt500, and Pt1000 models. Independent resistance-table tests
# remain separate from this coefficient source so generated conformance data
# cannot substitute for scientific validation.
IEC_60751_PT385_DEFINITION = CallendarVanDusenCharacteristicDefinition(
    characteristic_id="iec60751_pt385",
    display_name="IEC 60751 PT-385 curve",
    material="platinum",
    a=3.9083e-3,
    b=-5.775e-7,
    c=-4.183e-12,
    minimum_temperature_c=-200.0,
    maximum_temperature_c=850.0,
    source_references=(_IEC_60751,),
)


# Former DIN 43760 nickel characteristic (6178/6180 ppm/K). Missing odd-power
# terms are retained explicitly as zeros so the tuple maps directly to c1..c6
# in PolynomialRTDCurve rather than hiding the published polynomial structure.
NI_6180_DIN_43760_DEFINITION = PolynomialCharacteristicDefinition(
    characteristic_id="ni6180_din43760",
    display_name="Former DIN 43760 nickel 6180 ppm/K curve",
    material="nickel",
    coefficients=(
        5.485e-3,
        6.650e-6,
        0.0,
        2.805e-11,
        0.0,
        -2.000e-17,
    ),
    reference_temperature_c=0.0,
    minimum_temperature_c=-60.0,
    maximum_temperature_c=250.0,
    source_references=(_ABB_DIN_NICKEL, _IST_NICKEL_ND),
)


# IST AG publishes the distinct Nickel NL / TK5000 cubic characteristic. The
# E+E Elektronik resistance table remains an independent validation source in
# the test suite rather than becoming another source of runtime coefficients.
NI_5000_TK5000_DEFINITION = PolynomialCharacteristicDefinition(
    characteristic_id="ni5000_tk5000",
    display_name="Ni1000 TK5000 nickel 5000 ppm/K curve",
    material="nickel",
    coefficients=(
        4.427e-3,
        5.172e-6,
        5.585e-9,
    ),
    reference_temperature_c=0.0,
    minimum_temperature_c=-60.0,
    maximum_temperature_c=250.0,
    source_references=(_IST_NICKEL_NL,),
)


# Minco publishes the North American 6720 ppm/K characteristic as twelve cubic
# source intervals. The coefficients below are source data and must not include
# runtime continuity offsets. Their printed precision leaves small join
# mismatches; the largest required normalized constant offset is about 7.2e-6
# (about 0.000864 ohm for a 120-ohm model), so 1e-5 is the explicitly authorized
# upper bound while preserving each source segment's slope and higher terms.
NI_6720_NORTH_AMERICAN_DEFINITION = PiecewisePolynomialCharacteristicDefinition(
    characteristic_id="ni6720_north_american",
    display_name="North American nickel 120 ohm 6720 ppm/K curve",
    material="nickel",
    segments=(
        PolynomialSegmentDefinition(
            minimum_temperature_c=-80.0,
            maximum_temperature_c=-60.0,
            coefficients=(
                9.980384367e-1,
                5.779005438e-3,
                4.519218356e-6,
                1.883007648e-8,
            ),
        ),
        PolynomialSegmentDefinition(
            minimum_temperature_c=-60.0,
            maximum_temperature_c=-30.0,
            coefficients=(
                9.995545058e-1,
                5.854808892e-3,
                5.782609262e-6,
                2.584891485e-8,
            ),
        ),
        PolynomialSegmentDefinition(
            minimum_temperature_c=-30.0,
            maximum_temperature_c=0.0,
            coefficients=(
                1.0,
                5.899358312e-3,
                7.267589932e-6,
                4.234870007e-8,
            ),
        ),
        PolynomialSegmentDefinition(
            minimum_temperature_c=0.0,
            maximum_temperature_c=30.0,
            coefficients=(
                1.0,
                5.899358312e-3,
                7.267589932e-6,
                1.154640832e-8,
            ),
        ),
        PolynomialSegmentDefinition(
            minimum_temperature_c=30.0,
            maximum_temperature_c=60.0,
            coefficients=(
                1.000118847,
                5.887473643e-3,
                7.663745572e-6,
                7.144678985e-9,
            ),
        ),
        PolynomialSegmentDefinition(
            minimum_temperature_c=60.0,
            maximum_temperature_c=90.0,
            coefficients=(
                1.002329124,
                5.776959768e-3,
                9.505643490e-6,
                -3.088087226e-9,
            ),
        ),
        PolynomialSegmentDefinition(
            minimum_temperature_c=90.0,
            maximum_temperature_c=120.0,
            coefficients=(
                9.940315172e-1,
                6.053466667e-3,
                6.432455728e-6,
                8.294089672e-9,
            ),
        ),
        PolynomialSegmentDefinition(
            minimum_temperature_c=120.0,
            maximum_temperature_c=150.0,
            coefficients=(
                1.007022904,
                5.728761999e-3,
                9.138994624e-6,
                7.759260700e-10,
            ),
        ),
        PolynomialSegmentDefinition(
            minimum_temperature_c=150.0,
            maximum_temperature_c=180.0,
            coefficients=(
                8.918592090e-1,
                8.032035898e-3,
                -6.216164699e-6,
                3.489850234e-8,
            ),
        ),
        PolynomialSegmentDefinition(
            minimum_temperature_c=180.0,
            maximum_temperature_c=210.0,
            coefficients=(
                9.060247382e-1,
                7.795943744e-3,
                -4.904541625e-6,
                3.246957072e-8,
            ),
        ),
        PolynomialSegmentDefinition(
            minimum_temperature_c=210.0,
            maximum_temperature_c=240.0,
            coefficients=(
                1.103473241,
                4.975250849e-3,
                8.527329303e-6,
                1.114941068e-8,
            ),
        ),
        PolynomialSegmentDefinition(
            minimum_temperature_c=240.0,
            maximum_temperature_c=260.0,
            coefficients=(
                1.437355995,
                8.017164189e-4,
                2.591705610e-5,
                -1.300325764e-8,
            ),
        ),
    ),
    reference_temperature_c=0.0,
    maximum_continuity_adjustment_ratio=1.0e-5,
    continuity_adjustment_reason=(
        "Minco publishes independently rounded cubic source segments. The bounded "
        "constant offsets reconcile printed join mismatches without changing source "
        "coefficients or segment slopes."
    ),
    source_references=(_MINCO_NA,),
)


_CHARACTERISTIC_DEFINITIONS = (
    IEC_60751_PT385_DEFINITION,
    NI_6180_DIN_43760_DEFINITION,
    NI_5000_TK5000_DEFINITION,
    NI_6720_NORTH_AMERICAN_DEFINITION,
)

BUILTIN_CHARACTERISTIC_DEFINITIONS: Mapping[str, CharacteristicDefinition] = (
    MappingProxyType(
        {
            definition.characteristic_id: definition
            for definition in _CHARACTERISTIC_DEFINITIONS
        }
    )
)

if len(BUILTIN_CHARACTERISTIC_DEFINITIONS) != len(_CHARACTERISTIC_DEFINITIONS):
    raise RuntimeError("Duplicate built-in RTD characteristic ID")


# Order is part of catalog.supported_models() public behavior; append new built-ins.
_MODEL_DEFINITIONS = (
    BuiltinRTDModelDefinition(
        model_id="pt100",
        display_name="Pt100",
        characteristic_id="iec60751_pt385",
        reference_resistance_ohms=100.0,
    ),
    BuiltinRTDModelDefinition(
        model_id="pt500",
        display_name="Pt500",
        characteristic_id="iec60751_pt385",
        reference_resistance_ohms=500.0,
    ),
    BuiltinRTDModelDefinition(
        model_id="pt1000",
        display_name="Pt1000",
        characteristic_id="iec60751_pt385",
        reference_resistance_ohms=1000.0,
    ),
    BuiltinRTDModelDefinition(
        model_id="ni1000",
        display_name="Ni1000 6180",
        characteristic_id="ni6180_din43760",
        reference_resistance_ohms=1000.0,
    ),
    BuiltinRTDModelDefinition(
        model_id="ni1000_tk5000",
        display_name="Ni1000 TK5000",
        characteristic_id="ni5000_tk5000",
        reference_resistance_ohms=1000.0,
    ),
    BuiltinRTDModelDefinition(
        model_id="ni120",
        display_name="Ni120 North American 6720",
        characteristic_id="ni6720_north_american",
        reference_resistance_ohms=120.0,
    ),
)

BUILTIN_MODEL_DEFINITIONS: Mapping[str, BuiltinRTDModelDefinition] = MappingProxyType(
    {definition.model_id: definition for definition in _MODEL_DEFINITIONS}
)

if len(BUILTIN_MODEL_DEFINITIONS) != len(_MODEL_DEFINITIONS):
    raise RuntimeError("Duplicate built-in RTD model ID")

for _model_definition in BUILTIN_MODEL_DEFINITIONS.values():
    if _model_definition.characteristic_id not in BUILTIN_CHARACTERISTIC_DEFINITIONS:
        raise RuntimeError(
            "Built-in RTD model references unknown characteristic: "
            f"{_model_definition.model_id!r} -> "
            f"{_model_definition.characteristic_id!r}"
        )
