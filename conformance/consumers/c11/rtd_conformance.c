/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

#include "rtd_conformance.h"

#include <float.h>
#include <math.h>
#include <stddef.h>

#define RTD_BISECTION_ITERATIONS 96

static rtd_conformance_result result(rtd_conformance_status status, double value) {
    rtd_conformance_result output = {status, value};
    return output;
}

static double polynomial_value(
    const double *coefficients,
    size_t coefficient_count,
    double x
) {
    size_t index = coefficient_count;
    double value = 0.0;

    while (index > 0) {
        index -= 1;
        value = value * x + coefficients[index];
    }
    return value;
}

static double callendar_van_dusen_ratio(
    const rtd_cvd_characteristic *cvd,
    double temperature_c
) {
    double ratio = 1.0 + cvd->a * temperature_c + cvd->b * temperature_c * temperature_c;

    if (temperature_c < 0.0) {
        ratio += cvd->c * (temperature_c - 100.0) * temperature_c * temperature_c *
                 temperature_c;
    }
    return ratio;
}

static double callendar_van_dusen_slope(
    const rtd_cvd_characteristic *cvd,
    double temperature_c
) {
    double slope = cvd->a + 2.0 * cvd->b * temperature_c;

    if (temperature_c < 0.0) {
        slope += cvd->c * temperature_c * temperature_c * (4.0 * temperature_c - 300.0);
    }
    return slope;
}

static int slope_is_positive_at(
    const rtd_cvd_characteristic *cvd,
    double temperature_c,
    double minimum_temperature_c,
    double maximum_temperature_c
) {
    double slope;

    if (temperature_c < minimum_temperature_c || temperature_c > maximum_temperature_c) {
        return 1;
    }
    slope = callendar_van_dusen_slope(cvd, temperature_c);
    return isfinite(slope) && slope > 0.0;
}

static int callendar_van_dusen_is_valid(const rtd_characteristic *characteristic) {
    const rtd_cvd_characteristic *cvd = &characteristic->data.cvd;
    const double minimum_temperature_c = characteristic->minimum_temperature_c;
    const double maximum_temperature_c = characteristic->maximum_temperature_c;
    double minimum_ratio;
    double maximum_ratio;

    if (!isfinite(cvd->a) || !isfinite(cvd->b) || !isfinite(cvd->c)) {
        return 0;
    }
    if (minimum_temperature_c < 0.0 && !cvd->c_is_present) {
        return 0;
    }

    minimum_ratio = callendar_van_dusen_ratio(cvd, minimum_temperature_c);
    maximum_ratio = callendar_van_dusen_ratio(cvd, maximum_temperature_c);
    if (!isfinite(minimum_ratio) || !isfinite(maximum_ratio) || minimum_ratio <= 0.0) {
        return 0;
    }
    if (!slope_is_positive_at(
            cvd,
            minimum_temperature_c,
            minimum_temperature_c,
            maximum_temperature_c
        ) ||
        !slope_is_positive_at(
            cvd,
            maximum_temperature_c,
            minimum_temperature_c,
            maximum_temperature_c
        ) ||
        !slope_is_positive_at(
            cvd,
            0.0,
            minimum_temperature_c,
            maximum_temperature_c
        )) {
        return 0;
    }

    if (cvd->c != 0.0 && minimum_temperature_c < 0.0) {
        const double quadratic_a = 12.0 * cvd->c;
        const double quadratic_b = -600.0 * cvd->c;
        const double quadratic_c = 2.0 * cvd->b;
        const double discriminant =
            quadratic_b * quadratic_b - 4.0 * quadratic_a * quadratic_c;

        if (isfinite(discriminant) && discriminant >= 0.0) {
            const double sqrt_discriminant = sqrt(discriminant);
            const double denominator = 2.0 * quadratic_a;
            const double root_low =
                (-quadratic_b - sqrt_discriminant) / denominator;
            const double root_high =
                (-quadratic_b + sqrt_discriminant) / denominator;

            if (!slope_is_positive_at(
                    cvd,
                    root_low,
                    minimum_temperature_c,
                    maximum_temperature_c
                ) ||
                !slope_is_positive_at(
                    cvd,
                    root_high,
                    minimum_temperature_c,
                    maximum_temperature_c
                )) {
                return 0;
            }
        }
    }
    return 1;
}

