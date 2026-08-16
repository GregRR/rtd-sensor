# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import pytest

from rtd_sensor import catalog, measurement, models, pt100, pt1000, simulation


def _accept_resistance_reader(
    reader: measurement.ResistanceReader,
) -> measurement.ResistanceReader:
    """Static regression: third-party readers satisfy the public protocol."""
    return reader


def test_third_party_reader_structurally_satisfies_protocol() -> None:
    class ThirdPartyReader:
        def read_resistance_ohms(self) -> float:
            return 123.456

    reader = _accept_resistance_reader(ThirdPartyReader())

    assert reader.read_resistance_ohms() == 123.456


def test_simulation_reexports_neutral_measurement_api() -> None:
    assert simulation.ResistanceReader is measurement.ResistanceReader
    assert simulation.read_temperature_celsius is measurement.read_temperature_celsius


def test_resistance_reader_is_owned_by_neutral_module() -> None:
    assert measurement.ResistanceReader.__module__ == "rtd_sensor.measurement"


def test_read_temperature_accepts_catalog_model() -> None:
    class Reader:
        def read_resistance_ohms(self) -> float:
            return pt1000.celsius_to_resistance(65.0)

    temperature_c = measurement.read_temperature_celsius(
        Reader(),
        model=catalog.get_model("pt1000"),
    )

    assert temperature_c == pytest.approx(65.0, abs=1e-9)


def test_read_temperature_accepts_characterized_model() -> None:
    model = models.IEC60751RTDModel(r0_ohms=100.037)

    class Reader:
        def read_resistance_ohms(self) -> float:
            return model.celsius_to_resistance(65.0)

    assert measurement.read_temperature_celsius(Reader(), model=model) == pytest.approx(
        65.0, abs=1e-9
    )


def test_read_temperature_accepts_third_party_structural_model() -> None:
    class ThirdPartyModel:
        def celsius_to_resistance(self, temperature_c: float) -> float:
            return 100.0 + temperature_c

        def resistance_to_celsius(self, resistance_ohms: float) -> float:
            return resistance_ohms - 100.0

        def resistance_sensitivity_ohms_per_celsius(
            self, temperature_c: float
        ) -> float:
            return 1.0

        def temperature_sensitivity_celsius_per_ohm(
            self, temperature_c: float
        ) -> float:
            return 1.0

    class Reader:
        def read_resistance_ohms(self) -> float:
            return 165.0

    model: models.RTDModel = ThirdPartyModel()
    assert measurement.read_temperature_celsius(Reader(), model=model) == 65.0


def test_read_temperature_retains_builtin_type_convenience() -> None:
    class Reader:
        def read_resistance_ohms(self) -> float:
            return pt1000.celsius_to_resistance(65.0)

    assert measurement.read_temperature_celsius(
        Reader(), rtd_type="pt1000"
    ) == pytest.approx(65.0, abs=1e-9)


def test_untyped_reader_retains_pt100_default() -> None:
    class Reader:
        def read_resistance_ohms(self) -> float:
            return pt100.celsius_to_resistance(65.0)

    assert measurement.read_temperature_celsius(Reader()) == pytest.approx(
        65.0, abs=1e-9
    )


def test_explicit_model_and_rtd_type_are_mutually_exclusive() -> None:
    class Reader:
        def read_resistance_ohms(self) -> float:
            raise AssertionError("Selection conflict must fail before reading")

    with pytest.raises(ValueError, match="either model or rtd_type"):
        measurement.read_temperature_celsius(
            Reader(),
            model=catalog.get_model("pt100"),
            rtd_type="pt100",
        )


def test_explicit_model_rejects_reader_declared_identity() -> None:
    reader = simulation.TemperatureSequenceReader([65.0], rtd_type="pt100")

    with pytest.raises(
        ValueError, match="Cannot combine an explicit RTD model with reader-declared"
    ):
        measurement.read_temperature_celsius(
            reader,
            model=catalog.get_model("pt100"),
        )

    # Reject ambiguity before consuming the source reading.
    assert measurement.read_temperature_celsius(reader) == pytest.approx(65.0, abs=1e-9)


def test_invalid_reader_declaration_cannot_be_bypassed_by_model() -> None:
    class Reader:
        rtd_type = "cu10"

        def read_resistance_ohms(self) -> float:
            raise AssertionError("Invalid declaration must fail before reading")

    with pytest.raises(ValueError, match="Unsupported RTD type"):
        measurement.read_temperature_celsius(
            Reader(),
            model=catalog.get_model("pt100"),
        )


def test_non_string_reader_declaration_is_rejected_before_reading() -> None:
    class Reader:
        rtd_type = None

        def read_resistance_ohms(self) -> float:
            raise AssertionError("Invalid declaration must fail before reading")

    with pytest.raises(ValueError, match="Reader-declared RTD type must be a string"):
        measurement.read_temperature_celsius(
            Reader(),
            model=catalog.get_model("pt100"),
        )


def test_reader_and_model_exceptions_propagate_without_translation() -> None:
    class HardwareError(RuntimeError):
        pass

    class FailedReader:
        def read_resistance_ohms(self) -> float:
            raise HardwareError("ADC unavailable")

    with pytest.raises(HardwareError, match="ADC unavailable"):
        measurement.read_temperature_celsius(
            FailedReader(), model=catalog.get_model("pt100")
        )

    class RejectingModel:
        def celsius_to_resistance(self, temperature_c: float) -> float:
            return temperature_c

        def resistance_to_celsius(self, resistance_ohms: float) -> float:
            raise ValueError("model rejected resistance")

        def resistance_sensitivity_ohms_per_celsius(
            self, temperature_c: float
        ) -> float:
            return 1.0

        def temperature_sensitivity_celsius_per_ohm(
            self, temperature_c: float
        ) -> float:
            return 1.0

    class Reader:
        def read_resistance_ohms(self) -> float:
            return 100.0

    model: models.RTDModel = RejectingModel()
    with pytest.raises(ValueError, match="model rejected resistance"):
        measurement.read_temperature_celsius(Reader(), model=model)
