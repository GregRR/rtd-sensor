# rtd-sensor

`rtd-sensor` is a platform-independent Python library for resistance-to-temperature
and temperature-to-resistance conversion and modeling of resistance temperature
detectors (RTDs). Its verified built-in characteristics include IEC 60751 PT-385
Pt100, Pt500, and Pt1000, along with documented Ni1000 and Ni120 nickel RTD
characteristics.

Beyond basic conversion, the library supports configurable Callendar–Van Dusen
models for traceable coefficient sets; generic polynomial, piecewise-polynomial, and
table-backed custom characteristics; dependency-free polynomial calibration fitting
and batch conversion; versioned portable model definitions; IEC 60751 platinum
tolerance calculations; measurement uncertainty; simulation; built-in model
discovery; hardware-neutral measurement composition; and stable language-neutral
conformance artifacts with independent C11/binary32 verification.

It is intended for developers building software, test, measurement, and scientific
applications that already have an RTD resistance measurement and need conversion,
modeling, calibration, tolerance, uncertainty, simulation, or cross-language
validation tools.

## Scope

`rtd-sensor` currently provides these verified built-in characteristics:

| Built-in | Characteristic | R0 at 0 °C | Supported characteristic range |
| --- | --- | ---: | ---: |
| Pt100 | IEC 60751 PT-385 platinum | 100 Ω | -200 °C to 850 °C |
| Pt500 | IEC 60751 PT-385 platinum | 500 Ω | -200 °C to 850 °C |
| Pt1000 | IEC 60751 PT-385 platinum | 1000 Ω | -200 °C to 850 °C |
| Ni1000 6180 | former DIN 43760 / Nickel ND 6178/6180 ppm/K | 1000 Ω | -60 °C to 250 °C |
| Ni1000 TK5000 | Nickel NL 5000 ppm/K | 1000 Ω | -60 °C to 250 °C |
| Ni120 6720 | North American / Minco NA 6720 ppm/K | 120 Ω | -80 °C to 260 °C |

Each built-in converts resistance in ohms to temperature in Celsius and temperature
in Celsius to resistance in ohms. Pt100, Pt500, and Pt1000 share the normalized
IEC 60751 PT-385 platinum curve (α ≈ 0.00385) and differ by nominal resistance.

`rtd_sensor.ni1000` implements the distinct former DIN 43760 nickel characteristic with
1000 Ω at 0 °C, approximately 6178/6180 ppm/K over 0–100 °C, and a
supported characteristic range of -60 °C through 250 °C. It must not be
interchanged with `rtd_sensor.ni1000_tk5000`, which uses a different
resistance-temperature curve.

The conversion modules describe ideal characteristics rather than a particular
sensor manufacturer's packaging or probe construction.

Hardware-specific concerns such as ADC readings, GPIO, SPI, I²C, excitation circuits, two-/three-/four-wire topology, and lead-wire compensation belong in separate hardware layers.

Only RTD characteristics whose equations, validity ranges, independent reference values, tests, and documentation are complete are considered supported.

### Typical uses

`rtd-sensor` is useful when you need to:

- convert a compensated RTD resistance measurement to temperature;
- calculate the expected resistance of an RTD at a known temperature;
- convert ordered batches of temperatures or resistances without a NumPy dependency;
- model an individual IEC 60751 probe with a characterized R0 or custom Callendar–Van Dusen coefficients;
- fit a validated polynomial RTD model from calibration observations while retaining auditable fit evidence;
- serialize and reconstruct supported configurable or fitted models with a versioned portable definition;
- preserve authoritative manufacturer/user table data with a table-backed RTD model;
- discover verified built-in models and their immutable metadata;
- compose a hardware-neutral resistance reader with any structural RTD model;
- evaluate IEC 60751 platinum tolerance limits;
- propagate resistance-measurement uncertainty into temperature uncertainty;
- generate RTD measurements for software testing and simulation; or
- validate independent implementations against the stable conformance-v1 artifacts.

