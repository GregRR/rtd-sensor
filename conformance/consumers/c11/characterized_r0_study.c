/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Deterministic binary32 stress study for characterized IEC 60751 PT-385 R0.
 *
 * This program deliberately keeps its binary64 reference equation local rather
 * than importing Python results. The float path under test is the independent
 * rtd_conformance_f32 consumer. It is evidence for the bounded characterized-R0
 * acceptance profile, not a production embedded implementation.
 */

#include "rtd_conformance_f32.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>

#define R0_GRID_INTERVALS 80
#define TEMPERATURE_GRID_INTERVALS 4200
#define RANDOM_SAMPLE_COUNT 300000

static double reference_ratio(double temperature_c) {
    const double a = 3.9083e-3;
    const double b = -5.775e-7;
    const double c = -4.183e-12;
    double ratio = 1.0 + a * temperature_c + b * temperature_c * temperature_c;

    if (temperature_c < 0.0) {
        ratio += c * (temperature_c - 100.0) * temperature_c * temperature_c *
                 temperature_c;
    }
    return ratio;
}

static uint32_t random_state = UINT32_C(0x6d2b79f5);

static uint32_t next_random(void) {
    random_state = random_state * UINT32_C(1664525) + UINT32_C(1013904223);
    return random_state;
}

static double unit_random(void) {
    return (double)next_random() / 4294967295.0;
}

static int evaluate_case(
    const rtd_characteristic *characteristic,
    double reference_resistance_ohms,
    double temperature_c,
    double *maximum_forward_error,
    double *maximum_inverse_error,
    double *maximum_r0_representation_effect
) {
    const float binary32_r0 = (float)reference_resistance_ohms;
    const double reference_resistance =
        reference_resistance_ohms * reference_ratio(temperature_c);
    const double rounded_r0_reference_resistance =
        (double)binary32_r0 * reference_ratio(temperature_c);
    const rtd_model model = {
        .model_id = "characterized_r0_study",
        .characteristic = characteristic,
        .reference_resistance_ohms = binary32_r0,
        .minimum_temperature_c = -200.0f,
        .maximum_temperature_c = 850.0f,
    };
    const rtd_conformance_result forward =
        rtd_temperature_to_resistance(&model, (float)temperature_c);
    const rtd_conformance_result inverse =
        rtd_resistance_to_temperature(&model, (float)reference_resistance);
    const double forward_error = fabs((double)forward.value - reference_resistance);
    const double inverse_error = fabs((double)inverse.value - temperature_c);
    const double r0_representation_effect =
        fabs(rounded_r0_reference_resistance - reference_resistance);

    if (forward.status != RTD_CONFORMANCE_OK ||
        inverse.status != RTD_CONFORMANCE_OK) {
        return 0;
    }
    if (forward_error > *maximum_forward_error) {
        *maximum_forward_error = forward_error;
    }
    if (inverse_error > *maximum_inverse_error) {
        *maximum_inverse_error = inverse_error;
    }
    if (r0_representation_effect > *maximum_r0_representation_effect) {
        *maximum_r0_representation_effect = r0_representation_effect;
    }
    return 1;
}

int main(void) {
    const rtd_characteristic characteristic = {
        .characteristic_id = "iec60751_pt385",
        .curve_kind = RTD_CURVE_CALLENDAR_VAN_DUSEN,
        .reference_temperature_c = 0.0f,
        .minimum_temperature_c = -200.0f,
        .maximum_temperature_c = 850.0f,
        .data = {.cvd = {
            .a = 3.9083e-3f,
            .b = -5.775e-7f,
            .c = -4.183e-12f,
            .c_is_present = 1,
        }},
    };
    const double nominal_r0_values[] = {100.0, 500.0, 1000.0};
    double maximum_forward_error = 0.0;
    double maximum_inverse_error = 0.0;
    double maximum_r0_representation_effect = 0.0;
    unsigned long long sample_count = 0;
    size_t nominal_index;

    for (
        nominal_index = 0;
        nominal_index < sizeof(nominal_r0_values) / sizeof(nominal_r0_values[0]);
        nominal_index += 1
    ) {
        const double nominal_r0 = nominal_r0_values[nominal_index];
        int r0_index;

        for (r0_index = 0; r0_index <= R0_GRID_INTERVALS; r0_index += 1) {
            const double fraction =
                0.95 + 0.10 * (double)r0_index / (double)R0_GRID_INTERVALS;
            const double reference_resistance_ohms = nominal_r0 * fraction;
            int temperature_index;

            for (
                temperature_index = 0;
                temperature_index <= TEMPERATURE_GRID_INTERVALS;
                temperature_index += 1
            ) {
                const double temperature_c =
                    -200.0 + 0.25 * (double)temperature_index;
                if (!evaluate_case(
                        &characteristic,
                        reference_resistance_ohms,
                        temperature_c,
                        &maximum_forward_error,
                        &maximum_inverse_error,
                        &maximum_r0_representation_effect
                    )) {
                    return 2;
                }
                sample_count += 1;
            }
        }
    }

    for (int random_index = 0; random_index < RANDOM_SAMPLE_COUNT; random_index += 1) {
        const size_t nominal_index_random = next_random() % 3U;
        const double nominal_r0 = nominal_r0_values[nominal_index_random];
        const double reference_resistance_ohms =
            nominal_r0 * (0.95 + 0.10 * unit_random());
        const double temperature_c = -200.0 + 1050.0 * unit_random();

        if (!evaluate_case(
                &characteristic,
                reference_resistance_ohms,
                temperature_c,
                &maximum_forward_error,
                &maximum_inverse_error,
                &maximum_r0_representation_effect
            )) {
            return 3;
        }
        sample_count += 1;
    }

    printf("sample_count=%llu\n", sample_count);
    printf("maximum_forward_error_ohm=%.17g\n", maximum_forward_error);
    printf("maximum_inverse_error_c=%.17g\n", maximum_inverse_error);
    printf(
        "maximum_r0_representation_effect_ohm=%.17g\n",
        maximum_r0_representation_effect
    );
    return 0;
}
