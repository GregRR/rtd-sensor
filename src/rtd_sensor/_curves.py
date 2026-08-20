# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Internal RTD resistance-ratio curve definitions."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol, TypeVar

from . import _definitions
from ._validation import as_float as _as_float
from .exceptions import RTDOutOfRangeError

__all__ = [
    "BUILTIN_RTD_CURVES",
    "CallendarVanDusenCurve",
    "IEC_60751_PT385",
    "NI_5000_TK5000",
    "NI_6180_DIN_43760",
    "NI_6720_NORTH_AMERICAN",
    "PiecewisePolynomialRTDCurve",
    "PolynomialRTDCurve",
    "PolynomialRTDSegment",
    "RTDCurve",
]

_BISECTION_ITERATIONS = 60
_MAX_POLYNOMIAL_DEGREE = 12
_CurveT = TypeVar("_CurveT")


class RTDCurve(Protocol):
    """Internal interface for a normalized RTD resistance curve."""

    @property
    def name(self) -> str:
        """Return the descriptive name of the curve."""
        ...

    @property
    def reference_temperature_c(self) -> float:
        """Return the temperature at which the normalized ratio is 1."""
        ...

    @property
    def minimum_temperature_c(self) -> float:
        """Return the minimum supported temperature."""
        ...

    @property
    def maximum_temperature_c(self) -> float:
        """Return the maximum supported temperature."""
        ...

    def resistance_ratio(self, temperature_c: float) -> float:
        """Return R(T) / Rref for a temperature in Celsius."""
        ...

    def resistance_ratio_slope(self, temperature_c: float) -> float:
        """Return d(R/Rref)/dT at a temperature in Celsius."""
        ...

    def temperature_from_resistance_ratio(
        self,
        resistance_ratio: float,
    ) -> float:
        """Return temperature in Celsius for R(T) / Rref."""
        ...


