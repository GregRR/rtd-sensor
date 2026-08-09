# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""General measurement-uncertainty primitives.

This module provides small, dependency-free helpers that follow the
measurement-uncertainty conventions used by the GUM/JCGM framework and
NIST Technical Note 1297.  The helpers operate on already-evaluated
uncertainty quantities; they do not decide which physical effects belong
in a particular RTD uncertainty budget.

A tolerance limit is not automatically a standard uncertainty.  If a
bounded specification is converted with :func:`standard_uncertainty_from_bound`,
the selected probability distribution is an explicit modeling assumption
made by the caller.
"""

from __future__ import annotations

import math
from typing import Literal

__all__ = [
    "BoundDistribution",
    "combine_independent_standard_uncertainties",
    "expanded_uncertainty",
    "standard_uncertainty_from_bound",
    "standard_uncertainty_from_expanded",
]


type BoundDistribution = Literal["rectangular", "triangular"]


def standard_uncertainty_from_bound(
    half_width: float,
    *,
    distribution: BoundDistribution,
) -> float:
    """Convert a symmetric bound half-width to standard uncertainty.

    Args:
        half_width: Positive magnitude ``a`` of a symmetric interval
            ``estimate ± a``.
        distribution: Probability model assigned to values inside the
            interval. ``rectangular`` gives ``a / sqrt(3)`` and
            ``triangular`` gives ``a / sqrt(6)``.

    Returns:
        Standard uncertainty in the same units as ``half_width``.

    Raises:
        ValueError: If the half-width is negative or non-finite, or if the
            distribution is unsupported.

    Notes:
        Choosing a distribution is part of the uncertainty model.  This
        function must not be read as asserting that an IEC tolerance band,
        manufacturer limit, or other specification has a particular
        probability distribution.
    """
    bound = _validate_nonnegative_finite(half_width, name="Half-width")

    if distribution == "rectangular":
        divisor = math.sqrt(3.0)
    elif distribution == "triangular":
        divisor = math.sqrt(6.0)
    else:
        raise ValueError(
            "Distribution must be 'rectangular' or 'triangular'"
        )

    return bound / divisor


def standard_uncertainty_from_expanded(
    expanded_uncertainty_value: float,
    *,
    coverage_factor: float,
) -> float:
    """Convert expanded uncertainty ``U`` to standard uncertainty ``u``.

    This performs the inverse of ``U = k * u`` and therefore requires the
    coverage factor from the certificate or other source that reported the
    expanded uncertainty.
    """
    expanded = _validate_nonnegative_finite(
        expanded_uncertainty_value,
        name="Expanded uncertainty",
    )
    factor = _validate_positive_finite(
        coverage_factor,
        name="Coverage factor",
    )
    standard = expanded / factor
    if not math.isfinite(standard):
        raise ValueError("Standard uncertainty result must remain finite")
    return standard


def combine_independent_standard_uncertainties(
    *standard_uncertainties: float,
) -> float:
    """Combine independent standard uncertainties by root-sum-square.

    Args:
        *standard_uncertainties: One or more non-negative standard
            uncertainties expressed in the same output units.

    Returns:
        Combined standard uncertainty in those same units.

    Raises:
        ValueError: If no components are supplied or if any component is
            negative or non-finite.

    Notes:
        This helper assumes the supplied components are uncorrelated.  It
        intentionally does not accept covariance or correlation terms; those
        require a covariance-aware propagation model.
    """
    if not standard_uncertainties:
        raise ValueError("At least one standard uncertainty is required")

    validated = [
        _validate_nonnegative_finite(value, name="Standard uncertainty")
        for value in standard_uncertainties
    ]

    # math.hypot performs the root-sum-square calculation without the
    # avoidable overflow/underflow risk of explicitly squaring every input.
    combined = math.hypot(*validated)
    if not math.isfinite(combined):
        raise ValueError("Combined standard uncertainty must remain finite")
    return combined


def expanded_uncertainty(
    combined_standard_uncertainty: float,
    *,
    coverage_factor: float,
) -> float:
    """Return expanded uncertainty ``U = k * u_c``.

    No confidence level is inferred from the coverage factor.  A coverage
    factor such as ``k=2`` only has a probability interpretation when that
    interpretation is justified by the underlying uncertainty analysis.
    """
    combined = _validate_nonnegative_finite(
        combined_standard_uncertainty,
        name="Combined standard uncertainty",
    )
    factor = _validate_positive_finite(
        coverage_factor,
        name="Coverage factor",
    )
    expanded = factor * combined
    if not math.isfinite(expanded):
        raise ValueError("Expanded uncertainty result must remain finite")
    return expanded


def _validate_nonnegative_finite(value: float, *, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if number < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return number


def _validate_positive_finite(value: float, *, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if number <= 0.0:
        raise ValueError(f"{name} must be greater than zero")
    return number
