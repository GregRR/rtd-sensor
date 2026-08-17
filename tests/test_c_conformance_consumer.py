# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Cross-language verification using the independent C11 conformance consumer."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CONFORMANCE_DIR = _ROOT / "conformance" / "v1"
_CONSUMER_DIR = _ROOT / "conformance" / "consumers" / "c11"
_BUILTIN_VECTOR_FILENAMES = (
    "builtin-temperature-to-resistance.json",
    "builtin-resistance-to-temperature.json",
    "builtin-temperature-to-resistance-status.json",
    "builtin-resistance-to-temperature-status.json",
)

_CUSTOM_VECTOR_FILENAMES = (
    "custom-temperature-to-resistance.json",
    "custom-resistance-to-temperature.json",
    "custom-temperature-to-resistance-status.json",
    "custom-resistance-to-temperature-status.json",
)

_STATUS_ENUMS = {
    "ok": "RTD_CONFORMANCE_OK",
    "out_of_range_low": "RTD_CONFORMANCE_OUT_OF_RANGE_LOW",
    "out_of_range_high": "RTD_CONFORMANCE_OUT_OF_RANGE_HIGH",
    "invalid_input": "RTD_CONFORMANCE_INVALID_INPUT",
    "invalid_model": "RTD_CONFORMANCE_INVALID_MODEL",
    "calculation_failure": "RTD_CONFORMANCE_CALCULATION_FAILURE",
}

_CURVE_ENUMS = {
    "callendar_van_dusen": "RTD_CURVE_CALLENDAR_VAN_DUSEN",
    "polynomial": "RTD_CURVE_POLYNOMIAL",
    "piecewise_polynomial": "RTD_CURVE_PIECEWISE_POLYNOMIAL",
}

_CAPABILITY_ENUMS = {
    "conversion.temperature_to_resistance": "OP_TEMPERATURE_TO_RESISTANCE",
    "conversion.resistance_to_temperature": "OP_RESISTANCE_TO_TEMPERATURE",
}


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _c_float(value: int | float) -> str:
    numeric = float(value)
    if numeric == 0.0:
        return "0.0"
    return numeric.hex()


def _c_input(input_document: dict[str, Any]) -> str:
    if "value" in input_document:
        value = input_document["value"]
        assert isinstance(value, int | float)
        return _c_float(value)

    special = input_document["special"]
    assert isinstance(special, str)
    return {
        "nan": "NAN",
        "positive_infinity": "INFINITY",
        "negative_infinity": "(-INFINITY)",
    }[special]


def _available_c_compiler() -> list[str] | None:
    configured = os.environ.get("CC")
    if configured:
        command = shlex.split(configured)
        if command and shutil.which(command[0]):
            return command

    for candidate in ("cc", "clang", "gcc"):
        executable = shutil.which(candidate)
        if executable is not None:
            return [executable]
    return None


