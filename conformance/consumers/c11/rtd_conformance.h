/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

#ifndef RTD_CONFORMANCE_H
#define RTD_CONFORMANCE_H

#include <stddef.h>

typedef enum {
    RTD_CONFORMANCE_OK = 0,
    RTD_CONFORMANCE_OUT_OF_RANGE_LOW,
    RTD_CONFORMANCE_OUT_OF_RANGE_HIGH,
    RTD_CONFORMANCE_INVALID_INPUT,
    RTD_CONFORMANCE_INVALID_MODEL,
    RTD_CONFORMANCE_CALCULATION_FAILURE
} rtd_conformance_status;

typedef enum {
    RTD_CURVE_CALLENDAR_VAN_DUSEN = 0,
    RTD_CURVE_POLYNOMIAL,
    RTD_CURVE_PIECEWISE_POLYNOMIAL
} rtd_curve_kind;

typedef struct {
    double minimum_temperature_c;
    double maximum_temperature_c;
    double temperature_origin_c;
    const double *coefficients;
    size_t coefficient_count;
    double continuity_adjustment;
} rtd_piecewise_segment;

typedef struct {
    const double *coefficients;
    size_t coefficient_count;
} rtd_polynomial_characteristic;

typedef struct {
    const rtd_piecewise_segment *segments;
    size_t segment_count;
    double maximum_continuity_adjustment_ratio;
} rtd_piecewise_characteristic;

typedef struct {
    double a;
    double b;
    double c;
    int c_is_present;
} rtd_cvd_characteristic;

typedef struct {
    const char *characteristic_id;
    rtd_curve_kind curve_kind;
    double reference_temperature_c;
    double minimum_temperature_c;
    double maximum_temperature_c;
    union {
        rtd_cvd_characteristic cvd;
        rtd_polynomial_characteristic polynomial;
        rtd_piecewise_characteristic piecewise;
    } data;
} rtd_characteristic;

typedef struct {
    const char *model_id;
    const rtd_characteristic *characteristic;
    double reference_resistance_ohms;
    double minimum_temperature_c;
    double maximum_temperature_c;
} rtd_model;

typedef struct {
    rtd_conformance_status status;
    double value;
} rtd_conformance_result;

rtd_conformance_status rtd_validate_model(const rtd_model *model);

rtd_conformance_result rtd_temperature_to_resistance(
    const rtd_model *model,
    double temperature_c
);

rtd_conformance_result rtd_resistance_to_temperature(
    const rtd_model *model,
    double resistance_ohms
);

const char *rtd_conformance_status_name(rtd_conformance_status status);

#endif
