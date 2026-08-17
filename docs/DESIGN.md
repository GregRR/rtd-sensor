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
total effective weight, not a reduced-chi-square or degrees-of-freedom-adjusted
statistic.

The fitted `PolynomialRTDModel` uses the midpoint of the declared fitted validity
range as its reference temperature. This is a deterministic numerical anchor, not a
claim that a calibration observation exists at that exact temperature.

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
3. Covariance-aware uncertainty propagation, effective degrees of freedom, fitted-coefficient covariance, and Monte Carlo methods.
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
traceable custom Callendar–Van Dusen coefficient set, but the library does
not currently fit calibration coefficients from observations. Sensor
tolerance, lead-wire resistance, self-heating, and measurement-circuit
errors remain separate concerns.

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
