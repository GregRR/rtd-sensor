# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public configurable RTD models.

The built-in :mod:`rtd_sensor.pt100`, :mod:`rtd_sensor.pt500`, and
:mod:`rtd_sensor.pt1000` modules remain the simplest interfaces for nominal
IEC 60751 sensors. This module provides advanced models for individually
characterized RTDs, platinum RTDs with user-supplied Callendar-Van Dusen
coefficient sets, and generic RTD characteristics defined by a traceable
polynomial. Callendar-Van Dusen is a
platinum-specific model; non-platinum RTDs should use a characteristic form
that matches their documented resistance-temperature relationship.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from . import _curves
from ._curves import CallendarVanDusenCurve as _CallendarVanDusenCurve
from ._curves import PiecewisePolynomialRTDCurve as _PiecewisePolynomialRTDCurve
from ._curves import PolynomialRTDCurve as _PolynomialRTDCurve
from ._curves import PolynomialRTDSegment as _PolynomialRTDSegment
from ._models import RTDModel as _RTDModel
from ._validation import as_float as _as_float

__all__ = [
    "CallendarVanDusenRTDModel",
    "IEC60751RTDModel",
    "PiecewisePolynomialRTDModel",
    "PiecewisePolynomialSegment",
    "PolynomialRTDModel",
]


@dataclass(frozen=True, slots=True)
class IEC60751RTDModel:
    """Configurable RTD using the IEC 60751 PT-385 curve.

    This model is useful when an individual sensor has a characterized
    or calibrated R0 value but still uses the standard IEC 60751 curve.
    The optional temperature limits can restrict the model to a probe's
    declared or calibrated operating range without changing the
    underlying standardized curve.

    Args:
        r0_ohms: Sensor resistance at 0 °C in ohms.
        name: Human-readable model or probe name.
        minimum_temperature_c: Lowest temperature at which this model
            should be used.
        maximum_temperature_c: Highest temperature at which this model
            should be used.

    Raises:
        ValueError: If R0 or either temperature limit is invalid, if the
            limits are reversed, or if the declared range extends beyond
            the IEC 60751 PT-385 curve implemented by this package.
    """

    r0_ohms: float
    name: str = "IEC 60751 RTD"
    minimum_temperature_c: float = _curves.IEC_60751_PT385.minimum_temperature_c
    maximum_temperature_c: float = _curves.IEC_60751_PT385.maximum_temperature_c
    _model: _RTDModel = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        r0_ohms = _as_float(self.r0_ohms, name="R0")
        minimum_temperature_c = _as_float(
            self.minimum_temperature_c,
            name="Minimum temperature",
        )
        maximum_temperature_c = _as_float(
            self.maximum_temperature_c,
            name="Maximum temperature",
        )

        if not math.isfinite(minimum_temperature_c):
            raise ValueError("Minimum temperature must be finite")
        if not math.isfinite(maximum_temperature_c):
            raise ValueError("Maximum temperature must be finite")
        if minimum_temperature_c >= maximum_temperature_c:
            raise ValueError("Minimum temperature must be below maximum temperature")
        if minimum_temperature_c < _curves.IEC_60751_PT385.minimum_temperature_c:
            raise ValueError("Minimum temperature is below the IEC 60751 PT-385 range")
        if maximum_temperature_c > _curves.IEC_60751_PT385.maximum_temperature_c:
            raise ValueError("Maximum temperature is above the IEC 60751 PT-385 range")

        model = _RTDModel(
            name=self.name,
            reference_resistance_ohms=r0_ohms,
            curve=_curves.IEC_60751_PT385,
        )

        object.__setattr__(self, "r0_ohms", model.r0_ohms)
        object.__setattr__(
            self,
            "minimum_temperature_c",
            minimum_temperature_c,
        )
        object.__setattr__(
            self,
            "maximum_temperature_c",
            maximum_temperature_c,
        )
        object.__setattr__(self, "_model", model)

    def celsius_to_resistance(self, temperature_c: float) -> float:
        """Convert Celsius to resistance using this RTD model."""
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)
        return self._model.celsius_to_resistance(temperature)

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        """Convert resistance in ohms to Celsius using this RTD model."""
        resistance = _as_float(resistance_ohms, name="Resistance")
        self._validate_resistance(resistance)
        return self._model.resistance_to_celsius(resistance)

    def resistance_sensitivity_ohms_per_celsius(
        self,
        temperature_c: float,
    ) -> float:
        """Return the exact local resistance sensitivity dR/dT."""
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)
        return self._model.resistance_sensitivity_ohms_per_celsius(temperature)

    def temperature_sensitivity_celsius_per_ohm(
        self,
        temperature_c: float,
    ) -> float:
        """Return the exact local inverse sensitivity dT/dR."""
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)
        return self._model.temperature_sensitivity_celsius_per_ohm(temperature)

    def _validate_temperature(self, temperature_c: float) -> None:
        if not math.isfinite(temperature_c):
            raise ValueError("Temperature must be finite")
        if not (
            self.minimum_temperature_c <= temperature_c <= self.maximum_temperature_c
        ):
            raise ValueError(
                "Temperature must be between "
                f"{self.minimum_temperature_c:g} °C and "
                f"{self.maximum_temperature_c:g} °C"
            )

    def _validate_resistance(self, resistance_ohms: float) -> None:
        if not math.isfinite(resistance_ohms):
            raise ValueError("Resistance must be finite")
        if resistance_ohms <= 0.0:
            raise ValueError("Resistance must be greater than zero")

        minimum_resistance = self._model.celsius_to_resistance(
            self.minimum_temperature_c
        )
        maximum_resistance = self._model.celsius_to_resistance(
            self.maximum_temperature_c
        )

        if resistance_ohms < minimum_resistance:
            raise ValueError("Resistance is below the declared model range")
        if resistance_ohms > maximum_resistance:
            raise ValueError("Resistance is above the declared model range")


