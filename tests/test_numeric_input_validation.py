# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections.abc import Callable

import pytest

from rtd import pt100, pt500, pt1000, simulation, tolerance, uncertainty
from rtd.models import CallendarVanDusenRTDModel, IEC60751RTDModel


@pytest.mark.parametrize(
    "function",
    [
        pt100.celsius_to_resistance,
        pt100.resistance_to_celsius,
        pt100.resistance_sensitivity_ohms_per_celsius,
        pt100.temperature_sensitivity_celsius_per_ohm,
        pt500.celsius_to_resistance,
        pt500.resistance_to_celsius,
        pt500.resistance_sensitivity_ohms_per_celsius,
        pt500.temperature_sensitivity_celsius_per_ohm,
        pt1000.celsius_to_resistance,
        pt1000.resistance_to_celsius,
    ],
)
def test_builtin_conversion_apis_reject_boolean_measurements(
    function: Callable[[float], float],
) -> None:
    with pytest.raises(TypeError, match="not bool"):
        function(True)


def test_public_iec_model_rejects_boolean_parameters_and_measurements() -> None:
    with pytest.raises(TypeError, match="R0.*not bool"):
        IEC60751RTDModel(r0_ohms=True)

    with pytest.raises(TypeError, match="Minimum temperature.*not bool"):
        IEC60751RTDModel(
            r0_ohms=100.0,
            minimum_temperature_c=True,
            maximum_temperature_c=100.0,
        )

    model = IEC60751RTDModel(r0_ohms=100.0)
    with pytest.raises(TypeError, match="Temperature.*not bool"):
        model.celsius_to_resistance(True)
    with pytest.raises(TypeError, match="Resistance.*not bool"):
        model.resistance_to_celsius(True)


def test_custom_cvd_model_rejects_boolean_coefficients() -> None:
    with pytest.raises(TypeError, match="A coefficient.*not bool"):
        CallendarVanDusenRTDModel(
            r0_ohms=100.0,
            a=True,
            b=-5.775e-7,
            c=-4.183e-12,
            minimum_temperature_c=-50.0,
            maximum_temperature_c=100.0,
        )


def test_tolerance_apis_reject_boolean_temperature() -> None:
    with pytest.raises(TypeError, match="Temperature.*not bool"):
        tolerance.thermometer_tolerance_c(
            True,
            tolerance_class="A",
            construction="wire_wound",
        )

    with pytest.raises(TypeError, match="Temperature.*not bool"):
        tolerance.platinum_resistor_tolerance_c(
            False,
            tolerance_class="W0.15",
        )


def test_uncertainty_apis_reject_boolean_quantities() -> None:
    with pytest.raises(TypeError, match="Half-width.*not bool"):
        uncertainty.standard_uncertainty_from_bound(
            True,
            distribution="rectangular",
        )

    with pytest.raises(TypeError, match="Coverage factor.*not bool"):
        uncertainty.expanded_uncertainty(
            0.1,
            coverage_factor=True,
        )

    with pytest.raises(TypeError, match="Standard uncertainty.*not bool"):
        uncertainty.combine_independent_standard_uncertainties(0.1, False)

    with pytest.raises(TypeError, match="Resistance.*not bool"):
        uncertainty.propagate_resistance_uncertainty(
            True,
            0.01,
            model=pt100,
        )


def test_simulation_rejects_boolean_physical_values_but_accepts_controls() -> None:
    with pytest.raises(TypeError, match="Resistance.*not bool"):
        simulation.FixedResistanceReader(True)

    with pytest.raises(TypeError, match="Temperature.*not bool"):
        simulation.TemperatureSequenceReader([True])

    with pytest.raises(TypeError, match="Noise standard deviation.*not bool"):
        simulation.NoisyTemperatureReader(
            0.0,
            noise_standard_deviation_c=True,
        )

    reader = simulation.ResistanceSequenceReader(
        [100.0],
        repeat=True,
    )
    assert reader.read_resistance_ohms() == 100.0
    assert reader.read_resistance_ohms() == 100.0
