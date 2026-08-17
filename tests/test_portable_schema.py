# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from rtd_sensor import portable
from rtd_sensor.exceptions import InvalidPortableModelDefinitionError
from rtd_sensor.models import (
    CallendarVanDusenRTDModel,
    IEC60751RTDModel,
    PiecewisePolynomialRTDModel,
    PiecewisePolynomialSegment,
    PolynomialRTDModel,
)

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "portable"
    / "v1"
    / "model-definition.schema.json"
)


def _schema() -> dict[str, Any]:
    value = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _validator() -> Draft202012Validator:
    return Draft202012Validator(_schema())


def _models() -> tuple[portable.PortableRTDModel, ...]:
    return (
        IEC60751RTDModel(
            r0_ohms=100.017,
            minimum_temperature_c=-50.0,
            maximum_temperature_c=250.0,
        ),
        CallendarVanDusenRTDModel(
            r0_ohms=100.025,
            a=3.91e-3,
            b=-5.8e-7,
            c=-4.2e-12,
            minimum_temperature_c=-100.0,
            maximum_temperature_c=250.0,
        ),
        PolynomialRTDModel(
            reference_resistance_ohms=1000.0,
            reference_temperature_c=25.0,
            coefficients=(0.004, 1e-6),
            minimum_temperature_c=-20.0,
            maximum_temperature_c=120.0,
        ),
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
                    coefficients=(1.0, 0.02),
                ),
            ),
        ),
    )


def test_portable_identifier_grammar_matches_conformance_v1() -> None:
    portable_pattern = _schema()["$defs"]["identifier"]["pattern"]
    conformance_path = (
        Path(__file__).resolve().parents[1]
        / "conformance"
        / "v1"
        / "schemas"
        / "model-fixture-catalog.schema.json"
    )
    conformance_schema = json.loads(conformance_path.read_text(encoding="utf-8"))

    assert portable_pattern == conformance_schema["$defs"]["identifier"]["pattern"]


def test_portable_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(_schema())


@pytest.mark.parametrize("model", _models())
def test_serialized_portable_models_validate_against_schema(
    model: portable.PortableRTDModel,
) -> None:
    artifact = portable.model_to_portable_definition(
        model,
        metadata={"source": "schema test", "unknown_future_note": {"value": 1}},
    )

    _validator().validate(artifact)


def test_schema_rejects_conformance_fixture_semantics() -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    artifact["expected_status"] = "ok"

    with pytest.raises(ValidationError):
        _validator().validate(artifact)


def test_schema_rejects_unknown_behavior_field() -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    definition["extrapolate"] = True

    with pytest.raises(ValidationError):
        _validator().validate(artifact)


def test_schema_allows_open_nonbehavioral_metadata() -> None:
    artifact = portable.model_to_portable_definition(
        IEC60751RTDModel(r0_ohms=100.0),
        metadata={
            "future_provenance": {
                "laboratory": "Example",
                "references": ["A", "B"],
            }
        },
    )

    _validator().validate(artifact)


@pytest.mark.parametrize(
    ("format_version", "expected_valid"),
    [
        (1, True),
        (1.0, True),
        (2, False),
        (1.5, False),
        ("1", False),
        (True, False),
    ],
)
def test_schema_and_loader_agree_on_format_version(
    format_version: object,
    expected_valid: bool,
) -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    artifact["format_version"] = format_version

    schema_valid = not list(_validator().iter_errors(artifact))
    assert schema_valid is expected_valid

    if expected_valid:
        portable.model_from_portable_definition(artifact)
    else:
        with pytest.raises(InvalidPortableModelDefinitionError):
            portable.model_from_portable_definition(artifact)


def test_schema_and_loader_both_reject_boolean_behavioral_number() -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    definition["reference_resistance_ohms"] = True

    assert list(_validator().iter_errors(artifact))
    with pytest.raises(InvalidPortableModelDefinitionError):
        portable.model_from_portable_definition(artifact)


def test_schema_and_loader_both_reject_oversized_polynomial_coefficients() -> None:
    artifact = portable.model_to_portable_definition(
        PolynomialRTDModel(
            reference_resistance_ohms=100.0,
            coefficients=(0.004,),
            minimum_temperature_c=0.0,
            maximum_temperature_c=100.0,
        )
    )
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    definition["coefficients"] = [0.001] * 13

    assert list(_validator().iter_errors(artifact))
    with pytest.raises(InvalidPortableModelDefinitionError):
        portable.model_from_portable_definition(artifact)