def _characteristic_source(
    characteristics: list[dict[str, Any]],
) -> tuple[str, dict[str, int]]:
    lines: list[str] = []
    characteristic_indexes: dict[str, int] = {}

    for characteristic_index, characteristic in enumerate(characteristics):
        characteristic_id = characteristic["characteristic_id"]
        assert isinstance(characteristic_id, str)
        characteristic_indexes[characteristic_id] = characteristic_index

        curve_kind = characteristic["curve_kind"]
        assert isinstance(curve_kind, str)
        if curve_kind == "polynomial":
            coefficients = characteristic["coefficients"]
            assert isinstance(coefficients, list)
            rendered = ", ".join(_c_float(value) for value in coefficients)
            lines.append(
                "static const double characteristic_"
                f"{characteristic_index}_coefficients[] = {{{rendered}}};"
            )
        elif curve_kind == "piecewise_polynomial":
            segments = characteristic["segments"]
            adjustments = characteristic["derived_continuity_adjustments"]
            assert isinstance(segments, list)
            assert isinstance(adjustments, list)
            assert len(segments) == len(adjustments)

            for segment_index, segment in enumerate(segments):
                coefficients = segment["coefficients"]
                assert isinstance(coefficients, list)
                rendered = ", ".join(_c_float(value) for value in coefficients)
                lines.append(
                    "static const double "
                    f"characteristic_{characteristic_index}_segment_"
                    f"{segment_index}_coefficients[] = {{{rendered}}};"
                )

            lines.append(
                "static const rtd_piecewise_segment "
                f"characteristic_{characteristic_index}_segments[] = {{"
            )
            for segment_index, (segment, adjustment) in enumerate(
                zip(segments, adjustments, strict=True)
            ):
                coefficients = segment["coefficients"]
                assert isinstance(coefficients, list)
                lines.extend(
                    (
                        "    {",
                        "        .minimum_temperature_c = "
                        f"{_c_float(segment['minimum_temperature_c'])},",
                        "        .maximum_temperature_c = "
                        f"{_c_float(segment['maximum_temperature_c'])},",
                        "        .temperature_origin_c = "
                        f"{_c_float(segment['temperature_origin_c'])},",
                        "        .coefficients = characteristic_"
                        f"{characteristic_index}_segment_{segment_index}_coefficients,",
                        f"        .coefficient_count = {len(coefficients)},",
                        f"        .continuity_adjustment = {_c_float(adjustment)},",
                        "    },",
                    )
                )
            lines.append("};")

    lines.append("static const rtd_characteristic characteristics[] = {")
    for characteristic_index, characteristic in enumerate(characteristics):
        curve_kind = characteristic["curve_kind"]
        assert isinstance(curve_kind, str)
        lines.extend(
            (
                "    {",
                "        .characteristic_id = "
                f'"{characteristic["characteristic_id"]}",',
                f"        .curve_kind = {_CURVE_ENUMS[curve_kind]},",
                "        .reference_temperature_c = "
                f"{_c_float(characteristic['reference_temperature_c'])},",
                "        .minimum_temperature_c = "
                f"{_c_float(characteristic['minimum_temperature_c'])},",
                "        .maximum_temperature_c = "
                f"{_c_float(characteristic['maximum_temperature_c'])},",
            )
        )

        if curve_kind == "callendar_van_dusen":
            parameters = characteristic["parameters"]
            assert isinstance(parameters, dict)
            lines.extend(
                (
                    "        .data = {.cvd = {",
                    f"            .a = {_c_float(parameters['a'])},",
                    f"            .b = {_c_float(parameters['b'])},",
                    f"            .c = {_c_float(parameters['c'])},",
                    "            .c_is_present = "
                    f"{1 if characteristic.get('c_is_present', True) else 0},",
                    "        }},",
                )
            )
        elif curve_kind == "polynomial":
            coefficients = characteristic["coefficients"]
            assert isinstance(coefficients, list)
            lines.extend(
                (
                    "        .data = {.polynomial = {",
                    "            .coefficients = characteristic_"
                    f"{characteristic_index}_coefficients,",
                    f"            .coefficient_count = {len(coefficients)},",
                    "        }},",
                )
            )
        elif curve_kind == "piecewise_polynomial":
            segments = characteristic["segments"]
            maximum_adjustment = characteristic.get(
                "maximum_continuity_adjustment_ratio", 0.0
            )
            assert isinstance(segments, list)
            assert isinstance(maximum_adjustment, int | float)
            lines.extend(
                (
                    "        .data = {.piecewise = {",
                    "            .segments = characteristic_"
                    f"{characteristic_index}_segments,",
                    f"            .segment_count = {len(segments)},",
                    "            .maximum_continuity_adjustment_ratio = "
                    f"{_c_float(maximum_adjustment)},",
                    "        }},",
                )
            )
        else:
            raise AssertionError(f"Unexpected curve kind: {curve_kind}")
        lines.extend(("    },",))
    lines.append("};")

    return "\n".join(lines), characteristic_indexes


def _model_source(
    models: list[dict[str, Any]],
    characteristic_indexes: dict[str, int],
) -> tuple[str, dict[str, int]]:
    lines = ["static const rtd_model models[] = {"]
    model_indexes: dict[str, int] = {}

    for model_index, model in enumerate(models):
        model_id = model["model_id"]
        characteristic_id = model["characteristic_id"]
        assert isinstance(model_id, str)
        assert isinstance(characteristic_id, str)
        model_indexes[model_id] = model_index
        characteristic_index = characteristic_indexes[characteristic_id]
        lines.extend(
            (
                "    {",
                f'        .model_id = "{model_id}",',
                f"        .characteristic = &characteristics[{characteristic_index}],",
                "        .reference_resistance_ohms = "
                f"{_c_float(model['reference_resistance_ohms'])},",
                "        .minimum_temperature_c = "
                f"{_c_float(model['minimum_temperature_c'])},",
                "        .maximum_temperature_c = "
                f"{_c_float(model['maximum_temperature_c'])},",
                "    },",
            )
        )
    lines.append("};")
    return "\n".join(lines), model_indexes