Hardware acquisition remains separate. For example, if a MAX31865 or another
acquisition layer has already produced a compensated resistance measurement,
`rtd-sensor` can handle the RTD conversion and modeling stage; it does not
communicate with the hardware itself.

## Installation

```bash
python -m pip install rtd-sensor
```

**Requires Python 3.14 or later.** The package has no runtime dependencies.

The distribution name uses a hyphen (`rtd-sensor`), while the Python import package uses an underscore (`rtd_sensor`).

## Basic usage

```python
from rtd_sensor import ni1000, ni1000_tk5000, ni120, pt100, pt500, pt1000

pt100_temperature_c = pt100.resistance_to_celsius(119.3971)
pt100_resistance_ohms = pt100.celsius_to_resistance(50.0)

pt500_temperature_c = pt500.resistance_to_celsius(596.99)
pt500_resistance_ohms = pt500.celsius_to_resistance(50.0)

pt1000_temperature_c = pt1000.resistance_to_celsius(1193.971)
pt1000_resistance_ohms = pt1000.celsius_to_resistance(50.0)

ni1000_temperature_c = ni1000.resistance_to_celsius(1617.8)
ni1000_resistance_ohms = ni1000.celsius_to_resistance(100.0)

tk5000_temperature_c = ni1000_tk5000.resistance_to_celsius(1500.00)
tk5000_resistance_ohms = ni1000_tk5000.celsius_to_resistance(100.0)

ni120_temperature_c = ni120.resistance_to_celsius(200.64)
ni120_resistance_ohms = ni120.celsius_to_resistance(100.0)
```

Physical numerical inputs such as temperature, resistance, coefficients, and uncertainty values reject Python Boolean values. This prevents `True`/`False` from being silently interpreted as `1.0`/`0.0`, while ordinary integer, floating-point, and other float-convertible numeric inputs continue to work normally. Boolean control options such as simulation `repeat=True` are unaffected.

## Batch conversion

`rtd_sensor.batch` applies any structural RTD model's scalar conversion behavior to
an ordered iterable and returns an ordinary Python list. The batch helpers have no
NumPy dependency, accept one-pass iterables such as generators, and preserve the
model's scalar validation and exception behavior.

```python
from rtd_sensor import batch, pt100

temperatures_c = [0.0, 25.0, 50.0, 100.0]
resistances_ohms = batch.celsius_to_resistance(pt100, temperatures_c)
round_trip_c = batch.resistance_to_celsius(pt100, resistances_ohms)
```

Conversion is fail-fast: if one element would raise in the scalar API, the same
exception propagates from the batch call and no partial result list is returned.
Scalar conversion remains the authoritative numerical behavior.

## Migrating from pt100-core 0.3.x

Version 0.4.0 renames both the distribution and the Python import package as the project expands beyond its original Pt100-only scope:

```text
Old distribution:  pt100-core
New distribution:  rtd-sensor
Old Python import: rtd
New Python import: rtd_sensor
```

For example:

```python
# pt100-core 0.3.x and earlier
from rtd import pt100

# rtd-sensor 0.4.0 and later
from rtd_sensor import pt100
```

Advanced-model imports change the same way, for example from `rtd.models` to `rtd_sensor.models`. `rtd-sensor` intentionally does **not** ship an `rtd` compatibility package; applications migrating from `pt100-core` must update their imports. Existing `pt100-core` releases remain part of the historical release line.

## Ni1000 6180 / former DIN 43760

`rtd_sensor.ni1000` means the former DIN 43760 / Nickel ND characteristic, not an
arbitrary sensor whose nominal resistance happens to be 1000 Ω. Its normalized
forward equation is:

```text
R(T) / R0 = 1 + 5.485e-3 T + 6.650e-6 T²
              + 2.805e-11 T⁴ - 2.000e-17 T⁶
```

