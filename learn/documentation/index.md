---
title: Full rtd-sensor Documentation
description: Complete user documentation for rtd-sensor, including conversion, calibrated models, self-heating, measurement composition, tolerance, uncertainty, simulation, and integration.
---

# Full rtd-sensor Documentation

This is the complete user guide for `rtd-sensor`. It is written to be useful to
professional and scientific users without assuming that every reader already
knows RTD terminology, metrology vocabulary, or the package's internal design.

`rtd-sensor` is a platform-independent Python library for resistance temperature
detector (RTD) conversion and modeling. It works at the **RTD model boundary**:
give it resistance in ohms and it can calculate temperature in degrees Celsius,
or give it temperature and it can calculate the corresponding model resistance.

The package also provides calibration fitting, custom models, portable model
definitions, self-heating and zero-power analysis, tolerance calculations,
uncertainty tools, simulation, batch conversion, model discovery, and cross-language
conformance support.

## Choose a section

### Using rtd-sensor

Start with everyday conversion, ranges, errors, sensitivity, batch conversion,
and discovering the built-in models.

[Using rtd-sensor](using/index.md)

### Built-in RTDs

Detailed documentation for Pt100, Pt500, Pt1000, Ni1000 6180, Ni1000 TK5000,
and Ni120 6720.

[Built-in RTDs](built-in-rtds/index.md)

### Custom & calibrated models

Use a characterized reference resistance, custom Callendar–Van Dusen
coefficients, polynomial models, piecewise models, tabulated data, calibration
fitting, and portable definitions.

[Custom & calibrated models](custom-models/index.md)

### Measurement & uncertainty

Understand the acquisition boundary, compose resistance readers with models,
analyze self-heating and zero-power resistance, calculate IEC 60751 tolerance limits,
and build inspectable uncertainty budgets.

[Measurement & uncertainty](measurement-uncertainty/index.md)

### Simulation & testing

Generate deterministic or noisy RTD measurements for application tests,
demonstrations, and hardware-independent development.

[Simulation & testing](simulation-testing/index.md)

### Integration

Use the structural RTD model interface, plug in third-party models, handle
errors deliberately, and keep hardware acquisition separate from RTD science.

[Integration](integration/index.md)

## Package scope at a glance

Verified built-in models currently include:

| Built-in | Characteristic | R0 at 0 °C | Supported characteristic range |
| --- | --- | ---: | ---: |
| Pt100 | IEC 60751 PT-385 platinum | 100 Ω | -200 °C to 850 °C |
| Pt500 | IEC 60751 PT-385 platinum | 500 Ω | -200 °C to 850 °C |
| Pt1000 | IEC 60751 PT-385 platinum | 1000 Ω | -200 °C to 850 °C |
| Ni1000 6180 | former DIN 43760 / Nickel ND | 1000 Ω | -60 °C to 250 °C |
| Ni1000 TK5000 | Nickel NL 5000 ppm/K | 1000 Ω | -60 °C to 250 °C |
| Ni120 6720 | North American / Minco NA | 120 Ω | -80 °C to 260 °C |

Hardware-specific concerns such as ADC readings, GPIO, SPI, I²C, excitation
circuits, and lead-wire compensation remain outside the package. See
[The hardware/acquisition boundary](measurement-uncertainty/acquisition-boundary.md).

## Need a faster lookup?

If you already know what feature or function you need, use the
[API Reference](../api/index.md).