def _case_source(
    model_indexes: dict[str, int],
    *,
    vector_filenames: tuple[str, ...],
    group_identity_field: str,
    acceptance_profile: str,
    included_identities: frozenset[str] | None = None,
) -> tuple[str, int]:
    cases: list[str] = []

    for filename in vector_filenames:
        document = _load_json(_CONFORMANCE_DIR / "vectors" / filename)
        capability_id = document["capability_id"]
        assert isinstance(capability_id, str)
        operation = _CAPABILITY_ENUMS[capability_id]
        groups = document["test_groups"]
        assert isinstance(groups, list)

        for group in groups:
            model_identity = group[group_identity_field]
            assert isinstance(model_identity, str)
            if (
                included_identities is not None
                and model_identity not in included_identities
            ):
                continue
            model_index = model_indexes[model_identity]
            group_cases = group["cases"]
            assert isinstance(group_cases, list)

            for case in group_cases:
                expected = case["expected"]
                input_document = case["input"]
                assert isinstance(expected, dict)
                assert isinstance(input_document, dict)
                status = expected["status"]
                assert isinstance(status, str)

                if status == "ok":
                    expected_value = expected["value"]
                    acceptance = expected["acceptance"]
                    assert isinstance(expected_value, int | float)
                    assert isinstance(acceptance, dict)
                    profile = acceptance[acceptance_profile]
                    assert isinstance(profile, dict)
                    tolerance = profile["absolute_tolerance"]
                    assert isinstance(tolerance, int | float)
                    expects_value = 1
                    expected_value_c = _c_float(expected_value)
                    tolerance_c = _c_float(tolerance)
                else:
                    expects_value = 0
                    expected_value_c = "0.0"
                    tolerance_c = "0.0"

                cases.append(
                    "    {"
                    f'"{case["case_id"]}", {operation}, {model_index}, '
                    f"{_c_input(input_document)}, {_STATUS_ENUMS[status]}, "
                    f"{expected_value_c}, {tolerance_c}, {expects_value}"
                    "},"
                )

    source = "\n".join(
        (
            "static const conformance_case cases[] = {",
            *cases,
            "};",
        )
    )
    return source, len(cases)


