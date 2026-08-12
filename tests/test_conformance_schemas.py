# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

_SCHEMA_DIR = Path(__file__).resolve().parents[1] / "conformance" / "v1" / "schemas"
_SCHEMA_NAMES = (
    "characteristic-catalog.schema.json",
    "model-catalog.schema.json",
    "vector-set.schema.json",
)


def _load_schema(name: str) -> dict[str, Any]:
    with (_SCHEMA_DIR / name).open(encoding="utf-8") as handle:
        value = json.load(handle)
    assert isinstance(value, dict)
    return value


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(_load_schema(name))


def _source_reference() -> dict[str, Any]:
    return {
        "citation": "Example source",
        "url": "https://example.invalid/rtd-source",
    }


def _characteristic_catalog() -> dict[str, Any]:
    return {
        "artifact_type": "characteristic_catalog",
        "format_version": 1,
        "contract_version": 1,
        "rtd_sensor_version": "0.5.0",
        "characteristics": [
            {
                "characteristic_id": "iec60751_pt385",
                "display_name": "IEC 60751 PT-385 curve",
                "material": "platinum",
                "curve_kind": "callendar_van_dusen",
                "reference_temperature_c": 0.0,
                "minimum_temperature_c": -200.0,
                "maximum_temperature_c": 850.0,
                "parameters": {
                    "a": 3.9083e-3,
                    "b": -5.775e-7,
                    "c": -4.183e-12,
                },
                "source_references": [_source_reference()],
            },
            {
                "characteristic_id": "ni6180_din43760",
                "display_name": "Former DIN 43760 nickel 6180 ppm/K curve",
                "material": "nickel",
                "curve_kind": "polynomial",
                "reference_temperature_c": 0.0,
                "minimum_temperature_c": -60.0,
                "maximum_temperature_c": 250.0,
                "coefficients": [5.485e-3, 6.65e-6],
                "source_references": [_source_reference()],
            },
            {
                "characteristic_id": "ni6720_north_american",
                "display_name": "North American nickel 6720 ppm/K curve",
                "material": "nickel",
                "curve_kind": "piecewise_polynomial",
                "reference_temperature_c": 0.0,
                "minimum_temperature_c": -80.0,
                "maximum_temperature_c": 260.0,
                "segments": [
                    {
                        "minimum_temperature_c": -80.0,
                        "maximum_temperature_c": 0.0,
                        "coefficients": [1.0, 5.9e-3],
                        "temperature_origin_c": 0.0,
                    },
                    {
                        "minimum_temperature_c": 0.0,
                        "maximum_temperature_c": 260.0,
                        "coefficients": [1.0, 5.8e-3],
                        "temperature_origin_c": 0.0,
                    },
                ],
                "continuity_adjustment_kind": "additive_resistance_ratio_offset",
                "maximum_continuity_adjustment_ratio": 1.0e-5,
                "continuity_adjustment_reason": "Reconcile rounded source joins.",
                "derived_continuity_adjustments": [0.0, 2.0e-7],
                "source_references": [_source_reference()],
            },
        ],
    }


def _model_catalog() -> dict[str, Any]:
    return {
        "artifact_type": "model_catalog",
        "format_version": 1,
        "contract_version": 1,
        "rtd_sensor_version": "0.5.0",
        "models": [
            {
                "model_id": "pt100",
                "display_name": "Pt100",
                "characteristic_id": "iec60751_pt385",
                "reference_resistance_ohms": 100.0,
                "minimum_temperature_c": -200.0,
                "maximum_temperature_c": 850.0,
            }
        ],
    }


def _vector_set() -> dict[str, Any]:
    return {
        "artifact_type": "vector_set",
        "format_version": 1,
        "contract_version": 1,
        "rtd_sensor_version": "0.5.0",
        "capability_id": "conversion.temperature_to_resistance",
        "input_unit": "degree_celsius",
        "output_unit": "ohm",
        "test_groups": [
            {
                "group_id": "pt100.temperature_to_resistance",
                "model_id": "pt100",
                "cases": [
                    {
                        "case_id": "pt100.temperature_to_resistance.reference_0c",
                        "tags": ["reference_temperature"],
                        "input": {"value": 0.0},
                        "expected": {
                            "status": "ok",
                            "value": 100.0,
                            "acceptance": {
                                "binary64_reference": {"absolute_tolerance": 1.0e-12}
                            },
                        },
                    },
                    {
                        "case_id": "pt100.temperature_to_resistance.low_error",
                        "input": {"value": -201.0},
                        "expected": {"status": "out_of_range_low"},
                    },
                    {
                        "case_id": "pt100.temperature_to_resistance.nan",
                        "input": {"special": "nan"},
                        "expected": {"status": "invalid_input"},
                    },
                ],
            }
        ],
    }