with `R0 = 1000 Ω` at 0 °C and a supported characteristic range of -60 °C
through 250 °C. Published physical sensors may specify narrower operating or
conformity ranges; those product limits are separate from the mathematical
characteristic.

Ni1000 TK5000 is a different characteristic and is not interchangeable with
`rtd_sensor.ni1000`.

## Ni1000 TK5000 / Nickel NL 5000 ppm/K

`rtd_sensor.ni1000_tk5000` implements the distinct TK5000 characteristic. IST AG
publishes the same cubic as `Nickel NL (5000 ppm/K)`:

```text
R(T) / R0 = 1 + 4.427e-3 T + 5.172e-6 T² + 5.585e-9 T³
```

with `R0 = 1000 Ω` at 0 °C and a supported characteristic range of -60 °C
through 250 °C. E+E Elektronik's independently published Ni1000 TK5000 R/T
table is used by the test suite to validate the coefficient implementation.
As with the 6180 characteristic, a packaged sensor may have a narrower physical
operating range than the mathematical characteristic represented here.

The explicit module name is intentional: `Ni1000` alone does not uniquely
identify an R/T curve, so the package must not silently choose TK5000 when a
user actually has the former-DIN 6180 characteristic, or vice versa.

## Ni120 / North American 6720 ppm/K

`rtd_sensor.ni120` implements Minco's `NA` nickel characteristic: 120 Ω at 0 °C
with nominal TCR 0.00672 Ω/Ω/°C. Minco publishes this characteristic as
twelve cubic intervals from -80 °C through 260 °C rather than as one global
polynomial:

```text
R(T) / R0 = A + B*T + C*T² + D*T³
```

The A/B/C/D coefficients change at the published interval boundaries. The
library preserves those source coefficient tuples exactly. Because Minco's
printed interval fits contain tiny join mismatches at their published
precision, the built-in characteristic uses the generic piecewise model's
explicit bounded constant-offset stitching. The largest applied normalized
adjustment is about 7.2e-6, equivalent to less than 0.001 Ω for this 120 Ω
characteristic; slopes and higher-order shape remain the published Minco
values.

Pyromation's independently published 120 Ω / 0.00672 R/T table is used for
validation. As with the other built-ins, the characteristic range is distinct
from narrower operating limits that a particular packaged sensor may specify.

## Configurable IEC 60751 models

For an individual Pt100, Pt500, Pt1000, or other IEC 60751 PT-385 sensor with a characterized resistance at 0 °C, use `IEC60751RTDModel`:

```python
from rtd_sensor.models import IEC60751RTDModel

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
from rtd_sensor.models import CallendarVanDusenRTDModel

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
from rtd_sensor.models import PolynomialRTDModel

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

Do not force a published piecewise or tabulated characteristic into this single-polynomial API. Use `PiecewisePolynomialRTDModel` for a source that publishes separate interval equations and `TabulatedRTDModel` when the authoritative source is a resistance/temperature table.

## Polynomial calibration fitting

`rtd_sensor.fitting` can fit a validated `PolynomialRTDModel` directly from measured `(temperature, resistance)` calibration observations without adding NumPy or another numerical dependency:

```python
from rtd_sensor import fitting

observations = (
    fitting.CalibrationObservation(temperature_c=0.0, resistance_ohms=100.02),
    fitting.CalibrationObservation(temperature_c=50.0, resistance_ohms=119.43),
    fitting.CalibrationObservation(temperature_c=100.0, resistance_ohms=138.56),
)