def _custom_characteristics_and_models() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[tuple[str, str]],
]:
    fixture_catalog = _load_json(_CONFORMANCE_DIR / "model-fixtures.json")
    fixtures = fixture_catalog["fixtures"]
    assert isinstance(fixtures, list)

    characteristics: list[dict[str, Any]] = []
    models: list[dict[str, Any]] = []
    expectations: list[tuple[str, str]] = []

    for fixture in fixtures:
        assert isinstance(fixture, dict)
        fixture_id = fixture["fixture_id"]
        fixture_kind = fixture["fixture_kind"]
        expected_status = fixture["expected_status"]
        definition = fixture["definition"]
        assert isinstance(fixture_id, str)
        assert isinstance(fixture_kind, str)
        assert isinstance(expected_status, str)
        assert isinstance(definition, dict)

        if fixture_kind == "characteristic_model":
            characteristic_id = definition["characteristic_id"]
            minimum_temperature_c = definition["minimum_temperature_c"]
            maximum_temperature_c = definition["maximum_temperature_c"]
        else:
            characteristic_id = f"fixture.{fixture_id}"
            if fixture_kind == "callendar_van_dusen":
                minimum_temperature_c = definition["minimum_temperature_c"]
                maximum_temperature_c = definition["maximum_temperature_c"]
                characteristics.append(
                    {
                        "characteristic_id": characteristic_id,
                        "curve_kind": "callendar_van_dusen",
                        "reference_temperature_c": 0.0,
                        "minimum_temperature_c": minimum_temperature_c,
                        "maximum_temperature_c": maximum_temperature_c,
                        "parameters": {
                            "a": definition["a"],
                            "b": definition["b"],
                            "c": definition.get("c", 0.0),
                        },
                        "c_is_present": "c" in definition,
                    }
                )
            elif fixture_kind == "polynomial":
                minimum_temperature_c = definition["minimum_temperature_c"]
                maximum_temperature_c = definition["maximum_temperature_c"]
                characteristics.append(
                    {
                        "characteristic_id": characteristic_id,
                        "curve_kind": "polynomial",
                        "reference_temperature_c": definition[
                            "reference_temperature_c"
                        ],
                        "minimum_temperature_c": minimum_temperature_c,
                        "maximum_temperature_c": maximum_temperature_c,
                        "coefficients": definition["coefficients"],
                    }
                )
            elif fixture_kind == "piecewise_polynomial":
                segments = definition["segments"]
                assert isinstance(segments, list)
                minimum_temperature_c = segments[0]["minimum_temperature_c"]
                maximum_temperature_c = segments[-1]["maximum_temperature_c"]
                derived = fixture.get("derived")
                if derived is None:
                    adjustments = [0.0] * len(segments)
                else:
                    assert isinstance(derived, dict)
                    adjustments = derived["continuity_adjustments"]
                    assert isinstance(adjustments, list)
                characteristics.append(
                    {
                        "characteristic_id": characteristic_id,
                        "curve_kind": "piecewise_polynomial",
                        "reference_temperature_c": definition[
                            "reference_temperature_c"
                        ],
                        "minimum_temperature_c": minimum_temperature_c,
                        "maximum_temperature_c": maximum_temperature_c,
                        "segments": segments,
                        "derived_continuity_adjustments": adjustments,
                        "maximum_continuity_adjustment_ratio": definition[
                            "maximum_continuity_adjustment_ratio"
                        ],
                    }
                )
            else:
                raise AssertionError(f"Unexpected fixture kind: {fixture_kind}")

        models.append(
            {
                "model_id": fixture_id,
                "characteristic_id": characteristic_id,
                "reference_resistance_ohms": definition["reference_resistance_ohms"],
                "minimum_temperature_c": minimum_temperature_c,
                "maximum_temperature_c": maximum_temperature_c,
            }
        )
        expectations.append((fixture_id, expected_status))

    return characteristics, models, expectations


def _binary32_custom_fixture_ids() -> frozenset[str]:
    fixture_ids: set[str] = set()
    for filename in (
        "custom-temperature-to-resistance.json",
        "custom-resistance-to-temperature.json",
    ):
        document = _load_json(_CONFORMANCE_DIR / "vectors" / filename)
        groups = document["test_groups"]
        assert isinstance(groups, list)
        for group in groups:
            assert isinstance(group, dict)
            group_cases = group["cases"]
            assert isinstance(group_cases, list)
            if not any(
                isinstance(case, dict)
                and isinstance(case.get("expected"), dict)
                and isinstance(case["expected"].get("acceptance"), dict)
                and "binary32_compatible" in case["expected"]["acceptance"]
                for case in group_cases
            ):
                continue
            fixture_id = group["fixture_id"]
            assert isinstance(fixture_id, str)
            fixture_ids.add(fixture_id)

    return frozenset(fixture_ids)


def _characterized_r0_models() -> tuple[list[dict[str, Any]], frozenset[str]]:
    binary32_fixture_ids = _binary32_custom_fixture_ids()
    fixture_catalog = _load_json(_CONFORMANCE_DIR / "model-fixtures.json")
    fixtures = fixture_catalog["fixtures"]
    assert isinstance(fixtures, list)

    models: list[dict[str, Any]] = []
    found_fixture_ids: set[str] = set()
    for fixture in fixtures:
        assert isinstance(fixture, dict)
        fixture_id = fixture["fixture_id"]
        assert isinstance(fixture_id, str)
        if fixture_id not in binary32_fixture_ids:
            continue
        assert fixture["fixture_kind"] == "characteristic_model"
        assert fixture["expected_status"] == "ok"
        definition = fixture["definition"]
        assert isinstance(definition, dict)
        characteristic_id = definition["characteristic_id"]
        assert isinstance(characteristic_id, str)
        found_fixture_ids.add(fixture_id)
        models.append(
            {
                "model_id": fixture_id,
                "characteristic_id": characteristic_id,
                "reference_resistance_ohms": definition["reference_resistance_ohms"],
                "minimum_temperature_c": definition["minimum_temperature_c"],
                "maximum_temperature_c": definition["maximum_temperature_c"],
            }
        )

    assert found_fixture_ids == set(binary32_fixture_ids)
    return models, binary32_fixture_ids