@dataclass(frozen=True, slots=True)
class CallendarVanDusenCurve:
    """A normalized Callendar-Van Dusen platinum RTD curve.

    The normalized equation remains referenced to R0 at 0 °C, but a custom
    characteristic may intentionally declare a narrower validity interval
    that does not include 0 °C. The supported interval therefore describes
    where conversion is valid, not where the equation's reference resistance
    is defined.
    """

    name: str
    a: float
    b: float
    c: float
    minimum_temperature_c: float
    maximum_temperature_c: float

    @property
    def reference_temperature_c(self) -> float:
        """Return the 0 °C reference temperature of the CVD curve."""
        return 0.0

    def __post_init__(self) -> None:
        coefficients = (self.a, self.b, self.c)
        if not all(math.isfinite(value) for value in coefficients):
            raise ValueError("Curve coefficients must be finite")

        if not math.isfinite(self.minimum_temperature_c):
            raise ValueError("Minimum temperature must be finite")
        if not math.isfinite(self.maximum_temperature_c):
            raise ValueError("Maximum temperature must be finite")
        if self.minimum_temperature_c >= self.maximum_temperature_c:
            raise ValueError("Minimum temperature must be below maximum temperature")
        self._validate_curve_shape()

    def _validate_curve_shape(self) -> None:
        try:
            endpoint_ratios = [
                self._resistance_ratio_unchecked(self.minimum_temperature_c),
                self._resistance_ratio_unchecked(self.maximum_temperature_c),
            ]
            slope_candidates = [
                self.minimum_temperature_c,
                self.maximum_temperature_c,
                0.0,
                *self._negative_slope_extrema(),
            ]
        except OverflowError as exc:
            raise ValueError("Curve calculations must remain finite") from exc

        if not all(math.isfinite(ratio) for ratio in endpoint_ratios):
            raise ValueError("Curve resistance ratio must remain finite")
        if endpoint_ratios[0] <= 0.0:
            raise ValueError("Curve resistance ratio must remain positive")

        for temperature_c in slope_candidates:
            if not (
                self.minimum_temperature_c
                <= temperature_c
                <= self.maximum_temperature_c
            ):
                continue
            try:
                slope = self._resistance_ratio_slope_unchecked(temperature_c)
            except OverflowError as exc:
                raise ValueError("Curve slope must remain finite") from exc
            if not math.isfinite(slope):
                raise ValueError("Curve slope must remain finite")
            if slope <= 0.0:
                raise ValueError(
                    "Curve must be strictly increasing over its supported range"
                )

    def _negative_slope_extrema(self) -> list[float]:
        negative_maximum_c = min(self.maximum_temperature_c, 0.0)
        if self.minimum_temperature_c >= negative_maximum_c or self.c == 0.0:
            return []

        quadratic_a = 12.0 * self.c
        quadratic_b = -600.0 * self.c
        quadratic_c = 2.0 * self.b
        discriminant = quadratic_b**2 - 4.0 * quadratic_a * quadratic_c
        if discriminant < 0.0:
            return []

        sqrt_discriminant = math.sqrt(discriminant)
        denominator = 2.0 * quadratic_a
        return [
            (-quadratic_b - sqrt_discriminant) / denominator,
            (-quadratic_b + sqrt_discriminant) / denominator,
        ]

    def _resistance_ratio_slope_unchecked(
        self,
        temperature_c: float,
    ) -> float:
        slope = self.a + 2.0 * self.b * temperature_c
        if temperature_c < 0.0:
            slope += self.c * temperature_c**2 * (4.0 * temperature_c - 300.0)
        return slope

    def resistance_ratio(self, temperature_c: float) -> float:
        """Return the normalized resistance ratio R(T) / R0."""
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)
        return self._resistance_ratio_unchecked(temperature)

    def resistance_ratio_slope(self, temperature_c: float) -> float:
        """Return the exact local slope d(R/R0)/dT.

        The derivative is evaluated analytically from the same
        Callendar-Van Dusen equation used for conversion.  Keeping this
        calculation in the curve object ensures uncertainty propagation uses
        the model's actual coefficients rather than a finite-difference
        approximation.
        """
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)
        return self._resistance_ratio_slope_unchecked(temperature)

    def temperature_from_resistance_ratio(
        self,
        resistance_ratio: float,
    ) -> float:
        """Invert a normalized resistance ratio to Celsius."""
        ratio = _as_float(resistance_ratio, name="Resistance ratio")
        ratio = self._validated_resistance_ratio(ratio)

        minimum_ratio, maximum_ratio = self._resistance_ratio_bounds()
        if ratio == minimum_ratio:
            return self.minimum_temperature_c
        if ratio == maximum_ratio:
            return self.maximum_temperature_c
        # A characterized CVD model may declare a validity interval that does
        # not include 0 °C even though R0 remains the equation's reference
        # resistance.  In a wholly one-sided interval, resistance relative to
        # R0 does not reliably identify the temperature side: custom
        # coefficients can cross R/R0 == 1 away from 0 °C.  Bisection over the
        # already-validated declared interval therefore gives the unique
        # supported root without relying on standard IEC coefficient behavior.
        if self.minimum_temperature_c >= 0.0 or self.maximum_temperature_c <= 0.0:
            return self._bounded_ratio_to_celsius(
                ratio,
                lower_c=self.minimum_temperature_c,
                upper_c=self.maximum_temperature_c,
            )

        if ratio == 1.0:
            return 0.0

        if ratio > 1.0:
            return self._nonnegative_ratio_to_celsius(ratio)

        return self._bounded_ratio_to_celsius(
            ratio,
            lower_c=self.minimum_temperature_c,
            upper_c=0.0,
        )

    def _resistance_ratio_unchecked(self, temperature_c: float) -> float:
        resistance_ratio = 1.0 + self.a * temperature_c + self.b * temperature_c**2

        if temperature_c < 0.0:
            resistance_ratio += self.c * (temperature_c - 100.0) * temperature_c**3

        return resistance_ratio

    def _nonnegative_ratio_to_celsius(
        self,
        resistance_ratio: float,
    ) -> float:
        if self.b == 0.0:
            if self.a == 0.0:
                raise ValueError(
                    f"Resistance ratio cannot be converted using {self.name}"
                )
            temperature_c = (resistance_ratio - 1.0) / self.a
        else:
            discriminant = self.a**2 - 4.0 * self.b * (1.0 - resistance_ratio)

            if discriminant < 0.0:
                raise ValueError(
                    f"Resistance ratio cannot be converted using {self.name}"
                )

            # The direct quadratic root ``(-A + sqrt(D)) / (2B)``
            # suffers cancellation for ordinary platinum RTD coefficients
            # because ``sqrt(D)`` is close to ``A``.  This algebraically
            # equivalent form keeps the numerator well-conditioned.
            temperature_c = (2.0 * (1.0 - resistance_ratio)) / (
                -self.a - math.sqrt(discriminant)
            )

        # The resistance ratio was already validated against a strictly
        # increasing curve, so its mathematical inverse is necessarily in
        # range.  A second strict comparison here can only turn harmless
        # inverse-rounding noise near the endpoint into a false rejection.
        return temperature_c

    def _bounded_ratio_to_celsius(
        self,
        resistance_ratio: float,
        *,
        lower_c: float,
        upper_c: float,
    ) -> float:
        """Invert on a known strictly increasing CVD temperature interval."""
        for _ in range(_BISECTION_ITERATIONS):
            midpoint_c = (lower_c + upper_c) / 2.0
            midpoint_ratio = self._resistance_ratio_unchecked(midpoint_c)

            if midpoint_ratio < resistance_ratio:
                lower_c = midpoint_c
            else:
                upper_c = midpoint_c

        return (lower_c + upper_c) / 2.0

    def _validate_temperature(self, temperature_c: float) -> None:
        if not math.isfinite(temperature_c):
            raise ValueError("Temperature must be finite")
        if not (
            self.minimum_temperature_c <= temperature_c <= self.maximum_temperature_c
        ):
            raise RTDOutOfRangeError(
                "Temperature must be between "
                f"{self.minimum_temperature_c:g} °C and "
                f"{self.maximum_temperature_c:g} °C"
            )

    def _resistance_ratio_bounds(self) -> tuple[float, float]:
        return (
            self._resistance_ratio_unchecked(self.minimum_temperature_c),
            self._resistance_ratio_unchecked(self.maximum_temperature_c),
        )

    def _validated_resistance_ratio(self, resistance_ratio: float) -> float:
        minimum_ratio, maximum_ratio = self._resistance_ratio_bounds()
        return _validated_resistance_ratio_at_bounds(
            resistance_ratio,
            minimum_ratio=minimum_ratio,
            maximum_ratio=maximum_ratio,
        )


