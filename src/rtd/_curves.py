# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Internal RTD resistance-ratio curve definitions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from ._validation import as_float as _as_float

__all__ = [
    "CallendarVanDusenCurve",
    "IEC_60751_PT385",
    "RTDCurve",
]

_BISECTION_ITERATIONS = 60


class RTDCurve(Protocol):
    """Internal interface for a normalized RTD resistance curve."""

    @property
    def name(self) -> str:
        """Return the descriptive name of the curve."""
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
        """Return R(T) / R0 for a temperature in Celsius."""
        ...

    def resistance_ratio_slope(self, temperature_c: float) -> float:
        """Return d(R/R0)/dT at a temperature in Celsius."""
        ...

    def temperature_from_resistance_ratio(
        self,
        resistance_ratio: float,
    ) -> float:
        """Return temperature in Celsius for R(T) / R0."""
        ...


@dataclass(frozen=True, slots=True)
class CallendarVanDusenCurve:
    """A normalized Callendar-Van Dusen platinum RTD curve."""

    name: str
    a: float
    b: float
    c: float
    minimum_temperature_c: float
    maximum_temperature_c: float

    def __post_init__(self) -> None:
        coefficients = (self.a, self.b, self.c)
        if not all(math.isfinite(value) for value in coefficients):
            raise ValueError("Curve coefficients must be finite")

        if not math.isfinite(self.minimum_temperature_c):
            raise ValueError("Minimum temperature must be finite")
        if not math.isfinite(self.maximum_temperature_c):
            raise ValueError("Maximum temperature must be finite")
        if self.minimum_temperature_c >= self.maximum_temperature_c:
            raise ValueError(
                "Minimum temperature must be below maximum temperature"
            )
        if not (
            self.minimum_temperature_c <= 0.0
            <= self.maximum_temperature_c
        ):
            raise ValueError("Curve temperature range must include 0 °C")

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
        discriminant = (
            quadratic_b**2 - 4.0 * quadratic_a * quadratic_c
        )
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
            slope += (
                self.c
                * temperature_c**2
                * (4.0 * temperature_c - 300.0)
            )
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
        if ratio == 1.0:
            return 0.0

        if ratio > 1.0:
            return self._nonnegative_ratio_to_celsius(ratio)

        return self._negative_ratio_to_celsius(ratio)

    def _resistance_ratio_unchecked(self, temperature_c: float) -> float:
        resistance_ratio = (
            1.0
            + self.a * temperature_c
            + self.b * temperature_c**2
        )

        if temperature_c < 0.0:
            resistance_ratio += (
                self.c
                * (temperature_c - 100.0)
                * temperature_c**3
            )

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
            discriminant = (
                self.a**2
                - 4.0 * self.b * (1.0 - resistance_ratio)
            )

            if discriminant < 0.0:
                raise ValueError(
                    f"Resistance ratio cannot be converted using {self.name}"
                )

            # The direct quadratic root ``(-A + sqrt(D)) / (2B)``
            # suffers cancellation for ordinary platinum RTD coefficients
            # because ``sqrt(D)`` is close to ``A``.  This algebraically
            # equivalent form keeps the numerator well-conditioned.
            temperature_c = (
                2.0 * (1.0 - resistance_ratio)
            ) / (-self.a - math.sqrt(discriminant))

        # The resistance ratio was already validated against a strictly
        # increasing curve, so its mathematical inverse is necessarily in
        # range.  A second strict comparison here can only turn harmless
        # inverse-rounding noise near the endpoint into a false rejection.
        return temperature_c

    def _negative_ratio_to_celsius(
        self,
        resistance_ratio: float,
    ) -> float:
        lower_c = self.minimum_temperature_c
        upper_c = 0.0

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
            self.minimum_temperature_c
            <= temperature_c
            <= self.maximum_temperature_c
        ):
            raise ValueError(
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
        """Validate and normalize a ratio at floating-point boundaries.

        A public model converts a measured resistance back to a ratio with
        ``R / R0``.  At an exact model endpoint, the preceding ``R0 * ratio``
        multiplication can make that round trip land one representable float
        just outside the original ratio.  Accepting exactly that one-ULP
        neighbor preserves the model's own endpoint round trip without
        admitting a materially out-of-range measurement.
        """
        if not math.isfinite(resistance_ratio):
            raise ValueError("Resistance ratio must be finite")
        if resistance_ratio <= 0.0:
            raise ValueError("Resistance ratio must be greater than zero")

        minimum_ratio, maximum_ratio = self._resistance_ratio_bounds()
        minimum_neighbor = math.nextafter(minimum_ratio, -math.inf)
        maximum_neighbor = math.nextafter(maximum_ratio, math.inf)

        if resistance_ratio < minimum_ratio:
            if resistance_ratio == minimum_neighbor:
                return minimum_ratio
            raise ValueError("Resistance ratio is below the supported range")
        if resistance_ratio > maximum_ratio:
            if resistance_ratio == maximum_neighbor:
                return maximum_ratio
            raise ValueError("Resistance ratio is above the supported range")

        return resistance_ratio


IEC_60751_PT385 = CallendarVanDusenCurve(
    name="IEC 60751 PT-385 curve",
    a=3.9083e-3,
    b=-5.775e-7,
    c=-4.183e-12,
    minimum_temperature_c=-200.0,
    maximum_temperature_c=850.0,
)