def _fixture_expectation_source(
    expectations: list[tuple[str, str]],
    model_indexes: dict[str, int],
) -> str:
    lines = ["static const fixture_expectation fixture_expectations[] = {"]
    for fixture_id, expected_status in expectations:
        lines.append(
            "    {"
            f'"{fixture_id}", {model_indexes[fixture_id]}, '
            f"{_STATUS_ENUMS[expected_status]}"
            "},"
        )
    lines.append("};")
    return "\n".join(lines)


def _custom_runner_source() -> tuple[str, int, int]:
    characteristic_catalog = _load_json(_CONFORMANCE_DIR / "characteristics.json")
    builtin_characteristics = characteristic_catalog["characteristics"]
    assert isinstance(builtin_characteristics, list)

    custom_characteristics, models, expectations = _custom_characteristics_and_models()
    characteristics = [*builtin_characteristics, *custom_characteristics]
    characteristic_source, characteristic_indexes = _characteristic_source(
        characteristics
    )
    model_source, model_indexes = _model_source(models, characteristic_indexes)
    expectation_source = _fixture_expectation_source(expectations, model_indexes)
    case_source, case_count = _case_source(
        model_indexes,
        vector_filenames=_CUSTOM_VECTOR_FILENAMES,
        group_identity_field="fixture_id",
        acceptance_profile="binary64_reference",
    )

    source = f"""#include "rtd_conformance.h"

#include <math.h>
#include <stddef.h>
#include <stdio.h>

typedef enum {{
    OP_TEMPERATURE_TO_RESISTANCE = 0,
    OP_RESISTANCE_TO_TEMPERATURE
}} conformance_operation;

typedef struct {{
    const char *case_id;
    conformance_operation operation;
    size_t model_index;
    double input;
    rtd_conformance_status expected_status;
    double expected_value;
    double tolerance;
    int expects_value;
}} conformance_case;

typedef struct {{
    const char *fixture_id;
    size_t model_index;
    rtd_conformance_status expected_status;
}} fixture_expectation;

{characteristic_source}

{model_source}

{expectation_source}

{case_source}

int main(void) {{
    size_t index;
    size_t validated_fixtures = 0;
    size_t passed_cases = 0;

    for (
        index = 0;
        index < sizeof(fixture_expectations) / sizeof(fixture_expectations[0]);
        index += 1
    ) {{
        const fixture_expectation *expectation = &fixture_expectations[index];
        const rtd_conformance_status actual =
            rtd_validate_model(&models[expectation->model_index]);
        if (actual != expectation->expected_status) {{
            fprintf(
                stderr,
                "%s: expected model status %s, got %s\\n",
                expectation->fixture_id,
                rtd_conformance_status_name(expectation->expected_status),
                rtd_conformance_status_name(actual)
            );
            return 1;
        }}
        validated_fixtures += 1;
    }}

    for (index = 0; index < sizeof(cases) / sizeof(cases[0]); index += 1) {{
        const conformance_case *test_case = &cases[index];
        const rtd_model *model = &models[test_case->model_index];
        rtd_conformance_result actual;

        if (test_case->operation == OP_TEMPERATURE_TO_RESISTANCE) {{
            actual = rtd_temperature_to_resistance(model, test_case->input);
        }} else {{
            actual = rtd_resistance_to_temperature(model, test_case->input);
        }}

        if (actual.status != test_case->expected_status) {{
            fprintf(
                stderr,
                "%s: expected status %s, got %s\\n",
                test_case->case_id,
                rtd_conformance_status_name(test_case->expected_status),
                rtd_conformance_status_name(actual.status)
            );
            return 1;
        }}

        if (test_case->expects_value) {{
            const double error = fabs(actual.value - test_case->expected_value);
            if (!isfinite(actual.value) || error > test_case->tolerance) {{
                fprintf(
                    stderr,
                    "%s: expected %.17g +/- %.17g, got %.17g (error %.17g)\\n",
                    test_case->case_id,
                    test_case->expected_value,
                    test_case->tolerance,
                    actual.value,
                    error
                );
                return 1;
            }}
        }}
        passed_cases += 1;
    }}

    printf(
        "validated %zu fixtures; passed %zu cases\\n",
        validated_fixtures,
        passed_cases
    );
    return 0;
}}
"""
    return source, len(expectations), case_count