@dataclass(frozen=True, slots=True, kw_only=True)
class CallendarVanDusenRTDModel:
    """Platinum RTD model with user-supplied CVD coefficients.

    This model is intended for coefficient sets supplied by a calibration
    certificate, manufacturer, or another traceable technical source. It
    uses the IEC-style ``R0, A, B, C`` form of the Callendar-Van Dusen
    equation, but a model created with custom coefficients is *not*
    automatically an IEC 60751 compliant model.

    ``C`` is used only below 0 °C. It may therefore be omitted when the
    declared valid range is entirely at or above 0 °C. A negative-temperature
    range requires an explicit ``C`` value.

    The supplied coefficients must produce a finite, positive-resistance,
    strictly increasing curve over the declared model range. ``R0`` remains
    the equation's resistance reference at 0 °C even when that reference
    temperature lies outside the declared validity interval; behavior outside
    the traceable interval is not treated as part of the model. This validates
    the mathematical behavior actually required by the converter rather than
    assuming that custom coefficients have the same signs or validity range as
    the standard IEC coefficient set.

    Args:
        r0_ohms: Sensor resistance at 0 °C in ohms.
        a: Callendar-Van Dusen A coefficient in °C⁻¹.
        b: Callendar-Van Dusen B coefficient in °C⁻².
        c: Callendar-Van Dusen C coefficient in °C⁻⁴. May be ``None`` only
            when ``minimum_temperature_c`` is at or above 0 °C.
        minimum_temperature_c: Lowest temperature for which the supplied
            coefficient set is declared valid.
        maximum_temperature_c: Highest temperature for which the supplied
            coefficient set is declared valid.
        name: Human-readable model or probe name.
        coefficient_source: Optional free-form provenance such as a
            calibration-certificate identifier, manufacturer document, or
            other source of the coefficient set. It is retained as metadata
            and does not affect calculations.

    Raises:
        ValueError: If any numerical input is invalid, if the range is
            reversed, if ``C`` is missing for a negative-temperature range,
            or if the coefficients do not define a finite, positive, strictly
            increasing RTD curve over the declared validity interval.
    """

    r0_ohms: float
    a: float
    b: float
    minimum_temperature_c: float
    maximum_temperature_c: float
    c: float | None = None
    name: str = "Custom Callendar-Van Dusen RTD"
    coefficient_source: str | None = None
    _model: _RTDModel = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        r0_ohms = _as_float(self.r0_ohms, name="R0")
        a = _as_float(self.a, name="A coefficient")
        b = _as_float(self.b, name="B coefficient")
        minimum_temperature_c = _as_float(
            self.minimum_temperature_c,
            name="Minimum temperature",
        )
        maximum_temperature_c = _as_float(
            self.maximum_temperature_c,
            name="Maximum temperature",
        )
        c = None if self.c is None else _as_float(self.c, name="C coefficient")

        if not math.isfinite(r0_ohms):
            raise ValueError("R0 must be finite")
        if r0_ohms <= 0.0:
            raise ValueError("R0 must be greater than zero")
        if not math.isfinite(a):
            raise ValueError("A coefficient must be finite")
        if not math.isfinite(b):
            raise ValueError("B coefficient must be finite")
        if c is not None and not math.isfinite(c):
            raise ValueError("C coefficient must be finite")
        if not math.isfinite(minimum_temperature_c):
            raise ValueError("Minimum temperature must be finite")
        if not math.isfinite(maximum_temperature_c):
            raise ValueError("Maximum temperature must be finite")
        if minimum_temperature_c >= maximum_temperature_c:
            raise ValueError("Minimum temperature must be below maximum temperature")

        if minimum_temperature_c < 0.0 and c is None:
            raise ValueError(
                "C coefficient is required for a negative-temperature range"
            )

        effective_c = 0.0 if c is None else c

        # R0 is the CVD equation's 0 °C reference resistance, but a traceable
        # calibration or manufacturer fit may be declared valid only over a
        # narrower interval that does not include 0 °C.  Expanding that interval
        # merely to include the reference point would validate behavior the
        # source never claimed and can falsely reject an otherwise valid
        # restricted fit.  Keep the mathematical validation and inversion
        # domain exactly equal to the caller's declared validity interval.
        curve = _CallendarVanDusenCurve(
            name=f"{self.name} Callendar-Van Dusen curve",
            a=a,
            b=b,
            c=effective_c,
            minimum_temperature_c=minimum_temperature_c,
            maximum_temperature_c=maximum_temperature_c,
        )

        coefficient_source = self.coefficient_source
        if coefficient_source is not None:
            coefficient_source = coefficient_source.strip()
            if not coefficient_source:
                raise ValueError("Coefficient source must not be empty")

        model = _RTDModel(
            name=self.name,
            reference_resistance_ohms=r0_ohms,
            curve=curve,
        )

        object.__setattr__(self, "r0_ohms", model.r0_ohms)
        object.__setattr__(self, "a", a)
        object.__setattr__(self, "b", b)
        object.__setattr__(self, "c", c)
        object.__setattr__(
            self,
            "minimum_temperature_c",
            minimum_temperature_c,
        )
        object.__setattr__(
            self,
            "maximum_temperature_c",
            maximum_temperature_c,
        )
        object.__setattr__(self, "coefficient_source", coefficient_source)
        object.__setattr__(self, "_model", model)

    def celsius_to_resistance(self, temperature_c: float) -> float:
        """Convert Celsius to resistance using this coefficient set."""
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)
        return self._model.celsius_to_resistance(temperature)

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        """Convert resistance in ohms to Celsius using this coefficient set."""
        resistance = _as_float(resistance_ohms, name="Resistance")
        self._validate_resistance(resistance)
        return self._model.resistance_to_celsius(resistance)

    def resistance_sensitivity_ohms_per_celsius(
        self,
        temperature_c: float,
    ) -> float:
        """Return the exact local resistance sensitivity dR/dT."""
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)
        return self._model.resistance_sensitivity_ohms_per_celsius(temperature)

    def temperature_sensitivity_celsius_per_ohm(
        self,
        temperature_c: float,
    ) -> float:
        """Return the exact local inverse sensitivity dT/dR."""
        temperature = _as_float(temperature_c, name="Temperature")
        self._validate_temperature(temperature)
        return self._model.temperature_sensitivity_celsius_per_ohm(temperature)

    def _validate_temperature(self, temperature_c: float) -> None:
        if not math.isfinite(temperature_c):
            raise ValueError("Temperature must be finite")
        if not (
            self.minimum_temperature_c <= temperature_c <= self.maximum_temperature_c
        ):
            raise ValueError(
                "Temperature must be between "
                f"{self.minimum_temperature_c:g} °C and "
                f"{self.maximum_temperature_c:g} °C"
            )

    def _validate_resistance(self, resistance_ohms: float) -> None:
        if not math.isfinite(resistance_ohms):
            raise ValueError("Resistance must be finite")
        if resistance_ohms <= 0.0:
            raise ValueError("Resistance must be greater than zero")

        minimum_resistance = self._model.celsius_to_resistance(
            self.minimum_temperature_c
        )
        maximum_resistance = self._model.celsius_to_resistance(
            self.maximum_temperature_c
        )

        if resistance_ohms < minimum_resistance:
            raise ValueError("Resistance is below the declared model range")
        if resistance_ohms > maximum_resistance:
            raise ValueError("Resistance is above the declared model range")


