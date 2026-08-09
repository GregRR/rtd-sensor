# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
from typing import cast

import pytest

from rtd import pt100, pt1000, simulation


def test_fixed_resistance_reader_repeats_value() -> None:
    reader = simulation.FixedResistanceReader(119.3971)

    assert reader.read_resistance_ohms() == 119.3971
    assert reader.read_resistance_ohms() == 119.3971


@pytest.mark.parametrize(
    "resistance_ohms",
    [
        0.0,
        -1.0,
        18.0,
        391.0,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_fixed_reader_rejects_invalid_resistance(
    resistance_ohms: float,
) -> None:
    with pytest.raises(ValueError):
        simulation.FixedResistanceReader(resistance_ohms)


def test_fixed_reader_supports_pt1000_resistance() -> None:
    resistance = pt1000.celsius_to_resistance(65.0)
    reader = simulation.FixedResistanceReader(
        resistance,
        rtd_type="pt1000",
    )

    assert simulation.read_temperature_celsius(
        reader
    ) == pytest.approx(65.0, abs=1e-9)


def test_resistance_sequence_returns_values_in_order() -> None:
    reader = simulation.ResistanceSequenceReader(
        [100.0, 109.734656, 119.397125]
    )

    assert reader.read_resistance_ohms() == 100.0
    assert reader.read_resistance_ohms() == 109.734656
    assert reader.read_resistance_ohms() == 119.397125


def test_resistance_sequence_stops_when_exhausted() -> None:
    reader = simulation.ResistanceSequenceReader([100.0])

    assert reader.read_resistance_ohms() == 100.0

    with pytest.raises(StopIteration):
        reader.read_resistance_ohms()


def test_resistance_sequence_can_repeat() -> None:
    reader = simulation.ResistanceSequenceReader(
        [100.0, 119.397125],
        repeat=True,
    )

    assert reader.read_resistance_ohms() == 100.0
    assert reader.read_resistance_ohms() == 119.397125
    assert reader.read_resistance_ohms() == 100.0
    assert reader.read_resistance_ohms() == 119.397125


def test_resistance_sequence_can_repeat_pt1000_values() -> None:
    readings = [
        pt1000.celsius_to_resistance(0.0),
        pt1000.celsius_to_resistance(100.0),
    ]
    reader = simulation.ResistanceSequenceReader(
        readings,
        repeat=True,
        rtd_type="pt1000",
    )

    temperatures = [
        simulation.read_temperature_celsius(reader)
        for _ in range(4)
    ]

    assert temperatures == pytest.approx(
        [0.0, 100.0, 0.0, 100.0],
        abs=1e-9,
    )


def test_resistance_sequence_rejects_empty_sequence() -> None:
    with pytest.raises(ValueError):
        simulation.ResistanceSequenceReader([])


def test_resistance_sequence_rejects_invalid_reading() -> None:
    with pytest.raises(ValueError):
        simulation.ResistanceSequenceReader([100.0, 0.0])


def test_temperature_sequence_generates_pt100_resistance() -> None:
    reader = simulation.TemperatureSequenceReader(
        [0.0, 25.0, 50.0]
    )

    assert reader.read_resistance_ohms() == pytest.approx(
        pt100.celsius_to_resistance(0.0)
    )
    assert reader.read_resistance_ohms() == pytest.approx(
        pt100.celsius_to_resistance(25.0)
    )
    assert reader.read_resistance_ohms() == pytest.approx(
        pt100.celsius_to_resistance(50.0)
    )


def test_temperature_sequence_generates_pt1000_resistance() -> None:
    reader = simulation.TemperatureSequenceReader(
        [0.0, 25.0, 50.0],
        rtd_type="pt1000",
    )

    assert reader.read_resistance_ohms() == pytest.approx(
        pt1000.celsius_to_resistance(0.0)
    )
    assert reader.read_resistance_ohms() == pytest.approx(
        pt1000.celsius_to_resistance(25.0)
    )
    assert reader.read_resistance_ohms() == pytest.approx(
        pt1000.celsius_to_resistance(50.0)
    )


def test_temperature_sequence_can_repeat() -> None:
    reader = simulation.TemperatureSequenceReader(
        [0.0, 100.0],
        repeat=True,
    )

    temperatures = [
        simulation.read_temperature_celsius(reader)
        for _ in range(4)
    ]

    assert temperatures == pytest.approx(
        [0.0, 100.0, 0.0, 100.0],
        abs=1e-9,
    )


def test_pt1000_temperature_sequence_can_repeat() -> None:
    reader = simulation.TemperatureSequenceReader(
        [0.0, 100.0],
        repeat=True,
        rtd_type="pt1000",
    )

    temperatures = [
        simulation.read_temperature_celsius(reader)
        for _ in range(4)
    ]

    assert temperatures == pytest.approx(
        [0.0, 100.0, 0.0, 100.0],
        abs=1e-9,
    )


def test_temperature_sequence_rejects_empty_sequence() -> None:
    with pytest.raises(ValueError):
        simulation.TemperatureSequenceReader([])


def test_temperature_sequence_rejects_invalid_temperature() -> None:
    with pytest.raises(ValueError):
        simulation.TemperatureSequenceReader([0.0, 851.0])


def test_read_temperature_celsius_uses_reader_interface() -> None:
    resistance = pt100.celsius_to_resistance(65.0)
    reader = simulation.FixedResistanceReader(resistance)

    assert simulation.read_temperature_celsius(
        reader
    ) == pytest.approx(
        65.0,
        abs=1e-9,
    )


def test_read_temperature_celsius_accepts_explicit_pt1000_type() -> None:
    class BareResistanceReader:
        def read_resistance_ohms(self) -> float:
            return pt1000.celsius_to_resistance(65.0)

    reader = BareResistanceReader()

    assert simulation.read_temperature_celsius(
        reader,
        rtd_type="pt1000",
    ) == pytest.approx(65.0, abs=1e-9)


def test_untyped_external_reader_defaults_to_pt100() -> None:
    class BareResistanceReader:
        def read_resistance_ohms(self) -> float:
            return pt100.celsius_to_resistance(65.0)

    reader = BareResistanceReader()

    assert simulation.read_temperature_celsius(
        reader
    ) == pytest.approx(65.0, abs=1e-9)


def test_zero_noise_returns_exact_temperature() -> None:
    reader = simulation.NoisyTemperatureReader(
        temperature_c=65.0,
        noise_standard_deviation_c=0.0,
        seed=12345,
    )

    temperatures = [
        simulation.read_temperature_celsius(reader)
        for _ in range(5)
    ]

    assert temperatures == pytest.approx(
        [65.0] * 5,
        abs=1e-9,
    )


def test_pt1000_zero_noise_returns_exact_temperature() -> None:
    reader = simulation.NoisyTemperatureReader(
        temperature_c=65.0,
        noise_standard_deviation_c=0.0,
        seed=12345,
        rtd_type="pt1000",
    )

    temperatures = [
        simulation.read_temperature_celsius(reader)
        for _ in range(5)
    ]

    assert temperatures == pytest.approx(
        [65.0] * 5,
        abs=1e-9,
    )


def test_seeded_noise_is_reproducible() -> None:
    first = simulation.NoisyTemperatureReader(
        temperature_c=65.0,
        noise_standard_deviation_c=0.1,
        seed=12345,
    )
    second = simulation.NoisyTemperatureReader(
        temperature_c=65.0,
        noise_standard_deviation_c=0.1,
        seed=12345,
    )

    first_readings = [
        first.read_resistance_ohms()
        for _ in range(10)
    ]
    second_readings = [
        second.read_resistance_ohms()
        for _ in range(10)
    ]

    assert first_readings == second_readings


def test_different_seeds_produce_different_sequences() -> None:
    first = simulation.NoisyTemperatureReader(
        temperature_c=65.0,
        noise_standard_deviation_c=0.1,
        seed=1,
    )
    second = simulation.NoisyTemperatureReader(
        temperature_c=65.0,
        noise_standard_deviation_c=0.1,
        seed=2,
    )

    first_readings = [
        first.read_resistance_ohms()
        for _ in range(5)
    ]
    second_readings = [
        second.read_resistance_ohms()
        for _ in range(5)
    ]

    assert first_readings != second_readings


@pytest.mark.parametrize(
    "standard_deviation",
    [
        -0.1,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_noisy_reader_rejects_invalid_standard_deviation(
    standard_deviation: float,
) -> None:
    with pytest.raises(ValueError):
        simulation.NoisyTemperatureReader(
            temperature_c=65.0,
            noise_standard_deviation_c=standard_deviation,
        )


@pytest.mark.parametrize(
    "temperature_c",
    [
        -201.0,
        851.0,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_noisy_reader_rejects_invalid_temperature(
    temperature_c: float,
) -> None:
    with pytest.raises(ValueError):
        simulation.NoisyTemperatureReader(
            temperature_c=temperature_c
        )


def test_unsupported_rtd_type_is_rejected() -> None:
    unsupported = cast(simulation.RTDType, "pt500")

    with pytest.raises(ValueError, match="Unsupported RTD type"):
        simulation.TemperatureSequenceReader(
            [0.0],
            rtd_type=unsupported,
        )