def _validated_resistance_ratio_at_bounds(
    resistance_ratio: float,
    *,
    minimum_ratio: float,
    maximum_ratio: float,
) -> float:
    """Validate and normalize a ratio at floating-point boundaries.

    A public model converts a measured resistance back to a ratio with
    ``R / Rref``. At an exact model endpoint, the preceding
    ``Rref * ratio`` multiplication can make that round trip land one
    representable float just outside the original ratio. Accepting exactly
    that one-ULP neighbor preserves the model's own endpoint round trip
    without admitting a materially out-of-range measurement.
    """
    if not math.isfinite(resistance_ratio):
        raise ValueError("Resistance ratio must be finite")
    if resistance_ratio <= 0.0:
        raise ValueError("Resistance ratio must be greater than zero")

    minimum_neighbor = math.nextafter(minimum_ratio, -math.inf)
    maximum_neighbor = math.nextafter(maximum_ratio, math.inf)

    if resistance_ratio < minimum_ratio:
        if resistance_ratio == minimum_neighbor:
            return minimum_ratio
        raise RTDOutOfRangeError("Resistance ratio is below the supported range")
    if resistance_ratio > maximum_ratio:
        if resistance_ratio == maximum_neighbor:
            return maximum_ratio
        raise RTDOutOfRangeError("Resistance ratio is above the supported range")

    return resistance_ratio


def _polynomial_value(coefficients: Sequence[float], x: float) -> float:
    """Evaluate an ascending-power polynomial with Horner's method."""
    result = 0.0
    for coefficient in reversed(coefficients):
        result = result * x + coefficient
    return result


def _polynomial_derivative(
    coefficients: Sequence[float],
) -> tuple[float, ...]:
    return tuple(
        power * coefficient
        for power, coefficient in enumerate(coefficients[1:], start=1)
    )


def _trim_polynomial(coefficients: Sequence[float]) -> tuple[float, ...]:
    trimmed = list(coefficients)
    while len(trimmed) > 1 and trimmed[-1] == 0.0:
        trimmed.pop()
    return tuple(trimmed)


def _polynomial_evaluation_scale(
    coefficients: Sequence[float],
    x: float,
) -> float:
    """Return a magnitude scale for judging near-zero polynomial values."""
    absolute_x = abs(x)
    power = 1.0
    terms: list[float] = []
    for coefficient in coefficients:
        terms.append(abs(coefficient) * power)
        power *= absolute_x
    return math.fsum(terms)


def _polynomial_value_is_roundoff_zero(
    value: float,
    coefficients: Sequence[float],
    x: float,
) -> bool:
    scale = _polynomial_evaluation_scale(coefficients, x)
    if not math.isfinite(scale):
        return False
    if scale == 0.0:
        return value == 0.0
    return abs(value) <= 64.0 * math.ulp(scale)


def _deduplicate_sorted_roots(roots: Sequence[float]) -> list[float]:
    if not roots:
        return []

    ordered = sorted(roots)
    result = [ordered[0]]
    for root in ordered[1:]:
        previous = result[-1]
        tolerance = max(
            8.0 * math.ulp(abs(previous) if previous != 0.0 else 1.0),
            8.0 * math.ulp(abs(root) if root != 0.0 else 1.0),
        )
        if abs(root - previous) > tolerance:
            result.append(root)
    return result


def _polynomial_roots_in_interval(
    coefficients: Sequence[float],
    lower: float,
    upper: float,
) -> list[float]:
    """Find real polynomial roots in a bounded interval.

    The recursive derivative partition follows Rolle's theorem: roots of the
    derivative divide the interval into regions on which the polynomial is
    monotonic, so each region contains at most one sign-changing root. This
    is used only during model construction to locate derivative extrema for
    monotonicity validation; conversion itself remains a simple bounded
    bisection on a curve already proven strictly increasing.
    """
    polynomial = _trim_polynomial(coefficients)
    degree = len(polynomial) - 1
    if degree <= 0:
        return []

    if degree == 1:
        root = -polynomial[0] / polynomial[1]
        if lower < root < upper:
            return [root]
        return []

    critical_points = _polynomial_roots_in_interval(
        _polynomial_derivative(polynomial),
        lower,
        upper,
    )
    partition = [lower, *critical_points, upper]
    roots: list[float] = []

    for point in critical_points:
        value = _polynomial_value(polynomial, point)
        if _polynomial_value_is_roundoff_zero(value, polynomial, point):
            roots.append(point)

    for interval_lower, interval_upper in zip(partition, partition[1:], strict=False):
        lower_value = _polynomial_value(polynomial, interval_lower)
        upper_value = _polynomial_value(polynomial, interval_upper)

        if not math.isfinite(lower_value) or not math.isfinite(upper_value):
            raise ValueError("Polynomial calculations must remain finite")

        lower_is_zero = _polynomial_value_is_roundoff_zero(
            lower_value, polynomial, interval_lower
        )
        upper_is_zero = _polynomial_value_is_roundoff_zero(
            upper_value, polynomial, interval_upper
        )

        if lower_is_zero or upper_is_zero:
            continue
        if (lower_value < 0.0) == (upper_value < 0.0):
            continue

        left = interval_lower
        right = interval_upper
        left_value = lower_value
        for _ in range(_BISECTION_ITERATIONS):
            midpoint = (left + right) / 2.0
            midpoint_value = _polynomial_value(polynomial, midpoint)
            if midpoint_value == 0.0:
                left = midpoint
                right = midpoint
                break
            if (left_value < 0.0) == (midpoint_value < 0.0):
                left = midpoint
                left_value = midpoint_value
            else:
                right = midpoint

        roots.append((left + right) / 2.0)

    return _deduplicate_sorted_roots(roots)


