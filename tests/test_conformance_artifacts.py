# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from rtd_sensor import _conformance_artifacts, _curves, _definitions, _models

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONFORMANCE_DIR = _REPO_ROOT / "conformance" / "v1"
_SCHEMA_DIR = _CONFORMANCE_DIR / "schemas"
_VECTOR_DIR = _CONFORMANCE_DIR / "vectors"
_SUCCESS_VECTOR_FILENAMES = (
    "builtin-temperature-to-resistance.json",
    "builtin-resistance-to-temperature.json",
)
_STATUS_VECTOR_FILENAMES = (
    "builtin-temperature-to-resistance-status.json",
    "builtin-resistance-to-temperature-status.json",
)
_VECTOR_FILENAMES = _SUCCESS_VECTOR_FILENAMES + _STATUS_VECTOR_FILENAMES


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


def _vector_groups(filename: str) -> list[dict[str, Any]]:
    document = _load_json(_VECTOR_DIR / filename)
    groups = document["test_groups"]
    assert isinstance(groups, list)
    return groups


@pytest.mark.parametrize(
    ("filename", "schema_filename"),
    [
        ("characteristics.json", "characteristic-catalog.schema.json"),
        ("models.json", "model-catalog.schema.json"),
        (
            "vectors/builtin-temperature-to-resistance.json",
            "vector-set.schema.json",
        ),
        (
            "vectors/builtin-resistance-to-temperature.json",
            "vector-set.schema.json",
        ),
        (
            "vectors/builtin-temperature-to-resistance-status.json",
            "vector-set.schema.json",
        ),
        (
            "vectors/builtin-resistance-to-temperature-status.json",
            "vector-set.schema.json",
        ),
    ],
)
def test_generated_artifact_validates_against_schema(
    filename: str,
    schema_filename: str,
) -> None:
    schema = _load_json(_SCHEMA_DIR / schema_filename)
    Draft202012Validator(schema).validate(_load_json(_CONFORMANCE_DIR / filename))


def test_committed_artifacts_match_deterministic_generator() -> None:
    assert _conformance_artifacts.stale_generated_artifacts(_CONFORMANCE_DIR) == ()

    for filename, expected in _conformance_artifacts.generated_artifacts().items():
        assert (_CONFORMANCE_DIR / filename).read_text(encoding="utf-8") == expected
        assert expected.endswith("\n")


