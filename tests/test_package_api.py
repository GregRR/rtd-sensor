# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rtd import models, pt100, pt500, pt1000, simulation, tolerance, uncertainty


def test_package_exports_pt100_module() -> None:
    from rtd import pt100 as imported_pt100

    assert imported_pt100 is pt100


def test_package_exports_pt500_module() -> None:
    from rtd import pt500 as imported_pt500

    assert imported_pt500 is pt500


def test_package_exports_pt1000_module() -> None:
    from rtd import pt1000 as imported_pt1000

    assert imported_pt1000 is pt1000


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
    }


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