@dataclass(frozen=True, slots=True, kw_only=True)
class PolynomialRTDModel:
    """RTD model defined by a user- or manufacturer-supplied polynomial.

    For ``x = T - reference_temperature_c``, the model evaluates

    ``R(T) = Rref * (1 + c1*x + c2*x**2 + ... + cn*x**n)``.

    ``coefficients`` therefore contains the first-order and higher-order
    normalized coefficients only; the constant term is implicitly 1 because
    ``reference_resistance_ohms`` is, by definition, the resistance at the
    reference temperature. This form can represent published low-order nickel
    characteristics today and leaves room for future RTDs referenced at a
    temperature other than 0 °C.

    The polynomial is validated over the complete declared range. Construction
    fails if resistance becomes non-finite or non-positive, or if the exact
    analytical slope reaches zero or becomes negative. Resistance-to-temperature
    conversion then uses dependency-free bounded bisection on that proven
    monotonic characteristic rather than an approximate inverse polynomial.

    Args:
        reference_resistance_ohms: Resistance in ohms at
            ``reference_temperature_c``.
        coefficients: Normalized coefficients ``(c1, c2, ..., cn)`` for the
            powers of ``T - reference_temperature_c``. Polynomial degree is
            currently limited to 12 because high-order calibration fits are
            numerically fragile and are not the intended use of this API.
        minimum_temperature_c: Lowest temperature for which the characteristic
            is declared valid.
        maximum_temperature_c: Highest temperature for which the characteristic
            is declared valid.
        reference_temperature_c: Temperature associated with
            ``reference_resistance_ohms``. Defaults to 0 °C.
        name: Human-readable model or characteristic name.
        coefficient_source: Optional provenance such as a manufacturer data
            sheet, calibration certificate, or standards document.

    Notes:
        This class represents a *single global polynomial*. Published
        piecewise-polynomial and tabulated RTD characteristics should not be
        forced into this form; dedicated representations for those models are
        planned separately.
    """

    reference_resistance_ohms: float
    coefficients: Sequence[float]
    minimum_temperature_c: float
    maximum_temperature_c: float
    reference_temperature_c: float = 0.0
    name: str = "Polynomial RTD"
    coefficient_source: str | None = None
    _model: _RTDModel = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        reference_resistance_ohms = _as_float(
            self.reference_resistance_ohms,
            name="Reference resistance",
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
        coefficients = tuple(
            _as_float(value, name=f"Polynomial coefficient c{index}")
            for index, value in enumerate(self.coefficients, start=1)
        )

        coefficient_source = self.coefficient_source
        if coefficient_source is not None:
            coefficient_source = coefficient_source.strip()
            if not coefficient_source:
                raise ValueError("Coefficient source must not be empty")

        curve = _PolynomialRTDCurve(
            name=f"{self.name} polynomial characteristic",
            coefficients=coefficients,
            reference_temperature_c=reference_temperature_c,
            minimum_temperature_c=minimum_temperature_c,
            maximum_temperature_c=maximum_temperature_c,
        )
        model = _RTDModel(
            name=self.name,
            reference_resistance_ohms=reference_resistance_ohms,
            curve=curve,
        )

        object.__setattr__(
            self,
            "reference_resistance_ohms",
            model.reference_resistance_ohms,
        )
        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "reference_temperature_c", reference_temperature_c)
        object.__setattr__(self, "minimum_temperature_c", minimum_temperature_c)
        object.__setattr__(self, "maximum_temperature_c", maximum_temperature_c)
        object.__setattr__(self, "coefficient_source", coefficient_source)
        object.__setattr__(self, "_model", model)

    def celsius_to_resistance(self, temperature_c: float) -> float:
        """Convert Celsius to resistance using this polynomial model."""
        return self._model.celsius_to_resistance(temperature_c)

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        """Convert resistance in ohms to Celsius using this polynomial model."""
        return self._model.resistance_to_celsius(resistance_ohms)

    def resistance_sensitivity_ohms_per_celsius(
        self,
        temperature_c: float,
    ) -> float:
        """Return the exact local resistance sensitivity dR/dT."""
        return self._model.resistance_sensitivity_ohms_per_celsius(temperature_c)

    def temperature_sensitivity_celsius_per_ohm(
        self,
        temperature_c: float,
    ) -> float:
        """Return the exact local inverse sensitivity dT/dR."""
        return self._model.temperature_sensitivity_celsius_per_ohm(temperature_c)


