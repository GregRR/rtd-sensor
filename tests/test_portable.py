# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import json
import math
from typing import Any

import pytest

from rtd_sensor import fitting, portable
from rtd_sensor.exceptions import InvalidPortableModelDefinitionError
from rtd_sensor.models import (
    CallendarVanDusenRTDModel,
    IEC60751RTDModel,
    PiecewisePolynomialRTDModel,
    PiecewisePolynomialSegment,
    PolynomialRTDModel,
    TabulatedRTDModel,
    TabulatedRTDPoint,
)


def _round_trip(model: portable.PortableRTDModel) -> portable.PortableModelDefinition:
    artifact = portable.model_to_portable_definition(model)
    encoded = json.dumps(artifact, allow_nan=False)
    decoded = json.loads(encoded)
    return portable.model_from_portable_definition(decoded)


def _assert_behavior_matches(
    original: portable.PortableRTDModel,
    reconstructed: portable.PortableRTDModel,
    temperatures_c: list[float],
) -> None:
    for temperature_c in temperatures_c:
        original_resistance = original.celsius_to_resistance(temperature_c)
        reconstructed_resistance = reconstructed.celsius_to_resistance(temperature_c)
        assert reconstructed_resistance == pytest.approx(original_resistance, rel=1e-14)
        reconstructed_temperature = reconstructed.resistance_to_celsius(
            reconstructed_resistance
        )
        assert reconstructed_temperature == pytest.approx(temperature_c, abs=1e-10)


def test_characterized_iec_model_round_trip_preserves_behavior_and_range() -> None:
    model = IEC60751RTDModel(
        r0_ohms=100.017,
        minimum_temperature_c=-50.0,
        maximum_temperature_c=250.0,
    )

    loaded = _round_trip(model)

    assert isinstance(loaded.model, IEC60751RTDModel)
    assert loaded.model.r0_ohms == 100.017
    assert loaded.model.minimum_temperature_c == -50.0
    assert loaded.model.maximum_temperature_c == 250.0
    _assert_behavior_matches(model, loaded.model, [-50.0, 0.0, 100.0, 250.0])


def test_fitted_iec_r0_can_be_reconstructed_without_refitting() -> None:
    source_model = IEC60751RTDModel(r0_ohms=100.037)
    observations = (
        fitting.CalibrationObservation(
            temperature_c=0.0,
            resistance_ohms=source_model.celsius_to_resistance(0.0),
        ),
        fitting.CalibrationObservation(
            temperature_c=100.0,
            resistance_ohms=source_model.celsius_to_resistance(100.0),
        ),
    )
    fit = fitting.fit_iec60751_r0(
        observations,
        minimum_temperature_c=-50.0,
        maximum_temperature_c=250.0,
    )

    artifact = portable.model_to_portable_definition(fit.model)
    loaded = portable.model_from_portable_definition(json.loads(json.dumps(artifact)))

    assert isinstance(loaded.model, IEC60751RTDModel)
    assert loaded.model.r0_ohms == fit.model.r0_ohms
    assert loaded.model.minimum_temperature_c == -50.0
    assert loaded.model.maximum_temperature_c == 250.0
    _assert_behavior_matches(fit.model, loaded.model, [-50.0, 0.0, 100.0, 250.0])


def test_custom_cvd_round_trip_preserves_behavior() -> None:
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.025,
        a=3.91e-3,
        b=-5.8e-7,
        c=-4.2e-12,
        minimum_temperature_c=-100.0,
        maximum_temperature_c=250.0,
    )

    loaded = _round_trip(model)

    assert isinstance(loaded.model, CallendarVanDusenRTDModel)
    assert loaded.model.c == -4.2e-12
    _assert_behavior_matches(model, loaded.model, [-100.0, 0.0, 100.0, 250.0])


