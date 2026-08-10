# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from rtd_sensor import ni120, ni1000, ni1000_tk5000, pt100, pt500, pt1000, simulation

_CONFLICTING_RTD_TYPE_PAIRS = tuple(
    (declared_type, explicit_type)
    for declared_type in simulation.SUPPORTED_RTD_TYPES
    for explicit_type in simulation.SUPPORTED_RTD_TYPES
    if declared_type != explicit_type
)


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

    assert simulation.read_temperature_celsius(reader) == pytest.approx(65.0, abs=1e-9)


def test_fixed_reader_supports_pt500_resistance() -> None:
    resistance = pt500.celsius_to_resistance(65.0)
    reader = simulation.FixedResistanceReader(
        resistance,
        rtd_type="pt500",
    )

    assert simulation.read_temperature_celsius(reader) == pytest.approx(65.0, abs=1e-9)


def test_resistance_sequence_returns_values_in_order() -> None:
    reader = simulation.ResistanceSequenceReader([100.0, 109.734656, 119.397125])

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

    temperatures = [simulation.read_temperature_celsius(reader) for _ in range(4)]

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
    reader = simulation.TemperatureSequenceReader([0.0, 25.0, 50.0])

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

    temperatures = [simulation.read_temperature_celsius(reader) for _ in range(4)]

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

    temperatures = [simulation.read_temperature_celsius(reader) for _ in range(4)]

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

    assert simulation.read_temperature_celsius(reader) == pytest.approx(
        65.0,
        abs=1e-9,
    )


def test_read_temperature_celsius_accepts_explicit_pt500_type() -> None:
    class Reader:
        def read_resistance_ohms(self) -> float:
            return pt500.celsius_to_resistance(65.0)

    assert simulation.read_temperature_celsius(
        Reader(),
        rtd_type="pt500",
    ) == pytest.approx(65.0, abs=1e-9)


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

    assert simulation.read_temperature_celsius(reader) == pytest.approx(65.0, abs=1e-9)


def test_zero_noise_returns_exact_temperature() -> None:
    reader = simulation.NoisyTemperatureReader(
        temperature_c=65.0,
        noise_standard_deviation_c=0.0,
        seed=12345,
    )

    temperatures = [simulation.read_temperature_celsius(reader) for _ in range(5)]

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

    temperatures = [simulation.read_temperature_celsius(reader) for _ in range(5)]

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

    first_readings = [first.read_resistance_ohms() for _ in range(10)]
    second_readings = [second.read_resistance_ohms() for _ in range(10)]

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

    first_readings = [first.read_resistance_ohms() for _ in range(5)]
    second_readings = [second.read_resistance_ohms() for _ in range(5)]

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
        simulation.NoisyTemperatureReader(temperature_c=temperature_c)


def test_pt500_temperature_sequence_round_trip() -> None:
    reader = simulation.TemperatureSequenceReader(
        [-100.0, 0.0, 123.5],
        rtd_type="pt500",
    )

    assert simulation.read_temperature_celsius(reader) == pytest.approx(
        -100.0, abs=1e-9
    )
    assert simulation.read_temperature_celsius(reader) == pytest.approx(0.0, abs=1e-9)
    assert simulation.read_temperature_celsius(reader) == pytest.approx(123.5, abs=1e-9)


def test_ni1000_temperature_sequence_round_trip() -> None:
    reader = simulation.TemperatureSequenceReader(
        [-60.0, 0.0, 100.0, 250.0],
        rtd_type="ni1000",
    )

    temperatures = [simulation.read_temperature_celsius(reader) for _ in range(4)]
    assert temperatures == pytest.approx(
        [-60.0, 0.0, 100.0, 250.0],
        abs=1e-9,
    )


def test_explicit_ni1000_type_converts_bare_reader() -> None:
    class BareResistanceReader:
        def read_resistance_ohms(self) -> float:
            return ni1000.celsius_to_resistance(65.0)

    assert simulation.read_temperature_celsius(
        BareResistanceReader(),
        rtd_type="ni1000",
    ) == pytest.approx(65.0, abs=1e-9)


def test_ni1000_tk5000_temperature_sequence_round_trip() -> None:
    reader = simulation.TemperatureSequenceReader(
        [-60.0, 0.0, 100.0, 250.0],
        rtd_type="ni1000_tk5000",
    )

    temperatures = [simulation.read_temperature_celsius(reader) for _ in range(4)]
    assert temperatures == pytest.approx(
        [-60.0, 0.0, 100.0, 250.0],
        abs=1e-9,
    )


def test_explicit_ni1000_tk5000_type_converts_bare_reader() -> None:
    class BareResistanceReader:
        def read_resistance_ohms(self) -> float:
            return ni1000_tk5000.celsius_to_resistance(65.0)

    assert simulation.read_temperature_celsius(
        BareResistanceReader(),
        rtd_type="ni1000_tk5000",
    ) == pytest.approx(65.0, abs=1e-9)