@dataclass(frozen=True, slots=True, kw_only=True)
class PiecewisePolynomialSegment:
    """One source polynomial interval for :class:`PiecewisePolynomialRTDModel`.

    Unlike :class:`PolynomialRTDModel`, ``coefficients`` includes the constant
    term because published piecewise characteristics commonly provide an
    independent full polynomial for each interval. For
    ``x = T - temperature_origin_c`` the normalized segment equation is

    ``R(T) / Rref = c0 + c1*x + c2*x**2 + ... + cn*x**n``.

    Segment bounds are closed as source metadata. During routing, an interior
    boundary belongs to the segment on its right; the final maximum belongs to
    the last segment. This deterministic convention also defines which
    one-sided analytical sensitivity is reported at a non-C1 join.
    """

    minimum_temperature_c: float
    maximum_temperature_c: float
    coefficients: Sequence[float]
    temperature_origin_c: float = 0.0

    def __post_init__(self) -> None:
        internal = _PolynomialRTDSegment(
            minimum_temperature_c=self.minimum_temperature_c,
            maximum_temperature_c=self.maximum_temperature_c,
            coefficients=tuple(self.coefficients),
            temperature_origin_c=self.temperature_origin_c,
        )
        object.__setattr__(
            self, "minimum_temperature_c", internal.minimum_temperature_c
        )
        object.__setattr__(
            self, "maximum_temperature_c", internal.maximum_temperature_c
        )
        object.__setattr__(self, "coefficients", internal.coefficients)
        object.__setattr__(self, "temperature_origin_c", internal.temperature_origin_c)


