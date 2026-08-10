# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Simulation tools for RTD-based applications.

All simulated readers expose resistance in ohms. This allows application
code to use the same interface for simulated data and physical hardware.

Simulation defaults to Pt100 for backward compatibility. Pass an explicit
``rtd_type`` to select Pt500, Pt1000, or the built-in former-DIN Ni1000 6180
characteristic.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from . import _models
from ._validation import as_float as _as_float

__all__ = [
    "FixedResistanceReader",
    "NoisyTemperatureReader",
    "RTDType",
    "ResistanceReader",
    "ResistanceSequenceReader",
    "TemperatureSequenceReader",
    "read_temperature_celsius",
]


type RTDType = Literal["pt100", "pt500", "pt1000", "ni1000"]

_SUPPORTED_MODELS: dict[RTDType, _models.RTDModel] = {
    "pt100": _models.PT100_IEC_60751,
    "pt500": _models.PT500_IEC_60751,
    "pt1000": _models.PT1000_IEC_60751,
    "ni1000": _models.NI1000_6180,
}


class ResistanceReader(Protocol):
    """An object capable of returning an RTD resistance measurement."""

    def read_resistance_ohms(self) -> float:
        """Return one resistance measurement in ohms."""
        ...


@runtime_checkable
class _ModelAwareResistanceReader(ResistanceReader, Protocol):
    """Internal protocol for readers that declare their RTD type."""

    @property
    def rtd_type(self) -> RTDType:
        """Return the RTD type represented by this reader."""
        ...


class _FixedRTDIdentity:
    """Prevent a reader's declared RTD type from diverging from its model.

    Built-in readers resolve and cache their conversion model during
    construction. Allowing ``rtd_type`` to change afterward would leave the
    public identity and cached model inconsistent, so only the initial
    dataclass assignment is permitted. Other reader state remains mutable
    where required, such as a sequence reader's internal index.
    """

    __slots__ = ()

    def __setattr__(self, name: str, value: object) -> None:
        if name == "rtd_type":
            try:
                object.__getattribute__(self, name)
            except AttributeError:
                pass
            else:
                raise AttributeError(
                    "rtd_type is read-only after reader construction"
                )

        object.__setattr__(self, name, value)


@dataclass(slots=True)
class FixedResistanceReader(_FixedRTDIdentity):
    """Return the same resistance for every reading."""

    resistance_ohms: float
    rtd_type: RTDType = "pt100"
    _model: _models.RTDModel = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._model = _model_for_rtd_type(self.rtd_type)
        self.resistance_ohms = _validate_resistance(
            self.resistance_ohms,
            self._model,
        )

    def read_resistance_ohms(self) -> float:
        """Return the configured resistance."""
        return self.resistance_ohms


