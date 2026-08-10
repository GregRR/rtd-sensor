# pt100-core Design

## 1. Purpose

`pt100-core` provides a small, dependable, platform-independent implementation of resistance-to-temperature and temperature-to-resistance conversion for standardized platinum resistance temperature detectors.

The currently supported sensor models are:

- Pt100: nominal resistance 100 Ω at 0 °C
- Pt1000: nominal resistance 1000 Ω at 0 °C
- standard: IEC 60751
- normalized platinum curve: PT-385, α ≈ 0.00385

The project exists so applications can share one tested scientific conversion layer while keeping hardware acquisition code separate.

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
pt100-core
              |
              v
temperature in Celsius
```

`pt100-core` does not determine how raw electrical signals become resistance. That responsibility belongs to hardware-facing code.

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

### 3.3 Small public API

The public interfaces for supported RTD models should remain parallel and simple:

```python
from rtd import ni1000, ni1000_tk5000, pt100, pt1000

temperature_c = pt100.resistance_to_celsius(resistance_ohms)
resistance_ohms = pt100.celsius_to_resistance(temperature_c)

pt1000_temperature_c = pt1000.resistance_to_celsius(resistance_ohms)
pt1000_resistance_ohms = pt1000.celsius_to_resistance(temperature_c)

ni1000_temperature_c = ni1000.resistance_to_celsius(resistance_ohms)
ni1000_resistance_ohms = ni1000.celsius_to_resistance(temperature_c)

tk5000_temperature_c = ni1000_tk5000.resistance_to_celsius(resistance_ohms)
tk5000_resistance_ohms = ni1000_tk5000.celsius_to_resistance(temperature_c)
```

### 3.4 Simulation as a first-class use case

Temperature-to-resistance conversion is part of the supported public API, not merely an internal helper. It enables application testing without attached hardware.

### 3.5 No premature hardware coupling

Wire compensation, excitation circuits, ADC scaling, amplifier gain, reference resistors, and device-register handling must not leak into the scientific conversion layer.

### 3.6 Verifiability

Results must be tested against authoritative IEC 60751 reference values or independently reproduced reference tables.

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

The supported models differ in nominal resistance at 0 °C:

```text
Pt100:  R0 = 100 Ω
Pt1000: R0 = 1000 Ω
```

Resistance-to-temperature conversion above 0 °C may use the analytic inverse of the quadratic equation. The implementation should use an algebraically stable quadratic form that avoids subtracting nearly equal terms for ordinary platinum RTD coefficients. Below 0 °C, the implementation may use a bounded numerical solution of the complete equation.

The implementation must document numerical tolerances and must avoid silently extrapolating beyond its supported range.

### 4.1 Former DIN 43760 Ni1000 6178/6180 characteristic

The built-in `rtd.ni1000` module represents the former DIN 43760 nickel
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

The built-in `rtd.ni1000_tk5000` module represents the distinct TK5000 nickel
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

`rtd.ni1000` and `rtd.ni1000_tk5000` must remain separate model identities.
They share the same nominal resistance at 0 °C but differ materially away from
that reference point, so nominal resistance alone cannot select a nickel RTD
characteristic safely.

## 5. Supported public API

The supported built-in model modules are `rtd.pt100`, `rtd.pt500`,
`rtd.pt1000`, `rtd.ni1000`, and `rtd.ni1000_tk5000`. Each exposes the same
conversion interface:

```python
def resistance_to_celsius(resistance_ohms: float) -> float:
    ...

def celsius_to_resistance(temperature_c: float) -> float:
    ...
```

Potential future convenience functions may include:

```python
def resistance_to_fahrenheit(resistance_ohms: float) -> float:
    ...

def fahrenheit_to_resistance(temperature_f: float) -> float:
    ...
