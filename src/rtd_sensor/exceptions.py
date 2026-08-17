# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public exceptions for RTD fitting, model selection, configuration, and
range failures.

The hierarchy is intentionally small. Acquisition-layer exceptions from hardware
readers are not translated into these types, and third-party RTD model exceptions
continue to propagate unchanged.
"""

from __future__ import annotations

__all__ = [
    "InvalidRTDModelError",
    "RTDError",
    "RTDFitError",
    "RTDModelSelectionError",
    "RTDOutOfRangeError",
    "UnknownRTDModelError",
]


class RTDError(Exception):
    """Base class for package-owned RTD domain errors."""


class UnknownRTDModelError(RTDError, KeyError):
    """Raised when a canonical built-in RTD model ID is unknown."""

    def __str__(self) -> str:
        """Render the message without KeyError's repr-style quoting."""
        return Exception.__str__(self)


class RTDOutOfRangeError(RTDError, ValueError):
    """Raised when a temperature or resistance lies outside a model range."""


class InvalidRTDModelError(RTDError, ValueError):
    """Raised when a custom RTD model configuration is mathematically invalid."""


class RTDFitError(RTDError, ValueError):
    """Raised when calibration fitting cannot produce a valid RTD model."""


class RTDModelSelectionError(RTDError, ValueError):
    """Raised when reader/model selection declarations are invalid or ambiguous."""