def test_ni120_temperature_sequence_round_trip() -> None:
    reader = simulation.TemperatureSequenceReader(
        [-80.0, 0.0, 100.0, 260.0],
        rtd_type="ni120",
    )

    temperatures = [simulation.read_temperature_celsius(reader) for _ in range(4)]
    assert temperatures == pytest.approx(
        [-80.0, 0.0, 100.0, 260.0],
        abs=1e-9,
    )


def test_explicit_ni120_type_converts_bare_reader() -> None:
    class BareResistanceReader:
        def read_resistance_ohms(self) -> float:
            return ni120.celsius_to_resistance(65.0)

    assert simulation.read_temperature_celsius(
        BareResistanceReader(),
        rtd_type="ni120",
    ) == pytest.approx(65.0, abs=1e-9)


def test_unsupported_rtd_type_is_rejected() -> None:
    unsupported: simulation.RTDType = "cu10"

    with pytest.raises(ValueError, match="Unsupported RTD type"):
        simulation.TemperatureSequenceReader(
            [0.0],
            rtd_type=unsupported,
        )


@pytest.mark.parametrize(
    ("declared_type", "explicit_type"),
    _CONFLICTING_RTD_TYPE_PAIRS,
)
def test_model_aware_reader_rejects_conflicting_explicit_type(
    declared_type: simulation.RTDType,
    explicit_type: simulation.RTDType,
) -> None:
    reader = simulation.TemperatureSequenceReader(
        [65.0],
        rtd_type=declared_type,
    )

    with pytest.raises(
        ValueError,
        match="conflicts with reader-declared RTD type",
    ):
        simulation.read_temperature_celsius(
            reader,
            rtd_type=explicit_type,
        )

    # Reject the mismatch before consuming the source reading.
    assert simulation.read_temperature_celsius(reader) == pytest.approx(
        65.0,
        abs=1e-9,
    )


@pytest.mark.parametrize("rtd_type", simulation.SUPPORTED_RTD_TYPES)
def test_model_aware_reader_accepts_matching_explicit_type(
    rtd_type: simulation.RTDType,
) -> None:
    reader = simulation.TemperatureSequenceReader(
        [65.0],
        rtd_type=rtd_type,
    )

    assert simulation.read_temperature_celsius(
        reader,
        rtd_type=rtd_type,
    ) == pytest.approx(65.0, abs=1e-9)


@pytest.mark.parametrize(
    ("declared_type", "explicit_type"),
    _CONFLICTING_RTD_TYPE_PAIRS,
)
def test_external_model_aware_reader_rejects_conflicting_type(
    declared_type: simulation.RTDType,
    explicit_type: simulation.RTDType,
) -> None:
    class DeclaredReader:
        def __init__(self, rtd_type: simulation.RTDType) -> None:
            self.rtd_type = rtd_type

        def read_resistance_ohms(self) -> float:
            raise AssertionError("Conflicting model must fail before reading")

    reader = DeclaredReader(declared_type)

    with pytest.raises(
        ValueError,
        match="conflicts with reader-declared RTD type",
    ):
        simulation.read_temperature_celsius(
            reader,
            rtd_type=explicit_type,
        )


def test_external_model_aware_reader_rejects_unsupported_declaration() -> None:
    class InvalidDeclaredReader:
        rtd_type: simulation.RTDType = "cu10"

        def read_resistance_ohms(self) -> float:
            return pt100.celsius_to_resistance(65.0)

    with pytest.raises(ValueError, match="Unsupported RTD type"):
        simulation.read_temperature_celsius(InvalidDeclaredReader())


@pytest.mark.parametrize("rtd_type", simulation.SUPPORTED_RTD_TYPES)
def test_builtin_reader_rtd_identity_is_read_only(
    rtd_type: simulation.RTDType,
) -> None:
    replacement_type = next(
        candidate
        for candidate in simulation.SUPPORTED_RTD_TYPES
        if candidate != rtd_type
    )
    reference_reader = simulation.TemperatureSequenceReader(
        [0.0],
        rtd_type=rtd_type,
    )
    reference_resistance_ohms = reference_reader.read_resistance_ohms()

    readers = (
        simulation.FixedResistanceReader(
            reference_resistance_ohms,
            rtd_type=rtd_type,
        ),
        simulation.ResistanceSequenceReader(
            [reference_resistance_ohms],
            rtd_type=rtd_type,
        ),
        simulation.TemperatureSequenceReader(
            [0.0],
            rtd_type=rtd_type,
        ),
        simulation.NoisyTemperatureReader(
            0.0,
            noise_standard_deviation_c=0.0,
            rtd_type=rtd_type,
        ),
    )

    for reader in readers:
        assert reader.rtd_type == rtd_type

        with pytest.raises(
            AttributeError,
            match="read-only after reader construction",
        ):
            reader.rtd_type = replacement_type

        assert reader.rtd_type == rtd_type
