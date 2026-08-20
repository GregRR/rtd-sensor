---
title: Custom & calibrated models
description: Model characterized, calibrated, polynomial, piecewise, and tabulated RTDs with rtd-sensor and save supported definitions portably.
---

# Custom & calibrated models

Built-in models represent verified nominal RTD characteristics. Real projects
often need something more specific: an individually characterized reference
resistance, coefficients from a calibration certificate, a manufacturer
polynomial, a published table, or a model fitted from measured calibration
points.

`rtd-sensor` provides several model families so you can represent the source you
actually have instead of forcing every RTD into one mathematical form.

- [Characterized IEC 60751 models](characterized-iec60751.md)
- [Callendar–Van Dusen models](callendar-van-dusen.md)
- [Polynomial models](polynomial.md)
- [Piecewise polynomial models](piecewise-polynomial.md)
- [Tabulated models](tabulated.md)
- [Calibration fitting](calibration-fitting.md)
- [Portable model definitions](portable-definitions.md)

## Preserve the evidence behind the model

A model answers the numerical question “what resistance corresponds to this
temperature?” Evidence answers a different question: “why should we trust this
model for this device and range?”

For that reason, fitting results keep the fitted model separate from fit evidence,
and configurable models provide provenance fields such as `coefficient_source`
or `table_source` where appropriate.
