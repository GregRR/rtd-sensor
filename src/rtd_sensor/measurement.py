# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Hardware-neutral RTD resistance measurement and model composition.

Acquisition code is responsible for producing the best available estimate of
sensor-element resistance in ohms. That may include converter-specific
calculations, lead-wire compensation, or other hardware-side corrections.
This module defines the small structural boundary consumed by rtd-sensor and
combines it with an independently selected RTD model; it does not define how
hardware obtains resistance.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from . import catalog as _catalog
from ._protocols import RTDModel as _RTDModel

__all__ = ["ResistanceReader", "read_temperature_celsius"]


class ResistanceReader(Protocol):
    """Structural interface for a source of RTD resistance measurements.

    Implementations do not need to inherit from an rtd-sensor base class. A
    compatible object only needs to provide :meth:`read_resistance_ohms`.
    """

    def read_resistance_ohms(self) -> float:
        """Return one sensor-element resistance value in ohms."""
        ...


@runtime_checkable
class _ModelAwareResistanceReader(ResistanceReader, Protocol):
    """Internal compatibility protocol for readers that declare a built-in ID."""

    @property
    def rtd_type(self) -> str:
        """Return the built-in RTD model ID represented by this reader."""
        ...


def read_temperature_celsius(
    reader: ResistanceReader,
    *,
    model: _RTDModel | None = None,
    rtd_type: str | None = None,
) -> float:
    """Read compensated resistance and convert it to Celsius.

    ``model`` is the preferred composition path for new application and
    hardware code because any object satisfying :class:`rtd_sensor.models.RTDModel`
    may be supplied. ``rtd_type`` retains the canonical built-in string-ID
    convenience used by existing simulation integrations.

    Readers without a declared RTD type default to Pt100 when neither selection
    argument is supplied, preserving the historical simulation behavior. A
    reader-declared built-in type is honored when no explicit selection is made
    and must agree with an explicitly supplied ``rtd_type``.

    An explicit model cannot be combined with ``rtd_type`` or with a reader
    that declares ``rtd_type``. The structural RTDModel protocol deliberately
    carries no identity metadata, so such combinations cannot be proven
    consistent and are rejected rather than risking conversion with a
    contradictory characteristic.

    Hardware/acquisition exceptions from ``reader`` and conversion exceptions
    from ``model`` propagate unchanged; this layer does not translate hardware
    failures into model failures or vice versa.

    Raises:
        ValueError: If model-selection declarations conflict or are ambiguous,
            or if a selected built-in RTD type is unsupported.
    """
    declared_type: str | None = None

    if isinstance(reader, _ModelAwareResistanceReader):
        # Runtime-checkable protocols verify attribute presence, not the runtime
        # value type supplied by an arbitrary third-party object.
        declared_value: object = reader.rtd_type
        if not isinstance(declared_value, str):
            raise ValueError(
                "Reader-declared RTD type must be a string; "
                f"got {type(declared_value).__name__}"
            )
        declared_type = declared_value
        # A declaration must remain valid even when the caller supplies another
        # selection mechanism; an invalid/stale identity cannot be bypassed.
        _model_for_rtd_type(declared_type)

    if model is not None and rtd_type is not None:
        raise ValueError("Specify either model or rtd_type, not both")

    if model is not None:
        if declared_type is not None:
            raise ValueError(
                "Cannot combine an explicit RTD model with reader-declared "
                f"RTD type {declared_type!r}; use a neutral ResistanceReader "
                "when selecting a model object directly"
            )
        selected_model = model
    elif rtd_type is not None:
        selected_model = _model_for_rtd_type(rtd_type)
        if declared_type is not None and rtd_type != declared_type:
            raise ValueError(
                f"Explicit RTD type {rtd_type!r} conflicts with "
                f"reader-declared RTD type {declared_type!r}"
            )
    else:
        selected_model = _model_for_rtd_type(declared_type or "pt100")

    resistance = reader.read_resistance_ohms()
    return selected_model.resistance_to_celsius(resistance)


def _model_for_rtd_type(rtd_type: str) -> _RTDModel:
    try:
        return _catalog.get_model(rtd_type)
    except KeyError as error:
        supported = ", ".join(sorted(_catalog.supported_models()))
        raise ValueError(
            f"Unsupported RTD type {rtd_type!r}; expected one of: {supported}"
        ) from error