def _runner_source(
    *,
    acceptance_profile: str = "binary64_reference",
) -> tuple[str, int]:
    characteristic_catalog = _load_json(_CONFORMANCE_DIR / "characteristics.json")
    model_catalog = _load_json(_CONFORMANCE_DIR / "models.json")
    characteristics = characteristic_catalog["characteristics"]
    models = model_catalog["models"]
    assert isinstance(characteristics, list)
    assert isinstance(models, list)

    characteristic_source, characteristic_indexes = _characteristic_source(
        characteristics
    )
    model_source, model_indexes = _model_source(models, characteristic_indexes)
    case_source, case_count = _case_source(
        model_indexes,
        vector_filenames=_BUILTIN_VECTOR_FILENAMES,
        group_identity_field="model_id",
        acceptance_profile=acceptance_profile,
    )

    source = f"""#include "rtd_conformance.h"

#include <math.h>
#include <stddef.h>
#include <stdio.h>

typedef enum {{
    OP_TEMPERATURE_TO_RESISTANCE = 0,
    OP_RESISTANCE_TO_TEMPERATURE
}} conformance_operation;

typedef struct {{
    const char *case_id;
    conformance_operation operation;
    size_t model_index;
    double input;
    rtd_conformance_status expected_status;
    double expected_value;
    double tolerance;
    int expects_value;
}} conformance_case;

{characteristic_source}

{model_source}

{case_source}

int main(void) {{
    size_t index;
    size_t passed = 0;
    double maximum_forward_error = 0.0;
    double maximum_inverse_error = 0.0;

    for (index = 0; index < sizeof(cases) / sizeof(cases[0]); index += 1) {{
        const conformance_case *test_case = &cases[index];
        const rtd_model *model = &models[test_case->model_index];
        rtd_conformance_result actual;

        if (test_case->operation == OP_TEMPERATURE_TO_RESISTANCE) {{
            actual = rtd_temperature_to_resistance(model, test_case->input);
        }} else {{
            actual = rtd_resistance_to_temperature(model, test_case->input);
        }}

        if (actual.status != test_case->expected_status) {{
            fprintf(
                stderr,
                "%s: expected status %s, got %s\\n",
                test_case->case_id,
                rtd_conformance_status_name(test_case->expected_status),
                rtd_conformance_status_name(actual.status)
            );
            return 1;
        }}

        if (test_case->expects_value) {{
            const double error = fabs(actual.value - test_case->expected_value);
            if (!isfinite(actual.value) || error > test_case->tolerance) {{
                fprintf(
                    stderr,
                    "%s: expected %.17g +/- %.17g, got %.17g (error %.17g)\\n",
                    test_case->case_id,
                    test_case->expected_value,
                    test_case->tolerance,
                    actual.value,
                    error
                );
                return 1;
            }}
            if (test_case->operation == OP_TEMPERATURE_TO_RESISTANCE) {{
                if (error > maximum_forward_error) {{
                    maximum_forward_error = error;
                }}
            }} else if (error > maximum_inverse_error) {{
                maximum_inverse_error = error;
            }}
        }}
        passed += 1;
    }}

    printf(
        "passed %zu cases; max forward error %.17g ohm; max inverse error %.17g C\\n",
        passed,
        maximum_forward_error,
        maximum_inverse_error
    );
    return 0;
}}
"""
    return source, case_count


