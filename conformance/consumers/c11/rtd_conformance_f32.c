/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

#include "rtd_conformance_f32.h"

#include <float.h>
#include <math.h>
#include <stddef.h>

#define RTD_BISECTION_ITERATIONS 64
#define RTD_ENDPOINT_GUARD_ULPS 4

static rtd_conformance_result result(rtd_conformance_status status, float value) {
    rtd_conformance_result output = {status, value};
    return output;
}

static float polynomial_value(
    const float *coefficients,
    size_t coefficient_count,
    float x
) {
    size_t index = coefficient_count;
    float value = 0.0f;

    while (index > 0) {
        index -= 1;
        value = value * x + coefficients[index];
    }
    return value;
}

static int model_is_valid(const rtd_model *model) {
    if (model == NULL || model->characteristic == NULL) {
        return 0;
    }
    if (model->model_id == NULL || model->characteristic->characteristic_id == NULL) {
        return 0;
    }
    if (!isfinite(model->reference_resistance_ohms) ||
        model->reference_resistance_ohms <= 0.0f) {
        return 0;
    }
    if (!isfinite(model->minimum_temperature_c) ||
        !isfinite(model->maximum_temperature_c) ||
        model->minimum_temperature_c >= model->maximum_temperature_c) {
        return 0;
    }
    if (model->minimum_temperature_c < model->characteristic->minimum_temperature_c ||
        model->maximum_temperature_c > model->characteristic->maximum_temperature_c) {
        return 0;
    }
    return 1;
}

static int piecewise_segment_index(
    const rtd_piecewise_characteristic *piecewise,
    float temperature_c,
    size_t *index_out
) {
    size_t index;

    if (piecewise->segments == NULL || piecewise->segment_count == 0 ||
        index_out == NULL) {
        return 0;
    }

    for (index = 0; index < piecewise->segment_count; index += 1) {
        const rtd_piecewise_segment *segment = &piecewise->segments[index];
        const int is_last = index + 1 == piecewise->segment_count;
        if (segment->minimum_temperature_c <= temperature_c &&
            (temperature_c < segment->maximum_temperature_c ||
             (is_last && temperature_c <= segment->maximum_temperature_c))) {
            *index_out = index;
            return 1;
        }
    }
    return 0;
}

static int characteristic_ratio(
    const rtd_characteristic *characteristic,
    float temperature_c,
    float *ratio_out
) {
    float ratio;

    if (characteristic == NULL || ratio_out == NULL || !isfinite(temperature_c)) {
        return 0;
    }
    if (temperature_c < characteristic->minimum_temperature_c ||
        temperature_c > characteristic->maximum_temperature_c) {
        return 0;
    }

    switch (characteristic->curve_kind) {
        case RTD_CURVE_CALLENDAR_VAN_DUSEN: {
            const rtd_cvd_characteristic *cvd = &characteristic->data.cvd;
            ratio = 1.0f + cvd->a * temperature_c +
                    cvd->b * temperature_c * temperature_c;
            if (temperature_c < 0.0f) {
                ratio += cvd->c * (temperature_c - 100.0f) * temperature_c *
                         temperature_c * temperature_c;
            }
            break;
        }

        case RTD_CURVE_POLYNOMIAL: {
            const rtd_polynomial_characteristic *polynomial =
                &characteristic->data.polynomial;
            const float x = temperature_c - characteristic->reference_temperature_c;
            if (polynomial->coefficients == NULL || polynomial->coefficient_count == 0) {
                return 0;
            }
            ratio = 1.0f +
                    x * polynomial_value(
                            polynomial->coefficients,
                            polynomial->coefficient_count,
                            x
                        );
            break;
        }

        case RTD_CURVE_PIECEWISE_POLYNOMIAL: {
            const rtd_piecewise_characteristic *piecewise =
                &characteristic->data.piecewise;
            size_t index;
            const rtd_piecewise_segment *segment;
            const float *coefficients;
            float x;

            if (temperature_c == characteristic->reference_temperature_c) {
                *ratio_out = 1.0f;
                return 1;
            }
            if (!piecewise_segment_index(piecewise, temperature_c, &index)) {
                return 0;
            }
            segment = &piecewise->segments[index];
            coefficients = segment->coefficients;
            if (coefficients == NULL || segment->coefficient_count == 0) {
                return 0;
            }
            x = temperature_c - segment->temperature_origin_c;
            ratio = polynomial_value(coefficients, segment->coefficient_count, x) +
                    segment->continuity_adjustment;
            break;
        }

        default:
            return 0;
    }

    if (!isfinite(ratio) || ratio <= 0.0f) {
        return 0;
    }
    *ratio_out = ratio;
    return 1;
}

static int model_resistance_unchecked(
    const rtd_model *model,
    float temperature_c,
    float *resistance_out
) {
    float ratio;
    float resistance;

    if (!characteristic_ratio(model->characteristic, temperature_c, &ratio)) {
        return 0;
    }
    resistance = model->reference_resistance_ohms * ratio;
    if (!isfinite(resistance) || resistance <= 0.0f) {
        return 0;
    }
    *resistance_out = resistance;
    return 1;
}

