# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from rtd import ni1000, pt100, pt500, pt1000, tolerance, uncertainty
from rtd.models import CallendarVanDusenRTDModel, IEC60751RTDModel


def test_temperature_uncertainty_component_normalizes_metadata() -> None:
    component = uncertainty.TemperatureUncertaintyComponent(
        name="  calibration  ",
        standard_uncertainty_c=0.05,
        evaluation_method="B",
        source="  certificate 123  ",
        note="  k=2 converted separately  ",
    )

    assert component.name == "calibration"
    assert component.standard_uncertainty_c == 0.05
    assert component.evaluation_method == "B"
    assert component.source == "certificate 123"
    assert component.note == "k=2 converted separately"


@pytest.mark.parametrize("name", ["", "   "])
def test_temperature_uncertainty_component_rejects_empty_name(name: str) -> None:
    with pytest.raises(ValueError):
        uncertainty.TemperatureUncertaintyComponent(
            name=name,
            standard_uncertainty_c=0.1,
        )


@pytest.mark.parametrize("value", [-1.0, math.inf, -math.inf, math.nan])
def test_temperature_uncertainty_component_rejects_invalid_uncertainty(
    value: float,
) -> None:
    with pytest.raises(ValueError):
        uncertainty.TemperatureUncertaintyComponent(
            name="component",
            standard_uncertainty_c=value,
        )


def test_temperature_uncertainty_component_rejects_invalid_evaluation_method() -> None:
    with pytest.raises(ValueError):
        uncertainty.TemperatureUncertaintyComponent(
            name="component",
            standard_uncertainty_c=0.1,
            evaluation_method="C",  # type: ignore[arg-type]
        )


def test_temperature_uncertainty_component_rejects_blank_source() -> None:
    with pytest.raises(ValueError):
        uncertainty.TemperatureUncertaintyComponent(
            name="component",
            standard_uncertainty_c=0.1,
            source="   ",
        )


def test_temperature_uncertainty_component_rejects_blank_note() -> None:
    with pytest.raises(ValueError):
        uncertainty.TemperatureUncertaintyComponent(
            name="component",
            standard_uncertainty_c=0.1,
            note="   ",
        )


def test_propagate_pt100_resistance_uncertainty_at_zero() -> None:
    result = uncertainty.propagate_resistance_uncertainty(
        100.0,
        0.01,
        model=pt100,
    )

    expected_sensitivity = 1.0 / 0.39083
    assert result.resistance_ohms == 100.0
    assert result.temperature_c == 0.0
    assert result.resistance_standard_uncertainty_ohms == 0.01
    assert result.temperature_sensitivity_celsius_per_ohm == pytest.approx(
        expected_sensitivity
    )
    assert result.temperature_standard_uncertainty_c == pytest.approx(
        expected_sensitivity * 0.01
    )


def test_propagate_pt500_uses_pt500_sensitivity() -> None:
    resistance = pt500.celsius_to_resistance(100.0)
    result = uncertainty.propagate_resistance_uncertainty(
        resistance,
        0.05,
        model=pt500,
    )

    expected = pt500.temperature_sensitivity_celsius_per_ohm(100.0) * 0.05
    assert result.temperature_c == pytest.approx(100.0, abs=1e-10)
    assert result.temperature_standard_uncertainty_c == pytest.approx(expected)


def test_propagate_pt1000_uses_pt1000_sensitivity() -> None:
    resistance = pt1000.celsius_to_resistance(100.0)
    result = uncertainty.propagate_resistance_uncertainty(
        resistance,
        0.1,
        model=pt1000,
    )

    expected = (
        pt1000.temperature_sensitivity_celsius_per_ohm(100.0) * 0.1
    )
    assert result.temperature_c == pytest.approx(100.0, abs=1e-10)
    assert result.temperature_standard_uncertainty_c == pytest.approx(expected)


def test_propagate_ni1000_uses_nickel_sensitivity() -> None:
    resistance = ni1000.celsius_to_resistance(100.0)
    result = uncertainty.propagate_resistance_uncertainty(
        resistance,
        0.1,
        model=ni1000,
    )

    expected = ni1000.temperature_sensitivity_celsius_per_ohm(100.0) * 0.1
    assert result.temperature_c == pytest.approx(100.0, abs=1e-10)
    assert result.temperature_standard_uncertainty_c == pytest.approx(expected)


def test_propagation_supports_configurable_iec_model() -> None:
    model = IEC60751RTDModel(r0_ohms=100.017)
    resistance = model.celsius_to_resistance(50.0)

    result = uncertainty.propagate_resistance_uncertainty(
        resistance,
        0.02,
        model=model,
    )

    assert result.temperature_c == pytest.approx(50.0, abs=1e-10)
    assert result.temperature_standard_uncertainty_c == pytest.approx(
        model.temperature_sensitivity_celsius_per_ohm(50.0) * 0.02
    )


def test_propagation_supports_custom_cvd_model() -> None:
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.025,
        a=3.91e-3,
        b=-5.80e-7,
        c=-4.20e-12,
        minimum_temperature_c=-50.0,
        maximum_temperature_c=250.0,
    )
    resistance = model.celsius_to_resistance(-25.0)

    result = uncertainty.propagate_resistance_uncertainty(
        resistance,
        0.01,
        model=model,
    )

    assert result.temperature_c == pytest.approx(-25.0, abs=1e-10)
    assert result.temperature_standard_uncertainty_c == pytest.approx(
        model.temperature_sensitivity_celsius_per_ohm(-25.0) * 0.01
    )