def test_generated_artifacts_record_current_project_version() -> None:
    expected_version = _conformance_artifacts._project_version()

    for filename in _conformance_artifacts.generated_artifacts():
        assert (
            _load_json(_CONFORMANCE_DIR / filename)["rtd_sensor_version"]
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


@pytest.mark.parametrize("filename", _VECTOR_FILENAMES)
def test_conversion_vectors_preserve_authoritative_model_order(filename: str) -> None:
    expected_ids = list(_definitions.BUILTIN_MODEL_DEFINITIONS)
    actual_ids = [group["model_id"] for group in _vector_groups(filename)]

    assert actual_ids == expected_ids


def test_conversion_vector_ids_are_unique() -> None:
    for filename in _VECTOR_FILENAMES:
        groups = _vector_groups(filename)
        group_ids = [group["group_id"] for group in groups]
        case_ids = [case["case_id"] for group in groups for case in group["cases"]]

        assert len(group_ids) == len(set(group_ids))
        assert len(case_ids) == len(set(case_ids))


def test_conversion_vectors_match_runtime_and_pair_round_trip_anchors() -> None:
    forward_groups = {
        group["model_id"]: group
        for group in _vector_groups("builtin-temperature-to-resistance.json")
    }
    inverse_groups = {
        group["model_id"]: group
        for group in _vector_groups("builtin-resistance-to-temperature.json")
    }

    assert forward_groups.keys() == inverse_groups.keys()

    for model_id, forward_group in forward_groups.items():
        assert isinstance(model_id, str)
        model = _models.BUILTIN_RTD_MODELS[model_id]
        inverse_cases = {
            case["case_id"].rsplit(".", 1)[-1]: case
            for case in inverse_groups[model_id]["cases"]
        }

        for forward_case in forward_group["cases"]:
            temperature_c = forward_case["input"]["value"]
            expected_resistance = forward_case["expected"]["value"]
            assert isinstance(temperature_c, int | float)
            assert isinstance(expected_resistance, int | float)
            assert model.celsius_to_resistance(float(temperature_c)) == float(
                expected_resistance
            )

            token = forward_case["case_id"].rsplit(".", 1)[-1]
            inverse_case = inverse_cases[token]
            assert inverse_case["input"]["value"] == expected_resistance
            assert inverse_case["expected"]["value"] == temperature_c

            tolerance = inverse_case["expected"]["acceptance"]["binary64_reference"][
                "absolute_tolerance"
            ]
            converted = model.resistance_to_celsius(float(expected_resistance))
            assert abs(converted - float(temperature_c)) <= tolerance


def test_initial_conversion_vectors_publish_only_binary64_acceptance() -> None:
    for filename in _SUCCESS_VECTOR_FILENAMES:
        for group in _vector_groups(filename):
            for case in group["cases"]:
                acceptance = case["expected"]["acceptance"]
                assert set(acceptance) == {"binary64_reference"}
                assert acceptance["binary64_reference"]["absolute_tolerance"] == 1e-9


def test_conversion_vectors_cover_boundaries_reference_and_branch_cases() -> None:
    groups = {
        group["model_id"]: group
        for group in _vector_groups("builtin-temperature-to-resistance.json")
    }

    for group in groups.values():
        all_tags = {tag for case in group["cases"] for tag in case["tags"]}
        assert "minimum_boundary" in all_tags
        assert "maximum_boundary" in all_tags
        assert "reference_temperature" in all_tags
        assert "round_trip_anchor" in all_tags

    for model_id in ("pt100", "pt500", "pt1000"):
        all_tags = {tag for case in groups[model_id]["cases"] for tag in case["tags"]}
        assert "branch_boundary" in all_tags
        assert "branch_neighbor" in all_tags

    ni120_tags = [tag for case in groups["ni120"]["cases"] for tag in case["tags"]]
    assert ni120_tags.count("piecewise_join") == 11
    assert ni120_tags.count("piecewise_segment") == 12


def _status_input_value(input_document: dict[str, Any]) -> float:
    if "value" in input_document:
        value = input_document["value"]
        assert isinstance(value, int | float)
        return float(value)

    special = input_document["special"]
    assert isinstance(special, str)
    return {
        "nan": float("nan"),
        "positive_infinity": float("inf"),
        "negative_infinity": float("-inf"),
    }[special]


def test_status_vectors_publish_expected_status_coverage() -> None:
    forward_groups = _vector_groups("builtin-temperature-to-resistance-status.json")
    inverse_groups = _vector_groups("builtin-resistance-to-temperature-status.json")

    for group in forward_groups:
        statuses = [case["expected"]["status"] for case in group["cases"]]
        assert statuses.count("out_of_range_low") == 1
        assert statuses.count("out_of_range_high") == 1
        assert statuses.count("invalid_input") == 3

    for group in inverse_groups:
        statuses = [case["expected"]["status"] for case in group["cases"]]
        assert statuses.count("out_of_range_low") == 1
        assert statuses.count("out_of_range_high") == 1
        assert statuses.count("invalid_input") == 5


def test_status_vectors_match_runtime_rejection_and_semantic_classification() -> None:
    for filename in _STATUS_VECTOR_FILENAMES:
        document = _load_json(_VECTOR_DIR / filename)
        capability_id = document["capability_id"]
        assert isinstance(capability_id, str)

        for group in _vector_groups(filename):
            model_id = group["model_id"]
            assert isinstance(model_id, str)
            model = _models.BUILTIN_RTD_MODELS[model_id]
            minimum_resistance = model.celsius_to_resistance(
                model.minimum_temperature_c
            )
            maximum_resistance = model.celsius_to_resistance(
                model.maximum_temperature_c
            )

            for case in group["cases"]:
                input_document = case["input"]
                expected = case["expected"]
                assert isinstance(input_document, dict)
                assert isinstance(expected, dict)
                assert set(expected) == {"status"}
                status = expected["status"]
                value = _status_input_value(input_document)

                if capability_id == "conversion.temperature_to_resistance":
                    with pytest.raises(ValueError):
                        model.celsius_to_resistance(value)
                    if status == "out_of_range_low":
                        assert value < model.minimum_temperature_c
                    elif status == "out_of_range_high":
                        assert value > model.maximum_temperature_c
                    else:
                        assert status == "invalid_input"
                        assert not math.isfinite(value)
                else:
                    with pytest.raises(ValueError):
                        model.resistance_to_celsius(value)
                    if status == "out_of_range_low":
                        assert 0.0 < value < minimum_resistance
                    elif status == "out_of_range_high":
                        assert value > maximum_resistance
                    else:
                        assert status == "invalid_input"
                        assert value <= 0.0 or not math.isfinite(value)


def test_success_vectors_include_inside_boundary_neighbors() -> None:
    for filename in _SUCCESS_VECTOR_FILENAMES:
        for group in _vector_groups(filename):
            tags = {tag for case in group["cases"] for tag in case["tags"]}
            assert "inside_boundary" in tags
            assert "minimum_boundary_neighbor" in tags
            assert "maximum_boundary_neighbor" in tags


def test_generator_writes_deterministic_artifacts(tmp_path: Path) -> None:
    def generated_files() -> dict[str, bytes]:
        return {
            path.relative_to(tmp_path).as_posix(): path.read_bytes()
            for path in sorted(tmp_path.rglob("*.json"))
        }

    _conformance_artifacts.write_generated_artifacts(tmp_path)
    first = generated_files()

    _conformance_artifacts.write_generated_artifacts(tmp_path)
    second = generated_files()

    assert first == second
    assert set(first) == set(_conformance_artifacts.generated_artifacts())


def test_stale_generated_artifacts_detects_missing_and_modified_files(
    tmp_path: Path,
) -> None:
    assert set(_conformance_artifacts.stale_generated_artifacts(tmp_path)) == set(
        _conformance_artifacts.generated_artifacts()
    )

    _conformance_artifacts.write_generated_artifacts(tmp_path)
    vector_path = tmp_path / "vectors" / "builtin-resistance-to-temperature.json"
    vector_path.write_text("{}\n", encoding="utf-8")

    assert _conformance_artifacts.stale_generated_artifacts(tmp_path) == (
        "vectors/builtin-resistance-to-temperature.json",
    )


def test_render_json_rejects_nonfinite_numbers() -> None:
    with pytest.raises(ValueError):
        _conformance_artifacts.render_json({"value": float("nan")})
