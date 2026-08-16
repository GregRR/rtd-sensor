# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Simulation tools for RTD-based applications.

All simulated readers expose resistance in ohms. This allows application
code to use the same interface for simulated data and physical hardware. The
hardware-neutral :class:`rtd_sensor.measurement.ResistanceReader` protocol and
model-composition helper are re-exported here for compatibility with existing
simulation imports.

Simulation defaults to Pt100 for backward compatibility. Pass an explicit
``rtd_type`` to select Pt500, Pt1000, the built-in former-DIN Ni1000
6180 characteristic, Ni1000 TK5000, or North American Ni120.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, field

from . import _models
from ._protocols import RTDModel as _RTDModelProtocol
from ._validation import as_float as _as_float
from .measurement import ResistanceReader, read_temperature_celsius

__all__ = [
    "FixedResistanceReader",
    "NoisyTemperatureReader",
    "RTDType",
    "ResistanceReader",
    "ResistanceSequenceReader",
    "SUPPORTED_RTD_TYPES",
    "TemperatureSequenceReader",
    "read_temperature_celsius",
]


type RTDType = str

# Python's type system cannot derive a Literal[...] union from a runtime
# registry. Keep the public spelling as strings and make the immutable model
# registry the authoritative source of what is actually supported. This avoids
# duplicating every new built-in identity in both a type alias and a lookup
# table while retaining strict runtime validation.
SUPPORTED_RTD_TYPES: tuple[RTDType, ...] = tuple(_models.BUILTIN_RTD_MODELS)


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
                raise AttributeError("rtd_type is read-only after reader construction")

        object.__setattr__(self, name, value)


@dataclass(slots=True)
class FixedResistanceReader(_FixedRTDIdentity):
    """Return the same resistance for every reading."""

    resistance_ohms: float
    rtd_type: RTDType = "pt100"
    _model: _RTDModelProtocol = field(
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
    _model: _RTDModelProtocol = field(
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
            raise ValueError("At least one resistance reading is required")

        self._model = _model_for_rtd_type(self.rtd_type)
        self._readings = tuple(
            _validate_resistance(reading, self._model) for reading in self.readings_ohms
        )

    def read_resistance_ohms(self) -> float:
        """Return the next resistance value.

        Raises:
            StopIteration: When a non-repeating sequence is exhausted.
        """
        if self._index >= len(self._readings):
            if not self.repeat:
                raise StopIteration("No simulated resistance readings remain")

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
    _model: _RTDModelProtocol = field(
        init=False,
        repr=False,
    )
    _reader: ResistanceSequenceReader = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not self.temperatures_c:
            raise ValueError("At least one simulated temperature is required")

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
    _model: _RTDModelProtocol = field(
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
            raise ValueError("Noise standard deviation must be finite")

        if standard_deviation < 0.0:
            raise ValueError("Noise standard deviation cannot be negative")

        self.noise_standard_deviation_c = standard_deviation
        self._random = random.Random(self.seed)

    def read_resistance_ohms(self) -> float:
        """Return one noisy simulated RTD resistance reading."""
        simulated_temperature = self._random.gauss(
            self.temperature_c,
            self.noise_standard_deviation_c,
        )

        return self._model.celsius_to_resistance(simulated_temperature)


def _model_for_rtd_type(rtd_type: RTDType) -> _RTDModelProtocol:
    try:
        return _models.BUILTIN_RTD_MODELS[rtd_type]
    except KeyError as error:
        supported = ", ".join(sorted(SUPPORTED_RTD_TYPES))
        raise ValueError(
            f"Unsupported RTD type {rtd_type!r}; expected one of: {supported}"
        ) from error


def _validate_resistance(
    resistance_ohms: float,
    model: _RTDModelProtocol,
) -> float:
    resistance = _as_float(resistance_ohms, name="Resistance")

    if not math.isfinite(resistance):
        raise ValueError("Resistance must be finite")

    if resistance <= 0.0:
        raise ValueError("Resistance must be greater than zero")

    model.resistance_to_celsius(resistance)

    return resistance