@dataclass(frozen=True, slots=True)
class PolynomialRTDSegment:
    """One normalized polynomial segment of a piecewise RTD characteristic.

    ``coefficients`` includes the constant term. For
    ``x = T - temperature_origin_c``, a segment evaluates

    ``R(T) / Rref = c0 + c1*x + c2*x**2 + ... + cn*x**n``.

    Piecewise source equations often publish an independent constant for each
    interval, so this representation intentionally differs from
    :class:`PolynomialRTDCurve`, whose constant is fixed at 1 at one global
    reference temperature.
    """

    minimum_temperature_c: float
    maximum_temperature_c: float
    coefficients: tuple[float, ...]
    temperature_origin_c: float = 0.0

    def __post_init__(self) -> None:
        minimum_temperature_c = _as_float(
            self.minimum_temperature_c,
            name="Segment minimum temperature",
        )
        maximum_temperature_c = _as_float(
            self.maximum_temperature_c,
            name="Segment maximum temperature",
        )
        temperature_origin_c = _as_float(
            self.temperature_origin_c,
            name="Segment temperature origin",
        )
        coefficients = tuple(
            _as_float(value, name=f"Segment coefficient c{index}")
            for index, value in enumerate(self.coefficients)
        )

        if not coefficients:
            raise ValueError("At least one segment coefficient is required")
        if len(coefficients) > _MAX_POLYNOMIAL_DEGREE + 1:
            raise ValueError(
                f"Segment polynomial degree must not exceed {_MAX_POLYNOMIAL_DEGREE}"
            )
        if not all(math.isfinite(value) for value in coefficients):
            raise ValueError("Segment polynomial coefficients must be finite")
        if not math.isfinite(minimum_temperature_c):
            raise ValueError("Segment minimum temperature must be finite")
        if not math.isfinite(maximum_temperature_c):
            raise ValueError("Segment maximum temperature must be finite")
        if not math.isfinite(temperature_origin_c):
            raise ValueError("Segment temperature origin must be finite")
        if minimum_temperature_c >= maximum_temperature_c:
            raise ValueError(
                "Segment minimum temperature must be below maximum temperature"
            )

        object.__setattr__(self, "minimum_temperature_c", minimum_temperature_c)
        object.__setattr__(self, "maximum_temperature_c", maximum_temperature_c)
        object.__setattr__(self, "temperature_origin_c", temperature_origin_c)
        object.__setattr__(self, "coefficients", coefficients)
        self._validate_shape()

    def resistance_ratio_unchecked(self, temperature_c: float) -> float:
        """Evaluate this source segment without range routing."""
        x = temperature_c - self.temperature_origin_c
        return _polynomial_value(self.coefficients, x)

    def resistance_ratio_slope_unchecked(self, temperature_c: float) -> float:
        """Evaluate the analytical source-segment slope."""
        x = temperature_c - self.temperature_origin_c
        slope_coefficients = _polynomial_derivative(self.coefficients)
        return _polynomial_value(slope_coefficients, x)

    def _validate_shape(self) -> None:
        lower_x = self.minimum_temperature_c - self.temperature_origin_c
        upper_x = self.maximum_temperature_c - self.temperature_origin_c
        slope_coefficients = _polynomial_derivative(self.coefficients)
        second_derivative_coefficients = _polynomial_derivative(slope_coefficients)

        try:
            minimum_ratio = _polynomial_value(self.coefficients, lower_x)
            maximum_ratio = _polynomial_value(self.coefficients, upper_x)
            slope_extrema_x = _polynomial_roots_in_interval(
                second_derivative_coefficients,
                lower_x,
                upper_x,
            )
        except OverflowError as exc:
            raise ValueError(
                "Piecewise polynomial calculations must remain finite"
            ) from exc

        if not math.isfinite(minimum_ratio) or not math.isfinite(maximum_ratio):
            raise ValueError("Piecewise polynomial resistance ratio must remain finite")
        if minimum_ratio <= 0.0:
            raise ValueError(
                "Piecewise polynomial resistance ratio must remain positive"
            )

        for x in (lower_x, *slope_extrema_x, upper_x):
            try:
                slope = _polynomial_value(slope_coefficients, x)
            except OverflowError as exc:
                raise ValueError(
                    "Piecewise polynomial slope must remain finite"
                ) from exc
            if not math.isfinite(slope):
                raise ValueError("Piecewise polynomial slope must remain finite")
            if slope <= 0.0:
                raise ValueError(
                    "Piecewise polynomial segment must be strictly increasing "
                    "over its supported range"
                )


