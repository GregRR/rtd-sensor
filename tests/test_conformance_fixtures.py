# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from rtd_sensor import _conformance_artifacts, _conformance_fixtures, _definitions
from rtd_sensor.models import PiecewisePolynomialRTDModel

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONFORMANCE_DIR = _REPO_ROOT / "conformance" / "v1"
_VECTOR_DIR = _CONFORMANCE_DIR / "vectors"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    assert isinstance(document, dict)
    return document


def _fixture_documents() -> list[dict[str, Any]]:
    fixtures = _load_json(_CONFORMANCE_DIR / "model-fixtures.json")["fixtures"]
    assert isinstance(fixtures, list)
    return fixtures


def _vector_groups(filename: str) -> list[dict[str, Any]]:
    groups = _load_json(_VECTOR_DIR / filename)["test_groups"]
    assert isinstance(groups, list)
    return groups


def test_generated_custom_fixture_artifacts_validate_against_schemas() -> None:
    pairs = (
        ("model-fixtures.json", "model-fixture-catalog.schema.json"),
        ("vectors/custom-temperature-to-resistance.json", "vector-set.schema.json"),
        ("vectors/custom-resistance-to-temperature.json", "vector-set.schema.json"),
        (
            "vectors/custom-temperature-to-resistance-status.json",
            "vector-set.schema.json",
        ),
        (
            "vectors/custom-resistance-to-temperature-status.json",
            "vector-set.schema.json",
        ),
    )
    for filename, schema_filename in pairs:
        schema = _load_json(_CONFORMANCE_DIR / "schemas" / schema_filename)
        Draft202012Validator(schema).validate(_load_json(_CONFORMANCE_DIR / filename))


def test_fixture_ids_are_local_and_unique() -> None:
    fixture_ids = [
        fixture.fixture_id for fixture in _conformance_fixtures.MODEL_FIXTURES
    ]

    assert len(fixture_ids) == len(set(fixture_ids))
    assert not set(fixture_ids) & set(_definitions.BUILTIN_MODEL_DEFINITIONS)


def test_characteristic_model_fixtures_reference_known_characteristics() -> None:
    known_characteristics = set(_definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS)

    for document in _fixture_documents():
        if document["fixture_kind"] != "characteristic_model":
            continue

        definition = document["definition"]
        assert isinstance(definition, dict)
        characteristic_id = definition["characteristic_id"]
        assert isinstance(characteristic_id, str)
        assert characteristic_id in known_characteristics


def test_fixture_catalog_preserves_declared_fixture_order_and_status() -> None:
    expected = [
        (fixture.fixture_id, fixture.expected_status)
        for fixture in _conformance_fixtures.MODEL_FIXTURES
    ]
    actual = [
        (document["fixture_id"], document["expected_status"])
        for document in _fixture_documents()
    ]

    assert actual == expected


def test_fixture_expected_status_matches_python_construction() -> None:
    for fixture in _conformance_fixtures.MODEL_FIXTURES:
        if fixture.expected_status == "ok":
            _conformance_fixtures.build_fixture_model(fixture)
        else:
            with pytest.raises((TypeError, ValueError)):
                _conformance_fixtures.build_fixture_model(fixture)


def test_invalid_model_fixtures_cover_all_configurable_families() -> None:
    invalid = {
        fixture.fixture_id
        for fixture in _conformance_fixtures.MODEL_FIXTURES
        if fixture.expected_status == "invalid_model"
    }

    assert invalid == {
        "invalid_calibrated_r0_nonpositive",
        "invalid_cvd_missing_c_negative_range",
        "invalid_cvd_nonmonotonic",
        "invalid_polynomial_decreasing",
        "invalid_piecewise_gap",
        "invalid_piecewise_unapproved_discontinuity",
    }


def test_custom_success_vectors_reference_only_valid_fixture_ids() -> None:
    valid_ids = {
        fixture.fixture_id
        for fixture in _conformance_fixtures.MODEL_FIXTURES
        if fixture.expected_status == "ok"
    }
    for filename in (
        "custom-temperature-to-resistance.json",
        "custom-resistance-to-temperature.json",
    ):
        groups = _vector_groups(filename)
        assert {group["fixture_id"] for group in groups} == valid_ids
        assert all("model_id" not in group for group in groups)


def test_custom_vectors_match_reference_models_and_pair_round_trips() -> None:
    forward_groups = {
        group["fixture_id"]: group
        for group in _vector_groups("custom-temperature-to-resistance.json")
    }
    inverse_groups = {
        group["fixture_id"]: group
        for group in _vector_groups("custom-resistance-to-temperature.json")
    }
    assert forward_groups.keys() == inverse_groups.keys()

    for fixture_id, forward_group in forward_groups.items():
        assert isinstance(fixture_id, str)
        fixture = _conformance_fixtures.fixture_by_id(fixture_id)
        model = _conformance_fixtures.build_fixture_model(fixture)
        inverse_cases = {
            case["case_id"].rsplit(".", 1)[-1]: case
            for case in inverse_groups[fixture_id]["cases"]
        }

        for forward_case in forward_group["cases"]:
            temperature_c = float(forward_case["input"]["value"])
            resistance_ohms = float(forward_case["expected"]["value"])
            assert model.celsius_to_resistance(temperature_c) == resistance_ohms

            token = forward_case["case_id"].rsplit(".", 1)[-1]
            inverse_case = inverse_cases[token]
            assert inverse_case["input"]["value"] == resistance_ohms
            assert inverse_case["expected"]["value"] == temperature_c
            tolerance = inverse_case["expected"]["acceptance"]["binary64_reference"][
                "absolute_tolerance"
            ]
            assert (
                abs(model.resistance_to_celsius(resistance_ohms) - temperature_c)
                <= tolerance
            )


