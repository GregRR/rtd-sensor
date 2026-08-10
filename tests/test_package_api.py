# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rtd import (
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


def test_package_exports_pt100_module() -> None:
    from rtd import pt100 as imported_pt100

    assert imported_pt100 is pt100

def test_package_exports_pt500_module() -> None:
    from rtd import pt500 as imported_pt500

    assert imported_pt500 is pt500

def test_package_exports_pt1000_module() -> None:
    from rtd import pt1000 as imported_pt1000

    assert imported_pt1000 is pt1000

def test_package_exports_ni1000_module() -> None:
    from rtd import ni1000 as imported_ni1000

    assert imported_ni1000 is ni1000

def test_package_exports_ni1000_tk5000_module() -> None:
    from rtd import ni1000_tk5000 as imported_ni1000_tk5000

    assert imported_ni1000_tk5000 is ni1000_tk5000

def test_package_exports_ni120_module() -> None:
    from rtd import ni120 as imported_ni120

    assert imported_ni120 is ni120


def test_package_exports_models_module() -> None:
    from rtd import models as imported_models

    assert imported_models is models

def test_package_exports_simulation_module() -> None:
    from rtd import simulation as imported_simulation

    assert imported_simulation is simulation

def test_package_public_api() -> None:
    import rtd

    assert set(rtd.__all__) == {
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
    }

def test_models_public_api() -> None:
    assert set(models.__all__) == {
        "CallendarVanDusenRTDModel",
        "IEC60751RTDModel",
        "PiecewisePolynomialRTDModel",
        "PiecewisePolynomialSegment",
        "PolynomialRTDModel",
    }

def test_ni1000_public_api() -> None:
    assert set(ni1000.__all__) == {
        "MAX_TEMPERATURE_C",
        "MIN_TEMPERATURE_C",
        "R0_OHMS",
        "celsius_to_resistance",
        "resistance_sensitivity_ohms_per_celsius",
        "resistance_to_celsius",
        "temperature_sensitivity_celsius_per_ohm",
    }
    assert not hasattr(ni1000, "NI1000_6180")

def test_ni1000_tk5000_public_api() -> None:
    assert set(ni1000_tk5000.__all__) == {
        "MAX_TEMPERATURE_C",
        "MIN_TEMPERATURE_C",
        "R0_OHMS",
        "celsius_to_resistance",
        "resistance_sensitivity_ohms_per_celsius",
        "resistance_to_celsius",
        "temperature_sensitivity_celsius_per_ohm",
    }
    assert not hasattr(ni1000_tk5000, "NI1000_TK5000")

def test_ni120_public_api() -> None:
    assert set(ni120.__all__) == {
        "MAX_TEMPERATURE_C",
        "MIN_TEMPERATURE_C",
        "R0_OHMS",
        "celsius_to_resistance",
        "resistance_sensitivity_ohms_per_celsius",
        "resistance_to_celsius",
        "temperature_sensitivity_celsius_per_ohm",
    }
    assert not hasattr(ni120, "NI120_6720")


def test_pt100_public_api() -> None:
    assert set(pt100.__all__) == {
        "MAX_TEMPERATURE_C",
        "MIN_TEMPERATURE_C",
        "R0_OHMS",
        "celsius_to_resistance",
        "resistance_sensitivity_ohms_per_celsius",
        "resistance_to_celsius",
        "temperature_sensitivity_celsius_per_ohm",
    }

def test_pt500_public_api() -> None:
    assert set(pt500.__all__) == {
        "MAX_TEMPERATURE_C",
        "MIN_TEMPERATURE_C",
        "R0_OHMS",
        "celsius_to_resistance",
        "resistance_sensitivity_ohms_per_celsius",
        "resistance_to_celsius",
        "temperature_sensitivity_celsius_per_ohm",
    }

def test_pt1000_public_api() -> None:
    assert set(pt1000.__all__) == {
        "MAX_TEMPERATURE_C",
        "MIN_TEMPERATURE_C",
        "R0_OHMS",
        "celsius_to_resistance",
        "resistance_sensitivity_ohms_per_celsius",
        "resistance_to_celsius",
        "temperature_sensitivity_celsius_per_ohm",
    }

def test_package_exports_tolerance_module() -> None:
    from rtd import tolerance as imported_tolerance

    assert imported_tolerance is tolerance

def test_tolerance_public_api() -> None:
    assert set(tolerance.__all__) == {
        "PlatinumResistorToleranceClass",
        "RTDConstruction",
        "ThermometerToleranceClass",
        "platinum_resistor_tolerance_c",
        "thermometer_tolerance_c",
    }

def test_package_exports_uncertainty_module() -> None:
    from rtd import uncertainty as imported_uncertainty

    assert imported_uncertainty is uncertainty

def test_uncertainty_public_api() -> None:
    assert set(uncertainty.__all__) == {
        "BoundDistribution",
        "EvaluationMethod",
        "RTDUncertaintyModel",
        "ResistanceUncertaintyPropagation",
        "TemperatureUncertaintyBudget",
        "TemperatureUncertaintyComponent",
        "combine_independent_standard_uncertainties",
        "expanded_uncertainty",
        "propagate_resistance_uncertainty",
        "standard_uncertainty_from_bound",
        "standard_uncertainty_from_expanded",
        "temperature_uncertainty_budget",
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

def test_public_modules_do_not_leak_internal_model_singletons() -> None:
    assert not hasattr(pt100, "PT100_IEC_60751")
    assert not hasattr(pt500, "PT500_IEC_60751")
    assert not hasattr(pt1000, "PT1000_IEC_60751")
    assert not hasattr(models, "IEC_60751_PT385")
    assert not hasattr(simulation, "PT100_IEC_60751")
    assert not hasattr(simulation, "PT500_IEC_60751")
    assert not hasattr(simulation, "PT1000_IEC_60751")
    assert not hasattr(simulation, "RTDModel")
