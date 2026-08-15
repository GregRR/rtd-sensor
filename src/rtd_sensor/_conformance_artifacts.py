# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Deterministic generation of language-neutral RTD conformance artifacts.

The generated catalogs and reference vectors are derived from the same
authoritative built-in characteristic/model definitions used to construct the
Python runtime. This module deliberately contains serialization logic, not a
second copy of the scientific constants.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from . import _conformance_fixtures, _curves, _definitions, _models
from .models import PiecewisePolynomialRTDModel

_FORMAT_VERSION = 1
_CONTRACT_VERSION = 1
_DISTRIBUTION_NAME = "rtd-sensor"
_CHARACTERISTICS_FILENAME = "characteristics.json"
_MODELS_FILENAME = "models.json"
_MODEL_FIXTURES_FILENAME = "model-fixtures.json"
_MANIFEST_FILENAME = "manifest.json"
_CONTRACT_STATUS = "stable"
_CUSTOM_TEMPERATURE_TO_RESISTANCE_FILENAME = (
    "vectors/custom-temperature-to-resistance.json"
)
_CUSTOM_RESISTANCE_TO_TEMPERATURE_FILENAME = (
    "vectors/custom-resistance-to-temperature.json"
)
_CUSTOM_TEMPERATURE_TO_RESISTANCE_STATUS_FILENAME = (
    "vectors/custom-temperature-to-resistance-status.json"
)
_CUSTOM_RESISTANCE_TO_TEMPERATURE_STATUS_FILENAME = (
    "vectors/custom-resistance-to-temperature-status.json"
)
_TEMPERATURE_TO_RESISTANCE_FILENAME = "vectors/builtin-temperature-to-resistance.json"
_RESISTANCE_TO_TEMPERATURE_FILENAME = "vectors/builtin-resistance-to-temperature.json"
_TEMPERATURE_TO_RESISTANCE_STATUS_FILENAME = (
    "vectors/builtin-temperature-to-resistance-status.json"
)
_RESISTANCE_TO_TEMPERATURE_STATUS_FILENAME = (
    "vectors/builtin-resistance-to-temperature-status.json"
)
_BINARY64_ABSOLUTE_TOLERANCE = 1.0e-9
_BINARY32_FORWARD_ABSOLUTE_TOLERANCE = 0.002
_BINARY32_INVERSE_ABSOLUTE_TOLERANCE = 0.001
_BOUNDARY_TEMPERATURE_OFFSET_C = 0.001
_BOUNDARY_RESISTANCE_OFFSET_OHMS = 0.01


def _project_version() -> str:
    """Return the package version used as generated-artifact provenance."""
    try:
        return version(_DISTRIBUTION_NAME)
    except PackageNotFoundError:
        # Source-tree tooling may run without an installed distribution. The
        # project metadata is the release authority in that case.
        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        with pyproject_path.open("rb") as handle:
            project = tomllib.load(handle)["project"]
        project_version = project["version"]
        if not isinstance(project_version, str) or not project_version:
            raise RuntimeError(
                "pyproject.toml contains an invalid project version"
            ) from None
        return project_version


def _json_number(value: float) -> float:
    """Normalize semantically zero floats so generated JSON never emits ``-0.0``."""
    return 0.0 if value == 0.0 else value


def _source_reference_document(
    reference: _definitions.SourceReference,
) -> dict[str, object]:
    document: dict[str, object] = {"citation": reference.citation}
    if reference.url is not None:
        document["url"] = reference.url
    return document


def _common_characteristic_document(
    definition: _definitions.CharacteristicDefinition,
) -> dict[str, object]:
    return {
        "characteristic_id": definition.characteristic_id,
        "display_name": definition.display_name,
        "material": definition.material,
        "curve_kind": definition.curve_kind,
        "reference_temperature_c": definition.reference_temperature_c,
        "minimum_temperature_c": definition.minimum_temperature_c,
        "maximum_temperature_c": definition.maximum_temperature_c,
        "source_references": [
            _source_reference_document(reference)
            for reference in definition.source_references
        ],
    }