@dataclass(frozen=True, slots=True)
class PiecewisePolynomialRTDCurve:
    """Normalized RTD characteristic composed of polynomial segments.

    Source segments are preserved exactly. When a published piecewise fit is
    intended to represent one continuous characteristic but its independently
    rounded segment coefficients leave tiny numerical discontinuities,
    ``maximum_continuity_adjustment_ratio`` can explicitly authorize bounded
    additive adjustments to the normalized constant term of each segment.

    Stitching is anchored at ``reference_temperature_c`` so the declared
    reference resistance remains exact, then propagated outward. Derivatives
    are unchanged because only constant terms are shifted. This is preferable
    to silently accepting gaps/overlaps, which would make resistance-to-
    temperature inversion non-unique or undefined near a join.

    At an interior segment boundary, ``resistance_ratio_slope`` returns the
    right-hand segment slope. The final endpoint uses the last segment. This
    makes sensitivity deterministic even when a source fit is C0-continuous
    but not exactly C1-continuous at printed coefficient precision.
    """

    name: str
    segments: tuple[PolynomialRTDSegment, ...]
    reference_temperature_c: float
    maximum_continuity_adjustment_ratio: float = 0.0
    _continuity_adjustments: tuple[float, ...] = field(
        init=False, repr=False, compare=False
    )
    _join_temperatures: tuple[float, ...] = field(init=False, repr=False, compare=False)
    _join_ratios: tuple[float, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        segments = tuple(self.segments)
        reference_temperature_c = _as_float(
            self.reference_temperature_c,
            name="Reference temperature",
        )
        maximum_adjustment = _as_float(
            self.maximum_continuity_adjustment_ratio,
            name="Maximum continuity adjustment ratio",
        )

        if not segments:
            raise ValueError("At least one piecewise polynomial segment is required")
        if not all(isinstance(segment, PolynomialRTDSegment) for segment in segments):
            raise TypeError(
                "Piecewise curve segments must be PolynomialRTDSegment values"
            )
        if not math.isfinite(reference_temperature_c):
            raise ValueError("Reference temperature must be finite")
        if not math.isfinite(maximum_adjustment):
            raise ValueError("Maximum continuity adjustment ratio must be finite")
        if maximum_adjustment < 0.0:
            raise ValueError("Maximum continuity adjustment ratio must not be negative")

        for previous, current in zip(segments, segments[1:], strict=False):
            if previous.maximum_temperature_c < current.minimum_temperature_c:
                raise ValueError(
                    "Piecewise polynomial segments must not contain temperature gaps"
                )
            if previous.maximum_temperature_c > current.minimum_temperature_c:
                raise ValueError("Piecewise polynomial segments must not overlap")

        minimum_temperature_c = segments[0].minimum_temperature_c
        maximum_temperature_c = segments[-1].maximum_temperature_c
        if not (
            minimum_temperature_c <= reference_temperature_c <= maximum_temperature_c
        ):
            raise ValueError(
                "Reference temperature must lie within the piecewise range"
            )

        anchor_index = self._segment_index_for_temperature_in(
            segments, reference_temperature_c
        )
        adjustments = [0.0] * len(segments)

        anchor_ratio = segments[anchor_index].resistance_ratio_unchecked(
            reference_temperature_c
        )
        reference_error = anchor_ratio - 1.0
        reference_roundoff = 64.0 * math.ulp(max(abs(anchor_ratio), 1.0))
        if abs(reference_error) > reference_roundoff:
            raise ValueError(
                "The segment containing the reference temperature must evaluate "
                "to a normalized resistance ratio of 1"
            )
        # Normalize only machine-roundoff at the semantic Rref anchor. A
        # source-level reference mismatch is rejected above even when join
        # stitching is enabled, because changing Rref would change the model's
        # stated physical meaning rather than merely reconciling rounded joins.
        adjustments[anchor_index] = -reference_error

        for index in range(anchor_index + 1, len(segments)):
            boundary_c = segments[index].minimum_temperature_c
            previous_ratio = (
                segments[index - 1].resistance_ratio_unchecked(boundary_c)
                + adjustments[index - 1]
            )
            current_ratio = segments[index].resistance_ratio_unchecked(boundary_c)
            adjustment = previous_ratio - current_ratio
            self._validate_adjustment(
                adjustment,
                maximum_adjustment=maximum_adjustment,
                scale=max(abs(previous_ratio), abs(current_ratio), 1.0),
                context=f"segment join at {boundary_c:g} °C",
            )
            adjustments[index] = adjustment

        for index in range(anchor_index - 1, -1, -1):
            boundary_c = segments[index].maximum_temperature_c
            next_ratio = (
                segments[index + 1].resistance_ratio_unchecked(boundary_c)
                + adjustments[index + 1]
            )
            current_ratio = segments[index].resistance_ratio_unchecked(boundary_c)
            adjustment = next_ratio - current_ratio
            self._validate_adjustment(
                adjustment,
                maximum_adjustment=maximum_adjustment,
                scale=max(abs(next_ratio), abs(current_ratio), 1.0),
                context=f"segment join at {boundary_c:g} °C",
            )
            adjustments[index] = adjustment

        for segment, adjustment in zip(segments, adjustments, strict=True):
            minimum_ratio = (
                segment.resistance_ratio_unchecked(segment.minimum_temperature_c)
                + adjustment
            )
            maximum_ratio = (
                segment.resistance_ratio_unchecked(segment.maximum_temperature_c)
                + adjustment
            )
            if not math.isfinite(minimum_ratio) or not math.isfinite(maximum_ratio):
                raise ValueError(
                    "Adjusted piecewise resistance ratio must remain finite"
                )
            if minimum_ratio <= 0.0:
                raise ValueError(
                    "Adjusted piecewise resistance ratio must remain positive"
                )

        join_temperatures = tuple(
            segment.maximum_temperature_c for segment in segments[:-1]
        )
        join_ratios = tuple(
            segments[index].resistance_ratio_unchecked(boundary_c) + adjustments[index]
            for index, boundary_c in enumerate(join_temperatures)
        )

        object.__setattr__(self, "segments", segments)
        object.__setattr__(self, "reference_temperature_c", reference_temperature_c)
        object.__setattr__(
            self, "maximum_continuity_adjustment_ratio", maximum_adjustment
        )
        object.__setattr__(self, "_continuity_adjustments", tuple(adjustments))
        object.__setattr__(self, "_join_temperatures", join_temperatures)
        object.__setattr__(self, "_join_ratios", join_ratios)

    @property
    def minimum_temperature_c(self) -> float:
        """Return the first segment's lower temperature bound."""
        return self.segments[0].minimum_temperature_c

    @property
    def maximum_temperature_c(self) -> float:
        """Return the final segment's upper temperature bound."""
        return self.segments[-1].maximum_temperature_c

    @property
    def continuity_adjustments(self) -> tuple[float, ...]:
        """Return additive normalized-ratio offsets applied to source segments."""
        return self._continuity_adjustments

    def resistance_ratio(self, temperature_c: float) -> float:
        """Return the stitched normalized resistance ratio R(T) / Rref."""
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)

        if temperature == self.reference_temperature_c:
            return 1.0
        for boundary_c, boundary_ratio in zip(
            self._join_temperatures, self._join_ratios, strict=True
        ):
            if temperature == boundary_c:
                return boundary_ratio

        index = self._segment_index_for_temperature(temperature)
        return self._resistance_ratio_unchecked(index, temperature)

    def resistance_ratio_slope(self, temperature_c: float) -> float:
        """Return the active segment's analytical slope d(R/Rref)/dT."""
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)
        index = self._segment_index_for_temperature(temperature)
        return self.segments[index].resistance_ratio_slope_unchecked(temperature)

    def temperature_from_resistance_ratio(self, resistance_ratio: float) -> float:
        """Invert the stitched characteristic by bounded global bisection."""
        ratio = _as_float(resistance_ratio, name="Resistance ratio")
        minimum_ratio, maximum_ratio = self._resistance_ratio_bounds()
        ratio = _validated_resistance_ratio_at_bounds(
            ratio,
            minimum_ratio=minimum_ratio,
            maximum_ratio=maximum_ratio,
        )

        if ratio == minimum_ratio:
            return self.minimum_temperature_c
        if ratio == maximum_ratio:
            return self.maximum_temperature_c
        if ratio == 1.0:
            return self.reference_temperature_c
        for boundary_c, boundary_ratio in zip(
            self._join_temperatures, self._join_ratios, strict=True
        ):
            if ratio == boundary_ratio:
                return boundary_c

        lower_c = self.minimum_temperature_c
        upper_c = self.maximum_temperature_c
        for _ in range(_BISECTION_ITERATIONS):
            midpoint_c = (lower_c + upper_c) / 2.0
            midpoint_ratio = self._resistance_ratio_at_temperature(midpoint_c)
            if midpoint_ratio < ratio:
                lower_c = midpoint_c
            else:
                upper_c = midpoint_c
        return (lower_c + upper_c) / 2.0

    @staticmethod
    def _validate_adjustment(
        adjustment: float,
        *,
        maximum_adjustment: float,
        scale: float,
        context: str,
    ) -> None:
        if not math.isfinite(adjustment):
            raise ValueError("Continuity adjustment must remain finite")

        # Even algebraically continuous source polynomials can evaluate a join
        # a few representable floats apart because each side follows a different
        # operation sequence.  That machine-roundoff allowance is automatic; a
        # larger source-level discontinuity requires explicit opt-in.
        roundoff_allowance = 64.0 * math.ulp(scale)
        permitted = max(maximum_adjustment, roundoff_allowance)
        if abs(adjustment) > permitted:
            raise ValueError(
                f"Piecewise polynomial {context} requires normalized-ratio "
                f"adjustment {adjustment:.12g}, exceeding the declared maximum "
                f"{maximum_adjustment:.12g}"
            )

    @staticmethod
    def _segment_index_for_temperature_in(
        segments: tuple[PolynomialRTDSegment, ...],
        temperature_c: float,
    ) -> int:
        for index, segment in enumerate(segments):
            is_last = index == len(segments) - 1
            if segment.minimum_temperature_c <= temperature_c and (
                temperature_c < segment.maximum_temperature_c
                or (is_last and temperature_c <= segment.maximum_temperature_c)
            ):
                return index
        raise ValueError("Temperature is outside the piecewise segment range")

    def _segment_index_for_temperature(self, temperature_c: float) -> int:
        return self._segment_index_for_temperature_in(self.segments, temperature_c)

    def _resistance_ratio_unchecked(self, index: int, temperature_c: float) -> float:
        return (
            self.segments[index].resistance_ratio_unchecked(temperature_c)
            + self._continuity_adjustments[index]
        )

    def _resistance_ratio_at_temperature(self, temperature_c: float) -> float:
        if temperature_c == self.reference_temperature_c:
            return 1.0
        for boundary_c, boundary_ratio in zip(
            self._join_temperatures, self._join_ratios, strict=True
        ):
            if temperature_c == boundary_c:
                return boundary_ratio
        index = self._segment_index_for_temperature(temperature_c)
        return self._resistance_ratio_unchecked(index, temperature_c)

    def _validate_temperature(self, temperature_c: float) -> None:
        if not math.isfinite(temperature_c):
            raise ValueError("Temperature must be finite")
        if not (
            self.minimum_temperature_c <= temperature_c <= self.maximum_temperature_c
        ):
            raise RTDOutOfRangeError(
                "Temperature must be between "
                f"{self.minimum_temperature_c:g} °C and "
                f"{self.maximum_temperature_c:g} °C"
            )

    def _resistance_ratio_bounds(self) -> tuple[float, float]:
        return (
            self._resistance_ratio_unchecked(0, self.minimum_temperature_c),
            self._resistance_ratio_unchecked(
                len(self.segments) - 1, self.maximum_temperature_c
            ),
        )


