# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Resistance temperature detector conversion and simulation tools.

Example:
    from rtd import pt100, simulation

    reader = simulation.TemperatureSequenceReader(
        [20.0, 40.0, 60.0]
    )
    temperature_c = simulation.read_temperature_celsius(reader)
"""

from . import models, pt100, pt1000, simulation, tolerance

__all__ = [
    "models",
    "pt100",
    "pt1000",
    "simulation",
    "tolerance",
]
