# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Hardware-neutral interfaces for RTD resistance measurements.

Acquisition code is responsible for producing the best available estimate of
sensor-element resistance in ohms. That may include converter-specific
calculations, lead-wire compensation, or other hardware-side corrections.
This module defines only the small structural boundary consumed by rtd-sensor;
it does not define how hardware obtains that resistance.
"""

from __future__ import annotations

from typing import Protocol

__all__ = ["ResistanceReader"]


class ResistanceReader(Protocol):
    """Structural interface for a source of RTD resistance measurements.

    Implementations do not need to inherit from an rtd-sensor base class. A
    compatible object only needs to provide :meth:`read_resistance_ohms`.
    """

    def read_resistance_ohms(self) -> float:
        """Return one sensor-element resistance value in ohms."""
        ...
