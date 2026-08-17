# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from collections.abc import Iterator

import pytest

from rtd_sensor import batch, pt100
from rtd_sensor.exceptions import RTDOutOfRangeError
from rtd_sensor.models import PolynomialRTDModel, RTDModel


class _LinearThirdPartyRTD:
    """Minimal structural RTD model used to test third-party compatibility."""

    def __init__(self) -> None:
        self.forward_calls: list[float] = []
        self.inverse_calls: list[float] = []

    def celsius_to_resistance(self, temperature_c: float) -> float:
        self.forward_calls.append(temperature_c)
        return 100.0 + temperature_c

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        self.inverse_calls.append(resistance_ohms)
        return resistance_ohms - 100.0

    def resistance_sensitivity_ohms_per_celsius(
        self,
        temperature_c: float,
    ) -> float:
        del temperature_c
        return 1.0

    def temperature_sensitivity_celsius_per_ohm(
        self,
        temperature_c: float,
    ) -> float:
        del temperature_c
        return 1.0


class _OnePassIterable:
    """Iterable that fails if the batch layer attempts a second iteration."""

    def __init__(self, values: list[float]) -> None:
        self._values = values
        self.iteration_count = 0

    def __iter__(self) -> Iterator[float]:
        self.iteration_count += 1
        if self.iteration_count > 1:
            raise AssertionError("input iterable was consumed more than once")
        yield from self._values


class _FailingThirdPartyRTD(_LinearThirdPartyRTD):
    def __init__(self, error: RuntimeError) -> None:
        super().__init__()
        self._error = error

    def celsius_to_resistance(self, temperature_c: float) -> float:
        self.forward_calls.append(temperature_c)
        if temperature_c == 20.0:
            raise self._error
        return 100.0 + temperature_c

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        self.inverse_calls.append(resistance_ohms)
        if resistance_ohms == 120.0:
            raise self._error
        return resistance_ohms - 100.0


def _as_rtd_model(model: _LinearThirdPartyRTD) -> RTDModel:
    """Static regression: batch accepts structural third-party RTD models."""
    return model


def test_public_api() -> None:
    assert set(batch.__all__) == {"celsius_to_resistance", "resistance_to_celsius"}


def test_celsius_to_resistance_matches_ordered_scalar_calls() -> None:
    temperatures = [-50.0, 0.0, 25.0, 100.0]

    expected = [pt100.celsius_to_resistance(value) for value in temperatures]

    assert batch.celsius_to_resistance(pt100, temperatures) == expected


def test_resistance_to_celsius_matches_ordered_scalar_calls() -> None:
    temperatures = [-50.0, 0.0, 25.0, 100.0]
    resistances = [pt100.celsius_to_resistance(value) for value in temperatures]

    expected = [pt100.resistance_to_celsius(value) for value in resistances]

    assert batch.resistance_to_celsius(pt100, resistances) == expected


def test_batch_returns_eager_lists() -> None:
    model = _LinearThirdPartyRTD()

    forward = batch.celsius_to_resistance(model, (0.0, 10.0, 20.0))
    inverse = batch.resistance_to_celsius(model, (100.0, 110.0, 120.0))

    assert isinstance(forward, list)
    assert isinstance(inverse, list)
    assert forward == [100.0, 110.0, 120.0]
    assert inverse == [0.0, 10.0, 20.0]


def test_batch_accepts_empty_iterables() -> None:
    assert batch.celsius_to_resistance(pt100, []) == []
    assert batch.resistance_to_celsius(pt100, []) == []


def test_celsius_to_resistance_consumes_one_pass_iterable_once_in_order() -> None:
    model = _LinearThirdPartyRTD()
    values = _OnePassIterable([0.0, 10.0, 20.0])

    result = batch.celsius_to_resistance(model, values)

    assert result == [100.0, 110.0, 120.0]
    assert values.iteration_count == 1
    assert model.forward_calls == [0.0, 10.0, 20.0]