def _example_artifact_for_schema(schema_name: str) -> dict[str, Any]:
    match schema_name:
        case "characteristic-catalog.schema.json":
            return _characteristic_catalog()
        case "model-catalog.schema.json":
            return _model_catalog()
        case "vector-set.schema.json":
            return _vector_set()
        case _:
            raise AssertionError(f"Unknown conformance schema fixture: {schema_name}")


@pytest.mark.parametrize("schema_name", _SCHEMA_NAMES)
def test_conformance_schema_is_valid_draft_2020_12(schema_name: str) -> None:
    schema = _load_schema(schema_name)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("schema_name", _SCHEMA_NAMES)
def test_conformance_schema_rejects_wrong_contract_version(schema_name: str) -> None:
    schema = _load_schema(schema_name)
    instance = _example_artifact_for_schema(schema_name)
    instance["contract_version"] = 2

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_characteristic_catalog_accepts_all_initial_curve_kinds() -> None:
    _validator("characteristic-catalog.schema.json").validate(_characteristic_catalog())


def test_characteristic_catalog_rejects_unknown_properties() -> None:
    catalog = _characteristic_catalog()
    characteristic = catalog["characteristics"][0]
    assert isinstance(characteristic, dict)
    characteristic["unexpected"] = True

    with pytest.raises(ValidationError):
        _validator("characteristic-catalog.schema.json").validate(catalog)


def test_characteristic_catalog_rejects_noncanonical_identifier() -> None:
    catalog = _characteristic_catalog()
    characteristic = catalog["characteristics"][0]
    assert isinstance(characteristic, dict)
    characteristic["characteristic_id"] = "IEC60751 PT385"

    with pytest.raises(ValidationError):
        _validator("characteristic-catalog.schema.json").validate(catalog)


def test_characteristic_catalog_rejects_empty_polynomial_coefficients() -> None:
    catalog = _characteristic_catalog()
    characteristic = catalog["characteristics"][1]
    assert isinstance(characteristic, dict)
    characteristic["coefficients"] = []

    with pytest.raises(ValidationError):
        _validator("characteristic-catalog.schema.json").validate(catalog)


def test_characteristic_catalog_requires_piecewise_derived_adjustments() -> None:
    catalog = _characteristic_catalog()
    characteristic = catalog["characteristics"][2]
    assert isinstance(characteristic, dict)
    del characteristic["derived_continuity_adjustments"]

    with pytest.raises(ValidationError):
        _validator("characteristic-catalog.schema.json").validate(catalog)


def test_characteristic_curve_kind_selects_one_shape() -> None:
    catalog = _characteristic_catalog()
    characteristic = catalog["characteristics"][0]
    assert isinstance(characteristic, dict)
    characteristic["curve_kind"] = "polynomial"

    with pytest.raises(ValidationError):
        _validator("characteristic-catalog.schema.json").validate(catalog)


def test_model_catalog_accepts_builtin_model_shape() -> None:
    _validator("model-catalog.schema.json").validate(_model_catalog())


def test_model_catalog_rejects_nonpositive_reference_resistance() -> None:
    catalog = _model_catalog()
    model = catalog["models"][0]
    assert isinstance(model, dict)
    model["reference_resistance_ohms"] = 0.0

    with pytest.raises(ValidationError):
        _validator("model-catalog.schema.json").validate(catalog)


def test_model_catalog_rejects_unknown_properties() -> None:
    catalog = _model_catalog()
    model = catalog["models"][0]
    assert isinstance(model, dict)
    model["aliases"] = ["pt-100"]

    with pytest.raises(ValidationError):
        _validator("model-catalog.schema.json").validate(catalog)


def test_vector_set_accepts_success_error_and_special_input_cases() -> None:
    _validator("vector-set.schema.json").validate(_vector_set())


