# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from rtd_sensor import measurement, simulation


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


def test_simulation_reexports_neutral_resistance_reader() -> None:
    assert simulation.ResistanceReader is measurement.ResistanceReader


def test_resistance_reader_is_owned_by_neutral_module() -> None:
    assert measurement.ResistanceReader.__module__ == "rtd_sensor.measurement"
