---
title: Choosing an RTD model
description: Decide whether to use a built-in RTD, characterized IEC model, custom CVD, polynomial, piecewise, tabulated, or fitted model in rtd-sensor.
---

# Choosing the right model

The best model is the one that represents the **documented characteristic or
calibration evidence you actually have**. Do not choose a model family merely
because its class name sounds familiar.

## Use a built-in model when

Use a built-in such as `pt100`, `pt500`, `pt1000`, `ni1000`,
`ni1000_tk5000`, or `ni120` when the physical sensor is intended to follow that
verified nominal characteristic and you do not need an individually
characterized model.

See [Built-in RTDs](../built-in-rtds/index.md).

## Use `IEC60751RTDModel` when

You have an IEC 60751 PT-385 platinum sensor with a characterized resistance at
0 °C, often written `R0`, but still want to use the standard PT-385 curve shape.

Example: a calibration record says the probe's `R0` is 100.017 Ω.

[Characterized IEC 60751 models](../custom-models/characterized-iec60751.md)

## Use `CallendarVanDusenRTDModel` when

A calibration certificate, manufacturer, or technical source gives you an
explicit Callendar–Van Dusen coefficient set and valid temperature range.

[Callendar–Van Dusen models](../custom-models/callendar-van-dusen.md)

## Use `PolynomialRTDModel` when

The authoritative source publishes one polynomial over the complete declared
range, or when you intentionally fit a global polynomial from calibration data.

[Polynomial models](../custom-models/polynomial.md)

## Use `PiecewisePolynomialRTDModel` when

The source publishes different polynomial coefficients over different
temperature intervals. Keeping those intervals preserves the source model more
faithfully than forcing everything into one global polynomial.

[Piecewise polynomial models](../custom-models/piecewise-polynomial.md)

## Use `TabulatedRTDModel` when

The authoritative source is a resistance-temperature table and linear
interpolation between the published points is the behavior you want to retain.

[Tabulated models](../custom-models/tabulated.md)

## Use calibration fitting when

You have your own measured `(temperature, resistance)` observations and want to
fit a characterized IEC `R0`, selected custom CVD parameters, or a validated
polynomial model while retaining residuals, covariance, fit range, and
conditioning/identifiability diagnostics.

[Calibration fitting](../custom-models/calibration-fitting.md)

## A practical decision rule

Prefer the representation closest to the authoritative source:

```text
verified nominal characteristic → built-in model
standard PT-385 + characterized R0 → IEC60751RTDModel
published CVD coefficients → CallendarVanDusenRTDModel
one published polynomial → PolynomialRTDModel
published interval polynomials → PiecewisePolynomialRTDModel
published R/T table → TabulatedRTDModel
measured calibration observations → fit_iec60751_r0(),
                                    fit_callendar_van_dusen(),
                                    or fit_polynomial()
```

## Do not identify an RTD by resistance alone

A nominal 1000 Ω sensor could be Pt1000, Ni1000 6180, Ni1000 TK5000, or another
characteristic entirely. The resistance at 0 °C is only one part of model
identity.
