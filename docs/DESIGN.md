# rtd-sensor Design

## 1. Purpose

`rtd-sensor` provides a small, dependable, platform-independent implementation of resistance-to-temperature and temperature-to-resistance conversion and modeling for resistance temperature detectors (RTDs).

Verified built-in characteristics currently include:

- IEC 60751 PT-385 Pt100: nominal resistance 100 Ω at 0 °C
- IEC 60751 PT-385 Pt500: nominal resistance 500 Ω at 0 °C
- IEC 60751 PT-385 Pt1000: nominal resistance 1000 Ω at 0 °C
- former-DIN Ni1000 6178/6180: nominal resistance 1000 Ω at 0 °C
- Ni1000 TK5000 / Nickel NL 5000 ppm/K: nominal resistance 1000 Ω at 0 °C
- North American Ni120 / 6720 ppm/K: nominal resistance 120 Ω at 0 °C

The library also supports traceable custom equation- and table-backed RTD models, built-in model discovery, hardware-neutral resistance/model composition, a small public exception taxonomy, IEC 60751 platinum tolerance calculations, measurement-uncertainty analysis, simulation, and stable language-neutral conformance artifacts.

The project exists so applications can share one tested scientific conversion and modeling layer while keeping hardware acquisition code separate.

## 2. Core architectural boundary

The project begins only after a hardware or simulated measurement has been expressed as resistance in ohms.

```text
raw ADC or digital-interface data
              |
              v
hardware-specific measurement and compensation
              |
              v
resistance in ohms
              |
              v
rtd-sensor
              |
              v
temperature in Celsius
```

`rtd-sensor` does not determine how raw electrical signals become resistance. That responsibility belongs to hardware-facing code.

This boundary allows identical conversion code to be used with:

- BeagleBone Black
- Raspberry Pi
- desktop computers
- microcomputer test environments
- MAX31865 interfaces
- custom analog front ends
- recorded datasets
- simulated data

## 3. Design principles

### 3.1 Platform independence

The core package must not depend on GPIO, SPI, I²C, ADC, or board-specific libraries.

`rtd-sensor` is developed primarily with Python 3.14 while supporting CPython
3.11 and later. Runtime code must remain compatible with the minimum supported
Python version, and CI verifies each supported Python minor release.

### 3.2 Scientific transparency

The implementation should identify the standard, equation, constants, assumptions, and supported range. Constants must not appear as unexplained magic numbers.

`docs/REFERENCES.md` is the canonical bibliography for external scientific and engineering sources. When a source materially determines an implemented equation, coefficient set, range, tolerance rule, uncertainty method, calibration method, or numerical scientific decision, the implementation point should carry a concise `Source:` comment when that provenance is not already obvious from structured source metadata. Independent test data should use `Validation source:` so implementation provenance is not confused with external verification. The complete bibliographic citation remains in `docs/REFERENCES.md`.

### 3.3 Small public API

The public interfaces for supported RTD models should remain parallel and simple:

```python
from rtd_sensor import ni1000, ni1000_tk5000, ni120, pt100, pt500, pt1000

pt100_temperature_c = pt100.resistance_to_celsius(resistance_ohms)
pt100_resistance_ohms = pt100.celsius_to_resistance(temperature_c)

pt500_temperature_c = pt500.resistance_to_celsius(resistance_ohms)
pt500_resistance_ohms = pt500.celsius_to_resistance(temperature_c)

pt1000_temperature_c = pt1000.resistance_to_celsius(resistance_ohms)
pt1000_resistance_ohms = pt1000.celsius_to_resistance(temperature_c)

ni1000_temperature_c = ni1000.resistance_to_celsius(resistance_ohms)
ni1000_resistance_ohms = ni1000.celsius_to_resistance(temperature_c)

tk5000_temperature_c = ni1000_tk5000.resistance_to_celsius(resistance_ohms)
tk5000_resistance_ohms = ni1000_tk5000.celsius_to_resistance(temperature_c)

ni120_temperature_c = ni120.resistance_to_celsius(resistance_ohms)
ni120_resistance_ohms = ni120.celsius_to_resistance(temperature_c)
```

The public `rtd_sensor.models.RTDModel` protocol defines the common numerical behavior expected by code that accepts arbitrary RTD models: temperature-to-resistance conversion, resistance-to-temperature conversion, and both local sensitivity directions. The protocol is structural, so the built-in sensor modules, configurable package models, and compatible third-party objects can satisfy it without inheriting from a package base class. Identity and descriptive metadata are intentionally excluded from this behavioral protocol and remain separate interface concerns.

The narrower `rtd_sensor.uncertainty.RTDUncertaintyModel` protocol is retained for uncertainty-only callers. `RTDModel` includes that narrower behavior rather than replacing it with a broader requirement that would break third-party uncertainty integrations.

### 3.4 Simulation as a first-class use case

Temperature-to-resistance conversion is part of the supported public API, not merely an internal helper. It enables application testing without attached hardware.

### 3.5 No premature hardware coupling

Wire compensation, excitation circuits, ADC scaling, amplifier gain, reference resistors, and device-register handling must not leak into the scientific conversion layer.

### 3.6 Verifiability

Results must be tested against authoritative standards, traceable manufacturer equations or tables, or independently reproduced reference data appropriate to each characteristic.

## 4. Mathematical model

The built-in platinum models use the IEC 60751 Callendar–Van Dusen
relationship. Built-in non-platinum models use their own documented
characteristic equations rather than being forced into CVD.

For temperatures at or above 0 °C:

```text
R(T) = R0 × (1 + A×T + B×T²)
```

For temperatures below 0 °C:

```text
R(T) = R0 × [1 + A×T + B×T² + C×(T - 100)×T³]
```

For the standard IEC 60751 PT-385 curve:

```text
A  = 3.9083 × 10⁻³ °C⁻¹
B  = -5.775 × 10⁻⁷ °C⁻²
C  = -4.183 × 10⁻¹² °C⁻⁴
```

The supported IEC 60751 PT-385 platinum models differ in nominal resistance at 0 °C:

```text
Pt100:  R0 = 100 Ω
Pt500:  R0 = 500 Ω
Pt1000: R0 = 1000 Ω
```

Resistance-to-temperature conversion above 0 °C may use the analytic inverse of the quadratic equation. The implementation should use an algebraically stable quadratic form that avoids subtracting nearly equal terms for ordinary platinum RTD coefficients. Below 0 °C, the implementation may use a bounded numerical solution of the complete equation.

The implementation must document numerical tolerances and must avoid silently extrapolating beyond its supported range.

### 4.1 Former DIN 43760 Ni1000 6178/6180 characteristic

The built-in `rtd_sensor.ni1000` module represents the former DIN 43760 nickel
characteristic with `R0 = 1000 Ω` at 0 °C:

```text
R(T) = R0 × (1 + A×T + B×T² + D×T⁴ + F×T⁶)

A = 5.485 × 10⁻³ °C⁻¹
B = 6.650 × 10⁻⁶ °C⁻²
D = 2.805 × 10⁻¹¹ °C⁻⁴
F = -2.000 × 10⁻¹⁷ °C⁻⁶
```

The supported characteristic range is -60 °C through 250 °C. This is a
mathematical characteristic range, not a guarantee that every physical Ni1000
product can operate or conform across the entire interval. Ni1000 TK5000 is a
different characteristic and must use a separate model identity.

### 4.2 Ni1000 TK5000 / Nickel NL 5000 ppm/K characteristic

The built-in `rtd_sensor.ni1000_tk5000` module represents the distinct TK5000 nickel
characteristic. IST AG publishes the forward coefficients under the name
`Nickel NL (5000 ppm/K)`:

```text
R(T) = R0 × (1 + A×T + B×T² + C×T³)

A = 4.427 × 10⁻³ °C⁻¹
B = 5.172 × 10⁻⁶ °C⁻²
C = 5.585 × 10⁻⁹ °C⁻³
```

The model uses `R0 = 1000 Ω` at 0 °C and a supported characteristic range of
-60 °C through 250 °C. The E+E Elektronik Ni1000 TK5000 R/T table provides an
independent validation source. Product-specific operating limits remain
separate from the characteristic range.

`rtd_sensor.ni1000` and `rtd_sensor.ni1000_tk5000` must remain separate model identities.
They share the same nominal resistance at 0 °C but differ materially away from
that reference point, so nominal resistance alone cannot select a nickel RTD
characteristic safely.

### 4.3 North American Ni120 / 6720 ppm/K characteristic

The built-in `rtd_sensor.ni120` module represents Minco's `NA` nickel characteristic
with `R0 = 120 Ω` at 0 °C and nominal TCR 0.00672 Ω/Ω/°C. Minco publishes a
stepwise approximation using twelve temperature intervals from -80 °C through
260 °C:

```text
R(T) = R0 × (A + B×T + C×T² + D×T³)
```

The coefficients are interval-specific and must be preserved as source data;
they must not be replaced by a convenient two-segment or global fit. Minco's
printed coefficients leave tiny discontinuities at several joins. The built-in
curve therefore uses the generic piecewise model's explicit bounded continuity
stitching, anchored at 0 °C. Only normalized constant offsets are applied, so
the published segment derivatives and higher-order shapes are unchanged. The
largest adjustment is below `1e-5` in normalized resistance (below 0.001 Ω for
Ni120), and the applied offsets remain inspectable on the internal curve.

Pyromation's independent 120 Ω / 0.00672 table validates the implemented
characteristic. The -80 °C through 260 °C model range comes from the published
piecewise equation/table and remains separate from any individual product's
physical operating range.

## 5. Supported public API

The supported built-in model modules are `rtd_sensor.pt100`, `rtd_sensor.pt500`,
`rtd_sensor.pt1000`, `rtd_sensor.ni1000`, `rtd_sensor.ni1000_tk5000`, and `rtd_sensor.ni120`. Each
exposes the same conversion interface:

```python
def resistance_to_celsius(resistance_ohms: float) -> float: ...


def celsius_to_resistance(temperature_c: float) -> float: ...
```

Potential future convenience functions may include:

```python
def resistance_to_fahrenheit(resistance_ohms: float) -> float: ...


def fahrenheit_to_resistance(temperature_f: float) -> float: ...
```

Those convenience functions are not currently part of the public API. Celsius is the native temperature representation used by the supported characteristic definitions.

### 5.1 Batch conversion API

Batch conversion is a Python convenience layer, not an expansion of the public
`RTDModel` structural protocol. Adding required batch methods to `RTDModel` would
unnecessarily break third-party structural implementations that already satisfy
the scalar protocol. The 0.6.0 implementation uses a separate
`rtd_sensor.batch` module with two generic operations conceptually equivalent to:

```python
def celsius_to_resistance(
    model: RTDModel,
    temperatures_c: Iterable[float],
) -> list[float]: ...


def resistance_to_celsius(
    model: RTDModel,
    resistances_ohms: Iterable[float],
) -> list[float]: ...
```

The batch contract is deliberately small:

* the input may be any one-pass iterable of scalar values, including a generator;
* inputs are consumed once, in order, and the result is an eagerly evaluated
  `list[float]` in the same order;
* an empty iterable returns an empty list;
* each element is processed by the same scalar conversion behavior used by the
  supplied model;
* conversion is fail-fast: the first scalar exception propagates unchanged and
  no partial result collection is returned;
* the initial API does not introduce per-element status objects or a partial-failure
  result type;
* NumPy is neither imported nor required, but a NumPy array or other iterable may
  be supplied when its elements satisfy the scalar API; the return type remains a
  normal Python list rather than attempting to preserve an input container type;
  and
* the initial batch surface covers conversion only, not sensitivity, tolerance,
  uncertainty, simulation, or fitting.

Scalar conversion remains authoritative. Tests for the batch layer should compare
its outputs and failures directly with ordered scalar calls so optimized or future
implementations cannot acquire different numerical, range, or exception semantics.
This Python convenience API does not create a new conformance capability and does
not imply that an embedded implementation needs a batch API.

## 6. Validation and errors

The conversion functions should reject:

- non-finite numeric values
- non-positive resistance values
- temperatures outside the documented supported range
- resistance values that cannot represent a temperature inside that range

The public `rtd_sensor.exceptions` module provides a deliberately small taxonomy for package-owned RTD domain failures. `RTDOutOfRangeError`, `InvalidRTDModelError`, `RTDModelSelectionError`, and `RTDFitError` subclass `ValueError`; `UnknownRTDModelError` subclasses `KeyError`; and all five also derive from `RTDError`. Existing callers that catch the historical built-in exception types therefore remain compatible while applications can branch on package-owned RTD failures without parsing messages.

The taxonomy is intentionally selective. Non-finite/non-positive scalar input validation continues to use the established `ValueError` behavior unless the failure is specifically a supported-range violation, and type-category mistakes continue to use `TypeError`. Hardware/acquisition exceptions and arbitrary third-party model exceptions are not translated into `RTDError`.

The package should not silently clamp physical measurements. One narrow numerical exception is permitted at normalized curve boundaries: converting an exact endpoint through `R0 × ratio` and then back through `R / R0` can land exactly one representable floating-point value beyond the original ratio. The curve layer may normalize that one-ULP artifact back to the mathematical endpoint, while the public resistance-in-ohms validation remains strict. Values farther outside the supported range must still be rejected.

Physical numerical inputs also reject Python Boolean values explicitly. Although `bool` is a subclass of `int`, silently interpreting `True` as `1.0` or `False` as `0.0` can turn a programming flag into a plausible resistance, temperature, coefficient, or uncertainty. Boolean control parameters such as simulation `repeat` remain ordinary booleans. Other float-convertible numeric inputs retain the existing coercion behavior.

## 7. Simulation

Simulation should support two levels.

### 7.1 Exact reference simulation

The inverse conversion function generates ideal resistance from a requested temperature:

```python
resistance = pt100.celsius_to_resistance(65.0)
```

This is sufficient for deterministic tests of application behavior.

### 7.2 Measurement-stream simulation

The simulation module currently provides fixed resistance readings, finite and
repeating resistance sequences, temperature-defined sequences, and reproducible
seeded temperature noise. Temperature-based readers are model-aware and support
Pt100, Pt500, Pt1000, the former-DIN Ni1000 6180 characteristic, Ni1000
TK5000, and North American Ni120. Pt100
remains the default for backward compatibility.

A reader that declares an RTD type establishes a model-identity invariant: its declared type must not diverge from the model used to validate or generate its resistance values. Built-in readers therefore keep `rtd_type` read-only after construction. `read_temperature_celsius()` also rejects an explicit RTD type that conflicts with a model-aware reader's declaration. Generic readers that expose only resistance remain supported; callers may select their RTD type explicitly, and untyped readers still default to Pt100 for backward compatibility.

Built-in simulation identities are registered with their internal `RTDModel` definitions and exposed through one immutable identity-to-model registry. Simulation must consume that registry rather than maintain a second sensor list. This keeps conversion support and simulation identity from drifting apart as new verified characteristics are added. `simulation.SUPPORTED_RTD_TYPES` is generated from the same registry.

`simulation.RTDType` is intentionally a string alias rather than a closed `Literal[...]` union. Python's static type system cannot derive a literal union from the runtime registry, so retaining both would recreate two sources of truth. Runtime model selection remains strict: a string not present in the built-in registry raises `ValueError`. There is no public runtime registration/plugin API at this stage; the registry represents the package's verified built-in characteristics only.

Future simulation additions may include ramps, heating and cooling profiles, and injected open-circuit or short-circuit faults.

Simulation components expose resistance values so they exercise the same application path as real hardware.

### 7.3 Hardware-neutral resistance-reader contract

The public `rtd_sensor.measurement.ResistanceReader` protocol owns the boundary between acquisition and RTD interpretation. It is deliberately structural and minimal: a compatible object provides only `read_resistance_ohms()` and need not inherit from an `rtd-sensor` class.

The returned value represents the acquisition layer's best available estimate of sensor-element resistance in ohms. Device-specific conversion, excitation/reference-resistor calculations, wiring topology, lead compensation, transport, and hardware fault handling remain responsibilities of the acquisition layer. The protocol therefore does not include wire count, converter type, bus operations, or raw ADC values.

RTD model identity is also intentionally absent from the neutral reader contract. A resistance source and an RTD model are separate pieces of application composition; simulation readers may carry built-in identity as a convenience, but future physical readers are not required to do so. `rtd_sensor.simulation.ResistanceReader` re-exports the neutral protocol for backward compatibility, so simulation and physical acquisition implementations remain peers at the same boundary.

### 7.4 Resistance-to-temperature model composition

The public `rtd_sensor.measurement.read_temperature_celsius()` helper is the application-level seam between acquisition and RTD interpretation. It reads compensated resistance from a `ResistanceReader` and delegates inverse conversion to any structural `RTDModel`; the composition layer does not inspect curve internals or require a package-specific model base class.

New integrations should prefer explicit `model=` composition. The existing built-in `rtd_type` string convenience and the historical Pt100 default for untyped readers remain for compatibility. `model` and `rtd_type` are mutually exclusive. If a reader itself declares `rtd_type`, an explicit model object is rejected rather than treated as an override: `RTDModel` deliberately carries no identity metadata, so the package cannot prove that the declarations describe the same characteristic. A matching explicit `rtd_type` remains valid, while a contradictory one is rejected before consuming a reading.

