# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Dependency-free batch RTD conversion helpers.

The helpers in this module are deliberately thin convenience wrappers around
an RTD model's scalar conversion methods. Scalar behavior remains authoritative:
inputs are consumed once in order, results are returned eagerly as ordinary
Python lists, and the first scalar exception propagates unchanged.
"""

from __future__ import annotations

from collections.abc import Iterable

from ._protocols import RTDModel

__all__ = ["celsius_to_resistance", "resistance_to_celsius"]


def celsius_to_resistance(
    model: RTDModel,
    temperatures_c: Iterable[float],
) -> list[float]:
    """Convert an iterable of Celsius temperatures to resistance in ohms.

    The iterable is consumed once and in order. Each element is passed directly
    to ``model.celsius_to_resistance`` so scalar validation, range handling, and
    exceptions remain authoritative. The first scalar exception propagates
    unchanged and no partial result list is returned.
    """
    return [model.celsius_to_resistance(value) for value in temperatures_c]


def resistance_to_celsius(
    model: RTDModel,
    resistances_ohms: Iterable[float],
) -> list[float]:
    """Convert an iterable of resistances in ohms to Celsius temperatures.

    The iterable is consumed once and in order. Each element is passed directly
    to ``model.resistance_to_celsius`` so scalar validation, range handling, and
    exceptions remain authoritative. The first scalar exception propagates
    unchanged and no partial result list is returned.
    """
    return [model.resistance_to_celsius(value) for value in resistances_ohms]