def test_independent_c11_consumer_passes_published_builtin_vectors(
    tmp_path: Path,
) -> None:
    compiler = _available_c_compiler()
    if compiler is None:
        pytest.skip("No C compiler is available for independent conformance testing")

    runner_source, case_count = _runner_source()
    runner_path = tmp_path / "generated_conformance_runner.c"
    executable_path = tmp_path / "rtd_conformance_consumer"
    runner_path.write_text(runner_source, encoding="utf-8")

    compile_result = subprocess.run(
        [
            *compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-O2",
            "-I",
            str(_CONSUMER_DIR),
            str(_CONSUMER_DIR / "rtd_conformance.c"),
            str(runner_path),
            "-lm",
            "-o",
            str(executable_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stderr

    run_result = subprocess.run(
        [str(executable_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stderr
    assert run_result.stdout.startswith(f"passed {case_count} cases;")


def test_independent_c11_consumer_passes_published_custom_fixture_layer(
    tmp_path: Path,
) -> None:
    compiler = _available_c_compiler()
    if compiler is None:
        pytest.skip("No C compiler is available for custom conformance testing")

    runner_source, fixture_count, case_count = _custom_runner_source()
    runner_path = tmp_path / "generated_custom_conformance_runner.c"
    executable_path = tmp_path / "rtd_custom_conformance_consumer"
    runner_path.write_text(runner_source, encoding="utf-8")

    compile_result = subprocess.run(
        [
            *compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-O2",
            "-I",
            str(_CONSUMER_DIR),
            str(_CONSUMER_DIR / "rtd_conformance.c"),
            str(runner_path),
            "-lm",
            "-o",
            str(executable_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stderr

    run_result = subprocess.run(
        [str(executable_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stderr
    assert run_result.stdout.startswith(
        f"validated {fixture_count} fixtures; passed {case_count} cases"
    )


def _characterized_r0_binary32_runner_source() -> tuple[str, int]:
    characteristic_catalog = _load_json(_CONFORMANCE_DIR / "characteristics.json")
    characteristics = characteristic_catalog["characteristics"]
    assert isinstance(characteristics, list)

    models, fixture_ids = _characterized_r0_models()
    characteristic_source, characteristic_indexes = _characteristic_source(
        characteristics
    )
    model_source, model_indexes = _model_source(models, characteristic_indexes)
    case_source, case_count = _case_source(
        model_indexes,
        vector_filenames=_CUSTOM_VECTOR_FILENAMES,
        group_identity_field="fixture_id",
        acceptance_profile="binary32_compatible",
        included_identities=fixture_ids,
    )

    source = f"""#include "rtd_conformance_f32.h"

#include <math.h>
#include <stddef.h>
#include <stdio.h>

typedef enum {{
    OP_TEMPERATURE_TO_RESISTANCE = 0,
    OP_RESISTANCE_TO_TEMPERATURE
}} conformance_operation;

typedef struct {{
    const char *case_id;
    conformance_operation operation;
    size_t model_index;
    float input;
    rtd_conformance_status expected_status;
    double expected_value;
    double tolerance;
    int expects_value;
}} conformance_case;

{characteristic_source}

{model_source}

{case_source}

int main(void) {{
    size_t index;
    size_t passed = 0;
    double maximum_forward_error = 0.0;
    double maximum_inverse_error = 0.0;

    for (index = 0; index < sizeof(cases) / sizeof(cases[0]); index += 1) {{
        const conformance_case *test_case = &cases[index];
        const rtd_model *model = &models[test_case->model_index];
        rtd_conformance_result actual;

        if (test_case->operation == OP_TEMPERATURE_TO_RESISTANCE) {{
            actual = rtd_temperature_to_resistance(model, test_case->input);
        }} else {{
            actual = rtd_resistance_to_temperature(model, test_case->input);
        }}

        if (actual.status != test_case->expected_status) {{
            fprintf(
                stderr,
                "%s: expected status %s, got %s\\n",
                test_case->case_id,
                rtd_conformance_status_name(test_case->expected_status),
                rtd_conformance_status_name(actual.status)
            );
            return 1;
        }}

        if (test_case->expects_value) {{
            const double error = fabs((double)actual.value - test_case->expected_value);
            if (!isfinite(actual.value) || error > test_case->tolerance) {{
                fprintf(
                    stderr,
                    "%s: expected %.17g +/- %.17g, got %.17g (error %.17g)\\n",
                    test_case->case_id,
                    test_case->expected_value,
                    test_case->tolerance,
                    (double)actual.value,
                    error
                );
                return 1;
            }}
            if (test_case->operation == OP_TEMPERATURE_TO_RESISTANCE) {{
                if (error > maximum_forward_error) {{
                    maximum_forward_error = error;
                }}
            }} else if (error > maximum_inverse_error) {{
                maximum_inverse_error = error;
            }}
        }}
        passed += 1;
    }}

    printf(
        "passed %zu characterized-R0 cases; max forward error %.17g ohm; "
        "max inverse error %.17g C\\n",
        passed,
        maximum_forward_error,
        maximum_inverse_error
    );
    return 0;
}}
"""
    source = source.replace(
        "static const double characteristic_",
        "static const float characteristic_",
    )
    return source, case_count


def _binary32_runner_source() -> tuple[str, int]:
    source, case_count = _runner_source(acceptance_profile="binary32_compatible")
    source = source.replace(
        '#include "rtd_conformance.h"',
        '#include "rtd_conformance_f32.h"',
        1,
    )
    source = source.replace(
        "static const double characteristic_",
        "static const float characteristic_",
    )
    source = source.replace("    double input;", "    float input;")
    return source, case_count


def test_independent_c11_binary32_consumer_passes_published_builtin_vectors(
    tmp_path: Path,
) -> None:
    compiler = _available_c_compiler()
    if compiler is None:
        pytest.skip("No C compiler is available for binary32 conformance testing")

    runner_source, case_count = _binary32_runner_source()
    runner_path = tmp_path / "generated_binary32_conformance_runner.c"
    executable_path = tmp_path / "rtd_binary32_conformance_consumer"
    runner_path.write_text(runner_source, encoding="utf-8")

    compile_result = subprocess.run(
        [
            *compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-O2",
            "-I",
            str(_CONSUMER_DIR),
            str(_CONSUMER_DIR / "rtd_conformance_f32.c"),
            str(runner_path),
            "-lm",
            "-o",
            str(executable_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stderr

    run_result = subprocess.run(
        [str(executable_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stderr
    assert run_result.stdout.startswith(f"passed {case_count} cases;")


def test_independent_c11_binary32_consumer_passes_characterized_r0_vectors(
    tmp_path: Path,
) -> None:
    compiler = _available_c_compiler()
    if compiler is None:
        pytest.skip("No C compiler is available for characterized-R0 testing")

    runner_source, case_count = _characterized_r0_binary32_runner_source()
    runner_path = tmp_path / "generated_characterized_r0_binary32_runner.c"
    executable_path = tmp_path / "rtd_characterized_r0_binary32_consumer"
    runner_path.write_text(runner_source, encoding="utf-8")

    compile_result = subprocess.run(
        [
            *compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-O2",
            "-I",
            str(_CONSUMER_DIR),
            str(_CONSUMER_DIR / "rtd_conformance_f32.c"),
            str(runner_path),
            "-lm",
            "-o",
            str(executable_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stderr

    run_result = subprocess.run(
        [str(executable_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stderr
    assert run_result.stdout.startswith(f"passed {case_count} characterized-R0 cases;")


def test_characterized_r0_binary32_stress_study_stays_within_profile(
    tmp_path: Path,
) -> None:
    compiler = _available_c_compiler()
    if compiler is None:
        pytest.skip("No C compiler is available for characterized-R0 study")

    executable_path = tmp_path / "characterized_r0_binary32_study"
    compile_result = subprocess.run(
        [
            *compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-O2",
            "-I",
            str(_CONSUMER_DIR),
            str(_CONSUMER_DIR / "rtd_conformance_f32.c"),
            str(_CONSUMER_DIR / "characterized_r0_study.c"),
            "-lm",
            "-o",
            str(executable_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stderr

    run_result = subprocess.run(
        [str(executable_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stderr

    metrics = dict(
        line.split("=", 1) for line in run_result.stdout.splitlines() if "=" in line
    )
    assert int(metrics["sample_count"]) == 1_320_843
    # Keep CI substantially inside the public profile so the documented
    # engineering margin cannot silently collapse while the broad tolerance
    # still passes.
    assert float(metrics["maximum_forward_error_ohm"]) < 0.001
    assert float(metrics["maximum_inverse_error_c"]) < 0.0004