static float ulps_toward(float value, float direction, unsigned int count) {
    unsigned int index;

    for (index = 0; index < count; index += 1) {
        value = nextafterf(value, direction);
    }
    return value;
}

rtd_conformance_result rtd_temperature_to_resistance(
    const rtd_model *model,
    float temperature_c
) {
    float resistance;

    if (!model_is_valid(model)) {
        return result(RTD_CONFORMANCE_INVALID_MODEL, NAN);
    }
    if (!isfinite(temperature_c)) {
        return result(RTD_CONFORMANCE_INVALID_INPUT, NAN);
    }
    if (temperature_c < model->minimum_temperature_c) {
        return result(RTD_CONFORMANCE_OUT_OF_RANGE_LOW, NAN);
    }
    if (temperature_c > model->maximum_temperature_c) {
        return result(RTD_CONFORMANCE_OUT_OF_RANGE_HIGH, NAN);
    }
    if (!model_resistance_unchecked(model, temperature_c, &resistance)) {
        return result(RTD_CONFORMANCE_CALCULATION_FAILURE, NAN);
    }
    return result(RTD_CONFORMANCE_OK, resistance);
}

rtd_conformance_result rtd_resistance_to_temperature(
    const rtd_model *model,
    float resistance_ohms
) {
    float minimum_resistance;
    float maximum_resistance;
    float lower_c;
    float upper_c;
    size_t iteration;

    if (!model_is_valid(model)) {
        return result(RTD_CONFORMANCE_INVALID_MODEL, NAN);
    }
    if (!isfinite(resistance_ohms) || resistance_ohms <= 0.0f) {
        return result(RTD_CONFORMANCE_INVALID_INPUT, NAN);
    }
    if (!model_resistance_unchecked(
            model,
            model->minimum_temperature_c,
            &minimum_resistance
        ) ||
        !model_resistance_unchecked(
            model,
            model->maximum_temperature_c,
            &maximum_resistance
        )) {
        return result(RTD_CONFORMANCE_CALCULATION_FAILURE, NAN);
    }

    /* A binary64 endpoint vector can round one or two float ULPs beyond the
     * endpoint resistance produced by binary32 evaluation. The guard preserves
     * endpoint success semantics without changing the physical model range.
     * The published 0.01 ohm out-of-range anchors remain well outside it.
     */
    if (resistance_ohms < minimum_resistance) {
        if (resistance_ohms >=
            ulps_toward(minimum_resistance, -INFINITY, RTD_ENDPOINT_GUARD_ULPS)) {
            return result(RTD_CONFORMANCE_OK, model->minimum_temperature_c);
        }
        return result(RTD_CONFORMANCE_OUT_OF_RANGE_LOW, NAN);
    }
    if (resistance_ohms > maximum_resistance) {
        if (resistance_ohms <=
            ulps_toward(maximum_resistance, INFINITY, RTD_ENDPOINT_GUARD_ULPS)) {
            return result(RTD_CONFORMANCE_OK, model->maximum_temperature_c);
        }
        return result(RTD_CONFORMANCE_OUT_OF_RANGE_HIGH, NAN);
    }
    if (resistance_ohms == minimum_resistance) {
        return result(RTD_CONFORMANCE_OK, model->minimum_temperature_c);
    }
    if (resistance_ohms == maximum_resistance) {
        return result(RTD_CONFORMANCE_OK, model->maximum_temperature_c);
    }

    lower_c = model->minimum_temperature_c;
    upper_c = model->maximum_temperature_c;
    for (iteration = 0; iteration < RTD_BISECTION_ITERATIONS; iteration += 1) {
        const float midpoint_c = (lower_c + upper_c) * 0.5f;
        float midpoint_resistance;

        if (midpoint_c == lower_c || midpoint_c == upper_c) {
            break;
        }
        if (!model_resistance_unchecked(model, midpoint_c, &midpoint_resistance)) {
            return result(RTD_CONFORMANCE_CALCULATION_FAILURE, NAN);
        }
        if (midpoint_resistance < resistance_ohms) {
            lower_c = midpoint_c;
        } else {
            upper_c = midpoint_c;
        }
    }

    return result(RTD_CONFORMANCE_OK, (lower_c + upper_c) * 0.5f);
}

const char *rtd_conformance_status_name(rtd_conformance_status status) {
    switch (status) {
        case RTD_CONFORMANCE_OK:
            return "ok";
        case RTD_CONFORMANCE_OUT_OF_RANGE_LOW:
            return "out_of_range_low";
        case RTD_CONFORMANCE_OUT_OF_RANGE_HIGH:
            return "out_of_range_high";
        case RTD_CONFORMANCE_INVALID_INPUT:
            return "invalid_input";
        case RTD_CONFORMANCE_INVALID_MODEL:
            return "invalid_model";
        case RTD_CONFORMANCE_CALCULATION_FAILURE:
            return "calculation_failure";
        default:
            return "unknown_status";
    }
}