The helper deliberately preserves failure ownership. Exceptions raised while acquiring resistance propagate as acquisition failures, and exceptions raised by the selected model propagate as model/conversion failures. The public exception taxonomy provides stable package-owned model-side distinctions while preserving this boundary: the composition seam must not translate hardware failures or arbitrary third-party model failures into RTD-domain failures.

`rtd_sensor.simulation.read_temperature_celsius` remains an exact compatibility re-export of the neutral helper. Higher-level channel objects that bind hardware configuration, a reader, a model, labels, or control behavior belong in application/hardware packages rather than this scientific core.

## 8. Testing strategy

Tests should include:

- 0 °C equals exactly 100 Ω
- representative negative temperatures
- representative positive temperatures
- round-trip temperature → resistance → temperature
- round-trip resistance → temperature → resistance
- boundary values
- invalid input
- non-finite values
- monotonicity across the supported range
- known IEC reference-table values

Round-trip tests alone are insufficient because the forward and inverse implementations could share the same error. At least some expected values must come from an independent reference source.

## 9. Accuracy boundaries

The built-in Pt100, Pt500, and Pt1000 conversion functions describe the ideal standardized IEC curve. The advanced model APIs can represent an individually characterized `R0`, a traceable custom Callendar–Van Dusen coefficient set, or a separately sourced polynomial RTD characteristic. `rtd_sensor.tolerance` currently calculates the numerical IEC platinum class limit. These layers remain distinct: none of them, by themselves, establishes the total measurement accuracy of a physical installation.

Effects that remain outside nominal curve conversion include:

- whether a physical sensor actually conforms to its stated tolerance class;
- calibration uncertainty and residual calibration error;
- lead-wire resistance not removed by the acquisition system;
- self-heating;
- excitation-current error;
- amplifier offset or gain;
- ADC quantization;
- reference-resistor tolerance;
- thermal gradients;
- immersion depth; and
- response time.

Hardware-facing acquisition code should correct applicable electrical effects before passing resistance into this package. Characterized or calibrated curve parameters may be represented with the public model APIs. Statistical combination of remaining uncertainty contributions belongs to the separate uncertainty layer.

### RTD uncertainty-budget model

The uncertainty layer uses the same RTD model for both the nominal resistance-to-temperature conversion and the exact local inverse sensitivity `dT/dR`. A resistance standard uncertainty `u(R)` is propagated with the first-order relationship:

```text
u(T)_R = |dT/dR| × u(R)
```

The resulting resistance contribution remains visible in the returned result rather than being collapsed into an anonymous total. Additional uncertainty contributions may be supplied only after the caller has expressed them as standard uncertainties in °C. Each such component may retain a name, Type A/Type B evaluation-method label, source, and note for auditability.

The current structured budget combines the resistance contribution and additional temperature-domain components as uncorrelated terms by root-sum-square. This is intentionally narrower than the full GUM law of propagation: covariance and correlation terms are not silently assumed to be zero when they are known to matter. Instead, covariance-aware propagation remains a deferred capability.

IEC tolerance values remain separate from uncertainty. A caller may choose to model a tolerance bound as an uncertainty component only after explicitly selecting and documenting a probability-distribution assumption. The library must not infer such a distribution from the tolerance class itself.

Expanded uncertainty is optional and requires an explicit coverage factor. The result retains that factor and does not infer a confidence level from it.

First-order propagation is a local linearization. For sufficiently large input uncertainties, strongly nonlinear regions, or uncertainty in correlated calibration coefficients, a distribution-propagation method such as Monte Carlo analysis may be more appropriate and remains future work.

## 10. Package structure

Current structure:

```
src/rtd_sensor/
├── __init__.py
├── _curves.py
├── _models.py
├── _validation.py
├── measurement.py
├── models.py
├── ni1000.py
├── ni1000_tk5000.py
├── ni120.py
├── pt100.py
├── pt500.py
├── pt1000.py
├── simulation.py
├── tolerance.py
└── uncertainty.py

tests/
├── test_boundary_roundtrips.py
├── test_custom_cvd_models.py
├── test_measurement.py
├── test_models.py
├── test_ni1000.py
├── test_ni1000_tk5000.py
├── test_ni120.py
├── test_numeric_input_validation.py
├── test_package_api.py
├── test_piecewise_polynomial_models.py
├── test_polynomial_models.py
├── test_pt100.py
├── test_pt500.py
├── test_pt1000.py
├── test_public_models.py
├── test_simulation.py
├── test_tolerance.py
├── test_uncertainty.py
└── test_uncertainty_budget.py
```

## 11. Repository and namespace strategy

The project began as the `pt100-core` distribution and repository because its initial scope was Pt100 conversion. Releases through 0.3.x used the Python import package `rtd`.

Beginning with 0.4.0, the project identity is:

```text
PyPI distribution:  rtd-sensor
Python import:       rtd_sensor
GitHub repository:   rtd-sensor
```

The corresponding public import is therefore:

```python
from rtd_sensor import pt100
```

The import-package rename is intentional. Version 0.4.0 does not ship an `rtd` compatibility package, so the historical ambiguous namespace does not become a permanent compatibility burden. Existing `pt100-core` releases remain part of the historical release line, and migration from 0.3.x requires updating imports from `rtd` to `rtd_sensor`. The README contains the user-facing migration instructions.

The detailed feature sequence is tracked in [`ROADMAP.md`](ROADMAP.md).


## 12. Generalized RTD architecture and future support

The conversion architecture separates a normalized resistance-temperature characteristic from the resistance used to scale that characteristic.

A general curve describes:

```text
R(T) / Rref
```

where `Rref` is the resistance at the curve's explicit reference temperature `Tref`. For the IEC 60751 platinum characteristic, `Tref = 0 °C` and `Rref` is the traditional `R0`. Keeping the reference temperature explicit avoids baking the 0 °C convention into the generic RTD layer and leaves room for future characteristics referenced at another temperature.

An RTD model combines:

* a normalized characteristic;
* a reference resistance (`Rref`);
* the characteristic's reference temperature (`Tref`);
* an optional built-in model identity, where applicable.

This permits multiple RTD models to share one verified characteristic without duplicating conversion logic. Verified package built-ins carry a stable string identity used by simulation; ad hoc/custom internal models do not become built-ins merely by having conversion behavior.

Built-in scientific definitions are centralized as immutable internal metadata. The characteristic ID, curve kind, source coefficients or segments, reference temperature, range, provenance, model ID, and reference resistance are defined once; the runtime curve and model registries are constructed from those definitions. Runtime-derived values such as piecewise continuity adjustments remain separate from the source coefficients that authorized them. The same definition layer backs the stable language-neutral conformance artifacts and the public read-only `rtd_sensor.catalog` discovery metadata without creating parallel sources of truth. The catalog returns cached protocol-compatible adapters and frozen application-facing descriptors while keeping the concrete runtime models, construction machinery, and internal registry mappings private.

The implementation defines the IEC 60751 PT-385 Callendar–Van Dusen curve once and combines it with model-specific `R0` values. Pt100 uses `R0 = 100 Ω`, Pt500 uses `R0 = 500 Ω`, and Pt1000 uses `R0 = 1000 Ω`.

The low-level curve and model infrastructure remains internal. Public modules should therefore reference internal singletons through private/module-qualified names rather than exposing those implementation objects as accidental module attributes. Public wrappers expose the supported configurable and calibrated-model capabilities without making the internal numerical abstractions part of the compatibility contract.


### Public configurable and calibrated models

The public advanced-model API has five deliberately distinct levels.

`rtd_sensor.models.IEC60751RTDModel` represents an RTD that retains the standardized IEC 60751 PT-385 curve while allowing:

* an individually characterized or calibrated `R0`;
* a human-readable model or probe name; and
* a declared valid temperature range that may be narrower than the full IEC curve.

The built-in `rtd_sensor.pt100`, `rtd_sensor.pt500`, and `rtd_sensor.pt1000` modules remain the preferred APIs for nominal standard sensors. `IEC60751RTDModel` is for cases where an individual probe's `R0` is known more precisely or its usable/calibrated range should be enforced. A declared range constrains use of the model; it does not modify the underlying IEC curve.

`rtd_sensor.models.CallendarVanDusenRTDModel` represents a **platinum RTD** for which a calibration certificate, manufacturer, or other traceable technical source provides an IEC-style `R0`, `A`, `B`, `C` Callendar–Van Dusen coefficient set. It requires an explicit valid temperature range because custom coefficients have no package-defined universal range.

Callendar–Van Dusen is intentionally a platinum-specific abstraction in this package. Nickel, copper, and other non-platinum characteristics must not be forced into `CallendarVanDusenRTDModel` merely because their published resistance-temperature relationship is polynomial. They should use `PolynomialRTDModel`, `PiecewisePolynomialRTDModel`, or `TabulatedRTDModel`, whichever representation faithfully matches the source definition.

The custom-CVD model follows these rules:

* `R0`, `A`, and `B` are required;
* `C` is required when the declared range includes temperatures below 0 °C and may be omitted for a wholly non-negative range;
* all numerical inputs must be finite and `R0` must be positive;
* the supplied coefficients must define a finite, positive-resistance, strictly increasing curve over exactly the declared validity interval;
* `R0` remains the equation's reference resistance at 0 °C, but that reference point does not silently widen a positive-only or negative-only validity interval; behavior outside the traceable interval is deliberately neither validated nor accepted for conversion;
* the declared range is enforced in both conversion directions; and
* optional `coefficient_source` metadata may retain a calibration-certificate identifier, manufacturer document, or other provenance label.

A user-supplied coefficient set is not automatically described as IEC 60751 compliant merely because it uses the same algebraic form. The standard `IEC60751RTDModel` remains the explicit API for the package's verified IEC PT-385 curve.

Version 0.6.0 adds polynomial calibration fitting from raw `(temperature, resistance)` observations. It does not fit `R0`, `A`, `B`, or `C` for characterized-standard or custom Callendar–Van Dusen models; those remain configurable inputs. Historical `R0`, alpha, delta, beta coefficient notation and ITS-90 interpolation functions remain outside the current public API.

### Calibration fitting and portable model definitions

Calibration fitting must remain scientifically distinct from using a published or
otherwise supplied model. A fitting operation should produce two related but
separate results:

1. **fit evidence**, retaining the observations, residuals, fitting diagnostics,
   RMS and maximum error, fitting range, weighting or calibration-point uncertainty
   when supplied, and the assumptions needed to reproduce the fit; and
2. a **numerical model definition** that can be reconstructed and used without
   rerunning the fit.

The deployable model definition is not a replacement for the fit evidence.
Conversely, a downstream process, laboratory instrument, data logger, C/C++
program, or embedded controller should not need the original observations or
fitting implementation merely to reproduce the already accepted fitted curve.

#### 0.6.0 fitting scope and failure semantics

The initial fitting scope is polynomial fitting from `(temperature, resistance)`
observations using a caller-selected polynomial degree. Characterized-reference-
resistance models remain configurable inputs in 0.6.0; fitting an `R0`-only model
is not required by the initial fitting milestone. If an `R0`-only fitter is added
later, its deployable result must use the same characterized-standard-
characteristic representation as `IEC60751RTDModel`, not a parallel model kind.

The initial public fitting layer is `rtd_sensor.fitting`. It treats temperature as
the independent variable and resistance as the fitted dependent variable. A
resistance standard uncertainty may therefore weight resistance residuals, but the
initial ordinary least-squares model does not represent temperature uncertainty or
perform errors-in-variables regression.

A fitting call is successful only when both the numerical fit and the resulting
RTD model are scientifically usable over the declared fitted range. The initial
contract therefore follows these rules:

* temperatures and resistances must be finite and resistances must be positive;
* the requested polynomial degree must be valid and the observations must contain
  at least `degree + 1` **distinct** temperature values;
* repeated observations at the same temperature are allowed as independent
  measurements, are retained in the fit evidence, and are never silently averaged
  or discarded;
* rank-deficient systems and non-finite numerical solutions are fitting failures;
* the observed temperature span is linearly scaled to `[-1, 1]` before fitting and
  the least-squares system is solved by Householder QR rather than by forming normal
  equations;
* fit evidence retains the scaling center/half-range and the infinity-norm condition
  number of the resulting Householder `R` factor; the initial guardrail rejects a
  scaled-system condition number above `1e10`; this threshold is a numerical
  stability guardrail, not an accuracy guarantee, and regression coverage must keep
  both well-spaced high-degree systems and deliberately clustered pathological
  systems on the intended sides of the boundary;
* the fitted candidate must satisfy the same finite, positive-resistance, strictly
  increasing, unique-inverse requirements as a directly constructed polynomial
  model over the complete declared range; if it does not, the fitting operation
  fails and no deployable model is returned; and
* the initial fitted validity interval may not silently extend beyond the observed
  temperature span. A caller may narrow the range, but unvalidated extrapolation is
  not part of the initial fitting API.

Package-owned fitting failures such as insufficient independent observations,
rank deficiency, rejected ill-conditioning, or a scientifically invalid fitted
curve should use a dedicated fit-domain exception rather than overloading
`InvalidRTDModelError` with failures that occur before a valid model exists. The
implementation should add a small `RTDFitError` under the existing `RTDError` /
`ValueError` compatibility pattern. Ordinary type-category mistakes remain
`TypeError`, and ordinary malformed scalar inputs retain the package's established
`ValueError` behavior. Fitting is not currently a conformance-v1 conversion
capability, so these Python fitting failures do not redefine the language-neutral
conversion status `calculation_failure`.

Residuals are always retained in physical resistance units. RMS residual error and
maximum absolute residual error are reported unweighted so they remain directly
interpretable even when weighting is used. When caller-supplied weights or
resistance standard uncertainties influence the fit, the corresponding weighted
objective/statistic is retained **in addition to**, not instead of, the unweighted
diagnostics. A fit is either wholly unweighted, uses an explicit positive relative
weight for every observation, or uses a positive resistance standard uncertainty
for every observation; weighting conventions are not mixed within one fit. Effective
weights are normalized so the largest is `1.0`, which leaves the least-squares
solution unchanged while avoiding arbitrary overall scale. Standard uncertainties
are converted to normalized inverse-variance weights proportional to `1 / u²`, and
the original observations plus effective weights are retained so the objective is
reproducible.

The reported unweighted RMS residual is the descriptive quantity
`sqrt(sum(residual²) / observation_count)`, not a degrees-of-freedom-adjusted
estimate of residual standard deviation. Fit evidence therefore also records the
observation count, fitted-parameter count (`degree + 1`), and residual degrees of
freedom. A saturated fit with zero residual degrees of freedom can interpolate its
observations nearly exactly; a small RMS or maximum residual in that case must not be
interpreted by itself as evidence of predictive quality or freedom from overfitting.
The weighted RMS is likewise a descriptive weighted residual measure normalized by
total effective weight. The 0.7.0 diagnostics add
`chi_squared = sum((residual/u_R)^2)` for fits whose observations all provide
absolute resistance standard uncertainties and, when residual degrees of freedom
are positive, `reduced_chi_squared = chi_squared / dof`. These are residual-consistency
diagnostics under the stated independent resistance-uncertainty model, not automatic
fit-acceptance thresholds and not substitutes for a complete calibration uncertainty
budget. Relative/manual weights have no absolute variance scale, so they do not
produce these chi-square diagnostics.

The fitted `PolynomialRTDModel` uses the midpoint of the declared fitted validity
range as its reference temperature. This is a deterministic numerical anchor, not a
claim that a calibration observation exists at that exact temperature.

#### 0.7.0 characterized-reference-resistance fitting

The first 0.7.0 fitting milestone estimates only `R0` while holding the verified
IEC 60751 PT-385 normalized characteristic fixed. The public entry point is
`rtd_sensor.fitting.fit_iec60751_r0()`. For observations `(T_i, R_i)`, the
model is linear in the single fitted parameter:

```text
R_i = R0 × rho_IEC(T_i)
```

where `rho_IEC(T)` is the package's existing normalized IEC characteristic.
The fitter therefore uses the closed-form one-parameter least-squares solution
rather than introducing a second numerical optimizer. Explicit relative weights
and resistance standard uncertainties use the same normalized weighting
conventions as `fit_polynomial()`. Temperature remains the independent variable;
this milestone does not reinterpret reference-temperature uncertainty as resistance
uncertainty or implement an errors-in-variables fit.

The result must reuse `IEC60751RTDModel`; fitting `R0` does not create a parallel
calibrated-model kind. Fit evidence remains separate and retains the original
observations, resistance residuals, observation/fitted-parameter/degrees-of-freedom
counts, observation temperature span, declared model range, weighting diagnostics,
and the fitting method. Residuals remain observed resistance minus fitted
resistance.

