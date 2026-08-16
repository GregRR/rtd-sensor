# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import pytest

from rtd_sensor import ni120, ni1000, ni1000_tk5000, pt100, pt500, pt1000
from rtd_sensor.models import (
    CallendarVanDusenRTDModel,
    IEC60751RTDModel,
    PiecewisePolynomialRTDModel,
    PolynomialRTDModel,
    RTDModel,
    TabulatedRTDModel,
)
from rtd_sensor.uncertainty import RTDUncertaintyModel

_BUILTIN_MODELS: tuple[tuple[RTDModel, float], ...] = (
    (pt100, 100.0),
    (pt500, 500.0),
    (pt1000, 1000.0),
    (ni1000, 1000.0),
    (ni1000_tk5000, 1000.0),
    (ni120, 120.0),
)


class _LinearThirdPartyRTD:
    """Minimal third-party implementation used to verify structural typing."""

    def celsius_to_resistance(self, temperature_c: float) -> float:
        return 100.0 + temperature_c

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        return resistance_ohms - 100.0

    def resistance_sensitivity_ohms_per_celsius(
        self,
        temperature_c: float,
    ) -> float:
        del temperature_c
        return 1.0

    def temperature_sensitivity_celsius_per_ohm(
        self,
        temperature_c: float,
    ) -> float:
        del temperature_c
        return 1.0


class _UncertaintyOnlyModel:
    """Third-party object that intentionally implements only uncertainty needs."""

    def resistance_to_celsius(self, resistance_ohms: float) -> float:
        return resistance_ohms - 100.0

    def temperature_sensitivity_celsius_per_ohm(
        self,
        temperature_c: float,
    ) -> float:
        del temperature_c
        return 1.0


def _configurable_models_are_rtd_models(
    iec: IEC60751RTDModel,
    cvd: CallendarVanDusenRTDModel,
    polynomial: PolynomialRTDModel,
    piecewise: PiecewisePolynomialRTDModel,
    tabulated: TabulatedRTDModel,
) -> tuple[RTDModel, ...]:
    """Static regression: every public configurable model satisfies RTDModel."""
    return (iec, cvd, polynomial, piecewise, tabulated)


def _rtd_model_is_an_uncertainty_model(model: RTDModel) -> RTDUncertaintyModel:
    """Static regression: the full model protocol includes uncertainty needs."""
    return model


def _behavior_only_third_party_is_an_rtd_model(
    model: _LinearThirdPartyRTD,
) -> RTDModel:
    """Static regression: RTDModel does not require discovery/range metadata."""
    return model


@pytest.mark.parametrize(("model", "r0_ohms"), _BUILTIN_MODELS)
def test_builtin_modules_share_public_rtd_model_behavior(
    model: RTDModel,
    r0_ohms: float,
) -> None:
    assert model.celsius_to_resistance(0.0) == pytest.approx(r0_ohms)
    assert model.resistance_to_celsius(r0_ohms) == pytest.approx(0.0, abs=1e-12)
    assert model.resistance_sensitivity_ohms_per_celsius(0.0) > 0.0
    assert model.temperature_sensitivity_celsius_per_ohm(0.0) > 0.0


def test_third_party_model_requires_no_package_inheritance() -> None:
    model: RTDModel = _LinearThirdPartyRTD()

    assert model.celsius_to_resistance(25.0) == 125.0
    assert model.resistance_to_celsius(125.0) == 25.0
    assert model.resistance_sensitivity_ohms_per_celsius(25.0) == 1.0
    assert model.temperature_sensitivity_celsius_per_ohm(25.0) == 1.0


def test_uncertainty_only_model_keeps_narrow_protocol_compatibility() -> None:
    model: RTDUncertaintyModel = _UncertaintyOnlyModel()

    assert model.resistance_to_celsius(125.0) == 25.0
    assert model.temperature_sensitivity_celsius_per_ohm(25.0) == 1.0