@dataclass(frozen=True, slots=True)
class PolynomialRTDCurve:
    """Normalized RTD characteristic represented by a power-series polynomial.

    ``coefficients`` contains the first- and higher-order terms only. For
    ``x = T - Tref``, the normalized characteristic is

    ``R(T) / Rref = 1 + c1*x + c2*x**2 + ... + cn*x**n``.

    The curve validates the actual polynomial over its declared range. It
    rejects characteristics that become non-finite, non-positive, or whose
    analytical slope reaches zero or becomes negative. The slope extrema are
    located from the real roots of the second derivative rather than from a
    coarse sampling grid, so narrow non-monotonic regions cannot hide between
    arbitrary test points.
    """

    name: str
    coefficients: tuple[float, ...]
    reference_temperature_c: float
    minimum_temperature_c: float
    maximum_temperature_c: float

    def __post_init__(self) -> None:
        coefficients = tuple(
            _as_float(value, name=f"Polynomial coefficient c{index}")
            for index, value in enumerate(self.coefficients, start=1)
        )
        reference_temperature_c = _as_float(
            self.reference_temperature_c,
            name="Reference temperature",
        )
        minimum_temperature_c = _as_float(
            self.minimum_temperature_c,
            name="Minimum temperature",
        )
        maximum_temperature_c = _as_float(
            self.maximum_temperature_c,
            name="Maximum temperature",
        )

        if not coefficients:
            raise ValueError("At least one polynomial coefficient is required")
        if len(coefficients) > _MAX_POLYNOMIAL_DEGREE:
            raise ValueError(
                f"Polynomial degree must not exceed {_MAX_POLYNOMIAL_DEGREE}"
            )
        if not all(math.isfinite(value) for value in coefficients):
            raise ValueError("Polynomial coefficients must be finite")
        if not math.isfinite(reference_temperature_c):
            raise ValueError("Reference temperature must be finite")
        if not math.isfinite(minimum_temperature_c):
            raise ValueError("Minimum temperature must be finite")
        if not math.isfinite(maximum_temperature_c):
            raise ValueError("Maximum temperature must be finite")
        if minimum_temperature_c >= maximum_temperature_c:
            raise ValueError("Minimum temperature must be below maximum temperature")

        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "reference_temperature_c", reference_temperature_c)
        object.__setattr__(self, "minimum_temperature_c", minimum_temperature_c)
        object.__setattr__(self, "maximum_temperature_c", maximum_temperature_c)
        self._validate_curve_shape()

    def resistance_ratio(self, temperature_c: float) -> float:
        """Return the normalized resistance ratio R(T) / Rref."""
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)
        return self._resistance_ratio_unchecked(temperature)

    def resistance_ratio_slope(self, temperature_c: float) -> float:
        """Return the exact analytical slope d(R/Rref)/dT."""
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)
        return self._resistance_ratio_slope_unchecked(temperature)

    def temperature_from_resistance_ratio(
        self,
        resistance_ratio: float,
    ) -> float:
        """Invert a normalized resistance ratio by bounded bisection."""
        ratio = _as_float(resistance_ratio, name="Resistance ratio")
        minimum_ratio, maximum_ratio = self._resistance_ratio_bounds()
        ratio = _validated_resistance_ratio_at_bounds(
            ratio,
            minimum_ratio=minimum_ratio,
            maximum_ratio=maximum_ratio,
        )

        if ratio == minimum_ratio:
            return self.minimum_temperature_c
        if ratio == maximum_ratio:
            return self.maximum_temperature_c
        if (
            self.minimum_temperature_c
            <= self.reference_temperature_c
            <= self.maximum_temperature_c
            and ratio == 1.0
        ):
            return self.reference_temperature_c

        lower_c = self.minimum_temperature_c
        upper_c = self.maximum_temperature_c
        for _ in range(_BISECTION_ITERATIONS):
            midpoint_c = (lower_c + upper_c) / 2.0
            midpoint_ratio = self._resistance_ratio_unchecked(midpoint_c)
            if midpoint_ratio < ratio:
                lower_c = midpoint_c
            else:
                upper_c = midpoint_c
        return (lower_c + upper_c) / 2.0

    def _resistance_ratio_unchecked(self, temperature_c: float) -> float:
        x = temperature_c - self.reference_temperature_c
        return 1.0 + x * _polynomial_value(self.coefficients, x)

    def _resistance_ratio_slope_unchecked(
        self,
        temperature_c: float,
    ) -> float:
        x = temperature_c - self.reference_temperature_c
        ratio_coefficients = (1.0, *self.coefficients)
        slope_coefficients = _polynomial_derivative(ratio_coefficients)
        return _polynomial_value(slope_coefficients, x)

    def _validate_curve_shape(self) -> None:
        lower_x = self.minimum_temperature_c - self.reference_temperature_c
        upper_x = self.maximum_temperature_c - self.reference_temperature_c
        ratio_coefficients = (1.0, *self.coefficients)
        slope_coefficients = _polynomial_derivative(ratio_coefficients)
        second_derivative_coefficients = _polynomial_derivative(slope_coefficients)

        try:
            minimum_ratio = _polynomial_value(ratio_coefficients, lower_x)
            maximum_ratio = _polynomial_value(ratio_coefficients, upper_x)
            slope_extrema_x = _polynomial_roots_in_interval(
                second_derivative_coefficients,
                lower_x,
                upper_x,
            )
        except OverflowError as exc:
            raise ValueError("Polynomial calculations must remain finite") from exc

        if not math.isfinite(minimum_ratio) or not math.isfinite(maximum_ratio):
            raise ValueError("Polynomial resistance ratio must remain finite")
        if minimum_ratio <= 0.0:
            raise ValueError("Polynomial resistance ratio must remain positive")

        for x in (lower_x, *slope_extrema_x, upper_x):
            try:
                slope = _polynomial_value(slope_coefficients, x)
            except OverflowError as exc:
                raise ValueError("Polynomial slope must remain finite") from exc
            if not math.isfinite(slope):
                raise ValueError("Polynomial slope must remain finite")
            if slope <= 0.0:
                raise ValueError(
                    "Polynomial RTD curve must be strictly increasing over "
                    "its supported range"
                )

    def _validate_temperature(self, temperature_c: float) -> None:
        if not math.isfinite(temperature_c):
            raise ValueError("Temperature must be finite")
        if not (
            self.minimum_temperature_c <= temperature_c <= self.maximum_temperature_c
        ):
            raise RTDOutOfRangeError(
                "Temperature must be between "
                f"{self.minimum_temperature_c:g} °C and "
                f"{self.maximum_temperature_c:g} °C"
            )

    def _resistance_ratio_bounds(self) -> tuple[float, float]:
        return (
            self._resistance_ratio_unchecked(self.minimum_temperature_c),
            self._resistance_ratio_unchecked(self.maximum_temperature_c),
        )