@pytest.mark.parametrize(
    "status",
    [
        "out_of_range_low",
        "out_of_range_high",
        "invalid_input",
        "invalid_model",
        "calculation_failure",
    ],
)
def test_vector_set_accepts_every_declared_error_status(status: str) -> None:
    vectors = _vector_set()
    group = vectors["test_groups"][0]
    assert isinstance(group, dict)
    case = group["cases"][1]
    assert isinstance(case, dict)
    case["expected"] = {"status": status}

    _validator("vector-set.schema.json").validate(vectors)


def test_vector_set_accepts_inverse_conversion_unit_pair() -> None:
    vectors = _vector_set()
    vectors["capability_id"] = "conversion.resistance_to_temperature"
    vectors["input_unit"] = "ohm"
    vectors["output_unit"] = "degree_celsius"

    _validator("vector-set.schema.json").validate(vectors)


def test_vector_set_rejects_capability_unit_mismatch() -> None:
    vectors = _vector_set()
    vectors["input_unit"] = "ohm"

    with pytest.raises(ValidationError):
        _validator("vector-set.schema.json").validate(vectors)


def test_vector_set_rejects_unknown_special_value() -> None:
    vectors = _vector_set()
    group = vectors["test_groups"][0]
    assert isinstance(group, dict)
    case = group["cases"][2]
    assert isinstance(case, dict)
    case["input"] = {"special": "not_a_number"}

    with pytest.raises(ValidationError):
        _validator("vector-set.schema.json").validate(vectors)


def test_vector_set_rejects_unsupported_model_as_result_status() -> None:
    vectors = _vector_set()
    group = vectors["test_groups"][0]
    assert isinstance(group, dict)
    case = group["cases"][1]
    assert isinstance(case, dict)
    case["expected"] = {"status": "unsupported_model"}

    with pytest.raises(ValidationError):
        _validator("vector-set.schema.json").validate(vectors)


def test_vector_set_rejects_value_on_error_result() -> None:
    vectors = _vector_set()
    group = vectors["test_groups"][0]
    assert isinstance(group, dict)
    case = group["cases"][1]
    assert isinstance(case, dict)
    case["expected"] = {"status": "out_of_range_low", "value": 0.0}

    with pytest.raises(ValidationError):
        _validator("vector-set.schema.json").validate(vectors)


def test_vector_set_rejects_success_without_acceptance_profile() -> None:
    vector_set = _vector_set()
    group = vector_set["test_groups"][0]
    assert isinstance(group, dict)
    case = group["cases"][0]
    assert isinstance(case, dict)
    expected = case["expected"]
    assert isinstance(expected, dict)
    expected.pop("acceptance")

    with pytest.raises(ValidationError):
        _validator("vector-set.schema.json").validate(vector_set)


def test_vector_set_rejects_unknown_acceptance_profile() -> None:
    vectors = _vector_set()
    group = vectors["test_groups"][0]
    assert isinstance(group, dict)
    case = group["cases"][0]
    assert isinstance(case, dict)
    expected = case["expected"]
    assert isinstance(expected, dict)
    acceptance = expected["acceptance"]
    assert isinstance(acceptance, dict)
    acceptance["binary16"] = {"absolute_tolerance": 1.0}

    with pytest.raises(ValidationError):
        _validator("vector-set.schema.json").validate(vectors)


def test_vector_set_rejects_negative_acceptance_tolerance() -> None:
    vectors = _vector_set()
    group = vectors["test_groups"][0]
    assert isinstance(group, dict)
    case = group["cases"][0]
    assert isinstance(case, dict)
    expected = case["expected"]
    assert isinstance(expected, dict)
    acceptance = expected["acceptance"]
    assert isinstance(acceptance, dict)
    profile = acceptance["binary64_reference"]
    assert isinstance(profile, dict)
    profile["absolute_tolerance"] = -1.0

    with pytest.raises(ValidationError):
        _validator("vector-set.schema.json").validate(vectors)


def test_vector_set_rejects_duplicate_tags() -> None:
    vectors = _vector_set()
    group = vectors["test_groups"][0]
    assert isinstance(group, dict)
    case = group["cases"][0]
    assert isinstance(case, dict)
    case["tags"] = ["reference_temperature", "reference_temperature"]

    with pytest.raises(ValidationError):
        _validator("vector-set.schema.json").validate(vectors)


def test_vector_set_rejects_unknown_properties() -> None:
    vectors = copy.deepcopy(_vector_set())
    vectors["notes"] = "not part of the normative v1 vector shape"

    with pytest.raises(ValidationError):
        _validator("vector-set.schema.json").validate(vectors)
