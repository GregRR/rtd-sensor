# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from rtd_sensor import _definitions, catalog
from rtd_sensor.models import RTDModel

_EXPECTED_MODEL_IDS = (
    "pt100",
    "pt500",
    "pt1000",
    "ni1000",
    "ni1000_tk5000",
    "ni120",
)


def _catalog_model_is_an_rtd_model(model_id: str) -> RTDModel:
    """Static regression: catalog lookups satisfy the public model protocol."""
    return catalog.get_model(model_id)


def test_supported_models_returns_canonical_definition_order() -> None:
    assert catalog.supported_models() == _EXPECTED_MODEL_IDS
    assert catalog.supported_models() == tuple(_definitions.BUILTIN_MODEL_DEFINITIONS)


@pytest.mark.parametrize(
    ("model_id", "reference_resistance_ohms"),
    [
        ("pt100", 100.0),
        ("pt500", 500.0),
        ("pt1000", 1000.0),
        ("ni1000", 1000.0),
        ("ni1000_tk5000", 1000.0),
        ("ni120", 120.0),
    ],
)
def test_get_model_returns_public_rtd_behavior(
    model_id: str,
    reference_resistance_ohms: float,
) -> None:
    model = _catalog_model_is_an_rtd_model(model_id)

    assert model.celsius_to_resistance(0.0) == pytest.approx(reference_resistance_ohms)
    assert model.resistance_to_celsius(reference_resistance_ohms) == pytest.approx(
        0.0, abs=1e-12
    )
    assert model.resistance_sensitivity_ohms_per_celsius(0.0) > 0.0
    assert model.temperature_sensitivity_celsius_per_ohm(0.0) > 0.0


def test_model_info_is_derived_from_authoritative_definitions() -> None:
    for model_id, definition in _definitions.BUILTIN_MODEL_DEFINITIONS.items():
        characteristic = _definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS[
            definition.characteristic_id
        ]
        info = catalog.model_info(model_id)

        assert info.model_id == definition.model_id
        assert info.display_name == definition.display_name
        assert info.characteristic_id == definition.characteristic_id
        assert info.characteristic_display_name == characteristic.display_name
        assert info.material == characteristic.material
        assert info.curve_kind == characteristic.curve_kind
        assert info.reference_resistance_ohms == (definition.reference_resistance_ohms)
        assert info.reference_temperature_c == characteristic.reference_temperature_c
        assert info.minimum_temperature_c == characteristic.minimum_temperature_c
        assert info.maximum_temperature_c == characteristic.maximum_temperature_c
        assert info.source_references == tuple(
            catalog.RTDSourceReference(
                citation=reference.citation,
                url=reference.url,
            )
            for reference in characteristic.source_references
        )


def test_shared_characteristic_identity_remains_distinct_from_model_identity() -> None:
    pt100 = catalog.model_info("pt100")
    pt500 = catalog.model_info("pt500")
    pt1000 = catalog.model_info("pt1000")

    assert {
        pt100.model_id,
        pt500.model_id,
        pt1000.model_id,
    } == {"pt100", "pt500", "pt1000"}
    assert {
        pt100.characteristic_id,
        pt500.characteristic_id,
        pt1000.characteristic_id,
    } == {"iec60751_pt385"}
    assert {
        pt100.reference_resistance_ohms,
        pt500.reference_resistance_ohms,
        pt1000.reference_resistance_ohms,
    } == {100.0, 500.0, 1000.0}


def test_model_info_and_source_references_are_immutable() -> None:
    info = catalog.model_info("pt100")
    reference = info.source_references[0]

    with pytest.raises(FrozenInstanceError):
        info.display_name = "Replacement"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        reference.citation = "Replacement"  # type: ignore[misc]


def test_catalog_returns_stable_package_owned_objects() -> None:
    model = catalog.get_model("pt100")

    assert model is catalog.get_model("pt100")
    assert catalog.model_info("pt100") is catalog.model_info("pt100")
    private_attribute = "_model"
    with pytest.raises(FrozenInstanceError):
        setattr(model, private_attribute, object())


def test_catalog_model_does_not_expose_private_runtime_model_surface() -> None:
    model = catalog.get_model("pt100")

    assert type(model).__module__ == "rtd_sensor.catalog"
    assert "rtd_sensor._models" not in repr(model)
    for attribute in (
        "curve",
        "identity",
        "r0_ohms",
        "reference_resistance_ohms",
        "minimum_temperature_c",
        "maximum_temperature_c",
    ):
        assert not hasattr(model, attribute)


def test_catalog_model_behavior_matches_discovery_metadata() -> None:
    for model_id in catalog.supported_models():
        model = catalog.get_model(model_id)
        info = catalog.model_info(model_id)

        assert model.celsius_to_resistance(
            info.reference_temperature_c
        ) == pytest.approx(info.reference_resistance_ohms)
        assert model.resistance_to_celsius(
            info.reference_resistance_ohms
        ) == pytest.approx(info.reference_temperature_c, abs=1e-12)


def test_public_metadata_dataclasses_require_keyword_arguments() -> None:
    with pytest.raises(TypeError):
        catalog.RTDSourceReference("source")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        catalog.BuiltinRTDModelInfo("pt100")  # type: ignore[call-arg]


@pytest.mark.parametrize("model_id", ["", "PT100", "pt100 ", "unknown"])
def test_unknown_model_id_raises_key_error(model_id: str) -> None:
    with pytest.raises(KeyError, match="Unknown built-in RTD model ID"):
        catalog.get_model(model_id)
    with pytest.raises(KeyError, match="Unknown built-in RTD model ID"):
        catalog.model_info(model_id)


@pytest.mark.parametrize("model_id", [None, 100, True, object()])
def test_non_string_model_id_raises_type_error(model_id: object) -> None:
    with pytest.raises(TypeError, match="RTD model ID must be a string"):
        catalog.get_model(model_id)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="RTD model ID must be a string"):
        catalog.model_info(model_id)  # type: ignore[arg-type]