def test_positive_only_cvd_omits_unused_c() -> None:
    model = CallendarVanDusenRTDModel(
        r0_ohms=100.0,
        a=-6.0e-4,
        b=1.0e-5,
        minimum_temperature_c=50.0,
        maximum_temperature_c=100.0,
    )

    artifact = portable.model_to_portable_definition(model)
    definition = artifact["definition"]

    assert isinstance(definition, dict)
    assert "c" not in definition
    loaded = portable.model_from_portable_definition(artifact)
    assert isinstance(loaded.model, CallendarVanDusenRTDModel)
    assert loaded.model.c is None


def test_polynomial_round_trip_preserves_behavior_and_parameters() -> None:
    model = PolynomialRTDModel(
        reference_resistance_ohms=1000.0,
        reference_temperature_c=25.0,
        coefficients=(0.004, 1e-6),
        minimum_temperature_c=-20.0,
        maximum_temperature_c=120.0,
    )

    loaded = _round_trip(model)

    assert isinstance(loaded.model, PolynomialRTDModel)
    assert loaded.model.reference_resistance_ohms == 1000.0
    assert loaded.model.reference_temperature_c == 25.0
    assert loaded.model.coefficients == (0.004, 1e-6)
    _assert_behavior_matches(model, loaded.model, [-20.0, 25.0, 80.0, 120.0])


def test_fitted_polynomial_can_be_reconstructed_without_refitting() -> None:
    observations = (
        fitting.CalibrationObservation(temperature_c=0.0, resistance_ohms=100.0),
        fitting.CalibrationObservation(temperature_c=50.0, resistance_ohms=119.5),
        fitting.CalibrationObservation(temperature_c=100.0, resistance_ohms=139.0),
        fitting.CalibrationObservation(temperature_c=150.0, resistance_ohms=158.5),
    )
    fit = fitting.fit_polynomial(observations, degree=1)

    artifact = portable.model_to_portable_definition(fit.model)
    loaded = portable.model_from_portable_definition(json.loads(json.dumps(artifact)))

    assert isinstance(loaded.model, PolynomialRTDModel)
    assert loaded.model.coefficients == fit.model.coefficients
    assert loaded.model.reference_resistance_ohms == fit.model.reference_resistance_ohms
    _assert_behavior_matches(fit.model, loaded.model, [0.0, 75.0, 150.0])


def test_piecewise_round_trip_rederives_same_continuity_adjustments() -> None:
    model = PiecewisePolynomialRTDModel(
        reference_resistance_ohms=100.0,
        segments=(
            PiecewisePolynomialSegment(
                minimum_temperature_c=-10.0,
                maximum_temperature_c=0.0,
                coefficients=(1.0, 0.01),
            ),
            PiecewisePolynomialSegment(
                minimum_temperature_c=0.0,
                maximum_temperature_c=10.0,
                coefficients=(1.0, 0.01),
            ),
            PiecewisePolynomialSegment(
                minimum_temperature_c=10.0,
                maximum_temperature_c=20.0,
                coefficients=(0.999999, 0.01),
            ),
        ),
        maximum_continuity_adjustment_ratio=2e-6,
    )

    artifact = portable.model_to_portable_definition(model)
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    assert "continuity_adjustments" not in definition

    loaded = portable.model_from_portable_definition(artifact)
    assert isinstance(loaded.model, PiecewisePolynomialRTDModel)
    assert loaded.model.continuity_adjustments == model.continuity_adjustments
    _assert_behavior_matches(model, loaded.model, [-10.0, 0.0, 10.0, 20.0])


def test_metadata_is_preserved_without_affecting_model_construction() -> None:
    model = IEC60751RTDModel(r0_ohms=100.017)
    metadata = {
        "source": "calibration record 2026-08",
        "nested": {"lab": "Example", "flags": [True, None, 3]},
    }

    artifact = portable.model_to_portable_definition(model, metadata=metadata)
    loaded = portable.model_from_portable_definition(json.loads(json.dumps(artifact)))

    assert loaded.metadata == metadata
    assert loaded.model.name == "IEC 60751 RTD"