Range semantics differ deliberately from the polynomial fitter because the
standard characteristic shape is not being inferred from the calibration points.
When at least two distinct calibration temperatures are supplied and no model
range is given, the deployable model defaults to the observed span. A
single-temperature fit can identify `R0`, but it must declare both model range
limits explicitly because no nonzero applicability interval can be inferred from
one temperature. When both limits are explicitly supplied, the declared
applicability range is independent of the observation span: it may be broader,
narrower, or disjoint, but must remain within the supported IEC PT-385 range.
This is intentional because the standard characteristic shape is fixed rather
than inferred from the calibration temperatures. The caller-declared range must
not be presented as evidence that the calibration observations validated
performance throughout that interval.

An `R0` fit establishes only the best-fit reference resistance under the assumed
IEC characteristic and resistance-residual model. It does not establish IEC
tolerance-class conformance, physical sensor accuracy, or calibration validity
outside what the retained evidence and caller-declared range justify.

#### 0.7.0 custom Callendar–Van Dusen fitting and identifiability

The custom-CVD fitting milestone adds
`rtd_sensor.fitting.fit_callendar_van_dusen()`. The caller explicitly names the
subset of `r0_ohms`, `a`, `b`, and `c` to estimate; every parameter not fitted must
be supplied as a fixed value, except `C` may be absent for a wholly non-negative
declared range where the CVD `C` term is unused. This explicit parameter-selection
contract prevents the package from silently fitting an over-parameterized model.

The implementation uses the modern CVD form documented by Pearce et al. (2022),
Appendix 1:

```text
R(T) = R0 [1 + A*T + B*T^2 + C*(T-100)*T^3]   for T < 0 °C
R(T) = R0 [1 + A*T + B*T^2]                    for T >= 0 °C
```

When `R0` is among the fitted parameters, the least-squares problem is solved in
the algebraically linearized parameter basis `(R0, R0*A, R0*B, R0*C)` for the
requested shape coefficients. Fixed shape coefficients are folded into the `R0`
design column. When `R0` is fixed, the requested shape coefficients are linear
directly after multiplication by the fixed `R0`. This is an exact algebraic
reparameterization of the CVD equation; it does not require a generic nonlinear
optimizer.

Identifiability is enforced from the actual calibration design. The requested
parameter count may not exceed the number of distinct calibration temperatures,
fitting `C` requires at least one negative-temperature observation because its
basis function is identically zero at and above 0 °C, and the resulting design
matrix must remain full-rank and below the same severe scaled-system condition
limit used by polynomial fitting. CVD design columns have very different physical
scales (`1`, `T`, `T²`, and a fourth-order negative-temperature term), so each
column is scaled by its largest absolute value before Householder QR. The evidence
retains those scales, the linearized parameter names, and the scaled-system
condition diagnostic so the identifiability decision is inspectable.

Covariance is calculated first in the solved linearized basis. If `R0` and shape
coefficients are jointly fit, public `A`, `B`, or `C` are ratios of fitted product
coefficients to fitted `R0`, so their covariance is transformed with the first-order
Jacobian of `A=(R0*A)/R0`, and likewise for `B` and `C`. The coefficient values
themselves are algebraically exact, but this covariance basis transformation is a
delta-method/first-order propagation. `FitParameterCovariance.parameter_names`
always match the public fitted parameters, and `parameter_transformation` records
the first-order ratio transformation when it was required.
`FitParameterCovariance` also exposes covariance-derived standard uncertainties
and a parameter correlation matrix as read-only diagnostics. Correlations involving
a zero-variance parameter are undefined and are reported as `None`. Strong
parameter correlation is evidence callers can inspect, not a separate acceptance
threshold.

Range semantics depend on what was estimated. If any shape coefficient (`A`, `B`,
or `C`) is fitted, the returned model may be narrowed but not extended beyond the
calibration-observation span because the curve shape itself was inferred from those
data. If only `R0` is fitted while all shape coefficients are fixed from an
independent source, an explicitly supplied applicability range may be broader,
narrower, or disjoint from the observation span, following the characterized-R0
principle already established for the IEC fitter.

A successful CVD fit returns the existing `CallendarVanDusenRTDModel`; fit evidence
remains separate from the numerical model and from portable deployment metadata. A
fitted curve must not acquire IEC, manufacturer, or calibration-laboratory
provenance merely because it uses the CVD algebraic form.

#### 0.7.0 reference-temperature uncertainty and calibration provenance

Calibration/reference-temperature uncertainty is uncertainty in the independent
coordinate of the current resistance-on-temperature regression. It must therefore
remain distinct from resistance uncertainty. Ordinary weighted least squares may
use `standard_uncertainty_ohms` as dependent-variable inverse-variance weights, but
it must not transform a temperature uncertainty into an apparent resistance
uncertainty merely by multiplying by a local slope and then present that as the
same statistical model. NIST calibration work on errors-in-variables regression
(Bartel, Stoudt, & Possolo, 2016) is the implementation/design basis for this
boundary: when uncertainty in the applied/reference independent variable matters,
the regression model itself must account for uncertainty in both coordinates.

`CalibrationObservation.standard_uncertainty_temperature_c` therefore records a
positive standard uncertainty associated with the calibration/reference temperature
coordinate without asserting an independence or cross-observation correlation model.
Current `rtd_sensor.fitting` least-squares operations reject observations carrying
that field by default. A caller that deliberately wants the numerical fit performed
under the existing exact-temperature assumption may select
`temperature_uncertainty_handling="retain_not_used"`. In that mode:

* the supplied temperature uncertainty remains in the immutable observations;
* fit coefficients, residuals, resistance weighting, chi-square diagnostics, and
  parameter covariance are still conditional on treating the supplied temperature
  coordinates as exact;
* the evidence records `temperature_uncertainty_treatment="retained_not_used"`;
* no equivalent resistance uncertainty is synthesized from `dR/dT`; and
* the result must not be described as an errors-in-variables, orthogonal-distance,
  or complete calibration-uncertainty analysis.

This explicit opt-in exists for auditability and transitional workflows, not as a
recommended substitute for a regression model that includes reference-temperature
uncertainty. A future errors-in-variables or generalized calibration method may use
the retained values together with an explicit dependence/correlation model; the
current observation field alone is intentionally insufficient to claim such a model.

Calibration provenance is likewise retained as evidence rather than numerical model
state. `CalibrationProvenance` provides application-neutral optional fields for a
certificate identifier, calibration date, laboratory, reference standard, source
document, and notes. The package trims and validates those textual fields but does
not interpret them as scientific authority. Provenance supplied to a fitter is
retained by the fit evidence and cannot alter coefficients, weights, diagnostics,
valid range, or model behavior. It is not automatically copied into a model's
`coefficient_source` and is not automatically inserted into portable-model metadata.
Callers may separately choose an appropriate portable metadata representation when
they have a downstream provenance contract that justifies doing so.

This preserves four distinct layers: calibration observations and their stated
uncertainties, calibration/fit provenance and diagnostics, the accepted numerical
model, and an optional downstream deployment representation.

#### 0.7.0 fitted-parameter covariance

Fitted-parameter covariance is retained as **fit evidence**, never as part of the
portable deployable model definition. The covariance contract follows the
least-squares assumptions already made by the fitting API: resistance is the
error coordinate being minimized, calibration temperatures are treated as exact
independent-variable values by the numerical fit, and observation errors are
treated as independent unless a later API explicitly represents correlation. When
temperature standard uncertainties are explicitly retained as unmodeled evidence,
this covariance remains conditional on the exact-temperature assumption.

The covariance scale depends on what the observations actually provide:

* for unweighted fits and fits using caller-supplied **relative** weights, the
  common residual-variance scale is unknown and is estimated from the weighted or
  unweighted residual sum of squares divided by the residual degrees of freedom;
  covariance is therefore unavailable when residual degrees of freedom are zero;
* when every observation supplies an absolute resistance
  `standard_uncertainty_ohms`, those values define inverse-variance weights with
  physical scale. Parameter covariance is then obtained from the inverse weighted
  information matrix without rescaling it by the observed residual scatter, and it
  remains available for a saturated fit. A poor weighted residual diagnostic is
  still evidence of model/data inconsistency; it does not silently inflate or
  redefine the supplied measurement uncertainties.

For the one-parameter IEC fit, the covariance parameterization is simply `R0` in
ohms. Custom CVD covariance is retained in the actual fitted subset of the public
`R0`, `A`, `B`, `C` basis after transforming out of the internal linearized product
parameters. Polynomial fitting solves in its numerically scaled power basis, but
the retained covariance is linearly transformed to an unnormalized resistance
power series at the **returned model's reference temperature**:

```text
R(T) = a0 + a1*x + a2*x^2 + ...
x = T - reference_temperature_c
```

Here `a0` is the returned model's `reference_resistance_ohms`, and for `k >= 1`,
`a_k = reference_resistance_ohms * model.coefficients[k - 1]`. Retaining covariance
in this linear resistance-space parameterization avoids implying that the
normalized deployable coefficients were independently fitted and gives later
prediction-uncertainty propagation a direct sensitivity vector `(1, x, x^2, ...)`.

The covariance object records its parameter names, matrix, parameterization, and
estimation method. The enclosing fit evidence records an explicit reason when
covariance is unavailable, including zero residual degrees of freedom when a
residual scale must be estimated or a covariance result that is numerically invalid
(for example, non-finite entries or a negative diagonal variance from floating-point
arithmetic). Parameter covariance is not itself a complete sensor or
measurement uncertainty budget: it represents uncertainty associated with the
fitted parameters under the stated regression assumptions and does not include
reference-temperature uncertainty, systematic calibration effects, sensor drift,
or other components unless they are represented separately by a later model.

This implementation follows the least-squares calibration variance/covariance
treatment in JCGM 100:2008 Appendix H.3, with the NIST/SEMATECH Engineering
Statistics Handbook section 4.1.4.3 retained as corroboration for weighted least
squares and inverse-variance weighting. The 0.7.0 covariance-propagation APIs use
that retained covariance for forward resistance and inverse temperature results.

#### 0.7.0 fitted-covariance resistance propagation

The fitted-covariance resistance API propagates retained fitted-parameter covariance
into **predicted resistance uncertainty** while keeping that contribution separate
from acquisition uncertainty and other measurement-budget components. For a
model prediction ``R(T, theta)``, covariance propagation uses the full covariance
matrix:

```text
u²_fit(R) = J Cov(theta) J^T
```

where ``J`` contains the resistance sensitivity coefficients with respect to the
fitted parameters. This is the correlated-input law of propagation from JCGM
100:2008 sections 5.1-5.2 and NIST Technical Note 1297 Appendix A; covariance
off-diagonal terms must therefore be retained rather than treating the fitted
parameters as independent. For IEC-R0 and polynomial fit-space
parameterizations, resistance is linear in the retained fitted parameters, so
this forward resistance covariance transformation is exact at fixed temperature
under the fit model. For custom CVD covariance retained in the public
`R0`, `A`, `B`, `C` basis, joint fitting of `R0` with shape coefficients makes
the forward relationship nonlinear in that public parameterization; its
propagation is therefore first-order/local.

For an IEC 60751 `R0` fit, ``R(T) = R0 * rho(T)`` and the sensitivity vector is
``(rho(T),)``. For custom CVD fits the vector follows the fitted parameter subset:
``dR/dR0 = R/R0``, ``dR/dA = R0*T``, ``dR/dB = R0*T²``, and below 0 °C
``dR/dC = R0*(T-100)*T³`` (zero at and above 0 °C). For a polynomial fit whose
covariance is retained in the resistance-space basis at the returned model
reference temperature, ``x = T - reference_temperature_c`` and the sensitivity
vector is directly ``(1, x, x², ...)``. The propagation API records that vector
alongside the covariance object, propagated variance in ohm², and standard
uncertainty in ohms so the calculation remains auditable.

Propagation is available only when the fit evidence actually contains parameter
covariance. A fit that succeeded without estimable covariance remains a valid fit,
but requesting covariance propagation from it fails explicitly and preserves the
fit evidence's unavailability reason. Model temperature-range checks continue to
apply.

This result is intentionally **not** inserted automatically into
``temperature_uncertainty_budget()``. Fitted-model uncertainty, uncertainty in a
subsequent resistance measurement, reference-temperature uncertainty, drift,
self-heating, tolerance assumptions, and other effects can have different sources
and possible dependence relationships. Automatically combining them would assert
independence that the package cannot generally know. The resistance-domain result
therefore remains a separate inspectable contribution.

#### 0.7.0 fitted-covariance temperature propagation

Fitted-parameter covariance can also be propagated into the temperature inferred
from a fixed resistance measurement. This is a different mathematical case from
the forward resistance result. Let the fitted model satisfy
``R_model(T, theta) = R_measured``. Implicit differentiation with the measured
resistance held fixed gives

```text
dT/dtheta = -(dR/dtheta) * (dT/dR)
```

where ``dR/dtheta`` is the same fitted-parameter resistance sensitivity vector
used by the forward propagation milestone and ``dT/dR`` is the model's local
inverse RTD sensitivity at the inferred temperature. The resulting parameter
sensitivity vector is propagated through the full retained covariance matrix:

```text
u²_fit(T) = J_T Cov(theta) J_T^T
```

Unlike the forward resistance transformation for the currently supported
linear-in-parameter representations, inferred temperature is generally nonlinear
in the fitted parameters. This result is therefore explicitly a **first-order
local linearization** around the fitted model and converted temperature. The
measured resistance is treated as fixed; uncertainty in that resistance is not
silently added to the fitted-model contribution.

The public result retains the fixed resistance, inferred temperature, covariance
object, resistance-parameter sensitivity vector, local ``dT/dR`` sensitivity,
temperature-parameter sensitivity vector, propagated variance in °C², and standard
uncertainty in °C. This keeps the implicit sensitivity calculation inspectable and
makes the distinction from a complete measurement uncertainty budget explicit.

The same separation rule as the resistance-side milestone applies: this fitted-
model contribution is not automatically inserted into
``temperature_uncertainty_budget()``. A later caller may combine fitted-model,
resistance-measurement, reference-temperature, drift, self-heating, and other
effects only when their provenance and dependence assumptions justify that
combination. JCGM 100:2008 sections 5.1-5.2 and NIST Technical Note 1297 Appendix A
remain the implementation basis for this first-order covariance propagation.

#### 0.8.0 self-heating and zero-power extrapolation

Self-heating remains separate from nominal RTD curve conversion. The public
``rtd_sensor.self_heating`` analysis layer consumes caller-supplied steady-state
measurement-current/resistance observations; it does not control excitation
current, bridges, ADCs, MAX31865 devices, or other acquisition hardware.

The first 0.8.0 implementation uses the BIPM/CCT two-current model

```text
R(i) = R0 + k * i^2
```

under the caller's assumption that both observations represent the same stable
external thermal condition. ``SelfHeatingObservation`` therefore records a
positive measurement-current magnitude in amperes and a positive measured
resistance in ohms. Observation-level ``I^2`` and ``I^2 R`` quantities remain
inspectable, while the standard two-current extrapolation uses resistance versus
current squared as documented by the retained metrology guidance.

Two distinct current levels exactly determine the line and therefore provide zero
residual degrees of freedom. ``TwoCurrentZeroPowerResult`` exposes the extrapolated
zero-power resistance while ``TwoCurrentZeroPowerEvidence`` retains the normalized
low/high-current observations, current ratio, current-squared span, resistance
change, slope, method identity, and zero residual degrees of freedom. A zero or
negative observed resistance change is retained as evidence rather than silently
reinterpreted as proof of a valid physical self-heating correction. With two
points alone the package cannot establish experimental stability or test linearity.

The temperature-composition step applies one explicitly supplied RTD model to
the zero-power resistance and both retained observed resistances. It reports the
corresponding zero-power temperature and each observed temperature rise relative
to that inferred zero-current state, and retains the exact supplied model object
with the temperature result. Model conversion and range errors propagate unchanged,
and the result does not independently establish ambient temperature.

Two-current measurement uncertainty is propagated from the original four inputs
(``I_low``, ``R_low``, ``I_high``, ``R_high``) with a first-order local
linearization. The public result retains the standard uncertainties, fixed input
order, sensitivity vectors, propagated variances, and standard uncertainties.
Current uncertainty is included because the extrapolated intercept depends on the
current-squared coordinates as well as on the measured resistances. As a local
first-order approximation, this propagation assumes the supplied uncertainties are
small enough for the linearization to remain meaningful; current uncertainty large
relative to the separation between the two current levels requires more careful
treatment.

The temperature-side propagation uses the local ``dT/dR`` sensitivity supplied by
the exact RTD model retained in the temperature result. Temperature-rise
uncertainties are propagated directly from the original four inputs rather than by
combining already-derived observed and zero-power temperatures as if they were
independent; those quantities share resistance observations by construction.

The four supplied standard uncertainty magnitudes are treated as mutually
independent by default. When dependence is known, callers may additionally supply a
4 x 4 `TwoCurrentInputCorrelationMatrix` in the same fixed input order. The matrix
must be finite, symmetric, positive semidefinite, and have unit diagonal. It is
combined with the supplied standard uncertainties to form the full covariance
matrix, and propagation uses the correlated-input form `u²(y) = J Cov(x) Jᵀ`. The
result retains the correlation object, exposes the covariance matrix actually used,
and records whether propagation used independent or correlated inputs.

