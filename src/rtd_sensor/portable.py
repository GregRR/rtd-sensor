# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Portable, language-neutral RTD model definitions.

The portable format is intentionally separate from the stable conformance
fixture catalog.  It contains only valid reconstructable model definitions and
uses its own ``format_version``.  Fit evidence, physical probe identity, and
hardware configuration are not part of the numerical definition.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypeAlias

from .exceptions import InvalidPortableModelDefinitionError, InvalidRTDModelError
from .models import (
    CallendarVanDusenRTDModel,
    IEC60751RTDModel,
    PiecewisePolynomialRTDModel,
    PiecewisePolynomialSegment,
    PolynomialRTDModel,
)

__all__ = [
    "PortableModelDefinition",
    "PortableRTDModel",
    "model_from_portable_definition",
    "model_to_portable_definition",
]

_PORTABLE_ARTIFACT_TYPE = "portable_model_definition"
_PORTABLE_FORMAT_VERSION = 1
_IEC60751_PT385_CHARACTERISTIC_ID = "iec60751_pt385"
_PIECEWISE_CONTINUITY_KIND = "additive_resistance_ratio_offset"

PortableRTDModel: TypeAlias = (
    IEC60751RTDModel
    | CallendarVanDusenRTDModel
    | PolynomialRTDModel
    | PiecewisePolynomialRTDModel
)


@dataclass(frozen=True, slots=True)
class PortableModelDefinition:
    """A reconstructed portable model plus preserved non-behavioral metadata.

    ``metadata`` is preserved as JSON-compatible data but is never interpreted
    as part of RTD conversion behavior.  The reconstructed model is always
    created from the schema-defined numerical ``definition`` only.
    """

    model: PortableRTDModel
    metadata: dict[str, object]