```

Those convenience functions are not required for the first release. Celsius is the native temperature representation because the governing standard is expressed in Celsius.

## 6. Validation and errors

The conversion functions should reject:

- non-finite numeric values
- non-positive resistance values
- temperatures outside the documented supported range
- resistance values that cannot represent a temperature inside that range

Domain/range failures should use clear `ValueError` messages unless a dedicated exception hierarchy becomes justified. Type-category mistakes may use `TypeError`; in particular, Boolean values passed as physical numerical quantities are rejected as the wrong input type rather than coerced to numbers.

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
Pt100, Pt500, Pt1000, the former-DIN Ni1000 6180 characteristic, and Ni1000
TK5000. Pt100
remains the default for backward compatibility.

A reader that declares an RTD type establishes a model-identity invariant: its declared type must not diverge from the model used to validate or generate its resistance values. Built-in readers therefore keep `rtd_type` read-only after construction. `read_temperature_celsius()` also rejects an explicit RTD type that conflicts with a model-aware reader's declaration. Generic readers that expose only resistance remain supported; callers may select their RTD type explicitly, and untyped readers still default to Pt100 for backward compatibility.

Future simulation additions may include ramps, heating and cooling profiles, and injected open-circuit or short-circuit faults.

Simulation components expose resistance values so they exercise the same application path as real hardware.

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

The built-in Pt100, Pt500, and Pt1000 conversion functions describe the ideal standardized IEC curve. The advanced model APIs can represent an individually characterized `R0`, a traceable custom Callendar–Van Dusen coefficient set, or a separately sourced polynomial RTD characteristic. `rtd.tolerance` currently calculates the numerical IEC platinum class limit. These layers remain distinct: none of them, by themselves, establishes the total measurement accuracy of a physical installation.

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
src/rtd/
├── __init__.py
├── _curves.py
├── _models.py
├── _validation.py
├── models.py
├── ni1000.py
├── ni1000_tk5000.py
├── pt100.py
├── pt500.py
├── pt1000.py
├── simulation.py
├── tolerance.py
└── uncertainty.py

tests/
├── test_boundary_roundtrips.py
├── test_custom_cvd_models.py
├── test_models.py
├── test_ni1000.py
├── test_ni1000_tk5000.py
├── test_numeric_input_validation.py
├── test_package_api.py
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

The `rtd` namespace is intentionally broader than the initial repository name.

## 11. Repository and namespace strategy

The repository begins as `pt100-core` because users commonly search for the specific term “Pt100.”

The Python import namespace begins as `rtd`:

```python
from rtd import pt100
```

The project has now outgrown the Pt100-only identity. The planned 0.4.x migration is to rename the distribution and repository to `rtd-sensor` and the Python import package to `rtd_sensor`. That is intentionally a public migration rather than preserving the ambiguous `rtd` import forever. Existing `pt100-core` releases remain part of the historical release line and the rename must include explicit migration documentation.

The detailed feature and migration sequence is tracked in [`ROADMAP.md`](ROADMAP.md).


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
* a model identity.

This permits multiple RTD models to share one verified characteristic without duplicating conversion logic.

The implementation defines the IEC 60751 PT-385 Callendar–Van Dusen curve once and combines it with model-specific `R0` values. Pt100 uses `R0 = 100 Ω`, Pt500 uses `R0 = 500 Ω`, and Pt1000 uses `R0 = 1000 Ω`.

The low-level curve and model infrastructure remains internal. Public modules should therefore reference internal singletons through private/module-qualified names rather than exposing those implementation objects as accidental module attributes. Public wrappers expose the supported configurable and calibrated-model capabilities without making the internal numerical abstractions part of the compatibility contract.


### Public configurable and calibrated models

The public advanced-model API has four deliberately distinct levels.

`rtd.models.IEC60751RTDModel` represents an RTD that retains the standardized IEC 60751 PT-385 curve while allowing:

* an individually characterized or calibrated `R0`;
* a human-readable model or probe name; and
* a declared valid temperature range that may be narrower than the full IEC curve.

The built-in `rtd.pt100`, `rtd.pt500`, and `rtd.pt1000` modules remain the preferred APIs for nominal standard sensors. `IEC60751RTDModel` is for cases where an individual probe's `R0` is known more precisely or its usable/calibrated range should be enforced. A declared range constrains use of the model; it does not modify the underlying IEC curve.

`rtd.models.CallendarVanDusenRTDModel` represents a **platinum RTD** for which a calibration certificate, manufacturer, or other traceable technical source provides an IEC-style `R0`, `A`, `B`, `C` Callendar–Van Dusen coefficient set. It requires an explicit valid temperature range because custom coefficients have no package-defined universal range.

Callendar–Van Dusen is intentionally a platinum-specific abstraction in this package. Nickel, copper, and other non-platinum characteristics must not be forced into `CallendarVanDusenRTDModel` merely because their published resistance-temperature relationship is polynomial. They should use `PolynomialRTDModel`, `PiecewisePolynomialRTDModel`, or a future characteristic type such as a tabulated representation that faithfully matches the source definition.

The custom-CVD model follows these rules:

* `R0`, `A`, and `B` are required;
* `C` is required when the declared range includes temperatures below 0 °C and may be omitted for a wholly non-negative range;
* all numerical inputs must be finite and `R0` must be positive;
* the supplied coefficients must define a finite, positive-resistance, strictly increasing curve over the interval required for inversion;
* the declared range is enforced in both conversion directions; and
* optional `coefficient_source` metadata may retain a calibration-certificate identifier, manufacturer document, or other provenance label.

A user-supplied coefficient set is not automatically described as IEC 60751 compliant merely because it uses the same algebraic form. The standard `IEC60751RTDModel` remains the explicit API for the package's verified IEC PT-385 curve.

The library consumes characterized or calibrated parameters; it does not currently fit `R0`, `A`, `B`, or `C` from raw calibration observations. Historical `R0`, alpha, delta, beta coefficient notation and ITS-90 interpolation functions are also outside the current public API.

### Generic polynomial characteristics

`rtd.models.PolynomialRTDModel` provides the first material-neutral public characteristic model. For `x = T - Tref`, it represents:

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

The single-polynomial model must not be used to distort an authoritative piecewise or tabulated characteristic. Piecewise-polynomial characteristics use the separate representation described below; table-backed characteristics remain planned and are recorded in `ROADMAP.md`.

### Piecewise polynomial characteristics

`rtd.models.PiecewisePolynomialRTDModel` represents one characteristic as an ordered set of contiguous polynomial intervals. A public `PiecewisePolynomialSegment` stores the complete normalized coefficient set `(c0, c1, ..., cn)` because published piecewise equations commonly assign an independent constant term to each interval. Each segment may also declare its own temperature origin.

Every source segment is validated analytically for finite positive resistance and strictly positive slope over its entire interval. Segment partitions may not contain gaps or overlaps. The complete model is then inverted with bounded bisection only after the joins have been made continuous, preserving the library invariant that a supported resistance maps to one temperature.

The continuity policy is deliberately explicit. Some authoritative engineering references publish independently rounded polynomial fits whose values differ slightly at a shared boundary even though the underlying physical characteristic is intended to be continuous. Minco's published 120-ohm nickel stepwise approximation is a concrete motivating example. The source coefficient tuples are preserved unchanged. By default, source-level discontinuities are rejected; an explicit `maximum_continuity_adjustment_ratio` may authorize a bounded additive normalized-ratio offset to a segment constant term. Stitching is anchored at the declared reference-temperature segment and propagated outward, and the applied offsets remain available as model metadata. Pure floating-point roundoff at an otherwise continuous join is tolerated automatically.

Only constant offsets are used for stitching, so source-segment slopes and higher derivatives are not altered. If adjacent source segments are continuous in value but not exactly in first derivative, the public sensitivity convention uses the right-hand segment at an interior boundary and the final segment at the global maximum. This is a deterministic one-sided convention, not a claim that a non-C1 source fit has a unique derivative at the join.

This bounded-stitching mechanism must not be used to conceal genuinely incompatible equations. The permitted adjustment is part of the model definition and should be justified from source precision or an equivalent traceable reason.

The generic model also deliberately supports a reference temperature other than 0 °C. That capability is architectural future-proofing; it does not imply that any particular future Cu10 or other characteristic is supported until its provenance and reference definition are independently established.

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

The public `rtd.tolerance` API exposes the positive magnitude of that maximum permitted deviation in degrees Celsius. A returned value of `x` therefore describes a nominal tolerance band of ±`x` °C around the reference temperature; it is not a prediction that the sensor will have an error of magnitude `x`. The API enforces the IEC 60751:2022 temperature range of validity for each standard class and construction and does not extrapolate a standard class beyond the range in which the standard defines that designation.

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

### Planned characteristic expansion

The current development roadmap is maintained in [`ROADMAP.md`](ROADMAP.md). The 0.4.x work has added the generic polynomial infrastructure and distinct built-in Ni1000 6180 and TK5000 characteristics. The next characteristic-infrastructure target is piecewise-polynomial support for the specifically identified North-American Ni120 characteristic. Later research includes additional nickel/Balco variants and Cu10/Cu100 candidates.

A nominal resistance or TCR value alone is not sufficient evidence that two RTDs share one characteristic. Every built-in characteristic must retain explicit identity and provenance, and apparently similar manufacturer curves must remain distinct when their published resistance/temperature behavior differs.

Nominal conversion, calibration, tolerance, and uncertainty are related but separate concerns. Basic resistance-temperature conversion should continue to return the ideal value represented by the selected model. Calibration, tolerance, and uncertainty should be layered on top rather than silently altering nominal conversion behavior.

The scalar, dependency-free implementation should remain the reference calculation. Future piecewise, tabulated, vectorized, fitting, or lookup implementations should be verified against their authoritative source representation and must preserve the same range and inversion guarantees.

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
6. the public `rtd.pt1000` conversion module; and
7. model-aware simulation supporting Pt100 and Pt1000 while preserving Pt100 defaults.

No additional RTD type should be added merely because the shared engine can represent it. Each future type must independently satisfy the support-readiness policy above.


Pt500 now follows that process as a verified public type. Nickel, copper, and other future RTD characteristics must follow the same process rather than being assumed supported merely because the generalized model layer can be extended.


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
3. Covariance-aware uncertainty propagation, effective degrees of freedom, and Monte Carlo methods.
4. Optional vectorized conversion support.
5. Exact public APIs for piecewise-polynomial and tabulated characteristics.
6. Calibration-point fitting APIs and how fitted-coefficient covariance should
   integrate with later uncertainty propagation.




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

The currently supported models are:

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