fit = fitting.fit_polynomial(observations, degree=2)
model = fit.model
print(fit.evidence.rms_residual_ohms)
```

The fit result deliberately keeps the validated numerical model separate from the evidence supporting it. Evidence retains the original observations, per-point resistance residuals, RMS and maximum absolute residual error, fitting range, solver/scaling information, a conditioning diagnostic, and observation/parameter/residual-degree-of-freedom counts. Repeated temperatures are retained as independent observations rather than silently averaged. The reported RMS is a descriptive root mean square over the observations, not a degrees-of-freedom-adjusted uncertainty estimate; a nearly saturated fit can therefore have very small residuals without demonstrating predictive quality.

Weighted least squares may use either a positive relative `weight` on every observation or a positive `standard_uncertainty_ohms` on every observation. Resistance standard uncertainties are converted to normalized inverse-variance weights; temperature is treated as the independent variable, so this initial fitter does not model temperature uncertainty. A caller may narrow the fitted model's validity range inside the observed calibration span, but the API does not silently extrapolate beyond that span. Rank-deficient, severely ill-conditioned, non-positive, or non-monotonic fitted curves raise `RTDFitError` instead of returning a deployable model.

## Portable model definitions

`rtd_sensor.portable` serializes validated configurable or fitted RTD models to a
versioned language-neutral definition that can be reconstructed without rerunning a
fit. Version 1 supports characterized IEC 60751 PT-385 models, custom
Callendar–Van Dusen models, global polynomial models, and piecewise-polynomial
models. Tabulated-model portability remains future work.

```python
from rtd_sensor import portable
from rtd_sensor.models import IEC60751RTDModel

model = IEC60751RTDModel(
    r0_ohms=100.017,
    minimum_temperature_c=-50.0,
    maximum_temperature_c=250.0,
)

artifact = portable.model_to_portable_definition(
    model,
    metadata={"source": "calibration record 2026-08"},
)
loaded = portable.model_from_portable_definition(artifact)

assert loaded.model.r0_ohms == 100.017
assert loaded.metadata["source"] == "calibration record 2026-08"
```

The portable format is separate from conformance fixtures and has its own
`format_version`. Unknown behavior-changing fields, unsupported format versions,
unsupported model kinds, and invalid numerical definitions are rejected rather
than guessed. Optional metadata is non-behavioral and preserved separately from
the reconstructed model; physical probe identity, hardware configuration, and
application-specific channel semantics remain outside the artifact. The versioned
JSON Schema and language-neutral format notes are in
[`portable/README.md`](https://github.com/GregRR/rtd-sensor/blob/main/portable/README.md).

## Piecewise polynomial RTD models

`PiecewisePolynomialRTDModel` preserves documented characteristics that publish a different polynomial over each temperature interval. Each `PiecewisePolynomialSegment` stores the complete normalized polynomial for one interval, including its constant term:

```text
R(T) / Rref = c0 + c1*x + c2*x² + ... + cn*xⁿ
x = T - segment_temperature_origin
```

For example:

```python
from rtd_sensor.models import PiecewisePolynomialRTDModel, PiecewisePolynomialSegment

example = PiecewisePolynomialRTDModel(
    reference_resistance_ohms=100.0,
    segments=(
        PiecewisePolynomialSegment(
            minimum_temperature_c=-10.0,
            maximum_temperature_c=0.0,
            coefficients=(1.0, 0.01),
        ),
        PiecewisePolynomialSegment(
            minimum_temperature_c=0.0,
            maximum_temperature_c=10.0,
            coefficients=(1.0, 0.02),
        ),
    ),
    coefficient_source="Example only — not a real sensor characteristic",
)
```

Segments must be contiguous, positive-resistance, and strictly increasing. The model preserves each source coefficient tuple and provides one bounded inverse across the complete characteristic. Interior temperature boundaries route to the segment on their right; if adjacent segments have different slopes, sensitivity at the boundary therefore reports that right-hand slope.

Published piecewise fits are sometimes independently rounded and miss exact continuity by a tiny amount. The default API does not hide such a mismatch. A caller may explicitly set `maximum_continuity_adjustment_ratio` to authorize only a bounded additive correction to each segment's normalized constant term. The reference-temperature segment remains the anchor, derivatives are unchanged, and the applied offsets are exposed as `continuity_adjustments` for auditability. This mechanism is for documented source-rounding effects, not for making genuinely incompatible segments appear valid.

## Tabulated RTD models

`TabulatedRTDModel` preserves an authoritative resistance/temperature table instead of fitting a new equation to it. Supply immutable `TabulatedRTDPoint` rows in strictly increasing temperature and resistance order:

```python
from rtd_sensor.models import TabulatedRTDModel, TabulatedRTDPoint