def test_custom_vectors_publish_binary64_only_until_separately_characterized() -> None:
    for filename in (
        "custom-temperature-to-resistance.json",
        "custom-resistance-to-temperature.json",
    ):
        for group in _vector_groups(filename):
            for case in group["cases"]:
                acceptance = case["expected"]["acceptance"]
                assert acceptance == {
                    "binary64_reference": {"absolute_tolerance": 1.0e-9}
                }


def test_positive_only_cvd_fixture_crosses_reference_ratio_away_from_zero() -> None:
    fixture = _conformance_fixtures.fixture_by_id("custom_cvd_positive_ratio_crossing")
    model = _conformance_fixtures.build_fixture_model(fixture)

    assert model.minimum_temperature_c == 50.0
    assert model.maximum_temperature_c == 100.0
    assert model.celsius_to_resistance(60.0) == pytest.approx(100.0, abs=1e-12)
    with pytest.raises(ValueError):
        model.celsius_to_resistance(0.0)


def test_negative_only_cvd_fixture_does_not_infer_branch_from_r_over_r0() -> None:
    fixture = _conformance_fixtures.fixture_by_id("custom_cvd_negative_only")
    model = _conformance_fixtures.build_fixture_model(fixture)
    resistance = model.celsius_to_resistance(-75.0)

    assert resistance > 100.0
    assert model.resistance_to_celsius(resistance) == pytest.approx(-75.0, abs=1e-9)


def test_piecewise_fixture_preserves_source_data_and_exports_derived_offsets() -> None:
    fixture = _conformance_fixtures.fixture_by_id("custom_piecewise_stitched_join")
    model = _conformance_fixtures.build_fixture_model(fixture)
    assert isinstance(model, PiecewisePolynomialRTDModel)

    document = next(
        item
        for item in _fixture_documents()
        if item["fixture_id"] == "custom_piecewise_stitched_join"
    )
    definition = document["definition"]
    assert isinstance(definition, dict)
    segments = definition["segments"]
    assert isinstance(segments, list)
    assert segments[1]["coefficients"] == [0.999999, 0.01]
    derived = document["derived"]
    assert isinstance(derived, dict)
    assert derived["continuity_adjustment_kind"] == "additive_resistance_ratio_offset"
    assert derived["continuity_adjustments"] == pytest.approx([0.0, 1.0e-6])
    assert model.segments[1].coefficients == (0.999999, 0.01)


def test_custom_fixture_artifacts_are_part_of_deterministic_generation() -> None:
    generated = _conformance_artifacts.generated_artifacts()

    assert "model-fixtures.json" in generated
    assert "vectors/custom-temperature-to-resistance.json" in generated
    assert "vectors/custom-resistance-to-temperature.json" in generated
    assert "vectors/custom-temperature-to-resistance-status.json" in generated
    assert "vectors/custom-resistance-to-temperature-status.json" in generated


def _status_input_value(input_document: dict[str, Any]) -> float:
    if "value" in input_document:
        return float(input_document["value"])
    special = input_document["special"]
    assert isinstance(special, str)
    return {
        "nan": float("nan"),
        "positive_infinity": float("inf"),
        "negative_infinity": float("-inf"),
    }[special]


def test_custom_status_vectors_reference_only_valid_fixture_ids() -> None:
    valid_ids = {
        fixture.fixture_id
        for fixture in _conformance_fixtures.MODEL_FIXTURES
        if fixture.expected_status == "ok"
    }
    for filename in (
        "custom-temperature-to-resistance-status.json",
        "custom-resistance-to-temperature-status.json",
    ):
        groups = _vector_groups(filename)
        assert {group["fixture_id"] for group in groups} == valid_ids
        assert all("model_id" not in group for group in groups)


def test_custom_status_vectors_match_reference_runtime_semantics() -> None:
    for filename in (
        "custom-temperature-to-resistance-status.json",
        "custom-resistance-to-temperature-status.json",
    ):
        document = _load_json(_VECTOR_DIR / filename)
        capability_id = document["capability_id"]
        assert isinstance(capability_id, str)

        for group in _vector_groups(filename):
            fixture_id = group["fixture_id"]
            assert isinstance(fixture_id, str)
            fixture = _conformance_fixtures.fixture_by_id(fixture_id)
            model = _conformance_fixtures.build_fixture_model(fixture)
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
                else:
                    with pytest.raises(ValueError):
                        model.resistance_to_celsius(value)
                    if status == "out_of_range_low":
                        assert 0.0 < value < minimum_resistance
                    elif status == "out_of_range_high":
                        assert value > maximum_resistance
                    else:
                        assert status == "invalid_input"


def test_one_sided_cvd_status_vectors_reject_excluded_reference_temperature() -> None:
    groups = {
        group["fixture_id"]: group
        for group in _vector_groups("custom-temperature-to-resistance-status.json")
    }
    expected = {
        "custom_cvd_positive_ratio_crossing": "out_of_range_low",
        "custom_cvd_negative_only": "out_of_range_high",
    }
    for fixture_id, status in expected.items():
        cases = {
            case["case_id"].rsplit(".", 1)[-1]: case
            for case in groups[fixture_id]["cases"]
        }
        case = cases["excluded_reference_temperature"]
        assert case["input"] == {"value": 0.0}
        assert case["expected"] == {"status": status}


def test_negative_only_fixture_includes_off_zero_ratio_crossing_anchor() -> None:
    fixture = _conformance_fixtures.fixture_by_id("custom_cvd_negative_only")
    model = _conformance_fixtures.build_fixture_model(fixture)

    assert model.celsius_to_resistance(-80.0) == pytest.approx(100.0, abs=1e-12)
    assert model.resistance_to_celsius(100.0) == pytest.approx(-80.0, abs=1e-9)