def _characteristic_document(
    definition: _definitions.CharacteristicDefinition,
) -> dict[str, object]:
    document = _common_characteristic_document(definition)

    if isinstance(definition, _definitions.CallendarVanDusenCharacteristicDefinition):
        document["parameters"] = {
            "a": definition.a,
            "b": definition.b,
            "c": definition.c,
        }
        return document

    if isinstance(definition, _definitions.PolynomialCharacteristicDefinition):
        document["coefficients"] = list(definition.coefficients)
        return document

    if isinstance(
        definition,
        _definitions.PiecewisePolynomialCharacteristicDefinition,
    ):
        curve = _curves.BUILTIN_RTD_CURVES[definition.characteristic_id]
        if not isinstance(curve, _curves.PiecewisePolynomialRTDCurve):
            raise TypeError(
                "Piecewise characteristic constructed with unexpected runtime "
                f"curve type: {definition.characteristic_id!r} -> "
                f"{type(curve).__name__}"
            )

        document.update(
            {
                "segments": [
                    {
                        "minimum_temperature_c": segment.minimum_temperature_c,
                        "maximum_temperature_c": segment.maximum_temperature_c,
                        "coefficients": list(segment.coefficients),
                        "temperature_origin_c": segment.temperature_origin_c,
                    }
                    for segment in definition.segments
                ],
                "continuity_adjustment_kind": ("additive_resistance_ratio_offset"),
                "maximum_continuity_adjustment_ratio": (
                    definition.maximum_continuity_adjustment_ratio
                ),
                "continuity_adjustment_reason": definition.continuity_adjustment_reason,
                "derived_continuity_adjustments": [
                    _json_number(adjustment)
                    for adjustment in curve.continuity_adjustments
                ],
            }
        )
        return document

    raise TypeError(
        "Unsupported built-in characteristic definition for conformance export: "
        f"{type(definition)!r}"
    )


def build_characteristic_catalog(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, object]:
    """Build the conformance-v1 characteristic catalog document."""
    producer_version = rtd_sensor_version or _project_version()
    return {
        "artifact_type": "characteristic_catalog",
        "format_version": _FORMAT_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "rtd_sensor_version": producer_version,
        "characteristics": [
            _characteristic_document(definition)
            for definition in _definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS.values()
        ],
    }


def build_model_catalog(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, object]:
    """Build the conformance-v1 built-in model catalog document."""
    producer_version = rtd_sensor_version or _project_version()
    models: list[dict[str, object]] = []

    for definition in _definitions.BUILTIN_MODEL_DEFINITIONS.values():
        characteristic = _definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS[
            definition.characteristic_id
        ]
        models.append(
            {
                "model_id": definition.model_id,
                "display_name": definition.display_name,
                "characteristic_id": definition.characteristic_id,
                "reference_resistance_ohms": definition.reference_resistance_ohms,
                "minimum_temperature_c": characteristic.minimum_temperature_c,
                "maximum_temperature_c": characteristic.maximum_temperature_c,
            }
        )

    return {
        "artifact_type": "model_catalog",
        "format_version": _FORMAT_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "rtd_sensor_version": producer_version,
        "models": models,
    }


def _fixture_document(
    fixture: _conformance_fixtures.ModelFixture,
) -> dict[str, object]:
    """Serialize one custom/calibrated model conformance fixture."""
    common: dict[str, object] = {
        "fixture_id": fixture.fixture_id,
        "display_name": fixture.display_name,
        "fixture_purpose": fixture.fixture_purpose,
        "expected_status": fixture.expected_status,
    }

    if isinstance(fixture, _conformance_fixtures.CharacteristicModelFixture):
        common.update(
            {
                "fixture_kind": "characteristic_model",
                "definition": {
                    "characteristic_id": fixture.characteristic_id,
                    "reference_resistance_ohms": fixture.reference_resistance_ohms,
                    "minimum_temperature_c": fixture.minimum_temperature_c,
                    "maximum_temperature_c": fixture.maximum_temperature_c,
                },
            }
        )
        return common

    if isinstance(fixture, _conformance_fixtures.CallendarVanDusenFixture):
        definition: dict[str, object] = {
            "reference_resistance_ohms": fixture.reference_resistance_ohms,
            "a": fixture.a,
            "b": fixture.b,
            "minimum_temperature_c": fixture.minimum_temperature_c,
            "maximum_temperature_c": fixture.maximum_temperature_c,
        }
        if fixture.c is not None:
            definition["c"] = fixture.c
        common.update(
            {
                "fixture_kind": "callendar_van_dusen",
                "definition": definition,
            }
        )
        return common

    if isinstance(fixture, _conformance_fixtures.PolynomialFixture):
        common.update(
            {
                "fixture_kind": "polynomial",
                "definition": {
                    "reference_resistance_ohms": fixture.reference_resistance_ohms,
                    "reference_temperature_c": fixture.reference_temperature_c,
                    "coefficients": list(fixture.coefficients),
                    "minimum_temperature_c": fixture.minimum_temperature_c,
                    "maximum_temperature_c": fixture.maximum_temperature_c,
                },
            }
        )
        return common

    if isinstance(fixture, _conformance_fixtures.PiecewisePolynomialFixture):
        common.update(
            {
                "fixture_kind": "piecewise_polynomial",
                "definition": {
                    "reference_resistance_ohms": fixture.reference_resistance_ohms,
                    "reference_temperature_c": fixture.reference_temperature_c,
                    "segments": [
                        {
                            "minimum_temperature_c": segment.minimum_temperature_c,
                            "maximum_temperature_c": segment.maximum_temperature_c,
                            "coefficients": list(segment.coefficients),
                            "temperature_origin_c": segment.temperature_origin_c,
                        }
                        for segment in fixture.segments
                    ],
                    "maximum_continuity_adjustment_ratio": (
                        fixture.maximum_continuity_adjustment_ratio
                    ),
                },
            }
        )
        if fixture.expected_status == "ok":
            model = _conformance_fixtures.build_fixture_model(fixture)
            if not isinstance(model, PiecewisePolynomialRTDModel):
                raise TypeError(
                    "Piecewise fixture constructed with unexpected model type: "
                    f"{fixture.fixture_id!r} -> {type(model).__name__}"
                )
            common["derived"] = {
                "continuity_adjustment_kind": "additive_resistance_ratio_offset",
                "continuity_adjustments": [
                    _json_number(adjustment)
                    for adjustment in model.continuity_adjustments
                ],
            }
        return common

    raise TypeError(
        f"Unsupported model fixture for conformance export: {type(fixture)!r}"
    )