example = TabulatedRTDModel(
    points=(
        TabulatedRTDPoint(temperature_c=0.0, resistance_ohms=100.0),
        TabulatedRTDPoint(temperature_c=50.0, resistance_ohms=119.4),
        TabulatedRTDPoint(temperature_c=100.0, resistance_ohms=138.5),
    ),
    name="Illustrative table-backed RTD",
    table_source="Example only — not a real sensor table",
    source_precision="temperature 0.1 °C; resistance 0.1 Ω",
)

assert example.celsius_to_resistance(75.0) == 128.95
```

The model uses piecewise-linear interpolation between adjacent source rows. Linear interpolation is deliberate: it retains every supplied point, cannot overshoot a strictly monotonic table, introduces no fitted curvature, and has an exact inverse within each interval. The first release does not extrapolate at all; temperatures or resistances beyond the source table raise `RTDOutOfRangeError`.

At an interior source point, local sensitivity uses the interval on the point's right; the final point uses the last interval. This gives deterministic `dR/dT` and `dT/dR` behavior when adjacent table intervals have different slopes, matching the one-sided convention used for piecewise-polynomial joins. `source_precision` is optional provenance metadata: extra digits produced by interpolation do not imply more scientific precision than the published table.

## Public RTD model protocol

Application code that accepts more than one RTD characteristic can type against the structural `RTDModel` protocol instead of depending on a concrete model class:

```python
from rtd_sensor import pt100
from rtd_sensor.models import IEC60751RTDModel, RTDModel


def convert_temperature(model: RTDModel, resistance_ohms: float) -> float:
    return model.resistance_to_celsius(resistance_ohms)


nominal_temperature_c = convert_temperature(pt100, 119.397125)

calibrated_probe = IEC60751RTDModel(r0_ohms=100.017)
calibrated_temperature_c = convert_temperature(calibrated_probe, 119.42)
```

`RTDModel` is a structural typing interface: a third-party object does not need to inherit from an `rtd-sensor` base class. It qualifies when it provides the same forward conversion, inverse conversion, `dR/dT`, and `dT/dR` operations. Model identity, discoverable built-in metadata, and hardware acquisition remain separate concerns rather than being forced into this numerical behavior contract.

The existing `rtd_sensor.uncertainty.RTDUncertaintyModel` remains a narrower structural interface for callers that provide only the inverse conversion and `dT/dR` behavior required by uncertainty propagation. Every full `RTDModel` satisfies that narrower interface.

## Built-in model discovery

Applications that need to discover supported built-ins at runtime can use the read-only `rtd_sensor.catalog` API instead of maintaining their own model table:

```python
from rtd_sensor import catalog

model_ids = catalog.supported_models()
# ("pt100", "pt500", "pt1000", "ni1000", "ni1000_tk5000", "ni120")

info = catalog.model_info("pt100")
print(info.characteristic_id)  # iec60751_pt385
print(info.reference_resistance_ohms)  # 100.0
print(info.minimum_temperature_c)  # -200.0
print(info.maximum_temperature_c)  # 850.0

model = catalog.get_model("pt100")
temperature_c = model.resistance_to_celsius(119.397125)
```

`BuiltinRTDModelInfo` descriptors are immutable and are derived from the same authoritative definitions used to construct the runtime models and stable conformance artifacts. They expose canonical model and characteristic identities, display names, material and curve kind, reference resistance/temperature, valid temperature range, and characteristic source references.

The catalog contains only verified package built-ins. Canonical IDs are exact and stable; the discovery API intentionally does not provide aliases or a public registration/plugin mechanism for user-defined models. Custom model objects can continue to satisfy the structural `RTDModel` protocol without becoming globally registered identities.

## Hardware-neutral resistance readers

Acquisition layers that already produce the best available estimate of sensor-element resistance in ohms can type against the hardware-neutral `ResistanceReader` protocol:

```python
from rtd_sensor.measurement import ResistanceReader


