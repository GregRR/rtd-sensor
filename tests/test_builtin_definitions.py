# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

import rtd_sensor._curves as _curves
from rtd_sensor import _definitions
from rtd_sensor._curves import (
    BUILTIN_RTD_CURVES,
    PiecewisePolynomialRTDCurve,
    PolynomialRTDCurve,
)
from rtd_sensor._models import BUILTIN_RTD_MODELS, RTDModel

_EXPECTED_CHARACTERISTIC_IDS = {
    "iec60751_pt385",
    "ni6180_din43760",
    "ni5000_tk5000",
    "ni6720_north_american",
}

_EXPECTED_MODEL_IDS = {
    "pt100",
    "pt500",
    "pt1000",
    "ni1000",
    "ni1000_tk5000",
    "ni120",
}


def test_authoritative_characteristic_ids_match_runtime_registry() -> None:
    assert set(_definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS) == (
        _EXPECTED_CHARACTERISTIC_IDS
    )
    assert set(BUILTIN_RTD_CURVES) == _EXPECTED_CHARACTERISTIC_IDS


def test_authoritative_model_ids_match_runtime_registry() -> None:
    assert set(_definitions.BUILTIN_MODEL_DEFINITIONS) == _EXPECTED_MODEL_IDS
    assert set(BUILTIN_RTD_MODELS) == _EXPECTED_MODEL_IDS


def test_every_model_definition_references_registered_characteristic() -> None:
    for definition in _definitions.BUILTIN_MODEL_DEFINITIONS.values():
        assert definition.characteristic_id in (
            _definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS
        )
        assert (
            BUILTIN_RTD_MODELS[definition.model_id].curve
            is BUILTIN_RTD_CURVES[definition.characteristic_id]
        )


@pytest.mark.parametrize(
    ("model_id", "expected_characteristic_id", "expected_rref"),
    [
        ("pt100", "iec60751_pt385", 100.0),
        ("pt500", "iec60751_pt385", 500.0),
        ("pt1000", "iec60751_pt385", 1000.0),
        ("ni1000", "ni6180_din43760", 1000.0),
        ("ni1000_tk5000", "ni5000_tk5000", 1000.0),
        ("ni120", "ni6720_north_american", 120.0),
    ],
)
def test_runtime_models_are_constructed_from_authoritative_definitions(
    model_id: str,
    expected_characteristic_id: str,
    expected_rref: float,
) -> None:
    definition = _definitions.BUILTIN_MODEL_DEFINITIONS[model_id]
    model = BUILTIN_RTD_MODELS[model_id]

    assert definition.characteristic_id == expected_characteristic_id
    assert definition.reference_resistance_ohms == expected_rref
    assert model.identity == definition.model_id
    assert model.name == definition.display_name
    assert model.reference_resistance_ohms == definition.reference_resistance_ohms
    assert model.curve is BUILTIN_RTD_CURVES[definition.characteristic_id]


def test_polynomial_runtime_curve_preserves_source_coefficients() -> None:
    definition = _definitions.NI_6180_DIN_43760_DEFINITION
    curve = BUILTIN_RTD_CURVES[definition.characteristic_id]

    assert isinstance(curve, PolynomialRTDCurve)
    assert curve.coefficients == definition.coefficients
    assert curve.reference_temperature_c == definition.reference_temperature_c
    assert curve.minimum_temperature_c == definition.minimum_temperature_c
    assert curve.maximum_temperature_c == definition.maximum_temperature_c


def test_piecewise_runtime_curve_preserves_source_segments() -> None:
    definition = _definitions.NI_6720_NORTH_AMERICAN_DEFINITION
    curve = BUILTIN_RTD_CURVES[definition.characteristic_id]

    assert isinstance(curve, PiecewisePolynomialRTDCurve)
    assert len(curve.segments) == len(definition.segments)

    for source_segment, runtime_segment in zip(
        definition.segments,
        curve.segments,
        strict=True,
    ):
        assert runtime_segment.minimum_temperature_c == (
            source_segment.minimum_temperature_c
        )
        assert runtime_segment.maximum_temperature_c == (
            source_segment.maximum_temperature_c
        )
        assert runtime_segment.coefficients == source_segment.coefficients
        assert runtime_segment.temperature_origin_c == (
            source_segment.temperature_origin_c
        )


def test_piecewise_continuity_adjustments_remain_derived_runtime_metadata() -> None:
    definition = _definitions.NI_6720_NORTH_AMERICAN_DEFINITION
    curve = BUILTIN_RTD_CURVES[definition.characteristic_id]

    assert isinstance(curve, PiecewisePolynomialRTDCurve)
    assert definition.maximum_continuity_adjustment_ratio == 1.0e-5
    assert max(map(abs, curve.continuity_adjustments)) > 0.0
    assert max(map(abs, curve.continuity_adjustments)) <= (
        definition.maximum_continuity_adjustment_ratio
    )