def build_model_fixture_catalog(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, object]:
    """Build the conformance-v1 custom/calibrated model fixture catalog."""
    return {
        "artifact_type": "model_fixture_catalog",
        "format_version": _FORMAT_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "rtd_sensor_version": rtd_sensor_version or _project_version(),
        "fixtures": [
            _fixture_document(fixture)
            for fixture in _conformance_fixtures.MODEL_FIXTURES
        ],
    }


def _fixture_successful_expected(value: float) -> dict[str, object]:
    """Return one successful custom-fixture result for binary64 conformance."""
    return {
        "status": "ok",
        "value": _json_number(value),
        "acceptance": {
            "binary64_reference": {
                "absolute_tolerance": _BINARY64_ABSOLUTE_TOLERANCE,
            }
        },
    }


def _build_custom_conversion_vector_set(
    capability_id: str,
    *,
    rtd_sensor_version: str,
) -> dict[str, object]:
    """Build successful conversion vectors for valid custom-model fixtures."""
    if capability_id == "conversion.temperature_to_resistance":
        input_unit = "degree_celsius"
        output_unit = "ohm"
        operation_id = "temperature_to_resistance"
    elif capability_id == "conversion.resistance_to_temperature":
        input_unit = "ohm"
        output_unit = "degree_celsius"
        operation_id = "resistance_to_temperature"
    else:
        raise ValueError(f"Unsupported conformance capability: {capability_id!r}")

    test_groups: list[dict[str, object]] = []
    for fixture in _conformance_fixtures.MODEL_FIXTURES:
        if fixture.expected_status != "ok":
            continue
        model = _conformance_fixtures.build_fixture_model(fixture)
        cases: list[dict[str, object]] = []
        for anchor in fixture.anchors:
            resistance_ohms = model.celsius_to_resistance(anchor.temperature_c)
            token = _temperature_token(anchor.temperature_c)
            if capability_id == "conversion.temperature_to_resistance":
                input_document = {"value": _json_number(anchor.temperature_c)}
                expected = _fixture_successful_expected(resistance_ohms)
            else:
                input_document = {"value": _json_number(resistance_ohms)}
                expected = _fixture_successful_expected(anchor.temperature_c)

            tags = ["custom_fixture", "round_trip_anchor", *anchor.tags]
            cases.append(
                {
                    "case_id": f"{fixture.fixture_id}.{operation_id}.{token}",
                    "tags": list(dict.fromkeys(tags)),
                    "input": input_document,
                    "expected": expected,
                }
            )

        test_groups.append(
            {
                "group_id": f"{fixture.fixture_id}.{operation_id}",
                "fixture_id": fixture.fixture_id,
                "cases": cases,
            }
        )

    return {
        "artifact_type": "vector_set",
        "format_version": _FORMAT_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "rtd_sensor_version": rtd_sensor_version,
        "capability_id": capability_id,
        "input_unit": input_unit,
        "output_unit": output_unit,
        "test_groups": test_groups,
    }


def build_custom_temperature_to_resistance_vectors(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, object]:
    """Build valid custom-fixture temperature-to-resistance vectors."""
    return _build_custom_conversion_vector_set(
        "conversion.temperature_to_resistance",
        rtd_sensor_version=rtd_sensor_version or _project_version(),
    )


def build_custom_resistance_to_temperature_vectors(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, object]:
    """Build valid custom-fixture resistance-to-temperature vectors."""
    return _build_custom_conversion_vector_set(
        "conversion.resistance_to_temperature",
        rtd_sensor_version=rtd_sensor_version or _project_version(),
    )


