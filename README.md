# pt100-core

A small, platform-independent Python library for resistance temperature detectors (RTDs).
Its verified built-in sensor modules currently cover IEC 60751 Pt100, Pt500, and Pt1000. The
library also provides configurable and calibrated Callendar–Van Dusen models, a generic
polynomial RTD model for traceable manufacturer/user characteristics, standard platinum
tolerance calculations, measurement-uncertainty tools, and simulation support.

## Scope

`pt100-core` currently handles:

```text
Pt100 resistance in ohms  ↔ temperature in Celsius
Pt500 resistance in ohms  ↔ temperature in Celsius
Pt1000 resistance in ohms ↔ temperature in Celsius
```

The supported models use the IEC 60751 PT-385 platinum curve:

* Pt100: 100 Ω at 0 °C
* Pt500: 500 Ω at 0 °C
* Pt1000: 1000 Ω at 0 °C
* α ≈ 0.00385
* ideal standardized curve from -200 °C through 850 °C

The conversion is not specific to a particular sensor manufacturer or probe construction.

Hardware-specific concerns such as ADC readings, GPIO, SPI, I²C, excitation circuits, two-/three-/four-wire topology, and lead-wire compensation belong in separate hardware layers.

## Basic usage

```python
from rtd import pt100, pt500, pt1000

pt100_temperature_c = pt100.resistance_to_celsius(119.3971)
pt100_resistance_ohms = pt100.celsius_to_resistance(50.0)

pt500_temperature_c = pt500.resistance_to_celsius(596.99)
pt500_resistance_ohms = pt500.celsius_to_resistance(50.0)

pt1000_temperature_c = pt1000.resistance_to_celsius(1193.971)
pt1000_resistance_ohms = pt1000.celsius_to_resistance(50.0)
```

Physical numerical inputs such as temperature, resistance, coefficients, and uncertainty values reject Python Boolean values. This prevents `True`/`False` from being silently interpreted as `1.0`/`0.0`, while ordinary integer, floating-point, and other float-convertible numeric inputs continue to work normally. Boolean control options such as simulation `repeat=True` are unaffected.

## Configurable IEC 60751 models

For an individual Pt100, Pt500, Pt1000, or other IEC 60751 PT-385 sensor with a characterized resistance at 0 °C, use `IEC60751RTDModel`:

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

## Generic polynomial RTD models

For a manufacturer, calibration laboratory, or legacy RTD characteristic that is published as one global polynomial, use `PolynomialRTDModel`:

```python
from rtd.models import PolynomialRTDModel

example = PolynomialRTDModel(
    reference_resistance_ohms=10.0,
    reference_temperature_c=25.0,
    coefficients=(0.01,),
    minimum_temperature_c=-20.0,
    maximum_temperature_c=80.0,
    name="Illustrative linear RTD",
    coefficient_source="Example only — not a real sensor characteristic",
)

assert example.celsius_to_resistance(25.0) == 10.0
```

For `x = T - reference_temperature_c`, the model uses:

```text
R(T) = Rref × (1 + c1*x + c2*x² + ... + cn*xⁿ)
```

`coefficients` therefore contains `(c1, c2, ..., cn)`; the constant term is implicitly 1 at the reference temperature. This formulation is intentionally not tied to platinum or to a 0 °C reference point.

The model analytically differentiates the polynomial, validates that resistance stays finite and positive, and locates derivative extrema to prove the characteristic remains strictly increasing over its declared range. Resistance-to-temperature conversion then uses dependency-free bounded bisection on that validated curve instead of an approximate inverse polynomial.

Do not force a published piecewise or tabulated characteristic into this single-polynomial API. Piecewise-polynomial and authoritative table-based characteristics are separate planned model types.

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

RTD models also expose their exact local resistance/temperature sensitivity. For the built-in platinum models this derivative comes from the Callendar–Van Dusen characteristic, while polynomial models differentiate their supplied polynomial analytically:

```python
from rtd import pt100

d_r_d_t = pt100.resistance_sensitivity_ohms_per_celsius(100.0)
d_t_d_r = pt100.temperature_sensitivity_celsius_per_ohm(100.0)
```

These derivatives are evaluated analytically from the active RTD model rather than estimated by finite differences. They are also used by the RTD-specific propagation helpers.

### RTD uncertainty propagation and budgets

