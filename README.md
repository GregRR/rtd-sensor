# pt100-core

A small, platform-independent Python library for converting resistance measurements from standard IEC 60751 Pt100 and Pt1000 resistance temperature detectors into temperature.

It also supports the inverse conversion from temperature to ideal RTD resistance for simulation and testing.

## Scope

`pt100-core` currently handles:

```text
Pt100 resistance in ohms  ↔ temperature in Celsius
Pt1000 resistance in ohms ↔ temperature in Celsius
```

The supported models use the IEC 60751 PT-385 platinum curve:

* Pt100: 100 Ω at 0 °C
* Pt1000: 1000 Ω at 0 °C
* α ≈ 0.00385
* ideal standardized curve from -200 °C through 850 °C

The conversion is not specific to a particular sensor manufacturer or probe construction.

Hardware-specific concerns such as ADC readings, GPIO, SPI, I²C, excitation circuits, two-/three-/four-wire topology, and lead-wire compensation belong in separate hardware layers.

## Basic usage

```python
from rtd import pt100, pt1000

pt100_temperature_c = pt100.resistance_to_celsius(119.3971)
pt100_resistance_ohms = pt100.celsius_to_resistance(50.0)

pt1000_temperature_c = pt1000.resistance_to_celsius(1193.971)
pt1000_resistance_ohms = pt1000.celsius_to_resistance(50.0)
```

## Configurable IEC 60751 models

For an individual Pt100, Pt1000, or other IEC 60751 PT-385 sensor with a characterized resistance at 0 °C, use `IEC60751RTDModel`:

```python
from rtd.models import IEC60751RTDModel

probe = IEC60751RTDModel(
    r0_ohms=100.017,
    name="Calibrated probe A",
    minimum_temperature_c=-50.0,
    maximum_temperature_c=250.0,
)

temperature_c = probe.resistance_to_celsius(119.42)
```

The configurable model retains the standard IEC 60751 PT-385 curve while allowing an individually characterized `R0` and a narrower declared or calibrated temperature range.

For a probe whose calibration certificate or manufacturer documentation supplies an IEC-style Callendar–Van Dusen coefficient set, use `CallendarVanDusenRTDModel`:

```python
from rtd.models import CallendarVanDusenRTDModel

calibrated_probe = CallendarVanDusenRTDModel(
    r0_ohms=100.025,
    a=3.91e-3,
    b=-5.80e-7,
    c=-4.20e-12,
    minimum_temperature_c=-50.0,
    maximum_temperature_c=250.0,
    name="Probe SN-123",
    coefficient_source="Calibration certificate SN-123",
)
```

Custom coefficient models must declare their valid temperature range. `C` may be omitted only when that range is entirely at or above 0 °C. The model validates that the supplied curve remains finite, positive-resistance, and strictly increasing over the interval required for conversion. Custom coefficients are not automatically described as IEC 60751 compliant; `coefficient_source` can retain a calibration-certificate or manufacturer reference alongside the model.

## Simulation

Simulation readers support both Pt100 and Pt1000. Pt100 remains the default for backward compatibility.

```python
from rtd import simulation

reader = simulation.TemperatureSequenceReader(
    [20.0, 40.0, 60.0],
    rtd_type="pt1000",
)

temperature_c = simulation.read_temperature_celsius(reader)
```

Hardware or other generic resistance readers can specify the RTD type when converting a compensated resistance measurement:

```python
temperature_c = simulation.read_temperature_celsius(
    hardware_reader,
    rtd_type="pt1000",
)
```

## Development setup

The project targets Python 3.14 and uses [uv](https://docs.astral.sh/uv/) for development environments and dependency locking.

```bash
uv sync --locked
```

Run the checks:

```bash
uv run --locked pytest
uv run --locked ruff check .
uv run --locked mypy
```

## Project structure

```text
src/rtd/
    _curves.py
    _models.py
    models.py
    pt100.py
    pt1000.py
    simulation.py

tests/
docs/DESIGN.md
```

The repository is named `pt100-core` for discoverability. The Python package uses the broader `rtd` namespace so additional RTD models and curves can be added later without changing existing Pt100 or Pt1000 imports.

See [`docs/DESIGN.md`](docs/DESIGN.md) for detailed architecture, mathematical assumptions, testing requirements, and future plans.

## Status

The current development branch provides:

- IEC 60751 Pt100 resistance-to-temperature and temperature-to-resistance conversion
- IEC 60751 Pt1000 resistance-to-temperature and temperature-to-resistance conversion
- independently sourced reference-value tests for both supported RTD types
- shared internal RTD curve and model infrastructure
- model-aware Pt100/Pt1000 simulation while preserving Pt100 defaults
- public configurable IEC 60751 models for individually characterized `R0` values and declared temperature ranges
- public Callendar–Van Dusen models for traceable user-supplied `R0`, `A`, `B`, and optional `C` coefficient sets

Potential future RTD types are not considered supported until their equations, ranges, independent reference values, tests, and documentation are complete.

## License

This project is licensed under the Mozilla Public License 2.0. See [`LICENSE`](LICENSE).