def read_resistance(reader: ResistanceReader) -> float:
    return reader.read_resistance_ohms()
```

`ResistanceReader` is structural: hardware packages and application objects do not need to inherit from an `rtd-sensor` base class. The interface deliberately contains only `read_resistance_ohms()`; converter configuration, ADC/reference-resistor calculations, wiring topology, lead compensation, GPIO/SPI/I²C, and RTD model selection remain outside the acquisition contract.

Application code composes that resistance source with any public `RTDModel`:

```python
from rtd_sensor import catalog, measurement

model = catalog.get_model("pt1000")
temperature_c = measurement.read_temperature_celsius(
    hardware_reader,
    model=model,
)
```

The same path accepts characterized or third-party structural models:

```python
from rtd_sensor import measurement, models

model = models.IEC60751RTDModel(r0_ohms=100.037)
temperature_c = measurement.read_temperature_celsius(
    hardware_reader,
    model=model,
)
```

The built-in `rtd_type="pt1000"` convenience and historical untyped-reader Pt100 default remain available for compatibility. `model` and `rtd_type` are mutually exclusive. A reader that itself declares `rtd_type` cannot be combined with an explicit model object because the structural `RTDModel` protocol intentionally carries no identity metadata with which to prove the two declarations agree.

Existing `rtd_sensor.simulation.ResistanceReader` and `simulation.read_temperature_celsius` imports continue to work as compatibility re-exports of the neutral measurement API. Simulation readers and future physical acquisition readers are therefore peers at the compensated-resistance boundary.

## Public exceptions

Applications that need stable branching for package-owned RTD domain failures can use the deliberately small `rtd_sensor.exceptions` hierarchy:

```python
from rtd_sensor import exceptions, pt100

try:
    temperature_c = pt100.resistance_to_celsius(measured_resistance)
except exceptions.RTDOutOfRangeError:
    # The resistance was read, but it cannot represent a temperature
    # inside this RTD model's supported range.
    ...
```

`RTDOutOfRangeError`, `InvalidRTDModelError`, `RTDModelSelectionError`, and `RTDFitError` remain subclasses of `ValueError`, so existing callers that already catch `ValueError` continue to work. `UnknownRTDModelError` remains a subclass of `KeyError` for the same reason. All five also derive from `RTDError`, allowing applications to catch package-owned RTD domain failures without also catching unrelated hardware exceptions.

The hierarchy does not wrap acquisition failures from `ResistanceReader` implementations or exceptions raised by arbitrary third-party `RTDModel` objects. Non-finite or otherwise invalid scalar inputs that are not range failures also retain their established `ValueError`/`TypeError` behavior.

## IEC 60751 tolerance classes

The `rtd_sensor.tolerance` module calculates the maximum permitted temperature deviation for the standard IEC 60751:2022 tolerance classes. The standard distinguishes complete thermometers from bare platinum resistors, and it assigns different validity ranges to wire-wound and film construction.

For an assembled thermometer:

```python
from rtd_sensor import tolerance

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

The `rtd_sensor.uncertainty` module provides the low-level numerical building blocks used by measurement-uncertainty analysis. It does **not** automatically decide which effects belong in a particular sensor or hardware uncertainty budget.

For a symmetric bound `±a`, convert the bound to a standard uncertainty only after choosing an appropriate probability model:

```python
from rtd_sensor import uncertainty

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
from rtd_sensor import pt100

d_r_d_t = pt100.resistance_sensitivity_ohms_per_celsius(100.0)
d_t_d_r = pt100.temperature_sensitivity_celsius_per_ohm(100.0)
```

