# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from rtd_sensor import _conformance_artifacts, _curves, _definitions, _models

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONFORMANCE_DIR = _REPO_ROOT / "conformance" / "v1"
_SCHEMA_DIR = _CONFORMANCE_DIR / "schemas"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    assert isinstance(document, dict)
    return document


def _characteristics() -> list[dict[str, Any]]:
    document = _load_json(_CONFORMANCE_DIR / "characteristics.json")
    characteristics = document["characteristics"]
    assert isinstance(characteristics, list)
    return characteristics


def _models_catalog() -> list[dict[str, Any]]:
    document = _load_json(_CONFORMANCE_DIR / "models.json")
    models = document["models"]
    assert isinstance(models, list)
    return models


@pytest.mark.parametrize(
    ("filename", "schema_filename"),
    [
        ("characteristics.json", "characteristic-catalog.schema.json"),
        ("models.json", "model-catalog.schema.json"),
    ],
)
def test_generated_catalog_validates_against_schema(
    filename: str,
    schema_filename: str,
) -> None:
    schema = _load_json(_SCHEMA_DIR / schema_filename)
    Draft202012Validator(schema).validate(_load_json(_CONFORMANCE_DIR / filename))


def test_committed_catalogs_match_deterministic_generator() -> None:
    assert _conformance_artifacts.stale_generated_artifacts(_CONFORMANCE_DIR) == ()

    for filename, expected in _conformance_artifacts.generated_artifacts().items():
        assert (_CONFORMANCE_DIR / filename).read_text(encoding="utf-8") == expected
        assert expected.endswith("\n")


def test_generated_catalogs_record_current_project_version() -> None:
    expected_version = _conformance_artifacts._project_version()

    assert (
        _load_json(_CONFORMANCE_DIR / "characteristics.json")["rtd_sensor_version"]
        == expected_version
    )
    assert (
        _load_json(_CONFORMANCE_DIR / "models.json")["rtd_sensor_version"]
        == expected_version
    )


def test_characteristic_catalog_preserves_authoritative_definition_order() -> None:
    expected_ids = list(_definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS)
    actual_ids = [item["characteristic_id"] for item in _characteristics()]

    assert actual_ids == expected_ids


def test_model_catalog_preserves_authoritative_definition_order() -> None:
    expected_ids = list(_definitions.BUILTIN_MODEL_DEFINITIONS)
    actual_ids = [item["model_id"] for item in _models_catalog()]

    assert actual_ids == expected_ids


def test_model_catalog_references_known_characteristics_and_runtime_ranges() -> None:
    known_characteristics = set(_definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS)

    for model_document in _models_catalog():
        model_id = model_document["model_id"]
        characteristic_id = model_document["characteristic_id"]
        assert isinstance(model_id, str)
        assert isinstance(characteristic_id, str)
        assert characteristic_id in known_characteristics

        runtime_model = _models.BUILTIN_RTD_MODELS[model_id]
        assert (
            model_document["reference_resistance_ohms"]
            == runtime_model.reference_resistance_ohms
        )
        assert (
            model_document["minimum_temperature_c"]
            == runtime_model.minimum_temperature_c
        )
        assert (
            model_document["maximum_temperature_c"]
            == runtime_model.maximum_temperature_c
        )


def test_piecewise_catalog_separates_source_coefficients_from_derived_offsets() -> None:
    definition = _definitions.NI_6720_NORTH_AMERICAN_DEFINITION
    runtime_curve = _curves.NI_6720_NORTH_AMERICAN
    document = next(
        item
        for item in _characteristics()
        if item["characteristic_id"] == definition.characteristic_id
    )

    source_coefficients = [
        list(segment.coefficients) for segment in definition.segments
    ]
    serialized_segments = document["segments"]
    assert isinstance(serialized_segments, list)
    serialized_coefficients = [
        segment["coefficients"] for segment in serialized_segments
    ]

    assert serialized_coefficients == source_coefficients
    assert document["derived_continuity_adjustments"] == [
        0.0 if adjustment == 0.0 else adjustment
        for adjustment in runtime_curve.continuity_adjustments
    ]
    assert any(adjustment != 0.0 for adjustment in runtime_curve.continuity_adjustments)


def test_generator_writes_deterministic_catalogs(tmp_path: Path) -> None:
    _conformance_artifacts.write_generated_artifacts(tmp_path)
    first = {path.name: path.read_bytes() for path in sorted(tmp_path.glob("*.json"))}

    _conformance_artifacts.write_generated_artifacts(tmp_path)
    second = {path.name: path.read_bytes() for path in sorted(tmp_path.glob("*.json"))}

    assert first == second
    assert set(first) == {"characteristics.json", "models.json"}


def test_stale_generated_artifacts_detects_missing_and_modified_files(
    tmp_path: Path,
) -> None:
    assert set(_conformance_artifacts.stale_generated_artifacts(tmp_path)) == {
        "characteristics.json",
        "models.json",
    }

    _conformance_artifacts.write_generated_artifacts(tmp_path)
    (tmp_path / "models.json").write_text("{}\n", encoding="utf-8")

    assert _conformance_artifacts.stale_generated_artifacts(tmp_path) == (
        "models.json",
    )


def test_render_json_rejects_nonfinite_numbers() -> None:
    with pytest.raises(ValueError):
        _conformance_artifacts.render_json({"value": float("nan")})