def test_characteristics_retain_traceable_source_metadata() -> None:
    for definition in _definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS.values():
        assert definition.source_references
        assert all(reference.citation for reference in definition.source_references)


def test_definition_sequence_inputs_are_snapshotted_as_immutable_tuples() -> None:
    source = _definitions.SourceReference(citation="Test source")
    coefficient_input = [1.0, 2.0]
    source_input = [source]
    segment = _definitions.PolynomialSegmentDefinition(
        minimum_temperature_c=0.0,
        maximum_temperature_c=10.0,
        coefficients=cast(tuple[float, ...], coefficient_input),
    )
    segment_input = [segment]

    polynomial = _definitions.PolynomialCharacteristicDefinition(
        characteristic_id="test_polynomial",
        display_name="Test polynomial",
        material="nickel",
        coefficients=cast(tuple[float, ...], coefficient_input),
        reference_temperature_c=0.0,
        minimum_temperature_c=0.0,
        maximum_temperature_c=10.0,
        source_references=cast(
            tuple[_definitions.SourceReference, ...],
            source_input,
        ),
    )
    piecewise = _definitions.PiecewisePolynomialCharacteristicDefinition(
        characteristic_id="test_piecewise",
        display_name="Test piecewise",
        material="nickel",
        segments=cast(
            tuple[_definitions.PolynomialSegmentDefinition, ...],
            segment_input,
        ),
        reference_temperature_c=0.0,
        maximum_continuity_adjustment_ratio=1.0e-5,
        continuity_adjustment_reason="Test continuity policy",
        source_references=cast(
            tuple[_definitions.SourceReference, ...],
            source_input,
        ),
    )
    cvd = _definitions.CallendarVanDusenCharacteristicDefinition(
        characteristic_id="test_cvd",
        display_name="Test CVD",
        material="platinum",
        a=3.9083e-3,
        b=-5.775e-7,
        c=-4.183e-12,
        minimum_temperature_c=-200.0,
        maximum_temperature_c=850.0,
        source_references=cast(
            tuple[_definitions.SourceReference, ...],
            source_input,
        ),
    )

    coefficient_input.append(999.0)
    source_input.clear()
    segment_input.clear()

    assert segment.coefficients == (1.0, 2.0)
    assert polynomial.coefficients == (1.0, 2.0)
    assert polynomial.source_references == (source,)
    assert piecewise.segments == (segment,)
    assert piecewise.source_references == (source,)
    assert cvd.source_references == (source,)


def test_unsupported_characteristic_definition_fails_at_dispatch() -> None:
    unsupported = cast(_definitions.CharacteristicDefinition, object())

    with pytest.raises(
        TypeError,
        match="Unsupported built-in characteristic definition",
    ):
        _curves._curve_from_definition(unsupported)


def test_builtin_curve_export_type_check_rejects_registry_type_mismatch() -> None:
    with pytest.raises(
        TypeError,
        match="constructed with unexpected curve type",
    ):
        _curves._require_builtin_curve_type("iec60751_pt385", PolynomialRTDCurve)


def test_definition_registries_are_immutable() -> None:
    mutable_characteristics = cast(
        dict[str, _definitions.CharacteristicDefinition],
        _definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS,
    )
    mutable_models = cast(
        dict[str, _definitions.BuiltinRTDModelDefinition],
        _definitions.BUILTIN_MODEL_DEFINITIONS,
    )

    with pytest.raises(TypeError):
        mutable_characteristics["replacement"] = _definitions.IEC_60751_PT385_DEFINITION
    with pytest.raises(TypeError):
        mutable_models["replacement"] = _definitions.BUILTIN_MODEL_DEFINITIONS["pt100"]


def test_definitions_are_frozen() -> None:
    model_definition = _definitions.BUILTIN_MODEL_DEFINITIONS["pt100"]

    with pytest.raises(FrozenInstanceError):
        model_definition.reference_resistance_ohms = 101.0  # type: ignore[misc]


def test_runtime_registries_are_immutable_views_of_derived_objects() -> None:
    mutable_curves = cast(dict[str, object], BUILTIN_RTD_CURVES)
    mutable_models = cast(dict[str, RTDModel], BUILTIN_RTD_MODELS)

    with pytest.raises(TypeError):
        mutable_curves["replacement"] = BUILTIN_RTD_CURVES["iec60751_pt385"]
    with pytest.raises(TypeError):
        mutable_models["replacement"] = BUILTIN_RTD_MODELS["pt100"]
