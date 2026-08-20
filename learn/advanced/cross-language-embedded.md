---
title: Cross-language & embedded use
description: Use rtd-sensor's model identities, portable definitions, conformance artifacts, and subset claims cleanly from C, C++, MCU, or other non-Python implementations.
---

# Cross-language & embedded use

`rtd-sensor` is the Python reference implementation and conformance authority,
but an embedded or non-Python system does not need to reproduce the whole
package.

A clean downstream design is:

```text
rtd-sensor contract / portable model definition
                ↓
       independent implementation
                ↓
        application or MCU
```

## Choose an explicit subset

A minimal MCU might implement only one model and one direction:

```text
contract version: 1
model: pt100
operation: resistance_to_temperature
numerical profile: binary32_compatible
```

Claiming that subset does not imply support for fitting, tolerance, uncertainty,
portable parsing at runtime, or every built-in model.

## Reuse stable model identity

If host software and firmware both mean the built-in Pt100, they should reuse
canonical identity such as `pt100` rather than inventing nearly equivalent names.

Keep **physical probe identity** separate. Serial number, channel, location, and
asset history belong to the application.

## Portable definitions for calibrated/custom models

For supported configurable model families, a host can serialize the numerical
model with [portable definitions](../documentation/custom-models/portable-definitions.md).
A non-Python consumer can reconstruct that scientific definition according to
the published format without rerunning the calibration fit.

## Runtime JSON is optional

JSON is useful for schemas, build tooling, release artifacts, and CI. Firmware
can instead consume generated/static values produced at build time. The contract
does not require dynamic allocation or a JSON parser on the MCU.

## Keep hardware faults separate

RTD conversion statuses and model range behavior should not be merged with
hardware states such as open circuit, ADC fault, reference-resistor fault, SPI
failure, or stale sample. A higher-level protocol can carry both.

## Full implementation guide

The canonical engineering guide is
[`docs/CROSS_LANGUAGE_IMPLEMENTATIONS.md`](https://github.com/GregRR/rtd-sensor/blob/main/docs/CROSS_LANGUAGE_IMPLEMENTATIONS.md).