def _vector_temperatures(
    definition: _definitions.CharacteristicDefinition,
) -> tuple[float, ...]:
    """Return deterministic valid-domain anchors for one characteristic."""
    if isinstance(
        definition,
        _definitions.PiecewisePolynomialCharacteristicDefinition,
    ):
        anchors = {
            definition.reference_temperature_c,
            definition.minimum_temperature_c,
            definition.maximum_temperature_c,
            definition.minimum_temperature_c + _BOUNDARY_TEMPERATURE_OFFSET_C,
            definition.maximum_temperature_c - _BOUNDARY_TEMPERATURE_OFFSET_C,
        }
        for segment in definition.segments:
            anchors.add(segment.minimum_temperature_c)
            anchors.add(segment.maximum_temperature_c)
            anchors.add(
                (segment.minimum_temperature_c + segment.maximum_temperature_c) / 2.0
            )
        return tuple(sorted(anchors))

    anchors = {
        definition.minimum_temperature_c,
        definition.maximum_temperature_c,
        definition.minimum_temperature_c + _BOUNDARY_TEMPERATURE_OFFSET_C,
        definition.maximum_temperature_c - _BOUNDARY_TEMPERATURE_OFFSET_C,
    }
    reference_temperature_c = definition.reference_temperature_c
    if (
        definition.minimum_temperature_c
        <= reference_temperature_c
        <= definition.maximum_temperature_c
    ):
        anchors.add(reference_temperature_c)
        if definition.minimum_temperature_c < reference_temperature_c:
            anchors.add(
                (definition.minimum_temperature_c + reference_temperature_c) / 2.0
            )
        if reference_temperature_c < definition.maximum_temperature_c:
            anchors.add(
                (reference_temperature_c + definition.maximum_temperature_c) / 2.0
            )
        for offset_c in (-0.001, 0.001):
            candidate = reference_temperature_c + offset_c
            if (
                definition.minimum_temperature_c
                <= candidate
                <= definition.maximum_temperature_c
            ):
                anchors.add(candidate)

    for representative_c in (25.0, 100.0):
        if (
            definition.minimum_temperature_c
            <= representative_c
            <= definition.maximum_temperature_c
        ):
            anchors.add(representative_c)

    return tuple(sorted(anchors))


def _temperature_token(temperature_c: float) -> str:
    """Return a stable identifier token for one finite Celsius anchor."""
    rendered = format(_json_number(temperature_c), ".15g")
    token = rendered.replace("-", "neg").replace(".", "p")
    return f"{token}c"


def _vector_tags(
    definition: _definitions.CharacteristicDefinition,
    temperature_c: float,
) -> list[str]:
    """Return deterministic descriptive tags for one conversion anchor."""
    tags = ["round_trip_anchor"]

    if temperature_c == definition.minimum_temperature_c:
        tags.append("minimum_boundary")
    if temperature_c == definition.maximum_temperature_c:
        tags.append("maximum_boundary")
    if temperature_c == (
        definition.minimum_temperature_c + _BOUNDARY_TEMPERATURE_OFFSET_C
    ):
        tags.extend(("inside_boundary", "minimum_boundary_neighbor"))
    if temperature_c == (
        definition.maximum_temperature_c - _BOUNDARY_TEMPERATURE_OFFSET_C
    ):
        tags.extend(("inside_boundary", "maximum_boundary_neighbor"))
    if temperature_c == definition.reference_temperature_c:
        tags.append("reference_temperature")

    if temperature_c < 0.0:
        tags.append("negative_temperature")
    elif temperature_c > 0.0:
        tags.append("positive_temperature")

    if isinstance(
        definition,
        _definitions.CallendarVanDusenCharacteristicDefinition,
    ):
        if temperature_c == definition.reference_temperature_c:
            tags.append("branch_boundary")
        elif abs(temperature_c - definition.reference_temperature_c) == 0.001:
            tags.append("branch_neighbor")

    if isinstance(
        definition,
        _definitions.PiecewisePolynomialCharacteristicDefinition,
    ):
        joins = {segment.maximum_temperature_c for segment in definition.segments[:-1]}
        midpoints = {
            (segment.minimum_temperature_c + segment.maximum_temperature_c) / 2.0
            for segment in definition.segments
        }
        if temperature_c in joins:
            tags.append("piecewise_join")
        elif temperature_c in midpoints:
            tags.append("piecewise_segment")

    if not any(
        tag
        in {
            "minimum_boundary",
            "maximum_boundary",
            "reference_temperature",
            "piecewise_join",
            "piecewise_segment",
        }
        for tag in tags
    ):
        tags.append("representative")

    return tags


def _successful_expected(
    value: float,
    *,
    binary32_absolute_tolerance: float,
) -> dict[str, object]:
    """Return one successful expected result with published acceptance profiles."""
    return {
        "status": "ok",
        "value": _json_number(value),
        "acceptance": {
            "binary64_reference": {
                "absolute_tolerance": _BINARY64_ABSOLUTE_TOLERANCE,
            },
            "binary32_compatible": {
                "absolute_tolerance": binary32_absolute_tolerance,
            },
        },
    }


