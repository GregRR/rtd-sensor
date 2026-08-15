# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Read-only discovery for verified built-in RTD models.

The catalog is a public view over the package's authoritative built-in model
and characteristic definitions. It does not maintain a second scientific
registry and intentionally provides no registration API for user-defined
models.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

from . import _definitions, _models
from ._protocols import RTDModel as _RTDModel

__all__ = [
    "BuiltinRTDModelInfo",
    "RTDSourceReference",
    "get_model",
    "model_info",
    "supported_models",
]


@dataclass(frozen=True, slots=True, kw_only=True)
class RTDSourceReference:
    """Public immutable provenance reference for an RTD characteristic."""

    citation: str
    url: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class BuiltinRTDModelInfo:
    """Immutable application-facing metadata for one built-in RTD model.

    The descriptor separates canonical model identity from characteristic
    identity. Multiple models may share one characteristic while differing in
    reference resistance, as Pt100, Pt500, and Pt1000 do for IEC 60751 PT-385.
    """

    model_id: str
    display_name: str
    characteristic_id: str
    characteristic_display_name: str
    material: Literal["platinum", "nickel"]
    curve_kind: Literal[
        "callendar_van_dusen",
        "polynomial",
        "piecewise_polynomial",
    ]
    reference_resistance_ohms: float
    reference_temperature_c: float
    minimum_temperature_c: float
    maximum_temperature_c: float
    source_references: tuple[RTDSourceReference, ...]


@dataclass(frozen=True, slots=True, repr=False, eq=False, kw_only=True)
class _BuiltinRTDModelAdapter:
    """Expose only the public numerical behavior of one built-in model.

    The package-owned runtime model remains private implementation detail. The
    adapter deliberately omits identity, range, curve, coefficient, and
    reference-resistance attributes; callers obtain those supported discovery
    fields from :func:`model_info`.
    """

    _model: _models.RTDModel = field(repr=False, compare=False)

    def __repr__(self) -> str:
        return "<rtd_sensor.catalog built-in RTD model>"

    def celsius_to_resistance(self, temperature_c: float) -> float:
        return self._model.celsius_to_resistance(temperature_c)

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        return self._model.resistance_to_celsius(resistance_ohms)

    def resistance_sensitivity_ohms_per_celsius(
        self,
        temperature_c: float,
    ) -> float:
        return self._model.resistance_sensitivity_ohms_per_celsius(temperature_c)

    def temperature_sensitivity_celsius_per_ohm(
        self,
        temperature_c: float,
    ) -> float:
        return self._model.temperature_sensitivity_celsius_per_ohm(temperature_c)


def _build_model_info(
    definition: _definitions.BuiltinRTDModelDefinition,
) -> BuiltinRTDModelInfo:
    characteristic = _definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS[
        definition.characteristic_id
    ]
    source_references = tuple(
        RTDSourceReference(citation=reference.citation, url=reference.url)
        for reference in characteristic.source_references
    )
    return BuiltinRTDModelInfo(
        model_id=definition.model_id,
        display_name=definition.display_name,
        characteristic_id=definition.characteristic_id,
        characteristic_display_name=characteristic.display_name,
        material=characteristic.material,
        curve_kind=characteristic.curve_kind,
        reference_resistance_ohms=definition.reference_resistance_ohms,
        reference_temperature_c=characteristic.reference_temperature_c,
        minimum_temperature_c=characteristic.minimum_temperature_c,
        maximum_temperature_c=characteristic.maximum_temperature_c,
        source_references=source_references,
    )


_MODEL_INFO_BY_ID: Mapping[str, BuiltinRTDModelInfo] = MappingProxyType(
    {
        definition.model_id: _build_model_info(definition)
        for definition in _definitions.BUILTIN_MODEL_DEFINITIONS.values()
    }
)
_SUPPORTED_MODEL_IDS = tuple(_MODEL_INFO_BY_ID)
_MODEL_BY_ID: Mapping[str, _RTDModel] = MappingProxyType(
    {
        model_id: _BuiltinRTDModelAdapter(_model=_models.BUILTIN_RTD_MODELS[model_id])
        for model_id in _SUPPORTED_MODEL_IDS
    }
)


def supported_models() -> tuple[str, ...]:
    """Return canonical IDs for all verified built-in RTD models.

    The returned tuple follows the package's authoritative built-in definition
    order and cannot be used to mutate the internal registry.
    """
    return _SUPPORTED_MODEL_IDS


def get_model(model_id: str) -> _RTDModel:
    """Return the built-in RTD model identified by ``model_id``.

    The returned object is a cached immutable adapter satisfying
    :class:`rtd_sensor.models.RTDModel`. Use :func:`model_info` for descriptive
    identity, range, and provenance metadata.

    Raises:
        TypeError: If ``model_id`` is not a string.
        KeyError: If ``model_id`` is not a supported canonical built-in ID.
    """
    canonical_id = _require_known_model_id(model_id)
    return _MODEL_BY_ID[canonical_id]


def model_info(model_id: str) -> BuiltinRTDModelInfo:
    """Return immutable metadata for the built-in RTD identified by ``model_id``.

    Raises:
        TypeError: If ``model_id`` is not a string.
        KeyError: If ``model_id`` is not a supported canonical built-in ID.
    """
    canonical_id = _require_known_model_id(model_id)
    return _MODEL_INFO_BY_ID[canonical_id]


def _require_known_model_id(model_id: str) -> str:
    if not isinstance(model_id, str):
        raise TypeError("RTD model ID must be a string")
    if model_id not in _MODEL_INFO_BY_ID:
        raise KeyError(f"Unknown built-in RTD model ID: {model_id!r}")
    return model_id