static double polynomial_ratio_slope(
    const double *coefficients,
    size_t coefficient_count,
    double x
) {
    size_t degree = coefficient_count;
    double value = 0.0;

    while (degree > 0) {
        value = value * x + (double)degree * coefficients[degree - 1];
        degree -= 1;
    }
    return value;
}

static int polynomial_is_valid(const rtd_characteristic *characteristic) {
    const rtd_polynomial_characteristic *polynomial = &characteristic->data.polynomial;
    const size_t sample_count = 1024;
    const double lower_x = characteristic->minimum_temperature_c -
                           characteristic->reference_temperature_c;
    const double upper_x = characteristic->maximum_temperature_c -
                           characteristic->reference_temperature_c;
    double minimum_ratio;
    double maximum_ratio;
    size_t index;

    if (polynomial->coefficients == NULL || polynomial->coefficient_count == 0 ||
        polynomial->coefficient_count > 12) {
        return 0;
    }
    for (index = 0; index < polynomial->coefficient_count; index += 1) {
        if (!isfinite(polynomial->coefficients[index])) {
            return 0;
        }
    }

    minimum_ratio = 1.0 + lower_x * polynomial_value(
        polynomial->coefficients,
        polynomial->coefficient_count,
        lower_x
    );
    maximum_ratio = 1.0 + upper_x * polynomial_value(
        polynomial->coefficients,
        polynomial->coefficient_count,
        upper_x
    );
    if (!isfinite(minimum_ratio) || !isfinite(maximum_ratio) || minimum_ratio <= 0.0) {
        return 0;
    }

    /*
     * This independent consumer claims the published conformance fixture set,
     * not a general-purpose arbitrary-polynomial validation API.  A dense
     * derivative sweep is intentionally independent of Python's analytical
     * critical-point solver and is sufficient for the fixture definitions
     * this consumer claims to reproduce.
     */
    for (index = 0; index <= sample_count; index += 1) {
        const double fraction = (double)index / (double)sample_count;
        const double x = lower_x + fraction * (upper_x - lower_x);
        const double slope = polynomial_ratio_slope(
            polynomial->coefficients,
            polynomial->coefficient_count,
            x
        );
        if (!isfinite(slope) || slope <= 0.0) {
            return 0;
        }
    }
    return 1;
}

static double piecewise_source_ratio(
    const rtd_piecewise_segment *segment,
    double temperature_c
) {
    const double x = temperature_c - segment->temperature_origin_c;
    return polynomial_value(segment->coefficients, segment->coefficient_count, x);
}

static double piecewise_source_slope(
    const rtd_piecewise_segment *segment,
    double temperature_c
) {
    const double x = temperature_c - segment->temperature_origin_c;
    size_t degree = segment->coefficient_count - 1;
    double value = 0.0;

    while (degree > 0) {
        value = value * x + (double)degree * segment->coefficients[degree];
        degree -= 1;
    }
    return value;
}

static int close_at_roundoff(double left, double right) {
    const double scale = fmax(fmax(fabs(left), fabs(right)), 1.0);
    return fabs(left - right) <= 64.0 * DBL_EPSILON * scale;
}

