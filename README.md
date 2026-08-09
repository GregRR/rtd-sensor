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

## IEC 60751 tolerance classes

The `rtd.tolerance` module calculates the maximum permitted temperature deviation for the standard IEC 60751:2022 tolerance classes. The standard distinguishes complete thermometers from bare platinum resistors, and it assigns different validity ranges to wire-wound and film construction.

For an assembled thermometer:

```python
from rtd import tolerance

maximum_error_c = tolerance.thermometer_tolerance_c(
    100.0,
    tolerance_class="A",
    construction="wire_wound",
)
# 0.35 °C
```

For a bare platinum resistor, the public ASCII class designations combine the IEC `W`/`F` construction prefix with the class value:

```python
maximum_error_c = tolerance.platinum_resistor_tolerance_c(
    100.0,
    tolerance_class="F0.15",
)
# 0.35 °C
```

Use `thermometer_tolerance_c()` for a complete, assembled temperature sensor or probe. Use `platinum_resistor_tolerance_c()` when you are working with the bare platinum sensing element and its W/F resistor-class designation.

Both functions return the **positive magnitude** of the maximum permitted deviation. For example, a return value of `0.35` means a nominal tolerance band of ±0.35 °C at that temperature; it does not mean the sensor is expected to be off by 0.35 °C.

The standard validity range for the selected class is enforced. Values outside that range raise `ValueError` rather than silently extrapolating a class designation. Tolerance is a bounded conformity limit, not a probability distribution or standard uncertainty. These functions calculate the numerical class limit and validity range only; they do not assert that a physical sensor satisfies every IEC 60751 construction and test requirement.

## Measurement uncertainty primitives

The `rtd.uncertainty` module provides the low-level numerical building blocks used by measurement-uncertainty analysis. It does **not** automatically decide which effects belong in a particular sensor or hardware uncertainty budget.

For a symmetric bound `±a`, convert the bound to a standard uncertainty only after choosing an appropriate probability model:

```python
from rtd import uncertainty

u_rectangular = uncertainty.standard_uncertainty_from_bound(
    0.35,
    distribution="rectangular",
)

u_triangular = uncertainty.standard_uncertainty_from_bound(
    0.35,
    distribution="triangular",
)
```

The rectangular and triangular helpers use `a / sqrt(3)` and `a / sqrt(6)` respectively. Choosing either distribution is an explicit modeling assumption. In particular, an IEC tolerance limit is **not** automatically a standard uncertainty simply because the library can convert a bound numerically.

Independent standard-uncertainty components can be combined by root-sum-square, and expanded uncertainty can be calculated when the coverage factor is known:

```python
combined_u_c = uncertainty.combine_independent_standard_uncertainties(
    0.04,
    0.07,
    0.02,
)

expanded_u = uncertainty.expanded_uncertainty(
    combined_u_c,
    coverage_factor=2.0,
)
```

No confidence level is inferred from a coverage factor. A statement such as `k = 2` only has a probability interpretation when that interpretation is justified by the complete uncertainty analysis. Correlated components are not supported by this helper; covariance-aware propagation is a later capability.

RTD models also expose their exact local Callendar–Van Dusen sensitivity:

```python
from rtd import pt100

d_r_d_t = pt100.resistance_sensitivity_ohms_per_celsius(100.0)
d_t_d_r = pt100.temperature_sensitivity_celsius_per_ohm(100.0)
```

These derivatives are evaluated analytically from the active RTD model rather than estimated by finite differences. They form the basis for propagating resistance uncertainty into temperature uncertainty in the next uncertainty layer.

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
    tolerance.py
    uncertainty.py

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
- IEC 60751:2022 tolerance calculations for standard thermometer and platinum-resistor classes
- GUM-style uncertainty primitives for bound conversion, independent root-sum-square combination, expanded uncertainty, and exact RTD sensitivity

Potential future RTD types are not considered supported until their equations, ranges, independent reference values, tests, and documentation are complete.

## License

This project is licensed under the Mozilla Public License 2.0. See [`LICENSE`](LICENSE).
