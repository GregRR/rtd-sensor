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
import json
import tomllib
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from . import _curves, _definitions, _models

_FORMAT_VERSION = 1
_CONTRACT_VERSION = 1
_DISTRIBUTION_NAME = "rtd-sensor"
_CHARACTERISTICS_FILENAME = "characteristics.json"
_MODELS_FILENAME = "models.json"
_TEMPERATURE_TO_RESISTANCE_FILENAME = "vectors/builtin-temperature-to-resistance.json"
_RESISTANCE_TO_TEMPERATURE_FILENAME = "vectors/builtin-resistance-to-temperature.json"
_BINARY64_ABSOLUTE_TOLERANCE = 1.0e-9


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


def _successful_expected(value: float) -> dict[str, object]:
    """Return one successful binary64-reference expected result."""
    return {
        "status": "ok",
        "value": _json_number(value),
        "acceptance": {
            "binary64_reference": {
                "absolute_tolerance": _BINARY64_ABSOLUTE_TOLERANCE,
            }
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
    elif capability_id == "conversion.resistance_to_temperature":
        input_unit = "ohm"
        output_unit = "degree_celsius"
        operation_id = "resistance_to_temperature"
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
                expected = _successful_expected(resistance_ohms)
            else:
                input_document = {"value": _json_number(resistance_ohms)}
                expected = _successful_expected(temperature_c)

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


def generated_artifacts(
    *,
    rtd_sensor_version: str | None = None,
) -> dict[str, str]:
    """Return every generated artifact path and deterministic content."""
    producer_version = rtd_sensor_version or _project_version()
    return {
        _CHARACTERISTICS_FILENAME: render_json(
            build_characteristic_catalog(rtd_sensor_version=producer_version)
        ),
        _MODELS_FILENAME: render_json(
            build_model_catalog(rtd_sensor_version=producer_version)
        ),
        _TEMPERATURE_TO_RESISTANCE_FILENAME: render_json(
            build_temperature_to_resistance_vectors(rtd_sensor_version=producer_version)
        ),
        _RESISTANCE_TO_TEMPERATURE_FILENAME: render_json(
            build_resistance_to_temperature_vectors(rtd_sensor_version=producer_version)
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
