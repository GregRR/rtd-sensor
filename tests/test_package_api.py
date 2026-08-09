# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rtd import pt100, pt1000, simulation


def test_package_exports_pt100_module() -> None:
    from rtd import pt100 as imported_pt100

    assert imported_pt100 is pt100


def test_package_exports_pt1000_module() -> None:
    from rtd import pt1000 as imported_pt1000

    assert imported_pt1000 is pt1000


def test_package_exports_simulation_module() -> None:
    from rtd import simulation as imported_simulation

    assert imported_simulation is simulation


def test_package_public_api() -> None:
    import rtd

    assert set(rtd.__all__) == {
        "pt100",
        "pt1000",
        "simulation",
    }


def test_pt100_public_api() -> None:
    assert set(pt100.__all__) == {
        "MAX_TEMPERATURE_C",
        "MIN_TEMPERATURE_C",
        "R0_OHMS",
        "celsius_to_resistance",
        "resistance_to_celsius",
    }


def test_pt1000_public_api() -> None:
    assert set(pt1000.__all__) == {
        "MAX_TEMPERATURE_C",
        "MIN_TEMPERATURE_C",
        "R0_OHMS",
        "celsius_to_resistance",
        "resistance_to_celsius",
    }


def test_simulation_public_api() -> None:
    assert set(simulation.__all__) == {
        "FixedResistanceReader",
        "NoisyTemperatureReader",
        "RTDType",
        "ResistanceReader",
        "ResistanceSequenceReader",
        "TemperatureSequenceReader",
        "read_temperature_celsius",
    }
