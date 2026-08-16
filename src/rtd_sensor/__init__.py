# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Resistance temperature detector conversion, measurement, and simulation tools.

Example:
    from rtd_sensor import pt100, simulation

    reader = simulation.TemperatureSequenceReader(
        [20.0, 40.0, 60.0]
    )
    temperature_c = simulation.read_temperature_celsius(reader)
"""

from . import (
    catalog,
    measurement,
    models,
    ni120,
    ni1000,
    ni1000_tk5000,
    pt100,
    pt500,
    pt1000,
    simulation,
    tolerance,
    uncertainty,
)

__all__ = [
    "catalog",
    "measurement",
    "models",
    "ni1000",
    "ni1000_tk5000",
    "ni120",
    "pt100",
    "pt500",
    "pt1000",
    "simulation",
    "tolerance",
    "uncertainty",
]