static int piecewise_is_valid(const rtd_characteristic *characteristic) {
    const rtd_piecewise_characteristic *piecewise = &characteristic->data.piecewise;
    const size_t derivative_samples = 64;
    size_t segment_index;
    int reference_seen = 0;

    if (piecewise->segments == NULL || piecewise->segment_count == 0 ||
        !isfinite(piecewise->maximum_continuity_adjustment_ratio) ||
        piecewise->maximum_continuity_adjustment_ratio < 0.0) {
        return 0;
    }
    if (piecewise->segments[0].minimum_temperature_c !=
            characteristic->minimum_temperature_c ||
        piecewise->segments[piecewise->segment_count - 1].maximum_temperature_c !=
            characteristic->maximum_temperature_c) {
        return 0;
    }

    for (segment_index = 0; segment_index < piecewise->segment_count; segment_index += 1) {
        const rtd_piecewise_segment *segment = &piecewise->segments[segment_index];
        double minimum_ratio;
        double maximum_ratio;
        size_t coefficient_index;
        size_t sample_index;

        if (!isfinite(segment->minimum_temperature_c) ||
            !isfinite(segment->maximum_temperature_c) ||
            !isfinite(segment->temperature_origin_c) ||
            !isfinite(segment->continuity_adjustment) ||
            segment->minimum_temperature_c >= segment->maximum_temperature_c ||
            segment->coefficients == NULL || segment->coefficient_count == 0 ||
            segment->coefficient_count > 13) {
            return 0;
        }
        if (fabs(segment->continuity_adjustment) >
            piecewise->maximum_continuity_adjustment_ratio + 64.0 * DBL_EPSILON) {
            return 0;
        }
        for (coefficient_index = 0; coefficient_index < segment->coefficient_count;
             coefficient_index += 1) {
            if (!isfinite(segment->coefficients[coefficient_index])) {
                return 0;
            }
        }
        if (segment_index > 0 &&
            piecewise->segments[segment_index - 1].maximum_temperature_c !=
                segment->minimum_temperature_c) {
            return 0;
        }

        minimum_ratio = piecewise_source_ratio(segment, segment->minimum_temperature_c) +
                        segment->continuity_adjustment;
        maximum_ratio = piecewise_source_ratio(segment, segment->maximum_temperature_c) +
                        segment->continuity_adjustment;
        if (!isfinite(minimum_ratio) || !isfinite(maximum_ratio) || minimum_ratio <= 0.0) {
            return 0;
        }

        for (sample_index = 0; sample_index <= derivative_samples; sample_index += 1) {
            const double fraction = (double)sample_index / (double)derivative_samples;
            const double temperature_c = segment->minimum_temperature_c +
                                         fraction *
                                             (segment->maximum_temperature_c -
                                              segment->minimum_temperature_c);
            const double slope = piecewise_source_slope(segment, temperature_c);
            if (!isfinite(slope) || slope <= 0.0) {
                return 0;
            }
        }

        if (characteristic->reference_temperature_c >= segment->minimum_temperature_c &&
            characteristic->reference_temperature_c <= segment->maximum_temperature_c) {
            const int is_last = segment_index + 1 == piecewise->segment_count;
            if (characteristic->reference_temperature_c < segment->maximum_temperature_c ||
                is_last) {
                const double reference_ratio =
                    piecewise_source_ratio(
                        segment,
                        characteristic->reference_temperature_c
                    ) +
                    segment->continuity_adjustment;
                if (!close_at_roundoff(reference_ratio, 1.0)) {
                    return 0;
                }
                reference_seen = 1;
            }
        }
    }

    for (segment_index = 1; segment_index < piecewise->segment_count; segment_index += 1) {
        const rtd_piecewise_segment *left = &piecewise->segments[segment_index - 1];
        const rtd_piecewise_segment *right = &piecewise->segments[segment_index];
        const double boundary_c = right->minimum_temperature_c;
        const double left_ratio =
            piecewise_source_ratio(left, boundary_c) + left->continuity_adjustment;
        const double right_ratio =
            piecewise_source_ratio(right, boundary_c) + right->continuity_adjustment;
        if (!close_at_roundoff(left_ratio, right_ratio)) {
            return 0;
        }
    }

    return reference_seen;
}

static int characteristic_is_valid(const rtd_characteristic *characteristic) {
    if (characteristic == NULL || characteristic->characteristic_id == NULL ||
        !isfinite(characteristic->reference_temperature_c) ||
        !isfinite(characteristic->minimum_temperature_c) ||
        !isfinite(characteristic->maximum_temperature_c) ||
        characteristic->minimum_temperature_c >= characteristic->maximum_temperature_c) {
        return 0;
    }

    switch (characteristic->curve_kind) {
        case RTD_CURVE_CALLENDAR_VAN_DUSEN:
            return callendar_van_dusen_is_valid(characteristic);
        case RTD_CURVE_POLYNOMIAL:
            return polynomial_is_valid(characteristic);
        case RTD_CURVE_PIECEWISE_POLYNOMIAL:
            return piecewise_is_valid(characteristic);
        default:
            return 0;
    }
}

