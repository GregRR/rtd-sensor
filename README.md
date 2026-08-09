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
    pt100.py
    pt1000.py
    simulation.py

tests/
docs/DESIGN.md
```

The repository is named `pt100-core` for discoverability. The Python package uses the broader `rtd` namespace so additional RTD models and curves can be added later without changing existing Pt100 or Pt1000 imports.

See [`docs/DESIGN.md`](docs/DESIGN.md) for detailed architecture, mathematical assumptions, testing requirements, and future plans.

## Status

The published 0.1.0 release introduced IEC 60751 Pt100 conversion and simulation support.

Current development on `main` additionally provides:

- IEC 60751 Pt1000 resistance-to-temperature conversion
- Pt1000 temperature-to-resistance conversion
- independently sourced Pt1000 reference-value tests
- shared internal RTD curve and model infrastructure
- model-aware Pt100/Pt1000 simulation while preserving Pt100 defaults

Potential future RTD types are not considered supported until their equations, ranges, independent reference values, tests, and documentation are complete.

## License

This project is licensed under the Mozilla Public License 2.0. See [`LICENSE`](LICENSE).