def _build_conversion_vector_set(
    capability_id: str,
    *,
    rtd_sensor_version: str,
) -> dict[str, object]:
    """Build one valid-domain built-in conversion vector set."""
    if capability_id == "conversion.temperature_to_resistance":
        input_unit = "degree_celsius"
        output_unit = "ohm"
        operation_id = "temperature_to_resistance"
        binary32_tolerance = _BINARY32_FORWARD_ABSOLUTE_TOLERANCE
    elif capability_id == "conversion.resistance_to_temperature":
        input_unit = "ohm"
        output_unit = "degree_celsius"
        operation_id = "resistance_to_temperature"
        binary32_tolerance = _BINARY32_INVERSE_ABSOLUTE_TOLERANCE
    else:
        raise ValueError(f"Unsupported conformance capability: {capability_id!r}")

    test_groups: list[dict[str, object]] = []
    for model_definition in _definitions.BUILTIN_MODEL_DEFINITIONS.values():
        model = _models.BUILTIN_RTD_MODELS[model_definition.model_id]
        characteristic = _definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS[
            model_definition.characteristic_id
        ]
        cases: list[dict[str, object]] = []
        for temperature_c in _vector_temperatures(characteristic):
            resistance_ohms = model.celsius_to_resistance(temperature_c)
            token = _temperature_token(temperature_c)
            if capability_id == "conversion.temperature_to_resistance":
                input_document = {"value": _json_number(temperature_c)}
                expected = _successful_expected(
                    resistance_ohms,
                    binary32_absolute_tolerance=binary32_tolerance,
                )
            else:
                input_document = {"value": _json_number(resistance_ohms)}
                expected = _successful_expected(
                    temperature_c,
                    binary32_absolute_tolerance=binary32_tolerance,
                )

            cases.append(
                {
                    "case_id": f"{model_definition.model_id}.{operation_id}.{token}",
                    "tags": _vector_tags(characteristic, temperature_c),
                    "input": input_document,
                    "expected": expected,
                }
            )

        test_groups.append(
            {
                "group_id": f"{model_definition.model_id}.{operation_id}",
                "model_id": model_definition.model_id,
                "cases": cases,
            }
        )

    return {
        "artifact_type": "vector_set",
        "format_version": _FORMAT_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "rtd_sensor_version": rtd_sensor_version,
        "capability_id": capability_id,
        "input_unit": input_unit,
        "output_unit": output_unit,
        "test_groups": test_groups,
    }


def build_temperature_to_resistance_vectors(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, object]:
    """Build valid-domain binary64 temperature-to-resistance vectors."""
    return _build_conversion_vector_set(
        "conversion.temperature_to_resistance",
        rtd_sensor_version=rtd_sensor_version or _project_version(),
    )


def build_resistance_to_temperature_vectors(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, object]:
    """Build valid-domain binary64 resistance-to-temperature vectors."""
    return _build_conversion_vector_set(
        "conversion.resistance_to_temperature",
        rtd_sensor_version=rtd_sensor_version or _project_version(),
    )


def _status_case(
    *,
    case_id: str,
    tags: Sequence[str],
    input_document: dict[str, object],
    status: str,
) -> dict[str, object]:
    """Return one language-neutral non-success conversion case."""
    return {
        "case_id": case_id,
        "tags": list(tags),
        "input": input_document,
        "expected": {"status": status},
    }