Correlation is never inferred merely because readings share an instrument,
calibration, current source, bridge, or measurement sequence; the caller must have
a defensible covariance/correlation model. Fitted-model covariance and other
uncertainty-budget components also remain separate rather than being combined
automatically. JCGM 100:2008 sections 5.1-5.2 are the implementation basis for
both the independent and correlated first-order propagation.

The larger-observation fit keeps the same scientific model rather than changing
to a regression on observation-level `I^2 R` power. `fit_zero_power_resistance()`
requires at least three observations and two numerically distinct current levels.
By default it performs unweighted ordinary least squares of resistance versus
current squared. Callers may instead supply one absolute resistance standard
uncertainty for every observation; the fit then uses inverse-variance weighted
least squares with weights proportional to `1/u(R)^2`. In both cases the sampled
current-squared coordinates are treated as fixed/exact. Repeated measurements at
only two current levels are valid, which supports low/high measurement cycles while
providing positive residual degrees of freedom.

The evidence preserves caller order and reports every residual, descriptive RMS
residual, maximum absolute residual, residual standard deviation, observation and
distinct-current counts, and sampled current span. For uncertainty-weighted fits it
also retains the supplied resistance standard uncertainties, normalized effective
weights, weighted RMS residual, chi-square, and reduced chi-square. Normalizing the
weights changes neither the fitted line nor the relative influence of observations;
the original absolute uncertainties remain retained so covariance and chi-square
keep their physical scale. A zero or negative fitted slope is retained as evidence
rather than silently converted into a physical self-heating claim.

Those residual diagnostics can expose scatter or inconsistency with the fitted
linear relation, but they cannot by themselves prove thermal stability or identify
the physical cause of a poor fit. The implementation therefore does not invent a
universal residual or reduced-chi-square acceptance threshold. Supplied resistance
uncertainties are used only when the caller explicitly provides a complete positive
set; they are never inferred from replicate scatter or other acquisition context.

For an unweighted fit with positive residual degrees of freedom,
``estimate_zero_power_fit_uncertainty()`` estimates covariance of the fitted
zero-power resistance and ``dR/d(I^2)`` slope from the residual variance. This is
the ordinary-least-squares parameter-covariance model: resistance-domain errors
about the linear model are assumed independent and zero-mean with a common unknown
variance, estimated from the fitted residuals as
``SSE / residual_degrees_of_freedom``.

For an inverse-variance weighted fit, the supplied resistance standard
uncertainties are instead treated as absolute independent response uncertainties.
The fitted-parameter covariance is the corresponding weighted information-matrix
inverse and is **not** multiplied by reduced chi-square or otherwise rescaled to
make the observed scatter agree with the supplied uncertainties. Consequently an
exact fitted line can have zero chi-square residual while still retaining nonzero
parameter covariance. The public uncertainty result records which covariance model
was used; its ``residual_variance_ohms_squared`` is present only for the residual-
scatter ordinary-least-squares path.

When measurement-current standard uncertainties are supplied together with
resistance standard uncertainties for every observation, the 3+ observation fitter
uses York errors-in-variables regression rather than fixed-coordinate least
squares. The measured current magnitude is the supplied independent quantity, while
the fitted coordinate is ``I²``; current uncertainty is therefore propagated to the
fit coordinate by the first-order relation ``u(I²) = 2 I u(I)``. This is an explicit
local linearization of the coordinate transformation, not a claim that squared
current is normally distributed for arbitrarily large relative current uncertainty.

The York path also accepts an optional correlation coefficient for the current and
resistance errors of each observation. Since all accepted measurement currents are
positive, the first-order transformation from ``I`` to ``I²`` has positive
derivative and preserves that within-observation correlation coefficient. Omitting
the coefficients records zero within-observation correlation. York weights depend
on the fitted slope and both coordinate uncertainties, so the solver iterates to a
converged slope. Its chi-square uses the final combined coordinate-error model, and
its fitted intercept/slope covariance is obtained from the York adjusted
coordinates and supplied absolute uncertainties without residual rescaling.

This errors-in-variables path still treats separate observations as statistically
independent. Shared bridge calibration, resistance-reference effects, drift, or
other common influences can instead be represented in the fixed-current case by an
explicit full resistance covariance matrix. When such a positive-definite matrix is
supplied, the fitter uses generalized least squares (GLS), minimizing
``rᵀ V⁻¹ r`` and obtaining parameter covariance from
``(Xᵀ V⁻¹ X)⁻¹``. A diagonal covariance therefore reduces to the existing
inverse-variance weighted fit. The covariance matrix is treated as an absolute
measurement model and is not rescaled by reduced chi-square.

The GLS matrix must be positive definite and numerically invertible. Singular
positive-semidefinite models, such as an exactly common-mode uncertainty with no
independent component, are not pseudo-inverted because their null-space constraints
require a more explicit source/constrained model. Because the full matrix already
contains the marginal resistance variances, the GLS path cannot be combined with
separate resistance standard uncertainties. It also cannot be combined with
measurement-current uncertainty or York within-observation correlations; a model
with covariance across observations *and* errors in the current coordinate is a more
general correlated measurement-error problem. No covariance structure is inferred
from replicate scatter, instrument identity, or marginal standard uncertainties.

The 3+ observation fit can also be interpreted through one explicitly supplied
RTD model without changing the resistance-domain fit. The result converts the
fitted zero-power resistance, each observed resistance, and each fitted resistance
at the sampled current coordinates. It retains observed and fitted temperature
rises separately and reports both measured ``I²R_observed`` power and fitted
``I²R_fitted`` power in caller observation order. These power/temperature pairs are
experimental evidence; they are not automatically labeled as a transferable
self-heating coefficient or dissipation constant.

The retained intercept/slope covariance can be propagated through the same model
into the fitted zero-power temperature and fitted temperature rises. It may come
from residual-scatter ordinary least squares, supplied absolute resistance standard
uncertainties in the weighted fit, a supplied cross-observation resistance covariance
matrix in the GLS fit, or the supplied two-coordinate uncertainty model in the York
errors-in-variables fit. At each
sampled ``x = I²``, the fitted resistance sensitivity to ``(R0, k)`` is ``(1, x)``.
The temperature sensitivity vector is therefore the local ``dT/dR`` multiplied by
``(1, x)``, while the temperature-rise vector subtracts the corresponding
zero-power sensitivity before applying the full 2 x 2 covariance matrix. This
preserves the shared fitted intercept and its covariance with slope rather than
combining derived temperatures as independent quantities. The propagation remains
first-order/local and treats the RTD model itself as fixed.

For 3+ observation characterization, optional ``SelfHeatingExperimentContext``
provenance can be retained with the fit evidence. Its ``medium``,
``flow_condition``, ``mounting``, ``setup``, and ``notes`` fields are deliberately
non-behavioral: they do not change the least-squares result or RTD model. At least
one environmental descriptor other than notes is required when a context object is
created. This keeps the conditions that influence heat transfer attached to the
measurement evidence without turning them into RTD characteristic identity.

A named self-heating coefficient is intentionally available only from a 3+
observation temperature result whose fit retained that context and whose resistance-versus-
current-squared slope is positive. At each numerically distinct sampled current
level, the implementation uses the fitted temperature rise and fitted ``I²R``
power. Repeated observations at one current level affect the underlying unweighted
resistance fit but are represented only once in the secondary coefficient
calculation, avoiding an extra coefficient weight caused solely by replicate count.
The scalar coefficient is the through-origin least-squares slope

```text
ΔT = C_self * P
```

with ``C_self`` reported in °C/W and °C/mW. Its reciprocal is the dissipation
constant in W/°C and mW/°C. This scalar is explicitly a **finite-range**
description of the sampled fitted relationship, not the zero-power differential
``d(ΔT)/dP``. Even when ``R = R0 + kI²`` is exact, fitted power is
``P = I²(R0 + kI²)``; the ``kI⁴`` term means pointwise ``ΔT/P`` can change across
the sampled current range without measurement noise or RTD-model curvature. The
result therefore retains the distinct current-squared levels, fitted powers, fitted
temperature rises, pointwise ``ΔT/P`` values, and coefficient-fit residuals. The
residual RMS and maximum absolute residual are descriptive shape diagnostics of the
fitted ``ΔT``-versus-power relationship, not a second statistical residual-variance
estimate. No universal residual threshold is imposed; those diagnostics remain
available so callers can judge whether one scalar adequately describes their
sampled range and setup. The coefficient is local to the fitted zero-power
temperature and sampled power/current range as well as the retained thermal
environment; it is not assumed to transfer unchanged across temperature. A zero or
negative resistance slope remains valid fit evidence but is not promoted into a
named positive self-heating coefficient. The two-current path remains available for
zero-power correction and temperature-rise analysis, but its zero residual degrees
of freedom are not promoted into this named characterization result.

The scalar coefficient is a deterministic function of the retained fitted
``(R0, k)`` parameters and supplied RTD model. Its first-order uncertainty therefore
propagates the full residual-scatter intercept/slope covariance through both fitted
temperature rise and fitted power. The reciprocal dissipation-constant uncertainty
is propagated from the same parameter sensitivities. This uncertainty describes
only covariance of the retained **finite-range coefficient** under the retained
fixed-current OLS/WLS/GLS fit model; it
does not quantify the deterministic difference between that scalar and a zero-power
differential coefficient or another coefficient definition. Coefficient-fit
residual scatter, RTD-model parameter covariance, current-coordinate uncertainty,
correlated experimental effects, and uncertainty in the environmental description
are also not silently added. An exact resistance fit can therefore still produce
zero covariance-derived coefficient uncertainty without implying that the physical
self-heating behavior is known exactly or is range-independent.

`assess_zero_power_extrapolation()` adds a threshold-free evidence assessment to
both the two-current and 3+ observation result paths. It does not declare an
experiment "stable" or "unstable" and does not emit Python runtime warnings.
Instead, it reports structured warning codes for objective limitations that follow
directly from the retained evidence: two points have no residual check; a larger fit
with only two distinct current levels cannot test line shape across three or more
levels; a fit with no repeated current level cannot assess within-level
repeatability; and a zero or negative resistance slope does not show the positive
resistance rise expected for ordinary self-heating.

The same assessment exposes the minimum/maximum current ratio and the distance from
the lowest sampled `I²` point to zero current measured in units of the sampled `I²`
span, `min(I²) / (max(I²) - min(I²))`. These are descriptive geometry/conditioning
metrics only. No universal acceptable current ratio, extrapolation distance, or
residual magnitude is imposed. The BIPM/CCT guidance requires stable external
temperature and steady readings and notes that repeated cycles may be needed when
drift is present; current/resistance observations alone cannot prove those physical
conditions. Experiment-specific acceptance criteria therefore remain a caller or
future statistically justified API concern.

The self-heating layer still does not automatically alter an RTD model or a
general uncertainty budget. The required 0.8.0 regression scope is complete with
OLS, resistance-only WLS, fixed-current GLS for explicit cross-observation
resistance covariance, and York EIV for uncertainty in both fitted coordinates.
No universal residual acceptance criterion is encoded: the retained residual,
chi-square, repeatability, and geometry diagnostics are evidence for a caller's
experiment-specific requirement rather than a package-defined pass/fail rule.

#### Provisional 0.9.0 calibration experiment design

This section records the **provisional scientific and numerical contract** for the
0.9.0 calibration experiment planner. It is intentionally being reviewed before a
public API or production implementation is frozen. The initial implementation is a
planning and analysis layer only: it recommends calibration temperatures and reports
prospective fitted-model uncertainty; it does not control baths, bridges, ADCs,
current sources, GPIO, acquisition hardware, or other experimental equipment.

The initial fitted-model family is the existing polynomial calibration model. A
nominal RTD model is nevertheless required because the design criterion translates
prospective resistance-domain fit uncertainty into local temperature-equivalent
uncertainty. Supplying that scientific model does not weaken the hardware-neutral
boundary: the planner remains acquisition-neutral.

##### Prediction-oriented objective

The primary criterion is a continuous **sensitivity-weighted I-optimal** criterion.
The optimum-design literature is not perfectly uniform about the name: Atkinson
(2015, sections 8-9) notes that designs minimizing average prediction variance over
an integration region are variously called **I-optimal** or **V-optimal**. This
project uses **I-optimal** consistently for the continuous integrated criterion so
it is not confused with the discrete V-optimal terminology used in the NIST
Engineering Statistics Handbook. This is a terminology choice for clarity, not a
claim that ``V-optimal`` is an incorrect name in the broader literature. The same
terminology note should appear in the user-facing calibration-design documentation
and API reference when that planner becomes public.

For a polynomial fit with parameter vector ``theta`` and basis vector ``phi(T)``, let
``C_theta`` be the prospective fitted-parameter covariance. The prospective
resistance-domain fitted-curve variance is

```text
v_R(T) = phi(T)^T C_theta phi(T)
```

For the supplied nominal RTD model, let

```text
s(T) = dT/dR
```

at temperature ``T``. First-order local propagation gives

```text
v_T(T) ~= s(T)^2 v_R(T)
```

where ``v_T(T)`` is the prospective fitted-model contribution to temperature
variance. This is a local first-order model, not a complete calibration uncertainty
budget. In particular, the 0.9.0 criterion does not silently add reference-
temperature uncertainty, resistance acquisition uncertainty outside the supplied
prospective response uncertainties, drift, self-heating, or fitted-model inadequacy.

For a declared fitted operating range ``Omega`` and nonnegative operating-priority
density ``w(T)``, define

```text
W = integral_Omega w(T) dT
```

and

```text
J_T = integral_Omega w(T) s(T)^2 phi(T)^T C_theta phi(T) dT / W
```

``J_T`` has units of °C². Its square root is the **weighted RMS predicted
fitted-curve standard uncertainty** in °C; it is not the weighted arithmetic mean of
local standard uncertainties.

Define the sensitivity-weighted moment matrix

```text
M_T = integral_Omega w(T) s(T)^2 phi(T) phi(T)^T dT / W
```

Then the same criterion is evaluated by the standard trace identity

```text
J_T = trace(C_theta M_T)
```

The moment-matrix form is used because ``M_T`` depends only on the declared operating
priorities, polynomial basis, and frozen nominal-model sensitivity. It can therefore
be constructed once and reused while candidate designs change ``C_theta``. The
criterion is an adaptation of established I-optimal prediction-variance design to
RTD calibration by weighting prediction variance with the local ``dT/dR``
sensitivity required to express the objective in temperature-equivalent units.
Atkinson (2015, equations 24-27) gives the classical average-prediction-variance
integral, its trace rearrangement, and the corresponding model moment matrix;
``rtd-sensor`` adds the RTD-specific ``s(T)^2`` and operating-priority density.
Atkinson, Donev, and Tobias (2007) is the broader primary optimum-design source;
NIST Engineering Statistics Handbook sections 5.5.2 and 5.5.2.1 provide
corroborating candidate-set and model-dependent optimal-design context.

``C_theta`` and ``M_T`` **must use exactly the same polynomial parameter basis and
reference-temperature convention**. The existing fitter solves in a scaled internal
coordinate system for numerical stability and then exposes covariance in the
unnormalized resistance power-series basis

```text
x = T - reference_temperature_c
phi(T) = (1, x, x^2, ...)
```

For one planning request, the common planning reference temperature is fixed at the
midpoint of the complete declared fitted range ``Omega``:

```text
planning_reference_temperature_c = (Omega_min + Omega_max) / 2
```

``M_T`` is constructed once in the corresponding ``x = T -
planning_reference_temperature_c`` basis. Every candidate design's prospective
covariance is transformed into that **same fixed planning basis before it is scored**,
not only after a winning design is selected. The candidate's internal QR scaling
center and half-range still come from that candidate design's actual temperature span,
matching ``fit_polynomial()``'s numerical scaling strategy; the final covariance
re-centering is a separate change of basis.

This deliberately decouples the planning basis from an in-progress design's observed
span. A one-step augmented design may not yet span ``Omega``, but that does not change
the coordinate system in which it is compared with other candidates. Span coverage is
reported separately as feasibility/completion evidence. For a completed design that
does span ``Omega`` and is later fitted with ``Omega`` as its declared fitted range,
the fixed planning reference temperature is exactly the reference-temperature
convention already used by ``fit_polynomial()``.

The prospective covariance builder must therefore make the corresponding
candidate-specific scaled-to-fixed-basis transformation before ``trace(C_theta M_T)``
is evaluated. Combining matrices expressed in different parameterizations would make
the trace criterion meaningless while still producing a superficially plausible
finite number.

The planner does not expose a separate resistance-domain optimization mode in the
initial 0.9.0 public contract. The resistance-domain quantities remain inspectable as
intermediate evidence, while the primary scientific objective is the stated
temperature-equivalent prediction criterion.

##### Prospective covariance and uncertainty assumptions

Prospective covariance is constructed from candidate temperatures, polynomial degree,
and caller-supplied **absolute resistance standard uncertainties**. No measured
resistance values or post-fit residuals exist yet and no ``FitResult`` is fabricated.
The builder reuses the fitter's candidate-span scaling, Householder QR strategy, rank
handling, and covariance machinery so prospective planning and retrospective fitting
have one numerical notion of identifiability and feasibility. After that solve, every
candidate covariance is re-centered into the fixed planning reference basis defined
above; incomplete one-step designs do not substitute their own span midpoint as the
public comparison basis.