def test_resistance_to_celsius_consumes_one_pass_iterable_once_in_order() -> None:
    model = _LinearThirdPartyRTD()
    values = _OnePassIterable([100.0, 110.0, 120.0])

    result = batch.resistance_to_celsius(model, values)

    assert result == [0.0, 10.0, 20.0]
    assert values.iteration_count == 1
    assert model.inverse_calls == [100.0, 110.0, 120.0]


def test_celsius_to_resistance_propagates_first_scalar_exception_unchanged() -> None:
    error = RuntimeError("third-party conversion failure")
    model = _FailingThirdPartyRTD(error)

    with pytest.raises(RuntimeError) as caught:
        batch.celsius_to_resistance(model, [0.0, 20.0, 30.0])

    assert caught.value is error
    assert model.forward_calls == [0.0, 20.0]


def test_resistance_to_celsius_propagates_first_scalar_exception_unchanged() -> None:
    error = RuntimeError("third-party conversion failure")
    model = _FailingThirdPartyRTD(error)

    with pytest.raises(RuntimeError) as caught:
        batch.resistance_to_celsius(model, [100.0, 120.0, 130.0])

    assert caught.value is error
    assert model.inverse_calls == [100.0, 120.0]


def test_generator_stops_consumption_at_first_scalar_failure() -> None:
    error = RuntimeError("third-party conversion failure")
    model = _FailingThirdPartyRTD(error)
    seen: list[float] = []

    def values() -> Iterator[float]:
        for value in (0.0, 20.0, 30.0):
            seen.append(value)
            yield value

    with pytest.raises(RuntimeError) as caught:
        batch.celsius_to_resistance(model, values())

    assert caught.value is error
    assert seen == [0.0, 20.0]
    assert model.forward_calls == [0.0, 20.0]


def test_iteration_exception_propagates_without_additional_model_calls() -> None:
    model = _LinearThirdPartyRTD()
    error = ValueError("upstream read failed")

    def values() -> Iterator[float]:
        yield 0.0
        yield 10.0
        raise error

    with pytest.raises(ValueError) as caught:
        batch.celsius_to_resistance(model, values())

    assert caught.value is error
    assert model.forward_calls == [0.0, 10.0]


def test_builtin_scalar_range_error_propagates() -> None:
    with pytest.raises(RTDOutOfRangeError) as expected:
        pt100.celsius_to_resistance(851.0)

    with pytest.raises(RTDOutOfRangeError) as caught:
        batch.celsius_to_resistance(pt100, [0.0, 851.0, 100.0])

    assert str(caught.value) == str(expected.value)


def test_batch_supports_configurable_models() -> None:
    model = PolynomialRTDModel(
        reference_resistance_ohms=100.0,
        reference_temperature_c=0.0,
        coefficients=(0.004, 0.000001),
        minimum_temperature_c=-50.0,
        maximum_temperature_c=150.0,
    )
    temperatures = [-25.0, 0.0, 50.0, 100.0]

    resistances = batch.celsius_to_resistance(model, temperatures)
    round_trip = batch.resistance_to_celsius(model, resistances)

    assert round_trip == pytest.approx(temperatures, abs=1e-10)


def test_batch_supports_structural_third_party_models() -> None:
    model: RTDModel = _as_rtd_model(_LinearThirdPartyRTD())

    assert batch.celsius_to_resistance(model, [1.0, 2.0]) == [101.0, 102.0]
    assert batch.resistance_to_celsius(model, [101.0, 102.0]) == [1.0, 2.0]


def test_generator_input_is_consumed_lazily_by_iteration_but_result_is_eager() -> None:
    seen: list[float] = []

    def values() -> Iterator[float]:
        for value in (0.0, 10.0, 20.0):
            seen.append(value)
            yield value

    result = batch.celsius_to_resistance(_LinearThirdPartyRTD(), values())

    assert result == [100.0, 110.0, 120.0]
    assert seen == [0.0, 10.0, 20.0]
