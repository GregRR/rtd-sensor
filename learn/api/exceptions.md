---
title: exceptions API
description: Quick API reference for rtd-sensor public exceptions, inheritance, and introduction versions.
---

# `rtd_sensor.exceptions`

The public exception taxonomy began in **rtd-sensor 0.5.0** and was extended in
0.6.0 for fitting and portable-model failures.

```text
RTDError(Exception)
├── RTDOutOfRangeError(ValueError)
├── InvalidPortableModelDefinitionError(ValueError)
├── InvalidRTDModelError(ValueError)
├── RTDFitError(ValueError)
├── RTDModelSelectionError(ValueError)
└── UnknownRTDModelError(KeyError)
```

| Exception | Introduced in |
| --- | --- |
| `RTDError` | rtd-sensor 0.5.0 |
| `RTDOutOfRangeError` | rtd-sensor 0.5.0 |
| `UnknownRTDModelError` | rtd-sensor 0.5.0 |
| `InvalidRTDModelError` | rtd-sensor 0.5.0 |
| `RTDModelSelectionError` | rtd-sensor 0.5.0 |
| `InvalidPortableModelDefinitionError` | rtd-sensor 0.6.0 |
| `RTDFitError` | rtd-sensor 0.6.0 |

Use `RTDError` to catch package-owned RTD domain failures broadly while leaving
unrelated acquisition/hardware exceptions untouched.

See [Error handling](../documentation/integration/error-handling.md).