Relative weights alone determine information geometry only up to an unknown common
scale. They can therefore rank some designs, but they cannot establish an absolute
prospective covariance or predicted physical standard uncertainty before observations
exist. The primary 0.9.0 planner consequently requires absolute ``u(R)`` inputs rather
than exposing a relative-weight-only public mode.

Planned observations are modeled as **conditionally independent resistance
measurements given their supplied absolute standard uncertainties**. Correlation is
never inferred merely because observations share instrumentation, calibration,
measurement sequence, or environment. The initial planner does not model prospective
cross-observation covariance. Evidence must state this independence assumption and
warn that shared systematic effects can make the true information gain from repeated
measurements smaller than the independent-observation model predicts.

Reference-temperature uncertainty is not folded into candidate ``u(R)`` values and
is not modeled in the initial design criterion. This is consistent with the current
polynomial-fitting contract in which temperature is the independent variable unless a
separate errors-in-variables analysis explicitly says otherwise.

##### Explicit finite candidate set

The core planner receives a finite explicit set of candidate calibration temperatures.
This follows the standard computer-aided design framing in which treatment runs are
chosen from a caller-defined candidate set. The initial 0.9.0 planner does not perform
continuous arbitrary-temperature optimization.

A separate deterministic convenience helper may materialize an explicit candidate
list from a range and spacing. The generated values must be retained as the actual
candidate evidence; no hidden scoring grid may influence a recommendation.

Each candidate temperature is unique and carries the absolute resistance standard
uncertainty anticipated for **one new observation** at that temperature. A convenience
input may broadcast one common standard uncertainty across candidates, but the
materialized evidence remains a per-candidate table. A candidate uncertainty must be
finite and strictly positive. Two entries at exactly the same temperature with
different prospective uncertainties would represent different experimental procedures
or run types and are outside the initial 0.9.0 contract.

Candidate temperatures and the fitted operating range are different concepts. A
candidate may lie outside the region where prediction quality is prioritized when it
is still inside the nominal-sensitivity validity domain. This permits endpoint or
exterior calibration observations to improve a fit whose declared use range is
narrower than the full observed calibration span.

##### Operating-priority density

Operating priorities are a complete ordered non-overlapping piecewise-constant
partition of the entire declared fitted range. Each interval carries a finite
nonnegative **relative importance density per unit temperature**.

A weight of 2 means that prediction variance at each temperature in that interval
contributes twice as strongly to the objective as prediction variance at a
temperature in an interval with weight 1. This density interpretation makes the
objective invariant to harmless subdivision: replacing one interval by two adjacent
intervals with the same weight does not alter ``J_T``.

Only weight ratios matter because the criterion divides by ``W``. Multiplying every
weight by the same positive constant cannot change ``M_T``, ``J_T``, or the selected
design. Interval width still matters. For example, a 10 °C interval with density 2
has total unnormalized priority mass 20, while a 90 °C interval with density 1 has
mass 90.

Zero-weight intervals are permitted as an explicit refinement of the earlier common-
case description that prioritized intervals may simply receive greater positive
weight. A zero-weight interval remains part of the declared fitted range but does not
directly contribute to the optimization objective. This avoids forcing an artificial
tiny positive weight when a caller genuinely does not want one region to drive point
placement. Evidence must make clear that prediction precision there was not directly
optimized.

The priority partition must cover the complete fitted range without gaps or overlaps.
Intervals may touch at boundaries, each interval must have positive width, all
weights must be finite and nonnegative, and at least one interval must have positive
weight. Overlap is rejected rather than assigned additive, replacement, or precedence
semantics. Missing regions are rejected rather than silently interpreted as zero
weight.

The full-range calibration-span requirement is independent of operating weight. Even
if an interior region has zero weight, a complete design intended to support a
declared fitted range must still contain calibration observations whose overall span
brackets that **entire** range, because ``fit_polynomial()`` cannot later declare a
valid fitted range wider than the observed calibration span.

##### Complete-design and next-observation operations

The initial planner answers two distinct scientific questions.

**Complete-design planning** jointly selects a fixed requested number ``N`` of actual
experimental runs from the finite candidate set. The selected experiment is a
multiset of runs, not merely a set of unique temperatures. Joint optimization asks
for the minimum ``J_T`` over the complete admissible design space under the stated
repeat policy.

**Next-observation planning** holds an existing experiment fixed, evaluates every
eligible candidate for exactly one additional run, and returns the candidate or exact
tied candidates with the smallest augmented ``J_T``. Because the finite candidate
list is exhaustively evaluated, the recommendation is globally best among the
supplied admissible one-step augmentations.

Repeated calls to the one-step operation form a **greedy sequential procedure**.
They are not equivalent to joint ``N``-run optimization. In particular, a repeat at
an already informative temperature can be the best immediate improvement even when a
different jointly optimized allocation would be better over several remaining runs.
A caller with several uncommitted runs must not be told that looping the one-step API
solves the joint remainder problem. Joint optimization of several remaining runs
conditional on an already-started experiment is a legitimate future extension and is
not part of the initial 0.9.0 contract. NIST Engineering Statistics Handbook section
5.1.4 supports the broader iterative-experiment context; this project-specific API
still keeps the joint and one-step optimization questions distinct.

Execution ordering of a jointly selected fixed set is also a separate problem. A
caller who fears that an experiment may end early may reasonably want an order that
prioritizes the most useful runs under truncation risk, but that is not the same as
retroactively assigning marginal credit to points in an unordered joint design. Such
execution-order optimization is deferred.

##### Repeat policy and run semantics

``repeat_policy`` is a required input with **no default**. The caller must explicitly
choose whether repeated calibration temperatures are allowed or whether every
selected run must use a distinct candidate temperature. The package does not guess
what ``N`` calibration runs means for this scientific decision, just as it does not
invent a default observation uncertainty.

With repeats allowed, selecting the same candidate multiple times adds multiple rows
to the prospective weighted design matrix; observations are never deduplicated.
Every new run uses that candidate's prospective ``u(R)``. Custom per-temperature
repetition caps are deferred beyond the initial 0.9.0 scope.

Repeated observations can reduce prediction variance while worsening the spread of
the weighted-system singular directions. A repeat is therefore neither preferred nor
penalized by rule of thumb: it competes through ``J_T`` subject to the same numerical
feasibility guardrail as every other design. Repetition cannot replace the
``degree + 1`` distinct temperatures required to identify a degree-``d`` polynomial.

##### Existing observations for one-step planning

An existing completed run is represented for planning by exactly the information that
changes the prospective information geometry:

```text
temperature_c
standard_uncertainty_ohms
```

Measured resistance and fitted residual are deliberately absent. Under the initial
prospective criterion, the realized response value does not change the information
matrix. Requiring it would imply data dependence that the algorithm does not have and
would invite future accidental mixing of model-checking diagnostics into the design
criterion.

Existing repeated runs remain separate entries and may carry different standard
uncertainties. The uncertainty on an existing run is the **best presently justified
caller-supplied absolute standard uncertainty assigned to that completed resistance
observation**. It need not equal the uncertainty anticipated before that observation
was made. The package never derives or revises this value from replicate scatter,
residuals, or acquisition context; the caller explicitly supplies it. Prospective
candidate uncertainty remains a separate assumption and is not inherited from an
existing run at the same temperature.

Adaptive planning in response to surprising realized resistances, residuals,
outliers, apparent model inadequacy, or newly discovered heteroscedasticity is a
legitimate but separate future model-checking capability. The initial planner remains
response-independent.

##### Structural feasibility before scoring

Request feasibility is distinct from design scoring. The planner must fail explicitly
when hard constraints prove that no admissible design can satisfy the request rather
than returning a best-effort design that violates the declared experiment.

For complete-design planning, preflight includes at least:

- the candidate set's overall span must bracket the complete declared fitted range;
- the requested run count must be sufficient for ``degree + 1`` distinct-temperature
  identifiability;
- the candidate set must itself contain at least ``degree + 1`` temperatures;
- with distinct-only repeats, ``N`` cannot exceed the number of candidates; and
- there must exist an allowed ``N``-run selection whose span brackets the complete
  fitted range.

The candidate-set span failure diagnostic should name the missing low and/or high
coverage rather than hiding the rule as a search filter.

One-step planning has a separate identifiability precondition. If the existing design
has ``k`` distinct temperatures and the polynomial needs ``d + 1``:

- when ``k < d``, one additional observation cannot make the fit identifiable, so the
  operation fails before scoring and reports the shortfall;
- when ``k == d``, only candidates at genuinely new temperatures can make the
  augmented design identifiable, so repeat candidates are explicitly inadmissible;
- when ``k >= d + 1``, repeat and new candidates may both be considered subject to
  the stated repeat policy and numerical guardrail.

A one-step result also reports whether the augmented design spans the complete fitted
range. An in-progress experiment is allowed not to span it yet; the evidence must not
let one good next point imply that the calibration program is already complete.

Package-owned failures of a planning operation use a dedicated
``RTDExperimentDesignError`` (a public ``RTDError``/``ValueError`` subclass) rather
than ``RTDFitError``: no retrospective fit is being attempted. Invalid scalar/value-
object construction continues to use ordinary ``ValueError`` in the same style as
``CalibrationObservation``. ``RTDExperimentDesignError`` covers structural
infeasibility, inability to obtain an identifiable/numerically admissible planned
design, deterministic quadrature failure, and the exhaustive-search resource limit.
Third-party model exceptions continue to propagate unchanged rather than being
translated into package-owned planning failures.

##### Numerical conditioning

Conditioning is a **numerical feasibility guardrail and diagnostic**, not an
optimization criterion, calibration-quality score, or hidden tie breaker.

The planner reuses exactly the fitter's current conditioning calculation: the
**infinity-norm condition number of the Householder ``R`` factor** from the same
scaled, weighted polynomial system, together with the existing severe-conditioning
limit ``1.0e10``. It must not substitute a 2-norm condition number of the design
matrix or condition the normal/information matrix. The latter would also square the
2-norm condition number and would not reproduce the existing fitter's numerical
contract.

The conditioning calculation intentionally occurs in the fitter's internal scaled
coordinates. This is distinct from the public unnormalized coefficient basis in
which ``C_theta`` and ``M_T`` must agree for ``trace(C_theta M_T)``.

A design that violates the existing fitting guardrail is inadmissible; it does not
receive a large objective penalty and continue competing. For one-step planning,
every candidate is examined and the planner can conclusively report when no supplied
candidate yields an identifiable, numerically acceptable augmentation.

No caller-selected replacement condition threshold is exposed in the initial
planner. Callers may inspect the retained condition number and apply their own
application requirement outside the optimization, but the package does not turn a
condition number into a universal scientific pass/fail quality score.

The ``1.0e10`` guardrail is a **per-design** numerical admissibility test. Evaluating
many candidate designs does not tighten or reinterpret that threshold and does not
turn it into a search-wide accuracy guarantee. Search-wide comparison of numerically
close admissible designs is governed by the separate floating-point evidence and
validation rules below.

##### Diminishing returns

The package quantifies marginal improvement but does not invent a universal stopping
threshold. There is no built-in rule such as "less than 5% improvement means stop."

For an admissible current experiment ``D`` and selected next observation ``T*``:

```text
Delta J_next = J_T(D) - J_T(D + {T*})
```

and the corresponding user-facing RMS reduction is

```text
Delta U_RMS = sqrt(J_T(D)) - sqrt(J_T(D + {T*}))
```

A fractional objective reduction may also be reported when the baseline ``J_T(D)``
is defined and positive. If the current design is rank-deficient or violates the
conditioning guardrail, its baseline prospective covariance is not admissible and no
infinite baseline, percentage improvement, or fabricated marginal value is reported.

For experiment planning from scratch, diminishing returns are represented by a
**run-budget profile**. Complete designs are independently optimized at successive
feasible run counts:

```text
J_N* = min_{|D| = N} J_T(D)
```

and

```text
Delta J_N* = J_N* - J_(N+1)*
```

The ``N + 1`` design need not contain the ``N`` design. A budget profile must not be
constructed by greedily appending a point to the preceding row.

Adding an independent observation contributes a positive-semidefinite information
update. Therefore, whenever two budgets are both globally solved under the same
candidate set and assumptions,

```text
J_(N+1)* <= J_N*
```

More generally, the globally optimal objective cannot increase as additional allowed
runs are added. This Loewner-order monotonicity is a **provable implementation and
test invariant**, not merely a descriptive expectation. An increase beyond the
settled floating-point invariant allowance indicates an implementation or
optimality-status error. Equality is permitted and represents a genuine computed
plateau rather than a requirement that every extra run strictly improve the
criterion.

##### Result and evidence contract

Planning follows the package's existing **small result, rich immutable evidence**
pattern. Evidence retains the complete materialized scientific question and the
numerical state that actually produced the recommendation.

Shared request evidence includes at least:

- fitted model family and polynomial degree;
- complete declared fitted range;
- complete materialized candidate-temperature / prospective-``u(R)`` table;
- complete operating-priority partition with the caller's original weights;
- required repeat policy;
- nominal-sensitivity validity domain and declared breakpoints;
- criterion identity and first-order temperature-equivalent interpretation;
- prospective independence assumption; and
- explicit exclusion of reference-temperature uncertainty from the initial
  criterion.

Complete-design evidence additionally retains requested run count. One-step evidence
instead retains every existing run separately with its caller-supplied current
absolute resistance standard uncertainty.

Criterion evidence for a selected design retains:

- prospective ``C_theta``;
- ``M_T``;
- the common polynomial basis and reference temperature;
- deterministic moment-integration method and error evidence;
- ``J_T``;
- ``sqrt(J_T)`` with its RMS meaning stated explicitly;
- rank and distinct-temperature count;
- selected calibration span and whether it covers the complete fitted range;
- the exact Householder-``R`` infinity-norm condition number and guardrail; and
- the full-range maximum predicted fitted-curve standard uncertainty when that
  maximum can be established analytically under the nominal-model contract.

A complete jointly selected design is an unordered multiset. Its serialized/display
run tuple is canonicalized in ascending temperature order with repeats adjacent. This
canonical order does **not** recommend experiment execution order.

Complete-design evidence retains the winning design and bounded search provenance,
not every losing design or intermediate search step. One-step evidence, by contrast,
retains every candidate augmentation because the comparison is only linear in the
explicit candidate count. Each one-step candidate record identifies whether it is a
repeat or new temperature, admissibility and reason, augmented distinct count and
span status, conditioning when defined, ``J_T`` when admissible, and marginal
improvement when a valid baseline exists. This directly establishes why the returned
candidate was best among the supplied admissible choices.

Measured resistances, residuals, and fictitious fitted coefficients are not retained
as planning evidence because the initial criterion does not use them.

##### Frozen nominal-model evidence

The nominal RTD model may continue to satisfy the package's structural uncertainty-
model protocol rather than inheriting from a package base class. The live model
object is **not authoritative evidence**.

All sensitivity-derived numerical state is computed exactly once at planning time
from the model's state at that moment. ``M_T``, one-sided breakpoint sensitivity
values used by diagnostics, and other criterion-defining model-derived values are
then frozen into immutable evidence and are never lazily recomputed from a retained
live object. If a model reference or identity is kept for display/convenience, it is
explicitly non-authoritative. Mutating a third-party object after planning cannot
change the recommendation or its retained evidence.

For a non-portable third-party model, the frozen numerical evidence can reconstruct
how the model affected the completed criterion even when it cannot reconstruct the
external model's complete physical behavior or provenance.

##### Deterministic floating-point ordering and ties

Designs are ranked by strict ordering of their deterministically computed binary64
``J_T`` values. The planner defines no fuzzy or approximate scientific tie threshold.
Two designs are tied for optimization purposes only when their computed objective
values are exactly equal.

This prevents an arbitrary ``isclose`` tolerance from becoming a hidden practical-
equivalence criterion and avoids non-transitive approximate tie classes. A one-ULP
winner means only that the stated deterministic computation produced a smaller
**computed** objective; it does not imply a practically important experimental
improvement or prove that the exact real-arithmetic objectives are ordered at that
scale. Evidence should therefore retain score separation where practical.

That distinction matters because candidate covariance must be transformed from the
candidate's scaled QR basis into the fixed planning basis. The 0.6.0 independent
polynomial-fitting review measured about ``1.9e-10`` worst-case relative error at
degree 12 for the related point-coefficient binomial re-centering transform. The
covariance transformation uses the same change-of-basis matrix, but its end-to-end
error in ``J_T`` has **not** yet been established and the earlier coefficient result
must not be treated as a bound for covariance scoring. Before implementation is
accepted, a dedicated degree-12 numerical study must compare the production
covariance transformation and resulting ``J_T`` against an independent higher-
precision/reference calculation, including deliberately close candidate scores and
admissible systems near the conditioning guardrail. The measured envelope and margin
become numerical validation evidence; they do not become a fuzzy optimization-tie
threshold.