These derivatives are evaluated analytically from the active RTD model rather than estimated by finite differences. They are also used by the RTD-specific propagation helpers.

### RTD uncertainty propagation and budgets

Propagate a resistance standard uncertainty through the same RTD model used for the nominal conversion:

```python
from rtd_sensor import pt100, uncertainty

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
from rtd_sensor import pt100, tolerance, uncertainty

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

All verified built-in sensor modules and the public configurable-model classes,
including `PolynomialRTDModel`, can be passed as the `model`. Third-party models
may also participate if they provide compatible resistance-to-temperature
conversion and local `dT/dR` sensitivity methods.

## Simulation

Simulation readers support every verified built-in RTD characteristic through one
authoritative model-identity registry. Pt100 remains the default for backward
compatibility. The currently registered identities are available through
`simulation.SUPPORTED_RTD_TYPES`, so applications can populate selectors without
maintaining their own copy of the built-in identity list.

```python
from rtd_sensor import simulation

reader = simulation.TemperatureSequenceReader(
    [20.0, 40.0, 60.0],
    rtd_type="pt1000",
)

temperature_c = simulation.read_temperature_celsius(reader)
```

Hardware or other generic resistance readers can still specify a built-in RTD type through the compatibility helper:

```python
temperature_c = simulation.read_temperature_celsius(
    hardware_reader,
    rtd_type="pt1000",
)
```

For new hardware/application composition, prefer `measurement.read_temperature_celsius(..., model=model)` so characterized and third-party model objects use the same resistance boundary. `simulation.read_temperature_celsius` is the exact same function object and remains available for compatibility.

Built-in model-aware readers keep their RTD identity fixed after construction. If a reader declares `rtd_type="pt1000"`, passing a conflicting explicit `rtd_type="pt100"` to `read_temperature_celsius()` raises `ValueError` instead of silently interpreting the resistance with the wrong model. Supplying the same explicit type remains valid. `RTDType` remains a string alias because Python cannot derive a static `Literal[...]` union from the runtime registry; unsupported strings are still rejected strictly at runtime.

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

## Further documentation

See [`docs/DESIGN.md`](https://github.com/GregRR/rtd-sensor/blob/main/docs/DESIGN.md) for detailed architecture and mathematical
assumptions, [`docs/CONFORMANCE.md`](https://github.com/GregRR/rtd-sensor/blob/main/docs/CONFORMANCE.md) for the stable
language-neutral RTD conformance contract,
[`conformance/README.md`](https://github.com/GregRR/rtd-sensor/blob/main/conformance/README.md) for the published conformance
artifacts, [`docs/CROSS_LANGUAGE_IMPLEMENTATIONS.md`](https://github.com/GregRR/rtd-sensor/blob/main/docs/CROSS_LANGUAGE_IMPLEMENTATIONS.md)
for downstream C/C++/MCU implementation guidance, and
[`portable/README.md`](https://github.com/GregRR/rtd-sensor/blob/main/portable/README.md) for the versioned language-neutral
portable-model format and schema.

See [`docs/ROADMAP.md`](https://github.com/GregRR/rtd-sensor/blob/main/docs/ROADMAP.md) for planned RTD families and future
characteristic/calibration work, [`docs/REFERENCES.md`](https://github.com/GregRR/rtd-sensor/blob/main/docs/REFERENCES.md) for the
scientific standards, metrology guidance, and manufacturer/industrial technical sources used by the project,
[`docs/RELEASING.md`](https://github.com/GregRR/rtd-sensor/blob/main/docs/RELEASING.md) for the release checklist, and
[`CITATION.cff`](https://github.com/GregRR/rtd-sensor/blob/main/CITATION.cff) for software citation metadata.

## License

This project is licensed under the Mozilla Public License 2.0. See [`LICENSE`](https://github.com/GregRR/rtd-sensor/blob/main/LICENSE).