def test_model_names_and_python_provenance_are_not_serialized_implicitly() -> None:
    model = PolynomialRTDModel(
        reference_resistance_ohms=100.0,
        reference_temperature_c=0.0,
        coefficients=(0.004,),
        minimum_temperature_c=-20.0,
        maximum_temperature_c=100.0,
        name="Probe serial 123",
        coefficient_source="Private calibration certificate",
    )

    artifact = portable.model_to_portable_definition(model)

    assert "metadata" not in artifact
    assert "Probe serial 123" not in json.dumps(artifact)
    assert "Private calibration certificate" not in json.dumps(artifact)


def test_unsupported_tabulated_model_is_rejected_by_serializer() -> None:
    model = TabulatedRTDModel(
        points=(
            TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
            TabulatedRTDPoint(temperature_c=100.0, resistance_ohms=138.5),
        )
    )

    with pytest.raises(TypeError, match="Portable model definitions support"):
        portable.model_to_portable_definition(model)  # type: ignore[arg-type]


def test_loader_rejects_non_mapping_input() -> None:
    with pytest.raises(TypeError, match="must be a mapping"):
        portable.model_from_portable_definition([])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("artifact_type", "model_fixture_catalog", "artifact_type"),
        ("format_version", 2, "format_version"),
        ("format_version", True, "must be an integer"),
        ("model_kind", "tabulated", "model_kind"),
    ],
)
def test_loader_rejects_unsupported_top_level_semantics(
    field: str,
    value: object,
    message: str,
) -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    artifact[field] = value

    with pytest.raises(InvalidPortableModelDefinitionError, match=message):
        portable.model_from_portable_definition(artifact)


def test_loader_accepts_integral_float_format_version() -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    artifact["format_version"] = 1.0

    loaded = portable.model_from_portable_definition(artifact)

    assert isinstance(loaded.model, IEC60751RTDModel)


def test_loader_rejects_non_string_mapping_keys_cleanly() -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    malformed: dict[object, object] = {}
    malformed.update(artifact)
    malformed[1] = "not a JSON object key"

    with pytest.raises(
        InvalidPortableModelDefinitionError,
        match="object keys must be strings",
    ):
        portable.model_from_portable_definition(malformed)  # type: ignore[arg-type]


def test_loader_rejects_missing_and_unknown_top_level_fields() -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    del artifact["definition"]

    with pytest.raises(InvalidPortableModelDefinitionError, match="missing required"):
        portable.model_from_portable_definition(artifact)

    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    artifact["expected_status"] = "ok"
    with pytest.raises(InvalidPortableModelDefinitionError, match="unsupported field"):
        portable.model_from_portable_definition(artifact)


def test_loader_rejects_unknown_behavior_changing_definition_field() -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    definition["extrapolate"] = True

    with pytest.raises(InvalidPortableModelDefinitionError, match="unsupported field"):
        portable.model_from_portable_definition(artifact)


def test_loader_rejects_unsupported_characteristic_id() -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    definition["characteristic_id"] = "future_characteristic"

    with pytest.raises(InvalidPortableModelDefinitionError, match="characteristic_id"):
        portable.model_from_portable_definition(artifact)


def test_loader_wraps_scientifically_invalid_model_definition() -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    definition["reference_resistance_ohms"] = -1.0

    with pytest.raises(
        InvalidPortableModelDefinitionError,
        match="scientifically invalid",
    ):
        portable.model_from_portable_definition(artifact)


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_loader_rejects_nonfinite_behavioral_number(bad_value: float) -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    definition["reference_resistance_ohms"] = bad_value

    with pytest.raises(InvalidPortableModelDefinitionError, match="must be finite"):
        portable.model_from_portable_definition(artifact)


def test_loader_rejects_boolean_behavioral_number() -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    definition["reference_resistance_ohms"] = True

    with pytest.raises(InvalidPortableModelDefinitionError, match="JSON number"):
        portable.model_from_portable_definition(artifact)