One-step results retain all exact tied best candidates. If a convenience
representative is needed, the lowest-temperature tied candidate is chosen only as a
canonical representation rule. Complete-design results retain one canonical
lexicographically smallest run tuple and the total number of exactly equal computed
global minima established by exhaustive search. Lower temperature, lower condition
number, smaller maximum uncertainty, fewer repeats, or prettier spacing do not become
hidden secondary optimization criteria.

Caller input order never acts as a tie breaker. Mathematically identical run
multisets are sorted before numerical construction so they follow the same floating-
point evaluation path.

Roundoff tolerances are reserved for numerical consistency and provable-invariant
checks; they do not redefine ranking. For the trace calculation, let the number of
products be

```text
n_terms = (d + 1)^2
```

and compute

```text
absolute_sum = fsum(abs(C_ij * M_ji) for all i, j)
```

The project reuses the cancellation-aware convention already implemented by
``_covariance_quadratic_form``:

```text
tau_J = 8 * n_terms * ulp(absolute_sum)    if absolute_sum > 0
tau_J = 0                                  otherwise
```

The implementation should compute ``J_T`` through one canonical deterministic trace
helper. Re-evaluating that helper over the exact same frozen binary64 matrices is
expected to be bit-identical, so a runtime check of that exact path should require
exact equality. ``tau_J`` is retained only for an audit/invariant path that evaluates
the mathematically identical trace with a deliberately different deterministic
accumulation order or representation. It is not permission for two checks to use
different covariance or moment inputs, and it is not a tolerance for basis-
transformation or quadrature error.

The stronger direct-integral-versus-trace comparison is therefore a test-suite
requirement. Its acceptance budget includes the scalar quadrature error estimate,
the propagated ``M_T`` integration-error contribution, and trace roundoff rather
than asking ``tau_J`` to cover all three effects.

The true globally solved budget curve is non-increasing, but finite-precision QR,
covariance re-centering, moment integration, and trace evaluation can perturb the
computed values by more than ``tau_J`` alone. Before release, the same end-to-end
numerical study required above must establish a fixed documented **budget-
monotonicity invariant allowance** with an explicit margin. That allowance is used
only to test the mathematical monotonicity invariant; it never changes candidate
ranking or exact-tie semantics. An apparent globally solved increase beyond the fixed
end-to-end allowance is an internal invariant failure.

##### Nominal sensitivity domain and structural models

The planner obtains local sensitivity directly from
``temperature_sensitivity_celsius_per_ohm(T)``. It does not finite-difference
``resistance_to_celsius`` or ``celsius_to_resistance``, derive a reciprocal when the
model already supplies the direct sensitivity operation, or inspect arbitrary
third-party private coefficients to manufacture a derivative.

The existing structural model protocol deliberately does not promise model identity,
descriptive metadata, or valid-range discovery. Planning therefore adds an explicit
**nominal-sensitivity validity domain** without expanding that general protocol. The
fitted range and all candidate temperatures must lie inside this declared domain.

Nominal ``dT/dR`` must be finite and strictly positive over the planning domain. For
package-owned models this property is already established by their authoritative
construction/validation logic over the complete supported range. For arbitrary
third-party structural models, the package cannot analytically prove a global
positivity claim from a black-box callable. The caller therefore asserts positivity
and continuity between declared breakpoints; the planner can reject violations it
encounters at evaluated points but cannot guarantee that an undeclared adverse feature
never occurs between them. This limitation must remain explicit in evidence.

Package-owned CVD, global polynomial, piecewise-polynomial, and tabulated models may
all serve as nominal sensitivity models even though the **planned fitted model** in
the initial 0.9.0 feature remains polynomial. The nominal model supplies ``dT/dR``
for the temperature-equivalent objective; it is not necessarily the same
representation being fitted.

At package-owned piecewise-polynomial or tabulated boundaries, the public model
operation follows the existing right-hand-owns-the-boundary convention. Isolated
knot values have zero measure and therefore do not bias ``M_T``. Known formula
boundaries still split the numerical integration so quadrature never knowingly
crosses a sensitivity discontinuity or piecewise change.

For full-range maximum diagnostics, package code uses privileged access to the same
internal segment/table representations that define the package model. It evaluates
the analytical sensitivities of the adjacent pieces **at the shared boundary
directly**. It does not approximate one-sided limits by ``T +/- epsilon`` or
``math.nextafter`` probing. This internal cooperation does not enlarge the public
``RTDModel`` protocol.

For third-party nonsmooth models, declared breakpoint temperatures split the
integration and the package does not infer those boundaries by sampling. The initial
third-party criterion uses only the public
``temperature_sensitivity_celsius_per_ohm(T)`` operation. Because a black-box
third-party model cannot establish the full-range maximum under this contract, the
planner does **not** combine an independently implemented third-party
``resistance_sensitivity_ohms_per_celsius(T)`` with ``dT/dR`` and does not require the
two arbitrary methods to prove reciprocal consistency. Package-owned analytical
models may use their internal ``dR/dT`` representation for the established
full-range maximum because those implementations already define ``dT/dR`` as its
reciprocal. A future third-party analytical-extrema contract would need to specify
that relationship explicitly before it could claim an established maximum.

##### Deterministic moment integration

``M_T`` is constructed with a dependency-free deterministic adaptive **15-point
Gauss / 31-point Kronrod** procedure. This retains the package's no-runtime-
dependency numerical style while using a standard one-dimensional adaptive
quadrature method documented by QUADPACK and the Gauss-Kronrod literature.

Before quadrature, the complete fitted range is split at the union of:

- fitted-range endpoints;
- operating-priority boundaries; and
- declared nominal-sensitivity breakpoints.

Every initial piece therefore has constant priority density and one continuous
nominal-sensitivity branch. Zero-weight intervals contribute exactly zero to ``M_T``
and need not be numerically integrated, though they remain part of full-range
diagnostics.

The 15/31 pair is not an arbitrary high-order choice. The current polynomial fitting
limit is degree 12, so entries of ``phi(T) phi(T)^T`` have degree at most 24. On a
tabulated nominal-model interval, ``s(T)`` and ``w(T)`` are constant. Each moment
integrand is therefore a polynomial of degree at most 24, while a 15-point Gauss
rule is exact through degree 29 in exact arithmetic. The associated 31-point Kronrod
extension has still higher polynomial precision; Rabinowitz (1980) gives degree 47
for the ordinary unweighted ``n = 15`` case. Thus both members of the chosen pair
cover the supported tabulated-interval moment degree in exact arithmetic.

That exactness statement is **limited to tabulated pieces**. For CVD and analytical
polynomial nominal models, ``s(T) = 1 / (dR/dT)`` is generally rational rather than
polynomial, so the moment integrand is not degree-24 polynomial data. Those pieces
are supported by the adaptive 15/31 error-control procedure, not by a claim of exact
Gaussian polynomial integration.

All upper-triangular matrix components are evaluated together on one shared adaptive
subdivision tree. At each quadrature temperature the implementation evaluates
``s(T)`` once, constructs ``phi(T)`` once, and forms the upper triangle of

```text
G(T) = w(T) s(T)^2 phi(T) phi(T)^T
```

The accepted upper triangle is mirrored to make matrix symmetry structural rather
than dependent on independent quadrature runs.

The retained approximation is the 31-point Kronrod result with a QUADPACK-style
adjusted embedded error estimate from the 15/31 pair. For each matrix component on
an accepted leaf, require

```text
E_ij <= 1e-12 * A_ij
```

where ``E_ij`` is the adjusted absolute-error estimate and ``A_ij`` estimates the
integral of ``abs(G_ij(T))`` over that leaf. If ``A_ij`` is zero, the component must
have zero reported integration error. Scaling against the absolute integral avoids a
meaningless relative-error denominator when a signed off-diagonal moment nearly
cancels to zero. ``1e-12`` is a fixed numerical integration target; it is not a
design-equivalence or scientific acceptance threshold.

Using the same local condition on every accepted leaf gives the corresponding global
componentwise bound after summing leaf errors and absolute integrals. Adaptive
subdivision uses deterministic bisection and traversal ordering.

The normalization

```text
W = sum_k weight_k * interval_width_k
```

is evaluated directly from the piecewise-constant priority partition using
``math.fsum``. Quadrature constructs the unnormalized numerator matrix first; both
that matrix and its estimated error are divided by the exactly specified ``W`` to
obtain ``M_T`` and its normalized error evidence.

The integrator has a finite deterministic implementation resource guard. Failure to
meet the fixed numerical target within that budget is a planning failure. The
package does not silently relax the target, change algorithms, or return a
best-effort moment matrix. The exact resource ceiling is a named implementation
constant selected and benchmarked during implementation rather than a scientific
constant frozen in this design document.

Moment evidence retains the method identifier, fixed relative error target,
normalized estimated error matrix, initial structural partition, final accepted
subinterval count, nominal-sensitivity evaluation count, and whether adaptive
subdivision beyond the structural partition was required. It does not retain every
quadrature node or recursion step.

##### Full-range maximum predicted uncertainty

The maximum diagnostic covers the **entire declared fitted range**, including every
zero-weight interval, because its purpose is precisely to reveal a weak region that
the integrated objective may not prioritize.

For one selected design define

```text
q(T) = phi(T)^T C_theta phi(T)
r(T) = dR/dT > 0
v_T(T) = q(T) / r(T)^2
```

Within one smooth package-owned analytical model piece,

```text
dv_T/dT = (q'(T) r(T) - 2 q(T) r'(T)) / r(T)^3
```

so, because ``r(T) > 0``, stationary points are exactly the roots of

```text
h(T) = q'(T) r(T) - 2 q(T) r'(T)
```

For a degree-``d`` fitted polynomial, ``q`` has degree at most ``2d``. For a
nominal polynomial piece of degree ``m``, ``r`` has degree at most ``m - 1`` and
``h`` has degree at most

```text
2d + m - 2
```

which is at most 34 under the current ``d <= 12`` and ``m <= 12`` limits. For a
tabulated nominal model, ``r`` is constant on each table interval and the stationary
condition reduces to ``q'(T) = 0``, degree at most 23. The CVD branches likewise
reduce to bounded-degree polynomial stationary equations because their resistance
slopes are polynomial on each branch.

The implementation must not replace this calculation with a hidden temperature grid.
It reuses the package's existing no-grid polynomial-extrema strategy: recursively
partition derivative-root problems and apply bounded deterministic bisection so a
narrow interior extremum cannot hide between arbitrary sample points. The
stationary polynomial must be constructed in a numerically suitable local coordinate
for each piece rather than unnecessarily expanding high powers of raw Celsius values.
For ``q(x) = phi(x)^T C_theta phi(x)``, its local power coefficient at degree ``k``
is the deterministic anti-diagonal sum of covariance elements with ``i + j = k``;
polynomial differentiation and multiplication then construct ``q' r - 2 q r'`` in
the same local coordinate using cancellation-aware summation where coefficients are
combined.

The existing production root machinery has been exercised for polynomial-model
validation through degree 12, whereas this stationary equation can reach degree 34.
That reuse is therefore conditional on a dedicated top-degree validation probe, not
an assumption that previous degree-12 testing automatically extrapolates. Before the
planner ships, a checked-in independently derived high-precision reference case must
exercise a degree-12 fitted covariance and degree-12 nominal polynomial piece whose
``h`` approaches degree 34, including a numerically difficult but admissible case;
the production roots and resulting maximum must agree with that reference within a
documented numerical envelope.

For every smooth structural piece, the maximum search evaluates ordinary endpoints
and every interior root of ``h``. At declared nonsmooth boundaries it additionally
evaluates both one-sided limiting sensitivities settled above. Final variance values
are evaluated from the frozen covariance quadratic form and authoritative nominal
sensitivity, not from the root-locating polynomial itself. The diagnostic retains

```text
maximum_predicted_standard_uncertainty_c
maximum_location_temperature_c
```

with every exact tied maximum location when more than one exists. The quantity is a
predicted standard uncertainty, not an observed error.

An arbitrary third-party black-box sensitivity model does not provide enough
analytical structure to prove that a narrow interior maximum was not missed. Such a
model may still be used for the integrated ``J_T`` objective under its declared
continuity/breakpoint assumptions, but the full-range maximum status is
``not_established`` unless the package possesses an analytical representation from
which all stationary points can be established. The package does not report the
largest sampled value as a pseudo-worst-case maximum.

##### Exhaustive complete-design search in 0.9.0

The initial 0.9.0 complete-design planner uses **deterministic exhaustive finite
enumeration only**. A non-exhaustive exchange/Fedorov-style search is deliberately
not part of the first public contract. This keeps the meaning of "best complete
design" strong: a successful result establishes the globally minimum computed
``J_T`` over every admissible design in the supplied finite design space.

For ``M`` unique candidate temperatures and ``N`` requested runs, the unfiltered
finite design-space counts are

```text
C(M, N)
```

when repeats are disallowed and

```text
C(M + N - 1, N)
```

when repeats are allowed. These raw counts are useful evidence, but the exhaustive-
search resource ceiling must **not** reject a request merely because the raw multiset
space contains many designs that the already-known distinct-temperature/span rules
prove structurally inadmissible.

Let ``p = degree + 1`` and let ``S_k`` be the number of ``k``-temperature candidate
support sets whose minimum and maximum bracket the complete declared fitted range.
Then the number of structurally eligible designs before rank/conditioning checks is

```text
eligible_count = S_N                                  # distinct_only
eligible_count = sum(S_k * C(N - 1, k - 1),
                     k = p .. min(M, N))              # repeats_allowed
```

because ``C(N - 1, k - 1)`` is the number of positive multiplicity allocations of
``N`` runs over one selected ``k``-temperature support set. If ``L`` candidates are
at or below ``Omega_min`` and ``H`` candidates are at or above ``Omega_max``, then
``Omega_min < Omega_max`` makes those endpoint-support groups disjoint and the
span-bracketing support-set count is available directly by inclusion-exclusion:

```text
S_k = C(M, k)
      - C(M - L, k)
      - C(M - H, k)
      + C(M - L - H, k)
```

with ``C(a, b) = 0`` when ``b > a``. Thus ``S_k`` is calculated deterministically
from the ordered finite candidate set rather than discovered by enumerating all raw
multisets. The search generator then visits each structurally eligible canonical
design exactly once in lexicographic order. Rank/conditioning feasibility is checked
before ``J_T`` is evaluated.

The implementation search-space ceiling applies to this exactly calculated
**structurally eligible count**, while evidence may retain both raw and eligible
counts. This is important for high-degree planning: when ``N`` is close to the
``degree + 1`` identifiability minimum, most repeat-containing raw multisets may be
provably inadmissible and must not cause a false resource-limit rejection.

Complete-design planning in the initial release is intentionally a **small curated
candidate-set** capability, not a promise to optimize dense 1–5 °C grids across
hundreds of degrees. The range/spacing convenience helper may materialize a candidate
list that is perfectly valid for one-step planning yet too large for exhaustive joint
planning; in that case the complete-design operation fails explicitly at its search
limit rather than silently thinning the grid. The intended launch scale is candidate
sets in the low tens with run budgets in the single digits to low teens, subject to
the actual structurally eligible design count.

Before the public API is declared implementation-ready, benchmarks on the supported
Python runtime range must publish the exact tested envelope and choose the named
search-space ceiling. The benchmark gate must include representative distinct-only,
repeats-allowed, and high-degree-near-identifiability cases. If those benchmarks show
that only toy-sized curated searches are practical, the exhaustive-only scope must be
revisited **before** release rather than shipping a headline complete-design feature
whose normal documented inputs mostly hit the resource ceiling.

If the structurally eligible count exceeds the fixed implementation search-space
ceiling, planning fails **before search** with an explicit diagnostic containing the
calculated eligible count, raw count, and supported limit. The package does not
silently coarsen candidates, sample designs, truncate enumeration, or switch to a
heuristic. Exceeding this limit is an implementation resource limit, not scientific
infeasibility. As with the quadrature resource guard, the numerical ceiling is a
named implementation constant selected from benchmarks rather than a scientific
constant frozen here.

The initial complete-design outcome taxonomy therefore distinguishes:

- structural infeasibility established before search;
- exact search not attempted because the supported search-space ceiling was
  exceeded;
- exhaustive proof that no numerically admissible design exists; and
- globally solved complete design.

There is no ``best_found`` or local-optimum status in the initial 0.9.0 public
contract. Such evidence semantics remain appropriate for a future non-exhaustive
search extension, but are not frozen before an implementation needs them. Atkinson
(2015, section 7) describes exact-design exchange algorithms over candidate sets,
including repeated searches from random starting points; NIST Engineering Statistics
Handbook sections 5.5.2.1 and 4.3.4 independently document computer-aided exchange
search and the absence of a general guarantee that a generated design is the true
global optimum. Together they support the conservative exhaustive-only initial
scope without requiring those heuristic-search policies to be frozen before they
are needed.

Successful exhaustive complete-design evidence retains the complete exact-tie count
for globally equal computed minima. It does not retain every losing design.

