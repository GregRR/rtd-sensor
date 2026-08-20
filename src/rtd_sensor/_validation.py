# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared validation helpers for public numeric inputs."""

from __future__ import annotations

from typing import SupportsFloat, SupportsIndex


def as_float(
    value: str | bytes | bytearray | memoryview | SupportsFloat | SupportsIndex,
    *,
    name: str,
) -> float:
    """Return ``value`` as ``float`` while rejecting Boolean quantities.

    Python's ``bool`` type is a subclass of ``int``, so ``float(True)`` and
    ``float(False)`` silently become ``1.0`` and ``0.0``. That behavior is
    useful in ordinary Python arithmetic but is surprising for physical
    quantities such as resistance, temperature, coefficients, and uncertainty.
    Rejecting booleans here keeps accidental flags from becoming plausible
    measurement values while preserving the package's existing acceptance of
    ordinary float-convertible numeric inputs.
    """
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric, not bool")
    return float(value)