def test_zero_resistance_uncertainty_propagates_to_zero() -> None:
    result = uncertainty.propagate_resistance_uncertainty(
        pt100.celsius_to_resistance(50.0),
        0.0,
        model=pt100,
    )
    assert result.temperature_standard_uncertainty_c == 0.0


@pytest.mark.parametrize("value", [-1.0, math.inf, -math.inf, math.nan])
def test_propagation_rejects_invalid_resistance_uncertainty(value: float) -> None:
    with pytest.raises(ValueError):
        uncertainty.propagate_resistance_uncertainty(
            100.0,
            value,
            model=pt100,
        )


def test_propagation_preserves_model_range_validation() -> None:
    model = IEC60751RTDModel(
        r0_ohms=100.0,
        minimum_temperature_c=0.0,
        maximum_temperature_c=100.0,
    )
    with pytest.raises(ValueError):
        uncertainty.propagate_resistance_uncertainty(
            pt100.celsius_to_resistance(-10.0),
            0.01,
            model=model,
        )


def test_temperature_budget_combines_resistance_and_named_components() -> None:
    calibration = uncertainty.TemperatureUncertaintyComponent(
        name="Calibration certificate",
        standard_uncertainty_c=0.05,
        evaluation_method="B",
        source="Certificate 123",
    )
    repeatability = uncertainty.TemperatureUncertaintyComponent(
        name="Repeatability",
        standard_uncertainty_c=0.03,
        evaluation_method="A",
    )

    budget = uncertainty.temperature_uncertainty_budget(
        100.0,
        0.01,
        model=pt100,
        additional_components=(calibration, repeatability),
        coverage_factor=2.0,
    )

    resistance_u_c = (1.0 / 0.39083) * 0.01
    expected_combined = math.hypot(resistance_u_c, 0.05, 0.03)

    assert budget.temperature_c == 0.0
    assert budget.additional_components == (calibration, repeatability)
    assert budget.combined_standard_uncertainty_c == pytest.approx(
        expected_combined
    )
    assert budget.coverage_factor == 2.0
    assert budget.expanded_uncertainty_c == pytest.approx(
        2.0 * expected_combined
    )


def test_temperature_budget_without_coverage_factor_omits_expanded_result() -> None:
    budget = uncertainty.temperature_uncertainty_budget(
        100.0,
        0.01,
        model=pt100,
    )

    assert budget.coverage_factor is None
    assert budget.expanded_uncertainty_c is None
    assert budget.combined_standard_uncertainty_c == pytest.approx(
        budget.resistance.temperature_standard_uncertainty_c
    )


def test_temperature_budget_accepts_component_generator() -> None:
    components = (
        uncertainty.TemperatureUncertaintyComponent(
            name=f"component-{index}",
            standard_uncertainty_c=value,
        )
        for index, value in enumerate((0.01, 0.02))
    )

    budget = uncertainty.temperature_uncertainty_budget(
        100.0,
        0.0,
        model=pt100,
        additional_components=components,
    )

    assert len(budget.additional_components) == 2
    assert budget.combined_standard_uncertainty_c == pytest.approx(
        math.hypot(0.0, 0.01, 0.02)
    )


def test_temperature_budget_rejects_non_component_objects() -> None:
    with pytest.raises(TypeError):
        uncertainty.temperature_uncertainty_budget(
            100.0,
            0.01,
            model=pt100,
            additional_components=[0.1],  # type: ignore[list-item]
        )


@pytest.mark.parametrize("coverage_factor", [0.0, -1.0, math.inf, math.nan])
def test_temperature_budget_rejects_invalid_coverage_factor(
    coverage_factor: float,
) -> None:
    with pytest.raises(ValueError):
        uncertainty.temperature_uncertainty_budget(
            100.0,
            0.01,
            model=pt100,
            coverage_factor=coverage_factor,
        )


def test_tolerance_can_be_explicitly_modeled_as_budget_component() -> None:
    limit_c = tolerance.thermometer_tolerance_c(
        100.0,
        tolerance_class="A",
        construction="wire_wound",
    )
    standard_u_c = uncertainty.standard_uncertainty_from_bound(
        limit_c,
        distribution="rectangular",
    )
    sensor_component = uncertainty.TemperatureUncertaintyComponent(
        name="Sensor class limit",
        standard_uncertainty_c=standard_u_c,
        evaluation_method="B",
        source="IEC 60751 Class A tolerance modeled as rectangular",
    )

    budget = uncertainty.temperature_uncertainty_budget(
        pt100.celsius_to_resistance(100.0),
        0.0,
        model=pt100,
        additional_components=(sensor_component,),
    )

    assert budget.combined_standard_uncertainty_c == pytest.approx(standard_u_c)


def test_polynomial_model_participates_in_uncertainty_propagation() -> None:
    from rtd.models import PolynomialRTDModel

    model = PolynomialRTDModel(
        reference_resistance_ohms=100.0,
        reference_temperature_c=25.0,
        coefficients=(0.01,),
        minimum_temperature_c=-20.0,
        maximum_temperature_c=80.0,
        name="Synthetic linear RTD",
    )

    propagated = uncertainty.propagate_resistance_uncertainty(
        100.0,
        0.2,
        model=model,
    )

    # dR/dT = 100 ohm * 0.01 / °C = 1 ohm/°C, so 0.2 ohm of
    # standard resistance uncertainty propagates to 0.2 °C at this point.
    assert propagated.temperature_c == 25.0
    assert propagated.temperature_sensitivity_celsius_per_ohm == 1.0
    assert propagated.temperature_standard_uncertainty_c == pytest.approx(0.2)