def _build_status_vector_set(
    capability_id: str,
    *,
    rtd_sensor_version: str,
) -> dict[str, object]:
    """Build explicit built-in range and invalid-input status vectors."""
    if capability_id == "conversion.temperature_to_resistance":
        input_unit = "degree_celsius"
        output_unit = "ohm"
        operation_id = "temperature_to_resistance_status"
    elif capability_id == "conversion.resistance_to_temperature":
        input_unit = "ohm"
        output_unit = "degree_celsius"
        operation_id = "resistance_to_temperature_status"
    else:
        raise ValueError(f"Unsupported conformance capability: {capability_id!r}")

    test_groups: list[dict[str, object]] = []
    for model_definition in _definitions.BUILTIN_MODEL_DEFINITIONS.values():
        model = _models.BUILTIN_RTD_MODELS[model_definition.model_id]
        prefix = f"{model_definition.model_id}.{operation_id}"

        if capability_id == "conversion.temperature_to_resistance":
            cases = [
                _status_case(
                    case_id=f"{prefix}.below_minimum",
                    tags=("range_error", "outside_boundary", "below_minimum"),
                    input_document={
                        "value": _json_number(
                            model.minimum_temperature_c - _BOUNDARY_TEMPERATURE_OFFSET_C
                        )
                    },
                    status="out_of_range_low",
                ),
                _status_case(
                    case_id=f"{prefix}.above_maximum",
                    tags=("range_error", "outside_boundary", "above_maximum"),
                    input_document={
                        "value": _json_number(
                            model.maximum_temperature_c + _BOUNDARY_TEMPERATURE_OFFSET_C
                        )
                    },
                    status="out_of_range_high",
                ),
            ]
        else:
            minimum_resistance = model.celsius_to_resistance(
                model.minimum_temperature_c
            )
            maximum_resistance = model.celsius_to_resistance(
                model.maximum_temperature_c
            )
            if minimum_resistance <= _BOUNDARY_RESISTANCE_OFFSET_OHMS:
                raise RuntimeError(
                    "Built-in minimum resistance is too small for the configured "
                    "out-of-range conformance offset"
                )
            cases = [
                _status_case(
                    case_id=f"{prefix}.below_minimum",
                    tags=("range_error", "outside_boundary", "below_minimum"),
                    input_document={
                        "value": _json_number(
                            minimum_resistance - _BOUNDARY_RESISTANCE_OFFSET_OHMS
                        )
                    },
                    status="out_of_range_low",
                ),
                _status_case(
                    case_id=f"{prefix}.above_maximum",
                    tags=("range_error", "outside_boundary", "above_maximum"),
                    input_document={
                        "value": _json_number(
                            maximum_resistance + _BOUNDARY_RESISTANCE_OFFSET_OHMS
                        )
                    },
                    status="out_of_range_high",
                ),
                _status_case(
                    case_id=f"{prefix}.zero_resistance",
                    tags=("invalid_input", "nonpositive_resistance"),
                    input_document={"value": 0.0},
                    status="invalid_input",
                ),
                _status_case(
                    case_id=f"{prefix}.negative_resistance",
                    tags=("invalid_input", "nonpositive_resistance"),
                    input_document={"value": -1.0},
                    status="invalid_input",
                ),
            ]

        for special in ("nan", "positive_infinity", "negative_infinity"):
            cases.append(
                _status_case(
                    case_id=f"{prefix}.{special}",
                    tags=("invalid_input", "non_finite"),
                    input_document={"special": special},
                    status="invalid_input",
                )
            )

        test_groups.append(
            {
                "group_id": prefix,
                "model_id": model_definition.model_id,
                "cases": cases,
            }
        )

    return {
        "artifact_type": "vector_set",
        "format_version": _FORMAT_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "rtd_sensor_version": rtd_sensor_version,
        "capability_id": capability_id,
        "input_unit": input_unit,
        "output_unit": output_unit,
        "test_groups": test_groups,
    }


def build_temperature_to_resistance_status_vectors(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, object]:
    """Build built-in temperature-input range and invalid-input status vectors."""
    return _build_status_vector_set(
        "conversion.temperature_to_resistance",
        rtd_sensor_version=rtd_sensor_version or _project_version(),
    )


def build_resistance_to_temperature_status_vectors(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, object]:
    """Build built-in resistance-input range and invalid-input status vectors."""
    return _build_status_vector_set(
        "conversion.resistance_to_temperature",
        rtd_sensor_version=rtd_sensor_version or _project_version(),
    )