def test_loader_rejects_nonfinite_polynomial_coefficient() -> None:
    model = PolynomialRTDModel(
        reference_resistance_ohms=100.0,
        coefficients=(0.004,),
        minimum_temperature_c=0.0,
        maximum_temperature_c=100.0,
    )
    artifact = portable.model_to_portable_definition(model)
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    definition["coefficients"] = [math.nan]

    with pytest.raises(
        InvalidPortableModelDefinitionError,
        match=r"coefficients\[0\].*finite",
    ):
        portable.model_from_portable_definition(artifact)


def test_loader_rejects_oversized_polynomial_coefficients() -> None:
    model = PolynomialRTDModel(
        reference_resistance_ohms=100.0,
        coefficients=(0.004,),
        minimum_temperature_c=0.0,
        maximum_temperature_c=100.0,
    )
    artifact = portable.model_to_portable_definition(model)
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    definition["coefficients"] = [0.001] * 13

    with pytest.raises(
        InvalidPortableModelDefinitionError,
        match="scientifically invalid",
    ):
        portable.model_from_portable_definition(artifact)


def _piecewise_artifact() -> dict[str, object]:
    model = PiecewisePolynomialRTDModel(
        reference_resistance_ohms=100.0,
        reference_temperature_c=0.0,
        segments=(
            PiecewisePolynomialSegment(
                minimum_temperature_c=-10.0,
                maximum_temperature_c=0.0,
                coefficients=(1.0, 0.01),
            ),
            PiecewisePolynomialSegment(
                minimum_temperature_c=0.0,
                maximum_temperature_c=10.0,
                coefficients=(1.0, 0.01),
            ),
        ),
    )
    return portable.model_to_portable_definition(model)


def test_loader_rejects_empty_piecewise_segments() -> None:
    artifact = _piecewise_artifact()
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    definition["segments"] = []

    with pytest.raises(
        InvalidPortableModelDefinitionError,
        match="scientifically invalid",
    ):
        portable.model_from_portable_definition(artifact)


@pytest.mark.parametrize(
    ("second_minimum_temperature_c", "message"),
    [(1.0, "gaps"), (-1.0, "overlap")],
)
def test_loader_rejects_piecewise_gap_or_overlap(
    second_minimum_temperature_c: float,
    message: str,
) -> None:
    artifact = _piecewise_artifact()
    definition = artifact["definition"]
    assert isinstance(definition, dict)
    segments = definition["segments"]
    assert isinstance(segments, list)
    second = segments[1]
    assert isinstance(second, dict)
    second["minimum_temperature_c"] = second_minimum_temperature_c

    with pytest.raises(InvalidPortableModelDefinitionError, match=message):
        portable.model_from_portable_definition(artifact)


def test_portable_result_fields_are_frozen() -> None:
    artifact = portable.model_to_portable_definition(IEC60751RTDModel(r0_ohms=100.0))
    loaded = portable.model_from_portable_definition(artifact)

    with pytest.raises(AttributeError):
        loaded.__setattr__("model", IEC60751RTDModel(r0_ohms=100.1))


def test_metadata_must_be_json_compatible_and_finite() -> None:
    model = IEC60751RTDModel(r0_ohms=100.0)

    with pytest.raises(InvalidPortableModelDefinitionError, match="JSON-compatible"):
        portable.model_to_portable_definition(model, metadata={"bad": object()})

    with pytest.raises(InvalidPortableModelDefinitionError, match="must be finite"):
        portable.model_to_portable_definition(model, metadata={"bad": math.nan})


def test_metadata_input_is_normalized_without_aliasing_nested_values() -> None:
    model = IEC60751RTDModel(r0_ohms=100.0)
    nested = [1, {"value": 2}]
    metadata: dict[str, Any] = {"nested": nested}

    artifact = portable.model_to_portable_definition(model, metadata=metadata)
    nested.append(3)

    assert artifact["metadata"] == {"nested": [1, {"value": 2}]}
