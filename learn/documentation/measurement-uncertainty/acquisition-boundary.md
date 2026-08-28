---
title: Hardware and acquisition boundary
description: Understand what rtd-sensor expects from RTD acquisition hardware and which ADC, wiring, lead compensation, and converter responsibilities remain outside the package.
---

# The hardware/acquisition boundary

`rtd-sensor` starts once the best available estimate of the RTD sensing element's
resistance in ohms is available. Sometimes a separate acquisition layer must produce
that estimate; sometimes an instrument or RTD interface already provides it.

```text
physical RTD
    ↓
resistance-measurement source
    ├── raw converter / ADC / electrical interface
    │       ↓
    │   acquisition handling and corrections
    │       ↓
    │   resistance in ohms
    │
    └── DMM / bridge / DAQ / RTD interface with resistance output
            ↓
        resistance in ohms
            ↓
        rtd-sensor model
            ↓
        temperature in °C
```

## What belongs in the acquisition layer

Depending on the hardware, that may include:

- ADC or converter register handling;
- SPI, I²C, GPIO, or another bus;
- excitation-current behavior;
- reference-resistor calculations;
- two-, three-, or four-wire topology handling;
- lead-wire compensation;
- converter fault detection; and
- hardware-specific calibration.

For example, a MAX31865 integration should first use the converter's information
and circuit configuration to obtain an RTD resistance estimate. That resistance
can then be passed to `rtd-sensor`. If a laboratory DMM, bridge, DAQ, or RTD
interface already provides the desired element-resistance estimate in ohms, no
additional acquisition layer is required before passing it to `rtd-sensor`.

## What rtd-sensor owns

`rtd-sensor` owns the mathematical RTD model layer:

- resistance ↔ temperature conversion;
- RTD model range and validation;
- model sensitivity;
- custom/calibrated model behavior;
- RTD-specific uncertainty propagation;
- model identity and conformance semantics.

## Why keep the boundary clean?

A Pt100 model should behave the same whether the resistance came from an
industrial bridge, a MAX31865, a laboratory DMM, or a simulator. Keeping
hardware out of the model layer makes that possible and allows independent
testing of each responsibility.

## Hardware faults versus RTD model errors

An open circuit, SPI failure, stale ADC sample, or converter fault is an
**acquisition problem**. A resistance outside the model's valid range is an
**RTD model problem**. Applications may report both, but the package does not
collapse them into one exception vocabulary.

## Related features

- [ResistanceReader](resistance-reader.md)
- [Hardware integration](../integration/hardware-integration.md)
- [Error handling](../integration/error-handling.md)