def _build_custom_status_vector_set(
    capability_id: str,
    *,
    rtd_sensor_version: str,
) -> dict[str, object]:
    """Build range and invalid-input status vectors for valid custom fixtures."""
    if capability_id == "conversion.temperature_to_resistance":
        input_unit = "degree_celsius"
        output_unit = "ohm"
        operation_id = "temperature_to_resistance_status"
    elif capability_id == "conversion.resistance_to_temperature":
        input_unit = "ohm"
        output_unit = "degree_celsius"
        operation_id = "resistance_to_temperature_status"
    else:
        raise ValueError(f"Unsupported conformance capability: {capability_id!r}")

    test_groups: list[dict[str, object]] = []
    for fixture in _conformance_fixtures.MODEL_FIXTURES:
        if fixture.expected_status != "ok":
            continue
        model = _conformance_fixtures.build_fixture_model(fixture)
        prefix = f"{fixture.fixture_id}.{operation_id}"

        if capability_id == "conversion.temperature_to_resistance":
            cases = [
                _status_case(
                    case_id=f"{prefix}.below_minimum",
                    tags=("range_error", "outside_boundary", "below_minimum"),
                    input_document={
                        "value": _json_number(
                            model.minimum_temperature_c - _BOUNDARY_TEMPERATURE_OFFSET_C
                        )
                    },
                    status="out_of_range_low",
                ),
                _status_case(
                    case_id=f"{prefix}.above_maximum",
                    tags=("range_error", "outside_boundary", "above_maximum"),
                    input_document={
                        "value": _json_number(
                            model.maximum_temperature_c + _BOUNDARY_TEMPERATURE_OFFSET_C
                        )
                    },
                    status="out_of_range_high",
                ),
            ]
            if isinstance(
                fixture, _conformance_fixtures.CallendarVanDusenFixture
            ) and not (
                fixture.minimum_temperature_c <= 0.0 <= fixture.maximum_temperature_c
            ):
                status = (
                    "out_of_range_low"
                    if fixture.minimum_temperature_c > 0.0
                    else "out_of_range_high"
                )
                cases.append(
                    _status_case(
                        case_id=f"{prefix}.excluded_reference_temperature",
                        tags=(
                            "range_error",
                            "declared_range",
                            "excluded_reference_temperature",
                        ),
                        input_document={"value": 0.0},
                        status=status,
                    )
                )
        else:
            minimum_resistance = model.celsius_to_resistance(
                model.minimum_temperature_c
            )
            maximum_resistance = model.celsius_to_resistance(
                model.maximum_temperature_c
            )
            if minimum_resistance <= _BOUNDARY_RESISTANCE_OFFSET_OHMS:
                raise RuntimeError(
                    "Custom fixture minimum resistance is too small for the "
                    "configured out-of-range conformance offset"
                )
            cases = [
                _status_case(
                    case_id=f"{prefix}.below_minimum",
                    tags=("range_error", "outside_boundary", "below_minimum"),
                    input_document={
                        "value": _json_number(
                            minimum_resistance - _BOUNDARY_RESISTANCE_OFFSET_OHMS
                        )
                    },
                    status="out_of_range_low",
                ),
                _status_case(
                    case_id=f"{prefix}.above_maximum",
                    tags=("range_error", "outside_boundary", "above_maximum"),
                    input_document={
                        "value": _json_number(
                            maximum_resistance + _BOUNDARY_RESISTANCE_OFFSET_OHMS
                        )
                    },
                    status="out_of_range_high",
                ),
                _status_case(
                    case_id=f"{prefix}.zero_resistance",
                    tags=("invalid_input", "nonpositive_resistance"),
                    input_document={"value": 0.0},
                    status="invalid_input",
                ),
                _status_case(
                    case_id=f"{prefix}.negative_resistance",
                    tags=("invalid_input", "nonpositive_resistance"),
                    input_document={"value": -1.0},
                    status="invalid_input",
                ),
            ]

        for special in ("nan", "positive_infinity", "negative_infinity"):
            cases.append(
                _status_case(
                    case_id=f"{prefix}.{special}",
                    tags=("invalid_input", "non_finite"),
                    input_document={"special": special},
                    status="invalid_input",
                )
            )

        test_groups.append(
            {
                "group_id": prefix,
                "fixture_id": fixture.fixture_id,
                "cases": cases,
            }
        )

    return {
        "artifact_type": "vector_set",
        "format_version": _FORMAT_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "rtd_sensor_version": rtd_sensor_version,
        "capability_id": capability_id,
        "input_unit": input_unit,
        "output_unit": output_unit,
        "test_groups": test_groups,
    }


def build_custom_temperature_to_resistance_status_vectors(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, object]:
    """Build custom-fixture temperature-input status vectors."""
    return _build_custom_status_vector_set(
        "conversion.temperature_to_resistance",
        rtd_sensor_version=rtd_sensor_version or _project_version(),
    )


def build_custom_resistance_to_temperature_status_vectors(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, object]:
    """Build custom-fixture resistance-input status vectors."""
    return _build_custom_status_vector_set(
        "conversion.resistance_to_temperature",
        rtd_sensor_version=rtd_sensor_version or _project_version(),
    )