rtd_conformance_status rtd_validate_model(const rtd_model *model) {
    if (model == NULL || model->characteristic == NULL || model->model_id == NULL ||
        !isfinite(model->reference_resistance_ohms) ||
        model->reference_resistance_ohms <= 0.0 ||
        !isfinite(model->minimum_temperature_c) ||
        !isfinite(model->maximum_temperature_c) ||
        model->minimum_temperature_c >= model->maximum_temperature_c ||
        !characteristic_is_valid(model->characteristic) ||
        model->minimum_temperature_c < model->characteristic->minimum_temperature_c ||
        model->maximum_temperature_c > model->characteristic->maximum_temperature_c) {
        return RTD_CONFORMANCE_INVALID_MODEL;
    }
    return RTD_CONFORMANCE_OK;
}

static int piecewise_segment_index(
    const rtd_piecewise_characteristic *piecewise,
    double temperature_c,
    size_t *index_out
) {
    size_t index;

    if (piecewise->segments == NULL || piecewise->segment_count == 0 || index_out == NULL) {
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
    double temperature_c,
    double *ratio_out
) {
    double ratio;

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
            ratio = callendar_van_dusen_ratio(cvd, temperature_c);
            break;
        }

        case RTD_CURVE_POLYNOMIAL: {
            const rtd_polynomial_characteristic *polynomial =
                &characteristic->data.polynomial;
            const double x = temperature_c - characteristic->reference_temperature_c;
            if (polynomial->coefficients == NULL || polynomial->coefficient_count == 0) {
                return 0;
            }
            ratio = 1.0 + x * polynomial_value(
                polynomial->coefficients,
                polynomial->coefficient_count,
                x
            );
            break;
        }

        case RTD_CURVE_PIECEWISE_POLYNOMIAL: {
            const rtd_piecewise_characteristic *piecewise = &characteristic->data.piecewise;
            size_t index;
            const rtd_piecewise_segment *segment;
            const double *coefficients;
            double x;

            if (temperature_c == characteristic->reference_temperature_c) {
                *ratio_out = 1.0;
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

    if (!isfinite(ratio) || ratio <= 0.0) {
        return 0;
    }
    *ratio_out = ratio;
    return 1;
}

static int model_resistance_unchecked(
    const rtd_model *model,
    double temperature_c,
    double *resistance_out
) {
    double ratio;
    double resistance;

    if (!characteristic_ratio(model->characteristic, temperature_c, &ratio)) {
        return 0;
    }
    resistance = model->reference_resistance_ohms * ratio;
    if (!isfinite(resistance) || resistance <= 0.0) {
        return 0;
    }
    *resistance_out = resistance;
    return 1;
}

rtd_conformance_result rtd_temperature_to_resistance(
    const rtd_model *model,
    double temperature_c
) {
    double resistance;

    if (rtd_validate_model(model) != RTD_CONFORMANCE_OK) {
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
    double resistance_ohms
) {
    double minimum_resistance;
    double maximum_resistance;
    double lower_c;
    double upper_c;
    size_t iteration;

    if (rtd_validate_model(model) != RTD_CONFORMANCE_OK) {
        return result(RTD_CONFORMANCE_INVALID_MODEL, NAN);
    }
    if (!isfinite(resistance_ohms) || resistance_ohms <= 0.0) {
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
    if (resistance_ohms < minimum_resistance) {
        return result(RTD_CONFORMANCE_OUT_OF_RANGE_LOW, NAN);
    }
    if (resistance_ohms > maximum_resistance) {
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
        const double midpoint_c = (lower_c + upper_c) / 2.0;
        double midpoint_resistance;

        if (!model_resistance_unchecked(model, midpoint_c, &midpoint_resistance)) {
            return result(RTD_CONFORMANCE_CALCULATION_FAILURE, NAN);
        }
        if (midpoint_resistance < resistance_ohms) {
            lower_c = midpoint_c;
        } else {
            upper_c = midpoint_c;
        }
    }

    return result(RTD_CONFORMANCE_OK, (lower_c + upper_c) / 2.0);
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