def model_to_portable_definition(
    model: PortableRTDModel,
    *,
    metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return a JSON-compatible portable definition for a supported model.

    Human-readable model names and implementation-specific provenance fields
    are not copied automatically into ``metadata``.  Callers may provide
    application-neutral provenance explicitly when it should travel with the
    numerical definition.
    """

    model_kind, definition = _definition_from_model(model)
    artifact: dict[str, object] = {
        "artifact_type": _PORTABLE_ARTIFACT_TYPE,
        "format_version": _PORTABLE_FORMAT_VERSION,
        "model_kind": model_kind,
        "definition": definition,
    }
    if metadata is not None:
        artifact["metadata"] = _normalize_metadata(metadata)
    return artifact


def model_from_portable_definition(
    artifact: Mapping[str, object],
) -> PortableModelDefinition:
    """Validate and reconstruct a model from a portable definition artifact."""

    if not isinstance(artifact, Mapping):
        raise TypeError("Portable model definition must be a mapping")

    _require_exact_keys(
        artifact,
        required={"artifact_type", "format_version", "model_kind", "definition"},
        optional={"metadata"},
        context="Portable model definition",
    )

    artifact_type = artifact["artifact_type"]
    if artifact_type != _PORTABLE_ARTIFACT_TYPE:
        raise InvalidPortableModelDefinitionError(
            f"Unsupported portable artifact_type: {artifact_type!r}"
        )

    format_version = artifact["format_version"]
    if isinstance(format_version, bool) or not isinstance(format_version, int | float):
        raise InvalidPortableModelDefinitionError(
            "Portable format_version must be an integer"
        )
    numeric_format_version = float(format_version)
    if (
        not math.isfinite(numeric_format_version)
        or not numeric_format_version.is_integer()
    ):
        raise InvalidPortableModelDefinitionError(
            "Portable format_version must be an integer"
        )
    normalized_format_version = int(numeric_format_version)
    if normalized_format_version != _PORTABLE_FORMAT_VERSION:
        raise InvalidPortableModelDefinitionError(
            f"Unsupported portable format_version: {format_version}"
        )

    model_kind = artifact["model_kind"]
    if not isinstance(model_kind, str):
        raise InvalidPortableModelDefinitionError(
            "Portable model_kind must be a string"
        )

    raw_definition = artifact["definition"]
    if not isinstance(raw_definition, Mapping):
        raise InvalidPortableModelDefinitionError(
            "Portable model definition field must be an object"
        )

    raw_metadata = artifact.get("metadata", {})
    if not isinstance(raw_metadata, Mapping):
        raise InvalidPortableModelDefinitionError("Portable metadata must be an object")
    metadata = _normalize_metadata(raw_metadata)

    try:
        model = _model_from_definition(model_kind, raw_definition)
    except InvalidRTDModelError as error:
        raise InvalidPortableModelDefinitionError(
            f"Portable model definition is scientifically invalid: {error}"
        ) from error

    return PortableModelDefinition(model=model, metadata=metadata)


def _definition_from_model(model: PortableRTDModel) -> tuple[str, dict[str, object]]:
    if isinstance(model, IEC60751RTDModel):
        return (
            "characteristic_model",
            {
                "characteristic_id": _IEC60751_PT385_CHARACTERISTIC_ID,
                "reference_resistance_ohms": model.r0_ohms,
                "minimum_temperature_c": model.minimum_temperature_c,
                "maximum_temperature_c": model.maximum_temperature_c,
            },
        )

    if isinstance(model, CallendarVanDusenRTDModel):
        definition: dict[str, object] = {
            "reference_resistance_ohms": model.r0_ohms,
            "a": model.a,
            "b": model.b,
            "minimum_temperature_c": model.minimum_temperature_c,
            "maximum_temperature_c": model.maximum_temperature_c,
        }
        if model.c is not None:
            definition["c"] = model.c
        return "callendar_van_dusen", definition

    if isinstance(model, PolynomialRTDModel):
        return (
            "polynomial",
            {
                "reference_resistance_ohms": model.reference_resistance_ohms,
                "reference_temperature_c": model.reference_temperature_c,
                "coefficients": list(model.coefficients),
                "minimum_temperature_c": model.minimum_temperature_c,
                "maximum_temperature_c": model.maximum_temperature_c,
            },
        )

    if isinstance(model, PiecewisePolynomialRTDModel):
        return (
            "piecewise_polynomial",
            {
                "reference_resistance_ohms": model.reference_resistance_ohms,
                "reference_temperature_c": model.reference_temperature_c,
                "segments": [
                    {
                        "minimum_temperature_c": segment.minimum_temperature_c,
                        "maximum_temperature_c": segment.maximum_temperature_c,
                        "coefficients": list(segment.coefficients),
                        "temperature_origin_c": segment.temperature_origin_c,
                    }
                    for segment in model.segments
                ],
                "continuity_adjustment_kind": _PIECEWISE_CONTINUITY_KIND,
                "maximum_continuity_adjustment_ratio": (
                    model.maximum_continuity_adjustment_ratio
                ),
            },
        )

    raise TypeError(
        "Portable model definitions support IEC60751RTDModel, "
        "CallendarVanDusenRTDModel, PolynomialRTDModel, and "
        "PiecewisePolynomialRTDModel"
    )


def _model_from_definition(
    model_kind: str,
    definition: Mapping[str, object],
) -> PortableRTDModel:
    match model_kind:
        case "characteristic_model":
            return _characteristic_model_from_definition(definition)
        case "callendar_van_dusen":
            return _cvd_model_from_definition(definition)
        case "polynomial":
            return _polynomial_model_from_definition(definition)
        case "piecewise_polynomial":
            return _piecewise_model_from_definition(definition)
        case _:
            raise InvalidPortableModelDefinitionError(
                f"Unsupported portable model_kind: {model_kind!r}"
            )


def _characteristic_model_from_definition(
    definition: Mapping[str, object],
) -> IEC60751RTDModel:
    _require_exact_keys(
        definition,
        required={
            "characteristic_id",
            "reference_resistance_ohms",
            "minimum_temperature_c",
            "maximum_temperature_c",
        },
        context="Characteristic-model definition",
    )
    characteristic_id = definition["characteristic_id"]
    if characteristic_id != _IEC60751_PT385_CHARACTERISTIC_ID:
        raise InvalidPortableModelDefinitionError(
            f"Unsupported portable characteristic_id: {characteristic_id!r}"
        )
    return IEC60751RTDModel(
        r0_ohms=_number(definition, "reference_resistance_ohms"),
        minimum_temperature_c=_number(definition, "minimum_temperature_c"),
        maximum_temperature_c=_number(definition, "maximum_temperature_c"),
    )


def _cvd_model_from_definition(
    definition: Mapping[str, object],
) -> CallendarVanDusenRTDModel:
    _require_exact_keys(
        definition,
        required={
            "reference_resistance_ohms",
            "a",
            "b",
            "minimum_temperature_c",
            "maximum_temperature_c",
        },
        optional={"c"},
        context="Callendar-Van Dusen definition",
    )
    c = _optional_number(definition, "c")
    return CallendarVanDusenRTDModel(
        r0_ohms=_number(definition, "reference_resistance_ohms"),
        a=_number(definition, "a"),
        b=_number(definition, "b"),
        c=c,
        minimum_temperature_c=_number(definition, "minimum_temperature_c"),
        maximum_temperature_c=_number(definition, "maximum_temperature_c"),
    )


def _polynomial_model_from_definition(
    definition: Mapping[str, object],
) -> PolynomialRTDModel:
    _require_exact_keys(
        definition,
        required={
            "reference_resistance_ohms",
            "reference_temperature_c",
            "coefficients",
            "minimum_temperature_c",
            "maximum_temperature_c",
        },
        context="Polynomial definition",
    )
    return PolynomialRTDModel(
        reference_resistance_ohms=_number(definition, "reference_resistance_ohms"),
        reference_temperature_c=_number(definition, "reference_temperature_c"),
        coefficients=_number_sequence(definition, "coefficients"),
        minimum_temperature_c=_number(definition, "minimum_temperature_c"),
        maximum_temperature_c=_number(definition, "maximum_temperature_c"),
    )


def _piecewise_model_from_definition(
    definition: Mapping[str, object],
) -> PiecewisePolynomialRTDModel:
    _require_exact_keys(
        definition,
        required={
            "reference_resistance_ohms",
            "reference_temperature_c",
            "segments",
            "continuity_adjustment_kind",
            "maximum_continuity_adjustment_ratio",
        },
        context="Piecewise-polynomial definition",
    )
    continuity_kind = definition["continuity_adjustment_kind"]
    if continuity_kind != _PIECEWISE_CONTINUITY_KIND:
        raise InvalidPortableModelDefinitionError(
            f"Unsupported piecewise continuity_adjustment_kind: {continuity_kind!r}"
        )

    raw_segments = definition["segments"]
    if not isinstance(raw_segments, Sequence) or isinstance(
        raw_segments, (str, bytes, bytearray)
    ):
        raise InvalidPortableModelDefinitionError("Piecewise segments must be an array")

    segments: list[PiecewisePolynomialSegment] = []
    for index, raw_segment in enumerate(raw_segments):
        if not isinstance(raw_segment, Mapping):
            raise InvalidPortableModelDefinitionError(
                f"Piecewise segment {index} must be an object"
            )
        _require_exact_keys(
            raw_segment,
            required={
                "minimum_temperature_c",
                "maximum_temperature_c",
                "coefficients",
                "temperature_origin_c",
            },
            context=f"Piecewise segment {index}",
        )
        segments.append(
            PiecewisePolynomialSegment(
                minimum_temperature_c=_number(raw_segment, "minimum_temperature_c"),
                maximum_temperature_c=_number(raw_segment, "maximum_temperature_c"),
                coefficients=_number_sequence(raw_segment, "coefficients"),
                temperature_origin_c=_number(raw_segment, "temperature_origin_c"),
            )
        )

    return PiecewisePolynomialRTDModel(
        reference_resistance_ohms=_number(definition, "reference_resistance_ohms"),
        reference_temperature_c=_number(definition, "reference_temperature_c"),
        segments=segments,
        maximum_continuity_adjustment_ratio=_number(
            definition, "maximum_continuity_adjustment_ratio"
        ),
    )


def _require_exact_keys(
    value: Mapping[str, object],
    *,
    required: set[str],
    optional: set[str] | None = None,
    context: str,
) -> None:
    optional = set() if optional is None else optional
    non_string_keys = [key for key in value if not isinstance(key, str)]
    if non_string_keys:
        raise InvalidPortableModelDefinitionError(
            f"{context} object keys must be strings"
        )
    keys = set(value)
    missing = required - keys
    if missing:
        names = ", ".join(sorted(missing))
        raise InvalidPortableModelDefinitionError(
            f"{context} is missing required field(s): {names}"
        )
    unexpected = keys - required - optional
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise InvalidPortableModelDefinitionError(
            f"{context} contains unsupported field(s): {names}"
        )


def _number(value: Mapping[str, object], key: str) -> float:
    raw = value[key]
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        raise InvalidPortableModelDefinitionError(f"{key} must be a JSON number")
    converted = float(raw)
    if not math.isfinite(converted):
        raise InvalidPortableModelDefinitionError(f"{key} must be finite")
    return converted


def _optional_number(value: Mapping[str, object], key: str) -> float | None:
    if key not in value:
        return None
    return _number(value, key)


def _number_sequence(value: Mapping[str, object], key: str) -> tuple[float, ...]:
    raw = value[key]
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        raise InvalidPortableModelDefinitionError(f"{key} must be a JSON array")
    converted: list[float] = []
    for index, item in enumerate(raw):
        if isinstance(item, bool) or not isinstance(item, int | float):
            raise InvalidPortableModelDefinitionError(
                f"{key}[{index}] must be a JSON number"
            )
        number = float(item)
        if not math.isfinite(number):
            raise InvalidPortableModelDefinitionError(f"{key}[{index}] must be finite")
        converted.append(number)
    return tuple(converted)


def _normalize_metadata(value: Mapping[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise InvalidPortableModelDefinitionError(
                "Portable metadata object keys must be strings"
            )
        normalized[key] = _normalize_json_value(item, path=f"metadata.{key}")
    return normalized


def _normalize_json_value(value: object, *, path: str) -> object:
    if value is None or isinstance(value, bool | str | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidPortableModelDefinitionError(f"{path} must be finite")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise InvalidPortableModelDefinitionError(
                    f"{path} object keys must be strings"
                )
            normalized[key] = _normalize_json_value(item, path=f"{path}.{key}")
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            _normalize_json_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise InvalidPortableModelDefinitionError(
        f"{path} contains a value that is not JSON-compatible"
    )