def _curve_from_definition(
    definition: _definitions.CharacteristicDefinition,
) -> RTDCurve:
    """Construct a validated runtime curve from authoritative source metadata."""
    if isinstance(
        definition,
        _definitions.CallendarVanDusenCharacteristicDefinition,
    ):
        return CallendarVanDusenCurve(
            name=definition.display_name,
            a=definition.a,
            b=definition.b,
            c=definition.c,
            minimum_temperature_c=definition.minimum_temperature_c,
            maximum_temperature_c=definition.maximum_temperature_c,
        )

    if isinstance(definition, _definitions.PolynomialCharacteristicDefinition):
        return PolynomialRTDCurve(
            name=definition.display_name,
            coefficients=definition.coefficients,
            reference_temperature_c=definition.reference_temperature_c,
            minimum_temperature_c=definition.minimum_temperature_c,
            maximum_temperature_c=definition.maximum_temperature_c,
        )

    if isinstance(
        definition,
        _definitions.PiecewisePolynomialCharacteristicDefinition,
    ):
        return PiecewisePolynomialRTDCurve(
            name=definition.display_name,
            segments=tuple(
                PolynomialRTDSegment(
                    minimum_temperature_c=segment.minimum_temperature_c,
                    maximum_temperature_c=segment.maximum_temperature_c,
                    coefficients=segment.coefficients,
                    temperature_origin_c=segment.temperature_origin_c,
                )
                for segment in definition.segments
            ),
            reference_temperature_c=definition.reference_temperature_c,
            maximum_continuity_adjustment_ratio=(
                definition.maximum_continuity_adjustment_ratio
            ),
        )

    raise TypeError(
        f"Unsupported built-in characteristic definition: {type(definition)!r}"
    )


