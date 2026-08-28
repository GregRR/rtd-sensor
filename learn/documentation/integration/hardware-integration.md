---
title: Hardware integration
description: Integrate rtd-sensor with MAX31865, DMM, DAQ, bridge, RTD-interface, ADC, or recorded resistance sources while keeping acquisition separate from RTD conversion.
---

# Hardware integration

`rtd-sensor` intentionally does not ship drivers for MAX31865, ADCs, GPIO, SPI,
I²C, PLC modules, or laboratory instruments. Those systems differ too much in
wiring, calibration, error reporting, and operating constraints to belong inside
the RTD characteristic library.

The integration contract is simple:

> Acquisition code should provide the best available estimate of the RTD
> sensing element resistance in ohms.

The same contract also applies when another instrument or interface has already done
that acquisition work. `rtd-acquire` is useful when raw hardware still needs
converter handling, compensation, calibration, diagnostics, or a common acquisition
interface; it is not required merely because a physical RTD is involved.

## Where resistance can come from

| Resistance source | Needs a separate `rtd-acquire` step? | Relationship to `rtd-sensor` |
| --- | --- | --- |
| Manual reading, DMM, or resistance bridge | No | Pass the resistance in ohms directly |
| Raw RTD converter or configurable ADC | Usually | Convert the electrical observations into the best available RTD resistance first |
| USB/HAT/DAQ RTD interface that already reports resistance | Usually no | Feed the reported RTD resistance to `rtd-sensor` |
| PLC or universal input with a documented resistance mode | Usually no | Feed the resistance result to `rtd-sensor`; keep PLC/device faults upstream |
| Recorded resistance dataset | No | Convert or analyze the recorded resistance values directly |
| Smart device that exposes only calculated temperature | Not applicable | The device has already performed RTD interpretation; there is no original resistance for `rtd-sensor` to reinterpret |

Naming a source class here does not mean `rtd-sensor` contains a device driver. The
interoperability contract is the resistance value, not a vendor API.

## Direct composition

```python
from rtd_sensor import measurement, pt100


class HardwareReader:
    def read_resistance_ohms(self) -> float:
        # Driver-specific acquisition and compensation happen here.
        return read_compensated_rtd_resistance()


reader = HardwareReader()
temperature_c = measurement.read_temperature_celsius(reader, model=pt100)
```

## MAX31865-style architecture

Conceptually:

```text
Pt100 probe
    ↓
MAX31865 + wiring/reference configuration
    ↓
acquisition code computes compensated RTD resistance
    ↓
rtd-sensor Pt100 or calibrated model
    ↓
temperature
```

The exact MAX31865 library, board, reference resistor, 2/3/4-wire handling, and
fault registers remain acquisition concerns.

## Calibrated model composition

```python
from rtd_sensor import measurement
from rtd_sensor.models import IEC60751RTDModel

probe_model = IEC60751RTDModel(
    r0_ohms=100.017,
    minimum_temperature_c=-20.0,
    maximum_temperature_c=180.0,
)

temperature_c = measurement.read_temperature_celsius(
    reader,
    model=probe_model,
)
```

No hardware API changes are needed just because the RTD model changes from
nominal to characterized.

## Keep physical sensor identity separate

A model ID such as `pt100` identifies scientific behavior, not a physical asset.
Serial number, installed location, channel, replacement history, calibration
certificate association, and control-loop role belong in the application or
asset-management layer.

## Cross-language systems

A host and MCU can reuse the same model identities and conformance contract
without requiring Python on the embedded target. See
[Cross-language & embedded use](../../advanced/cross-language-embedded.md).