Propagate a resistance standard uncertainty through the same RTD model used for the nominal conversion:

```python
from rtd import pt100, uncertainty

propagated = uncertainty.propagate_resistance_uncertainty(
    100.0,
    0.01,
    model=pt100,
)

print(propagated.temperature_c)
print(propagated.temperature_sensitivity_celsius_per_ohm)
print(propagated.temperature_standard_uncertainty_c)
```

The result retains the measured resistance, converted temperature, resistance standard uncertainty, local `dT/dR` sensitivity, and the propagated temperature contribution. The propagation is first-order (local linearization); sufficiently large uncertainties or strongly nonlinear cases may require a higher-order or Monte Carlo treatment.

Additional independent contributions that are already expressed as standard uncertainties in °C can be kept as named, inspectable components:

```python
from rtd import pt100, tolerance, uncertainty

class_a_limit = tolerance.thermometer_tolerance_c(
    100.0,
    tolerance_class="A",
    construction="wire_wound",
)

# This rectangular model is an explicit user assumption. IEC 60751 does not
# state that values inside the tolerance band follow this distribution.
sensor_u = uncertainty.standard_uncertainty_from_bound(
    class_a_limit,
    distribution="rectangular",
)

sensor_component = uncertainty.TemperatureUncertaintyComponent(
    name="Sensor class limit",
    standard_uncertainty_c=sensor_u,
    evaluation_method="B",
    source="IEC 60751 Class A tolerance modeled as rectangular",
)

budget = uncertainty.temperature_uncertainty_budget(
    pt100.celsius_to_resistance(100.0),
    0.01,
    model=pt100,
    additional_components=(sensor_component,),
    coverage_factor=2.0,
)

print(budget.combined_standard_uncertainty_c)
print(budget.expanded_uncertainty_c)
```

`TemperatureUncertaintyComponent` can optionally retain a Type A/Type B evaluation-method label, source, and note. Those fields are provenance only; all supplied components must already be standard uncertainties in °C. The current budget combines the resistance contribution and additional components as **uncorrelated** terms. It does not yet support covariance matrices, coefficient covariance, effective degrees of freedom, or Monte Carlo propagation.

The built-in `pt100`, `pt500`, and `pt1000` modules and the public configurable-model classes, including `PolynomialRTDModel`, can be passed as the `model`. Third-party models may also participate if they provide compatible resistance-to-temperature conversion and local `dT/dR` sensitivity methods.

## Simulation

Simulation readers support Pt100, Pt500, and Pt1000. Pt100 remains the default for backward compatibility.

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

Built-in model-aware readers keep their RTD identity fixed after construction. If a reader declares `rtd_type="pt1000"`, passing a conflicting explicit `rtd_type="pt100"` to `read_temperature_celsius()` raises `ValueError` instead of silently interpreting the resistance with the wrong model. Supplying the same explicit type remains valid.

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
    _validation.py
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

See [`docs/DESIGN.md`](docs/DESIGN.md) for detailed architecture and mathematical assumptions, and [`docs/ROADMAP.md`](docs/ROADMAP.md) for planned RTD families and future characteristic/calibration work.

## Current capabilities

The current development branch provides:

- IEC 60751 Pt100 resistance-to-temperature and temperature-to-resistance conversion
- IEC 60751 Pt1000 resistance-to-temperature and temperature-to-resistance conversion
- independently sourced reference-value tests for both supported RTD types
- shared internal RTD curve and model infrastructure
- model-aware Pt100/Pt500/Pt1000 simulation while preserving Pt100 defaults
- public configurable IEC 60751 models for individually characterized `R0` values and declared temperature ranges
- public Callendar–Van Dusen models for traceable user-supplied `R0`, `A`, `B`, and optional `C` coefficient sets
- generic polynomial RTD models with explicit reference resistance/temperature, provenance, analytical sensitivity, and validated monotonic inversion
- IEC 60751:2022 tolerance calculations for standard thermometer and platinum-resistor classes
- GUM-style uncertainty primitives, exact RTD sensitivity, first-order resistance-to-temperature propagation, and structured independent-component temperature uncertainty budgets

Potential future RTD types are not considered supported until their equations, ranges, independent reference values, tests, and documentation are complete.

## License

This project is licensed under the Mozilla Public License 2.0. See [`LICENSE`](LICENSE).