def render_json(document: object) -> str:
    """Return one deterministic, standards-compliant JSON artifact."""
    return (
        json.dumps(
            document,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _generated_payload_artifacts(
    *,
    rtd_sensor_version: str,
) -> dict[str, str]:
    """Return generated catalogs and vectors, excluding the release manifest."""
    producer_version = rtd_sensor_version
    return {
        _CHARACTERISTICS_FILENAME: render_json(
            build_characteristic_catalog(rtd_sensor_version=producer_version)
        ),
        _MODELS_FILENAME: render_json(
            build_model_catalog(rtd_sensor_version=producer_version)
        ),
        _MODEL_FIXTURES_FILENAME: render_json(
            build_model_fixture_catalog(rtd_sensor_version=producer_version)
        ),
        _CUSTOM_TEMPERATURE_TO_RESISTANCE_FILENAME: render_json(
            build_custom_temperature_to_resistance_vectors(
                rtd_sensor_version=producer_version
            )
        ),
        _CUSTOM_RESISTANCE_TO_TEMPERATURE_FILENAME: render_json(
            build_custom_resistance_to_temperature_vectors(
                rtd_sensor_version=producer_version
            )
        ),
        _CUSTOM_TEMPERATURE_TO_RESISTANCE_STATUS_FILENAME: render_json(
            build_custom_temperature_to_resistance_status_vectors(
                rtd_sensor_version=producer_version
            )
        ),
        _CUSTOM_RESISTANCE_TO_TEMPERATURE_STATUS_FILENAME: render_json(
            build_custom_resistance_to_temperature_status_vectors(
                rtd_sensor_version=producer_version
            )
        ),
        _TEMPERATURE_TO_RESISTANCE_FILENAME: render_json(
            build_temperature_to_resistance_vectors(rtd_sensor_version=producer_version)
        ),
        _RESISTANCE_TO_TEMPERATURE_FILENAME: render_json(
            build_resistance_to_temperature_vectors(rtd_sensor_version=producer_version)
        ),
        _TEMPERATURE_TO_RESISTANCE_STATUS_FILENAME: render_json(
            build_temperature_to_resistance_status_vectors(
                rtd_sensor_version=producer_version
            )
        ),
        _RESISTANCE_TO_TEMPERATURE_STATUS_FILENAME: render_json(
            build_resistance_to_temperature_status_vectors(
                rtd_sensor_version=producer_version
            )
        ),
    }


def _repository_conformance_dir() -> Path:
    """Return the repository's committed conformance-v1 directory."""
    return Path(__file__).resolve().parents[2] / "conformance" / "v1"


def _static_release_json_artifacts() -> dict[str, str]:
    """Return committed non-generated JSON files included in a release bundle."""
    root = _repository_conformance_dir()
    generated_names = {
        _CHARACTERISTICS_FILENAME,
        _MODELS_FILENAME,
        _MODEL_FIXTURES_FILENAME,
        _CUSTOM_TEMPERATURE_TO_RESISTANCE_FILENAME,
        _CUSTOM_RESISTANCE_TO_TEMPERATURE_FILENAME,
        _CUSTOM_TEMPERATURE_TO_RESISTANCE_STATUS_FILENAME,
        _CUSTOM_RESISTANCE_TO_TEMPERATURE_STATUS_FILENAME,
        _TEMPERATURE_TO_RESISTANCE_FILENAME,
        _RESISTANCE_TO_TEMPERATURE_FILENAME,
        _TEMPERATURE_TO_RESISTANCE_STATUS_FILENAME,
        _RESISTANCE_TO_TEMPERATURE_STATUS_FILENAME,
        _MANIFEST_FILENAME,
    }
    artifacts: dict[str, str] = {}
    for path in sorted(root.rglob("*.json")):
        relative_path = path.relative_to(root).as_posix()
        if relative_path in generated_names:
            continue
        artifacts[relative_path] = path.read_text(encoding="utf-8")
    return artifacts


def _manifest_file_entry(path: str, content: str) -> dict[str, object]:
    encoded = content.encode("utf-8")
    return {
        "path": path,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "size_bytes": len(encoded),
    }


def build_release_manifest(
    *,
    rtd_sensor_version: str | None = None,
    payload_artifacts: dict[str, str] | None = None,
) -> dict[str, object]:
    """Build the deterministic manifest for the machine-readable v1 bundle."""
    producer_version = rtd_sensor_version or _project_version()
    payload = (
        payload_artifacts
        if payload_artifacts is not None
        else _generated_payload_artifacts(rtd_sensor_version=producer_version)
    )
    release_files = {**_static_release_json_artifacts(), **payload}
    return {
        "artifact_type": "conformance_manifest",
        "format_version": _FORMAT_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "contract_status": _CONTRACT_STATUS,
        "rtd_sensor_version": producer_version,
        "files": [
            _manifest_file_entry(path, release_files[path])
            for path in sorted(release_files)
        ],
    }


def generated_artifacts(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, str]:
    """Return every generated artifact path and deterministic content."""
    producer_version = rtd_sensor_version or _project_version()
    payload = _generated_payload_artifacts(rtd_sensor_version=producer_version)
    return {
        **payload,
        _MANIFEST_FILENAME: render_json(
            build_release_manifest(
                rtd_sensor_version=producer_version,
                payload_artifacts=payload,
            )
        ),
    }


def write_generated_artifacts(
    output_dir: Path,
    *,
    rtd_sensor_version: str | None = None,
) -> None:
    """Write deterministic conformance artifacts below ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in generated_artifacts(
        rtd_sensor_version=rtd_sensor_version
    ).items():
        path = output_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")


def stale_generated_artifacts(
    output_dir: Path,
    *,
    rtd_sensor_version: str | None = None,
) -> tuple[str, ...]:
    """Return generated artifact names that are missing or differ on disk."""
    stale: list[str] = []
    for filename, expected in generated_artifacts(
        rtd_sensor_version=rtd_sensor_version
    ).items():
        path = output_dir / filename
        try:
            actual = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            stale.append(filename)
            continue
        if actual != expected:
            stale.append(filename)
    return tuple(stale)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate rtd-sensor language-neutral conformance artifacts."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("conformance/v1"),
        help="Directory containing the generated conformance artifacts.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check committed artifacts for drift instead of writing them.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the conformance artifact generator command-line interface."""
    arguments = _parser().parse_args(argv)
    if arguments.check:
        stale = stale_generated_artifacts(arguments.output_dir)
        if stale:
            print("Conformance artifacts are stale: " + ", ".join(stale))
            return 1
        return 0

    write_generated_artifacts(arguments.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