Budget profiles must preserve an important repeat-policy asymmetry in search-limit
status using the **structurally eligible** counts above. Under
``repeat_policy = distinct_only``, the number of span-bracketing ``N``-temperature
support sets is not guaranteed to increase with ``N``; it can peak and later fall as
``N`` approaches ``M``. Ceiling-exceeded rows can therefore be **noncontiguous**, and
a later budget must not be skipped merely because an earlier one exceeded the limit.
Under ``repeat_policy = repeats_allowed``, once at least one eligible support set
exists, every eligible support set has at least ``p >= 2`` temperatures and its
positive-composition count ``C(N - 1, k - 1)`` increases with ``N``. The total
structurally eligible count therefore increases with run budget; once the exhaustive-
search ceiling is exceeded, all larger run budgets also exceed it. Budget-profile
evidence and iteration logic must reflect this difference explicitly so a hole in a
distinct-only profile is not mistaken for an internal error.

Globally solved rows on either side of an unavailable budget remain comparable under
the monotonic information argument: increasing the allowed run budget cannot increase
the globally minimum ``J_T`` when a valid larger design exists under the same
assumptions.

##### Required numerical and scientific validation

The implementation must be validated against independently derived references and
provable invariants rather than only self-comparison between two code paths. Required
coverage includes at least:

- closed-form constant-sensitivity polynomial moments for complete ``M_T`` matrices;
- tabulated-model piecewise analytic moments, including the maximum supported
  polynomial degree;
- independent direct scalar integration of the original ``J_T`` definition versus
  ``trace(C_theta M_T)`` with the combined quadrature-plus-roundoff error budget;
- fixed-planning-basis covariance re-centering for every candidate, including
  incomplete one-step spans and independently checked basis-equivalent scores;
- a degree-12 end-to-end covariance-transform/``J_T`` probe against an independent
  higher-precision reference, including close-score candidates and admissible systems
  near the conditioning guardrail, used to establish the documented numerical
  invariant allowance rather than an optimization-tie threshold;
- priority-partition splitting invariance when adjacent pieces have the same weight;
- invariance to common positive rescaling of all priority weights;
- deterministic quadrature repeatability and structural breakpoint splitting;
- finite/positive sensitivity failures and forced quadrature non-convergence;
- matrix symmetry and expected positive-semidefinite behavior within documented
  numerical allowances;
- analytically derived worst-case extrema for constant-sensitivity, tabulated,
  polynomial, and CVD cases;
- an independently derived high-precision top-degree stationary-polynomial fixture
  exercising a near-degree-34 ``h(T)`` and a numerically difficult admissible case;
- a deliberately narrow interior maximum that a coarse grid would miss;
- left- versus right-side maxima at a nonsmooth package-model boundary;
- a full-range maximum located inside a zero-weight interval;
- exact tied maximum locations;
- third-party maximum status ``not_established`` rather than a sampled pseudo-max;
- exact candidate-list exhaustive one-step comparison;
- complete-design exhaustive enumeration against small independently enumerated
  reference spaces;
- exact structurally eligible design-count formulas and evidence, including a
  high-degree case where the raw repeat-multiset count greatly exceeds the actually
  identifiable search space;
- pre-release performance benchmarks that publish the tested complete-design
  candidate/run envelope and justify the implementation search-space ceiling;
- exact tie counts and canonical representative invariance to caller input order;
- globally solved budget-profile non-increasing ``J_T`` behavior;
- noncontiguous exhaustive-search-limit gaps under distinct-only designs; and
- monotonic search-space ceiling behavior under repeats-allowed designs.

The no-grid root strategy used for the full-range maximum should also receive direct
boundary and narrow-extremum tests, following the same principle already used by the
package's polynomial monotonicity validation.

##### Equation and implementation provenance requirement

The equations in this subsection are part of the scientific design contract, not
mere explanatory notation. Production numerical helpers implementing them must carry
concise comments or docstrings that identify the corresponding equation/purpose and
point back to this design section and ``docs/REFERENCES.md``. In particular, code
should not leave the following as unexplained matrix algebra:

- ``v_R(T) = phi^T C_theta phi``;
- ``v_T(T) ~= (dT/dR)^2 v_R(T)``;
- the normalized sensitivity-weighted ``M_T`` integral;
- ``J_T = trace(C_theta M_T)``, including the classical I-optimal trace/moment-
  matrix derivation and the project's added RTD sensitivity/priority weighting;
- marginal ``Delta J`` and RMS reductions;
- the positive-semidefinite information-update monotonicity invariant;
- the fixed Householder-``R`` conditioning guardrail;
- the cancellation-aware ``tau_J`` trace-audit allowance and the distinct
  end-to-end numerical allowance used only for provable invariants;
- the 15/31 Gauss-Kronrod moment construction and its ``1e-12`` numerical target;
- ``h(T) = q'(T) r(T) - 2 q(T) r'(T)`` for full-range extrema; and
- the raw and structurally eligible finite-design combinatorial counts used for
  exhaustive-search preflight.

The comments should explain **why** each equation is used, not merely restate its
syntax. Where a rule is a project design decision rather than something prescribed
by a cited source, the documentation must say so explicitly. This preserves the
project's established distinction between external scientific provenance and local
API/numerical policy.


#### Portable model-definition format decision

The 0.6.0 portable model definition is a **separate artifact type and schema**
from conformance `model-fixtures.json`. This is a deliberate compatibility
decision, not an implementation detail. Conformance fixtures are allowed to encode
intentionally invalid definitions and local `fixture_id` values for testing; a
deployable model format must represent only valid reconstructable models and must
not inherit fixture-catalog lifecycle or `expected_status` semantics.

The portable format should nevertheless reuse the same scientific vocabulary and
parameter meanings so the project does not create two semantic definitions of a
model. Version 1 should use a structure conceptually like:

```json
{
  "artifact_type": "portable_model_definition",
  "format_version": 1,
  "model_kind": "polynomial",
  "definition": {},
  "metadata": {}
}
```

The exact kind-specific fields are schema-defined, but the compatibility rules are
fixed:

* `format_version` belongs to the portable-definition format and is independent of
  conformance `contract_version`;
* a loader must reject an unsupported `format_version` rather than guessing at
  newer serialization semantics;
* core and kind-specific fields are closed/validated rather than accepting unknown
  behavior-changing fields silently, and an unsupported `model_kind` must be
  reported explicitly rather than misinterpreted as a known kind;
* model-kind identifiers and parameter names reuse established project meanings
  wherever the same scientific concept already exists;
* version 1 covers the four model-definition families already exercised by the
  custom conformance vocabulary: characterized standard-characteristic models,
  custom Callendar-Van Dusen models, polynomial models, and piecewise-polynomial
  models; portable tabulated definitions remain a compatible future extension and
  are not required to release 0.6.0;
* the definition contains every numerical value needed to reconstruct the model,
  including its valid range and any authorized piecewise continuity adjustments;
* a portable artifact cannot encode the conformance-only concept of an intentionally
  invalid model definition;
* an optional `metadata` object is reserved for application-neutral, non-behavioral
  provenance and future traceability fields; metadata cannot alter conversion
  behavior, and portable-definition round trips should preserve it even when a
  consumer does not interpret every metadata entry; and
* hardware configuration, equipment-channel names, installation locations, probe
  asset identifiers, and application-specific semantics remain outside the portable
  model definition.

The implemented Python API lives in `rtd_sensor.portable` and deliberately
mirrors this boundary:

* `model_to_portable_definition(model, metadata=...)` emits a JSON-compatible
  dictionary for one supported public model;
* `model_from_portable_definition(artifact)` validates the artifact, reconstructs
  the public model, and returns preserved non-behavioral metadata separately;
* malformed artifacts use `InvalidPortableModelDefinitionError`, while an
  unsupported Python model passed to the serializer is a type-category error; and
* the checked-in Draft 2020-12 schema is
  `portable/v1/model-definition.schema.json`. Runtime loading remains dependency-free
  and does not require the development-only `jsonschema` package.

Human-readable model names and Python-specific `coefficient_source` fields are not
implicitly serialized because they may contain physical-probe identity or local
application context. Callers may copy appropriate application-neutral provenance
into the portable `metadata` object explicitly.

For piecewise models, version 1 serializes the source segments and the authorized
`maximum_continuity_adjustment_ratio`. The applied normalized-ratio offsets remain
deterministic derived values of the existing piecewise model semantics rather than
a second serialized source of numerical truth. Reconstruction must rederive the
same offsets and conversion behavior from the preserved source definition.

Richer calibration provenance may later standardize fields such as certificate
identifier, calibration date and laboratory, reference standard, fitting method,
calibrated range, uncertainty information, source precision, and notes. Version 1
reserves the metadata extension point now without making that richer certificate
schema a 0.6.0 requirement.

Round-trip reconstruction through the portable-definition API must preserve the
model's numerical parameters exactly where the representation permits exact JSON
number round trips and must preserve conversion behavior within explicitly tested
tolerances. Serialization/deserialization tests should reconstruct the public model
and compare both conversion directions and declared boundaries rather than merely
comparing serialized text.

Physical sensor identity remains separate from mathematical model identity. A
canonical model identity such as `pt100` describes RTD behavior; it does not
identify a particular probe serial number, installed location, equipment channel,
replacement history, or calibration-certificate association. Downstream inventory
and control systems may retain those identities alongside a portable model
definition without moving them into the core scientific model.

### Generic polynomial characteristics

`rtd_sensor.models.PolynomialRTDModel` provides the first material-neutral public characteristic model. For `x = T - Tref`, it represents:

```text
R(T) = Rref × (1 + c1*x + c2*x² + ... + cn*xⁿ)
```

The constant term is implicit because the normalized resistance must equal 1 at the reference temperature. The public model retains `Rref`, `Tref`, the normalized coefficients, the declared valid range, a human-readable name, and optional coefficient provenance.

A polynomial model is accepted only when the complete declared interval is mathematically usable as an RTD characteristic. Validation therefore requires:

* finite coefficients and reference quantities;
* positive reference resistance;
* finite, positive resistance throughout the supported range;
* a strictly positive analytical slope throughout the range; and
* a bounded, unique inverse.

The slope is evaluated analytically. Its extrema are located from roots of the polynomial's second derivative using recursive derivative partitioning and bounded bisection, rather than by checking an arbitrary temperature grid. This preserves the same design goal established by custom CVD validation: a narrow non-monotonic region must not be able to hide between sampled test points.

Once the curve is proven strictly increasing, resistance-to-temperature conversion uses bounded bisection on the authoritative forward polynomial. The library does not require SciPy and does not substitute a lower-accuracy approximate inverse polynomial merely for speed.

The single-polynomial model must not be used to distort an authoritative piecewise or tabulated characteristic. Piecewise-polynomial and table-backed characteristics use the separate representations described below.

### Piecewise polynomial characteristics

`rtd_sensor.models.PiecewisePolynomialRTDModel` represents one characteristic as an ordered set of contiguous polynomial intervals. A public `PiecewisePolynomialSegment` stores the complete normalized coefficient set `(c0, c1, ..., cn)` because published piecewise equations commonly assign an independent constant term to each interval. Each segment may also declare its own temperature origin.

Every source segment is validated analytically for finite positive resistance and strictly positive slope over its entire interval. Segment partitions may not contain gaps or overlaps. The complete model is then inverted with bounded bisection only after the joins have been made continuous, preserving the library invariant that a supported resistance maps to one temperature.

The continuity policy is deliberately explicit. Some authoritative engineering references publish independently rounded polynomial fits whose values differ slightly at a shared boundary even though the underlying physical characteristic is intended to be continuous. Minco's published 120-ohm nickel stepwise approximation is a concrete motivating example. The source coefficient tuples are preserved unchanged. By default, source-level discontinuities are rejected; an explicit `maximum_continuity_adjustment_ratio` may authorize a bounded additive normalized-ratio offset to a segment constant term. Stitching is anchored at the declared reference-temperature segment and propagated outward, and the applied offsets remain available as model metadata. Pure floating-point roundoff at an otherwise continuous join is tolerated automatically.

Only constant offsets are used for stitching, so source-segment slopes and higher derivatives are not altered. If adjacent source segments are continuous in value but not exactly in first derivative, the public sensitivity convention uses the right-hand segment at an interior boundary and the final segment at the global maximum. This is a deterministic one-sided convention, not a claim that a non-C1 source fit has a unique derivative at the join.

This bounded-stitching mechanism must not be used to conceal genuinely incompatible equations. The permitted adjustment is part of the model definition and should be justified from source precision or an equivalent traceable reason.

The generic model also deliberately supports a reference temperature other than 0 °C. That capability is architectural future-proofing; it does not imply that any particular future Cu10 or other characteristic is supported until its provenance and reference definition are independently established.

### Tabulated characteristics

`rtd_sensor.models.TabulatedRTDModel` represents a characteristic whose authoritative source is a resistance/temperature table rather than an equation. Each immutable `TabulatedRTDPoint` retains one public numeric source row `(temperature_c, resistance_ohms)`; the model snapshots the ordered point sequence without fitting, smoothing, continuity correction, or coefficient generation. Optional `table_source` and `source_precision` strings retain provenance and the source table's stated resolution/precision context.

The initial interpolation policy is deliberately piecewise linear. A monotonic cubic or spline can imply curvature the source never published and can introduce overshoot or more complicated inverse behavior. Linear interpolation instead preserves every source point, remains strictly monotonic when the table is strictly monotonic, and is exactly invertible inside each source interval without a numerical root finder. This scalar, dependency-free calculation is the reference behavior for the table model.

Construction requires at least two finite points with strictly increasing temperatures and strictly increasing positive resistances. The increasing-resistance rule preserves the package-wide positive-temperature-coefficient and unique-inverse invariant. Table order is source order; the model does not sort or silently repair malformed input.

Extrapolation is not part of the initial public API. Forward or inverse conversion beyond the first/last table point raises `RTDOutOfRangeError`. This avoids turning a source table into an unsupported mathematical characteristic outside its traceable range. If extrapolation is ever added, it requires an explicit policy rather than changing this default silently.

Within an interval, `dR/dT` is the exact line slope and `dT/dR` is its reciprocal. At an interior source knot, sensitivity uses the interval on the knot's right; the final knot uses the last interval. The convention is deterministic but does not claim that a slope-changing table knot has a unique mathematical derivative. Interpolated floating-point output may display more digits than the source rows; those digits do not create additional scientific precision.

### IEC 60751 tolerance classes

Tolerance calculations are a separate layer from nominal resistance-temperature conversion and from calibration. IEC 60751:2022 defines tolerance as a maximum permitted temperature deviation from the nominal resistance-temperature relationship and states that the tolerance classes apply for any value of `R0`.

The standard distinguishes two related cases:

* **platinum resistors** (bare sensing elements), whose class designation includes construction, for example `W 0.15` for wire wound or `F 0.15` for film; and
* **thermometers** (assembled temperature sensors), whose standard classes are `AA`, `A`, `B`, and `C` and whose validity range depends on whether the thermometer uses a wire-wound or film platinum resistor.

The standard tolerance formulas are:

| Thermometer class | Resistor class value | Maximum permitted deviation (°C) |
| --- | --- | --- |
| AA | 0.1 | `±(0.1 + 0.0017 × |t|)` |
| A | 0.15 | `±(0.15 + 0.002 × |t|)` |
| B | 0.3 | `±(0.3 + 0.005 × |t|)` |
| C | 0.6 | `±(0.6 + 0.01 × |t|)` |

The public `rtd_sensor.tolerance` API exposes the positive magnitude of that maximum permitted deviation in degrees Celsius. A returned value of `x` therefore describes a nominal tolerance band of ±`x` °C around the reference temperature; it is not a prediction that the sensor will have an error of magnitude `x`. The API enforces the IEC 60751:2022 temperature range of validity for each standard class and construction and does not extrapolate a standard class beyond the range in which the standard defines that designation.

`thermometer_tolerance_c()` accepts the standard thermometer class and the resistor construction separately. `platinum_resistor_tolerance_c()` uses normalized ASCII designations such as `W0.15` and `F0.3`, corresponding to the standard's wire-wound and film resistor class designations.

Special supplier/user-agreed tolerance classes and modified ranges permitted by IEC 60751 are not represented as standard classes by this API. They should not be inferred from the standard table without explicit supplier documentation. The numerical tolerance API also does not certify full IEC 60751 conformity; the standard imposes additional construction and test requirements outside this calculation layer.

Tolerance and uncertainty are deliberately not conflated. A tolerance limit is a bounded conformity requirement; converting that bound into a standard uncertainty requires an explicit uncertainty model and is deferred to the uncertainty-propagation layer.

### Measurement uncertainty foundation

The uncertainty layer follows the measurement-uncertainty terminology and first-order propagation framework described by JCGM 100:2008 (GUM) and NIST Technical Note 1297. The initial public API provides small numerical primitives rather than a monolithic sensor-error estimate.

All uncertainty components passed to combination helpers are expressed as **standard uncertainties** (estimated standard deviations) in common output units. Independent components are combined by root-sum-square. Expanded uncertainty is calculated as `U = k × u_c`, and the coverage factor `k` must be supplied explicitly. The library does not infer a confidence level from `k`.

For a symmetric bounded input `±a`, the public helper can convert the bound to standard uncertainty under an explicitly selected distribution:

```text
rectangular: u = a / sqrt(3)
triangular:  u = a / sqrt(6)
```

The choice of distribution is a property of the uncertainty model, not of the numerical bound itself. Consequently, IEC tolerance limits, manufacturer specifications, calibration limits, and similar bounded quantities are never converted automatically. The caller must explicitly choose the probability model justified by the available information.

Each supported characteristic exposes its local analytical resistance slope where the characteristic form permits it. For a normalized RTD model:

```text
dR/dT = Rref × d(R/Rref)/dT
dT/dR = 1 / (dR/dT)
```

For the IEC Callendar–Van Dusen platinum characteristic specifically, `Rref = R0` at 0 °C and:

For `t >= 0 °C`:

```text
d(R/R0)/dT = A + 2Bt
```

For `t < 0 °C`:

```text
d(R/R0)/dT = A + 2Bt + C t² (4t - 300)
```

These sensitivities are calculated from the active characteristic rather than approximated from the final temperature conversion. The CVD and polynomial models both provide analytical `dR/dT`, including user-supplied coefficients. They are the sensitivity coefficients used by the measurement-uncertainty layer to propagate resistance uncertainty into temperature uncertainty.

The initial helper for combining standard uncertainties assumes uncorrelated inputs. Covariance terms, coefficient covariance, effective degrees of freedom, coverage-interval selection, and Monte Carlo propagation remain outside this first uncertainty foundation and must not be implied by the root-sum-square helper.

### Measurement boundary

The core library begins with the best available estimate of the RTD sensing element's resistance in ohms.

Two-wire, three-wire, and four-wire topology affects acquisition and compensation rather than the standardized resistance-temperature relationship. Wiring topology, excitation, ADC configuration, reference-resistor calculations, lead-resistance compensation, and hardware fault detection therefore belong to hardware-facing acquisition layers.

The scientific conversion layer must not require a wire-count parameter.

Acquisition status must also remain separate from RTD conversion status. Hardware-facing layers may need outcomes such as `open_circuit`, `short_circuit`, `adc_fault`, `reference_resistor_fault`, `converter_fault`, `spi_failure`, or `stale_sample`; these are not `rtd-sensor` model outcomes. The language-neutral RTD contract instead owns statuses such as `ok`, `out_of_range_low`, `out_of_range_high`, `invalid_input`, `invalid_model`, and `calculation_failure`. A higher-level protocol may report both domains, or mark the RTD conversion as not evaluated when acquisition fails, without merging their vocabularies.

### Cross-language and constrained-runtime interoperability

The stable conformance contract is the authority for reproducing `rtd-sensor` behavior outside Python. A separate MCU-specific scientific definition system should not be created. A constrained implementation may claim only the model, operation, and numerical profiles that it actually supports, and a nominal Pt100 resistance-to-temperature implementation can already begin from the 0.5.1 conformance foundation.

For 0.6.0, constrained-precision support has been extended deliberately only to
characterized reference resistance using the already supported IEC 60751 PT-385
characteristic. The published characterized-R0 fixtures use the same empirically
justified `binary32_compatible` tolerances as the built-in profile: 0.002 Ω for
temperature-to-resistance and 0.001 °C for resistance-to-temperature.

The validation matches the rigor used for the built-in profile. The genuinely
independent C11 float path does not call Python or a binary64 conversion routine
and then cast the answer to `float`. A deterministic 1,320,843-case study spans
representative R0 deviations around the 100 Ω, 500 Ω, and 1000 Ω scales, negative
and positive temperatures, full-range boundaries, and inverse conditioning. Its
measured worst-case errors, binary32 R0 representation effect, compiler matrix,
and engineering margin are recorded in
`conformance/consumers/c11/BINARY32_CHARACTERIZED_R0.md`. The conformance claim
remains fixture-scoped for characterized-R0 test subjects; this work does not
turn portable model definitions into conformance identities.

That claim must not be generalized automatically to arbitrary custom model families. Each family should gain a constrained-precision profile only after its own numerical behavior is independently characterized:

- **custom CVD:** include two-sided, positive-only, and negative-only ranges, unusual but valid ratio-crossing cases, boundaries, inverse conditioning, representative coefficient ranges, and invalid or non-monotonic definitions;
- **single polynomial:** study coefficient scaling, conditioning, representative supported models, and defensible limits rather than making a blanket claim over arbitrary polynomials;
- **piecewise polynomial:** additionally exercise exact join routing, continuity adjustments, segment-local origins, endpoint rounding, and the distinction between source and derived coefficients; and
- **tabulated models:** define conformance for exact source points, interpolation and inverse interpolation, first and last intervals, local sensitivity, source precision, endpoints, just-outside range rejection, and monotonicity validation.

The existing C11 consumer remains an independent conformance implementation. It proves that the public contract is sufficient for a non-Python implementation, but it is not automatically the production runtime API for firmware or other constrained systems.

A future production embedded implementation should be free to use static or stack allocation, compile only selected models, implement only required operations such as resistance-to-temperature conversion, and return an explicit status plus result rather than emulate Python exceptions. A constrained implementation need not include batch conversion, simulation, fitting, tolerance calculations, uncertainty analysis, or model families it does not claim. Runtime JSON parsing must not be required: JSON artifacts are suitable for generation, CI, validation, and build tooling, while firmware may compile equivalent validated constants or structures. Range enforcement must follow the claimed RTD model contract, and a target should claim a published numerical profile such as `binary32_compatible` rather than merely stating that it uses `float`.

If production embedded use becomes substantial, a separate C/C++ sibling project is preferable by default to placing MCU toolchains and firmware-oriented APIs in the Python package. That decision should be based on actual implementation experience. Generated C headers, C++ `constexpr` definitions, compact selected-model bundles, or lookup tables may later reduce duplicated scientific constants, but should be introduced only when downstream evidence or profiling shows a maintenance, code-size, speed, power, or deterministic-latency benefit. Generation should permit selected models, operations, and numerical profiles rather than forcing every target to carry the complete catalog. Any generated or lookup representation must still satisfy its claimed conformance profile.

Cross-language implementation guidance is consolidated in
`docs/CROSS_LANGUAGE_IMPLEMENTATIONS.md`: how to consume released artifacts,
claim supported subsets, interpret stable model and characteristic identities,
map RTD statuses, use numerical acceptance profiles, and preserve the hardware
boundary. Downstream host/MCU protocols should reference those stable identities
and statuses rather than inventing parallel RTD vocabularies. Runtime JSON is
optional tooling rather than a firmware requirement.

### Planned characteristic expansion

The current development roadmap is maintained in [`ROADMAP.md`](ROADMAP.md).
Version 0.4.0 added generic single- and piecewise-polynomial infrastructure
plus distinct built-in Ni1000 6180, Ni1000 TK5000, and North American Ni120
characteristics. Version 0.5.0 added the table-backed characteristic form and
public discovery/composition contracts. Later characteristic research includes
additional nickel/Balco variants and Cu10/Cu100 candidates.

A nominal resistance or TCR value alone is not sufficient evidence that two RTDs share one characteristic. Every built-in characteristic must retain explicit identity and provenance, and apparently similar manufacturer curves must remain distinct when their published resistance/temperature behavior differs.

Nominal conversion, calibration, tolerance, and uncertainty are related but separate concerns. Basic resistance-temperature conversion should continue to return the ideal value represented by the selected model. Calibration, tolerance, and uncertainty should be layered on top rather than silently altering nominal conversion behavior.

The scalar, dependency-free implementation should remain the reference calculation. Future vectorized, fitting, or lookup implementations should be verified against their authoritative source representation and must preserve the same range and inversion guarantees.

### Support-readiness policy

An RTD type or standardized curve must not be described as supported merely because the generalized implementation is mathematically capable of calculating it.

Before an additional RTD type is publicly exported or advertised, the project must include:

* the applicable equation or curve definition;
* authoritative coefficient provenance;
* the documented valid temperature range;
* independently sourced reference values;
* representative negative- and positive-temperature tests where applicable;
* boundary and out-of-range tests;
* round-trip and monotonicity tests;
* public-API tests;
* user documentation;
* simulation tests where simulation support is provided.

Unfinished RTD types should not be exposed as placeholder modules, constants, or documented supported features.

### Completed Pt1000 milestone

Pt1000 is now implemented as a verified public RTD type. The milestone established:

1. the internal normalized curve abstraction;
2. the reusable RTD model abstraction;
3. Pt100 on the shared model without changing its public API;
4. generic model tests for R0 behavior, normalized resistance, boundaries, validation, monotonicity, and round trips;
5. Pt1000 reference provenance and independent reference-value tests;
6. the public `rtd_sensor.pt1000` conversion module; and
7. model-aware simulation for the then-supported Pt100 and Pt1000 models while
   preserving Pt100 defaults.

No additional RTD type should be added merely because the shared engine can represent it. Each future type must independently satisfy the support-readiness policy above.


Pt500 and the currently supported nickel characteristics now follow that process as verified public types. Copper and other future RTD characteristics must follow the same process rather than being assumed supported merely because the generalized model layer can be extended.


### Completed Pt500 milestone

Pt500 is implemented as the third verified IEC 60751 PT-385 nominal platinum RTD. It reuses the same normalized curve as Pt100 and Pt1000 with `R0 = 500 Ω`, but its public support is independently validated against a published Pt500 resistance table rather than inferred solely from scaling the existing models. Simulation and uncertainty propagation accept Pt500 through the same model-aware interfaces used by the other built-in platinum RTDs.


## 13. Related future repositories

Possible companion projects include:

```text
rtd-hardware
    Shared hardware-facing interfaces and measurement models

rtd-max31865
    MAX31865 driver independent of host platform

rtd-bbb
    BeagleBone-specific acquisition adapters

rtd-rpi
    Raspberry Pi-specific acquisition adapters

rtd-examples
    Complete applications and integration examples
```

These names are provisional. Hardware packages should be split by actual abstraction boundary rather than created in advance.

A production C/C++ RTD implementation may eventually justify a sibling project such as `rtd-sensor-embedded`, with `rtd-sensor` remaining the Python reference implementation and conformance authority. Do not create that repository merely to satisfy an architectural diagram; decide after real embedded work establishes the required runtime API, compiler/toolchain support, selected-model build strategy, and release cadence.

## 14. Explicit non-goals for the first stable major release

The first stable major release will not include:

- board-specific hardware drivers
- ADC configuration
- GPIO, SPI, or I²C access
- analog circuit design
- lead-wire compensation algorithms tied to a circuit
- MAX31865 register handling
- process-control logic
- heater or relay control
- data logging
- graphical interfaces
- network services

## 15. Deferred design decisions

The following decisions remain intentionally deferred:

1. Alternate standardized platinum curves and historical `R0`, alpha, delta, beta coefficient notation.
2. ITS-90 interpolation support for reference-grade calibrated PRTs.
3. General covariance-aware uncertainty budgets beyond the fitted-coefficient covariance propagation implemented in 0.7.0, effective degrees of freedom, coverage-interval selection, and Monte Carlo methods.
4. The exact production embedded repository/API boundary after real MCU implementation experience exists.
5. Whether generated C/C++ deployment artifacts or lookup tables provide enough demonstrated benefit to become maintained public outputs.
6. A richer public calibration-certificate metadata schema beyond the provenance needed to reconstruct and audit a model.




## References and calculations

### Normative standard

* International Electrotechnical Commission. **IEC 60751:2022,
  Industrial platinum resistance thermometers and platinum temperature
  sensors**, Edition 3.0, published January 27, 2022.

  IEC 60751 is the normative basis for the standardized resistance-
  temperature relationship and requirements for industrial platinum
  resistance thermometers and platinum temperature sensors.

  https://webstore.iec.ch/en/publication/63753

The complete standard is not reproduced in this repository because it
is a copyrighted publication available from the IEC.

### Public technical verification

* Analog Devices. **MAX31865 RTD-to-Digital Converter Data Sheet**,
  “Temperature Conversion” section.

  This data sheet provides an openly accessible description of the
  Callendar–Van Dusen relationship used for platinum RTDs and publishes
  the standard PT-385 coefficients used by this implementation.

  https://www.analog.com/media/en/technical-documentation/data-sheets/MAX31865.pdf

* Fluke Calibration. **PT100 Calculator: Convert Resistance and
  Temperature**.

  The Fluke calculator publishes the PT-385 equation and coefficients
  and identifies IEC 60751, ASTM E1137, and JIS C 1604 as its source
  standards. It is used as an independently accessible check of
  selected resistance-temperature reference values.

  https://www.fluke.com/en-ca/learn/tools-calculators/pt100-calculator

  Accessed August 4, 2026.

* UST Umweltsensortechnik GmbH. **Platinum thinfilm temperature sensor elements - Pt500 series: Basic resistance values**.

  The manufacturer-published Pt500 table states that its values are calculated according to DIN EN 60751, publishes the PT-385 `A`, `B`, and `C` coefficients, and spans -200 °C through 850 °C. Selected rounded values are used as the primary independent Pt500 reference dataset.

  https://www.umweltsensortechnik.de/fileadmin/assets/downloads/platin/datenblaetter/pt500-basic-resistance-values-202201-Rev00.pdf

  Accessed August 10, 2026.

* Italcoppie Sensori. **Pt1000 Resistance Chart**.

  The manufacturer-published table states that its values are according
  to DIN EN IEC 60751 and spans -200 °C through 850 °C in 1 °C
  increments. Selected rounded values are used as the primary independent
  Pt1000 reference dataset.

  https://www.italcoppie.com/wp-content/uploads/2022/08/Pt1000-Resistance-Chart-A4.pdf

* ABB. **Technical Note 153: Process variable measurement using an RTD**.

  ABB publishes an independent Pt1000 resistance table over a central
  portion of the range. These values corroborate the Italcoppie Pt1000
  references at their published precision.

  https://library.e.abb.com/public/f23fd36098164ef18489c604a0eb1308/Technical_Note_153_ProcessVariableMeasurementUsingARTD.pdf

* Beamex. **Pt100 temperature sensor – useful things to know**.

  Beamex documents the IEC-style Callendar–Van Dusen calibration
  coefficient form `R0`, `A`, `B`, `C` and notes that `C` may be absent
  when a sensor has not been calibrated below 0 °C. This supports the
  public custom-coefficient model's treatment of positive-only
  calibration ranges.

  https://blog.beamex.com/pt100-temperature-sensor

### Measurement uncertainty references

* Joint Committee for Guides in Metrology. **JCGM 100:2008, Evaluation of measurement data — Guide to the expression of uncertainty in measurement (GUM 1995 with minor corrections)**.

  This is the primary framework used for standard uncertainty, sensitivity coefficients, law-of-propagation concepts, combined standard uncertainty, and expanded uncertainty.

  https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf

* National Institute of Standards and Technology. **NIST Technical Note 1297, Guidelines for Evaluating and Expressing the Uncertainty of NIST Measurement Results**.

  TN 1297 provides openly accessible guidance for Type B evaluation, rectangular and triangular distributions, root-sum-square combination of independent standard uncertainties, and expanded uncertainty.

  https://www.nist.gov/pml/nist-technical-note-1297

### Implemented curve and models

The implementation supports the standard IEC 60751 PT-385 curve:

```text
A  = 3.9083 × 10⁻³ °C⁻¹
B  = -5.775 × 10⁻⁷ °C⁻²
C  = -4.183 × 10⁻¹² °C⁻⁴
```

The currently supported nominal IEC 60751 PT-385 platinum models are:

```text
Pt100:  R0 = 100.0 Ω
Pt500:  R0 = 500.0 Ω
Pt1000: R0 = 1000.0 Ω
```

For temperatures from 0 °C through 850 °C:

```text
R(t) = R0 × (1 + A×t + B×t²)
```

For temperatures from -200 °C through 0 °C:

```text
R(t) = R0 × [1 + A×t + B×t² + C×(t - 100)×t³]
```

The built-in Pt100, Pt500, and Pt1000 modules model the ideal standardized curve.
Public model objects can consume an individually characterized `R0` or a
traceable custom Callendar–Van Dusen coefficient set. Version 0.6.0 added
polynomial calibration fitting from observations, and 0.7.0 added characterized
`R0` and custom Callendar–Van Dusen parameter fitting. Sensor tolerance,
lead-wire resistance, self-heating, and measurement-circuit errors remain
separate concerns; the 0.8.0 self-heating analysis layer does not change nominal
RTD curve behavior.

### Test provenance

Pt100 reference-value tests use selected, rounded PT-385 values independently
checked against the Fluke PT100 calculator and published standard-compatible
tables. Pt500 reference-value tests use selected rounded values from the UST
Umweltsensortechnik Pt500 table. Pt1000 reference-value tests use selected
rounded values from the Italcoppie Pt1000 resistance chart, with ABB values
providing an additional independent cross-check over part of the range.

Exact supported-range boundary tests use values calculated from the full
Callendar–Van Dusen equation rather than rounded two-decimal table
values. This avoids rejecting a rounded boundary value such as 18.52 Ω
when the equation-defined resistance at -200 °C is slightly greater.

Round-trip tests are supplementary and are not treated as independent
verification, because forward and inverse implementations could share
the same defect.