@dataclass(frozen=True, slots=True, kw_only=True)
class PiecewisePolynomialRTDModel:
    """RTD model composed of contiguous polynomial source intervals.

    This representation is intended for documented characteristics whose
    source publishes a different polynomial over each temperature interval.
    It preserves the source segment coefficients rather than fitting a new
    global equation.

    Some manufacturer piecewise fits are independently rounded and therefore
    miss exact continuity by a tiny amount even though they approximate one
    continuous physical characteristic. By default this model permits only
    machine-roundoff reconciliation at joins. A nonzero
    ``maximum_continuity_adjustment_ratio`` explicitly
    authorizes the model to add a bounded constant offset to normalized
    segment ratios solely to stitch those joins. Stitching is anchored at the
    reference temperature and propagated outward, so ``Rref`` remains exact
    and all source-segment derivatives are preserved. The applied offsets are
    exposed as ``continuity_adjustments`` for auditability.

    Args:
        reference_resistance_ohms: Resistance in ohms at
            ``reference_temperature_c``.
        segments: Ordered, contiguous source polynomial intervals.
        reference_temperature_c: Temperature associated with the reference
            resistance. Defaults to 0 °C.
        name: Human-readable model or characteristic name.
        coefficient_source: Optional provenance for the segment equations.
        maximum_continuity_adjustment_ratio: Largest absolute normalized-ratio
            constant offset permitted for any segment beyond automatic
            machine-roundoff reconciliation. The default of zero rejects any
            source-level discontinuity.

    Notes:
        A nonzero continuity adjustment changes only a segment's constant term;
        it does not alter its slope or higher-order shape. This option exists
        for traceable published approximations with demonstrated rounding at
        joins, not as a general mechanism for repairing incompatible curves.
    """

    reference_resistance_ohms: float
    segments: Sequence[PiecewisePolynomialSegment]
    reference_temperature_c: float = 0.0
    name: str = "Piecewise polynomial RTD"
    coefficient_source: str | None = None
    maximum_continuity_adjustment_ratio: float = 0.0
    continuity_adjustments: tuple[float, ...] = field(
        init=False, repr=False, compare=False
    )
    _model: _RTDModel = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        reference_resistance_ohms = _as_float(
            self.reference_resistance_ohms,
            name="Reference resistance",
        )
        reference_temperature_c = _as_float(
            self.reference_temperature_c,
            name="Reference temperature",
        )
        maximum_adjustment = _as_float(
            self.maximum_continuity_adjustment_ratio,
            name="Maximum continuity adjustment ratio",
        )
        segments = tuple(self.segments)
        if not all(
            isinstance(segment, PiecewisePolynomialSegment) for segment in segments
        ):
            raise TypeError("Segments must be PiecewisePolynomialSegment values")

        coefficient_source = self.coefficient_source
        if coefficient_source is not None:
            coefficient_source = coefficient_source.strip()
            if not coefficient_source:
                raise ValueError("Coefficient source must not be empty")

        curve = _PiecewisePolynomialRTDCurve(
            name=f"{self.name} piecewise polynomial characteristic",
            segments=tuple(
                _PolynomialRTDSegment(
                    minimum_temperature_c=segment.minimum_temperature_c,
                    maximum_temperature_c=segment.maximum_temperature_c,
                    coefficients=tuple(segment.coefficients),
                    temperature_origin_c=segment.temperature_origin_c,
                )
                for segment in segments
            ),
            reference_temperature_c=reference_temperature_c,
            maximum_continuity_adjustment_ratio=maximum_adjustment,
        )
        model = _RTDModel(
            name=self.name,
            reference_resistance_ohms=reference_resistance_ohms,
            curve=curve,
        )

        object.__setattr__(
            self,
            "reference_resistance_ohms",
            model.reference_resistance_ohms,
        )
        object.__setattr__(self, "segments", segments)
        object.__setattr__(self, "reference_temperature_c", reference_temperature_c)
        object.__setattr__(self, "coefficient_source", coefficient_source)
        object.__setattr__(
            self, "maximum_continuity_adjustment_ratio", maximum_adjustment
        )
        object.__setattr__(self, "continuity_adjustments", curve.continuity_adjustments)
        object.__setattr__(self, "_model", model)

    @property
    def minimum_temperature_c(self) -> float:
        """Return the complete characteristic's minimum temperature."""
        return self._model.minimum_temperature_c

    @property
    def maximum_temperature_c(self) -> float:
        """Return the complete characteristic's maximum temperature."""
        return self._model.maximum_temperature_c

    def celsius_to_resistance(self, temperature_c: float) -> float:
        """Convert Celsius to resistance using the piecewise model."""
        return self._model.celsius_to_resistance(temperature_c)

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        """Convert resistance in ohms to Celsius using the piecewise model."""
        return self._model.resistance_to_celsius(resistance_ohms)

    def resistance_sensitivity_ohms_per_celsius(self, temperature_c: float) -> float:
        """Return the active segment's analytical dR/dT sensitivity."""
        return self._model.resistance_sensitivity_ohms_per_celsius(temperature_c)

    def temperature_sensitivity_celsius_per_ohm(self, temperature_c: float) -> float:
        """Return the active segment's analytical dT/dR sensitivity."""
        return self._model.temperature_sensitivity_celsius_per_ohm(temperature_c)
