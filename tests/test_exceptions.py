# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import math
from collections.abc import Callable

import pytest

from rtd_sensor import catalog, exceptions, measurement, models, pt100, simulation


def test_public_exception_inheritance_preserves_legacy_catch_types() -> None:
    assert issubclass(exceptions.UnknownRTDModelError, KeyError)
    assert issubclass(exceptions.RTDOutOfRangeError, ValueError)
    assert issubclass(exceptions.InvalidRTDModelError, ValueError)
    assert issubclass(exceptions.RTDModelSelectionError, ValueError)

    for exception_type in (
        exceptions.UnknownRTDModelError,
        exceptions.RTDOutOfRangeError,
        exceptions.InvalidRTDModelError,
        exceptions.RTDModelSelectionError,
    ):
        assert issubclass(exception_type, exceptions.RTDError)


def test_unknown_model_error_string_avoids_key_error_repr_quoting() -> None:
    error = exceptions.UnknownRTDModelError("unknown model")
    assert str(error) == "unknown model"


def test_catalog_raises_unknown_model_error_for_unknown_canonical_id() -> None:
    with pytest.raises(exceptions.UnknownRTDModelError):
        catalog.get_model("cu10")

    with pytest.raises(exceptions.UnknownRTDModelError):
        catalog.model_info("cu10")


def test_measurement_raises_model_selection_error_without_consuming_reader() -> None:
    class Reader:
        def read_resistance_ohms(self) -> float:
            raise AssertionError("selection failure must occur before reading")

    with pytest.raises(exceptions.RTDModelSelectionError):
        measurement.read_temperature_celsius(
            Reader(),
            model=catalog.get_model("pt100"),
            rtd_type="pt100",
        )


def test_simulation_unsupported_type_raises_model_selection_error() -> None:
    with pytest.raises(exceptions.RTDModelSelectionError):
        simulation.FixedResistanceReader(100.0, rtd_type="cu10")


def test_builtin_conversion_raises_out_of_range_error() -> None:
    with pytest.raises(exceptions.RTDOutOfRangeError):
        pt100.celsius_to_resistance(pt100.MAX_TEMPERATURE_C + 1.0)

    maximum_resistance = pt100.celsius_to_resistance(pt100.MAX_TEMPERATURE_C)
    with pytest.raises(exceptions.RTDOutOfRangeError):
        pt100.resistance_to_celsius(maximum_resistance + 1.0)


def test_nonfinite_input_remains_plain_value_error_not_range_error() -> None:
    with pytest.raises(ValueError) as caught:
        pt100.celsius_to_resistance(math.nan)

    assert not isinstance(caught.value, exceptions.RTDError)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: models.IEC60751RTDModel(r0_ohms=0.0),
        lambda: models.CallendarVanDusenRTDModel(
            r0_ohms=100.0,
            a=1.0e-3,
            b=-1.0e-5,
            minimum_temperature_c=0.0,
            maximum_temperature_c=100.0,
        ),
        lambda: models.PolynomialRTDModel(
            reference_resistance_ohms=100.0,
            coefficients=(-1.0e-3,),
            minimum_temperature_c=0.0,
            maximum_temperature_c=100.0,
        ),
    ],
)
def test_invalid_public_model_configuration_raises_invalid_model_error(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(exceptions.InvalidRTDModelError):
        factory()


def test_invalid_model_error_preserves_validation_cause() -> None:
    with pytest.raises(exceptions.InvalidRTDModelError) as caught:
        models.IEC60751RTDModel(r0_ohms=0.0)

    assert isinstance(caught.value.__cause__, ValueError)
    assert not isinstance(caught.value.__cause__, exceptions.RTDError)


def test_invalid_piecewise_segment_raises_invalid_model_error() -> None:
    with pytest.raises(exceptions.InvalidRTDModelError):
        models.PiecewisePolynomialSegment(
            minimum_temperature_c=10.0,
            maximum_temperature_c=0.0,
            coefficients=(1.0, 0.001),
        )


def test_declared_custom_model_range_raises_out_of_range_error() -> None:
    model = models.IEC60751RTDModel(
        r0_ohms=100.0,
        minimum_temperature_c=0.0,
        maximum_temperature_c=100.0,
    )

    with pytest.raises(exceptions.RTDOutOfRangeError):
        model.celsius_to_resistance(-0.001)