@dataclass(slots=True)
class ResistanceSequenceReader(_FixedRTDIdentity):
    """Return resistance values from a finite or repeating sequence."""

    readings_ohms: Sequence[float]
    repeat: bool = False
    rtd_type: RTDType = "pt100"
    _model: _models.RTDModel = field(
        init=False,
        repr=False,
    )
    _readings: tuple[float, ...] = field(
        init=False,
        repr=False,
    )
    _index: int = field(
        init=False,
        default=0,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not self.readings_ohms:
            raise ValueError(
                "At least one resistance reading is required"
            )

        self._model = _model_for_rtd_type(self.rtd_type)
        self._readings = tuple(
            _validate_resistance(reading, self._model)
            for reading in self.readings_ohms
        )

    def read_resistance_ohms(self) -> float:
        """Return the next resistance value.

        Raises:
            StopIteration: When a non-repeating sequence is exhausted.
        """
        if self._index >= len(self._readings):
            if not self.repeat:
                raise StopIteration(
                    "No simulated resistance readings remain"
                )

            self._index = 0

        resistance = self._readings[self._index]
        self._index += 1

        return resistance


@dataclass(slots=True)
class TemperatureSequenceReader(_FixedRTDIdentity):
    """Simulate RTD resistance from a temperature sequence."""

    temperatures_c: Sequence[float]
    repeat: bool = False
    rtd_type: RTDType = "pt100"
    _model: _models.RTDModel = field(
        init=False,
        repr=False,
    )
    _reader: ResistanceSequenceReader = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not self.temperatures_c:
            raise ValueError(
                "At least one simulated temperature is required"
            )

        self._model = _model_for_rtd_type(self.rtd_type)
        readings = tuple(
            self._model.celsius_to_resistance(temperature)
            for temperature in self.temperatures_c
        )

        self._reader = ResistanceSequenceReader(
            readings_ohms=readings,
            repeat=self.repeat,
            rtd_type=self.rtd_type,
        )

    def read_resistance_ohms(self) -> float:
        """Return resistance corresponding to the next temperature."""
        return self._reader.read_resistance_ohms()


@dataclass(slots=True)
class NoisyTemperatureReader(_FixedRTDIdentity):
    """Simulate a temperature with reproducible Gaussian noise.

    Noise is applied in degrees Celsius before the simulated temperature
    is converted into ideal resistance for the selected RTD type.

    Supplying the same seed produces the same sequence of readings.
    """

    temperature_c: float
    noise_standard_deviation_c: float = 0.05
    seed: int | None = None
    rtd_type: RTDType = "pt100"
    _model: _models.RTDModel = field(
        init=False,
        repr=False,
    )
    _random: random.Random = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._model = _model_for_rtd_type(self.rtd_type)

        # Validation belongs to the selected RTD model so the simulator
        # exercises the same range rules as real conversion calls.
        self._model.celsius_to_resistance(self.temperature_c)

        standard_deviation = _as_float(
            self.noise_standard_deviation_c,
            name="Noise standard deviation",
        )

        if not math.isfinite(standard_deviation):
            raise ValueError(
                "Noise standard deviation must be finite"
            )

        if standard_deviation < 0.0:
            raise ValueError(
                "Noise standard deviation cannot be negative"
            )

        self.noise_standard_deviation_c = standard_deviation
        self._random = random.Random(self.seed)

    def read_resistance_ohms(self) -> float:
        """Return one noisy simulated RTD resistance reading."""
        simulated_temperature = self._random.gauss(
            self.temperature_c,
            self.noise_standard_deviation_c,
        )

        return self._model.celsius_to_resistance(
            simulated_temperature
        )


def read_temperature_celsius(
    reader: ResistanceReader,
    *,
    rtd_type: RTDType | None = None,
) -> float:
    """Read resistance from a source and convert it to Celsius.

    Built-in simulation readers carry their RTD type, so no explicit
    ``rtd_type`` is needed when reading them. For an external hardware
    reader that exposes only resistance, pass ``rtd_type`` explicitly.

    Readers without a declared RTD type default to Pt100 for backward
    compatibility. If a reader declares its RTD type, an explicit conflicting
    ``rtd_type`` is rejected rather than silently interpreting the resistance
    with the wrong model.
    """
    declared_type: RTDType | None = None

    if isinstance(reader, _ModelAwareResistanceReader):
        declared_type = reader.rtd_type
        # A model-aware reader's declaration is part of the conversion
        # contract. Validate it even when the caller also supplies a type so
        # an invalid or stale declaration cannot be silently bypassed.
        _model_for_rtd_type(declared_type)

    if rtd_type is not None:
        model = _model_for_rtd_type(rtd_type)

        if declared_type is not None and rtd_type != declared_type:
            raise ValueError(
                f"Explicit RTD type {rtd_type!r} conflicts with "
                f"reader-declared RTD type {declared_type!r}"
            )
    else:
        selected_type = declared_type or "pt100"
        model = _model_for_rtd_type(selected_type)

    resistance = reader.read_resistance_ohms()
    return model.resistance_to_celsius(resistance)


def _model_for_rtd_type(rtd_type: RTDType) -> _models.RTDModel:
    try:
        return _SUPPORTED_MODELS[rtd_type]
    except KeyError as error:
        supported = ", ".join(sorted(_SUPPORTED_MODELS))
        raise ValueError(
            f"Unsupported RTD type {rtd_type!r}; expected one of: {supported}"
        ) from error


def _validate_resistance(
    resistance_ohms: float,
    model: _models.RTDModel,
) -> float:
    resistance = _as_float(resistance_ohms, name="Resistance")

    if not math.isfinite(resistance):
        raise ValueError("Resistance must be finite")

    if resistance <= 0.0:
        raise ValueError("Resistance must be greater than zero")

    model.resistance_to_celsius(resistance)

    return resistance