_BUILTIN_RTD_CURVES = {
    characteristic_id: _curve_from_definition(definition)
    for characteristic_id, definition in (
        _definitions.BUILTIN_CHARACTERISTIC_DEFINITIONS.items()
    )
}

# This immutable registry is the runtime view of the authoritative definitions.
# New built-in scientific data belongs in _definitions.py rather than here.
BUILTIN_RTD_CURVES: Mapping[str, RTDCurve] = MappingProxyType(_BUILTIN_RTD_CURVES)


def _require_builtin_curve_type(
    characteristic_id: str,
    expected_type: type[_CurveT],
) -> _CurveT:
    """Return one built-in curve after verifying its expected concrete type."""
    curve = BUILTIN_RTD_CURVES[characteristic_id]
    if not isinstance(curve, expected_type):
        raise TypeError(
            "Built-in RTD characteristic constructed with unexpected curve type: "
            f"{characteristic_id!r} -> {type(curve).__name__}, expected "
            f"{expected_type.__name__}"
        )
    return curve


IEC_60751_PT385 = _require_builtin_curve_type(
    "iec60751_pt385",
    CallendarVanDusenCurve,
)
NI_6180_DIN_43760 = _require_builtin_curve_type(
    "ni6180_din43760",
    PolynomialRTDCurve,
)
NI_5000_TK5000 = _require_builtin_curve_type(
    "ni5000_tk5000",
    PolynomialRTDCurve,
)
NI_6720_NORTH_AMERICAN = _require_builtin_curve_type(
    "ni6720_north_american",
    PiecewisePolynomialRTDCurve,
)
